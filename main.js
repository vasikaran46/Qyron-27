const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const backdrop = $('#modalBackdrop');
const modalContent = $('#modalContent');
const toast = $('#toast');
let toastTimer;
let activeDialog = null;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

function openModal(type) {
  activeDialog = type;
  backdrop.hidden = false;
  document.body.style.overflow = 'hidden';
  if (type === 'register') renderRegistration();
  else renderPortal(type === 'admin' ? 'admin' : 'participant');
  $('.portal-modal').scrollTop = 0;
  $('#modalClose').focus();
}

function closeModal() {
  backdrop.hidden = true;
  document.body.style.overflow = '';
  activeDialog = null;
}

function renderRegistration() {
  modalContent.innerHTML = `
    <h2 id="modalTitle">ASSEMBLE YOUR <span>TEAM.</span></h2>
    <p class="modal-subtitle">Register all 2–4 members together. The ₹150 team fee is due during the first-round registration.</p>
    <form id="registrationForm">
      <div class="form-grid">
        <div class="field"><label for="teamName">TEAM NAME</label><input id="teamName" name="teamName" required maxlength="70" placeholder="e.g. Theorem Keepers" /></div>
        <div class="field"><label for="college">COLLEGE / INSTITUTION</label><input id="college" name="college" required maxlength="120" placeholder="Your institution" /><small style="color:var(--toxic-lime);font-size:10px;display:block;margin-top:4px;">※ Inter-college participation is NOT allowed. All members must be from the same college.</small></div>
        <div class="field full"><label for="challengeTrack">CHALLENGE TRACK</label><select id="challengeTrack" name="track"><option value="">Challenge tracks to be announced</option></select></div>
      </div>
      <div class="member-fields"><h3>TEAM ROSTER <span id="memberCount">2 MEMBERS</span></h3><div id="memberRows"></div><button type="button" class="roster-add" id="addMember">＋ ADD MEMBER</button><p class="member-help">The first member is the team lead and registration contact.</p></div>
      <div class="upload-box">FIRST ROUND FEE · ₹150 PER TEAM <em>Payment method will be shared by the organizers. Registration deadline: Jan 20, 2027 · 11:59 PM IST.</em></div>
      <button class="button button-primary form-submit" type="submit">CONTINUE TO REGISTRATION <span>↗</span></button>
      <p class="form-notice" id="formNotice" aria-live="polite">Sign in with the first roster member’s email before submitting the complete team.</p>
      <button class="auth-switch" type="button" id="teamAccount">SIGN IN OR CREATE A PARTICIPANT ACCOUNT</button>
    </form>`;
  const rows = $('#memberRows');
  let count = 2;
  function drawRows() {
    rows.innerHTML = Array.from({length: count}, (_, index) => `<div class="member-row"><input aria-label="Member ${index + 1} full name" required maxlength="100" placeholder="${index === 0 ? 'Team lead name' : `Member ${index + 1} name`}" /><input aria-label="Member ${index + 1} email" required type="email" maxlength="254" placeholder="Email address" /><input aria-label="Member ${index + 1} student ID" required maxlength="80" placeholder="Student ID / roll no." /></div>`).join('');
    $('#memberCount').textContent = `${count} MEMBER${count === 1 ? '' : 'S'}`;
    $('#addMember').disabled = count >= 4;
    $('#addMember').textContent = count >= 4 ? 'MAXIMUM TEAM SIZE REACHED (4)' : '＋ ADD MEMBER';
    $$('.member-remove', rows).forEach(button => button.addEventListener('click', () => { if (count > 2) { count--; drawRows(); } }));
  }
  drawRows();
  $('#teamAccount').addEventListener('click', () => { closeModal(); openModal('portal'); });
  $('#addMember').addEventListener('click', () => { if (count < 4) { count++; drawRows(); } });
  $('#registrationForm').addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const emails = $$('#memberRows input[ type="email" ]').map(input => input.value.trim().toLowerCase());
    if (new Set(emails).size !== emails.length) {
      $('#formNotice').textContent = 'Each team member must use a different email address.';
      return;
    }
    const roster = $$('#memberRows .member-row').map(row => {
      const inputs = $$('input', row);
      return { full_name: inputs[0].value.trim(), email: inputs[1].value.trim(), student_id: inputs[2].value.trim() };
    });
    $('#formNotice').textContent = 'Submitting complete roster…';
    apiRequest('/api/participant/teams', { method: 'POST', body: JSON.stringify({ name: $('#teamName').value.trim(), college: $('#college').value.trim(), members: roster }) })
      .then(() => { showToast('Team registered · ₹150 team payment pending'); return apiRequest('/api/participant/dashboard'); })
      .then(data => renderParticipantDashboard(data))
      .catch(error => { $('#formNotice').textContent = error.message; });
  });
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options, headers: options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'The request could not be completed.');
  return data;
}

