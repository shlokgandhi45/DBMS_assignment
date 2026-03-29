'use strict';

/**
 * script.js — DBMS Normalization Tool Frontend
 * =============================================
 * Sections:
 *   1. Configuration
 *   2. DOM References
 *   3. Default Values
 *   4. Utility Functions
 *   5. API Call Functions
 *   6. Render Functions
 *   7. Normalization Tab Logic
 *   8. Input Validation
 *   9. Event Listeners
 *  10. Initialization
 */


/* ============================================================
   1. CONFIGURATION
   ============================================================ */

/** Base URL for all backend API calls. */
const API_BASE = 'http://127.0.0.1:5000';


/* ============================================================
   2. DOM REFERENCES
   ============================================================ */

// Inputs
const schemaInput   = document.getElementById('schema-input');
const fdInput       = document.getElementById('fd-input');
const attrsInput    = document.getElementById('attrs-input');

// Buttons
const btnClosure    = document.getElementById('btn-closure');
const btnKeys       = document.getElementById('btn-candidate-keys');
const btnNormalize  = document.getElementById('btn-normalize');
const btnClear      = document.getElementById('btn-clear');
const btnErrorClose = document.getElementById('error-banner-close');

// Error banner
const errorBanner   = document.getElementById('error-banner');
const errorBannerMsg= document.getElementById('error-banner-message');

// Spinner & Toast
const spinnerContainer = document.getElementById('spinner-container');
const toastContainer   = document.getElementById('toast-container');

// Slide Panel
const slidePanel    = document.getElementById('slide-panel');
const panelOverlay  = document.getElementById('panel-overlay');
const panelTitle    = document.getElementById('panel-title');
const btnClosePanel = document.getElementById('btn-close-panel');

// Result cards
const closureCard   = document.getElementById('closure-card');
const keysCard      = document.getElementById('keys-card');
const normCard      = document.getElementById('norm-card');

// Closure card internals
const closureBadge        = document.getElementById('closure-badge');
const closureInputDisplay = document.getElementById('closure-input-display');
const closureSteps        = document.getElementById('closure-steps');
const closureResultRow    = document.getElementById('closure-result-row');

// Keys card internals
const keysCandidate = document.getElementById('keys-candidate');
const keysPrime     = document.getElementById('keys-prime');
const keysNonPrime  = document.getElementById('keys-non-prime');

// Normalization tab buttons & panels
const tabButtons = {
  '2NF':  document.getElementById('tab-btn-2NF'),
  '3NF':  document.getElementById('tab-btn-3NF'),
  'BCNF': document.getElementById('tab-btn-BCNF'),
};
const tabPanels = {
  '2NF':  document.getElementById('tab-panel-2NF'),
  '3NF':  document.getElementById('tab-panel-3NF'),
  'BCNF': document.getElementById('tab-panel-BCNF'),
};


/* ============================================================
   3. DEFAULT VALUES (pre-populated on load)
   ============================================================ */

const DEFAULT_SCHEMA = 'R(BookingID, CustomerID, Name, Phone, BikeID, Model, CategoryID, CategoryName, StartDate, EndDate, PaymentID, Amount)';

const DEFAULT_FDS = [
  'BookingID -> CustomerID, BikeID, StartDate, EndDate',
  'CustomerID -> Name, Phone',
  'BikeID -> Model, CategoryID',
  'CategoryID -> CategoryName',
  'PaymentID -> BookingID, Amount',
].join('\n');

const DEFAULT_ATTRS = 'BookingID';


/* ============================================================
   4. UTILITY FUNCTIONS
   ============================================================ */

/**
 * Show the loading spinner and hide all result cards.
 */
function showSpinner() {
  spinnerContainer.hidden = false;
  closureCard.hidden = true;
  keysCard.hidden    = true;
  normCard.hidden    = true;
  btnClosure.disabled = true;
  btnKeys.disabled = true;
  btnNormalize.disabled = true;
}

/**
 * Hide the loading spinner.
 */
function hideSpinner() {
  spinnerContainer.hidden = true;
  btnClosure.disabled = false;
  btnKeys.disabled = false;
  btnNormalize.disabled = false;
}

/**
 * Display the global error banner with the given message.
 * @param {string} message - User-facing error text.
 */
