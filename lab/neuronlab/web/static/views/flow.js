// Control flow: the candidate as a graph and as the code freeze writes, replayed on a target row or custom values.
// The server computes the value (evaluate.predicted, exact decimals); the page only animates the path it returns.
import { edges, get, h, header, icons, loading, mount, post, runTabs, start, toast, valuePicker, wordsMode, wordsSwitch } from '../lib/h.js';

export async function render(root, { run, query }) {
  loading(root, 'runs');
  const value = query.get('value');
  const candidate = query.get('candidate');
  const params = new URLSearchParams();
  if (value) params.set('value', value);
  if (candidate) params.set('candidate', candidate);
  const d = await get(`/api/runs/${encodeURIComponent(run)}/flow?${params}`);
  const base = `#/runs/${encodeURIComponent(run)}`;
  const speed = 550;
  let preset = d.presets?.[0]?.key || null;
  let custom = null; // {feature: text} when the person edits values
  let result = null;
  let step = 0;
  let timer = null;
  let mode = wordsMode();

  const sequence = () => {
    if (!result) return [];
    return [['in'], ...result.path.map((id) => [id]), ['compute'], ['result']];
  };

  const play = () => {
    clearInterval(timer);
    step = 1;
    draw();
    timer = setInterval(() => {
      if (step >= sequence().length) { clearInterval(timer); return; }
      step += 1;
      draw();
    }, speed);
  };

  const evaluate = async () => {
    if (!preset) return;
    try {
      result = await post('/api/flow/eval', { run, value: d.value, candidate: d.candidate, key: preset, inputs: custom });
      play();
    } catch (e) {
      toast(e.message, true);
    }
  };

  const draw = () => {
    if (d.missing) {
      mount(root, header('runs'), h('div', { class: 'wrap' }, runTabs(run, 'flow'), h('p', { class: 'empty' }, `No ${d.missing} in this run yet.`)));
      return;
    }
    const seq = sequence();
    const done = result && step >= seq.length;
    const lit = new Set(seq.slice(0, step).flat());
    const now = new Set(step > 0 ? seq[step - 1] : []);
    const onPath = new Set(seq.flat());
    mount(root, header('runs'), h('div', { class: 'wrap' },
      h('div', { class: 'stack-8' },
        h('div', { class: 'crumbs' }, h('a', { href: '#/runs' }, 'Runs'), ' / ', h('a', { href: base, class: 'mono' }, run), ' / Control flow'),
        h('h1', {}, 'Control flow of the derived code'),
        h('p', { class: 'small muted', style: { maxWidth: '820px' } }, `Candidate ${d.candidate} (${d.name}): ${d.score.total} of the rows exact, ${d.score.holdout} on the holdout. Choose a row of the target, or change its values: the run moves down from the inputs, takes the branch each condition decides, and ends on the value.`)),
      runTabs(run, 'flow'),
      valuePicker(d.values, d.value, (v) => { location.hash = `${base}/flow?value=${encodeURIComponent(v)}`; }),
      d.replay ? null : h('div', { class: 'banner' }, icons.info(), h('span', { style: { flex: '1 1 400px' } }, 'The frame of this run is not on this machine (parquet files are not versioned), so rows cannot be replayed: the graph and the code are shown. '),
        h('button', { type: 'button', class: 'btn small', onClick: () => start('run', d.task, { steps: ['profile', 'frame', 'cluster', 'tree', 'pool', 'iterate', 'report'] }) }, 'Run the pipeline')),
      d.freeze ? h('div', { class: 'banner warn' }, icons.info(), h('span', { style: { flex: '1 1 400px' } }, `Freeze cannot write this candidate: ${d.freeze}`)) : null,
      h('section', { 'aria-label': 'Inputs', class: 'card tight', style: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'flex-end', gap: '20px' } },
        h('div', { class: 'row', style: { flex: '999 1 640px', minWidth: 0, alignItems: 'flex-end' } },
          h('label', { class: 'field', style: { flex: '1 1 280px' } }, 'Start from',
            h('select', { class: 'input mono', onChange: (e) => { preset = JSON.parse(e.target.value); custom = null; evaluate(); } },
              d.presets.map((p) => h('option', { value: JSON.stringify(p.key), selected: JSON.stringify(p.key) === JSON.stringify(preset) ? true : null }, p.label)))),
          (result ? Object.keys(result.inputs) : d.features).map((f) => h('label', { class: 'field', style: { flex: '1 1 150px' } },
            mode === 'plain' && d.subjects?.[f] ? h('span', { title: f }, d.subjects[f]) : h('span', { class: 'mono' }, f),
            h('input', { class: 'input mono', value: (custom && f in custom) ? custom[f] : (result?.inputs[f] ?? ''), onChange: (e) => { custom = { ...(custom || {}), [f]: e.target.value }; evaluate(); } }))),
          h('div', { class: 'row', style: { gap: '8px' } },
            h('button', { type: 'button', class: 'btn primary', onClick: evaluate }, 'Run'),
            h('button', { type: 'button', class: 'btn', onClick: () => { clearInterval(timer); step = step >= seq.length ? 1 : step + 1; draw(); } }, 'Step'),
            custom ? h('button', { type: 'button', class: 'btn', onClick: () => { custom = null; evaluate(); } }, 'Reset values') : null)),
        h('div', { role: 'status', 'aria-live': 'polite', class: 'tint', style: { flex: '1 1 260px', padding: '14px 16px', borderRadius: '8px' } },
          h('span', { class: 'small muted mono' }, d.value),
          h('span', { class: 'mono', style: { fontSize: '24px', fontWeight: 500, lineHeight: 1.2 } }, done ? result.computed ?? 'null' : '…'),
          h('span', { class: 'small', style: { color: !done ? 'var(--muted)' : result.equal ? 'var(--ok)' : result.equal === false ? 'var(--warn)' : 'var(--muted)' } },
            !done ? (result ? 'Running…' : 'Pick a row') : result.equal ? 'Equals the target file' : result.equal === false ? `Target file: ${result.target}` : 'Custom values: no target row to compare'))),
      h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('div', { class: 'stack' }, h('h2', {}, 'Graph'), h('span', { class: 'small muted' }, 'Leaves show the constant of each branch; counts are rows of the tree of step 3')),
        wordsSwitch(mode, (m) => { mode = m; draw(); })),
        graph(d.diagram, lit, now, done ? onPath : null, mode)),
      h('div', { class: 'row', style: { gap: '20px', alignItems: 'flex-start' } },
        codePanel(d, result, lit, now, step, seq.length),
        h('section', { class: 'card tight', style: { flex: '2 1 380px', minWidth: 0 } }, h('h3', {}, 'Trace'),
          h('ol', { style: { listStyle: 'none', margin: 0, padding: 0 } }, ((mode === 'plain' ? result?.say : null) || result?.trace || []).map((t, i) => h('li', { class: 'row', style: { gap: '12px', padding: '8px 0', borderTop: '1px solid var(--divider)', opacity: i < Math.max(1, step - 1) || done ? 1 : 0.3, flexWrap: 'nowrap' } },
            h('span', { class: 'mono tiny muted', style: { width: '18px', paddingTop: '2px' } }, i + 1), h('span', { class: mode === 'plain' && result?.say ? 'small' : 'mono small', style: { overflowWrap: 'anywhere' } }, t))))))));
  };

  draw();
  if (d.replay) evaluate();
  return () => clearInterval(timer);
}