const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);

function renderPortal(kind = 'participant') {
  $('.portal-modal')?.classList.remove('portal-modal-wide');
  const isAdmin = kind === 'admin';
  modalContent.innerHTML = `<h2 id="modalTitle">${isAdmin ? 'ADMIN' : 'PARTICIPANT'} <span>PORTAL.</span></h2><p class="modal-subtitle">${isAdmin ? 'Review submissions, score teams, verify fees, and manage the 20-team shortlist.' : 'See your team roster, payments, submission receipt, and shortlist status.'}</p><div class="portal-tabs"><button class="${!isAdmin ? 'active' : ''}" data-kind="participant">PARTICIPANT</button><button class="${isAdmin ? 'active' : ''}" data-kind="admin">ADMIN</button></div><form class="login-form" id="portalForm"><div class="field"><label for="portalEmail">${isAdmin ? 'ADMIN EMAIL' : 'TEAM LEAD EMAIL'}</label><input id="portalEmail" type="email" required autocomplete="email" placeholder="name@college.edu" /></div><div class="field"><label for="portalPassword">PASSWORD</label><input id="portalPassword" type="password" required autocomplete="current-password" minlength="8" placeholder="At least 8 characters" /></div><button class="button button-primary form-submit" type="submit">SIGN IN <span>↗</span></button><button type="button" class="auth-switch" id="createAccount">Create a participant account</button><p class="form-notice" id="portalNotice">Your account and team records are private to you. Admin access is assigned by the organizers.</p></form><div class="preview-actions"><span>EXPLORE THE INTERFACE</span><button class="preview-button" id="previewParticipant">Preview participant dashboard</button><button class="preview-button" id="previewAdmin">Preview admin review board</button><small>Sample data only. Preview actions are not saved.</small></div>`;
  $$('.portal-tabs button').forEach(button => button.addEventListener('click', () => renderPortal(button.dataset.kind)));
  $('#createAccount').addEventListener('click', () => renderSignup());
  $('#portalForm').addEventListener('submit', async event => {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    $('#portalNotice').textContent = 'Signing in…';
    try {
      await apiRequest('/api/auth/login', { method: 'POST', body: JSON.stringify({ email: $('#portalEmail').value, password: $('#portalPassword').value }) });
      const user = await apiRequest('/api/auth/me');
      userCanShortlist = user.role === 'admin';
      if (user.role === 'admin' || user.role === 'reviewer') await loadAdminDashboard();
      else await loadParticipantDashboard();
    } catch (error) { $('#portalNotice').textContent = error.message; }
  });
  $('#previewParticipant').addEventListener('click', () => renderParticipantDashboard(sampleParticipantData(), true));
  $('#previewAdmin').addEventListener('click', () => renderAdminDashboard(sampleAdminData(), true));
}