function showError(message) {
  errorBannerMsg.textContent = message;
  errorBanner.hidden = false;
  errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Hide the global error banner.
 */
function hideError() {
  errorBanner.hidden = true;
  errorBannerMsg.textContent = '';
}

/**
 * Show a generic toast notification.
 * @param {string} message - Display message.
 * @param {string} type    - e.g. 'success', 'warning'
 */
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === 'success' ? '✓' : '⚠'}</span>
    <span>${escapeHtml(message)}</span>
  `;
  toastContainer.appendChild(toast);

  // Remove after 3 seconds
  setTimeout(() => {
    toast.classList.add('toast-closing');
    toast.addEventListener('animationend', () => toast.remove());
  }, 3000);
}

/**
 * Open the slide panel with a specific title.
 * @param {string} title - The title to display in the panel header.
 */
function openPanel(title) {
  panelTitle.textContent = title;
  slidePanel.classList.add('active');
  panelOverlay.classList.add('active');
  document.body.style.overflow = 'hidden';
}

/**
 * Close the slide panel.
 */
function closePanel() {
  slidePanel.classList.remove('active');
  panelOverlay.classList.remove('active');
  document.body.style.overflow = '';
}

/**
 * Clear all result card contents and hide them.
 */
function clearResults() {
  closePanel();
  closureCard.hidden = true;
  keysCard.hidden    = true;
  normCard.hidden    = true;

  closureSteps.innerHTML    = '';
  closureResultRow.innerHTML = '';
  closureBadge.innerHTML    = '';
  closureBadge.className    = 'result-badge';
  closureInputDisplay.innerHTML = '';

  keysCandidate.innerHTML = '';
  keysPrime.innerHTML     = '';
  keysNonPrime.innerHTML  = '';

  Object.values(tabPanels).forEach(panel => { panel.innerHTML = ''; });
}

/**
 * Trigger a CSS fade-in animation on an element by toggling a class.
 * @param {HTMLElement} el - The element to animate.
 */
function fadeInElement(el) {
  el.style.animation = 'none';
  // Force reflow
  void el.offsetHeight;
  el.style.animation = '';
  el.classList.add('result-card');
}

/**
 * Escape dangerous HTML characters to prevent XSS.
 * @param {string} str - Raw string.
 * @returns {string} HTML-escaped string.
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Build a pill/badge HTML element string.
 * @param {string} text  - Label text.
 * @param {string} style - CSS modifier class suffix (key, prime, non-prime, attr, pk).
 * @returns {string} HTML string for a <span class="pill pill--X"> element.
 */
function makePill(text, style) {
  return `<span class="pill pill--${escapeHtml(style)}">${escapeHtml(text)}</span>`;
}

/**
 * Build an alert box HTML string.
 * @param {string}   type    - 'already' | 'violation' | 'warning'
 * @param {string}   icon    - Emoji or character icon.
 * @param {string}   title   - Alert heading.
 * @param {string[]} items   - Optional list of detail strings.
 * @returns {string} HTML string.
 */
function makeAlert(type, icon, title, items = []) {
  const listHtml = items.length
    ? `<ul class="alert-list">${items.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>`
    : '';
  return `
    <div class="alert alert--${escapeHtml(type)}">
      <span class="alert-icon">${icon}</span>
      <div class="alert-content">
        <div class="alert-title">${escapeHtml(title)}</div>
        ${listHtml}
      </div>
    </div>`;
}


/* ============================================================
   5. API CALL FUNCTIONS
   ============================================================ */

/**
 * Compute the attribute closure via the backend.
 *
 * @param {string}   schema     - Schema string (e.g. "R(A,B,C)").
 * @param {string[]} fds        - Array of FD strings.
 * @param {string[]} attributes - Starting attribute array.
 * @returns {Promise<object|null>} Parsed JSON response or null on error.
 */
async function fetchClosure(schema, fds, attributes) {
  showSpinner();
  try {
    const response = await fetch(`${API_BASE}/closure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema, fds, attributes }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      showError(data.error || `Server error (HTTP ${response.status}). Check backend logs.`);
      return null;
    }
    return data;
  } catch (err) {
    console.error('fetchClosure error:', err);
    showError('Cannot connect to backend. Make sure Flask is running on port 5000.');
    return null;
  } finally {
    hideSpinner();
  }
}

