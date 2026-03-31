'use strict';

/* ============================================================
   1. CONFIGURATION
   ============================================================ */
const API_BASE = "http://127.0.0.1:5001";
const API_FALLBACK = "http://127.0.0.1:5000";

/* ============================================================
   2. DOM REFERENCES
   ============================================================ */
// Forms & Inputs
const closureSchema = document.getElementById('closure-schema');
const closureFds    = document.getElementById('closure-fds');
const closureAttrs  = document.getElementById('closure-attrs');

const keysSchema    = document.getElementById('keys-schema');
const keysFds       = document.getElementById('keys-fds');

const normSchema    = document.getElementById('norm-schema');
const normFds       = document.getElementById('norm-fds');

// Bike quick entry (frontend only)
const bikeModelInput    = document.getElementById('bike-model');
const bikeCategoryInput = document.getElementById('bike-category');
const btnAddBike        = document.getElementById('btn-add-bike');
const bikeList          = document.getElementById('bike-list');
const btnClearBike      = document.getElementById('btn-clear-bike');
const btnClearGarage    = document.getElementById('btn-clear-garage');

// Dashboard bike state targets (with required IDs if present)
const garageListEl   = document.getElementById('garage-list') || bikeList;
const statTotalBikes = document.getElementById('stat-total-bikes') 
  || document.querySelector('.bike-metric-card .metric-value') 
  || null;

// Buttons
const btnClosure       = document.getElementById('btn-closure');
const btnClearClosure  = document.getElementById('btn-clear-closure');
const btnKeys          = document.getElementById('btn-candidate-keys');
const btnClearKeys     = document.getElementById('btn-clear-keys');
const btnNormalize     = document.getElementById('btn-normalize');
const btnClearNorm     = document.getElementById('btn-clear-norm');

// Dashboard DBMS launch buttons
const btnOpenClosurePanel   = document.getElementById('btn-open-closure-panel');
const btnOpenKeysPanel      = document.getElementById('btn-open-keys-panel');
const btnOpenNormalizePanel = document.getElementById('btn-open-normalize-panel');

// UI Elements
const spinnerContainer = document.getElementById('spinner-container');
const toastContainer = document.getElementById('toast-container');
const backendStatusBadge = document.getElementById('backend-status-badge');

// Slide Panel
const slidePanel    = document.getElementById('slide-panel');
const panelOverlay  = document.getElementById('panel-overlay');
const panelTitle    = document.getElementById('panel-title');
const panelContent  = document.getElementById('panel-content');
const btnClosePanel = document.getElementById('btn-close-panel');

/* ============================================================
   3. DEFAULT VALUES
   ============================================================ */
const DEFAULT_SCHEMA = 'Customer(CustomerID, Name, PhoneNumbers, City, Zip, State)';
const DEFAULT_FDS = 'CustomerID -> Name, PhoneNumbers, City, Zip\nZip -> State, City';
const DEFAULT_ATTRS = 'CustomerID';

// Bike state (frontend only, persisted via localStorage)
let bikes = [];
const BASE_BIKE_COUNT = 128;

/* ============================================================
   4. UTILITY FUNCTIONS
   ============================================================ */

function showSpinner() {
  if (spinnerContainer) spinnerContainer.style.display = 'flex';
  document.body.style.pointerEvents = 'none';
}

function hideSpinner() {
  if (spinnerContainer) spinnerContainer.style.display = 'none';
  document.body.style.pointerEvents = 'auto';
}

