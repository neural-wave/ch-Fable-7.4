// Runs: every run of the pipeline, of step 5, of scoring, of ablation and of the agent. Newest first.
import { cells, get, h, header, loading, mount, pill, post, start, table, toast } from '../lib/h.js';

const PAGE = 25;
const state = { kind: 'All', task: 'All tasks', search: '', page: 0 };

const KIND_ACTION = { Pipeline: 'run', 'Step 5': 'suggest', Score: 'score', Ablation: 'ablate' };

export async function render(root) {
  loading(root, 'runs');
  let data = await get('/api/runs');
  let timer = null;

  const draw = () => {
    const rows = data.runs.filter((r) => (state.kind === 'All' || r.kind === state.kind)
      && (state.task === 'All tasks' || r.task === state.task)
      && (!state.search || `${r.run} ${r.task} ${r.candidate || ''} ${r.note}`.toLowerCase().includes(state.search.toLowerCase())));
    const pages = Math.max(1, Math.ceil(rows.length / PAGE));
    state.page = Math.min(state.page, pages - 1);
    const shown = rows.slice(state.page * PAGE, (state.page + 1) * PAGE);
    const taskNames = [...new Set(data.runs.map((r) => r.task))].sort();

    const search = h('input', { id: 'runSearch', type: 'search', class: 'input', placeholder: 'Run, task or candidate', value: state.search,
      onInput: (e) => { state.search = e.target.value; state.page = 0; redraw(true); } });
    mount(root, header('runs'), h('div', { class: 'wrap' },
      h('div', { class: 'row-end' },
        h('div', { class: 'stack' }, h('h1', {}, 'Runs'),
          h('p', { class: 'muted small' }, 'Every run of the pipeline, of the language-model step, of scoring, of ablation and of the agent. Newest first.')),
        h('div', { class: 'row' },
          h('button', { type: 'button', class: 'btn', onClick: () => unattended(data) }, 'Run every task unattended'),
          h('button', { type: 'button', class: 'btn primary', onClick: () => newRun(data) }, 'New run'))),
      h('section', { 'aria-label': 'Latest result per task', class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))' } },
        data.tasks.map((t) => h('a', { href: `#/runs/${encodeURIComponent(t.id)}`, class: 'card tight', style: { textDecoration: 'none', color: 'inherit', gap: '6px', padding: '16px' } },
          h('span', { class: 'row-between' }, h('span', { class: 'mono strong small' }, t.id), stateDot(t.state)),
          h('span', { class: 'tiny muted' }, 'Holdout, exact'),
          h('span', { class: 'mono', style: { fontSize: '24px', fontWeight: 500, lineHeight: 1.2 } }, t.holdout),
          h('span', { class: 'small muted' }, t.frozen)))),
      h('section', { class: 'card flush' },
        h('div', { class: 'row', style: { padding: '16px 20px', borderBottom: '1px solid var(--divider)', alignItems: 'flex-end' } },
          h('label', { class: 'field', style: { flex: '1 1 260px' } }, 'Search', search),
          h('label', { class: 'field', style: { flex: '0 1 240px' } }, 'Task',
            h('select', { class: 'input', onChange: (e) => { state.task = e.target.value; state.page = 0; redraw(); } },
              ['All tasks', ...taskNames].map((n) => h('option', { selected: n === state.task ? true : null }, n)))),
          h('fieldset', { style: { border: 0, margin: 0, padding: 0 } },
            h('legend', { class: 'small strong', style: { padding: 0, marginBottom: '6px' } }, 'Kind'),
            h('div', { class: 'segmented' }, data.kinds.map((k) => h('button', { type: 'button', 'aria-pressed': String(k === state.kind),
              onClick: () => { state.kind = k; state.page = 0; redraw(); } }, k))))),
        rows.length ? table([
          { label: 'Status', cell: (r) => pill(r.status) },
          { label: 'Run', cell: (r) => h('a', { href: r.job ? `#/jobs/${r.id}` : `#/runs/${encodeURIComponent(r.run)}`, class: 'mono strong', style: { fontSize: '13.5px' } }, r.run) },
          { label: 'Kind', cell: (r) => h('span', { class: 'muted' }, r.kind) },
          { label: 'Steps', cell: (r) => cells(r.steps) },
          { label: 'Started', cell: (r) => h('span', { style: { whiteSpace: 'nowrap' } }, r.started) },
          { label: 'Took', num: true, key: 'took' },
          { label: 'Discovery', num: true, key: 'disc' },
          { label: 'Holdout', num: true, cell: (r) => [r.hold, ' ', h('span', { class: 'tiny', style: { color: (r.delta || '').startsWith('-') ? 'var(--bad)' : 'var(--ok)' } }, (r.delta || '').replace('-', '−'))] },
          { label: 'Winner or reason', cell: (r) => h('span', { style: { color: ['failed', 'interrupted'].includes(r.status) ? 'var(--bad)' : null } }, r.note) },
        ], shown, { minWidth: '1080px' }) : h('p', { class: 'empty', style: { margin: '20px' } }, 'No run matches.'),
        h('div', { class: 'row-between small muted', style: { padding: '12px 20px', borderTop: '1px solid var(--divider)' } },
          h('span', { class: 'row', style: { gap: '16px' } }, legend('done', 'done'), legend('running', 'running'), legend('skipped', 'reused or not in this run'), legend('failed', 'failed'), legend('waiting', 'waiting')),
          h('span', { class: 'row', style: { gap: '8px' } }, `Showing ${rows.length ? state.page * PAGE + 1 : 0}–${Math.min(rows.length, (state.page + 1) * PAGE)} of ${rows.length}`,
            h('button', { type: 'button', class: 'icon-btn', 'aria-label': 'Previous page', disabled: state.page === 0 ? true : null, onClick: () => { state.page -= 1; redraw(); } }, '‹'),
            h('button', { type: 'button', class: 'icon-btn', 'aria-label': 'Next page', disabled: state.page >= pages - 1 ? true : null, onClick: () => { state.page += 1; redraw(); } }, '›'))))));
    return search;
  };

  const redraw = (keepFocus) => {
    const search = draw();
    if (keepFocus) { search.focus(); search.setSelectionRange(search.value.length, search.value.length); }
  };
  draw();
  const refresh = async () => {
    if (data.runs.some((r) => r.status === 'running' || r.status === 'queued') && !document.activeElement?.matches('input, select')) {
      data = await get('/api/runs').catch(() => data);
      draw();
    }
  };
  timer = setInterval(refresh, 4000);
  return () => clearInterval(timer);
}

