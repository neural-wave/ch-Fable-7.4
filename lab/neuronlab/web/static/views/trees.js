// Step 3 · Decision trees: the optimal tree of the smallest feature set, the path of a leaf, regions, equivalents.
import { card, clusterColors, clusterInk, edges, get, h, header, loading, mount, runTabs, swatch, valuePicker, wordsMode, wordsSwitch } from '../lib/h.js';

export async function render(root, { run, query }) {
  loading(root, 'runs');
  const value = query.get('value');
  const set = query.get('set') || 0;
  const d = await get(`/api/runs/${encodeURIComponent(run)}/trees?set=${set}${value ? `&value=${encodeURIComponent(value)}` : ''}`);
  const base = `#/runs/${encodeURIComponent(run)}`;
  const firstLeaf = d.leaves?.slice().sort((a, b) => b.errors - a.errors)[0];
  let selected = firstLeaf ? firstLeaf.id : null;
  let mode = wordsMode();

  const draw = () => {
    const onPath = new Set(selected === null ? [] : Array.from({ length: selected.length + 1 }, (_, i) => selected.slice(0, i)));
    const leaf = d.leaves?.find((l) => l.id === selected);
    mount(root, header('runs'), h('div', { class: 'wrap' },
      h('div', { class: 'stack-8' },
        h('div', { class: 'crumbs' }, h('a', { href: '#/runs' }, 'Runs'), ' / ', h('a', { href: base, class: 'mono' }, run), ' / Decision trees'),
        h('h1', {}, 'Step 3 · Decision trees'),
        h('p', { class: 'small muted', style: { maxWidth: '820px' } }, 'An optimal tree predicts the cluster of each row from the features of the frame, with as few leaves as the data allows. Its paths become the conditions of the code; pick a leaf to follow its path.')),
      runTabs(run, 'trees'),
      valuePicker(d.values, d.value, (v) => { location.hash = `${base}/trees?value=${encodeURIComponent(v)}`; }),
      d.missing ? h('p', { class: 'empty' }, `No ${d.missing} in this run yet.`) : null,
      d.note ? h('div', { class: 'banner' }, d.note) : null,
      d.diagram ? [
        h('section', { 'aria-label': 'Summary', class: 'grid' },
          stat('Optimal tree', `${d.chosen.leaves} leaves · ${d.chosen.errors} errors`, `${d.chosen.optimal_trees ?? '?'} optimal trees · ${pctRight(d.chosen.errors, d.rows)} of ${num(d.rows)} rows in the right cluster`),
          stat('Smallest feature set', d.chosen.features.join(', '), `${d.sets.length} set${d.sets.length > 1 ? 's' : ''} of this size reach the optimum`, true),
          stat('Conflicting vectors', `${num(d.conflicting_rows)} rows`, 'same features, different cluster'),
          d.cart ? stat('CART baseline', `${d.cart.leaves} leaves`, `${d.cart.errors} errors · ${d.cart.holdout} on the holdout`) : null),
        d.sets.length > 1 ? h('div', { class: 'row' }, h('span', { class: 'small strong' }, 'Feature set'),
          d.sets.map((x, i) => h('a', { class: 'btn small', href: `${base}/trees?set=${i}${d.value ? `&value=${encodeURIComponent(d.value)}` : ''}`, 'aria-current': i === d.index ? 'true' : null,
            style: i === d.index ? { borderColor: 'var(--accent)', background: 'var(--accent-soft)' } : null }, x.features.join(', ')))) : null,
        card(h('div', { class: 'card-head' }, h('div', { class: 'stack' }, h('h2', {}, 'The tree'), h('span', { class: 'small muted' }, 'Leaves are clusters of step 2 · counts on discovery rows')),
          wordsSwitch(mode, (m) => { mode = m; draw(); })),
          treeDiagram(d, onPath, (id) => { selected = id; draw(); }, mode),
          leaf ? h('div', { role: 'status', class: 'row', style: { gap: '12px 24px', padding: '14px 16px', borderRadius: '6px', background: 'var(--tint)' } },
            h('span', { class: 'stack', style: { flex: '1 1 420px' } }, h('span', { class: 'small muted' }, 'Path to the selected leaf'),
              mode === 'plain' ? [h('span', { class: 'small' }, leaf.say), h('span', { class: 'mono tiny muted' }, leaf.path)] : h('span', { class: 'mono small' }, leaf.path)),
            h('span', { class: 'stack' }, h('span', { class: 'small muted' }, 'Wrong rows'), h('span', { class: 'mono small' }, `${num(leaf.errors)} of ${num(leaf.rows)}`)),
            h('a', { href: `${base}/flow${d.value ? `?value=${encodeURIComponent(d.value)}` : ''}`, class: 'small' }, 'Follow it in the control flow')) : null),
        h('div', { class: 'row', style: { gap: '20px', alignItems: 'flex-start' } },
          d.regions ? h('section', { class: 'card', style: { flex: '1 1 520px', minWidth: 0 } },
            h('div', { class: 'stack' }, h('h2', {}, 'The same tree as regions'),
              h('p', { class: 'small muted' }, 'Each cell is one combination of the values the tree tests; its color is the cluster it assigns. "other" is every value the tree does not name.')),
            regions(d.regions, d.centers, selected, (id) => { selected = id; draw(); }, mode)) : null,
          h('section', { class: 'card', style: { flex: '1 1 420px', minWidth: 0 } }, h('h2', {}, 'Feature sets and equivalent features'),
            h('ul', { style: { listStyle: 'none', margin: 0, padding: 0 } },
              d.sets.map((x, i) => h('li', { class: 'row-between', style: { padding: '12px 0', borderTop: '1px solid var(--divider)' } },
                h('span', { class: 'stack' }, h('span', { class: 'mono small strong' }, x.features.join(', ')),
                  h('span', { class: 'small muted' }, `${x.leaves} leaves · ${x.errors} errors${i === d.index ? ' · shown' : ''}`))))),
            Object.entries(d.chosen.equivalents).filter(([, eq]) => eq.length).map(([f, eq]) => h('div', { class: 'small' },
              h('span', { class: 'mono strong' }, f), h('span', { class: 'muted' }, ' splits the rows like '), h('span', { class: 'mono' }, eq.slice(0, 6).join(', ')), eq.length > 6 ? h('span', { class: 'muted' }, ` and ${eq.length - 6} more`) : null)),
            d.conflicts.length ? h('div', { class: 'stack-8', style: { padding: '14px', borderRadius: '6px', background: 'var(--warn-bg)', color: '#6E3A0F' } },
              h('span', { class: 'strong small' }, `${num(d.conflicting_rows)} conflicting rows`),
              h('span', { class: 'small' }, 'Same features, different cluster: a feature is missing, not a branch. Step 5 is asked for it.'),
              d.conflicts.slice(0, 3).map((c) => h('span', { class: 'mono tiny' }, `${Object.entries(c.vector).map(([k, v]) => `${k}=${v}`).join(', ')} → ${Object.entries(c.clusters).map(([k, v]) => `${k}: ${v}`).join(', ')} · e.g. ${c.example.join(' · ')}`))) : null)),
      ] : null));
  };
  draw();
}