function renderSignup() {
  modalContent.innerHTML = `<h2 id="modalTitle">CREATE YOUR <span>ACCOUNT.</span></h2><p class="modal-subtitle">Use the team lead's email address. A verification link will be sent to your email.</p><form class="login-form" id="signupForm"><div class="field"><label for="signupEmail">TEAM LEAD EMAIL</label><input id="signupEmail" type="email" required autocomplete="email" /></div><div class="field"><label for="signupPassword">PASSWORD</label><input id="signupPassword" type="password" required minlength="8" maxlength="128" autocomplete="new-password" /></div><button class="button button-primary form-submit" type="submit">CREATE PARTICIPANT ACCOUNT <span>↗</span></button><p class="form-notice" id="signupNotice" aria-live="polite">An account is required before the team lead can register the full roster.</p><button type="button" class="auth-switch" id="backToSignin">Back to sign in</button><button type="button" class="auth-switch" id="resendVerificationBtn" style="margin-top: 8px;">Didn't get the email? Resend verification</button></form>`;
  $('#backToSignin').addEventListener('click', () => renderPortal());
  $('#resendVerificationBtn').addEventListener('click', async () => {
    const email = $('#signupEmail').value.trim();
    if (!email) {
      $('#signupNotice').textContent = 'Please enter your team lead email above first.';
      return;
    }
    $('#signupNotice').textContent = 'Sending new verification link…';
    try {
      const data = await apiRequest('/api/auth/resend-verification', { method: 'POST', body: JSON.stringify({ email }) });
      $('#signupNotice').textContent = data.message;
    } catch (error) {
      $('#signupNotice').textContent = error.message;
    }
  });
  $('#signupForm').addEventListener('submit', async event => {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    $('#signupNotice').textContent = 'Creating account and sending verification email…';
    try {
      const data = await apiRequest('/api/auth/signup', { method: 'POST', body: JSON.stringify({ email: $('#signupEmail').value, password: $('#signupPassword').value }) });
      $('#signupNotice').textContent = data.message;
    } catch (error) { $('#signupNotice').textContent = error.message; }
  });
}

function sampleParticipantData() {
  return { team: { id: 'preview-01', name: 'Theorem Keepers', college: 'QYRON Demo College', registration_status: 'shortlisted' }, members: [{ full_name: 'A. Example', email: 'lead@example.edu', student_id: 'DEMO-01', is_team_lead: true }, { full_name: 'B. Example', email: 'member2@example.edu', student_id: 'DEMO-02' }, { full_name: 'C. Example', email: 'member3@example.edu', student_id: 'DEMO-03' }, { full_name: 'D. Example', email: 'member4@example.edu', student_id: 'DEMO-04' }], payments: [{ stage: 'registration', amount_inr: 150, status: 'verified' }, { stage: 'shortlisted', amount_inr: 350, status: 'pending', member_name: 'A. Example', member_email: 'lead@example.edu' }], submission: { original_filename: 'theorem-keepers-proposal.pdf', size_bytes: 1834000, submitted_at: '2027-01-24T14:30:00+05:30' }, shortlist: { selected: true } };
}

async function loadParticipantDashboard() {
  try { renderParticipantDashboard(await apiRequest('/api/participant/dashboard')); }
  catch (error) { renderPortal(); showToast(error.message); }
}

