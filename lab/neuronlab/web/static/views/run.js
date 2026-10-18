// Run · finished: scores, the seven steps, the candidates, the wrong rows, the language model, related runs.
import { card, confirmFreeze, get, h, header, icons, loading, mount, modelNotice, pill, runTabs, start, table, tech, term, valuePicker } from '../lib/h.js';

const TONE = { ink: 'var(--ink)', muted: 'var(--control)', accent: 'var(--accent)' };
const ACTION_HREF = { trees: 'trees', clusters: 'clusters' };

export async function render(root, { run, anchor, query }) {
  loading(root, 'runs');
  const value = query.get('value');
  const d = await get(`/api/runs/${encodeURIComponent(run)}${value ? `?value=${encodeURIComponent(value)}` : ''}`);
  const base = `#/runs/${encodeURIComponent(run)}`;
  const status = d.record?.status || (d.scores ? 'done' : 'queued');
  const freezeWinner = () => confirmFreeze(d.task, run, d.winner);

  mount(root, header('runs'), h('div', { class: 'wrap' },
    h('div', { class: 'row-end' },
      h('div', { class: 'stack-8' },
        h('div', { class: 'crumbs' }, h('a', { href: '#/runs' }, 'Runs'), ` / ${run}`),
        h('div', { class: 'row' }, h('h1', { class: 'mono' }, run), pill(status)),
        h('div', { class: 'small muted' }, [d.kind, d.record ? `started ${d.record.started.toLowerCase()}` : null,
          d.record && d.record.took !== '—' ? `took ${d.record.took}` : null].filter(Boolean).join(' · '))),
      h('div', { class: 'row' },
        h('button', { type: 'button', class: 'btn', onClick: () => start('suggest', d.task) }, 'Suggest features'),
        h('button', { type: 'button', class: 'btn', disabled: d.cannot.ablate ? true : null, title: d.cannot.ablate || null, onClick: () => start('ablate', d.task) }, 'Ablate rules'),
        h('button', { type: 'button', class: 'btn primary', disabled: d.freeze || !d.winner ? true : null, title: d.freeze || null, onClick: freezeWinner }, 'Freeze winner'))),
    runTabs(run, 'overview'),
    valuePicker(d.values, d.value, (v) => { location.hash = `${base}?value=${encodeURIComponent(v)}`; }),
    frozenBanner(d),
    d.freeze ? h('div', { class: 'banner warn', role: 'status' }, icons.info(), h('span', { style: { flex: '1 1 400px' } }, `Freeze: ${d.freeze}`)) : null,
    d.scores ? h('section', { 'aria-label': 'Scores', class: 'grid' },
      stat([term('Discovery'), ', exact'], d.scores.discovery, `${num(d.scores.discovery_pair[0])} of ${num(d.scores.discovery_pair[1])} rows`),
      stat([term('Holdout'), ', exact'], d.scores.holdout, `${num(d.scores.holdout_pair[0])} of ${num(d.scores.holdout_pair[1])} rows · 1 policy in 5`),
      stat(term('Wrong rows'), num(d.scores.wrong), `${num(d.scores.wrong_disc)} in discovery · ${num(d.scores.wrong_hold)} in holdout`),
      stat(term('Typed by hand'), num(d.scores.by_hand), 'wrong rows of policies listed in NREXCP')) :
      h('p', { class: 'empty' }, 'This run has no pool yet: run the pipeline first.'),
    h('div', { class: 'columns' },
      h('main', { class: 'main' },
        card(h('h2', {}, 'Pipeline'),
          h('ol', { class: 'steps' }, d.steps.map((st) => stepCard(st, run, base)))),
        d.candidates.length ? card(
          h('div', { class: 'card-head', id: 'candidates' },
            h('div', { class: 'stack' }, h('h2', {}, 'Candidates'), h('p', { class: 'small muted' }, `${d.pool_size} in the pool of step 4, scored exactly in step 6. Best ones first, ranked by holdout.`))),
          table([
            { label: term('Candidate'), cell: (c) => h('span', { class: 'stack' }, c.winner ? h('span', { class: 'chip accent', style: { alignSelf: 'flex-start' } }, 'Winner') : null,
              h('span', { style: { fontWeight: 500 } }, c.name), h('span', { class: 'small muted' }, `${c.id} · ${c.origin}${c.tie ? ' · ties with the winner' : ''}`)) },
            { label: 'Features', cell: (c) => h('span', { class: 'mono', style: { fontSize: '12.5px', whiteSpace: 'pre-line' } }, c.features.join('\n') || '—') },
            { label: 'Leaves', num: true, key: 'leaves' },
            { label: 'Discovery', num: true, key: 'disc' },
            { label: 'Holdout', num: true, cell: (c) => h('span', { style: { fontWeight: c.winner ? 600 : 400 } }, c.hold) },
            { label: h('span', { class: 'sr' }, 'Action'), cell: (c) => h('span', { class: 'actions' },
              h('a', { class: 'btn small', href: `${base}/flow?candidate=${encodeURIComponent(c.id)}${d.value ? `&value=${encodeURIComponent(d.value)}` : ''}` }, 'Flow'),
              h('button', { type: 'button', class: 'btn small', disabled: c.freeze ? true : null, title: c.freeze || `Write ${c.id} into submission.py and check it`,
                onClick: () => confirmFreeze(d.task, run, c.id) }, 'Freeze')) },
          ], d.candidates, { minWidth: '860px', selected: (c) => c.winner })) : null,
        d.residuals.length ? card(
          h('div', { class: 'stack', id: 'residuals' }, h('h2', {}, 'Wrong rows of the winner'),
            h('p', { class: 'small muted' }, 'Residuals by kind, from step 7. Rows typed by hand are left out of the rules on purpose.')),
          h('div', {}, d.residuals.map((r) => h('div', { class: 'row', style: { padding: '14px 0', borderTop: '1px solid var(--divider)', gap: '8px 20px' } },
            h('span', { class: 'stack', style: { flex: '1 1 260px' } }, h('span', { style: { fontWeight: 500 } }, r.kind), h('span', { class: 'small muted' }, r.detail)),
            h('span', { class: 'row', style: { flex: '2 1 220px', gap: '12px' } }, h('span', { class: 'bar' }, h('i', { style: { width: r.width, background: TONE[r.tone] } })),
              h('span', { class: 'mono strong', style: { width: '56px', textAlign: 'right' } }, num(r.count))),
            actionLink(r, d, base))))) : null,
        proposalsCard(d)),
      h('aside', { class: 'aside', 'aria-label': 'About this run' },
        h('section', { class: 'card tight' }, h('h3', {}, 'Run'),
          h('dl', { style: { margin: 0, display: 'grid', gridTemplateColumns: 'max-content minmax(0, 1fr)', gap: '8px 16px', fontSize: '14px' } },
            h('dt', { class: 'muted' }, 'Task'), h('dd', { style: { margin: 0 } }, h('a', { href: `#/tasks/${encodeURIComponent(d.task)}/review`, class: 'rowlink small' }, d.task)),
            h('dt', { class: 'muted' }, term('Holdout')), h('dd', { style: { margin: 0 }, class: 'small' }, '1 policy in 5')),
          tech('cli', 'Files and command line', h('div', { class: 'stack-8' },
            h('dl', { style: { margin: 0, display: 'grid', gridTemplateColumns: 'max-content minmax(0, 1fr)', gap: '8px 16px', fontSize: '14px' } },
              h('dt', { class: 'muted' }, 'Definition'), h('dd', { style: { margin: 0 }, class: 'mono small' }, `tasks/${d.task}.json`),
              h('dt', { class: 'muted' }, 'Rules'), h('dd', { style: { margin: 0 }, class: 'mono small' }, `rules/${d.task}.json`),
              h('dt', { class: 'muted' }, 'Holdout'), h('dd', { style: { margin: 0 }, class: 'mono small' }, 'crc32(policy) % 5 == 0')),
            h('pre', { class: 'code' }, d.commands.run))),
          h('div', { class: 'row', style: { gap: '8px' } },
            h('button', { type: 'button', class: 'btn small', onClick: () => start('run', d.task) }, 'Run again'),
            h('button', { type: 'button', class: 'btn small', disabled: d.cannot.score ? true : null, title: d.cannot.score || null, onClick: () => start('score', d.task) }, 'Score submission'),
            d.files.includes('report.md') ? h('a', { class: 'btn small', href: `/files/${encodeURIComponent(run)}/report.md` }, 'Open report.md') : null)),
        h('section', { class: 'card tight' }, h('h3', {}, 'Related runs'),
          d.related.length ? h('ul', { style: { listStyle: 'none', margin: 0, padding: 0 } }, d.related.map((x) => h('li', { class: 'stack', style: { padding: '10px 0', borderTop: '1px solid var(--divider)' } },
            h('a', { href: `#/runs/${encodeURIComponent(x.run)}`, class: 'rowlink small', style: { overflowWrap: 'anywhere' } }, x.run),
            h('span', { class: 'row-between small muted' }, h('span', {}, x.what), h('span', { style: { color: 'var(--ink)', fontWeight: 500 } }, x.score))))) :
            h('p', { class: 'small muted' }, 'No other run of this task.')),
        h('section', { class: 'card tight' }, h('h3', {}, 'Look closer'),
          h('a', { href: '/atlas', class: 'small' }, 'Before / after of each rule in the atlas'),
          d.files.includes('notes.md') ? h('a', { href: `/files/${encodeURIComponent(run)}/notes.md`, class: 'small' }, 'Notes of the agent') : null,
          tech('files', 'Raw files', h('div', { class: 'stack-8' },
            h('a', { href: `/files/${encodeURIComponent(run)}/ledger.jsonl`, class: 'small' }, 'Every scored candidate in ledger.jsonl'),
            h('a', { href: `/files/${encodeURIComponent(run)}/pool.json`, class: 'small' }, `All ${d.pool_size ?? ''} candidates in pool.json`),
            d.files.filter((f) => f.startsWith('agent-')).slice(-2).map((f) => h('a', { href: `/files/${encodeURIComponent(run)}/${f}`, class: 'small mono' }, f)))))))));
  if (anchor) document.getElementById(anchor)?.scrollIntoView();
}

