/**
 * QYRON'27 - TACTICAL REGISTRATION WIZARD (DOOMSDAY PROTOCOL)
 * 3-Step Flow:
 * Step 1: Team & Crew Assembly (Callsign, College, Operational Track, Leader, Dynamic Crew 4-6)
 * Step 2: Idea Submission Dossier (Title <=100, Summary <=10,000, Description <=50,000, PPT <=10MB)
 * Step 3: Review Manifest & Payment Authorization (₹150 Team Registration Fee)
 */

let currentStep = 1;
const totalSteps = 3;

// Crew Member Management (Min 3 crew + 1 leader = 4 units minimum; max 5 crew + 1 leader = 6 units)
let membersList = [
  { id: 2, name: '', phone: '', email: '', gender: '', degree: '', department: '', year: '3rd Year' },
  { id: 3, name: '', phone: '', email: '', gender: '', degree: '', department: '', year: '3rd Year' },
  { id: 4, name: '', phone: '', email: '', gender: '', degree: '', department: '', year: '3rd Year' }
];

let selectedPptFile = null;

function renderMembersContainer() {
  const container = document.getElementById('members-container');
  if (!container) return;

  container.innerHTML = '';

  membersList.forEach((m, idx) => {
    const memberNum = idx + 2;
    const isOptional = memberNum > 4; // Member 5 and 6 are optional additions
    const card = document.createElement('div');
    card.className = 'member-card';
    card.id = `member-card-${memberNum}`;
    
    card.innerHTML = `
      <div class="member-card-header">
        <span class="member-badge-title">CREW MEMBER #${memberNum} ${isOptional ? '(OPTIONAL UNIT)' : '(REQUIRED UNIT)'}</span>
        ${membersList.length > 3 ? `
          <button type="button" class="btn-remove-member" onclick="removeMember(${idx})">
            ✕ REMOVE
          </button>
        ` : ''}
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Member Full Name <span class="required">*</span></label>
          <input type="text" class="form-control" data-idx="${idx}" data-field="name" value="${escapeHtml(m.name || '')}" placeholder="Full Name" required>
          <span class="form-hint">Crew member #${memberNum} full legal name.</span>
        </div>
        <div class="form-group">
          <label class="form-label">Member Mobile Number <span class="required">*</span></label>
          <input type="tel" class="form-control" data-idx="${idx}" data-field="phone" value="${escapeHtml(m.phone || '')}" placeholder="10-digit primary mobile" required>
          <span class="form-hint">10-digit primary mobile number.</span>
        </div>
        <div class="form-group">
          <label class="form-label">Member Email ID <span class="required">*</span></label>
          <input type="email" class="form-control" data-idx="${idx}" data-field="email" value="${escapeHtml(m.email || '')}" placeholder="Email Address" required>
          <span class="form-hint">Official email address.</span>
        </div>
        <div class="form-group">
          <label class="form-label">Gender <span class="required">*</span></label>
          <select class="form-control" data-idx="${idx}" data-field="gender" required>
            <option value="">-- Select Gender --</option>
            <option value="Male" ${m.gender === 'Male' ? 'selected' : ''}>Male</option>
            <option value="Female" ${m.gender === 'Female' ? 'selected' : ''}>Female</option>
            <option value="Other" ${m.gender === 'Other' ? 'selected' : ''}>Other</option>
          </select>
          <span class="form-hint">Gender identity.</span>
        </div>
        <div class="form-group">
          <label class="form-label">Degree <span class="required">*</span></label>
          <select class="form-control" data-idx="${idx}" data-field="degree" required>
            <option value="">-- Select Degree --</option>
            <option value="B.Sc" ${m.degree === 'B.Sc' ? 'selected' : ''}>B.Sc (Mathematics / CS / Physics / Data)</option>
            <option value="B.E / B.Tech" ${m.degree === 'B.E / B.Tech' ? 'selected' : ''}>B.E / B.Tech</option>
            <option value="BCA" ${m.degree === 'BCA' ? 'selected' : ''}>BCA</option>
            <option value="B.Com" ${m.degree === 'B.Com' ? 'selected' : ''}>B.Com</option>
            <option value="BBA" ${m.degree === 'BBA' ? 'selected' : ''}>BBA</option>
            <option value="M.Sc" ${m.degree === 'M.Sc' ? 'selected' : ''}>M.Sc (Mathematics / Computing / AI)</option>
            <option value="MCA" ${m.degree === 'MCA' ? 'selected' : ''}>MCA</option>
            <option value="M.E / M.Tech" ${m.degree === 'M.E / M.Tech' ? 'selected' : ''}>M.E / M.Tech</option>
            <option value="Other" ${m.degree === 'Other' ? 'selected' : ''}>Other</option>
          </select>
          <span class="form-hint">Degree program currently enrolled in.</span>
        </div>
        <div class="form-group">
          <label class="form-label">Year of Study <span class="required">*</span></label>
          <select class="form-control" data-idx="${idx}" data-field="year" required>
            <option value="1st Year" ${m.year === '1st Year' ? 'selected' : ''}>1st Year</option>
            <option value="2nd Year" ${m.year === '2nd Year' ? 'selected' : ''}>2nd Year</option>
            <option value="3rd Year" ${m.year === '3rd Year' || !m.year ? 'selected' : ''}>3rd Year</option>
            <option value="4th Year" ${m.year === '4th Year' ? 'selected' : ''}>4th Year</option>
            <option value="Postgraduate" ${m.year === 'Postgraduate' ? 'selected' : ''}>Postgraduate</option>
          </select>
          <span class="form-hint">Current academic year of study.</span>
        </div>
        <div class="form-group" style="grid-column: 1 / -1;">
          <label class="form-label">Department / Branch <span class="required">*</span></label>
          <input type="text" class="form-control" data-idx="${idx}" data-field="department" value="${escapeHtml(m.department || '')}" placeholder="e.g. Department of Mathematics / Computer Applications" required>
          <span class="form-hint">Academic department &amp; branch of study.</span>
        </div>
      </div>
    `;
    container.appendChild(card);
  });

  // Attach change listeners to update membersList in memory
  container.querySelectorAll('input, select').forEach(input => {
    const updateHandler = (e) => {
      const idx = parseInt(e.target.dataset.idx, 10);
      const field = e.target.dataset.field;
      if (membersList[idx] && field) {
        membersList[idx][field] = e.target.value.trim();
      }
    };
    input.addEventListener('input', updateHandler);
    input.addEventListener('change', updateHandler);
  });

  // Update counter badges
  const totalCrew = 1 + membersList.length;
  const countEl = document.getElementById('total-crew-count');
  if (countEl) countEl.textContent = `${totalCrew} / 6 UNITS`;

  const dynamicCountEl = document.getElementById('members-dynamic-count');
  if (dynamicCountEl) dynamicCountEl.textContent = membersList.length;

  const totalUnitsEl = document.getElementById('total-units-badge');
  if (totalUnitsEl) totalUnitsEl.textContent = `${totalCrew} Units`;

  const addBtn = document.getElementById('btn-add-member');
  if (addBtn) {
    if (membersList.length >= 5) {
      addBtn.disabled = true;
      addBtn.textContent = 'MAX TEAM CAPACITY REACHED (6)';
    } else {
      addBtn.disabled = false;
      addBtn.textContent = '+ ADD TEAM MEMBER (UP TO 6)';
    }
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function addMember() {
  if (membersList.length >= 5) {
    alert('Maximum squad size is 6 members (1 Leader + 5 Crew Members).');
    return;
  }
  membersList.push({
    id: membersList.length + 2,
    name: '',
    phone: '',
    email: '',
    gender: '',
    degree: '',
    department: '',
    year: '3rd Year'
  });
  renderMembersContainer();
}

function removeMember(idx) {
  if (membersList.length <= 3) {
    alert('Minimum squad size is 4 members (1 Leader + 3 Crew Members).');
    return;
  }
  membersList.splice(idx, 1);
  renderMembersContainer();
}

// Step navigation & Callsign uniqueness check
let teamNameAvailability = {
  checkedName: '',
  isChecking: false,
  isAvailable: false,
  message: ''
};
let teamNameDebounceTimer = null;

async function verifyTeamName(name, silent = false) {
  const cleanName = (name || '').trim();
  const badgeEl = document.getElementById('team-name-badge');
  const iconEl = document.getElementById('team-name-icon');
  const feedbackEl = document.getElementById('team-name-feedback');
  const defaultHintEl = document.getElementById('team-name-default-hint');
  const inputEl = document.getElementById('team_name');

  if (!cleanName) {
    teamNameAvailability = { checkedName: '', isChecking: false, isAvailable: false, message: '' };
    if (badgeEl) badgeEl.style.display = 'none';
    if (iconEl) iconEl.style.display = 'none';
    if (feedbackEl) feedbackEl.style.display = 'none';
    if (defaultHintEl) defaultHintEl.style.display = 'block';
    if (inputEl) {
      inputEl.style.borderColor = '';
      inputEl.style.boxShadow = '';
    }
    return false;
  }

  if (teamNameAvailability.checkedName.toLowerCase() === cleanName.toLowerCase() && !teamNameAvailability.isChecking) {
    return teamNameAvailability.isAvailable;
  }

  teamNameAvailability.isChecking = true;
  if (!silent) {
    if (badgeEl) {
      badgeEl.style.display = 'inline-block';
      badgeEl.style.color = '#ffd000';
      badgeEl.textContent = '[CHECKING CALLSIGN...]';
    }
    if (iconEl) {
      iconEl.style.display = 'block';
      iconEl.style.color = '#ffd000';
      iconEl.innerHTML = '&#9881;';
    }
  }

  try {
    const res = await fetch(`/api/check-team-name?name=${encodeURIComponent(cleanName)}`);
    const data = await res.json();
    teamNameAvailability.checkedName = cleanName;
    teamNameAvailability.isChecking = false;
    teamNameAvailability.isAvailable = !!data.available;
    teamNameAvailability.message = data.message || '';

    if (defaultHintEl) defaultHintEl.style.display = 'none';
    if (feedbackEl) feedbackEl.style.display = 'block';
    if (badgeEl) badgeEl.style.display = 'inline-block';
    if (iconEl) iconEl.style.display = 'block';

    if (data.available) {
      if (badgeEl) {
        badgeEl.style.color = 'var(--doom-green)';
        badgeEl.textContent = '[CALLSIGN AVAILABLE]';
      }
      if (iconEl) {
        iconEl.style.color = 'var(--doom-green)';
        iconEl.innerHTML = '&#10004;';
      }
      if (feedbackEl) {
        feedbackEl.style.color = 'var(--doom-green)';
        feedbackEl.innerHTML = `&#10004; Callsign <strong>${escapeHtml(cleanName)}</strong> is available for deployment.`;
      }
      if (inputEl) {
        inputEl.style.borderColor = 'var(--doom-green)';
        inputEl.style.boxShadow = '0 0 12px rgba(57, 255, 20, 0.3)';
      }
      return true;
    } else {
      if (badgeEl) {
        badgeEl.style.color = '#ff4444';
        badgeEl.textContent = '[CALLSIGN TAKEN]';
      }
      if (iconEl) {
        iconEl.style.color = '#ff4444';
        iconEl.innerHTML = '&#10006;';
      }
      if (feedbackEl) {
        feedbackEl.style.color = '#ff4444';
        feedbackEl.innerHTML = `&#10006; Callsign <strong>${escapeHtml(cleanName)}</strong> is already registered. Team names are unique &amp; case-insensitive. Please choose another callsign.`;
      }
      if (inputEl) {
        inputEl.style.borderColor = '#ff4444';
        inputEl.style.boxShadow = '0 0 12px rgba(255, 68, 68, 0.3)';
      }
      return false;
    }
  } catch (err) {
    console.error('Error verifying callsign:', err);
    teamNameAvailability.isChecking = false;
    return true; // Fallback to server validation
  }
}

function setupTeamNameValidator() {
  const teamNameInput = document.getElementById('team_name');
  if (!teamNameInput) return;

  teamNameInput.addEventListener('input', (e) => {
    clearTimeout(teamNameDebounceTimer);
    const val = e.target.value.trim();
    if (!val) {
      verifyTeamName('');
      return;
    }
    teamNameDebounceTimer = setTimeout(() => {
      verifyTeamName(val);
    }, 350);
  });

  teamNameInput.addEventListener('blur', (e) => {
    clearTimeout(teamNameDebounceTimer);
    const val = e.target.value.trim();
    if (val) {
      verifyTeamName(val);
    }
  });
}

// Step navigation
async function goToStep(step) {
  if (step > currentStep) {
    const isValid = await validateCurrentStep(currentStep);
    if (!isValid) return;
  }

  currentStep = step;
  document.querySelectorAll('.form-step').forEach(el => el.classList.remove('active'));
  document.getElementById(`form-step-${step}`)?.classList.add('active');

  // Update wizard progress bar
  const progressPercent = ((step - 1) / (totalSteps - 1)) * 100;
  const progressBar = document.getElementById('wizard-progress-bar');
  if (progressBar) progressBar.style.width = `${progressPercent}%`;

  document.querySelectorAll('.step-node').forEach((node, idx) => {
    const nodeStep = idx + 1;
    node.classList.remove('active', 'completed');
    if (nodeStep === step) {
      node.classList.add('active');
    } else if (nodeStep < step) {
      node.classList.add('completed');
    }
  });

  if (step === 3) {
    populateReviewSummary();
  }

  window.scrollTo({ top: 120, behavior: 'smooth' });
}

async function validateCurrentStep(step) {
  if (step === 1) {
    const teamNameInput = document.getElementById('team_name');
    const teamName = teamNameInput?.value.trim();
    const collegeName = document.getElementById('college_name')?.value.trim();
    const track = document.getElementById('track')?.value;
    const leaderName = document.getElementById('leader_name')?.value.trim();
    const leaderPhone = document.getElementById('leader_phone')?.value.trim();
    const leaderEmail = document.getElementById('leader_email')?.value.trim();

    if (!teamName) {
      alert('Please enter your Squad / Team Callsign.');
      teamNameInput?.focus();
      return false;
    }

    // Verify team name uniqueness
    const isAvailable = await verifyTeamName(teamName);
    if (!isAvailable) {
      alert(`Team callsign "${teamName}" is already reserved by another squad.\n\nSquad names must be strictly unique (case-insensitive). Please enter a different team callsign.`);
      teamNameInput?.focus();
      return false;
    }

    if (!collegeName) {
      alert('Please enter your College / Institution Name.');
      document.getElementById('college_name')?.focus();
      return false;
    }
    if (!track) {
      alert('Please select an Operational Quantum Track.');
      document.getElementById('track')?.focus();
      return false;
    }
    if (!leaderName) {
      alert('Please enter the Team Leader Full Name.');
      document.getElementById('leader_name')?.focus();
      return false;
    }
    if (!leaderPhone || leaderPhone.length < 10) {
      alert('Please provide a valid 10-digit Mobile Number for the Team Leader.');
      document.getElementById('leader_phone')?.focus();
      return false;
    }
    if (!leaderEmail || !leaderEmail.includes('@')) {
      alert('Please provide a valid Email Address for the Team Leader.');
      document.getElementById('leader_email')?.focus();
      return false;
    }

    const leaderDegree = document.getElementById('leader_degree')?.value;
    const leaderDepartment = document.getElementById('leader_department')?.value.trim();
    const leaderGender = document.getElementById('leader_gender')?.value;

    if (!leaderDegree) {
      alert('Please select Degree for the Team Leader.');
      document.getElementById('leader_degree')?.focus();
      return false;
    }
    if (!leaderGender) {
      alert('Please select Gender for the Team Leader.');
      document.getElementById('leader_gender')?.focus();
      return false;
    }
    if (!leaderDepartment) {
      alert('Please enter Department / Branch for the Team Leader.');
      document.getElementById('leader_department')?.focus();
      return false;
    }
  } else if (step === 2) {
    const leaderEmail = document.getElementById('leader_email')?.value.trim().toLowerCase() || '';
    const allEmails = [leaderEmail];

    for (let i = 0; i < membersList.length; i++) {
      const m = membersList[i];
      const memberNum = i + 2;
      if (!m.name) {
        alert(`Please enter Full Name for Crew Member #${memberNum}.`);
        return false;
      }
      if (!m.phone || m.phone.length < 10) {
        alert(`Please enter a valid 10-digit Mobile Number for Crew Member #${memberNum}.`);
        return false;
      }
      if (!m.email || !m.email.includes('@')) {
        alert(`Please enter a valid Email ID for Crew Member #${memberNum}.`);
        return false;
      }
      if (allEmails.includes(m.email.toLowerCase())) {
        alert(`Duplicate email detected: "${m.email}". Every team member must have a distinct email address.`);
        return false;
      }
      allEmails.push(m.email.toLowerCase());

      if (!m.gender) {
        alert(`Please select Gender for Crew Member #${memberNum}.`);
        return false;
      }
      if (!m.degree) {
        alert(`Please select Degree for Crew Member #${memberNum}.`);
        return false;
      }
      if (!m.department) {
        alert(`Please enter Department / Branch for Crew Member #${memberNum}.`);
        return false;
      }
    }
  }
  return true;
}

function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function handleFileSelection(file) {
  const errorEl = document.getElementById('file-error-msg');
  const labelEl = document.getElementById('file-upload-label');
  const infoEl = document.getElementById('file-upload-info');
  const dropZone = document.getElementById('file-drop-zone');

  if (!file) return;

  const validExtensions = ['.ppt', '.pptx', '.pdf'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();

  if (!validExtensions.includes(ext)) {
    if (errorEl) {
      errorEl.textContent = 'Invalid file format. Please upload a .pptx, .ppt, or .pdf presentation file.';
      errorEl.style.display = 'block';
    }
    dropZone?.classList.remove('has-file');
    selectedPptFile = null;
    return;
  }

  // 10MB limit
  const maxBytes = 10 * 1024 * 1024;
  if (file.size > maxBytes) {
    if (errorEl) {
      errorEl.textContent = `File size (${formatBytes(file.size)}) exceeds the maximum allowed limit of 10MB.`;
      errorEl.style.display = 'block';
    }
    dropZone?.classList.remove('has-file');
    selectedPptFile = null;
    return;
  }

  if (errorEl) errorEl.style.display = 'none';
  selectedPptFile = file;

  if (labelEl) labelEl.textContent = `Attached: ${file.name}`;
  if (infoEl) infoEl.textContent = `Size: ${formatBytes(file.size)} • Ready for upload`;
  dropZone?.classList.add('has-file');
}

function setupCharacterCounters() {
  const counters = [
    { inputId: 'idea_title', counterId: 'char-count-title', max: 100 },
    { inputId: 'idea_summary', counterId: 'char-count-summary', max: 10000 },
    { inputId: 'idea_description', counterId: 'char-count-desc', max: 50000 }
  ];

  counters.forEach(({ inputId, counterId, max }) => {
    const input = document.getElementById(inputId);
    const counter = document.getElementById(counterId);
    if (!input || !counter) return;

    const updateCount = () => {
      const len = input.value.length;
      counter.textContent = `${len.toLocaleString()} / ${max.toLocaleString()} characters`;
      counter.classList.remove('limit-near', 'limit-reached');
      if (len >= max) {
        counter.classList.add('limit-reached');
      } else if (len >= max * 0.9) {
        counter.classList.add('limit-near');
      }
    };

    input.addEventListener('input', updateCount);
    updateCount();
  });
}

function setupFileUpload() {
  const dropZone = document.getElementById('file-drop-zone');
  const fileInput = document.getElementById('idea_ppt');
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener('click', (e) => {
    if (e.target !== fileInput) {
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0]);
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
      fileInput.files = e.dataTransfer.files;
    }
  });
}

function populateReviewSummary() {
  document.getElementById('sum-team-name').textContent = document.getElementById('team_name')?.value || '-';
  document.getElementById('sum-college').textContent = document.getElementById('college_name')?.value || '-';
  document.getElementById('sum-track').textContent = document.getElementById('track')?.value || '-';
  
  const leaderName = document.getElementById('leader_name')?.value || '-';
  const leaderPhone = document.getElementById('leader_phone')?.value || '';
  const leaderEmail = document.getElementById('leader_email')?.value || '';
  const leaderDegree = document.getElementById('leader_degree')?.value || '';
  const leaderDept = document.getElementById('leader_department')?.value || '';
  const leaderGender = document.getElementById('leader_gender')?.value || '';

  let leaderDetails = leaderName;
  const tagParts = [];
  if (leaderDegree) tagParts.push(leaderDegree);
  if (leaderDept) tagParts.push(leaderDept);
  if (leaderGender) tagParts.push(leaderGender);
  if (tagParts.length > 0) {
    leaderDetails += ` [${tagParts.join(' • ')}]`;
  }
  if (leaderPhone || leaderEmail) {
    leaderDetails += ` (${[leaderPhone, leaderEmail].filter(Boolean).join(' | ')})`;
  }
  document.getElementById('sum-leader').textContent = leaderDetails;
  document.getElementById('sum-crew-size').textContent = `${1 + membersList.length} Units (Leader + ${membersList.length} Crew)`;

  // Update dynamic UPI payment mobile deep link
  const teamName = document.getElementById('team_name')?.value || 'TEAM';
  const deepLink = document.getElementById('btn-upi-mobile-pay');
  if (deepLink) {
    const upiId = document.getElementById('upi-id-text')?.textContent || 'karanvasi80@okhdfcbank';
    const payee = document.getElementById('upi-payee-name')?.textContent || 'Vasikaran A';
    deepLink.href = `upi://pay?pa=${encodeURIComponent(upiId.trim())}&pn=${encodeURIComponent(payee.trim())}&am=150&cu=INR&tn=${encodeURIComponent('QYRON27 ' + teamName)}`;
  }
}

// Copy UPI ID helper function with tactile UI feedback
function copyUpiId() {
  const upiText = document.getElementById('upi-id-text')?.textContent || 'karanvasi80@okhdfcbank';
  navigator.clipboard.writeText(upiText.trim()).then(() => {
    const btn = document.getElementById('btn-copy-upi');
    if (btn) {
      const origText = btn.textContent;
      btn.textContent = 'COPIED ✓';
      btn.style.color = '#050706';
      btn.style.background = 'var(--doom-green)';
      setTimeout(() => {
        btn.textContent = origText;
        btn.style.color = 'var(--doom-green)';
        btn.style.background = 'rgba(57,255,20,0.15)';
      }, 2500);
    }
  }).catch(() => {
    alert('Official UPI ID: ' + upiText);
  });
}

// Submitting Registration & Initiating UPI Verification
async function initiateRegistrationAndPayment() {
  const utrInput = document.getElementById('upi_utr_number');
  const utrVal = utrInput ? utrInput.value.trim() : '';

  if (!utrVal) {
    alert('Please enter the 12-digit UPI Reference Number / UTR from your payment app.');
    if (utrInput) utrInput.focus();
    return;
  }
  if (utrVal.length < 6) {
    alert('Please enter a valid UPI Reference / UTR Number (usually 12 digits).');
    if (utrInput) utrInput.focus();
    return;
  }

  const payBtn = document.getElementById('btn-proceed-pay');
  payBtn.disabled = true;
  payBtn.textContent = 'VERIFYING UPI PAYMENT & DISPATCHING CREDENTIALS...';

  const formData = new FormData();
  formData.append('team_name', document.getElementById('team_name').value.trim());
  formData.append('college_name', document.getElementById('college_name').value.trim());
  formData.append('track', document.getElementById('track').value);

  formData.append('leader_name', document.getElementById('leader_name').value.trim());
  formData.append('leader_phone', document.getElementById('leader_phone').value.trim());
  formData.append('leader_email', document.getElementById('leader_email').value.trim());
  formData.append('leader_college', document.getElementById('college_name').value.trim());
  formData.append('leader_degree', document.getElementById('leader_degree')?.value || '');
  formData.append('leader_department', document.getElementById('leader_department')?.value.trim() || 'General');
  formData.append('leader_year', document.getElementById('leader_year')?.value || '3rd Year');
  formData.append('leader_gender', document.getElementById('leader_gender')?.value || '');

  // Members as JSON string
  formData.append('members', JSON.stringify(membersList));

  // Atomic Registration: Pass UTR & Payment Screenshot directly in the single registration request
  formData.append('utr_number', utrVal);
  const screenshotInput = document.getElementById('upi_payment_screenshot');
  if (screenshotInput && screenshotInput.files && screenshotInput.files[0]) {
    formData.append('payment_screenshot', screenshotInput.files[0]);
  }

  try {
    const res = await fetch('/api/register', {
      method: 'POST',
      body: formData
    });

    let data;
    try {
      data = await res.json();
    } catch (parseErr) {
      alert(`Server transmission error (${res.status}). Please check network or try again.`);
      payBtn.disabled = false;
      payBtn.textContent = 'CONFIRM UPI PAYMENT & RECEIVE CREDENTIALS ►';
      return;
    }

    if (!res.ok || !data.success) {
      alert(data.message || 'Registration failed. Please check form data.');
      payBtn.disabled = false;
      payBtn.textContent = 'CONFIRM UPI PAYMENT & RECEIVE CREDENTIALS ►';
      if (data.message && (data.message.toLowerCase().includes('callsign') || data.message.toLowerCase().includes('team name'))) {
        goToStep(1);
        const nameInput = document.getElementById('team_name');
        if (nameInput) {
          nameInput.focus();
          verifyTeamName(nameInput.value);
        }
      }
      return;
    }

    const teamCode = data.team_code;

    // Single-Request Atomic Registration Success (No secondary roundtrip required!)
    if (data.redirect_url) {
      try {
        const cached = {
          team_code: teamCode,
          portal_username: data.username || formData.get('leader_email'),
          portal_password: data.password,
          utr_number: utrVal,
          payment_status: 'pending_verification',
          leader_name: formData.get('leader_name'),
          leader_email: formData.get('leader_email'),
          leader_phone: formData.get('leader_phone'),
          team_name: formData.get('team_name'),
          track: formData.get('track'),
          college_name: formData.get('college_name')
        };
        sessionStorage.setItem('last_qyron_reg', JSON.stringify(cached));
      } catch(e) {}
      window.location.href = data.redirect_url;
      return;
    }

    const order = data.order || {};

    // Fallback: Verify UPI Payment with UTR and fallback squad fields for serverless lambdas
    const verifyFormData = new FormData();
    verifyFormData.append('team_code', teamCode);
    verifyFormData.append('utr_number', utrVal);
    verifyFormData.append('order_id', order.order_id || `order_${teamCode}`);
    verifyFormData.append('team_name', formData.get('team_name'));
    verifyFormData.append('college_name', formData.get('college_name'));
    verifyFormData.append('track', formData.get('track'));
    verifyFormData.append('leader_name', formData.get('leader_name'));
    verifyFormData.append('leader_email', formData.get('leader_email'));
    verifyFormData.append('leader_phone', formData.get('leader_phone'));
    verifyFormData.append('leader_degree', formData.get('leader_degree') || '');
    verifyFormData.append('leader_department', formData.get('leader_department') || '');
    verifyFormData.append('leader_gender', formData.get('leader_gender') || '');
    verifyFormData.append('members', formData.get('members'));

    if (screenshotInput && screenshotInput.files && screenshotInput.files[0]) {
      verifyFormData.append('payment_screenshot', screenshotInput.files[0]);
    }

    const verifyRes = await fetch('/api/payment/verify', {
      method: 'POST',
      body: verifyFormData
    });

    let verifyData;
    try {
      verifyData = await verifyRes.json();
    } catch (e) {
      verifyData = { success: false, message: 'Invalid response from verification server.' };
    }

    if (verifyRes.ok && verifyData.success) {
      try {
        const cached = {
          team_code: teamCode,
          portal_username: verifyData.username || formData.get('leader_email'),
          portal_password: verifyData.password,
          utr_number: utrVal,
          payment_status: 'pending_verification',
          leader_name: formData.get('leader_name'),
          leader_email: formData.get('leader_email'),
          leader_phone: formData.get('leader_phone'),
          team_name: formData.get('team_name'),
          track: formData.get('track'),
          college_name: formData.get('college_name')
        };
        sessionStorage.setItem('last_qyron_reg', JSON.stringify(cached));
      } catch(e) {}
      window.location.href = verifyData.redirect_url || `/confirmation?team_code=${teamCode}`;
    } else {
      alert(verifyData.message || 'Payment verification could not be recorded.');
      payBtn.disabled = false;
      payBtn.textContent = 'CONFIRM UPI PAYMENT & RECEIVE CREDENTIALS ►';
    }

  } catch (err) {
    console.error(err);
    alert('Network error connecting to verification gateway. Please try again.');
    payBtn.disabled = false;
    payBtn.textContent = 'CONFIRM UPI PAYMENT & RECEIVE CREDENTIALS ►';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  renderMembersContainer();
  setupCharacterCounters();
  setupFileUpload();
  setupTeamNameValidator();

  const addBtn = document.getElementById('btn-add-member');
  if (addBtn) {
    addBtn.addEventListener('click', addMember);
  }

  const payBtn = document.getElementById('btn-proceed-pay');
  if (payBtn) {
    payBtn.addEventListener('click', initiateRegistrationAndPayment);
  }
});