function renderParticipantDashboard(data, preview = false) {
  $('.portal-modal')?.classList.remove('portal-modal-wide');
  const team = data.team;
  if (!team) {
    modalContent.innerHTML = `<div class="portal-topline"><span>${preview ? 'SAMPLE PREVIEW · NOT SAVED' : 'PARTICIPANT DASHBOARD'}</span><button data-signout>Sign out</button></div><h2 id="modalTitle">YOUR TEAM <span>IS NEXT.</span></h2><p class="modal-subtitle">No registered team is linked to this account yet. Team registration must include the complete 2–4 member roster in one submission.</p><button class="button button-primary" id="dashboardRegister">REGISTER THE FULL TEAM <span>↗</span></button>`;
    $('#dashboardRegister').addEventListener('click', () => { closeModal(); openModal('register'); });
    bindSignOut();
    return;
  }
  const regPayment = (data.payments || []).find(item => item.stage === 'registration');
  const memberPayments = (data.payments || []).filter(item => item.stage === 'shortlisted');
  const status = data.shortlist?.selected === true ? 'SHORTLISTED' : data.shortlist?.selected === false ? 'NOT SHORTLISTED' : 'UNDER REVIEW';
  modalContent.innerHTML = `<div class="portal-topline"><span>${preview ? 'SAMPLE PREVIEW · ACTIONS NOT SAVED' : 'PARTICIPANT DASHBOARD'}</span><button data-signout>${preview ? 'Close preview' : 'Sign out'}</button></div><h2 id="modalTitle">${escapeHTML(team.name)} <span>// TEAM DASHBOARD</span></h2><p class="modal-subtitle">${escapeHTML(team.college)} · ${data.members?.length || 0} registered members</p><div class="dashboard-summary"><div><small>REGISTRATION FEE</small><b>${escapeHTML(regPayment?.status || 'pending').toUpperCase()}</b></div><div><small>PROPOSAL</small><b>${data.submission ? 'RECEIVED' : 'NOT UPLOADED'}</b></div><div><small>SHORTLIST</small><b>${status}</b></div><div><small>FINAL ROUND FEES</small><b>${memberPayments.length ? memberPayments.filter(item => item.status === 'verified').length + '/' + memberPayments.length + ' PAID' : 'IF SHORTLISTED'}</b></div></div><div class="dashboard-columns"><section class="dashboard-card"><div class="dashboard-card-title"><span>TEAM ROSTER</span><b>${data.members?.length || 0} / 6</b></div><ul class="roster-list">${(data.members || []).map(member => `<li><span class="roster-avatar">${escapeHTML(member.full_name?.slice(0,1)?.toUpperCase())}</span><span><strong>${escapeHTML(member.full_name)} ${member.is_team_lead ? '<i>LEAD</i>' : ''}</strong><small>${escapeHTML(member.email)} · ${escapeHTML(member.student_id)}</small></span></li>`).join('')}</ul></section><section class="dashboard-card"><div class="dashboard-card-title"><span>SUBMISSION RECEIPT</span><b>${data.submission ? 'RECEIVED' : 'PENDING'}</b></div>${data.submission ? `<p class="receipt-file">▤ ${escapeHTML(data.submission.original_filename)}</p><p class="receipt-detail">${(data.submission.size_bytes / 1048576).toFixed(2)} MB · ${new Date(data.submission.submitted_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST</p>` : '<p class="receipt-detail">PPT, PPTX, or PDF · 10 MB maximum</p>'}<form id="submissionUpload" class="upload-form"><label for="proposalFile">${data.submission ? 'REPLACE PROPOSAL' : 'UPLOAD PROPOSAL'}</label><input id="proposalFile" type="file" accept=".ppt,.pptx,.pdf,application/pdf,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation" required ${preview ? 'disabled' : ''}/><button class="button button-outline" type="submit" ${preview ? 'disabled' : ''}>${data.submission ? 'REPLACE FILE' : 'UPLOAD FILE'} ↗</button><p id="uploadNotice" class="form-notice" aria-live="polite">Deadline: Jan 25, 2027 · 11:59 PM IST · max 10 MB</p></form></section></div><section class="dashboard-card payment-ledger"><div class="dashboard-card-title"><span>PAYMENT TRACKER</span><b>₹150 / TEAM · ₹350 / MEMBER IF SHORTLISTED</b></div>${renderPaymentRows(data.payments || [], data, preview) || '<p class="receipt-detail">Payment status will appear here after registration.</p>'}</section>`;
  bindSignOut(preview);
  $('#submissionUpload')?.addEventListener('submit', async event => {
    event.preventDefault();
    const file = $('#proposalFile').files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { $('#uploadNotice').textContent = 'File is larger than the 10 MB limit.'; return; }
    if (preview) { $('#uploadNotice').textContent = 'Sample preview only. No file was uploaded.'; return; }
    const form = new FormData(); form.append('file', file);
    $('#uploadNotice').textContent = 'Uploading securely…';
    try { await apiRequest(`/api/participant/teams/${encodeURIComponent(team.id)}/submission`, { method: 'POST', body: form }); showToast('Proposal uploaded successfully'); await loadParticipantDashboard(); }
    catch (error) { $('#uploadNotice').textContent = error.message; }
  });
  $$('.payment-reference-form').forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault();
    if (preview) { $('#paymentNotice')?.replaceChildren(document.createTextNode('Preview only. No payment reference was submitted.')); return; }
    const input = $('input[name="payment_reference"]', form);
    try {
      await apiRequest(`/api/participant/teams/${encodeURIComponent(team.id)}/payments/${encodeURIComponent(form.dataset.payment)}/reference`, { method: 'POST', body: JSON.stringify({ payment_reference: input.value.trim() }) });
      showToast('Payment reference sent for review'); await loadParticipantDashboard();
    } catch (error) { const notice = $('.payment-reference-notice', form); if (notice) notice.textContent = error.message; }
  }));
}