function stateDot(status) {
  const colors = { done: 'var(--ok-dot)', running: 'var(--ink)', failed: 'var(--accent)', queued: 'var(--control)' };
  const label = { done: 'Done', running: 'Running', failed: 'Failed', queued: 'Queued', cancelled: 'Cancelled', interrupted: 'Interrupted' }[status] || status;
  return h('span', { class: 'row tiny', style: { gap: '6px' } }, h('span', { class: 'dot', style: { background: colors[status] || 'var(--faint)' } }), label);
}

function legend(state_, label) {
  return h('span', { class: 'row', style: { gap: '6px' } }, h('span', { class: ['cell', state_] }), label);
}

function dialog(title, body, actions) {
  const el = h('dialog', { style: { border: '1px solid var(--line)', borderRadius: '8px', padding: '24px', maxWidth: '560px', width: 'calc(100% - 32px)' } },
    h('form', { method: 'dialog', class: 'stack-16' }, h('h2', {}, title), body,
      h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, h('button', { class: 'btn', value: 'cancel' }, 'Cancel'), actions)));
  document.body.append(el);
  el.addEventListener('close', () => el.remove());
  el.showModal();
  return el;
}

function newRun(data) {
  const tasks = [...new Set(data.tasks.map((t) => t.id))];
  const task = h('select', { class: 'input mono' }, tasks.map((t) => h('option', {}, t)));
  const kind = h('select', { class: 'input' }, Object.keys(KIND_ACTION).map((k) => h('option', {}, k)));
  const go = h('button', { class: 'btn primary', value: 'go' }, 'Start');
  const el = dialog('New run', h('div', { class: 'stack-12' },
    h('label', { class: 'field' }, 'Task', task),
    h('label', { class: 'field' }, 'Kind', kind),
    h('p', { class: 'small muted' }, 'Pipeline runs steps 1–4, 6 and 7. Step 5 asks the language model for features. Score runs submission.py. Ablation switches each rule card off.')), go);
  go.addEventListener('click', () => { el.close(); start(KIND_ACTION[kind.value], task.value); });
}

function unattended(data) {
  const scored = data.tasks.map((t) => t.id).filter((t) => /^t\d_/.test(t) && !t.includes('projection_year') && !t.includes('holding') && !t.includes('booking'));
  const boxes = scored.map((t) => h('label', { class: 'check' }, h('input', { type: 'checkbox', value: t, checked: t !== 't0_commission' ? true : null }), h('span', { class: 'mono' }, t)));
  const go = h('button', { class: 'btn primary', value: 'go' }, 'Queue the sessions');
  const el = dialog('Run every task unattended', h('div', { class: 'stack-12' },
    h('p', { class: 'small muted' }, 'One headless Claude Code session per task, one after the other, with the skill rule-discovery: the same as lab agent. Each session edits submission.py.'),
    h('div', {}, boxes)), go);
  go.addEventListener('click', async () => {
    el.close();
    const chosen = boxes.map((b) => b.querySelector('input')).filter((i) => i.checked).map((i) => i.value);
    if (!chosen.length) return;
    try {
      let first = null;
      for (const t of chosen) {
        const job = await post('/api/jobs', { action: 'agent', task: t });
        first = first || job;
      }
      location.hash = `#/jobs/${first.id}`;
    } catch (e) {
      toast(e.message, true);
    }
  });
}
