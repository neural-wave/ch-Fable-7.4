// Step 2 · Clusters: the relations tried, the histogram of the best one, its clusters, rounding modes, noise.
import { card, clusterColors, clusterInk, get, h, header, loading, mount, runTabs, start, swatch, table, valuePicker } from '../lib/h.js';

export async function render(root, { run, query }) {
  loading(root, 'runs');
  const value = query.get('value');
  const d = await get(`/api/runs/${encodeURIComponent(run)}/clusters${value ? `?value=${encodeURIComponent(value)}` : ''}`);
  let selected = 0;
  const base = `#/runs/${encodeURIComponent(run)}`;

  const draw = () => {
    const relations = d.relations || [];
    const cur = relations[selected];
    mount(root, header('runs'), h('div', { class: 'wrap' },
      h('div', { class: 'stack-8' },
        h('div', { class: 'crumbs' }, h('a', { href: '#/runs' }, 'Runs'), ' / ', h('a', { href: base, class: 'mono' }, run), ' / Clusters'),
        h('h1', {}, 'Step 2 · Clusters'),
        h('p', { class: 'small muted', style: { maxWidth: '820px' } }, 'For each relation between the target and an input, the lab looks for values that many rows share exactly. Each dense cluster is a candidate constant of the formula; the rows that fit none are noise.')),
      runTabs(run, 'clusters'),
      valuePicker(d.values, d.value, (v) => { location.hash = `${base}/clusters?value=${encodeURIComponent(v)}`; }),
      d.missing ? h('p', { class: 'empty' }, `No ${d.missing} in this run yet.`) : null,
      d.note ? h('div', { class: 'banner warn' }, d.note, d.approximate ? ` · approximate: ${d.approximate.relation} near ${d.approximate.centers.join(', ')}` : '') : null,
      relations.length ? h('div', { class: 'columns' },
        h('aside', { class: 'aside-left', 'aria-label': 'Relations tried' },
          h('div', { class: 'card tight', style: { padding: '16px', gap: '8px' } }, h('h3', { style: { marginBottom: '4px' } }, 'Relations tried'),
            relations.map((r, k) => h('button', { type: 'button', 'aria-pressed': String(k === selected), onClick: () => { selected = k; draw(); },
              style: { display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px', width: '100%', minHeight: '44px', padding: '10px 12px', borderRadius: '6px',
                border: k === selected ? '2px solid var(--accent)' : '1px solid var(--divider)', background: k === selected ? 'var(--accent-soft)' : '#fff', color: 'var(--ink)', font: 'inherit', textAlign: 'left', cursor: 'pointer' } },
            h('span', { class: 'mono small', style: { fontWeight: 500 } }, r.label),
            h('span', { class: 'small', style: { color: r.best ? 'var(--ok)' : 'var(--muted)' } }, r.verdict)))),
          h('div', { class: 'card tight', style: { padding: '16px', gap: '6px' } }, h('h3', {}, 'How a relation is scored'),
            h('p', { class: 'small muted' }, 'Ratio and difference with an amount, days and months with a date, a constant, the previous value of the policy. The relation whose clusters reproduce the most rows exactly wins; a simpler one wins if it reproduces almost as many.'))),
        h('main', { class: 'main' },
          card(h('div', { class: 'card-head' },
            h('div', { class: 'stack' }, h('h2', { class: 'mono', style: { fontSize: '17px', fontWeight: 500 } }, cur.label),
              h('span', { class: 'small muted' }, cur.histogram ? `${num(cur.histogram.rows)} precise rows · bar height on a square-root scale${cur.histogram.outside ? ` · ${num(cur.histogram.outside)} outside the range` : ''}` : '')),
            h('span', { class: 'row', style: { gap: '8px' } }, h('span', { class: 'chip round', style: { background: cur.best ? 'var(--ok-bg)' : 'var(--info-bg)', color: cur.best ? 'var(--ok)' : 'var(--info)', fontWeight: 500 } }, cur.verdict.split(' · ')[0]),
              h('span', { class: 'chip round' }, cur.verdict.split(' · ')[1] || ''))),
          cur.histogram ? histogram(cur.histogram, selected === 0 ? d.centers : null) :
            h('p', { class: 'empty' }, 'No histogram in this run: it is written by step 2 since lab serve exists. ', h('button', { type: 'button', class: 'btn small', onClick: () => start('run', d.task, { steps: ['cluster', 'tree', 'pool', 'iterate', 'report'] }) }, 'Rerun steps 2 to 7'))),
          selected === 0 ? [
            card(h('div', { class: 'stack' }, h('h2', {}, 'Clusters'),
              h('p', { class: 'small muted' }, 'Each row gets the label of its cluster in ', h('code', {}, 'labels.parquet'), '; step 3 learns which label each row takes.')),
            table([
              { label: 'Cluster', cell: (c, i) => h('span', { class: 'row', style: { gap: '8px' } }, swatch(c.id === '·' ? null : i, c.id)) },
              { label: 'Center', num: true, key: 'center' },
              { label: 'Rows', num: true, cell: (c) => num(c.rows) },
              { label: 'Share', num: true, key: 'share' },
              { label: 'Formula it suggests', cell: (c) => h('span', { class: 'mono small' }, c.formula) },
              { label: 'Exact in every row with', cell: (c) => h('span', { class: 'small' }, c.exact_modes.length ? c.exact_modes.join(', ') : 'no single mode') },
            ], [...d.centers, { id: '·', center: '—', rows: d.noise, share: pctOf(d.noise, d.rows), formula: 'noise: near no center', exact_modes: [] }], { minWidth: '760px' })),
            card(h('div', { class: 'stack' }, h('h2', {}, 'Rounding modes that reproduce each cluster'),
              h('p', { class: 'small muted' }, 'Share of the cluster’s rows that equal the target to the cent, for each of the 7 modes of Python’s ', h('code', {}, 'decimal'), '.')),
            modeMatrix(d)),
            card(h('div', { class: 'card-head' }, h('h2', {}, `Noise · ${num(d.noise)} rows`), h('a', { href: `/files/${encodeURIComponent(run)}/outliers.json`, class: 'small' }, 'Open outliers.json')),
              h('div', { class: 'grid-200' },
                tile(d.noise_split.listed, 'wrong rows of the winner listed in NREXCP: typed by hand'),
                tile(d.noise_split.whole_units, 'noise rows of the winner off by whole units'),
                tile(d.ambiguous, 'ambiguous rows: several centers reproduce them')),
              d.noise_examples.length ? h('p', { class: 'small muted' }, 'Examples: ', h('span', { class: 'mono' }, d.noise_examples.map((k) => k.join(' · ')).join(', '))) : null),
          ] : card(h('h2', {}, 'Not used'), h('p', { class: 'small muted' }, cur.why)))) : null));
  };
  draw();
}