function num(n) {
  return n === null || n === undefined ? '—' : Number(n).toLocaleString('en-US').replace(/,/g, ' ');
}

function stat(label, big, small) {
  const m = /^([\d.]+)\s*%$/.exec(big || '');
  return h('div', { class: 'stat' }, h('span', { class: 'small muted' }, label), h('span', { class: 'big' }, m ? [m[1], h('small', {}, '%')] : big), h('span', { class: 'small muted' }, small));
}

function frozenBanner(d) {
  const f = d.frozen;
  if (!f) return null;
  if (d.cannot.score) return h('div', { class: 'banner', role: 'status' }, icons.info(), h('span', { style: { flex: '1 1 400px' } }, `Lab-only task: ${d.cannot.score}`));
  const text = f.label === 'Winner not frozen' ? `The winner of the last pipeline run scores better on the holdout than submission.py: ${f.better[0]} against ${f.holdout[0]} rows.`
    : f.label === 'Not frozen yet' ? 'submission.py has never been scored for this task: Score submission runs lab score.' : 'submission.py holds the best known function for this task.';
  return h('div', { class: ['banner', f.label === 'Frozen in submission' ? 'ok' : null], role: 'status' }, icons.info(), h('span', { style: { flex: '1 1 400px' } }, text));
}

function stepCard(st, run, base) {
  const hrefs = { 2: `${base}/clusters`, 3: `${base}/trees`, 4: `${base}#candidates`, 7: `${base}#residuals` };
  const label = { done: 'Done', skipped: 'Not in this run', waiting: 'Waiting', running: 'Running', failed: 'Failed', cancelled: 'Cancelled' }[st.state] || st.state;
  return h('li', { class: ['step', `is-${st.state}`] },
    h('span', { class: 'step-marker', 'aria-hidden': 'true' }, st.state === 'done' ? icons.check() : st.n),
    hrefs[st.n] ? h('a', { href: hrefs[st.n], class: 'step-name' }, st.name) : h('span', { class: 'step-name' }, st.name),
    h('span', { class: 'step-state' }, h('span', { class: 'sr' }, `Step ${st.n}: `), label + (st.secs ? ` · ${st.secs} s` : '')),
    stepFiles(st, run));
}