function renderPaymentRows(payments, data, preview) {
  return payments.map(payment => {
    const canSubmit = !preview && (payment.stage === 'registration' ? data.is_team_lead : payment.member_email?.toLowerCase() === data.viewer_email?.toLowerCase());
    const needsReference = canSubmit && ['pending', 'rejected'].includes(payment.status);
    const owner = payment.stage === 'registration' ? 'FIRST ROUND · TEAM' : `FINAL ROUND · ${escapeHTML(payment.member_name || 'MEMBER')}`;
    return `<div class="payment-entry"><div class="payment-row"><span>${owner}</span><b>₹${payment.amount_inr}</b><em class="status-chip status-${escapeHTML(payment.status)}">${escapeHTML(payment.status).toUpperCase()}</em></div>${needsReference ? `<form class="payment-reference-form" data-payment="${escapeHTML(payment.id)}"><label>PAYMENT REFERENCE<input name="payment_reference" minlength="3" maxlength="200" required value="${escapeHTML(payment.payment_reference||'')}" placeholder="Transaction / UTR reference"></label><button class="payment-submit" type="submit">SEND FOR VERIFICATION</button><small class="payment-reference-notice">The organizer will verify this payment.</small></form>` : ''}</div>`;
  }).join('');
}

function sampleAdminData() {
  return { shortlist_limit: 20, shortlisted_count: 19, teams: [
    { id: 'demo-a', name: 'Theorem Keepers', college: 'QYRON Demo College', registration_status: 'under_review', members: [{ full_name: 'A. Example', email: 'lead@example.edu', is_team_lead: true }, { full_name: 'B. Example', email: 'member@example.edu' }], submission: { original_filename: 'proposal-a.pdf', size_bytes: 1834000 }, shortlist: null, payments: [{ id: 'pay-a', stage: 'registration', amount_inr: 150, status: 'submitted', payment_reference: 'DEMO-150-A' }], reviews: [] },
    { id: 'demo-b', name: 'Vector Vanguard', college: 'North Demo Institute', registration_status: 'shortlisted', members: [{ full_name: 'C. Example', email: 'lead2@example.edu', is_team_lead: true }, { full_name: 'D. Example', email: 'member2@example.edu' }, { full_name: 'E. Example', email: 'member3@example.edu' }, { full_name: 'F. Example', email: 'member4@example.edu' }], submission: { original_filename: 'vector-vanguard.pptx', size_bytes: 2534000 }, shortlist: { selected: true, score: 82 }, payments: [{ id: 'pay-b', stage: 'registration', amount_inr: 150, status: 'verified' }, { id: 'pay-b2', stage: 'shortlisted', amount_inr: 350, status: 'pending' }], reviews: [{ reviewer_id: 'demo', total_score: 82, notes: 'Clear mathematical model; strong feasibility.' }] },
    { id: 'demo-c', name: 'Golden Ratio', college: 'West Demo University', registration_status: 'submitted', members: [{ full_name: 'G. Example', email: 'lead3@example.edu', is_team_lead: true }, { full_name: 'H. Example', email: 'member4@example.edu' }, { full_name: 'I. Example', email: 'member5@example.edu' }, { full_name: 'J. Example', email: 'member6@example.edu' }], submission: null, shortlist: null, payments: [{ id: 'pay-c', stage: 'registration', amount_inr: 150, status: 'pending' }], reviews: [] },
  ] };
}

async function loadAdminDashboard() {
  try { renderAdminDashboard(await apiRequest('/api/admin/dashboard')); }
  catch (error) { renderPortal('admin'); showToast(error.message); }
}