function num(n) {
  return n === null || n === undefined ? '—' : Number(n).toLocaleString('en-US').replace(/,/g, ' ');
}

function pctOf(n, total) {
  return total ? `${(100 * n / total).toFixed(2)} %` : '—';
}

function tile(n, text) {
  return h('div', { class: 'tint' }, h('span', { class: 'mono', style: { fontSize: '20px', fontWeight: 500 } }, num(n)), h('span', { class: 'small muted' }, text));
}

function histogram(hist, centers) {
  const max = Math.sqrt(Math.max(1, ...hist.counts));
  const colorOf = {};
  (hist.centers || []).forEach((c, i) => { colorOf[c.bin] = i; });
  const near = (b) => [b, b - 1, b + 1].find((x) => x in colorOf);
  const bars = hist.counts.map((n, b) => {
    const k = near(b);
    const i = k === undefined ? undefined : colorOf[k];
    return h('span', { class: 'b', style: { height: n ? `${Math.max(1.5, (Math.sqrt(n) / max) * 100).toFixed(1)}%` : '0', background: i !== undefined && centers ? clusterColors[i % clusterColors.length] : '#C4C5C0' } });
  });
  const width = hist.counts.length;
  const marks = centers ? (hist.centers || []).map((c, i) => h('span', { class: 'mark', style: { left: `${((c.bin + 0.5) / width) * 100}%` } },
    h('span', { class: 'swatch', style: { background: clusterColors[i % clusterColors.length], color: clusterInk[i % clusterInk.length] } }, centers[i]?.id || i))) : [];
  const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1].map((f) => h('span', { style: { left: `${f * 100}%`, transform: f === 0 ? 'none' : f === 1 ? 'translateX(-100%)' : null } }, short(hist.lo + f * (hist.hi - hist.lo))));
  const label = `Histogram of the relation from ${short(hist.lo)} to ${short(hist.hi)}${centers ? `, with peaks at ${(hist.centers || []).map((c) => c.center).join(', ')}` : ''}`;
  return h('div', { style: { overflowX: 'auto' } }, h('div', { style: { minWidth: '640px' } },
    h('div', { class: 'hist', role: 'img', 'aria-label': label }, bars, marks),
    h('div', { class: 'ticks' }, ticks)));
}

function short(x) {
  const a = Math.abs(x);
  return a >= 1000 ? x.toFixed(0) : a >= 10 ? x.toFixed(2) : x.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
}

function modeMatrix(d) {
  return table([
    { label: 'Cluster', cell: (c, i) => swatch(i, c.id) },
    ...d.modes.map((m) => ({ label: m, num: true, cell: (c) => {
      const share = c.rows ? (100 * (c.modes[m] || 0)) / c.rows : 0;
      const full = share === 100;
      return h('span', { style: { color: full ? 'var(--ok)' : share > 95 ? 'var(--ink)' : 'var(--muted)', fontWeight: full ? 600 : 400 } }, full ? '100 %' : `${share.toFixed(1)} %`);
    } })),
  ], d.centers, { minWidth: '760px' });
}
