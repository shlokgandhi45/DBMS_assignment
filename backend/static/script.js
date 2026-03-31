'use strict';

/* ============================================================
   1. CONFIGURATION
   ============================================================ */
const API_BASE = window.location.origin;

/* ============================================================
   2. DOM REFERENCES
   ============================================================ */
// Sidebar navigation
const navItems = document.querySelectorAll('.sidebar-item');
const contentSections = document.querySelectorAll('.content-section');

// Forms & Inputs
const closureSchema = document.getElementById('closure-schema');
const closureFds    = document.getElementById('closure-fds');
const closureAttrs  = document.getElementById('closure-attrs');

const keysSchema    = document.getElementById('keys-schema');
const keysFds       = document.getElementById('keys-fds');

const normSchema    = document.getElementById('norm-schema');
const normFds       = document.getElementById('norm-fds');

// Buttons
const btnClosure       = document.getElementById('btn-closure');
const btnClearClosure  = document.getElementById('btn-clear-closure');
const btnKeys          = document.getElementById('btn-candidate-keys');
const btnClearKeys     = document.getElementById('btn-clear-keys');
const btnNormalize     = document.getElementById('btn-normalize');
const btnClearNorm     = document.getElementById('btn-clear-norm');

// UI Elements
const spinnerOverlay = document.getElementById('spinner-overlay');
const toastContainer = document.getElementById('toast-container');

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

/* ============================================================
   4. UTILITY FUNCTIONS
   ============================================================ */

function showSpinner() {
  spinnerOverlay.hidden = false;
  document.body.style.pointerEvents = 'none';
}

function hideSpinner() {
  spinnerOverlay.hidden = true;
  document.body.style.pointerEvents = 'auto';
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === 'success' ? '✅' : '⚠️'}</span>
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
  panelTitle.textContent = title;
  panelContent.innerHTML = htmlContent;
  slidePanel.classList.add('show');
  panelOverlay.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closePanel() {
  slidePanel.classList.remove('show');
  panelOverlay.classList.remove('show');
  document.body.style.overflow = '';
}

function switchSection(sectionId) {
  // Update nav buttons
  navItems.forEach(item => {
    item.classList.toggle('sidebar-item--active', item.dataset.section === sectionId);
    item.setAttribute('aria-pressed', item.dataset.section === sectionId);
  });
  
  // Update content sections
  contentSections.forEach(section => {
    section.classList.toggle('active', section.id === `section-${sectionId}`);
  });
}

function clearInputs(schemaEl, fdsEl, attrsEl = null) {
  schemaEl.value = '';
  fdsEl.value = '';
  if (attrsEl) attrsEl.value = '';
  showToast('Inputs cleared');
}

/* ============================================================
   5. COMPONENT GENERATORS
   ============================================================ */

function renderRelationSmall(rel, problematicAttrs = []) {
  const attrsHtml = rel.attributes.map(attr => {
    const isPK = rel.primary_key.includes(attr);
    const isProblem = problematicAttrs.includes(attr);
    let className = isPK ? 'pk-underline' : '';
    if (isProblem) className += ' attr-highlight-red';
    return `<span class="${className}">${attr}</span>`;
  }).join(', ');

  let fdsHtml = '';
  if (rel.fds && rel.fds.length > 0) {
     fdsHtml = `<div style="font-size: 11px; color: var(--text-secondary, #A0A0A0); margin-top: 6px; font-family: monospace;">` +
               rel.fds.map(f => `${f.lhs.join(',')} &rarr; ${f.rhs.join(',')}`).join('<br>') +
               `</div>`;
  }

  return `
    <div class="rel-card-small">
      <span class="rel-name-pill">${rel.name}</span>
      <div class="rel-attrs-row">
        (${attrsHtml})
      </div>
      ${fdsHtml}
    </div>
  `;
}