function renderAdminDashboard(data, preview = false) {
  $('.portal-modal')?.classList.add('portal-modal-wide');
  if (preview) userCanShortlist = true;
  const state = data;
  const counts = { shortlisted: state.shortlisted_count ?? state.teams.filter(team => team.shortlist?.selected).length, total: state.teams.length, submissions: state.teams.filter(team => team.submission).length, pending: state.teams.reduce((sum, team) => sum + team.payments.filter(payment => ['submitted', 'pending'].includes(payment.status)).length, 0) };
  modalContent.innerHTML = `<div class="portal-topline"><span>${preview ? 'SAMPLE PREVIEW · ACTIONS NOT SAVED' : 'ORGANIZER REVIEW CONSOLE'}</span><button data-signout>${preview ? 'Close preview' : 'Sign out'}</button></div><h2 id="modalTitle">REVIEW <span>DIRECTORATE.</span></h2><p class="modal-subtitle">Score proposals, record reviewer notes, verify payment references, and publish no more than 20 shortlisted teams.</p><div class="admin-stats"><div><small>TEAMS</small><b>${counts.total}</b></div><div><small>SUBMISSIONS</small><b>${counts.submissions}</b></div><div><small>PAYMENTS TO REVIEW</small><b>${counts.pending}</b></div><div><small>SHORTLIST</small><b>${counts.shortlisted}<span> / 20</span></b></div></div><div class="shortlist-meter"><div style="width:${Math.min(100, counts.shortlisted / 20 * 100)}%"></div></div><div class="admin-toolbar"><label>FILTER <select id="teamFilter"><option value="all">All teams</option><option value="unreviewed">Needs review</option><option value="submitted">Has proposal</option><option value="shortlisted">Shortlisted</option></select></label><span>RUBRIC: SIX CRITERIA (100% TOTAL)</span></div><div class="admin-team-list">${state.teams.map(team => renderAdminTeam(team, state, preview)).join('')}</div>`;
  bindSignOut(preview);
  $('#teamFilter').addEventListener('change', event => $$('.admin-team-card').forEach(card => card.hidden = !matchesFilter(card, event.target.value)));
  $$('.team-review-form').forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault(); const tid = form.dataset.team; const payload = Object.fromEntries(new FormData(form).entries());
    for (const key of ['problem_understanding','quantum_implementation','originality','technical_execution','impact_scalability','presentation']) payload[key] = Number(payload[key] || 0);
    if (preview) { const team = state.teams.find(item => item.id === tid); team.reviews = [{ reviewer_id: 'preview', total_score: Object.values(payload).filter(value => typeof value === 'number').reduce((a,b)=>a+b,0), notes: payload.notes }]; showToast('Sample review updated in preview only'); renderAdminDashboard(state, true); return; }
    try { await apiRequest(`/api/admin/teams/${encodeURIComponent(tid)}/review`, { method: 'PUT', body: JSON.stringify(payload) }); showToast('Review saved'); await loadAdminDashboard(); } catch (error) { showToast(error.message); }
  }));
  $$('[data-shortlist]').forEach(button => button.addEventListener('click', async () => {
    const team = state.teams.find(item => item.id === button.dataset.shortlist);
    const currentlySelected = Boolean(team.shortlist?.selected);
    if (!currentlySelected && counts.shortlisted >= 20) { showToast('Shortlist is full — maximum 20 teams'); return; }
    if (preview) { team.shortlist = { selected: !currentlySelected, score: team.reviews?.[0]?.total_score || null }; state.shortlisted_count = state.teams.filter(item => item.shortlist?.selected).length + Math.max(0, counts.shortlisted - state.teams.filter(item => item.shortlist?.selected).length); renderAdminDashboard(state, true); return; }
    try { await apiRequest(`/api/admin/teams/${encodeURIComponent(team.id)}/shortlist`, { method: 'PUT', body: JSON.stringify({ selected: !currentlySelected }) }); showToast(!currentlySelected ? 'Team added to shortlist' : 'Team removed from shortlist'); await loadAdminDashboard(); }
    catch (error) { showToast(error.message); }
  }));
  $$('[data-payment]').forEach(button => button.addEventListener('click', async () => {
    if (preview) { const payment = state.teams.flatMap(team => team.payments).find(item => item.id === button.dataset.payment); payment.status = button.dataset.status; payment.reviewer_note = 'Updated in sample preview'; renderAdminDashboard(state, true); return; }
    const note = prompt('Optional payment review note:') || '';
    try { await apiRequest(`/api/admin/payments/${encodeURIComponent(button.dataset.payment)}`, { method: 'PATCH', body: JSON.stringify({ status: button.dataset.status, note }) }); showToast(`Payment ${button.dataset.status}`); await loadAdminDashboard(); }
    catch (error) { showToast(error.message); }
  }));
  $$('[data-submission-team]').forEach(button => button.addEventListener('click', async () => {
    if (preview) return;
    try {
      const data = await apiRequest(`/api/admin/teams/${encodeURIComponent(button.dataset.submissionTeam)}/submission-link`);
      window.open(data.url, '_blank', 'noopener,noreferrer');
    } catch (error) { showToast(error.message); }
  }));
}

