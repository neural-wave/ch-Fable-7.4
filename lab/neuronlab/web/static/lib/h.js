// Small DOM helpers: h() builds elements, the API client talks to `lab serve`, and the shared pieces of every page.

export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  apply(el, props);
  append(el, children);
  return el;
}

export function s(tag, props, ...children) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  apply(el, props);
  append(el, children);
  return el;
}

function apply(el, props) {
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'style' && typeof value === 'object') Object.assign(el.style, value);
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'class') el.setAttribute('class', Array.isArray(value) ? value.filter(Boolean).join(' ') : value);
    else if (key === 'value' && 'value' in el && el.tagName !== 'BUTTON') el.value = value;
    else if (key === 'checked') el.checked = Boolean(value);
    else el.setAttribute(key, value === true ? '' : value);
  }
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false || child === true) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function mount(root, ...nodes) {
  root.replaceChildren(...nodes.flat(Infinity).filter(Boolean));
}

// --- API -------------------------------------------------------------------------------------------------------

export async function get(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  const data = await response.json().catch(() => ({ error: response.statusText }));
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

export async function post(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Ergo': '1' },
    body: JSON.stringify(body || {}),
  });
  const data = await response.json().catch(() => ({ error: response.statusText }));
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

let toastTimer = null;
export function toast(text, bad = false) {
  document.querySelector('.toast')?.remove();
  const el = h('div', { class: ['toast', bad && 'bad'], role: bad ? 'alert' : 'status' },
    h('span', {}, text),
    h('button', { type: 'button', class: 'toast-close', 'aria-label': 'Dismiss', onClick: () => el.remove() }, icons.close()));
  document.body.append(el);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.remove(), bad ? 12000 : 5000);
}

export function dialog(title, body, actions, closeLabel) {
  const el = h('dialog', { class: 'dialog' },
    h('form', { method: 'dialog', class: 'stack-16' }, h('h2', {}, title), body,
      h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, h('button', { class: 'btn', value: 'cancel' }, closeLabel || (actions ? 'Cancel' : 'Close')), actions)));
  document.body.append(el);
  el.addEventListener('close', () => el.remove());
  el.showModal();
  return el;
}

// Freeze rewrites submission.py: say so and ask before the job starts.
export function confirmFreeze(task, run, candidate) {
  const go = h('button', { class: 'btn primary', value: 'go' }, 'Freeze and score');
  const el = dialog(`Freeze ${candidate}?`, h('div', { class: 'stack-8' },
    h('p', {}, 'Freeze writes this candidate as the function of ', h('span', { class: 'mono' }, task), ' in ', h('span', { class: 'mono' }, 'submission.py'), ', then scores the submission.'),
    h('p', { class: 'small muted' }, 'The function it replaces is overwritten: commit submission.py first if you want to keep it.')), go);
  go.addEventListener('click', () => { el.close(); start('freeze', task, { run, candidate }); });
}

// Words of the lab a newcomer meets first, explained on hover and focus.
export const GLOSSARY = {
  Discovery: 'Rows the rules are learned on (4 policies in 5). Exact = reproduced to the cent.',
  Holdout: 'Rows kept aside to check the rules (1 policy in 5, crc32(policy) % 5 == 0). The score that counts.',
  Freeze: 'Write a candidate into submission.py, then score it.',
  Candidate: 'One formula the pipeline proposes for the target, scored exactly on every row.',
  'Wrong rows': 'Rows where the winner does not give the exact legacy value.',
  'Typed by hand': 'Wrong rows of policies listed in NREXCP: the legacy values were edited by hand, no rule reproduces them.',
};

export function term(label, help = GLOSSARY[label]) {
  return help ? h('span', { class: 'term', title: help, tabindex: '0' }, label) : label;
}

// --- language model -------------------------------------------------------------------------------------------
// Step 5 (lab suggest) and the agent call Claude Code. /api/model asks it once, the way a task run reads its trace:
// the model named by the init event, connected when the request went through. Custom models come from .env.llm.

let settingsCache = null;
export function settings() {
  settingsCache = settingsCache || get('/api/settings').catch(() => null);
  return settingsCache;
}

const USE_LABEL = { suggest: 'Suggest features (step 5)', agent: 'Agent sessions' };

let modelCache = null;
export function modelStatus(refresh = false) {
  if (refresh || !modelCache) modelCache = pollModel(refresh);
  return modelCache;
}

async function pollModel(refresh) {
  let st = await (refresh ? post('/api/model/check') : get('/api/model')).catch(() => null);
  while (st && st.state === 'checking') {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    st = await get('/api/model').catch(() => null);
  }
  return st;
}