function renderNFSection(nf, data, originalSchema = '') {
  let stepsHtml = '';

  if (nf === '1NF') {
    // Step 1: Check
    const violationsHtml = data.violations.length > 0 
      ? data.violations.map(v => `<div class="violation-tag">⚠️ ${v}</div>`).join('')
      : '<div class="success-badge" style="display:inline-flex;">✅ Already in 1NF</div>';

    stepsHtml += `
      <div class="norm-step" style="margin-bottom: 20px;">
        <div class="norm-step-header" style="margin-bottom: 10px;">
           <span class="norm-step-title" style="font-weight: bold; color: var(--primary-purple);">1NF Check</span>
        </div>
        <div class="violation-list" style="display: flex; flex-direction: column; gap: 8px;">${violationsHtml}</div>
      </div>
    `;

    // Step 2 & 3: Transformation
    if (!data.already_satisfied) {
      // Extract original attributes, default to empty array if no match
      const match = originalSchema.match(/\((.*?)\)/);
      const originalAttrs = match ? match[1].split(',').map(s=>s.trim()) : [];
        
      const beforeRel = { name: "Original", attributes: originalAttrs, primary_key: [] };
      
      stepsHtml += `
        <div class="norm-step" style="margin-bottom: 30px; border-left: 2px solid var(--primary-purple); padding-left: 15px;">
          <div class="norm-step-header" style="margin-bottom: 10px;">
             <span class="norm-step-title" style="font-weight: 600;">Convert to 1NF</span>
          </div>
          <p style="font-size:13px; color:var(--text-secondary); margin-bottom:12px;">Extracting multi-valued/repeating attributes into separate linking tables.</p>
          <div class="relations-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
             ${data.relations.map(r => renderRelationSmall(r, data.problematic_attributes)).join('')}
          </div>
        </div>
      `;
    }
  } else {
    // 2NF, 3NF, BCNF
    const statusHtml = data.already_satisfied 
      ? `<div class="success-badge" style="display:inline-flex; border:1px solid #4ade80; padding: 4px 8px; border-radius: 4px; background: rgba(74, 222, 128, 0.1); color: #4ade80;">✅ Already in ${nf}</div>`
      : `<div class="violation-list" style="display: flex; flex-direction: column; gap: 8px;">${data.violations.map(v => `<div class="violation-tag" style="background: rgba(255,100,100,0.1); color: #ff8888; padding: 6px; border-radius: 4px;">⚠️ ${v}</div>`).join('')}</div>`;

    let relationsHtml = '';
    if (!data.already_satisfied && data.relations.length > 0) {
        relationsHtml = `
          <div style="margin-top: 15px;">
              <p style="font-size:13px; color:var(--text-secondary); margin-bottom:10px;">Decomposed Relations:</p>
              <div class="relations-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                 ${data.relations.map(r => renderRelationSmall(r)).join('')}
              </div>
          </div>
        `;
    }


    stepsHtml += `
      <div class="norm-step" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
        <div class="norm-step-header" style="margin-bottom: 10px;">
           <span class="norm-step-title" style="font-size: 1.2em; font-weight: bold; color: var(--primary-purple);">${nf} Decomposition</span>
        </div>
        ${statusHtml}
        ${relationsHtml}
      </div>
    `;
  }

  return stepsHtml;
}

/* ============================================================
   6. ACTION HANDLERS
   ============================================================ */

async function handleClosure() {
  const schema = closureSchema.value.trim();
  const attrs = closureAttrs.value.split(',').map(s => s.trim()).filter(Boolean);
  const fds = closureFds.value.split('\n').map(l => l.trim()).filter(l => l.includes('->'));

  if (!schema || !attrs.length || !fds.length) {
    showToast('Please fill all required fields', 'warning');
    return;
  }

  showSpinner();
  try {
    const resp = await fetch(`${API_BASE}/closure`, {
      method: 'POST',
      body: JSON.stringify({ schema, attributes: attrs, fds })
    });
    const data = await resp.json();
    if (data.success) {
      const html = `
        <div class="card" style="padding: 24px; background: var(--card-bg, #1A1A2E); border-radius: 12px;">
           <div class="key-box" style="margin-bottom:20px;">
              <label style="display:block; margin-bottom:8px; color:var(--text-secondary); font-size:14px;">Input Attributes</label>
              <div class="badge-row" style="display:flex; flex-wrap:wrap; gap:8px;">${data.input_attributes.map(a => `<span class="badge-item" style="padding:4px 8px; background:rgba(255,255,255,0.1); border-radius:4px; font-family:monospace;">${a}</span>`).join('')}</div>
           </div>
           
           <label style="display:block; margin-bottom:8px; color:var(--text-secondary); font-size:14px; margin-top:24px;">Computation Steps</label>
           <div class="step-list" style="background:rgba(0,0,0,0.2); padding:16px; border-radius:8px; font-family:monospace; font-size:13px; line-height:1.6; display:flex; flex-direction:column; gap:8px;">
              ${data.steps.map(s => `<div class="step-item" style="border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:8px;">${s}</div>`).join('')}
           </div>
           
           <div class="key-box" style="margin-top:24px; padding:16px; border:1px solid var(--primary-purple); border-radius:8px; background:rgba(157, 78, 221, 0.05);">
              <label style="display:block; margin-bottom:8px; color:white; font-size:14px; font-weight:bold;">Final Closure</label>
              <div class="badge-row" style="display:flex; flex-wrap:wrap; gap:8px;">${data.closure.map(a => `<span class="badge-item" style="background:var(--primary-purple); color:white; padding:6px 12px; border-radius:4px; font-family:monospace; font-weight:bold;">${a}</span>`).join('')}</div>
           </div>
           ${data.determines_all ? '<div style="margin-top:12px; color:#4ade80; font-size:14px;">✨ These attributes form a superkey!</div>' : ''}
        </div>
      `;
      openPanel('Attribute Closure Result', html);
      showToast('Closure computed');
    } else {
      showToast(data.error, 'warning');
    }
  } catch (e) {
    showToast('Backend connection error', 'warning');
    console.error(e);
  } finally {
    hideSpinner();
  }
}