function num(n) {
  return n === null || n === undefined ? '—' : Number(n).toLocaleString('en-US').replace(/,/g, ' ');
}

function pctRight(errors, rows) {
  return rows ? `${(100 * (1 - errors / rows)).toFixed(2)} %` : '—';
}

function stat(label, big, small, wrap) {
  return h('div', { class: 'stat', style: { padding: '16px' } }, h('span', { class: 'small muted' }, label),
    h('span', { class: 'mid', style: wrap ? { fontSize: '15px', overflowWrap: 'anywhere' } : null }, big), h('span', { class: 'small muted' }, small));
}

function treeDiagram(d, onPath, pick, mode) {
  const diagram = d.diagram;
  const nodes = diagram.nodes.map((n) => {
    const on = onPath.has(n.id);
    const box = { left: `${n.x}px`, top: `${n.y}px`, width: `${n.w}px`, height: `${n.h}px` };
    if (n.kind === 'split') {
      if (mode === 'plain' && n.say) {
        return h('div', { class: ['node', on && 'on'], style: box, title: `${n.feature} = ${n.value}` },
          h('span', {}, h('span', { class: 'say' }, n.say), h('span', { class: 'code-line' }, `${n.feature} = ${n.value}`)));
      }
      return h('div', { class: ['node', on && 'on'], style: box }, h('span', {}, h('b', {}, n.feature), h('br'), h('span', { class: 'muted' }, `= ${n.value} ?`)));
    }
    const right = n.rows ? `${(100 * (1 - n.errors / n.rows)).toFixed(2)} % right` : '';
    return h('button', { type: 'button', class: ['node', on && 'on'], style: box, 'aria-pressed': String(on), onClick: () => pick(n.id) },
      swatch(n.cluster, n.cluster === null || n.cluster === undefined ? '?' : String.fromCharCode(65 + n.cluster)),
      h('span', {}, h('b', {}, n.label), h('br'), `${num(n.rows)} row${n.rows === 1 ? '' : 's'} · ${right}`,
        mode === 'plain' && n.say ? h('span', { class: 'say', style: { marginTop: '4px', fontSize: '12px', lineHeight: '15px' } }, n.say) : null));
  });
  const labels = diagram.edges.map((e) => {
    const [x, y] = e.points.length > 2 ? e.points[2] : e.points[1];
    return h('span', { class: 'edge-label', style: { left: `${x + (e.branch === 'yes' ? -18 : 14)}px`, top: `${y + 12}px` } }, e.branch);
  });
  return h('div', { class: 'diagram-box' }, h('div', { class: 'diagram', style: { width: `${diagram.width}px`, height: `${diagram.height}px` } },
    edges(diagram, (e) => (onPath.has(e.to) ? 'var(--accent)' : '#8A8D90')), nodes, labels));
}