/**
 * Find all candidate keys via the backend.
 *
 * @param {string}   schema - Schema string.
 * @param {string[]} fds    - Array of FD strings.
 * @returns {Promise<object|null>} Parsed JSON response or null on error.
 */
async function fetchCandidateKeys(schema, fds) {
  showSpinner();
  try {
    const response = await fetch(`${API_BASE}/candidate-keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema, fds }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      showError(data.error || `Server error (HTTP ${response.status}). Check backend logs.`);
      return null;
    }
    return data;
  } catch (err) {
    console.error('fetchCandidateKeys error:', err);
    showError('Cannot connect to backend. Make sure Flask is running on port 5000.');
    return null;
  } finally {
    hideSpinner();
  }
}

/**
 * Decompose the relation into 2NF, 3NF, and BCNF via the backend.
 *
 * @param {string}   schema - Schema string.
 * @param {string[]} fds    - Array of FD strings.
 * @returns {Promise<object|null>} Parsed JSON response or null on error.
 */
async function fetchNormalize(schema, fds) {
  showSpinner();
  try {
    const response = await fetch(`${API_BASE}/normalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema, fds, target: 'ALL' }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      showError(data.error || `Server error (HTTP ${response.status}). Check backend logs.`);
      return null;
    }
    return data;
  } catch (err) {
    console.error('fetchNormalize error:', err);
    showError('Cannot connect to backend. Make sure Flask is running on port 5000.');
    return null;
  } finally {
    hideSpinner();
  }
}


/* ============================================================
   6. RENDER FUNCTIONS
   ============================================================ */

/**
 * Render the closure computation result into the closure card.
 *
 * @param {object} data - The success response JSON from POST /closure.
 */
function renderClosure(data) {
  // Clear first
  closureSteps.innerHTML     = '';
  closureResultRow.innerHTML = '';

  // Show input
  const inputStr = `{${data.input_attributes.join(', ')}}`;
  closureInputDisplay.textContent = `Computing closure of ${inputStr}`;

  // Badge
  if (data.determines_all) {
    closureBadge.classList.add('result-badge--success');
    closureBadge.textContent = '✓ Determines entire schema';
  } else {
    closureBadge.classList.add('result-badge--warning');
    closureBadge.textContent = '⚠ Partial closure';
  }

  // Steps list
  data.steps.forEach(step => {
    const li = document.createElement('li');
    li.textContent = step;
    closureSteps.appendChild(li);
  });

  // Final closure set
  const closureStr = `{${data.closure.join(', ')}}`;
  closureResultRow.innerHTML = `
    <span class="result-badge ${data.determines_all ? 'result-badge--success' : 'result-badge--warning'}">
      ${data.determines_all ? '✓ Complete' : '⚠ Incomplete'}
    </span>
    <div class="closure-final-set">Closure: ${escapeHtml(closureStr)}</div>
  `;

  closureCard.hidden = false;
  fadeInElement(closureCard);
  openPanel('Attribute Closure Result');
  showToast('Closure computed successfully!');
}

/**
 * Render the candidate keys result into the keys card.
 *
 * @param {object} data - The success response JSON from POST /candidate-keys.
 */
function renderCandidateKeys(data) {
  keysCandidate.innerHTML = '';
  keysPrime.innerHTML     = '';
  keysNonPrime.innerHTML  = '';

  // Candidate keys — one pill per key (which may be multi-attribute)
  data.candidate_keys.forEach(keyArr => {
    const keyLabel = `{${keyArr.join(', ')}}`;
    keysCandidate.insertAdjacentHTML('beforeend', makePill(keyLabel, 'key'));
  });

  // Prime attributes — individual pills
  data.prime_attributes.forEach(attr => {
    keysPrime.insertAdjacentHTML('beforeend', makePill(attr, 'prime'));
  });

  // Non-prime attributes — individual pills
  data.non_prime_attributes.forEach(attr => {
    keysNonPrime.insertAdjacentHTML('beforeend', makePill(attr, 'non-prime'));
  });

  keysCard.hidden = false;
  fadeInElement(keysCard);
  openPanel('Candidate Keys Result');
  showToast('Candidate keys discovered successfully!');
}

/**
 * Build the HTML for a single decomposed relation card.
 *
 * @param {object} relation - A relation dict with name, attributes, primary_key, fds.
 * @returns {string} HTML string for the relation card.
 */
