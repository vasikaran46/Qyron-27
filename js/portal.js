// ============================================================
// QYRON'27 - STANDALONE PORTAL CONTROLLER (DOOM ARCHITECTURE)
// ============================================================
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const getApp = () => $('#loginApp') || $('#registerApp') || $('#participantApp') || $('#adminApp') || $('#portalApp');
  const toast = $('#toast');
  let toastTimer;
  let currentTab = 'participant';
  let currentUser = null;
  let userCanShortlist = false;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 3200);
  }

  async function apiRequest(path, options = {}) {
    const response = await fetch(path, {
      credentials: 'same-origin',
      ...options,
      headers: options.body instanceof FormData
        ? options.headers
        : { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'The request could not be completed.');
    return data;
  }

  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);

  // Tab switcher
  function setTab(tabName) {
    currentTab = tabName;
    $$('.portal-tabs button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    window.location.hash = tabName;

    if (tabName === 'register') {
      window.location.href = '/register';
      return;
    } else if (tabName === 'admin') {
      if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'reviewer')) {
        loadAdminDashboard();
      } else {
        renderAuthView('admin');
      }
    } else { // participant
      if (currentUser) {
        loadParticipantDashboard();
      } else {
        renderAuthView('participant');
      }
    }
  }

  // --- VIEW 1: AUTHENTICATION (SIGN IN / SIGN UP) ---
  function renderAuthView(kind = 'participant') {
    const isAdmin = kind === 'admin';
    const app = getApp();
    if (!app) return;
    app.innerHTML = `
      <div class="hud-corner hud-corner-tl"></div>
      <div class="hud-corner hud-corner-tr"></div>
      <div class="hud-corner hud-corner-bl"></div>
      <div class="hud-corner hud-corner-br"></div>
      <div class="portal-topline">
        <span>LATVERIA SECURE ENCLAVE // ${isAdmin ? 'ADMIN ACCESS' : 'PARTICIPANT UPLINK'}</span>
        <span class="mono-tag" style="color:var(--doom-green);">TLS 1.3 ENCRYPTED</span>
      </div>
      <h2>${isAdmin ? 'ADMIN' : 'PARTICIPANT'} <span>PORTAL.</span></h2>
      <p class="modal-subtitle">
        ${isAdmin
          ? 'Enter your organizer credentials to evaluate submissions, verify payments, and manage the 30-team shortlist.'
          : 'Sign in with your team lead email to access your team dashboard, submit proposals, and monitor selection status.'}
      </p>

      <form class="login-form" id="portalForm" style="max-width:480px;">
        <div class="field">
          <label for="portalEmail">${isAdmin ? 'ORGANIZER / ADMIN EMAIL' : 'TEAM LEAD EMAIL'}</label>
          <input id="portalEmail" type="email" required autocomplete="email" placeholder="${isAdmin ? 'admin@latveria.qyron' : 'lead@college.edu'}" />
        </div>
        <div class="field">
          <label for="portalPassword">PASSWORD</label>
          <input id="portalPassword" type="password" required autocomplete="current-password" minlength="8" placeholder="Enter secure password" />
        </div>
        <button class="button button-primary form-submit" type="submit">SIGN IN TO GATEWAY <span>↗</span></button>
        ${!isAdmin ? `<button type="button" class="auth-switch" id="createAccountBtn">New team? Create a participant account</button>` : ''}
        <p class="form-notice" id="portalNotice" aria-live="polite">
          ${isAdmin
            ? 'Access restricted to authorized Department of Mathematics jury and reviewers.'
            : 'Your team records are private to your registered lead account.'}
        </p>
      </form>

      <div class="preview-actions">
        <span>EXPLORE PORTAL INTERFACES (SAMPLE DEMO)</span>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          <button class="preview-button" id="previewParticipantBtn">▶ Preview Participant Dashboard</button>
          <button class="preview-button" id="previewAdminBtn">▶ Preview Admin Review Console</button>
        </div>
        <small style="color:var(--text-dim); font-family:var(--font-mono); font-size:9px;">Sample mode runs locally for evaluation without modifying database records.</small>
      </div>
    `;

    $('#portalForm').addEventListener('submit', async event => {
      event.preventDefault();
      if (!event.currentTarget.reportValidity()) return;
      $('#portalNotice').textContent = 'Authenticating with Latveria Central Relay…';
      try {
        await apiRequest('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email: $('#portalEmail').value.trim(), password: $('#portalPassword').value })
        });
        currentUser = await apiRequest('/api/auth/me');
        userCanShortlist = currentUser.role === 'admin';
        showToast(`Authenticated as ${currentUser.email}`);

        if ($('#loginApp')) {
          if (currentUser.role === 'admin' || currentUser.role === 'reviewer') {
            window.location.href = '/admin';
          } else {
            window.location.href = '/participant';
          }
          return;
        }

        if (currentUser.role === 'admin' || currentUser.role === 'reviewer') {
          if ($('#adminApp')) loadAdminDashboard();
          else setTab('admin');
        } else {
          if ($('#participantApp')) loadParticipantDashboard();
          else setTab('participant');
        }
      } catch (error) {
        $('#portalNotice').textContent = error.message;
      }
    });

    $('#createAccountBtn')?.addEventListener('click', () => renderSignupView());
    $('#previewParticipantBtn').addEventListener('click', () => renderParticipantDashboard(sampleParticipantData(), true));
    $('#previewAdminBtn').addEventListener('click', () => renderAdminDashboard(sampleAdminData(), true));
  }

  // --- VIEW 2: SIGN UP VIEW ---
  function renderSignupView() {
    const app = getApp();
    if (!app) return;
    app.innerHTML = `
      <div class="hud-corner hud-corner-tl"></div>
      <div class="hud-corner hud-corner-tr"></div>
      <div class="hud-corner hud-corner-bl"></div>
      <div class="hud-corner hud-corner-br"></div>
      <div class="portal-topline">
        <span>ACCOUNT REGISTRATION // DOOMSDAY PROTOCOL</span>
        <button type="button" id="backToSigninBtn">← Back to Sign In</button>
      </div>
      <h2>CREATE <span>ACCOUNT.</span></h2>
      <p class="modal-subtitle">Use the team lead's email address. A verification link will be dispatched via secure SMTP.</p>

      <form class="login-form" id="signupForm" style="max-width:480px;">
        <div class="field">
          <label for="signupEmail">TEAM LEAD EMAIL</label>
          <input id="signupEmail" type="email" required autocomplete="email" placeholder="teamlead@college.edu" />
        </div>
        <div class="field">
          <label for="signupPassword">PASSWORD (MIN 8 CHARACTERS)</label>
          <input id="signupPassword" type="password" required minlength="8" maxlength="128" autocomplete="new-password" placeholder="At least 8 characters" />
        </div>
        <button class="button button-primary form-submit" type="submit">CREATE PARTICIPANT ACCOUNT <span>↗</span></button>
        <p class="form-notice" id="signupNotice" aria-live="polite">An account is required before registering your 4–6 member roster.</p>
        <button type="button" class="auth-switch" id="resendVerificationBtn" style="margin-top: 10px;">Didn't get the email? Resend verification link</button>
      </form>
    `;

    $('#backToSigninBtn').addEventListener('click', () => renderAuthView('participant'));

    $('#resendVerificationBtn').addEventListener('click', async () => {
      const email = $('#signupEmail').value.trim();
      if (!email) {
        $('#signupNotice').textContent = 'Please enter your team lead email address above first.';
        return;
      }
      $('#signupNotice').textContent = 'Dispatching new verification link via SMTP…';
      try {
        const data = await apiRequest('/api/auth/resend-verification', {
          method: 'POST',
          body: JSON.stringify({ email })
        });
        $('#signupNotice').textContent = data.message;
        showToast('Verification email resent');
      } catch (error) {
        $('#signupNotice').textContent = error.message;
      }
    });

    $('#signupForm').addEventListener('submit', async event => {
      event.preventDefault();
      if (!event.currentTarget.reportValidity()) return;
      $('#signupNotice').textContent = 'Creating account and sending verification email…';
      try {
        const data = await apiRequest('/api/auth/signup', {
          method: 'POST',
          body: JSON.stringify({ email: $('#signupEmail').value.trim(), password: $('#signupPassword').value })
        });
        $('#signupNotice').textContent = data.message;
        showToast('Registration successful! Check email.');
      } catch (error) {
        $('#signupNotice').textContent = error.message;
      }
    });
  }

  // --- VIEW 3: ASSEMBLE TEAM REGISTRATION ---
  function renderRegisterView() {
    const app = getApp();
    if (!app) return;
    app.innerHTML = `
      <div class="hud-corner hud-corner-tl"></div>
      <div class="hud-corner hud-corner-tr"></div>
      <div class="hud-corner hud-corner-bl"></div>
      <div class="hud-corner hud-corner-br"></div>
      <div class="portal-topline">
        <span>OPERATION: ASSEMBLE // COMPLETE ROSTER REGISTRATION</span>
        <span style="color:var(--gold);">FIRST ROUND: ₹150 / TEAM</span>
      </div>
      <h2>ASSEMBLE YOUR <span>TEAM.</span></h2>
      <p class="modal-subtitle">
        Register all 4–6 team members together. The ₹150 team registration fee qualifies your submission for jury review.
      </p>

      <form id="registrationForm">
        <div class="form-grid">
          <div class="field">
            <label for="teamName">TEAM NAME</label>
            <input id="teamName" name="teamName" required maxlength="70" placeholder="e.g. Theorem Keepers" />
          </div>
          <div class="field">
            <label for="college">COLLEGE / INSTITUTION</label>
            <input id="college" name="college" required maxlength="120" placeholder="e.g. Patrician College of Arts and Science" />
            <small style="color:var(--toxic-lime); font-size:10px; font-family:var(--font-mono); margin-top:4px; display:block;">※ Inter-college participation is strictly NOT allowed. All members must be from this institution.</small>
          </div>
          <div class="field full">
            <label for="challengeTrack">CHALLENGE TRACK</label>
            <select id="challengeTrack" name="track">
              <option value="Track 1: Quantum Superposition & Circuit Modeling">Track 1: Quantum Superposition & Circuit Modeling</option>
              <option value="Track 2: Quantum Algorithms, Cryptography & Security">Track 2: Quantum Algorithms, Cryptography & Security</option>
              <option value="Track 3: Quantum Error Correction & Optimization">Track 3: Quantum Error Correction & Optimization</option>
              <option value="Track 4: Open Mathematical & Post-Apocalyptic Computing">Track 4: Open Mathematical & Post-Apocalyptic Computing</option>
            </select>
          </div>
        </div>

        <div class="member-fields">
          <h3>TEAM ROSTER <span id="memberCount">4 MEMBERS</span></h3>
          <div id="memberRows"></div>
          <button type="button" class="roster-add" id="addMember">＋ ADD MEMBER</button>
          <p class="member-help">The first member is the team lead and must match your signed-in account email.</p>
        </div>

        <div class="upload-box">
          FIRST ROUND FEE · ₹150 PER TEAM
          <em>Payment reference can be submitted after registration. Registration deadline: 20 Jan 2027 · 11:59 PM IST.</em>
        </div>

        <button class="button button-primary form-submit" type="submit">SUBMIT COMPLETE ROSTER <span>↗</span></button>
        <p class="form-notice" id="regNotice" aria-live="polite">Sign in with the team lead account before submitting.</p>
      </form>
    `;

    const rows = $('#memberRows');
    let count = 4;
    function drawRows() {
      rows.innerHTML = Array.from({ length: count }, (_, index) => `
        <div class="member-row">
          <input aria-label="Member ${index + 1} full name" required maxlength="100" placeholder="${index === 0 ? 'Team lead full name' : `Member ${index + 1} name`}" />
          <input aria-label="Member ${index + 1} email" required type="email" maxlength="254" placeholder="${index === 0 ? 'Team lead email' : `Member ${index + 1} email`}" />
          <input aria-label="Member ${index + 1} student ID" required maxlength="80" placeholder="Student ID / Roll No." />
        </div>
      `).join('');
      $('#memberCount').textContent = `${count} MEMBERS`;
      $('#addMember').disabled = count >= 6;
      $('#addMember').textContent = count >= 6 ? 'MAXIMUM TEAM SIZE REACHED (6)' : '＋ ADD MEMBER';
    }
    drawRows();

    $('#addMember').addEventListener('click', () => {
      if (count < 6) {
        count++;
        drawRows();
      }
    });

    $('#registrationForm').addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.currentTarget;
      if (!form.reportValidity()) return;

      const emails = $$('#memberRows input[type="email"]').map(i => i.value.trim().toLowerCase());
      if (new Set(emails).size !== emails.length) {
        $('#regNotice').textContent = 'Each team member must have a unique email address.';
        return;
      }

      const roster = $$('#memberRows .member-row').map(row => {
        const inputs = $$('input', row);
        return { full_name: inputs[0].value.trim(), email: inputs[1].value.trim(), student_id: inputs[2].value.trim() };
      });

      $('#regNotice').textContent = 'Transmitting roster to Latveria Command…';
      try {
        await apiRequest('/api/participant/teams', {
          method: 'POST',
          body: JSON.stringify({
            name: $('#teamName').value.trim(),
            college: $('#college').value.trim(),
            members: roster
          })
        });
        showToast('Team registered successfully · ₹150 payment pending');
        if ($('#registerApp')) {
          setTimeout(() => { window.location.href = '/participant'; }, 1000);
        } else {
          await loadParticipantDashboard();
        }
      } catch (error) {
        $('#regNotice').textContent = error.message;
      }
    });
  }

  // --- VIEW 4: PARTICIPANT DASHBOARD ---
  async function loadParticipantDashboard() {
    try {
      const data = await apiRequest('/api/participant/dashboard');
      renderParticipantDashboard(data, false);
    } catch (error) {
      renderAuthView('participant');
      showToast(error.message);
    }
  }

  function renderParticipantDashboard(data, preview = false) {
    const team = data.team;
    if (!team) {
      const app = getApp();
    if (!app) return;
    app.innerHTML = `
        <div class="hud-corner hud-corner-tl"></div>
        <div class="hud-corner hud-corner-tr"></div>
        <div class="hud-corner hud-corner-bl"></div>
        <div class="hud-corner hud-corner-br"></div>
        <div class="portal-topline">
          <span>${preview ? 'DEMO PREVIEW · SIMULATED VIEW' : 'PARTICIPANT DASHBOARD'}</span>
          <button data-signout>${preview ? 'Exit Preview' : 'Sign Out'}</button>
        </div>
        <h2>YOUR TEAM <span>IS NEXT.</span></h2>
        <p class="modal-subtitle">No registered team is linked to this account yet. Assemble your 4–6 member squad and register.</p>
        <button class="button button-primary" id="btnGoRegister">REGISTER TEAM ROSTER NOW <span>↗</span></button>
      `;
      $('#btnGoRegister').addEventListener('click', () => setTab('register'));
      bindSignOut(preview);
      return;
    }

    const regPayment = (data.payments || []).find(item => item.stage === 'registration');
    const memberPayments = (data.payments || []).filter(item => item.stage === 'shortlisted');
    const status = data.shortlist?.selected === true ? 'SHORTLISTED' : data.shortlist?.selected === false ? 'NOT SHORTLISTED' : 'UNDER REVIEW';

    const app = getApp();
    if (!app) return;
    app.innerHTML = `
      <div class="hud-corner hud-corner-tl"></div>
      <div class="hud-corner hud-corner-tr"></div>
      <div class="hud-corner hud-corner-bl"></div>
      <div class="hud-corner hud-corner-br"></div>
      <div class="portal-topline">
        <span>${preview ? 'DEMO PREVIEW · NOT SAVED' : 'PARTICIPANT SECURE DASHBOARD'}</span>
        <button data-signout>${preview ? 'Exit Preview' : 'Sign Out'}</button>
      </div>
      <h2>${escapeHTML(team.name)} <span>// TEAM DASHBOARD</span></h2>
      <p class="modal-subtitle">${escapeHTML(team.college)} · ${data.members?.length || 0} registered members · Status: ${escapeHTML(team.registration_status).replace('_', ' ').toUpperCase()}</p>

      <div class="dashboard-summary">
        <div>
          <small>REGISTRATION FEE (₹150)</small>
          <b>${escapeHTML(regPayment?.status || 'pending').toUpperCase()}</b>
        </div>
        <div>
          <small>PROPOSAL DOSSIER</small>
          <b>${data.submission ? 'RECEIVED' : 'NOT UPLOADED'}</b>
        </div>
        <div>
          <small>SHORTLIST STATUS</small>
          <b>${status}</b>
        </div>
        <div>
          <small>FINAL ROUND FEES</small>
          <b>${memberPayments.length ? memberPayments.filter(i => i.status === 'verified').length + '/' + memberPayments.length + ' PAID' : 'IF SHORTLISTED'}</b>
        </div>
      </div>

      <div class="dashboard-columns">
        <section class="dashboard-card">
          <div class="dashboard-card-title">
            <span>TEAM ROSTER</span>
            <b>${data.members?.length || 0} / 6 MEMBERS</b>
          </div>
          <ul class="roster-list">
            ${(data.members || []).map(member => `
              <li>
                <span class="roster-avatar">${escapeHTML(member.full_name?.slice(0, 1)?.toUpperCase())}</span>
                <span>
                  <strong>${escapeHTML(member.full_name)} ${member.is_team_lead ? '<i>LEAD</i>' : ''}</strong>
                  <small>${escapeHTML(member.email)} · ${escapeHTML(member.student_id)}</small>
                </span>
              </li>
            `).join('')}
          </ul>
        </section>

        <section class="dashboard-card" style="grid-column: 1 / -1;">
          <div class="dashboard-card-title">
            <span>PROPOSAL DOSSIER &amp; PRESENTATION SUBMISSION</span>
            <b>${data.submission ? 'SUBMITTED' : 'ACTION REQUIRED'}</b>
          </div>
          ${data.submission ? `
            <div style="background:rgba(57,255,20,0.06); border:1px solid rgba(57,255,20,0.3); border-radius:4px; padding:14px; margin-bottom:16px;">
              <p class="receipt-file" style="margin-bottom:4px;">▤ ${escapeHTML(data.submission.original_filename)}</p>
              <p class="receipt-detail" style="margin:0;">${(data.submission.size_bytes / 1048576).toFixed(2)} MB · Uploaded on ${new Date(data.submission.submitted_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST · Stored in Google Drive</p>
            </div>
          ` : '<p class="receipt-detail" style="margin-bottom:14px;">Fill in your proposal title, executive abstract, technical architecture description, and upload your official 7-section PPT/PDF (10 MB maximum). The presentation will be stored directly to the official Google Drive archive.</p>'}

          <div style="display:flex; justify-content:flex-end; margin-bottom:14px;">
            <a href="/download/idea-template" class="button button-outline" download style="font-size:11px; padding:6px 14px; text-decoration:none;">
              <span>DOWNLOAD OFFICIAL PPT TEMPLATE</span> <span>↓</span>
            </a>
          </div>

          <form id="submissionUpload" class="upload-form" style="display:flex; flex-direction:column; gap:14px;">
            <div>
              <label for="proposalTitle" style="font-size:11px; font-weight:700; color:var(--doom-green); display:block; margin-bottom:6px;">PROPOSAL / PROJECT TITLE *</label>
              <input id="proposalTitle" type="text" placeholder="e.g. Topological Quantum Error Correction in Dystopian Sensor Networks" required ${preview ? 'disabled' : ''} value="${escapeHTML(team.idea_title || '')}" style="width:100%; box-sizing:border-box; background:rgba(0,0,0,0.4); border:1px solid rgba(57,255,20,0.3); color:#fff; padding:10px 12px; border-radius:3px; font-family:var(--font-sans);" />
            </div>

            <div>
              <label for="proposalAbstract" style="font-size:11px; font-weight:700; color:var(--doom-green); display:block; margin-bottom:6px;">EXECUTIVE ABSTRACT &amp; PROBLEM STATEMENT *</label>
              <textarea id="proposalAbstract" rows="3" placeholder="Brief 150-250 word summary of the challenge addressed, proposed mathematical or quantum formulation, and expected breakthroughs." required ${preview ? 'disabled' : ''} style="width:100%; box-sizing:border-box; background:rgba(0,0,0,0.4); border:1px solid rgba(57,255,20,0.3); color:#fff; padding:10px 12px; border-radius:3px; font-family:var(--font-sans); resize:vertical;">${escapeHTML(team.idea_summary || '')}</textarea>
            </div>

            <div>
              <label for="proposalDescription" style="font-size:11px; font-weight:700; color:var(--doom-green); display:block; margin-bottom:6px;">DETAILED TECHNICAL ARCHITECTURE &amp; METHODOLOGY *</label>
              <textarea id="proposalDescription" rows="4" placeholder="Comprehensive technical details: quantum circuit structure, Hamiltonians/algorithms utilized, fault tolerance, simulation framework (Qiskit/PennyLane/Cirq), and mathematical rigor." required ${preview ? 'disabled' : ''} style="width:100%; box-sizing:border-box; background:rgba(0,0,0,0.4); border:1px solid rgba(57,255,20,0.3); color:#fff; padding:10px 12px; border-radius:3px; font-family:var(--font-sans); resize:vertical;">${escapeHTML(team.idea_description || '')}</textarea>
            </div>

            <div>
              <label for="proposalFile" style="font-size:11px; font-weight:700; color:var(--doom-green); display:block; margin-bottom:6px;">${data.submission ? 'REPLACE PRESENTATION SLIDE DECK (.PPTX, .PPT, .PDF)' : 'UPLOAD PRESENTATION SLIDE DECK (.PPTX, .PPT, .PDF) *'}</label>
              <input id="proposalFile" type="file" accept=".ppt,.pptx,.pdf" ${data.submission ? '' : 'required'} ${preview ? 'disabled' : ''} style="width:100%; box-sizing:border-box; background:rgba(0,0,0,0.4); border:1px solid rgba(57,255,20,0.3); color:#fff; padding:8px 12px; border-radius:3px;" />
            </div>

            <button class="button button-outline" type="submit" ${preview ? 'disabled' : ''} style="width:100%; justify-content:center; padding:12px; font-weight:700; margin-top:6px;">
              <span>${data.submission ? 'UPDATE PROPOSAL DOSSIER &amp; RE-UPLOAD SLIDES' : 'SUBMIT PROPOSAL DOSSIER &amp; SLIDES'}</span> <span style="margin-left:8px;">➔</span>
            </button>
            <p id="uploadNotice" class="form-notice" aria-live="polite" style="margin:4px 0 0;">Submission Deadline: 25 Jan 2027 · 11:59 PM IST</p>
          </form>
        </section>
      </div>

      <section class="dashboard-card" style="margin-top:20px;">
        <div class="dashboard-card-title">
          <span>PAYMENT TRACKER &amp; VERIFICATION</span>
          <b>₹150 / TEAM INITIAL · ₹350 / MEMBER FINALIST</b>
        </div>
        ${renderPaymentRows(data.payments || [], data, preview) || '<p class="receipt-detail">No active payments pending.</p>'}
      </section>
    `;

    bindSignOut(preview);

    $('#submissionUpload')?.addEventListener('submit', async event => {
      event.preventDefault();
      const fileInput = $('#proposalFile');
      const file = fileInput.files[0];
      const title = $('#proposalTitle').value.trim();
      const abstract = $('#proposalAbstract').value.trim();
      const description = $('#proposalDescription').value.trim();

      if (!title || !abstract || !description) {
        $('#uploadNotice').textContent = 'Please fill in the proposal title, abstract, and technical description.';
        return;
      }

      if (!file && !data.submission) {
        $('#uploadNotice').textContent = 'Please select a presentation file (.pptx, .ppt, or .pdf).';
        return;
      }

      if (file && file.size > 10 * 1024 * 1024) {
        $('#uploadNotice').textContent = 'File is larger than the 10 MB limit.';
        return;
      }

      if (preview) {
        $('#uploadNotice').textContent = 'Simulated preview only. Proposal updated in memory.';
        return;
      }

      const form = new FormData();
      if (file) {
        form.append('file', file);
        form.append('idea_ppt', file);
      }
      form.append('title', title);
      form.append('idea_title', title);
      form.append('abstract', abstract);
      form.append('idea_summary', abstract);
      form.append('description', description);
      form.append('idea_description', description);
      form.append('team_code', team.team_code || team.id || '');
      form.append('email', (data.viewer_email || '').toLowerCase());

      $('#uploadNotice').textContent = 'Uploading proposal & presentation to Google Drive…';

      try {
        let res = null;
        try {
          res = await apiRequest(`/api/participant/teams/${encodeURIComponent(team.id)}/submission`, {
            method: 'POST',
            body: form
          });
        } catch (teamEndpointErr) {
          // Fallback to portal submit-proposal endpoint
          const directRes = await fetch('/api/portal/submit-proposal', {
            method: 'POST',
            body: form
          });
          res = await directRes.json();
          if (!directRes.ok || !res.success) {
            throw new Error(res.message || 'Submission failed');
          }
        }
        showToast('Proposal & Presentation submitted to Google Drive successfully!');
        await loadParticipantDashboard();
      } catch (error) {
        $('#uploadNotice').textContent = error.message;
      }
    });

    $$('.payment-reference-form').forEach(form => form.addEventListener('submit', async event => {
      event.preventDefault();
      if (preview) {
        showToast('Demo preview: reference update simulated');
        return;
      }
      const input = $('input[name="payment_reference"]', form);
      try {
        await apiRequest(`/api/participant/teams/${encodeURIComponent(team.id)}/payments/${encodeURIComponent(form.dataset.payment)}/reference`, {
          method: 'POST',
          body: JSON.stringify({ payment_reference: input.value.trim() })
        });
        showToast('Payment UTR sent to organizers');
        await loadParticipantDashboard();
      } catch (error) {
        const notice = $('.payment-reference-notice', form);
        if (notice) notice.textContent = error.message;
      }
    }));
  }

  function renderPaymentRows(payments, data, preview) {
    return payments.map(payment => {
      const canSubmit = !preview && (payment.stage === 'registration' ? data.is_team_lead : payment.member_email?.toLowerCase() === data.viewer_email?.toLowerCase());
      const needsReference = canSubmit && ['pending', 'rejected'].includes(payment.status);
      const owner = payment.stage === 'registration' ? 'STAGE 1: TEAM REGISTRATION' : `STAGE 2: FINALIST (${escapeHTML(payment.member_name || 'MEMBER')})`;
      return `
        <div class="payment-entry">
          <div class="payment-row">
            <span>${owner}</span>
            <b>₹${payment.amount_inr}</b>
            <em class="status-chip status-${escapeHTML(payment.status)}">${escapeHTML(payment.status).toUpperCase()}</em>
          </div>
          ${needsReference ? `
            <form class="payment-reference-form" data-payment="${escapeHTML(payment.id)}" style="margin-top:8px;">
              <div style="display:flex; gap:8px; align-items:center;">
                <input name="payment_reference" minlength="3" maxlength="200" required value="${escapeHTML(payment.payment_reference || '')}" placeholder="Enter Transaction / UTR reference" style="flex-grow:1; height:34px; background:#040906; border:1px solid var(--steel-border); color:#fff; padding:0 8px; font-family:var(--font-mono); font-size:11px;" />
                <button type="submit" class="button button-outline" style="height:34px; padding:0 12px; font-size:9px;">SUBMIT UTR</button>
              </div>
              <small class="payment-reference-notice" style="color:var(--text-muted); font-size:10px; margin-top:4px; display:block;">Organizers will review and verify this payment reference.</small>
            </form>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  // --- VIEW 5: ADMIN DASHBOARD ---
  async function loadAdminDashboard() {
    try {
      const data = await apiRequest('/api/admin/dashboard');
      renderAdminDashboard(data, false);
    } catch (error) {
      renderAuthView('admin');
      showToast(error.message);
    }
  }

  function renderAdminDashboard(data, preview = false) {
    if (preview) userCanShortlist = true;
    const state = data;
    const counts = {
      shortlisted: state.shortlisted_count ?? state.teams.filter(t => t.shortlist?.selected).length,
      total: state.teams.length,
      submissions: state.teams.filter(t => t.submission).length,
      pending: state.teams.reduce((acc, t) => acc + t.payments.filter(p => ['submitted', 'pending'].includes(p.status)).length, 0)
    };

    const app = getApp();
    if (!app) return;
    app.innerHTML = `
      <div class="hud-corner hud-corner-tl"></div>
      <div class="hud-corner hud-corner-tr"></div>
      <div class="hud-corner hud-corner-bl"></div>
      <div class="hud-corner hud-corner-br"></div>
      <div class="portal-topline">
        <span>${preview ? 'DEMO PREVIEW · SIMULATED ADMIN CONSOLE' : 'LATVERIA JURY DIRECTORATE'}</span>
        <button data-signout>${preview ? 'Exit Preview' : 'Sign Out'}</button>
      </div>
      <h2>REVIEW <span>DIRECTORATE.</span></h2>
      <p class="modal-subtitle">
        Score candidate proposals across the 5 mathematical lenses, verify UPI/UTR transaction references, and publish the 30 shortlisted finalist teams.
      </p>

      <div class="admin-stats">
        <div><small>REGISTERED TEAMS</small><b>${counts.total}</b></div>
        <div><small>PROPOSALS RECEIVED</small><b>${counts.submissions}</b></div>
        <div><small>PENDING PAYMENTS</small><b>${counts.pending}</b></div>
        <div><small>SHORTLISTED TEAMS</small><b>${counts.shortlisted}<span> / 30</span></b></div>
      </div>

      <div class="shortlist-meter">
        <div style="width:${Math.min(100, (counts.shortlisted / 30) * 100)}%"></div>
      </div>

      <!-- UPI REGISTRATION & PAYMENT VERIFICATION DESK -->
      <section class="dashboard-card" style="margin-bottom:28px; border-color:var(--doom-green); box-shadow:0 0 25px rgba(57,255,20,0.15);">
        <div class="dashboard-card-title" style="border-bottom:1px solid rgba(57,255,20,0.25); padding-bottom:12px; margin-bottom:16px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="pulse-led" style="background:var(--doom-green); box-shadow:0 0 8px var(--doom-green);"></span>
            <span style="color:var(--doom-green); font-family:var(--font-mono); font-size:13px; font-weight:700;">
              // UPI PAYMENT VERIFICATION DESK &bull; REGISTRATIONS DIRECTORY
            </span>
          </div>
          <button id="btnRefreshPayments" class="button button-outline" type="button" style="font-size:10px; padding:4px 10px; height:auto;">
            REFRESH DIRECTORY &#x21bb;
          </button>
        </div>
        <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:14px; line-height:1.5;">
          Cross-check each team's submitted 12-digit UPI Reference (UTR) against the college bank account. Once verified, click <strong>"VERIFY &amp; SEND EMAIL"</strong> to activate their portal account and dispatch the official <strong>Payment Verified &amp; Portal Credentials</strong> email.
        </p>
        <div id="upiRegistrationsTableContainer" style="overflow-x:auto;">
          <div style="text-align:center; padding:20px; font-family:var(--font-mono); color:var(--text-muted);">
            Loading registration records...
          </div>
        </div>
      </section>

      <div class="admin-toolbar">
        <label>
          FILTER TEAMS:
          <select id="teamFilter">
            <option value="all">All Teams (${counts.total})</option>
            <option value="unreviewed">Needs Review</option>
            <option value="submitted">Has Proposal</option>
            <option value="shortlisted">Shortlisted (${counts.shortlisted})</option>
          </select>
        </label>
        <span style="color:var(--gold);">RUBRIC: 5 CRITERIA · 20 POINTS EACH (100 TOTAL)</span>
      </div>

      <div class="admin-team-list">
        ${state.teams.map(team => renderAdminTeam(team, state, preview)).join('')}
      </div>
    `;

    bindSignOut(preview);

    $('#teamFilter').addEventListener('change', e => {
      $$('.admin-team-card').forEach(card => card.hidden = !matchesFilter(card, e.target.value));
    });

    $$('.team-review-form').forEach(form => form.addEventListener('submit', async event => {
      event.preventDefault();
      const tid = form.dataset.team;
      const payload = Object.fromEntries(new FormData(form).entries());
      for (const k of ['math_rigor', 'originality', 'impact', 'feasibility', 'presentation']) payload[k] = Number(payload[k]);
      if (preview) {
        showToast('Sample review updated in preview');
        return;
      }
      try {
        await apiRequest(`/api/admin/teams/${encodeURIComponent(tid)}/review`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        showToast('Evaluation saved successfully');
        await loadAdminDashboard();
      } catch (err) {
        showToast(err.message);
      }
    }));

    $$('[data-shortlist]').forEach(button => button.addEventListener('click', async () => {
      const tid = button.dataset.shortlist;
      const team = state.teams.find(t => t.id === tid);
      const isSelected = Boolean(team.shortlist?.selected);
      if (!isSelected && counts.shortlisted >= 30) {
        showToast('Shortlist is full (maximum 30 teams)');
        return;
      }
      if (preview) {
        team.shortlist = { selected: !isSelected };
        renderAdminDashboard(state, true);
        return;
      }
      try {
        await apiRequest(`/api/admin/teams/${encodeURIComponent(tid)}/shortlist`, {
          method: 'PUT',
          body: JSON.stringify({ selected: !isSelected })
        });
        showToast(!isSelected ? 'Team added to shortlist' : 'Team removed from shortlist');
        await loadAdminDashboard();
      } catch (err) {
        showToast(err.message);
      }
    }));

    $$('[data-payment]').forEach(button => button.addEventListener('click', async () => {
      if (preview) {
        showToast('Demo payment status updated');
        return;
      }
      const note = prompt('Optional payment review note:') || '';
      try {
        await apiRequest(`/api/admin/payments/${encodeURIComponent(button.dataset.payment)}`, {
          method: 'PATCH',
          body: JSON.stringify({ status: button.dataset.status, note })
        });
        showToast(`Payment marked as ${button.dataset.status}`);
        await loadAdminDashboard();
      } catch (err) {
        showToast(err.message);
      }
    }));

    $$('[data-submission-team]').forEach(button => button.addEventListener('click', async () => {
      if (preview) {
        showToast('Demo mode: Proposal preview simulated');
        return;
      }
      try {
        const data = await apiRequest(`/api/admin/teams/${encodeURIComponent(button.dataset.submissionTeam)}/submission-link`);
        window.open(data.url, '_blank', 'noopener,noreferrer');
      } catch (err) {
        showToast(err.message);
      }
    }));

    $('#btnRefreshPayments')?.addEventListener('click', () => loadUpiRegistrations());
    loadUpiRegistrations();
  }

  async function loadUpiRegistrations() {
    const container = document.getElementById('upiRegistrationsTableContainer');
    if (!container) return;
    try {
      const res = await fetch('/api/admin/registrations');
      const data = await res.json();
      const records = data.registrations || [];
      if (!records.length) {
        container.innerHTML = '<p style="color:var(--text-muted); font-size:13px; padding:14px 0;">No squad registrations found in registry.</p>';
        return;
      }
      container.innerHTML = `
        <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
          <thead>
            <tr style="border-bottom:2px solid var(--doom-green); color:var(--doom-green); font-family:var(--font-mono);">
              <th style="padding:10px 8px;">REG ID &amp; SQUAD</th>
              <th style="padding:10px 8px;">LEADER &amp; COLLEGE</th>
              <th style="padding:10px 8px;">SUBMITTED UTR</th>
              <th style="padding:10px 8px;">SCREENSHOT</th>
              <th style="padding:10px 8px;">PAYMENT STATUS</th>
              <th style="padding:10px 8px; text-align:right;">DIRECTORATE ACTION</th>
            </tr>
          </thead>
          <tbody>
            ${records.map(r => {
              const isPaid = r.payment_status === 'paid' || r.payment_status === 'verified';
              const isRejected = r.payment_status === 'rejected';
              const utr = r.utr_number || r.razorpay_payment_id || 'Pending UTR';
              const screenshot = r.payment_screenshot_url;
              return `
                <tr style="border-bottom:1px solid rgba(57,255,20,0.15); background:rgba(0,0,0,0.25);">
                  <td style="padding:10px 8px;">
                    <strong style="color:#fff;">${escapeHTML(r.team_code || '')}</strong><br>
                    <span style="color:var(--doom-green); font-size:11px;">${escapeHTML(r.team_name || '')}</span>
                  </td>
                  <td style="padding:10px 8px;">
                    <span style="color:#fff; font-weight:600;">${escapeHTML(r.leader_name || '')}</span><br>
                    <small style="color:var(--text-muted);">${escapeHTML(r.leader_phone || '')} &bull; ${escapeHTML(r.leader_email || '')}</small><br>
                    <small style="color:var(--silver); font-size:10px;">${escapeHTML(r.college_name || '')}</small>
                  </td>
                  <td style="padding:10px 8px; font-family:var(--font-mono);">
                    <code style="background:rgba(57,255,20,0.1); color:var(--doom-green); padding:3px 6px; border-radius:3px; font-weight:700;">${escapeHTML(utr)}</code>
                  </td>
                  <td style="padding:10px 8px;">
                    ${screenshot ? `<a href="${escapeHTML(screenshot)}" target="_blank" rel="noopener noreferrer" style="color:#00e5ff; text-decoration:underline; font-size:11.5px; font-weight:bold;">View Receipt ↗</a>` : '<span style="color:var(--text-muted); font-size:11px;">No upload</span>'}
                  </td>
                  <td style="padding:10px 8px;">
                    <span class="term-badge" style="${isPaid ? 'background:rgba(57,255,20,0.15); color:var(--doom-green); border-color:var(--doom-green);' : (isRejected ? 'background:rgba(239,68,68,0.15); color:#ef4444; border-color:#ef4444;' : 'background:rgba(245,158,11,0.15); color:#f59e0b; border-color:#f59e0b;')} font-size:10px;">
                      ${isPaid ? '✅ VERIFIED' : (isRejected ? '❌ REJECTED' : '⏳ PENDING')}
                    </span>
                  </td>
                  <td style="padding:10px 8px; text-align:right;">
                    ${!isPaid ? `
                      <button class="btn-verify-upi" data-code="${escapeHTML(r.team_code)}" style="background:rgba(57,255,20,0.18); border:1px solid var(--doom-green); color:var(--doom-green); padding:6px 12px; font-family:var(--font-mono); font-size:10.5px; border-radius:3px; cursor:pointer; font-weight:700;">
                        VERIFY &amp; SEND EMAIL ✓
                      </button>
                      <button class="btn-reject-upi" data-code="${escapeHTML(r.team_code)}" style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; color:#ef4444; padding:6px 8px; font-family:var(--font-mono); font-size:10.5px; border-radius:3px; cursor:pointer; margin-left:4px;">
                        REJECT ✗
                      </button>
                    ` : `
                      <button class="btn-verify-upi" data-code="${escapeHTML(r.team_code)}" style="background:rgba(0,229,255,0.15); border:1px solid #00e5ff; color:#00e5ff; padding:5px 10px; font-family:var(--font-mono); font-size:10px; border-radius:3px; cursor:pointer;">
                        RESEND EMAIL ↻
                      </button>
                    `}
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      `;

      container.querySelectorAll('.btn-verify-upi').forEach(btn => {
        btn.addEventListener('click', async () => {
          const code = btn.dataset.code;
          btn.disabled = true;
          btn.textContent = 'VERIFYING...';
          try {
            const vRes = await fetch(`/api/admin/registrations/${encodeURIComponent(code)}/verify-payment`, { method: 'POST' });
            const vData = await vRes.json();
            if (vRes.ok && vData.success) {
              showToast(vData.message || `Payment verified for ${code}!`);
              await loadUpiRegistrations();
            } else {
              alert(vData.message || 'Verification error');
              btn.disabled = false;
              btn.textContent = 'VERIFY & SEND EMAIL ✓';
            }
          } catch (e) {
            alert('Failed to connect to verification service.');
            btn.disabled = false;
            btn.textContent = 'VERIFY & SEND EMAIL ✓';
          }
        });
      });

      container.querySelectorAll('.btn-reject-upi').forEach(btn => {
        btn.addEventListener('click', async () => {
          const code = btn.dataset.code;
          if (!confirm(`Are you sure you want to REJECT payment for squad ${code}?`)) return;
          try {
            const rRes = await fetch(`/api/admin/registrations/${encodeURIComponent(code)}/reject-payment`, { method: 'POST' });
            const rData = await rRes.json();
            showToast(`Squad ${code} payment marked as rejected.`);
            await loadUpiRegistrations();
          } catch (e) {
            alert('Failed to reject payment.');
          }
        });
      });

    } catch (err) {
      container.innerHTML = `<p style="color:#ef4444; font-size:12px;">Failed to load registrations: ${escapeHTML(err.message)}</p>`;
    }
  }

  function renderAdminTeam(team, state, preview) {
    const selected = Boolean(team.shortlist?.selected);
    const limitHit = (state.shortlisted_count ?? state.teams.filter(t => t.shortlist?.selected).length) >= 30;
    const review = team.reviews?.[0] || {};
    const submitted = Boolean(team.submission);

    return `
      <article class="admin-team-card" data-review-state="${team.reviews?.length ? 'reviewed' : 'unreviewed'}" data-has-submission="${submitted}" data-shortlisted="${selected}">
        <div class="admin-team-head">
          <div>
            <span class="team-id">${escapeHTML(team.id.slice(0, 8))} // ${escapeHTML(team.college)}</span>
            <h3>${escapeHTML(team.name)}</h3>
            <small>${team.members?.length || 0} members · ${submitted ? escapeHTML(team.submission.original_filename) : 'No proposal file uploaded'}</small>
            ${submitted && !preview ? `<br><button class="file-review-link" type="button" data-submission-team="${escapeHTML(team.id)}">OPEN SECURE PROPOSAL DOSSIER ↗</button>` : ''}
          </div>
          <span class="status-chip ${selected ? 'status-verified' : ''}">${selected ? 'SHORTLISTED' : escapeHTML(team.registration_status || 'under_review').replace('_', ' ').toUpperCase()}</span>
        </div>

        <details style="margin:14px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:8px 0;">
          <summary style="font-family:var(--font-mono); font-size:10px; color:var(--gold); cursor:pointer;">VIEW ROSTER (${team.members?.length || 0}) &amp; REVIEWS</summary>
          <ul style="list-style:none; padding:8px 0 0; margin:0; font-size:12px; color:var(--silver);">
            ${(team.members || []).map(m => `<li>• ${escapeHTML(m.full_name)} (${escapeHTML(m.email)}) ${m.is_team_lead ? '<b>[LEAD]</b>' : ''}</li>`).join('')}
          </ul>
        </details>

        <form class="team-review-form" data-team="${escapeHTML(team.id)}">
          <div class="score-grid">
            ${[
              ['math_rigor', 'MATH RIGOR'],
              ['originality', 'ORIGINALITY'],
              ['impact', 'IMPACT'],
              ['feasibility', 'FEASIBILITY'],
              ['presentation', 'PRESENTATION']
            ].map(([k, label]) => `
              <label>
                ${label}
                <input name="${k}" type="number" min="0" max="20" value="${Number(review[k] || 0)}" required />
              </label>
            `).join('')}
          </div>
          <label class="review-notes-label">
            EVALUATOR NOTES &amp; FEEDBACK
            <textarea name="notes" rows="2" maxlength="5000" placeholder="Observations on mathematical model, quantum feasibility, etc.">${escapeHTML(review.notes || '')}</textarea>
          </label>
          <div class="admin-actions">
            <button class="button button-outline" type="submit" style="height:38px; padding:0 14px; font-size:9px;">SAVE EVALUATION</button>
            ${userCanShortlist ? `
              <button class="shortlist-toggle ${selected ? 'is-selected' : ''}" type="button" data-shortlist="${escapeHTML(team.id)}" ${!selected && limitHit ? 'disabled' : ''}>
                ${selected ? 'REMOVE FROM SHORTLIST ✓' : 'SHORTLIST FOR FINAL 30 +'}
              </button>
            ` : ''}
          </div>
        </form>

        <div class="admin-payments">
          ${(team.payments || []).map(payment => `
            <div>
              <span>${payment.stage === 'registration' ? 'STAGE 1 (₹150)' : 'STAGE 2 (₹350)'} · ${escapeHTML(payment.status).toUpperCase()} ${payment.payment_reference ? `// REF: ${escapeHTML(payment.payment_reference)}` : ''}</span>
              ${['pending', 'submitted'].includes(payment.status) && userCanShortlist ? `
                <div>
                  <button data-payment="${escapeHTML(payment.id)}" data-status="verified">VERIFY ✓</button>
                  <button data-payment="${escapeHTML(payment.id)}" data-status="rejected">REJECT ✗</button>
                </div>
              ` : ''}
            </div>
          `).join('')}
        </div>
      </article>
    `;
  }

  function matchesFilter(card, filter) {
    if (filter === 'unreviewed') return card.dataset.reviewState === 'unreviewed';
    if (filter === 'submitted') return card.dataset.hasSubmission === 'true';
    if (filter === 'shortlisted') return card.dataset.shortlisted === 'true';
    return true;
  }

  function bindSignOut(preview = false) {
    $('[data-signout]')?.addEventListener('click', async () => {
      if (preview) {
        if ($('#participantApp') || $('#adminApp') || $('#loginApp')) {
          window.location.reload();
        } else {
          setTab(currentTab);
        }
        return;
      }
      try {
        await apiRequest('/api/auth/logout', { method: 'POST', body: '{}' });
      } finally {
        currentUser = null;
        showToast('Signed out of relay');
        if ($('#participantApp') || $('#adminApp')) {
          window.location.href = '/login';
        } else {
          setTab(currentTab);
        }
      }
    });
  }

  function sampleParticipantData() {
    return {
      team: { id: 'preview-01', name: 'Theorem Keepers', college: 'Patrician College of Arts & Science', registration_status: 'shortlisted' },
      members: [
        { full_name: 'Vasikaran A', email: 'karanvasi80@gmail.com', student_id: 'QY-2027-01', is_team_lead: true },
        { full_name: 'Jai Bharath A', email: 'jaib9943@gmail.com', student_id: 'QY-2027-02' },
        { full_name: 'Nethra S', email: 'nethrasoundarrajan02@gmail.com', student_id: 'QY-2027-03' },
        { full_name: 'Immanuel GM', email: 'gmimmanuel4@gmail.com', student_id: 'QY-2027-04' }
      ],
      payments: [
        { stage: 'registration', amount_inr: 150, status: 'verified', payment_reference: 'UPI/2027/DEMO-VERIFIED' },
        { stage: 'shortlisted', amount_inr: 350, status: 'pending', member_name: 'Vasikaran A', member_email: 'karanvasi80@gmail.com' }
      ],
      submission: {
        original_filename: 'qyron-quantum-collapse-model.pptx',
        size_bytes: 3410000,
        submitted_at: '2027-01-24T18:45:00+05:30'
      },
      shortlist: { selected: true },
      viewer_email: 'karanvasi80@gmail.com',
      is_team_lead: true
    };
  }

  function sampleAdminData() {
    return {
      shortlist_limit: 30,
      shortlisted_count: 24,
      teams: [
        {
          id: 'team-demo-alpha',
          name: 'Quantum Vanguard',
          college: 'Patrician College of Arts & Science',
          registration_status: 'shortlisted',
          members: [
            { full_name: 'Vasikaran A', email: 'lead@demo.edu', is_team_lead: true },
            { full_name: 'Jai Bharath A', email: 'jaib9943@gmail.com' },
            { full_name: 'Nethra S', email: 'nethrasoundarrajan02@gmail.com' },
            { full_name: 'Immanuel GM', email: 'gmimmanuel4@gmail.com' }
          ],
          submission: { original_filename: 'quantum-vanguard-proposal.pdf', size_bytes: 2400000 },
          shortlist: { selected: true, score: 92 },
          payments: [
            { id: 'p1', stage: 'registration', amount_inr: 150, status: 'verified', payment_reference: 'UPI-DEMO-991' },
            { id: 'p2', stage: 'shortlisted', amount_inr: 350, status: 'submitted', payment_reference: 'UTR-DEMO-FINAL-01' }
          ],
          reviews: [{ reviewer_id: 'demo', math_rigor: 19, originality: 18, impact: 19, feasibility: 18, presentation: 18, total_score: 92, notes: 'Exceptional quantum tensor modeling. Clear mathematical foundation.' }]
        },
        {
          id: 'team-demo-beta',
          name: 'Eigenstate Enforcers',
          college: 'Institute of Mathematical Sciences',
          registration_status: 'submission_received',
          members: [
            { full_name: 'Karan V', email: 'lead2@demo.edu', is_team_lead: true },
            { full_name: 'Partner B', email: 'b@demo.edu' }
          ],
          submission: { original_filename: 'eigenstate-circuits.pptx', size_bytes: 4100000 },
          shortlist: null,
          payments: [
            { id: 'p3', stage: 'registration', amount_inr: 150, status: 'submitted', payment_reference: 'PAYTM-12847291' }
          ],
          reviews: []
        }
      ]
    };
  }

  // Initial page detection and auth check
  async function init() {
    // Check existing session
    try {
      currentUser = await apiRequest('/api/auth/me');
      userCanShortlist = currentUser.role === 'admin';
    } catch {
      currentUser = null;
    }

    const isLoginPage = !!$('#loginApp');
    const isRegisterPage = !!$('#registerApp');
    const isParticipantPage = !!$('#participantApp');
    const isAdminPage = !!$('#adminApp');

    if (isLoginPage) {
      const mode = window.location.hash === '#admin' ? 'admin' : 'participant';
      $$('.portal-tabs button').forEach(button => {
        button.classList.toggle('active', button.dataset.loginMode === mode);
        button.addEventListener('click', () => {
          $$('.portal-tabs button').forEach(b => b.classList.remove('active'));
          button.classList.add('active');
          renderAuthView(button.dataset.loginMode);
        });
      });
      renderAuthView(mode);
      return;
    }

    if (isRegisterPage) {
      renderRegisterView();
      return;
    }

    if (isParticipantPage) {
      if (currentUser) {
        loadParticipantDashboard();
      } else {
        renderAuthView('participant');
      }
      return;
    }

    if (isAdminPage) {
      if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'reviewer')) {
        loadAdminDashboard();
      } else {
        renderAuthView('admin');
      }
      return;
    }

    // Default: portal.html tabbed hub
    const hash = window.location.hash.replace('#', '');
    if (['participant', 'register', 'admin', 'login'].includes(hash)) {
      currentTab = hash === 'login' ? 'participant' : hash;
    }

    $$('.portal-tabs button').forEach(button => {
      button.addEventListener('click', () => setTab(button.dataset.tab));
    });

    setTab(currentTab);
  }

  init();
})();