function regions(r, centers, selected, pick, mode) {
  const say = (map, v) => (mode === 'plain' && map && map[v] && map[v] !== v ? `${map[v]} (${v})` : v);
  const cols = r.cols.length;
  return h('div', { style: { overflowX: 'auto' } }, h('div', { style: { display: 'grid', gridTemplateColumns: `minmax(72px, auto) repeat(${cols}, minmax(110px, 1fr))`, gap: '4px', minWidth: `${120 + cols * 114}px` } },
    h('span', { class: 'tiny muted', style: { alignSelf: 'end' } }, mode === 'plain' ? `${r.rows_subject} ↓ · ${r.cols_subject} →` : `${r.rows_feature} ↓ · ${r.cols_feature} →`),
    r.cols.map((c) => h('span', { class: 'small muted', style: { textAlign: 'center', padding: '4px 0' } }, say(r.cols_say, c))),
    r.rows.map((row) => [h('span', { class: 'small muted', style: { display: 'flex', alignItems: 'center' } }, say(r.rows_say, row)),
      r.cells.filter((c) => c.row === row).map((c) => {
        const i = c.cluster;
        const color = i === null || i === undefined ? '#C4C5C0' : clusterColors[i % clusterColors.length];
        const ink = i === null || i === undefined ? '#1A1C1E' : clusterInk[i % clusterInk.length];
        return h('button', { type: 'button', onClick: () => pick(c.leaf), style: { minHeight: '60px', padding: '8px', borderRadius: '6px', border: 0, outline: selected === c.leaf ? '3px solid var(--accent)' : '3px solid transparent', outlineOffset: '2px', background: color, color: ink, font: 'inherit', fontSize: '13px', cursor: 'pointer' } },
          h('b', { class: 'mono' }, c.label));
      })])));
}