async function handleKeys() {
  const schema = keysSchema.value.trim();
  const fds = keysFds.value.split('\n').map(l => l.trim()).filter(l => l.includes('->'));

  if (!schema || !fds.length) {
    showToast('Schema and FDs required', 'warning');
    return;
  }

  showSpinner();
  try {
    const resp = await fetch(`${API_BASE}/candidate-keys`, {
      method: 'POST',
      body: JSON.stringify({ schema, fds })
    });
    const data = await resp.json();
    if (data.success) {
      const html = `
        <div class="keys-grid" style="display:grid; gap:20px; padding: 20px;">
           <div class="key-box card" style="background:rgba(157, 78, 221, 0.1); border:1px solid var(--primary-purple);">
              <label style="display:block; color:white; font-weight:bold; margin-bottom:12px; font-size:16px;">Candidate Keys</label>
              <div class="badge-row" style="display:flex; flex-wrap:wrap; gap:10px;">
                ${data.candidate_keys.map(k => `<span class="badge-item" style="background:var(--primary-purple); color:white; padding:8px 16px; border-radius:6px; font-family:monospace; font-weight:bold; box-shadow:0 2px 8px rgba(157, 78, 221, 0.4);">{${k.join(', ')}}</span>`).join('')}
              </div>
           </div>
           <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-top: 10px;">
               <div class="key-box card">
                  <label style="display:block; color:var(--text-secondary); margin-bottom:10px;">Prime Attributes</label>
                  <div class="badge-row" style="display:flex; flex-wrap:wrap; gap:8px;">
                    ${data.prime_attributes.length ? data.prime_attributes.map(a => `<span class="badge-item" style="padding:4px 10px; background:rgba(255,255,255,0.1); border-radius:4px; font-family:monospace;">${a}</span>`).join('') : '<span style="color:#666; font-style:italic;">None</span>'}
                  </div>
               </div>
               <div class="key-box card">
                  <label style="display:block; color:var(--text-secondary); margin-bottom:10px;">Non-Prime Attributes</label>
                  <div class="badge-row" style="display:flex; flex-wrap:wrap; gap:8px;">
                    ${data.non_prime_attributes.length ? data.non_prime_attributes.map(a => `<span class="badge-item" style="padding:4px 10px; background:rgba(255,255,255,0.05); color:var(--text-secondary); border-radius:4px; font-family:monospace;">${a}</span>`).join('') : '<span style="color:#666; font-style:italic;">None</span>'}
                  </div>
               </div>
           </div>
        </div>
      `;
      openPanel('Candidate Keys Result', html);
      showToast('Keys found');
    } else {
      showToast(data.error, 'warning');
    }
  } catch (e) {
    showToast('Backend connection error', 'warning');
    console.error(e);
  } finally {
    hideSpinner();
  }
}

async function handleNormalize() {
  const schema = normSchema.value.trim();
  const fds = normFds.value.split('\n').map(l => l.trim()).filter(l => l.includes('->'));

  if (!schema || !fds.length) {
    showToast('Schema and FDs required', 'warning');
    return;
  }

  showSpinner();
  try {
    const resp = await fetch(`${API_BASE}/normalize`, {
      method: 'POST',
      body: JSON.stringify({ schema, fds, target: 'ALL' })
    });
    const data = await resp.json();
    if (data.success) {
      let html = '<div id="norm-results-container" style="padding: 20px;">';
      html += renderNFSection('1NF', data.results['1NF'], schema);
      html += renderNFSection('2NF', data.results['2NF']);
      html += renderNFSection('3NF', data.results['3NF']);
      if (data.results['BCNF']) html += renderNFSection('BCNF', data.results['BCNF']);
      html += '</div>';
      
      openPanel('Normalization Sequence', html);
      showToast('Normalization complete');
    } else {
      showToast(data.error, 'warning');
    }
  } catch (e) {
    showToast('Backend error', 'warning');
    console.error(e);
  } finally {
    hideSpinner();
  }
}

/* ============================================================
   7. EVENT LISTENERS
   ============================================================ */

btnClosure.addEventListener('click', handleClosure);
btnClearClosure.addEventListener('click', () => clearInputs(closureSchema, closureFds, closureAttrs));

btnKeys.addEventListener('click', handleKeys);
btnClearKeys.addEventListener('click', () => clearInputs(keysSchema, keysFds));

btnNormalize.addEventListener('click', handleNormalize);
btnClearNorm.addEventListener('click', () => clearInputs(normSchema, normFds));

btnClosePanel.addEventListener('click', closePanel);
panelOverlay.addEventListener('click', closePanel);

// Escape key to close panel
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && slidePanel.classList.contains('show')) {
        closePanel();
    }
});

// Sidebar Nav Interaction
navItems.forEach(item => {
  item.addEventListener('click', () => {
    switchSection(item.dataset.section);
  });
});

/* ============================================================
   8. INITIALIZATION
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  // Init default values for all inputs
  closureSchema.value = DEFAULT_SCHEMA;
  closureFds.value = DEFAULT_FDS;
  closureAttrs.value = DEFAULT_ATTRS;

  keysSchema.value = DEFAULT_SCHEMA;
  keysFds.value = DEFAULT_FDS;

  normSchema.value = DEFAULT_SCHEMA;
  normFds.value = DEFAULT_FDS;
  
  // Ensure correct initial view
  switchSection('closure');
});