function renderRelationCard(relation) {
  const pkSet = new Set(relation.primary_key);

  // Attributes: PK attrs highlighted, non-PK as gray
  const attrPills = relation.attributes
    .map(attr => makePill(attr, pkSet.has(attr) ? 'pk' : 'attr'))
    .join('');

  // FDs
  const fdLines = relation.fds.map(fd => {
    const lhs = fd.lhs.join(', ');
    const rhs = fd.rhs.join(', ');
    return `<div class="rel-fd-item">${escapeHtml(lhs)} → ${escapeHtml(rhs)}</div>`;
  }).join('') || '<div class="rel-fd-item">(none)</div>';

  return `
    <article class="rel-card">
      <div class="rel-card-header">
        <span class="rel-name">${escapeHtml(relation.name)}</span>
        <span class="pill pill--pk" style="font-size:10px;padding:2px 8px;">PK: {${escapeHtml(relation.primary_key.join(', '))}}</span>
      </div>
      <div>
        <div class="rel-section-label">Attributes (${relation.attributes.length})</div>
        <div class="rel-attrs">${attrPills}</div>
      </div>
      <div>
        <div class="rel-section-label">Functional Dependencies</div>
        <div class="rel-fds">${fdLines}</div>
      </div>
    </article>`;
}

/**
 * Render a single normal-form tab panel (2NF, 3NF, or BCNF).
 *
 * @param {HTMLElement} panel   - The tab panel DOM element.
 * @param {object}      nfData  - The normal form data object from the API.
 * @param {string}      nfLabel - "2NF", "3NF", or "BCNF".
 */
function renderNFPanel(panel, nfData, nfLabel) {
  let html = '';

  // Already satisfied?
  if (nfData.already_satisfied) {
    html += makeAlert(
      'already',
      '✓',
      `Relation is already in ${nfLabel}. No decomposition required.`
    );
  } else {
    // Violations
    if (nfData.violations && nfData.violations.length > 0) {
      html += makeAlert(
        'violation',
        '✕',
        `${nfData.violations.length} ${nfLabel} violation${nfData.violations.length > 1 ? 's' : ''} detected:`,
        nfData.violations
      );
    }

    // BCNF FD preservation warning
    if (nfData.fd_preservation_warning) {
      html += makeAlert(
        'warning',
        '⚠',
        'Dependency Preservation Warning',
        [nfData.fd_preservation_warning]
      );
    }
  }

  // Relations grid
  if (nfData.relations && nfData.relations.length > 0) {
    const count = nfData.relations.length;
    html += `
      <div class="relations-count-badge">
        Decomposed into <span class="count">${count}</span> relation${count !== 1 ? 's' : ''}
      </div>
      <div class="relations-grid">
        ${nfData.relations.map(renderRelationCard).join('')}
      </div>`;
  }

  panel.innerHTML = html;
}

/**
 * Render the full normalization result (all 3 tabs).
 *
 * @param {object} data - The success response JSON from POST /normalize.
 */
function renderNormalization(data) {
  const results = data.results;

  if (results['2NF'])  renderNFPanel(tabPanels['2NF'],  results['2NF'],  '2NF');
  if (results['3NF'])  renderNFPanel(tabPanels['3NF'],  results['3NF'],  '3NF');
  if (results['BCNF']) renderNFPanel(tabPanels['BCNF'], results['BCNF'], 'BCNF');

  normCard.hidden = false;
  fadeInElement(normCard);
  openPanel('Normalization Result');
  showToast('Normalization decomposed successfully!');

  // Default to 3NF tab
  switchTab('3NF');
}


/* ============================================================
   7. NORMALIZATION TAB LOGIC
   ============================================================ */

/**
 * Switch the active normalization tab.
 *
 * @param {string} targetNF - "2NF", "3NF", or "BCNF".
 */
function switchTab(targetNF) {
  Object.entries(tabButtons).forEach(([nf, btn]) => {
    const isActive = nf === targetNF;
    btn.classList.toggle('tab-btn--active', isActive);
    btn.setAttribute('aria-selected', String(isActive));
  });
  Object.entries(tabPanels).forEach(([nf, panel]) => {
    panel.hidden = nf !== targetNF;
  });
}