function stepFiles(st, run) {
  const files = (st.files || []).filter((f) => !f.endsWith('.parquet'));
  return files.length ? tech('files', `Files (${files.length})`, h('span', { class: 'stack' },
    files.map((f) => h('a', { href: `/files/${encodeURIComponent(run)}/${f}`, class: 'mono tiny', style: { overflowWrap: 'anywhere' } }, f)))) : null;
}

function actionLink(r, d, base) {
  if (ACTION_HREF[r.action]) return h('a', { href: `${base}/${ACTION_HREF[r.action]}`, class: 'small', style: { minWidth: '120px' } }, r.action === 'trees' ? 'Explain with trees' : 'See the clusters');
  if (r.action === 'outliers') return h('a', { href: `/files/${encodeURIComponent(d.run)}/outliers.json`, class: 'small', style: { minWidth: '120px' } }, `See the ${r.count} rows`);
  return h('button', { type: 'button', class: 'btn small', onClick: () => start('suggest', d.task) }, 'Suggest features');
}

function proposalsCard(d) {
  const p = d.proposals;
  if (!p) {
    return card(h('h2', {}, 'Features suggested by the language model'),
      h('p', { class: 'small muted' }, 'Step 5 has not run for this task. It asks Claude Code for at most three features in the DSL, validates them and scores them exactly.'),
      modelNotice('suggest'),
      h('div', {}, h('button', { type: 'button', class: 'btn', onClick: () => start('suggest', d.task) }, 'Suggest features')));
  }
  const tone = { Kept: ['var(--ok-bg)', 'var(--ok)'], Used: ['var(--ok-bg)', 'var(--ok)'], 'No gain': ['var(--info-bg)', 'var(--info)'], Refused: ['var(--bad-bg)', 'var(--bad)'] };
  const pct = (pair) => (pair && pair[1] ? `${(100 * pair[0] / pair[1]).toFixed(2)} %` : '—');
  return card(
    h('div', { class: 'stack' }, h('h2', {}, 'Features suggested by the language model'),
      h('p', { class: 'small muted' }, 'From ', h('a', { href: `#/runs/${encodeURIComponent(p.run)}`, class: 'mono' }, p.run), ` · ${p.model} · ${p.time} · each proposal parsed in the DSL and scored exactly.`)),
    modelNotice('suggest'),
    table([
      { label: 'Feature', cell: (x) => h('span', { class: 'mono small' }, x.name ? [h('b', { style: { fontWeight: 500 } }, x.name), ' = '] : null, x.expr) },
      { label: 'Holdout before', num: true, cell: (x) => pct(x.before) },
      { label: 'After', num: true, cell: (x) => pct(x.after) },
      { label: 'Outcome', cell: (x) => [h('span', { class: 'chip', style: { background: tone[x.outcome]?.[0], color: tone[x.outcome]?.[1], fontWeight: 500 } }, x.outcome), ' ', h('span', { class: 'small muted' }, x.why)] },
    ], p.items, { minWidth: '760px' }));
}