// ok: every use answers; warn: one of them does not; bad: none does, nothing can run.
export function modelState(st) {
  if (!st) return { level: 'unknown', chip: 'Model unknown', text: 'The lab could not ask Claude Code which model it uses.' };
  const uses = Object.values(st.uses || {});
  const up = uses.filter((u) => u.ok);
  const names = [...new Set(up.map((u) => u.model))].join(' / ');
  if (!up.length) {
    return { level: 'bad', chip: 'Model not connected', text: `Claude Code does not answer: ${uses[0]?.error || 'no answer'}` };
  }
  if (up.length < uses.length) {
    const down = Object.keys(st.uses).filter((k) => !st.uses[k].ok).map((k) => USE_LABEL[k]).join(', ');
    return { level: 'warn', chip: `${names} · one not connected`, text: `${down}: the model does not answer.` };
  }
  return { level: 'ok', chip: `Connected: ${names}`, text: `Claude Code answers with ${names}${st.endpoint ? ` on ${st.endpoint}` : ''} (checked at ${st.checked}).` };
}

const LEVEL_ICON = { ok: () => icons.check(), warn: () => icons.warn(), bad: () => icons.warn(), unknown: () => icons.info() };

function paintChip(chip, st) {
  const state = modelState(st);
  chip.dataset.level = state.level;
  chip.title = state.text;
  chip.replaceChildren(h('span', { class: 'dot' }), h('span', {}, state.chip));
}

function modelBody(st) {
  const state = modelState(st);
  const row = (use, u) => h('li', { class: ['model-row', u.ok ? 'ok' : 'warn'] },
    h('span', { class: 'model-row-icon' }, u.ok ? icons.check() : icons.warn()),
    h('span', { class: 'stack' }, h('span', { class: 'strong' }, USE_LABEL[use]),
      u.ok ? h('span', { class: 'small' }, 'Connected to ', h('span', { class: 'mono' }, u.model))
        : h('span', { class: 'small' }, 'Not connected', u.model ? [' to ', h('span', { class: 'mono' }, u.model)] : null, `: ${u.error}`),
      h('span', { class: 'small muted' }, u.requested ? ['Asked with ', h('span', { class: 'mono' }, `${u.variable}=${u.requested}`)] : ['Default model of Claude Code', h('span', { class: 'mono' }, ` (${u.variable} not set)`)],
        u.version ? ` · Claude Code ${u.version}` : null, u.source ? [' · ', u.source === 'none' ? 'login of claude' : ['key ', h('span', { class: 'mono' }, u.source)]] : null)));
  return h('div', { class: 'stack-16' },
    h('div', { class: ['banner', state.level === 'ok' ? 'ok' : state.level === 'bad' ? 'bad' : 'warn'] }, LEVEL_ICON[state.level](), h('span', { style: { flex: '1 1 300px' } }, state.text)),
    st ? h('ul', { class: 'model-rows' }, Object.entries(st.uses || {}).map(([use, u]) => row(use, u))) : null,
    state.level === 'ok' ? null : h('div', { class: 'stack-8' },
      h('h3', {}, 'How to fix it'),
      h('p', { class: 'small' }, 'Install Claude Code on this machine and log in once with ', h('span', { class: 'mono' }, 'claude'), '. For a custom model set the endpoint in ', h('span', { class: 'mono' }, '.env.llm'), ' at the root of the repository, then restart ', h('span', { class: 'mono' }, 'lab serve'), ':'),
      h('pre', { class: 'code' }, 'ANTHROPIC_BASE_URL=https://your-endpoint\nANTHROPIC_AUTH_TOKEN=your-key\nANTHROPIC_MODEL=your-model\nLLM_MODEL=your-model\nAGENT_MODEL=your-model')));
}

export function modelDialog() {
  const body = h('div', {}, h('p', { class: 'spinner' }, 'Asking Claude Code which model it uses…'));
  const again = h('button', { type: 'button', class: 'btn' }, 'Check again');
  const paint = (st) => {
    body.replaceChildren(modelBody(st));
    document.querySelectorAll('.model-chip').forEach((chip) => paintChip(chip, st));
    again.disabled = false;
  };
  again.addEventListener('click', () => {
    again.disabled = true;
    body.replaceChildren(h('p', { class: 'spinner' }, 'Asking Claude Code which model it uses…'));
    modelStatus(true).then(paint);
  });
  dialog('Language model', body, again, 'Close');
  modelStatus().then(paint);
}

function modelChip() {
  const chip = h('button', { type: 'button', class: 'model-chip', 'data-level': 'unknown', onClick: modelDialog, 'aria-haspopup': 'dialog' }, h('span', { class: 'dot' }), h('span', {}, 'Checking the model…'));
  modelStatus().then((st) => paintChip(chip, st));
  return chip;
}