/* ============================================================
   8. INPUT VALIDATION
   ============================================================ */

/**
 * Validate schema and FD inputs before any API call.
 * Calls showError() and returns false if validation fails.
 *
 * @param {boolean} requireAttrs - Whether closure-specific attrs field is required.
 * @returns {boolean} True if all inputs are valid.
 */
function validateInputs(requireAttrs = false) {
  const schema = schemaInput.value.trim();
  const fdsRaw = fdInput.value.trim();
  const attrs  = attrsInput.value.trim();

  if (!schema) {
    showError('Schema is required. Please enter a relation schema like R(A, B, C).');
    return false;
  }

  // Rough pattern: WORD(anything)
  if (!/^\w+\(.+\)\s*$/.test(schema)) {
    showError('Schema format is invalid. Expected format: RelationName(Attr1, Attr2, …).');
    return false;
  }

  if (!fdsRaw) {
    showError('Functional Dependencies are required. Enter at least one FD per line.');
    return false;
  }

  const fdLines = fdsRaw.split('\n').map(l => l.trim()).filter(Boolean);
  const hasArrow = fdLines.some(line => line.includes('->'));
  if (!hasArrow) {
    showError('No valid FD found. Each functional dependency must contain "->" (e.g. "A -> B, C").');
    return false;
  }

  if (requireAttrs) {
    if (!attrs) {
      showError('Attributes for closure are required. Enter a comma-separated list (e.g. "BookingID").');
      return false;
    }
  }

  return true;
}

/**
 * Parse the FD textarea into a clean array of non-empty FD strings.
 * @returns {string[]}
 */
function parseFdLines() {
  return fdInput.value
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0 && l.includes('->'));
}


/* ============================================================
   9. EVENT LISTENERS
   ============================================================ */

// ── Compute Closure ────────────────────────────────────────────────────────
btnClosure.addEventListener('click', async () => {
  hideError();
  if (!validateInputs(true)) return;

  const schema = schemaInput.value.trim();
  const fds    = parseFdLines();
  const attrs  = attrsInput.value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);

  if (!fds.length) {
    showError('No valid FDs found. Ensure each FD contains "->".');
    return;
  }

  const data = await fetchClosure(schema, fds, attrs);
  if (data) renderClosure(data);
});

// ── Find Candidate Keys ────────────────────────────────────────────────────
btnKeys.addEventListener('click', async () => {
  hideError();
  if (!validateInputs(false)) return;

  const schema = schemaInput.value.trim();
  const fds    = parseFdLines();

  if (!fds.length) {
    showError('No valid FDs found. Ensure each FD contains "->".');
    return;
  }

  const data = await fetchCandidateKeys(schema, fds);
  if (data) renderCandidateKeys(data);
});

// ── Normalize ─────────────────────────────────────────────────────────────
btnNormalize.addEventListener('click', async () => {
  hideError();
  if (!validateInputs(false)) return;

  const schema = schemaInput.value.trim();
  const fds    = parseFdLines();

  if (!fds.length) {
    showError('No valid FDs found. Ensure each FD contains "->".');
    return;
  }

  const data = await fetchNormalize(schema, fds);
  if (data) renderNormalization(data);
});

// ── Clear Results ─────────────────────────────────────────────────────────
btnClear.addEventListener('click', () => {
  clearResults();
  hideError();
});

// ── Slide Panel Close ─────────────────────────────────────────────────────
btnClosePanel.addEventListener('click', closePanel);
panelOverlay.addEventListener('click', closePanel);

// ── Dismiss Error banner ───────────────────────────────────────────────────
btnErrorClose.addEventListener('click', hideError);

// ── Tab switching ─────────────────────────────────────────────────────────
Object.entries(tabButtons).forEach(([nf, btn]) => {
  btn.addEventListener('click', () => switchTab(nf));
});


/* ============================================================
   10. INITIALIZATION
   ============================================================ */

/**
 * Run on DOMContentLoaded — pre-populate all input fields with demo data
 * and set the default active normalization tab.
 */
document.addEventListener('DOMContentLoaded', () => {
  // Pre-populate inputs
  schemaInput.value = DEFAULT_SCHEMA;
  fdInput.value     = DEFAULT_FDS;
  attrsInput.value  = DEFAULT_ATTRS;

  // Default tab
  switchTab('3NF');
});