function graph(diagram, lit, now, dimOff, mode) {
  const nodes = diagram.nodes.map((n) => {
    const on = lit.has(n.id);
    const box = { left: `${n.x}px`, top: `${n.y}px`, width: `${n.w}px`, height: `${n.h}px` };
    const dim = dimOff && !dimOff.has(n.id);
    const cls = ['node', n.kind === 'split' && 'decision', n.kind === 'result' && 'result', on && 'on', now.has(n.id) && 'now', dim && 'dim'];
    const code = n.kind === 'split' ? (n.value === 'true' ? n.feature : `${n.feature} = ${n.value}`) : n.kind === 'leaf' ? `c = ${n.label}` : n.label;
    if (mode === 'plain' && n.say) {
      return h('div', { class: cls, style: box, title: code }, h('span', {}, h('span', { class: 'say' }, n.say), h('span', { class: 'code-line' }, code)));
    }
    if (n.kind === 'split') return h('div', { class: cls, style: box }, h('span', {}, h('b', {}, n.feature), h('br'), h('span', {}, n.value === 'true' ? 'holds?' : `= ${n.value} ?`)));
    if (n.kind === 'leaf') return h('div', { class: cls, style: box }, h('span', {}, h('span', { class: 'tiny muted' }, 'c = '), h('b', {}, n.label), n.rows ? [h('br'), h('span', { class: 'tiny muted' }, `${n.rows} rows`)] : null));
    return h('div', { class: cls, style: box }, h('b', {}, n.label));
  });
  const labels = diagram.edges.filter((e) => e.branch).map((e) => {
    const [x, y] = e.points.length > 2 ? e.points[2] : e.points[1];
    return h('span', { class: 'edge-label', style: { left: `${x + (e.branch === 'yes' ? -18 : 14)}px`, top: `${y + 12}px` } }, e.branch);
  });
  return h('div', { class: 'diagram-box' }, h('div', { class: 'diagram', style: { width: `${diagram.width}px`, height: `${diagram.height}px` } },
    edges(diagram, (e) => (lit.has(e.from) && lit.has(e.to) ? 'var(--accent)' : '#A9ABA5'), { opacityOf: (e) => (dimOff && !(dimOff.has(e.from) && dimOff.has(e.to)) ? 0.3 : 1) }),
    nodes, labels));
}