function renderAdminTeam(team, state, preview) {
  const selected = Boolean(team.shortlist?.selected);
  const limitHit = (state.shortlisted_count ?? state.teams.filter(item => item.shortlist?.selected).length) >= 20;
  const review = team.reviews?.[0] || {};
  const submitted = Boolean(team.submission);
  return `<article class="admin-team-card" data-review-state="${team.reviews?.length ? 'reviewed' : 'unreviewed'}" data-has-submission="${submitted}" data-shortlisted="${selected}"><div class="admin-team-head"><div><span class="team-id">${escapeHTML(team.id.slice(0,8))} // ${escapeHTML(team.college)}</span><h3>${escapeHTML(team.name)}</h3><small>${team.members.length} members · ${submitted ? escapeHTML(team.submission.original_filename) : 'No proposal uploaded'}</small>${submitted&&!preview?`<button class="file-review-link" type="button" data-submission-team="${escapeHTML(team.id)}">OPEN PRIVATE PROPOSAL ↗</button>`:''}</div><span class="status-chip ${selected ? 'status-verified' : ''}">${selected ? 'SHORTLISTED' : escapeHTML(team.registration_status).replace('_',' ').toUpperCase()}</span></div><details class="admin-roster"><summary>VIEW ROSTER + REVIEW HISTORY <span>${team.reviews?.length || 0} REVIEWS</span></summary><ul>${team.members.map(member=>`<li>${escapeHTML(member.full_name)}${member.is_team_lead?' · LEAD':''} <small>${escapeHTML(member.email)}</small></li>`).join('')}</ul>${(team.reviews||[]).map(item=>`<p class="review-history"><b>${item.total_score ?? '—'} / 100</b> · ${escapeHTML(item.notes||'No notes')}</p>`).join('')}</details><form class="team-review-form" data-team="${escapeHTML(team.id)}"><div class="score-grid">${[['problem_understanding','PROBLEM (15%)',15],['quantum_implementation','QUANTUM (25%)',25],['originality','INNOVATION (20%)',20],['technical_execution','PROTOTYPE (20%)',20],['impact_scalability','IMPACT (10%)',10],['presentation','DEMO (10%)',10]].map(([key,label,max])=>`<label>${label}<input name="${key}" type="number" min="0" max="${max}" value="${Number(review[key]||0)}" required></label>`).join('')}</div><label class="review-notes-label">REVIEWER NOTES<textarea name="notes" rows="2" maxlength="5000" placeholder="Strengths, concerns, and feedback…">${escapeHTML(review.notes||'')}</textarea></label><div class="admin-actions"><button class="button button-outline" type="submit">SAVE REVIEW</button>${userCanShortlist ? `<button class="shortlist-toggle ${selected?'is-selected':''}" type="button" data-shortlist="${escapeHTML(team.id)}" ${!selected&&limitHit?'disabled':''}>${selected?'REMOVE FROM SHORTLIST':'SHORTLIST TEAM'} ${selected?'✓':'+'}</button>`:''}</div></form><div class="admin-payments">${team.payments.map(payment=>`<div><span>${payment.stage==='registration'?'TEAM FEE':'SHORTLISTED MEMBER FEE'} · ₹${payment.amount_inr} · ${escapeHTML(payment.status).toUpperCase()}${payment.payment_reference?` · REF ${escapeHTML(payment.payment_reference)}`:''}</span>${['pending','submitted'].includes(payment.status)&&userCanShortlist?`<button data-payment="${escapeHTML(payment.id)}" data-status="verified">VERIFY</button><button data-payment="${escapeHTML(payment.id)}" data-status="rejected">REJECT</button>`:''}</div>`).join('')}</div></article>`;
}

function matchesFilter(card, filter) {
  if (filter === 'unreviewed') return card.dataset.reviewState === 'unreviewed';
  if (filter === 'submitted') return card.dataset.hasSubmission === 'true';
  if (filter === 'shortlisted') return card.dataset.shortlisted === 'true';
  return true;
}

