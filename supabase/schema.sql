-- QYRON'27 schema. Tables stay private to clients; FastAPI enforces user roles.
create extension if not exists pgcrypto;
create schema if not exists private;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'participant' check (role in ('participant', 'reviewer', 'admin')),
  created_at timestamptz not null default now()
);

create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 70),
  college text not null check (char_length(college) between 1 and 120),
  team_lead_user_id uuid not null references auth.users(id) on delete restrict,
  registration_status text not null default 'pending_payment'
    check (registration_status in ('pending_payment', 'registration_complete', 'submission_received', 'under_review', 'shortlisted', 'not_shortlisted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.team_members (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams(id) on delete cascade,
  full_name text not null check (char_length(full_name) between 1 and 140),
  email text not null check (char_length(email) <= 254),
  student_id text not null check (char_length(student_id) <= 140),
  is_team_lead boolean not null default false,
  user_id uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (team_id, email)
);
create unique index if not exists team_members_email_lower_unique on public.team_members (lower(email));
create index if not exists team_members_team_id_idx on public.team_members (team_id);
create index if not exists teams_lead_created_idx on public.teams (team_lead_user_id, created_at desc);

create table if not exists public.submissions (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null unique references public.teams(id) on delete cascade,
  storage_path text not null,
  original_filename text not null,
  content_type text not null check (content_type in ('application/pdf', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation')),
  size_bytes bigint not null check (size_bytes > 0 and size_bytes <= 10485760),
  submitted_at timestamptz not null default now()
);

create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams(id) on delete cascade,
  member_id uuid references public.team_members(id) on delete cascade,
  stage text not null check (stage in ('registration', 'shortlisted')),
  amount_inr integer not null check (amount_inr in (150, 350)),
  status text not null default 'pending' check (status in ('pending', 'submitted', 'verified', 'rejected')),
  payment_reference text,
  reviewer_note text not null default '',
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  check ((stage = 'registration' and member_id is null and amount_inr = 150) or (stage = 'shortlisted' and member_id is not null and amount_inr = 350))
);
create unique index if not exists payments_team_registration_unique on public.payments (team_id) where stage = 'registration';
create unique index if not exists payments_team_member_shortlist_unique on public.payments (team_id, member_id) where stage = 'shortlisted';
create index if not exists payments_team_stage_idx on public.payments (team_id, stage, status);

create table if not exists public.team_reviews (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams(id) on delete cascade,
  reviewer_id uuid not null references auth.users(id) on delete restrict,
  math_rigor smallint not null check (math_rigor between 0 and 20),
  originality smallint not null check (originality between 0 and 20),
  impact smallint not null check (impact between 0 and 20),
  feasibility smallint not null check (feasibility between 0 and 20),
  presentation smallint not null check (presentation between 0 and 20),
  total_score smallint not null check (total_score between 0 and 100),
  notes text not null default '' check (char_length(notes) <= 5000),
  updated_at timestamptz not null default now(),
  unique (team_id, reviewer_id)
);
create index if not exists team_reviews_team_score_idx on public.team_reviews (team_id, total_score desc);

create table if not exists public.shortlist_decisions (
  team_id uuid primary key references public.teams(id) on delete cascade,
  selected boolean not null,
  score numeric(6,2),
  reviewer_notes text not null default '',
  decided_by uuid references auth.users(id) on delete set null,
  decided_at timestamptz not null default now()
);

-- Roles are provisioned by an operator; users never receive write access to profiles.
alter table public.profiles enable row level security;
alter table public.teams enable row level security;
alter table public.team_members enable row level security;
alter table public.submissions enable row level security;
alter table public.payments enable row level security;
alter table public.team_reviews enable row level security;
alter table public.shortlist_decisions enable row level security;
revoke all on public.profiles, public.teams, public.team_members, public.submissions, public.payments, public.team_reviews, public.shortlist_decisions from anon, authenticated;
grant all on public.profiles, public.teams, public.team_members, public.submissions, public.payments, public.team_reviews, public.shortlist_decisions to service_role;

-- Create the participant profile on verified Auth account creation.
create or replace function private.create_qyron_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, role) values (new.id, 'participant') on conflict (id) do nothing;
  return new;
end;
$$;
revoke all on function private.create_qyron_profile() from public, anon, authenticated;
drop trigger if exists qyron_profile_after_signup on auth.users;
create trigger qyron_profile_after_signup after insert on auth.users
for each row execute function private.create_qyron_profile();

-- Atomic full-team registration. Only the backend's service_role can invoke it.
create or replace function public.register_complete_team(
  p_name text, p_college text, p_team_lead_user_id uuid, p_members jsonb
) returns uuid
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  v_team_id uuid;
  v_member jsonb;
  v_count integer;
begin
  v_count := jsonb_array_length(p_members);
  if v_count < 4 or v_count > 6 then raise exception 'team size must be 4 to 6'; end if;
  if now() > timestamptz '2027-01-20 23:59:59+05:30' then raise exception 'registration is closed'; end if;
  if (select count(distinct lower(item.member->>'email')) from jsonb_array_elements(p_members) as item(member)) <> v_count then
    raise exception 'duplicate member email';
  end if;
  if lower(p_members->0->>'email') <> lower((select email from auth.users where id = p_team_lead_user_id)) then
    raise exception 'team lead email does not match authenticated account';
  end if;
  insert into public.teams (name, college, team_lead_user_id) values (trim(p_name), trim(p_college), p_team_lead_user_id) returning id into v_team_id;
  for v_member in select item.member from jsonb_array_elements(p_members) as item(member) loop
    insert into public.team_members (team_id, full_name, email, student_id, is_team_lead)
    values (v_team_id, trim(v_member->>'full_name'), lower(trim(v_member->>'email')), trim(v_member->>'student_id'), lower(trim(v_member->>'email')) = lower(p_members->0->>'email'));
  end loop;
  insert into public.payments (team_id, stage, amount_inr, status) values (v_team_id, 'registration', 150, 'pending');
  return v_team_id;
end;
$$;
revoke all on function public.register_complete_team(text, text, uuid, jsonb) from public, anon, authenticated;
grant execute on function public.register_complete_team(text, text, uuid, jsonb) to service_role;

-- Serialize shortlist changes so two concurrent admins cannot exceed 30 teams.
create or replace function public.set_team_shortlist(p_team_id uuid, p_selected boolean, p_decided_by uuid)
returns integer
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  v_selected_count integer;
  v_was_selected boolean;
begin
  perform pg_advisory_xact_lock(27127, 30);
  if not exists (select 1 from public.teams where id = p_team_id) then raise exception 'team not found'; end if;
  select coalesce((select selected from public.shortlist_decisions where team_id = p_team_id), false) into v_was_selected;
  select count(*) into v_selected_count from public.shortlist_decisions where selected;
  if p_selected and not v_was_selected and v_selected_count >= 30 then raise exception 'shortlist limit reached'; end if;
  insert into public.shortlist_decisions (team_id, selected, score, decided_by)
  values (p_team_id, p_selected, (select avg(total_score)::numeric(6,2) from public.team_reviews where team_id = p_team_id), p_decided_by)
  on conflict (team_id) do update set selected = excluded.selected, score = excluded.score, decided_by = excluded.decided_by, decided_at = now();
  update public.teams set registration_status = case when p_selected then 'shortlisted' else 'not_shortlisted' end, updated_at = now() where id = p_team_id;
  if p_selected then
    if not exists (select 1 from public.submissions where team_id = p_team_id) then raise exception 'proposal submission is required'; end if;
    if not exists (select 1 from public.payments where team_id = p_team_id and stage = 'registration' and status = 'verified') then raise exception 'verified registration payment is required'; end if;
    insert into public.payments (team_id, member_id, stage, amount_inr, status)
    select p_team_id, id, 'shortlisted', 350, 'pending' from public.team_members where team_id = p_team_id
    on conflict (team_id, member_id) where stage = 'shortlisted' do nothing;
  end if;
  select count(*) into v_selected_count from public.shortlist_decisions where selected;
  return v_selected_count;
end;
$$;
revoke all on function public.set_team_shortlist(uuid, boolean, uuid) from public, anon, authenticated;
grant execute on function public.set_team_shortlist(uuid, boolean, uuid) to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('qyron-submissions', 'qyron-submissions', false, 10485760,
        array['application/pdf', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'])
on conflict (id) do update set public = false, file_size_limit = 10485760;

-- Antothon-style Public Registration Wizard Table
create table if not exists public.registrations (
  team_code text primary key,
  team_name text not null,
  college_name text not null,
  track text not null,
  idea_title text not null,
  idea_summary text not null,
  idea_description text not null,
  idea_ppt_filename text,
  idea_ppt_path text,
  leader_name text not null,
  leader_email text not null,
  leader_phone text not null,
  leader_college text,
  leader_department text,
  leader_year text,
  leader_gender text,
  member_count integer not null default 4,
  members_data text,
  amount_paid integer not null default 150,
  payment_status text not null default 'pending',
  razorpay_order_id text,
  razorpay_payment_id text,
  payment_timestamp timestamptz,
  status text not null default 'submitted',
  created_at timestamptz not null default now()
);

-- Allow app service to insert and read registrations reliably
alter table public.registrations disable row level security;
grant all on public.registrations to anon, authenticated, service_role;