// Where a use of the model starts: the model it is connected to, or why it cannot run.
export function modelNotice(use) {
  const slot = h('div', { class: 'model-notice' });
  modelStatus().then((st) => {
    const u = st?.uses?.[use];
    if (!u) return;
    slot.replaceChildren(u.ok ? h('p', { class: 'small muted' }, 'Runs on ', h('span', { class: 'mono' }, u.model), ', connected at ', st.checked, '.')
      : h('div', { class: ['banner', 'bad'], role: 'status' }, icons.warn(),
        h('span', { style: { flex: '1 1 300px' } }, `The model does not answer, this step cannot run: ${u.error}`),
        h('button', { type: 'button', class: 'btn small', onClick: modelDialog }, 'How to fix it')));
  });
  return slot;
}

export async function start(action, task, options = {}) {
  if (action === 'suggest' || action === 'agent') {
    const u = (await modelStatus())?.uses?.[action];
    if (u && !u.ok && (!options.model || options.model === u.id)) { modelDialog(); return; }
  }
  try {
    const job = await post('/api/jobs', { action, task, options });
    location.hash = `#/jobs/${job.id}`;
  } catch (e) {
    toast(e.message, true);
  }
}

// --- shared pieces ---------------------------------------------------------------------------------------------

export const icons = {
  check: () => s('svg', { width: 14, height: 14, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'aria-hidden': 'true' }, s('path', { d: 'M3 8.5l3 3 7-7' })),
  warn: () => s('svg', { width: 14, height: 14, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 2, 'aria-hidden': 'true' }, s('path', { d: 'M8 2l6.5 11.5h-13z' }), s('path', { d: 'M8 7v3' }), s('path', { d: 'M8 12v0.5' })),
  info: () => s('svg', { width: 16, height: 16, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'aria-hidden': 'true' }, s('circle', { cx: 8, cy: 8, r: 6.5 }), s('path', { d: 'M8 7v4' }), s('path', { d: 'M8 4.8v0.4' })),
  close: () => s('svg', { width: 16, height: 16, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'aria-hidden': 'true' }, s('path', { d: 'M4 4l8 8M12 4l-8 8' })),
  upload: () => s('svg', { width: 28, height: 28, viewBox: '0 0 24 24', fill: 'none', stroke: '#575B60', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' }, s('path', { d: 'M12 15V4' }), s('path', { d: 'M7.5 8.5L12 4l4.5 4.5' }), s('path', { d: 'M4 15v4h16v-4' })),
};

const STATUS = { done: 'Done', running: 'Running', queued: 'Queued', failed: 'Failed', cancelled: 'Cancelled', interrupted: 'Interrupted' };

export function pill(status) {
  return h('span', { class: ['pill', `s-${status}`] }, h('span', { class: 'dot' }), STATUS[status] || status);
}

export function cells(states) {
  const text = states.map((st, i) => `${i + 1} ${st}`).join(', ');
  return h('span', { class: 'cells', role: 'img', 'aria-label': text, title: text },
    states.map((st) => h('span', { class: ['cell', st] })));
}

export function header(active) {
  const link = (href, label, key) => h('a', { href, 'aria-current': active === key ? 'page' : null }, label);
  return h('header', { class: 'top' },
    h('button', { type: 'button', class: 'skip', onClick: skipToContent }, 'Skip to content'),
    h('a', { href: '#/runs', class: 'brand' }, h('img', { src: '/static/brand/ergo-logo.png', alt: 'Ergo', height: 28 })),
    h('nav', { 'aria-label': 'Main' }, link('#/tasks', 'Tasks', 'tasks'), link('#/runs', 'Runs', 'runs'), link('/atlas', 'Atlas', 'atlas')),
    h('div', { class: 'top-end' }, workspaceName(), modelChip()));
}

function workspaceName() {
  const el = h('span', { class: 'workspace', title: 'Workspace' });
  settings().then((st) => { el.textContent = st?.workspace || ''; });
  return el;
}

// Hash routes own location.hash, so the skip link moves focus itself.
function skipToContent() {
  const wrap = document.querySelector('.wrap');
  if (!wrap) return;
  wrap.setAttribute('tabindex', '-1');
  wrap.focus();
}

export function card(...children) {
  return h('section', { class: 'card' }, ...children);
}

export function table(columns, rows, opts = {}) {
  return h('div', { class: 'table-box' },
    h('table', { class: 't', style: { minWidth: opts.minWidth || '640px' } },
      opts.caption ? h('caption', {}, opts.caption) : null,
      h('thead', {}, h('tr', {}, columns.map((c) => h('th', { scope: 'col', class: c.num ? 'num' : null }, c.label)))),
      h('tbody', {}, rows.map((r, i) => h('tr', { class: [opts.selected?.(r) && 'selected', opts.onRow && 'clickable'], onClick: opts.onRow ? () => opts.onRow(r, i) : null },
        columns.map((c) => h('td', { class: c.num ? 'num' : null }, c.cell ? c.cell(r, i) : r[c.key])))))));
}

export function runTabs(run, active, available = {}) {
  const tab = (href, label, key) => h('a', { href, 'aria-current': active === key ? 'page' : null, class: available[key] === false ? 'off' : null }, label);
  const base = `#/runs/${encodeURIComponent(run)}`;
  return h('nav', { class: 'tabs', 'aria-label': 'Run sections' },
    tab(base, 'Overview', 'overview'), tab(`${base}/clusters`, '2 · Clusters', 'clusters'), tab(`${base}/trees`, '3 · Trees', 'trees'),
    tab(`${base}#candidates`, '4 · Candidates', 'candidates'), tab(`${base}#residuals`, '7 · Residuals', 'residuals'), tab(`${base}/flow`, 'Control flow', 'flow'));
}

export function valuePicker(values, current, go) {
  if (!values || values.length < 2) return null;
  return h('label', { class: 'field', style: { maxWidth: '320px' } }, 'Value column',
    h('select', { class: 'input mono', onChange: (e) => go(e.target.value) }, values.map((v) => h('option', { value: v, selected: v === current ? true : null }, v))));
}

export function loading(root, active) {
  mount(root, header(active), h('div', { class: 'wrap' }, h('p', { class: 'spinner' }, 'Loading…')));
}

export function failure(root, active, error) {
  mount(root, header(active), h('div', { class: 'wrap' }, h('div', { class: 'banner bad', role: 'alert' }, icons.info(), h('span', {}, error.message || String(error)))));
}

export const clusterColors = ['var(--c0)', 'var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--c5)', 'var(--c6)', 'var(--c7)'];
export const clusterInk = ['#fff', '#fff', '#1A1C1E', '#fff', '#fff', '#fff', '#fff', '#fff'];

export function swatch(index, label) {
  const i = index === null || index === undefined ? null : index % clusterColors.length;
  return h('span', { class: 'swatch', style: { background: i === null ? '#C4C5C0' : clusterColors[i], color: i === null ? '#1A1C1E' : clusterInk[i] } }, label);
}

// Polylines of a laid-out diagram (coordinates from layout.py), with an arrow head at the end.
let markerId = 0;
export function edges(diagram, colorOf = () => '#8A8D90', opts = {}) {
  const id = `arrow-${++markerId}`;
  const svg = s('svg', { class: 'edges', width: diagram.width, height: diagram.height, 'aria-hidden': 'true' },
    s('defs', {}, s('marker', { id, orient: 'auto', markerWidth: 6, markerHeight: 6, refX: 5, refY: 3 }, s('path', { d: 'M0 0 L6 3 L0 6 Z', fill: 'context-stroke' }))));
  for (const e of diagram.edges) {
    const color = colorOf(e);
    svg.append(s('polyline', { points: e.points.map((p) => p.join(',')).join(' '), fill: 'none', stroke: color, 'stroke-width': 2,
      'stroke-linejoin': 'round', 'stroke-linecap': 'round', 'marker-end': opts.arrows === false ? null : `url(#${id})`,
      'stroke-dasharray': e.kind === 'temporal' ? '6 6' : null, opacity: opts.opacityOf ? opts.opacityOf(e) : null }));
  }
  return svg;
}

// JSON, commands and file names fold away for whoever does not need them; opened once, a kind stays open in this browser.
export function tech(kind, summary, children, cls) {
  let open = false;
  try { open = localStorage.getItem(`ergo-tech-${kind}`) === 'open'; } catch (e) { /* closed by default */ }
  const el = h('details', { class: ['tech', cls], open: open || null }, h('summary', {}, summary), children);
  el.addEventListener('toggle', () => { try { localStorage.setItem(`ergo-tech-${kind}`, el.open ? 'open' : 'closed'); } catch (e) { /* memory only */ } });
  return el;
}

// Plain language or codes on the diagrams: a choice of the viewer, kept in this browser.
export function wordsMode() {
  try { return localStorage.getItem('ergo-words') || 'plain'; } catch (e) { return 'plain'; }
}

export function wordsSwitch(mode, change) {
  const pick = (m) => () => { try { localStorage.setItem('ergo-words', m); } catch (e) { /* memory only */ } change(m); };
  return h('div', { class: 'segmented', role: 'group', 'aria-label': 'Labels' },
    h('button', { type: 'button', 'aria-pressed': String(mode === 'plain'), onClick: pick('plain') }, 'Plain language'),
    h('button', { type: 'button', 'aria-pressed': String(mode === 'codes'), onClick: pick('codes') }, 'Codes'));
}

export function fmtInt(n) {
  return n === null || n === undefined ? '—' : Number(n).toLocaleString('en-US').replace(/,/g, ' ');
}