let userCanShortlist = false;
function bindSignOut(preview = false) {
  $('[data-signout]')?.addEventListener('click', async () => {
    if (preview) { renderPortal(); return; }
    try { await apiRequest('/api/auth/logout', { method: 'POST', body: '{}' }); } finally { renderPortal(); }
  });
  if (!preview) apiRequest('/api/auth/me').then(user => { userCanShortlist = user.role === 'admin'; }).catch(() => { userCanShortlist = false; });
  else userCanShortlist = true;
}

$$('[data-open]').forEach(button => button.addEventListener('click', () => openModal(button.dataset.open)));
$('#modalClose').addEventListener('click', closeModal);
backdrop.addEventListener('click', event => { if (event.target === backdrop) closeModal(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !backdrop.hidden) closeModal(); });

$('#menuToggle').addEventListener('click', () => $('#mainNav').classList.toggle('open'));
$$('#mainNav a').forEach(link => link.addEventListener('click', () => $('#mainNav').classList.remove('open')));

// FAQ Accordion
$$('.faq-trigger').forEach(trigger => {
  trigger.addEventListener('click', () => {
    const item = trigger.closest('.faq-item');
    const isActive = item.classList.contains('active');
    $$('.faq-item').forEach(el => el.classList.remove('active'));
    if (!isActive) item.classList.add('active');
  });
});

const deadline = new Date('2027-01-20T23:59:59+05:30').getTime();
function updateCountdown() {
  const difference = deadline - Date.now();
  const items = $$('#countdown b');
  if (!items.length) return;
  const values = difference <= 0 ? ['00', '00', '00', '00'] : [Math.floor(difference / 86400000), Math.floor(difference / 3600000) % 24, Math.floor(difference / 60000) % 60, Math.floor(difference / 1000) % 60].map(value => String(value).padStart(2, '0'));
  items.forEach((item, index) => item.textContent = values[index]);
}
updateCountdown();
setInterval(updateCountdown, 1000);

const loadingScreen = $('#loadingScreen');
if (loadingScreen) {
  window.setTimeout(() => loadingScreen.classList.add('is-gone'), 820);
  window.setTimeout(() => loadingScreen.remove(), 1550);
}

const motionReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const revealTargets = $$('.stats-strip, .content-section, .final-cta');
if ('IntersectionObserver' in window && !motionReduced) {
  const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealTargets.forEach(target => {
    target.classList.add('reveal-target');
    revealObserver.observe(target);
  });
}

const emberCanvas = $('#emberCanvas');
if (emberCanvas) {
  const context = emberCanvas.getContext('2d');
  let width = 0;
  let height = 0;
  const embers = [];
  const emberCount = window.innerWidth < 650 ? 22 : 42;
  function resizeCanvas() {
    const bounds = emberCanvas.getBoundingClientRect();
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    width = bounds.width;
    height = bounds.height;
    emberCanvas.width = width * pixelRatio;
    emberCanvas.height = height * pixelRatio;
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }
  resizeCanvas();
  for (let i = 0; i < emberCount; i++) embers.push({
    x: Math.random() * width,
    y: Math.random() * height,
    radius: .5 + Math.random() * 1.5,
    speed: .08 + Math.random() * .22,
    drift: (Math.random() - .5) * .18,
    alpha: .14 + Math.random() * .38,
    gold: Math.random() > .78,
  });
  window.addEventListener('resize', resizeCanvas, { passive: true });
  function drawEmbers() {
    context.clearRect(0, 0, width, height);
    embers.forEach(ember => {
      context.beginPath();
      context.fillStyle = ember.gold ? `rgba(229,193,124,${ember.alpha})` : `rgba(57,255,20,${ember.alpha})`;
      context.shadowColor = ember.gold ? '#e5c17c' : '#39FF14';
      context.shadowBlur = ember.radius * 5;
      context.arc(ember.x, ember.y, ember.radius, 0, Math.PI * 2);
      context.fill();
      ember.y -= ember.speed;
      ember.x += ember.drift;
      if (ember.y < -4) { ember.y = height + 4; ember.x = Math.random() * width; }
      if (ember.x < -4) ember.x = width + 4;
      if (ember.x > width + 4) ember.x = -4;
    });
    context.shadowBlur = 0;
    if (!motionReduced) window.requestAnimationFrame(drawEmbers);
  }
  drawEmbers();
}