function codePanel(d, result, lit, now, step, total) {
  const style = { flex: '3 1 560px', minWidth: 0 };
  if (!d.code.length) {
    const hand = d.hand_written;
    return h('section', { class: 'dark', style }, h('div', { class: 'row-between' }, h('h2', {}, hand ? `${hand.file} · written by hand` : 'No code template'),
      h('span', { class: 'tiny muted' }, hand ? 'the function submission.py runs for this task' : '')),
      h('p', { class: 'small muted' }, hand ? 'Freeze has no template for this candidate, so the graph shows the lab’s rule and the code below is the hand-written function that check.py scores. It runs on whole tables, not row by row: no line is lit.' : d.freeze),
      hand ? h('pre', { class: 'code', style: { padding: 0, background: 'transparent', maxHeight: '520px', overflow: 'auto' } }, hand.source) : null);
  }
  const rule = result?.rule;
  const atLeaf = result && result.path.every((id) => lit.has(id));
  const computing = lit.has('compute');
  const firstRule = d.code.findIndex((l) => l.rule !== undefined);
  const lastRule = d.code.length - 1 - [...d.code].reverse().findIndex((l) => l.rule !== undefined);
  return h('section', { class: 'dark', style }, h('div', { class: 'row-between' }, h('h2', {}, `submission.py · ${d.task}`), h('span', { class: 'tiny muted' }, 'the code freeze writes; lines on the path light up')),
    h('div', { class: 'codelines' }, d.code.map((l, i) => {
      let cls = null;
      if (step > 0 && (firstRule < 0 || i < firstRule)) cls = 'lit';
      if (l.rule !== undefined && result) {
        if (l.rule === rule && atLeaf) cls = now.has(result.leaf) ? 'now' : 'lit';
        else if (rule !== null && l.rule < rule && l.test && atLeaf) cls = 'tested';
      }
      if (firstRule >= 0 && i > lastRule && computing) cls = now.has('compute') || now.has('result') ? 'now' : 'lit';
      if (firstRule < 0 && computing) cls = 'lit';
      return h('div', { class: cls }, h('span', { class: 'n' }, l.n), h('span', {}, l.src));
    })),
    step >= total && result ? h('p', { class: 'tiny muted' }, `${rule === null || rule === undefined ? 'a lookup' : `rule ${rule + 1}`} decided the constant ${result.constant}`) : null);
}