function showToast(message, type = 'success') {
  if (!toastContainer) return;
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <span class="icon">${type === 'success' ? '✅' : '⚠️'}</span>
    <span>${message}</span>
  `;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}

function openPanel(title, htmlContent) {
  if (panelTitle) panelTitle.textContent = title;
  if (panelContent) panelContent.innerHTML = htmlContent;
  if (slidePanel) slidePanel.classList.add('show');
  if (panelOverlay) panelOverlay.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closePanel() {
  if (slidePanel) slidePanel.classList.remove('show');
  if (panelOverlay) panelOverlay.classList.remove('show');
  document.body.style.overflow = '';
}

/**
 * Perform a fetch with automatic fallback between primary and secondary backend ports.
 * Returns an object { response, baseUrl } where baseUrl is the URL that succeeded.
 */
async function fetchWithFallback(path, options = {}) {
  const urlsTried = [];
  const errors = [];

  const makeRequest = async (baseUrl) => {
    const url = `${baseUrl}${path}`;
    urlsTried.push(url);
    try {
      const resp = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
        ...options,
      });
      return { resp, baseUrl };
    } catch (err) {
      errors.push({ url, error: err });
      return null;
    }
  };

  // Try primary
  let result = await makeRequest(API_BASE);
  if (result) return { response: result.resp, baseUrl: result.baseUrl };

  // Try fallback
  if (API_FALLBACK && API_FALLBACK !== API_BASE) {
    result = await makeRequest(API_FALLBACK);
    if (result) return { response: result.resp, baseUrl: result.baseUrl };
  }

  const detailMessage = `Tried: ${urlsTried.join(' , ')}`;
  console.error('Backend connection failed on all endpoints', {
    tried: urlsTried,
    errors,
  });
  const error = new Error('Unable to reach backend on any configured port.');
  error._backendDetail = detailMessage;
  throw error;
}

function clearInputs(schemaEl, fdsEl, attrsEl = null) {
  if (schemaEl) schemaEl.value = '';
  if (fdsEl) fdsEl.value = '';
  if (attrsEl) attrsEl.value = '';
  showToast('Inputs cleared');
}

function renderBikeCard(bike) {
  const row = document.createElement('div');
  row.className = 'bike-row bike-row--new';
  row.dataset.id = bike.id;
  row.innerHTML = `
    <div class="bike-row-main">
      <div class="bike-row-title">${bike.model}</div>
      <div class="bike-row-meta">${bike.category || 'Uncategorized'}</div>
    </div>
    <div class="bike-row-pill">Garage UI</div>
  `;
  return row;
}

function updateTotalBikesCount() {
  if (!statTotalBikes) return;
  const total = BASE_BIKE_COUNT + bikes.length;
  statTotalBikes.textContent = String(total);
  statTotalBikes.classList.remove('stat-bikes-pop');
  // Force reflow to restart animation
  // eslint-disable-next-line no-unused-expressions
  void statTotalBikes.offsetWidth;
  statTotalBikes.classList.add('stat-bikes-pop');
  console.log('Bike count:', total);
}

function renderBikesFromState() {
  if (!garageListEl) return;

  // Clear placeholder when we have bikes
  const empty = garageListEl.querySelector('.bike-list-empty');
  if (empty && bikes.length > 0) {
    empty.remove();
  }

  // Clear existing rendered rows
  garageListEl.querySelectorAll('.bike-row').forEach((n) => n.remove());

  bikes
    .slice()
    .reverse()
    .forEach((bike) => {
      const row = renderBikeCard(bike);
      garageListEl.prepend(row);
    });

  updateTotalBikesCount();
}

function persistBikes() {
  try {
    window.localStorage.setItem('bikes', JSON.stringify(bikes));
  } catch (err) {
    console.warn('Failed to persist bikes to localStorage', err);
  }
}

function loadBikesFromStorage() {
  try {
    const raw = window.localStorage.getItem('bikes');
    if (!raw) {
      bikes = [];
      return;
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      bikes = parsed.filter(
        (b) => b && typeof b.id === 'number' && typeof b.model === 'string'
      );
    } else {
      bikes = [];
    }
  } catch (err) {
    console.warn('Failed to load bikes from localStorage', err);
    bikes = [];
  }
}

function addBikeToList() {
  if (!bikeModelInput || !bikeCategoryInput || !garageListEl) return;

  const model = bikeModelInput.value.trim();
  const category = bikeCategoryInput.value.trim();

  if (!model) {
    showToast('Enter a bike model to add.', 'warning');
    return;
  }

  const bike = {
    id: Date.now(),
    model,
    category,
  };

  bikes.push(bike);
  persistBikes();

  // Remove empty state if present
  const empty = garageListEl.querySelector('.bike-list-empty');
  if (empty) {
    empty.remove();
  }

  const row = renderBikeCard(bike);
  garageListEl.prepend(row);

  updateTotalBikesCount();

  bikeModelInput.value = '';
  bikeCategoryInput.value = '';

  showToast('Bike added to local garage view.', 'success');
}

function openClosurePanelUI() {
  const baseSchema = document.getElementById('closure-schema');
  const baseFds = document.getElementById('closure-fds');
  const baseAttrs = document.getElementById('closure-attrs');

  const html = `
    <div class="card" style="background: var(--bg-input); border-radius: 16px; border:1px solid var(--border); padding: 24px;">
      <div class="card-header" style="margin-bottom: 20px;">
        <h2 class="section-title">Attribute Closure — Input</h2>
      </div>
      <div class="input-dashboard-grid">
        <div class="input-col-left">
          <div class="form-group">
            <label class="form-label" for="panel-closure-schema">RELATION SCHEMA</label>
            <input id="panel-closure-schema" type="text" class="form-input font-mono" placeholder="R(A, B, C...)">
          </div>
          <div class="form-group" style="margin-top:20px;">
            <label class="form-label" for="panel-closure-attrs">STARTING ATTRIBUTES</label>
            <input id="panel-closure-attrs" type="text" class="form-input font-mono" placeholder="A, B">
          </div>
        </div>
        <div class="input-col-right">
          <div class="form-group h-full">
            <label class="form-label" for="panel-closure-fds">FUNCTIONAL DEPENDENCIES</label>
            <textarea id="panel-closure-fds" class="form-textarea font-mono" placeholder="A -> B, C&#10;B -> D"></textarea>
          </div>
        </div>
      </div>
      <div class="action-row" style="margin-top: 8px;">
        <button id="panel-btn-closure" class="btn-primary" style="width:auto;">
          <span>⚙️</span> Compute Closure
        </button>
      </div>
    </div>
  `;

  openPanel('Attribute Closure', html);

  const pSchema = document.getElementById('panel-closure-schema');
  const pFds = document.getElementById('panel-closure-fds');
  const pAttrs = document.getElementById('panel-closure-attrs');
  const pBtn = document.getElementById('panel-btn-closure');

  if (baseSchema && pSchema) pSchema.value = baseSchema.value;
  if (baseFds && pFds) pFds.value = baseFds.value;
  if (baseAttrs && pAttrs) pAttrs.value = baseAttrs.value;

  const syncToBase = () => {
    if (baseSchema && pSchema) baseSchema.value = pSchema.value;
    if (baseFds && pFds) baseFds.value = pFds.value;
    if (baseAttrs && pAttrs) baseAttrs.value = pAttrs.value;
  };

  ['input', 'change'].forEach(evt => {
    if (pSchema) pSchema.addEventListener(evt, syncToBase);
    if (pFds) pFds.addEventListener(evt, syncToBase);
    if (pAttrs) pAttrs.addEventListener(evt, syncToBase);
  });

  if (pBtn) {
    pBtn.addEventListener('click', () => {
      syncToBase();
      if (btnClosure) btnClosure.click();
    });
  }
}

function openKeysPanelUI() {
  const baseSchema = document.getElementById('keys-schema');
  const baseFds = document.getElementById('keys-fds');

  const html = `
    <div class="card" style="background: var(--bg-input); border-radius: 16px; border:1px solid var(--border); padding: 24px;">
      <div class="card-header" style="margin-bottom: 20px;">
        <h2 class="section-title">Candidate Keys — Input</h2>
      </div>
      <div class="input-dashboard-grid">
        <div class="input-col-left">
          <div class="form-group">
            <label class="form-label" for="panel-keys-schema">RELATION SCHEMA</label>
            <input id="panel-keys-schema" type="text" class="form-input font-mono" placeholder="R(A, B, C...)">
          </div>
        </div>
        <div class="input-col-right">
          <div class="form-group h-full">
            <label class="form-label" for="panel-keys-fds">FUNCTIONAL DEPENDENCIES</label>
            <textarea id="panel-keys-fds" class="form-textarea font-mono" placeholder="A -> B, C&#10;B -> D"></textarea>
          </div>
        </div>
      </div>
      <div class="action-row" style="margin-top: 8px;">
        <button id="panel-btn-keys" class="btn-primary" style="width:auto;">
          <span>🔑</span> Find Candidate Keys
        </button>
      </div>
    </div>
  `;

  openPanel('Candidate Keys', html);

  const pSchema = document.getElementById('panel-keys-schema');
  const pFds = document.getElementById('panel-keys-fds');
  const pBtn = document.getElementById('panel-btn-keys');

  if (baseSchema && pSchema) pSchema.value = baseSchema.value;
  if (baseFds && pFds) pFds.value = baseFds.value;

  const syncToBase = () => {
    if (baseSchema && pSchema) baseSchema.value = pSchema.value;
    if (baseFds && pFds) baseFds.value = pFds.value;
  };

  ['input', 'change'].forEach(evt => {
    if (pSchema) pSchema.addEventListener(evt, syncToBase);
    if (pFds) pFds.addEventListener(evt, syncToBase);
  });

  if (pBtn) {
    pBtn.addEventListener('click', () => {
      syncToBase();
      if (btnKeys) btnKeys.click();
    });
  }
}

function openNormalizePanelUI() {
  const baseSchema = document.getElementById('norm-schema');
  const baseFds = document.getElementById('norm-fds');

  const html = `
    <div class="card" style="background: var(--bg-input); border-radius: 16px; border:1px solid var(--border); padding: 24px;">
      <div class="card-header" style="margin-bottom: 20px;">
        <h2 class="section-title">Normalization — Input</h2>
      </div>
      <div class="input-dashboard-grid">
        <div class="input-col-left">
          <div class="form-group">
            <label class="form-label" for="panel-norm-schema">RELATION SCHEMA</label>
            <input id="panel-norm-schema" type="text" class="form-input font-mono" placeholder="R(A, B, C...)">
            <p style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Use plural suffixes for 1NF multi-values (e.g. Phones)</p>
          </div>
        </div>
        <div class="input-col-right">
          <div class="form-group h-full">
            <label class="form-label" for="panel-norm-fds">FUNCTIONAL DEPENDENCIES</label>
            <textarea id="panel-norm-fds" class="form-textarea font-mono" placeholder="A -> B, C&#10;B -> D"></textarea>
          </div>
        </div>
      </div>
      <div class="action-row" style="margin-top: 8px;">
        <button id="panel-btn-normalize" class="btn-primary" style="width:auto;">
          <span>🧠</span> Normalize Database
        </button>
      </div>
    </div>
  `;

  openPanel('Normalization', html);

  const pSchema = document.getElementById('panel-norm-schema');
  const pFds = document.getElementById('panel-norm-fds');
  const pBtn = document.getElementById('panel-btn-normalize');

  if (baseSchema && pSchema) pSchema.value = baseSchema.value;
  if (baseFds && pFds) pFds.value = baseFds.value;

  const syncToBase = () => {
    if (baseSchema && pSchema) baseSchema.value = pSchema.value;
    if (baseFds && pFds) baseFds.value = pFds.value;
  };

  ['input', 'change'].forEach(evt => {
    if (pSchema) pSchema.addEventListener(evt, syncToBase);
    if (pFds) pFds.addEventListener(evt, syncToBase);
  });

  if (pBtn) {
    pBtn.addEventListener('click', () => {
      syncToBase();
      if (btnNormalize) btnNormalize.click();
    });
  }
}

/* ============================================================
   5. COMPONENT GENERATORS
   ============================================================ */

function renderRelationSmall(rel, problematicAttrs = []) {
  const attrsHtml = rel.attributes.map(attr => {
    const isPK = rel.primary_key.includes(attr);
    const isProblem = problematicAttrs.includes(attr);
    
    let style = "padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; background: rgba(255,255,255,0.05); color: white;";
    if (isPK) style += " border-bottom: 2px solid var(--primary-purple);";
    if (isProblem) style += " background: rgba(255, 60, 60, 0.2); color: #ff8888; animation: pulseRed 2s infinite;";
    
    return `<span style="${style}">${attr}</span>`;
  }).join(' ');

  let fdsHtml = '';
  if (rel.fds && rel.fds.length > 0) {
     fdsHtml = `<div style="font-size: 11px; color: var(--text-secondary); margin-top: 10px; font-family: monospace; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px;">` +
               rel.fds.map(f => `${f.lhs.join(',')} <span style="color: var(--primary-purple);">&rarr;</span> ${f.rhs.join(',')}`).join('<br>') +
               `</div>`;
  }

  return `
    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; min-width: 250px;">
      <span style="display:inline-block; font-size:12px; font-weight:700; color:var(--primary-purple); padding:2px 8px; border:1px solid var(--border-accent); border-radius:12px; margin-bottom:12px; letter-spacing:0.05em;">${rel.name}</span>
      <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:4px;">
        ${attrsHtml}
      </div>
      ${fdsHtml}
    </div>
  `;
}

function renderNFSection(nf, data, originalSchema = '', stepIndex = 0) {
  let stepsHtml = '';

  if (nf === '1NF') {
    // Step 1: Check
    const violationsHtml = data.violations.length > 0 
      ? data.violations.map(v => `<div style="color: #ff8888; font-size:14px; background: rgba(255,60,60,0.1); padding: 10px 14px; border-radius: 8px; border-left: 3px solid #ff8888;">⚠️ ${v}</div>`).join('')
      : '<div style="color: #4ade80; font-size:14px; background: rgba(74,222,128,0.1); padding: 10px 14px; border-radius: 8px; border-left: 3px solid #4ade80; display:inline-block;">✅ Schema is fully atomic (Already in 1NF)</div>';

    stepsHtml += `
      <div style="margin-bottom: 30px; background: var(--bg-input); padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
        <h3 style="font-size:16px; color:white; margin-bottom:16px; display:flex; gap:10px; align-items:center;">
           <span style="background:var(--primary-purple); color:white; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px;">1</span>
           1NF Atomicity Check
        </h3>
        <div style="display: flex; flex-direction: column; gap: 10px;">${violationsHtml}</div>
      </div>
    `;

    // Step 2 & 3: Transformation
    if (!data.already_satisfied) {
      stepsHtml += `
        <div style="margin-bottom: 30px; background: var(--bg-input); padding: 20px; border-radius: 12px; border: 1px solid var(--border); border-left: 3px solid var(--primary-purple);">
          <h3 style="font-size:14px; color:var(--text-secondary); margin-bottom:10px; text-transform:uppercase; letter-spacing:0.05em;">1NF Decomposition Result</h3>
          <p style="font-size:13px; color:var(--text-muted); margin-bottom:20px;">Multi-valued attributes were extracted into independent relations linked by the primary key.</p>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">
             ${data.relations.map(r => renderRelationSmall(r, data.problematic_attributes)).join('')}
          </div>
        </div>
      `;
    }
  } else {
    // 2NF, 3NF, BCNF
    const statusHtml = data.already_satisfied 
      ? `<div style="color: #4ade80; font-size:14px; background: rgba(74,222,128,0.1); padding: 10px 14px; border-radius: 8px; border-left: 3px solid #4ade80; display:inline-block;">✅ Already in ${nf} (No violations found)</div>`
      : `<div style="display: flex; flex-direction: column; gap: 10px;">${data.violations.map(v => `<div style="color: #ff8888; font-size:14px; background: rgba(255,100,100,0.1); padding: 10px 14px; border-radius: 8px; border-left: 3px solid #ff8888;">⚠️ ${v}</div>`).join('')}</div>`;

    let relationsHtml = '';
    if (!data.already_satisfied && data.relations.length > 0) {
        relationsHtml = `
          <div style="margin-top: 20px;">
              <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.05em;">Restructured Relations (${nf}):</p>
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">
                 ${data.relations.map(r => renderRelationSmall(r)).join('')}
              </div>
          </div>
        `;
    }


    stepsHtml += `
      <div style="margin-bottom: 30px; background: var(--bg-input); padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
        <h3 style="font-size:16px; color:white; margin-bottom:16px; display:flex; gap:10px; align-items:center;">
           <span style="background:var(--primary-purple); color:white; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px;">${nf.charAt(0)}</span>
           ${nf} Dependencies Check
        </h3>
        ${statusHtml}
        ${relationsHtml}
      </div>
    `;
  }

  return `<div class="nf-step" style="animation-delay: ${stepIndex * 0.15}s">\n${stepsHtml}\n</div>`;
}

/* ============================================================
   6. ACTION HANDLERS
   ============================================================ */

async function handleClosure() {
  const schema = closureSchema ? closureSchema.value.trim() : '';
  const attrs = closureAttrs ? closureAttrs.value.split(',').map(s => s.trim()).filter(Boolean) : [];
  const fds = closureFds ? closureFds.value.split('\n').map(l => l.trim()).filter(l => l.includes('->')) : [];

  if (!schema || !attrs.length || !fds.length) {
    showToast('Please fill all required fields', 'warning');
    return;
  }

  showSpinner();
  try {
    const { response: resp, baseUrl } = await fetchWithFallback('/closure', {
      method: 'POST',
      body: JSON.stringify({ schema, attributes: attrs, fds }),
    });

    const data = await resp.json();
    if (data.success) {
      const html = `
        <div style="background: var(--bg-input); border-radius: 16px; border: 1px solid var(--border); padding: 24px;">
           <div style="margin-bottom:24px;">
              <label style="display:block; margin-bottom:12px; color:var(--text-muted); font-size:13px; font-weight:600; letter-spacing:0.05em;">STARTING ATTRIBUTES</label>
              <div style="display:flex; flex-wrap:wrap; gap:8px;">${data.input_attributes.map(a => `<span style="padding:6px 12px; background:rgba(255,255,255,0.05); border:1px solid var(--border); border-radius:6px; font-family:monospace; color:var(--text-main); font-size:14px;">${a}</span>`).join('')}</div>
           </div>
           
           <label style="display:block; margin-bottom:12px; color:var(--text-muted); font-size:13px; font-weight:600; letter-spacing:0.05em;">COMPUTATION STEPS</label>
           <div style="background:rgba(0,0,0,0.3); padding:20px; border-radius:12px; border:1px solid var(--border); font-family:monospace; font-size:14px; color:var(--text-secondary); line-height:1.7; display:flex; flex-direction:column; gap:12px;">
              ${data.steps.map(s => `<div style="border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:12px;">${s}</div>`).join('')}
           </div>
           
           <div style="margin-top:32px; padding:24px; border:1px solid var(--border-accent); border-radius:12px; background:rgba(157, 78, 221, 0.05);">
              <label style="display:block; margin-bottom:12px; color:var(--primary-purple); font-size:14px; font-weight:700; letter-spacing:0.05em;">FINAL ATTRIBUTE CLOSURE</label>
              <div style="display:flex; flex-wrap:wrap; gap:10px;">${data.closure.map(a => `<span style="background:var(--primary-purple); color:white; padding:8px 16px; border-radius:8px; font-family:monospace; font-weight:700; font-size:15px; box-shadow:0 0 16px rgba(157, 78, 221, 0.3);">${a}</span>`).join('')}</div>
              ${data.determines_all ? '<div style="margin-top:16px; color:#4ade80; font-size:14px; font-weight:600;">✨ Found! These attributes form a Candidate Superkey!</div>' : ''}
           </div>
        </div>
      `;
      try {
        openPanel('Attribute Closure Calculation', html);
      } catch (renderErr) {
        console.error('Render error in handleClosure', renderErr);
        showToast('Render error while showing closure results.', 'warning');
      }
      showToast(`Matrix calculations complete (via ${baseUrl})`);
    } else {
      console.warn('Backend validation error (closure)', data);
      showToast(data.error || 'Backend reported an error for closure.', 'warning');
    }
  } catch (e) {
    const detail = e && e._backendDetail ? ` ${e._backendDetail}` : '';
    console.error('Closure request failed', e);
    showToast(`Cannot connect to backend for closure.${detail ? ' See console for details.' : ''}`, 'warning');
  } finally {
    hideSpinner();
  }
}

async function handleKeys() {
  const schema = keysSchema ? keysSchema.value.trim() : '';
  const fds = keysFds ? keysFds.value.split('\n').map(l => l.trim()).filter(l => l.includes('->')) : [];

  if (!schema || !fds.length) {
    showToast('Schema and FDs required', 'warning');
    return;
  }

  showSpinner();
  try {
    const { response: resp, baseUrl } = await fetchWithFallback('/candidate-keys', {
      method: 'POST',
      body: JSON.stringify({ schema, fds }),
    });

    const data = await resp.json();
    if (data.success) {
      const html = `
        <div style="display:flex; flex-direction:column; gap:24px;">
           <div style="background: linear-gradient(135deg, rgba(157,78,221,0.1) 0%, rgba(26,26,46,1) 100%); border: 1px solid var(--border-accent); border-radius: 16px; padding: 24px;">
              <h3 style="color:white; font-size:16px; font-weight:700; margin-bottom:16px; display:flex; gap:10px; align-items:center;">
                <span style="font-size:20px;">🔑</span> Derived Candidate Keys
              </h3>
              <div style="display:flex; flex-wrap:wrap; gap:12px;">
                ${data.candidate_keys.map(k => `<span style="background:var(--primary-purple); color:white; padding:10px 20px; border-radius:8px; font-family:monospace; font-weight:700; font-size:16px; box-shadow:0 4px 16px rgba(157, 78, 221, 0.4);">{${k.join(', ')}}</span>`).join('')}
              </div>
           </div>
           
           <div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px;">
               <div style="background: var(--bg-input); border-radius: 16px; border: 1px solid var(--border); padding: 20px;">
                  <h4 style="color:var(--text-muted); font-size:12px; font-weight:600; letter-spacing:0.05em; margin-bottom:16px;">PRIME ATTRIBUTES</h4>
                  <div style="display:flex; flex-wrap:wrap; gap:8px;">
                    ${data.prime_attributes.length ? data.prime_attributes.map(a => `<span style="padding:6px 12px; background:rgba(255,255,255,0.05); border:1px solid var(--border); border-radius:6px; font-family:monospace; color:var(--text-main); font-size:13px;">${a}</span>`).join('') : '<span style="color:var(--text-muted); font-style:italic; font-size:13px;">None</span>'}
                  </div>
               </div>
               
               <div style="background: var(--bg-input); border-radius: 16px; border: 1px solid var(--border); padding: 20px;">
                  <h4 style="color:var(--text-muted); font-size:12px; font-weight:600; letter-spacing:0.05em; margin-bottom:16px;">NON-PRIME ATTRIBUTES</h4>
                  <div style="display:flex; flex-wrap:wrap; gap:8px;">
                    ${data.non_prime_attributes.length ? data.non_prime_attributes.map(a => `<span style="padding:6px 12px; background:rgba(255,255,255,0.03); border:1px dashed var(--border); border-radius:6px; font-family:monospace; color:var(--text-secondary); font-size:13px;">${a}</span>`).join('') : '<span style="color:var(--text-muted); font-style:italic; font-size:13px;">None</span>'}
                  </div>
               </div>
           </div>
        </div>
      `;
      try {
        openPanel('Key Discovery Profile', html);
      } catch (renderErr) {
        console.error('Render error in handleKeys', renderErr);
        showToast('Render error while showing candidate key results.', 'warning');
      }
      showToast(`Key sets extracted (via ${baseUrl})`);
    } else {
      console.warn('Backend validation error (candidate-keys)', data);
      showToast(data.error || 'Backend reported an error for candidate keys.', 'warning');
    }
  } catch (e) {
    const detail = e && e._backendDetail ? ` ${e._backendDetail}` : '';
    console.error('Candidate keys request failed', e);
    showToast(`Cannot connect to backend for candidate keys.${detail ? ' See console for details.' : ''}`, 'warning');
  } finally {
    hideSpinner();
  }
}

async function handleNormalize() {
  const schema = normSchema ? normSchema.value.trim() : '';
  const fds = normFds ? normFds.value.split('\n').map(l => l.trim()).filter(l => l.includes('->')) : [];

  if (!schema || !fds.length) {
    showToast('Schema and FDs required', 'warning');
    return;
  }

  showSpinner();
  try {
    const { response: resp, baseUrl } = await fetchWithFallback('/normalize', {
      method: 'POST',
      body: JSON.stringify({ schema, fds, target: 'ALL' }),
    });

    const data = await resp.json();
    if (data.success) {
      let html = '<div style="padding-bottom: 20px;">';
      let stepIdx = 0;
      html += renderNFSection('1NF', data.results['1NF'], schema, stepIdx++);
      html += renderNFSection('2NF', data.results['2NF'], '', stepIdx++);
      html += renderNFSection('3NF', data.results['3NF'], '', stepIdx++);
      if (data.results['BCNF']) html += renderNFSection('BCNF', data.results['BCNF'], '', stepIdx++);
      html += '</div>';
      try {
        openPanel('Normalization Sequence', html);
      } catch (renderErr) {
        console.error('Render error in handleNormalize', renderErr);
        showToast('Render error while showing normalization results.', 'warning');
      }
      showToast(`Automated breakdown completed (via ${baseUrl})`);
    } else {
      console.warn('Backend validation error (normalize)', data);
      showToast(data.error || 'Backend reported an error for normalization.', 'warning');
    }
  } catch (e) {
    const detail = e && e._backendDetail ? ` ${e._backendDetail}` : '';
    console.error('Normalization request failed', e);
    showToast(`Cannot connect to backend for normalization.${detail ? ' See console for details.' : ''}`, 'warning');
  } finally {
    hideSpinner();
  }
}

/* ============================================================
   7. EVENT LISTENERS
   ============================================================ */

if(btnClosure) btnClosure.addEventListener('click', handleClosure);
if(btnClearClosure) btnClearClosure.addEventListener('click', () => clearInputs(closureSchema, closureFds, closureAttrs));

if(btnKeys) btnKeys.addEventListener('click', handleKeys);
if(btnClearKeys) btnClearKeys.addEventListener('click', () => clearInputs(keysSchema, keysFds));

if(btnNormalize) btnNormalize.addEventListener('click', handleNormalize);
if(btnClearNorm) btnClearNorm.addEventListener('click', () => clearInputs(normSchema, normFds));

if (btnAddBike) btnAddBike.addEventListener('click', addBikeToList);
if (btnClearBike) {
  btnClearBike.addEventListener('click', () => {
    if (bikeModelInput) bikeModelInput.value = '';
    if (bikeCategoryInput) bikeCategoryInput.value = '';
    if (bikeModelInput) bikeModelInput.focus();
  });
}

if (btnClearGarage) {
  btnClearGarage.addEventListener('click', () => {
    if (!window.confirm('Clear all bikes?')) return;
    bikes = [];
    try {
      window.localStorage.removeItem('bikes');
    } catch (err) {
      console.warn('Failed to clear bikes from localStorage', err);
    }
    if (garageListEl) {
      garageListEl.innerHTML = '';
    }
    updateTotalBikesCount();
  });
}

if (btnOpenClosurePanel) btnOpenClosurePanel.addEventListener('click', openClosurePanelUI);
if (btnOpenKeysPanel) btnOpenKeysPanel.addEventListener('click', openKeysPanelUI);
if (btnOpenNormalizePanel) btnOpenNormalizePanel.addEventListener('click', openNormalizePanelUI);

if(btnClosePanel) btnClosePanel.addEventListener('click', closePanel);
if(panelOverlay) panelOverlay.addEventListener('click', closePanel);

// Escape key to close panel
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && slidePanel && slidePanel.classList.contains('show')) {
        closePanel();
    }
});

/* ============================================================
   8. INITIALIZATION
   ============================================================ */
async function checkBackendHealthOnLoad() {
  if (!backendStatusBadge) return;

  backendStatusBadge.style.display = 'flex';
  backendStatusBadge.style.background = 'rgba(234, 179, 8, 0.1)';
  backendStatusBadge.style.color = '#facc15';
  backendStatusBadge.style.border = '1px solid rgba(234, 179, 8, 0.3)';
  backendStatusBadge.innerHTML = '<span>●</span> SYSTEM CHECKING...';

  try {
    const { response: resp, baseUrl } = await fetchWithFallback('/health', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await resp.json().catch(() => ({}));

    backendStatusBadge.style.background = 'rgba(34, 197, 94, 0.1)';
    backendStatusBadge.style.color = '#4ade80';
    backendStatusBadge.style.border = '1px solid rgba(34, 197, 94, 0.3)';
    backendStatusBadge.innerHTML = `<span>●</span> SYSTEM ONLINE (${baseUrl})`;

    console.info('Backend health check OK', { baseUrl, data });
  } catch (e) {
    console.error('Backend health check failed', e);
    const detail = e && e._backendDetail ? e._backendDetail : '';
    backendStatusBadge.style.background = 'rgba(239, 68, 68, 0.12)';
    backendStatusBadge.style.color = '#f87171';
    backendStatusBadge.style.border = '1px solid rgba(239, 68, 68, 0.3)';
    backendStatusBadge.innerHTML = `<span>●</span> BACKEND OFFLINE${detail ? ' — see console' : ''}`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Init default values for all inputs
  if(closureSchema) closureSchema.value = DEFAULT_SCHEMA;
  if(closureFds) closureFds.value = DEFAULT_FDS;
  if(closureAttrs) closureAttrs.value = DEFAULT_ATTRS;

  if(keysSchema) keysSchema.value = DEFAULT_SCHEMA;
  if(keysFds) keysFds.value = DEFAULT_FDS;

  if(normSchema) normSchema.value = DEFAULT_SCHEMA;
  if(normFds) normFds.value = DEFAULT_FDS;
  
  // Base initialization fixes on sliding panel mapping from initial css if required
  if (slidePanel) slidePanel.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
  if (panelOverlay) panelOverlay.style.transition = 'opacity 0.3s ease';

  // Backend health check indicator
  checkBackendHealthOnLoad();

  // Load bikes from localStorage and render
  loadBikesFromStorage();
  renderBikesFromState();
});
