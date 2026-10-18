// New task in four steps: legacy data, task description, test pairs, review and run. One draft per task, kept in
// memory and in this browser until it is saved as lab/tasks/<id>.json.
import { zoomCanvas } from '../lib/canvas.js';
import { card, edges, get, h, header, icons, loading, mount, post, table, tech, toast } from '../lib/h.js';

const STEPS = [['legacy', 'Legacy data', 'required'], ['task', 'Task description', ''], ['pairs', 'Test pairs', 'optional'], ['review', 'Review and run', '']];
const PIPELINE = [['profile', 'Profile keys and joins'], ['frame', 'Build the frame'], ['cluster', 'Cluster relations'], ['tree', 'Optimal decision trees'],
  ['pool', 'Candidate pool and exact scoring'], ['iterate', 'Pass on residuals'], ['report', 'Report for step 5']];
const TYPES = [['', 'to confirm'], ['string', 'string'], ['int', 'integer'], ['date', 'date (yyyymmdd)'], ['decimal:2', 'decimal, 2 places'], ['decimal:4', 'decimal, 4 places']];
const ROUNDINGS = ['discover', 'ROUND_HALF_UP', 'ROUND_HALF_EVEN', 'ROUND_HALF_DOWN', 'ROUND_DOWN', 'ROUND_UP', 'ROUND_FLOOR', 'ROUND_CEILING'];
const drafts = {};

function storageKey(task) { return `ergo-draft-${task}`; }

function remember(task) {
  try { localStorage.setItem(storageKey(task), JSON.stringify(drafts[task])); } catch (e) { /* private window: memory only */ }
}

async function draftOf(task) {
  if (drafts[task]) return drafts[task];
  let stored = null;
  try { stored = JSON.parse(localStorage.getItem(storageKey(task)) || 'null'); } catch (e) { stored = null; }
  const server = await get(`/api/tasks/${encodeURIComponent(task)}`);
  drafts[task] = stored && !server.saved ? stored : { definition: server.definition, saved: server.saved, drafted: server.drafted };
  return drafts[task];
}

export async function render(root, { task, step }) {
  loading(root, 'tasks');
  const draft = await draftOf(task);
  const def = draft.definition;
  const ctx = { root, task, step, draft, def, redraw: null, changed: () => { draft.dirty = true; remember(task); }, canvases: {} };
  const view = { legacy: legacyStep, task: taskStep, pairs: pairsStep, review: reviewStep }[step];
  ctx.redraw = async () => {
    const [mainNode, asideNode] = await view(ctx);
    mount(root, header('tasks'), h('div', { class: 'wrap' },
      h('div', { class: 'stack' },
        h('div', { class: 'crumbs' }, h('a', { href: '#/tasks' }, 'Tasks'), ` / ${task === 'new' ? 'New task' : task}`),
        h('div', { class: 'row' }, h('h1', {}, task === 'new' ? 'New task' : def.title || task),
          draft.saved ? h('span', { class: 'chip', style: { background: 'var(--ok-bg)', color: 'var(--ok)' } }, draft.dirty ? 'saved, with changes' : 'saved') :
            h('span', { class: 'chip' }, draft.drafted ? 'drafted from the last run' : 'draft'))),
      stepNav(task, step),
      h('div', { class: 'columns' }, h('main', { class: 'main' }, mainNode), h('aside', { class: 'aside', 'aria-label': 'Task definition so far' }, asideNode))));
  };
  await ctx.redraw();
}

function stepNav(task, current) {
  const index = STEPS.findIndex(([k]) => k === current);
  return h('ol', { class: 'wizard', 'aria-label': 'Steps' }, STEPS.map(([key, label, note], i) => h('li', {},
    h('a', { href: `#/tasks/${encodeURIComponent(task)}/${key}`, 'aria-current': key === current ? 'step' : null },
      i < index ? h('span', { style: { color: 'var(--ok)' } }, icons.check()) : h('span', { class: 'n' }, i + 1), ` ${label}`,
      note && key !== current ? h('span', { class: 'muted', style: { fontWeight: 400 } }, ` ${note}`) : null))));
}

function preview(title, data, note) {
  return [tech('json', [title, h('span', { class: 'tiny muted' }, 'live preview of the file')], h('pre', {}, JSON.stringify(data, null, 2)), 'dark'),
  note ? h('div', { class: 'card tight', style: { gap: '8px' } }, h('h3', {}, note[0]), h('p', { class: 'small muted' }, note[1])) : null];
}

function footer(ctx, back, nextHref, nextLabel, extra) {
  return h('div', { class: 'row-between', style: { padding: '16px 0' } },
    back ? h('a', { class: 'btn', href: back }, 'Back') : h('span', {}, extra || ''),
    h('div', { class: 'row' },
      h('button', { type: 'button', class: 'btn', onClick: () => { remember(ctx.task); toast('Draft kept in this browser: save it on the last step'); } }, 'Save draft'),
      nextHref ? h('a', { class: 'btn primary', href: nextHref }, nextLabel) : null));
}

function href(ctx, step) { return `#/tasks/${encodeURIComponent(ctx.task)}/${step}`; }

function tableEntry(def, name) {
  let entry = def.legacy.tables.find((t) => t.name === name);
  if (!entry) { entry = { name, key: [], columns: {} }; def.legacy.tables.push(entry); }
  return entry;
}

// --- step 1: legacy data ---------------------------------------------------------------------------------------

async function legacyStep(ctx) {
  const { def } = ctx;
  ctx.overview = ctx.overview || await get('/api/legacy');
  const ov = ctx.overview;
  const inTask = new Set(def.legacy.tables.map((t) => t.name));
  ctx.selected = ctx.selected || def.legacy.tables[0]?.name || ov.tables[0]?.name;
  const columns = ctx.selected ? await get(`/api/legacy/tables/${encodeURIComponent(ctx.selected)}`).catch(() => null) : null;
  const shown = inTask.size ? [...inTask] : [];
  const joinIds = new Set(def.legacy.joins.map((j) => `${j.from}->${j.to}`));
  const relevant = ov.joins.filter((j) => inTask.has(j.from.split('.')[0]) && inTask.has(j.to.split('.')[0]));
  for (const j of relevant) {
    if (!joinIds.has(j.id)) def.legacy.joins.push({ from: j.from, to: j.to, kind: j.kind, keep: true, origin: 'profile' });
  }
  const kept = def.legacy.joins.filter((j) => j.keep !== false && inTask.has(j.from.split('.')[0]) && inTask.has(j.to.split('.')[0]));
  const diagram = shown.length ? await post('/api/diagram', { tables: shown, joins: kept, highlight: ctx.selected }).catch(() => null) : null;
  const tableMeta = Object.fromEntries(ov.tables.map((t) => [t.name, t]));
  const untypedLeft = def.legacy.tables.flatMap((t) => (tableMeta[t.name]?.untyped || []).filter((c) => !(t.columns || {})[c]?.type).map((c) => `${t.name}.${c}`));

  const fileInput = h('input', { id: 'legacyFiles', type: 'file', multiple: true, accept: '.csv,.sql,.ddl,.json', class: 'sr', onChange: (e) => upload(ctx, e.target.files) });
  const folder = h('input', { id: 'legacyPath', class: 'input mono', value: ov.folder });
  const main = [
    card(h('div', { class: 'stack' }, h('h2', {}, 'Where is the legacy data?'),
      h('p', { class: 'small muted' }, 'Upload the files, or read them from a folder on the lab machine. Profiling, clustering and exact scoring all work on the data, so the CSV files are needed with the structure.')),
    h('div', { class: 'grid' },
      choice('src', def.legacy.source !== 'schema', 'CSV files', 'Types from NRDICT.csv, the dictionary of the extract', () => { def.legacy.source = 'folder'; ctx.changed(); ctx.redraw(); }),
      choice('src', def.legacy.source === 'schema', 'Schema file + CSV files', 'JSON or SQL DDL declares the types and becomes NRDICT.csv (no COBOL copybooks)', () => { def.legacy.source = 'schema'; ctx.changed(); ctx.redraw(); })),
    h('div', { class: 'stack-8', style: { border: '2px dashed var(--control)', borderRadius: '8px', padding: '28px 20px', background: 'var(--tint-2)', alignItems: 'center', textAlign: 'center' },
      onDragover: (e) => e.preventDefault(), onDrop: (e) => { e.preventDefault(); upload(ctx, e.dataTransfer.files); } },
    icons.upload(), h('span', { class: 'strong' }, 'Drop CSV files or a schema file here'),
    h('span', { class: 'small muted' }, '.csv, one file per table, separated by ";" · schema as .json, .sql or .ddl'),
    h('label', { for: 'legacyFiles', class: 'btn dark-outline' }, 'Choose files…'), fileInput),
    ov.notes?.length ? h('p', { class: 'small', style: { color: 'var(--ok)' } }, ov.notes.join(' · ')) : null,
    h('div', { class: 'row small muted' }, h('span', { style: { flex: 1, height: '1px', background: 'var(--divider)' } }), 'or', h('span', { style: { flex: 1, height: '1px', background: 'var(--divider)' } })),
    h('div', { class: 'row', style: { alignItems: 'flex-end' } },
      h('label', { class: 'field', style: { flex: '1 1 320px' } }, 'Read a folder on the lab machine', folder),
      h('button', { type: 'button', class: 'btn dark-outline', onClick: () => readFolder(ctx, folder.value) }, 'Read folder')),
    h('p', { class: 'small muted' }, ov.env ? 'The lab reads ' : 'Defaults to ', h('code', {}, 'NEURON_LEGACY'), ov.env ? ` = ${ov.folder}. ` : ' when it is set. ',
      'Every file gets a typed copy in ', h('code', {}, '.cache/'), '. ', ov.profiled ? `Keys and relationships come from the profile of ${ov.tables.length} tables.` : 'The tables have not been profiled yet: keys and relationships appear after step 1 of a run.')),
    diagram ? card(h('div', { class: 'stack' }, h('h2', {}, 'Structure at a glance'),
      h('p', { class: 'small muted' }, 'Tables in this task and their relationships. Each arrow goes from a foreign key to the key it references; dashed: a temporal join, read on a date.')),
    inCanvas(ctx, 'tables', 'Tables and joins of the task', diagram, erDiagram(diagram, tableMeta, ctx.selected))) : null,
    card(h('div', { class: 'card-head' }, h('h2', {}, 'Tables'), h('span', { class: 'small muted' }, 'Tick the tables of this task; pick one to check its columns')),
      table([
        { label: h('span', { class: 'sr' }, 'In this task'), cell: (t) => h('input', { type: 'checkbox', 'aria-label': `${t.name} in this task`, checked: inTask.has(t.name) ? true : null, style: { width: '18px', height: '18px', accentColor: 'var(--accent)' },
          onClick: (e) => e.stopPropagation(),
          onChange: (e) => { toggleTable(def, t.name, e.target.checked); ctx.changed(); ctx.redraw(); } }) },
        { label: 'Table', cell: (t) => h('span', { class: 'mono strong' }, t.name) },
        { label: 'What it holds', key: 'desc' },
        { label: 'Rows', num: true, cell: (t) => Number(t.rows).toLocaleString('en-US').replace(/,/g, ' ') },
        { label: 'Key found', cell: (t) => h('span', { class: 'mono small' }, t.key || '—') },
        { label: 'Status', cell: (t) => statusOf(t, def) },
      ], ov.tables, { minWidth: '820px', selected: (t) => t.name === ctx.selected, onRow: (t) => { ctx.selected = t.name; ctx.redraw(); } })),
    columns ? card(h('div', { class: 'card-head' }, h('h2', {}, h('span', { class: 'mono' }, columns.name), ' — columns'),
      h('span', { class: 'small muted' }, 'Amounts ', h('code', {}, 'N(s)'), ' are read as ', h('code', {}, 'Decimal(38, s)'), ', never as floats')),
    table([
      { label: 'Column', cell: (c) => h('span', { class: 'mono strong' }, c.name) },
      { label: 'Declared', cell: (c) => h('span', { class: 'mono small muted' }, c.declared) },
      { label: 'Read as', cell: (c) => (c.typed ? h('span', { class: 'mono small' }, c.type) : typeSelect(ctx, columns.name, c.name)) },
      { label: 'Meaning', key: 'meaning' },
      { label: 'Role', cell: (c) => h('span', { class: 'chip' }, c.role) },
      { label: 'Example', cell: (c) => h('span', { class: 'mono small' }, c.example) },
    ], columns.columns, { minWidth: '860px', selected: (c) => !c.typed })) : null,
    inTask.size ? card(h('div', { class: 'stack' }, h('h2', {}, 'Relationships'),
      h('p', { class: 'small muted' }, 'Found by profiling (inclusion dependencies into a key). Keep, reject, or add one by hand; a temporal join reads the row valid on a date of the grain.')),
    h('div', { class: 'stack-8' }, def.legacy.joins.filter((j) => inTask.has(j.from.split('.')[0]) && inTask.has(j.to.split('.')[0])).map((j) => h('div', { class: 'row', style: { padding: '12px 14px', border: '1px solid var(--divider)', borderRadius: '6px', gap: '8px 16px' } },
      h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: j.keep !== false ? true : null, onChange: (e) => { j.keep = e.target.checked; ctx.changed(); ctx.redraw(); } }),
        h('span', { class: 'mono' }, `${j.from} → ${j.to}`)),
      h('span', { class: 'chip', style: j.kind === 'temporal' ? { background: 'var(--bad-bg)', color: 'var(--bad)' } : null }, j.kind === 'temporal' ? 'temporal · read on each date' : 'plain'),
      h('span', { class: 'small muted', style: { marginLeft: 'auto' } }, j.origin === 'hand' ? 'added by hand' : 'found by profiling')))),
    addJoin(ctx)) : null,
    footer(ctx, null, href(ctx, 'task'), 'Next: describe the task',
      h('span', { class: 'stack small' }, h('span', { style: { color: inTask.size ? 'var(--ok)' : 'var(--warn-text)', fontWeight: 500 } }, inTask.size ? `${inTask.size} tables in this task` : 'Tick at least the table of the grain'),
        untypedLeft.length ? h('span', { style: { color: 'var(--warn-text)' } }, `${untypedLeft.length} columns still need a type`) : null)),
  ];
  return [main, preview('task.json', { legacy: { source: def.legacy.source, path: ov.folder, tables: def.legacy.tables.map((t) => ({ name: t.name, key: t.key, ...(Object.keys(t.columns || {}).length ? { columns: t.columns } : {}) })), joins: kept.map((j) => ({ from: j.from, to: j.to, kind: j.kind })) } },
    ['What the lab does with this', 'Step 1 of the pipeline profiles keys and joins and builds one frame per task, with the lineage of every column. Rejected relationships are dropped from the join graph, added ones join it, and only the tables of the task are joined into the frame.'])];
}

function choice(name, on, title, text, pick) {
  return h('label', { class: ['choice', on && 'on'] }, h('input', { type: 'radio', name, checked: on ? true : null, onChange: pick }),
    h('span', { class: 'stack' }, h('span', { class: 'strong' }, title), h('span', { class: 'small muted' }, text)));
}

function statusOf(t, def) {
  const entry = def.legacy.tables.find((x) => x.name === t.name);
  const left = (t.untyped || []).filter((c) => !(entry?.columns || {})[c]?.type);
  if (left.length) return h('span', { class: 'row small', style: { gap: '6px', color: 'var(--warn-text)', fontWeight: 500 } }, icons.warn(), `${left.length} types to confirm`);
  if (!t.key) return h('span', { class: 'small muted' }, 'key found by profiling');
  return h('span', { class: 'row small', style: { gap: '6px', color: 'var(--ok)', fontWeight: 500 } }, icons.check(), 'Confirmed');
}

function toggleTable(def, name, on) {
  if (on) {
    tableEntry(def, name);
    if (!def.task.scope.tables.includes(name)) def.task.scope.tables.push(name);
  } else {
    def.legacy.tables = def.legacy.tables.filter((t) => t.name !== name);
    def.task.scope.tables = def.task.scope.tables.filter((t) => t !== name);
  }
}

function typeSelect(ctx, table, column) {
  const entry = ctx.def.legacy.tables.find((t) => t.name === table);
  const current = entry?.columns?.[column]?.type || '';
  return h('select', { class: 'input mono', style: { minHeight: '36px', color: current ? 'var(--ink)' : 'var(--warn-text)' }, 'aria-label': `Type of ${column}`,
    onChange: (e) => { const t = tableEntry(ctx.def, table); t.columns = t.columns || {}; t.columns[column] = { ...(t.columns[column] || {}), type: e.target.value || undefined }; ctx.changed(); ctx.redraw(); } },
  TYPES.map(([v, label]) => h('option', { value: v, selected: v === current ? true : null }, label)));
}

function addJoin(ctx) {
  const from = h('input', { class: 'input mono', placeholder: 'NRPREM.PR_TFCD' });
  const to = h('input', { class: 'input mono', placeholder: 'NRBRTF.BR_TFCD' });
  const kind = h('select', { class: 'input' }, h('option', { value: 'plain' }, 'plain'), h('option', { value: 'temporal' }, 'temporal'));
  return h('details', {}, h('summary', { class: 'btn dashed', style: { listStyle: 'none', display: 'inline-flex' } }, '+ Add a relationship'),
    h('div', { class: 'row', style: { marginTop: '12px', alignItems: 'flex-end' } },
      h('label', { class: 'field', style: { flex: '1 1 200px' } }, 'From (table.column)', from), h('label', { class: 'field', style: { flex: '1 1 200px' } }, 'To the key (table.column)', to),
      h('label', { class: 'field', style: { flex: '0 1 140px' } }, 'Kind', kind),
      h('button', { type: 'button', class: 'btn', onClick: () => {
        if (!/^NR\w+\.\w+/.test(from.value) || !/^NR\w+\.\w+/.test(to.value)) { toast('Write both ends as TABLE.COLUMN', true); return; }
        ctx.def.legacy.joins.push({ from: from.value.trim(), to: to.value.trim(), kind: kind.value, keep: true, origin: 'hand' });
        for (const end of [from.value, to.value]) toggleTable(ctx.def, end.split('.')[0], true);
        ctx.changed(); ctx.redraw();
      } }, 'Add')));
}

function erDiagram(diagram, meta, selected) {
  const boxes = diagram.nodes.map((n) => h('div', { class: ['table-node', n.highlight && 'on'], style: { left: `${n.x}px`, top: `${n.y}px`, width: `${n.w}px`, height: `${n.h}px` } },
    h('b', { class: 'mono', style: { fontSize: '14px' } }, n.id), ' ', h('span', { class: 'muted' }, (meta[n.id]?.desc || '').split(',')[0]), h('br'),
    h('span', { class: 'mono', style: { fontSize: '12.5px' } }, (meta[n.id]?.key || '').split(', ').slice(0, 3).map((k, i) => [i ? h('br') : null, `${k} · PK`]))));
  return h('div', { class: 'diagram', style: { width: `${diagram.width}px`, height: `${diagram.height}px` } },
    edges(diagram, () => '#6B6F74'), boxes);
}

// One canvas per diagram of the step, kept in ctx so zoom and position survive the redraws of the page.
function inCanvas(ctx, key, label, diagram, node) {
  ctx.canvases[key] = ctx.canvases[key] || zoomCanvas(label);
  ctx.canvases[key].setContent(node, { w: diagram.width, h: diagram.height });
  return ctx.canvases[key].el;
}

async function upload(ctx, files) {
  if (!files?.length) return;
  const payload = {};
  for (const file of files) payload[file.name] = await toBase64(file);
  try {
    ctx.overview = await post('/api/legacy/upload', { files: payload });
    ctx.def.legacy.path = ctx.overview.folder;
    ctx.changed();
    toast(`Read ${files.length} file${files.length > 1 ? 's' : ''} into ${ctx.overview.folder}`);
    ctx.redraw();
  } catch (e) {
    toast(e.message, true);
  }
}

function toBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',', 2)[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function readFolder(ctx, path) {
  if (path !== ctx.overview.folder && !confirm('Reading another folder replaces the typed copies in lab/.cache and the legacy profile. Continue?')) return;
  try {
    ctx.overview = await post('/api/legacy/folder', { path });
    ctx.def.legacy.path = ctx.overview.folder;
    ctx.changed();
    ctx.redraw();
  } catch (e) {
    toast(e.message, true);
  }
}

// --- step 2: task description ----------------------------------------------------------------------------------

async function taskStep(ctx) {
  const { def } = ctx;
  const t = def.task;
  ctx.tasks = ctx.tasks || (await get('/api/tasks')).tasks;
  const scope = new Set(t.scope.tables);
  const outputs = [...t.keys.map((k) => ({ ...k, part: 'Key' })), ...t.values.map((v) => ({ ...v, part: 'Value' }))];
  const tableNames = def.legacy.tables.map((x) => x.name);
  const keptJoins = def.legacy.joins.filter((j) => j.keep !== false && scope.has(j.from.split('.')[0]) && scope.has(j.to.split('.')[0]));
  const diagram = tableNames.length ? await post('/api/diagram', { tables: tableNames.filter((n) => scope.has(n)), joins: keptJoins,
    extra: { id: t.keys.length || t.values.length ? def.id || 'this task' : 'this task' } }).catch(() => null) : null;
  const description = h('textarea', { id: 'taskDesc', rows: 7, class: 'input', value: t.description,
    onInput: (e) => { t.description = e.target.value; ctx.changed(); } });
  description.value = t.description;
  const main = [
    h('section', { class: 'card', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px 20px' } },
      h('label', { class: 'field' }, 'Task id', h('input', { class: 'input mono', value: def.id, onChange: (e) => { def.id = e.target.value.trim(); if (!def.examples.target_file.path) def.examples.target_file.path = `${def.id}.csv`; ctx.changed(); ctx.redraw(); } }),
        h('span', { class: 'tiny muted', style: { fontWeight: 400 } }, 'Becomes ', h('code', {}, `runs/${def.id || '<id>'}/`), ' and the function name in submission.py')),
      h('label', { class: 'field' }, 'Title', h('input', { class: 'input', value: def.title, onChange: (e) => { def.title = e.target.value; ctx.changed(); } }))),
    card(h('div', { class: 'stack' }, h('label', { for: 'taskDesc', style: { fontSize: '18px', fontWeight: 600 } }, 'What does the legacy system compute?'),
      h('p', { class: 'small muted' }, 'Write it as you would to a colleague: what, when, for which policies, known exceptions. The language model reads it in step 5; trees and clustering work from the data alone.')),
    description,
    h('div', { class: 'row', style: { gap: '8px' } }, h('span', { class: 'small muted' }, 'Mention if you can:'), ['rounding and currency', 'dates and calendars', 'system changes', 'manual overrides'].map((x) => h('span', { class: 'chip round' }, x)))),
    card(h('div', { class: 'stack' }, h('h2', {}, 'Output'), h('p', { class: 'small muted' }, 'The shape of the result. Keys identify a row; values are what the migrated code must reproduce to the cent.')),
      h('label', { class: 'field', style: { maxWidth: '520px' } }, 'Grain — one row per', h('input', { class: 'input', value: t.grain, onChange: (e) => { t.grain = e.target.value; ctx.changed(); } })),
      outputs.length ? table([
        { label: 'Column', cell: (o) => h('span', { class: 'mono strong' }, o.name) },
        { label: 'Part', cell: (o) => h('span', { class: ['chip', o.part === 'Key' ? 'key' : 'value'] }, o.part) },
        { label: 'Type', cell: (o) => h('span', { class: 'mono small' }, o.type || '—') },
        { label: 'Rounding', cell: (o) => (o.part === 'Key' ? '—' : h('select', { class: 'input mono', style: { minHeight: '36px' }, 'aria-label': `Rounding of ${o.name}`,
          onChange: (e) => { t.values.find((v) => v.name === o.name).rounding = e.target.value; ctx.changed(); ctx.redraw(); } },
        ROUNDINGS.map((r) => h('option', { value: r, selected: (o.rounding || 'discover') === r ? true : null }, r === 'discover' ? 'Discover' : r.replace('ROUND_', '').toLowerCase())))) },
        { label: 'Meaning', cell: (o) => h('input', { class: 'input', style: { minHeight: '36px' }, value: o.meaning || '', 'aria-label': `Meaning of ${o.name}`,
          onChange: (e) => { (o.part === 'Key' ? t.keys : t.values).find((x) => x.name === o.name).meaning = e.target.value; ctx.changed(); } }) },
        { label: h('span', { class: 'sr' }, 'Remove'), cell: (o) => h('button', { type: 'button', class: 'icon-btn', 'aria-label': `Remove ${o.name}`,
          onClick: () => { t.keys = t.keys.filter((x) => x.name !== o.name); t.values = t.values.filter((x) => x.name !== o.name); ctx.changed(); ctx.redraw(); } }, icons.close()) },
      ], outputs, { minWidth: '760px' }) : h('p', { class: 'empty' }, 'No column yet: add the keys and the values of the target file.'),
      addOutput(ctx)),
    card(h('div', { class: 'stack' }, h('h2', {}, 'Inputs in scope'), h('p', { class: 'small muted' }, 'Narrowing the scope speeds up profiling and keeps the frame small. Other tasks can be inputs too: their values join on the keys both share.')),
      diagram ? inCanvas(ctx, 'scope', 'Inputs in scope', diagram, h('div', { class: 'diagram', style: { width: `${diagram.width}px`, height: `${diagram.height}px` } },
        edges(diagram, () => '#6B6F74'), diagram.nodes.map((n) => h('div', { class: ['table-node', n.output && 'out'], style: { left: `${n.x}px`, top: `${n.y}px`, width: `${n.w}px`, height: `${n.h}px` } },
          h('b', { class: 'mono' }, n.id), h('br'), n.output ? [...t.keys.map((k) => `${k.name} · key`), ...t.values.map((v) => `${v.name} · value`)].slice(0, 4).map((x) => [h('span', { class: 'mono tiny' }, x), h('br')]) : null)))) : null,
      h('fieldset', { style: { border: 0, margin: 0, padding: 0 }, class: 'stack-8' }, h('legend', { class: 'small strong', style: { padding: 0, marginBottom: '6px' } }, 'Legacy tables'),
        h('div', { class: 'row', style: { gap: '8px' } }, tableNames.length ? tableNames.map((name) => h('label', { class: ['toggle-chip', scope.has(name) && 'on'] },
          h('input', { type: 'checkbox', checked: scope.has(name) ? true : null, onChange: (e) => { t.scope.tables = e.target.checked ? [...t.scope.tables, name] : t.scope.tables.filter((x) => x !== name); ctx.changed(); ctx.redraw(); } }), name)) :
          h('span', { class: 'small muted' }, 'Pick the tables in step 1.'))),
      h('fieldset', { style: { border: 0, margin: 0, padding: 0 }, class: 'stack-8' }, h('legend', { class: 'small strong', style: { padding: 0, marginBottom: '6px' } }, 'Other tasks'),
        h('div', { class: 'row', style: { gap: '8px' } }, ctx.tasks.filter((x) => x.target && x.id !== def.id).map((x) => h('label', { class: ['toggle-chip', t.scope.tasks.includes(x.id) && 'on'] },
          h('input', { type: 'checkbox', checked: t.scope.tasks.includes(x.id) ? true : null, onChange: (e) => { t.scope.tasks = e.target.checked ? [...t.scope.tasks, x.id] : t.scope.tasks.filter((y) => y !== x.id); ctx.changed(); ctx.redraw(); } }),
          x.id, h('span', { class: 'tiny muted', style: { fontFamily: 'var(--sans)' } }, x.scored ? '' : 'diagnostic')))))),
    hintsCard(ctx),
    footer(ctx, href(ctx, 'legacy'), href(ctx, 'pairs'), 'Next: test pairs'),
  ];
  return [main, preview('task.json', { task: { id: def.id, description: t.description ? `${t.description.slice(0, 60)}${t.description.length > 60 ? '…' : ''}` : '', grain: t.grain,
    keys: t.keys.map((k) => k.name), values: t.values.map((v) => ({ name: v.name, type: v.type, rounding: v.rounding || 'discover' })), scope: t.scope, hints: t.hints } },
  ['Rounding: discover', 'Clustering tries the 7 rounding modes of Python’s decimal module on every row and keeps those that reproduce it. Pick one here only if you know it: the pool then tries no other.'])];
}

function addOutput(ctx) {
  const name = h('input', { class: 'input mono', placeholder: 'surrender_value' });
  const part = h('select', { class: 'input' }, h('option', { value: 'key' }, 'Key'), h('option', { value: 'value' }, 'Value'));
  const type = h('select', { class: 'input mono' }, ['string', 'int', 'date', 'Decimal(38, 2)', 'Decimal(38, 4)'].map((x) => h('option', {}, x)));
  return h('details', {}, h('summary', { class: 'btn dashed', style: { listStyle: 'none', display: 'inline-flex' } }, '+ Add a column'),
    h('div', { class: 'row', style: { marginTop: '12px', alignItems: 'flex-end' } },
      h('label', { class: 'field', style: { flex: '1 1 200px' } }, 'Column of the target file', name), h('label', { class: 'field', style: { flex: '0 1 120px' } }, 'Part', part),
      h('label', { class: 'field', style: { flex: '0 1 180px' } }, 'Type', type),
      h('button', { type: 'button', class: 'btn', onClick: () => {
        const n = name.value.trim();
        if (!n) return;
        const list = part.value === 'key' ? ctx.def.task.keys : ctx.def.task.values;
        list.push(part.value === 'key' ? { name: n, type: type.value, meaning: '' } : { name: n, type: type.value, rounding: 'discover', meaning: '' });
        ctx.changed(); ctx.redraw();
      } }, 'Add')));
}

function hintsCard(ctx) {
  const t = ctx.def.task;
  const note = h('input', { class: 'input', placeholder: 'Neuron NG takes the age at the nearest birthday, not the last one.' });
  const fname = h('input', { class: 'input mono', placeholder: 'tier_at_receipt' });
  const fexpr = h('input', { class: 'input mono', placeholder: 'at(BR_TIER, PR_RCVDT)' });
  const verdict = h('span', { class: 'small', role: 'status' });
  return card(h('div', { class: 'stack' }, h('h2', {}, 'Domain hints ', h('span', { class: 'muted', style: { fontWeight: 400, fontSize: '14px' } }, 'optional')),
    h('p', { class: 'small muted' }, 'A note goes to the language model as context. A feature is an expression of the step-5 DSL, parsed now and scored like any other candidate: a hint never becomes a rule on its own.')),
  h('div', { class: 'stack-8' }, t.hints.map((x, i) => h('div', { class: 'row', style: { padding: '14px', border: '1px solid var(--divider)', borderRadius: '6px', gap: '8px 16px' } },
    x.note ? [h('span', { class: 'chip' }, 'Note'), h('span', { style: { flex: '1 1 300px' } }, x.note)] :
      [h('span', { class: 'chip value' }, 'Feature'), h('code', { style: { flex: '1 1 300px' } }, `${x.feature} = ${x.expr}`)],
    h('button', { type: 'button', class: 'icon-btn', 'aria-label': 'Remove hint', style: { marginLeft: 'auto' }, onClick: () => { t.hints.splice(i, 1); ctx.changed(); ctx.redraw(); } }, icons.close())))),
  h('div', { class: 'row', style: { alignItems: 'flex-end' } }, h('label', { class: 'field', style: { flex: '1 1 400px' } }, 'Note', note),
    h('button', { type: 'button', class: 'btn dashed', onClick: () => { if (note.value.trim()) { t.hints.push({ note: note.value.trim() }); ctx.changed(); ctx.redraw(); } } }, '+ Note')),
  h('div', { class: 'row', style: { alignItems: 'flex-end' } }, h('label', { class: 'field', style: { flex: '1 1 160px' } }, 'Feature name', fname),
    h('label', { class: 'field', style: { flex: '2 1 260px' } }, 'Expression', fexpr),
    h('button', { type: 'button', class: 'btn dashed', onClick: async () => {
      const name = fname.value.trim().replace(/[^A-Za-z0-9_]/g, '_');
      if (!name || !fexpr.value.trim()) return;
      const check = await post('/api/dsl/check', { task: ctx.def.id, expr: fexpr.value.trim() }).catch((e) => ({ ok: false, message: e.message }));
      verdict.textContent = check.message;
      verdict.style.color = check.ok ? 'var(--ok)' : 'var(--bad)';
      if (check.ok) { t.hints.push({ feature: name, expr: fexpr.value.trim() }); ctx.changed(); ctx.redraw(); }
    } }, '+ Feature')), verdict);
}

// --- step 3: test pairs ----------------------------------------------------------------------------------------

async function pairsStep(ctx) {
  const { def } = ctx;
  const ex = def.examples;
  ex.use_target = ex.use_target ?? true;
  const target = ex.use_target ? await post('/api/targets/preview', { definition: def }).catch((e) => ({ exists: false, error: e.message })) : null;
  const keys = def.task.keys.map((k) => k.name);
  const values = def.task.values.map((v) => v.name);
  const path = h('input', { id: 'targetPath', class: 'input mono', value: ex.target_file.path || '' });
  const main = [
    card(h('div', { class: 'stack' }, h('h2', {}, 'How will you give examples?'),
      h('p', { class: 'small muted' }, 'Examples are what makes a rule provable: every candidate is scored row by row against them. Without any, the lab can propose rules but cannot check them.')),
    h('div', { class: 'grid' },
      h('label', { class: ['choice', ex.use_target && 'on'] }, h('input', { type: 'checkbox', checked: ex.use_target ? true : null, onChange: (e) => { ex.use_target = e.target.checked; ctx.changed(); ctx.redraw(); } }),
        h('span', { class: 'stack' }, h('span', { class: 'strong' }, 'Target file'), h('span', { class: 'small muted' }, 'A CSV of keys and expected values, exported from the legacy system'))),
      h('label', { class: ['choice', ex.pairs.length && 'on'] }, h('input', { type: 'checkbox', checked: ex.pairs.length ? true : null, onChange: (e) => { if (e.target.checked && !ex.pairs.length) ex.pairs.push(emptyPair(keys, values)); if (!e.target.checked) ex.pairs = []; ctx.changed(); ctx.redraw(); } }),
        h('span', { class: 'stack' }, h('span', { class: 'strong' }, 'Pairs by hand'), h('span', { class: 'small muted' }, 'A few cases you know well, often the tricky ones'))),
      h('div', { class: 'small muted', style: { padding: '14px', border: '1px dashed var(--control)', borderRadius: '6px' } }, 'Leave both empty to skip: the task is saved as ', h('strong', { style: { color: 'var(--ink)' } }, 'unscored'), ' and only step 5 can run.'))),
    ex.use_target ? card(h('div', { class: 'card-head' }, h('h2', {}, 'Target file'),
      target?.exists ? (target.missing.length ? h('span', { class: 'row small', style: { color: 'var(--warn-text)', gap: '6px' } }, icons.warn(), `missing: ${target.missing.join(', ')}`) :
        h('span', { class: 'row small', style: { color: 'var(--ok)', gap: '6px', fontWeight: 500 } }, icons.check(), 'Every output column is in the file')) : null),
    h('div', { class: 'row', style: { alignItems: 'flex-end' } },
      h('label', { class: 'field', style: { flex: '1 1 320px' } }, 'File (absolute, or relative to the targets folder)', path),
      h('button', { type: 'button', class: 'btn dark-outline', onClick: () => { ex.target_file.path = path.value.trim(); ctx.changed(); ctx.redraw(); } }, 'Read file')),
    target?.exists ? [
      table([
        { label: 'In the file', cell: (c) => h('span', { class: 'mono' }, c.file) },
        { label: 'Maps to', cell: (c) => mapSelect(ctx, c) },
        { label: 'First value', cell: (c) => h('span', { class: 'mono small' }, c.example) },
      ], target.columns, { minWidth: '640px', caption: 'Columns of the file, matched to the output of step 2' }),
      h('div', { class: 'grid-200' },
        h('div', { class: 'tint' }, h('span', { class: 'small muted' }, 'Rows'), h('span', { class: 'mono', style: { fontSize: '18px', fontWeight: 500 } }, Number(target.rows).toLocaleString('en-US').replace(/,/g, ' '))),
        h('div', { class: 'tint' }, h('span', { class: 'small muted' }, 'Policies'), h('span', { class: 'mono', style: { fontSize: '18px', fontWeight: 500 } }, Number(target.policies).toLocaleString('en-US').replace(/,/g, ' '))),
        h('div', { class: 'tint' }, h('span', { class: 'small muted' }, 'Held out'), h('span', { class: 'mono', style: { fontSize: '15px', fontWeight: 500 } }, `crc32(${keys[0] || 'policy'}) % 5 == 0`))),
      h('p', { class: 'small muted' }, target.sampled ? 'Above one million rows the lab samples a fixed fifth of the policies. ' : '', 'Columns marked as input join the frame as inputs: a value never depends on a later column of the file.'),
    ] : h('p', { class: 'empty' }, target?.error || `No file at ${target?.path || 'this path'}.`)) : null,
    ex.pairs.length ? card(h('div', { class: 'stack' }, h('h2', {}, 'Pairs by hand'),
      h('p', { class: 'small muted' }, 'The input is a key: the lab joins the legacy rows itself. Pairs must point at keys that exist in the legacy data; synthetic rows, with values the data does not have, are not supported.')),
    ex.pairs.map((p, i) => pairCard(ctx, p, i, keys, values)),
    h('div', { class: 'row', style: { gap: '8px' } },
      h('button', { type: 'button', class: 'btn dashed', onClick: () => { ex.pairs.push(emptyPair(keys, values)); ctx.changed(); ctx.redraw(); } }, '+ Add a pair'),
      pasteRows(ctx, keys, values)),
    h('fieldset', { style: { border: 0, margin: 0, padding: '16px 0 0', borderTop: '1px solid var(--divider)' }, class: 'stack-8' },
      h('legend', { class: 'small strong', style: { padding: 0, marginBottom: '6px', float: 'left', width: '100%' } }, 'Use these pairs for'),
      radio('use', ex.pairs_use !== 'discovery', 'Acceptance only', [' — never shown to the pipeline; checked by ', h('code', {}, 'lab score'), ' on the frozen submission'], () => { ex.pairs_use = 'acceptance'; ctx.changed(); ctx.redraw(); }),
      radio('use', ex.pairs_use === 'discovery', 'Discovery too', ' — added to the target rows, with the same holdout rule', () => { ex.pairs_use = 'discovery'; ctx.changed(); ctx.redraw(); }))) : null,
    footer(ctx, href(ctx, 'task'), href(ctx, 'review'), 'Next: review'),
  ];
  return [main, preview('task.json', { examples: { target_file: ex.use_target ? { path: ex.target_file.path, inputs: ex.target_file.inputs, holdout: 'crc32 % 5 == 0' } : null,
    pairs: ex.pairs, pairs_use: ex.pairs_use } },
  ['Why keys, not full rows', 'A key keeps the pair tied to the real legacy rows, so the frame of step 1 and the trace of lab viz policy work on it unchanged.'])];
}

function radio(name, on, title, rest, pick) {
  return h('label', { class: 'check' }, h('input', { type: 'radio', name, checked: on ? true : null, onChange: pick }), h('span', {}, h('strong', {}, title), h('span', { class: 'muted' }, rest)));
}

function mapSelect(ctx, column) {
  const t = ctx.def.task;
  const inputs = ctx.def.examples.target_file.inputs;
  return h('select', { class: 'input mono', style: { minHeight: '36px' }, 'aria-label': `Role of ${column.file}`, onChange: (e) => {
    t.keys = t.keys.filter((k) => k.name !== column.file);
    t.values = t.values.filter((v) => v.name !== column.file);
    ctx.def.examples.target_file.inputs = inputs.filter((x) => x !== column.file);
    if (e.target.value === 'key') t.keys.push({ name: column.file, type: guessType(column.example), meaning: '' });
    if (e.target.value === 'value') t.values.push({ name: column.file, type: guessType(column.example), rounding: 'discover', meaning: '' });
    if (e.target.value === 'input') ctx.def.examples.target_file.inputs.push(column.file);
    ctx.changed(); ctx.redraw();
  } }, [['key', 'key'], ['value', 'value'], ['input', 'input'], ['unused', 'not used']].map(([v, label]) => h('option', { value: v, selected: column.part === v ? true : null }, label)));
}

function guessType(example) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(example)) return 'date';
  if (/^-?\d+$/.test(example)) return 'int';
  const m = example.match(/^-?\d+\.(\d+)$/);
  return m ? `Decimal(38, ${m[1].length})` : 'string';
}

function emptyPair(keys, values) {
  return { in: Object.fromEntries(keys.map((k) => [k, ''])), out: Object.fromEntries(values.map((v) => [v, ''])), noise: false };
}

function pairCard(ctx, p, i, keys, values) {
  const info = h('div', { class: 'row small', style: { gap: '6px' } });
  const resolve = async () => {
    if (!keys.every((k) => p.in[k])) return;
    const r = await post('/api/pairs/resolve', { definition: ctx.def, key: p.in }).catch(() => null);
    if (!r) return;
    info.replaceChildren(h('span', { class: 'muted' }, 'Joined:'), ...r.joined.map((j) => h('span', { class: 'mono' }, `${j.table} ${j.rows}`)),
      h('span', { class: 'muted' }, r.in_target ? '· in the target file' : '· not in the target file'),
      r.listed ? h('span', { class: 'row', style: { gap: '6px', padding: '4px 10px', borderRadius: '6px', background: 'var(--warn-tint)', color: '#6E3A0F' } }, icons.warn(), 'NREXCP has an entry for this policy: the value was probably typed by hand.') : null);
  };
  setTimeout(resolve, 0);
  return h('article', { 'aria-label': `Pair ${i + 1}`, style: { border: `1px solid ${p.noise ? '#E8C9A6' : 'var(--divider)'}`, borderRadius: '6px', display: 'flex', flexWrap: 'wrap' } },
    h('div', { class: 'stack-8', style: { flex: '1 1 340px', padding: '16px', borderRight: '1px solid var(--divider)' } },
      h('div', { class: 'tiny muted strong', style: { letterSpacing: '0.06em', textTransform: 'uppercase' } }, 'Input'),
      h('div', { class: 'row' }, keys.map((k) => h('label', { class: 'field', style: { flex: '1 1 140px' } }, k,
        h('input', { class: 'input mono', value: p.in[k] || '', onChange: (e) => { p.in[k] = e.target.value.trim(); ctx.changed(); resolve(); } })))),
      info),
    h('div', { class: 'stack-8', style: { flex: '1 1 260px', padding: '16px', background: 'var(--tint-2)' } },
      h('div', { class: 'row-between' }, h('span', { class: 'tiny muted strong', style: { letterSpacing: '0.06em', textTransform: 'uppercase' } }, 'Expected output'),
        h('button', { type: 'button', class: 'icon-btn', 'aria-label': `Remove pair ${i + 1}`, onClick: () => { ctx.def.examples.pairs.splice(i, 1); ctx.changed(); ctx.redraw(); } }, icons.close())),
      values.map((v) => h('label', { class: 'field' }, v, h('input', { class: 'input mono', style: { textAlign: 'right' }, value: p.out[v] || '', onChange: (e) => { p.out[v] = e.target.value.trim(); ctx.changed(); } }))),
      h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: p.noise ? true : null, onChange: (e) => { p.noise = e.target.checked; ctx.changed(); ctx.redraw(); } }), 'Typed by hand: keep out of discovery')));
}

function pasteRows(ctx, keys, values) {
  const area = h('textarea', { class: 'input mono', rows: 5, placeholder: [...keys, ...values].join('\t') });
  return h('details', {}, h('summary', { class: 'btn dashed', style: { listStyle: 'none', display: 'inline-flex' } }, 'Paste rows from a spreadsheet'),
    h('div', { class: 'stack-8', style: { marginTop: '12px' } }, h('span', { class: 'small muted' }, `One row per line, columns separated by tabs, in this order: ${[...keys, ...values].join(', ')}`), area,
      h('div', {}, h('button', { type: 'button', class: 'btn', onClick: () => {
        const rows = area.value.split(/\r?\n/).map((l) => l.split('\t').map((x) => x.trim())).filter((r) => r.length >= keys.length + values.length);
        for (const r of rows) ctx.def.examples.pairs.push({ in: Object.fromEntries(keys.map((k, i) => [k, r[i]])), out: Object.fromEntries(values.map((v, i) => [v, r[keys.length + i]])), noise: false });
        toast(`${rows.length} pair${rows.length === 1 ? '' : 's'} added`);
        ctx.changed(); ctx.redraw();
      } }, 'Add the rows'))));
}

// --- step 4: review and run ------------------------------------------------------------------------------------

async function reviewStep(ctx) {
  const { def, draft } = ctx;
  const [{ checks }, settings] = await Promise.all([post('/api/tasks/check', { definition: definitionToSave(def) }).catch((e) => ({ checks: [{ level: 'error', title: 'The checks did not run', detail: e.message }] })), get('/api/settings')]);
  const blocked = checks.some((c) => c.level === 'error');
  def.run = def.run || { steps: PIPELINE.map(([k]) => k), model: '', max_features: 3, suggest: false };
  const steps = new Set(def.run.steps);
  const features = def.task.hints.filter((x) => x.feature);
  const commands = [`lab task add tasks/${def.id || '<id>'}.json`, steps.size === PIPELINE.length ? `lab run ${def.id}` : [...steps].map((st) => `lab ${st} ${def.id}`).join('\n'),
    ...features.map((f) => `lab feature ${def.id} ${f.feature} "${f.expr}"`), def.run.suggest ? `lab suggest ${def.id}${def.run.max_features !== 3 ? ` --max-features ${def.run.max_features}` : ''}` : null].filter(Boolean);
  const save = async (andRun) => {
    try {
      await post('/api/tasks/save', { definition: definitionToSave(def) });
      draft.saved = true;
      draft.dirty = false;
      try { localStorage.removeItem(storageKey(ctx.task)); } catch (e) { /* nothing kept */ }
      if (!andRun) {
        toast(`Saved as lab/tasks/${def.id}.json`);
        if (ctx.task !== def.id) { drafts[def.id] = draft; location.hash = `#/tasks/${encodeURIComponent(def.id)}/review`; } else ctx.redraw();
        return;
      }
      const job = await post('/api/jobs', { action: 'run', task: def.id, options: { steps: [...steps], suggest: def.run.suggest, model: def.run.model, max_features: def.run.max_features, features: features.map((f) => ({ name: f.feature, expr: f.expr })) } });
      location.hash = `#/jobs/${job.id}`;
    } catch (e) {
      toast(e.message, true);
    }
  };
  const t = def.task;
  const main = [
    h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' } },
      summary('Legacy data', href(ctx, 'legacy'), def.legacy.path || '—', `${def.legacy.tables.length} tables · ${def.legacy.joins.filter((j) => j.keep !== false).length} relationships`,
        `${def.legacy.tables.reduce((n, x) => n + Object.values(x.columns || {}).filter((c) => c.type).length, 0)} types confirmed by hand`),
      summary('Task', href(ctx, 'task'), def.id || '(no id)', `${t.grain || '—'} → ${t.values.map((v) => v.name).join(', ') || '—'}`,
        `${t.hints.filter((x) => x.note).length} note · ${features.length} feature`),
      summary('Examples', href(ctx, 'pairs'), def.examples.use_target === false ? 'no target file' : def.examples.target_file.path || '—', 'Holdout: 1 policy in 5',
        def.examples.pairs.length ? `Pairs: ${def.examples.pairs.length}, ${def.examples.pairs_use}` : 'No pairs')),
    card(h('h2', {}, 'Checks'), h('ul', { style: { listStyle: 'none', margin: 0, padding: 0 } }, checks.map((c) => h('li', { class: 'row', style: { gap: '12px', alignItems: 'flex-start', padding: '12px 0', borderTop: '1px solid var(--divider)', flexWrap: 'nowrap' } },
      h('span', { class: ['level', `level-${c.level}`] }, c.level === 'warning' ? 'warning' : c.level), h('span', { class: 'stack' }, h('span', { style: { fontWeight: 500 } }, c.title), h('span', { class: 'small muted' }, c.detail)))))),
    card(h('div', { class: 'stack' }, h('h2', {}, 'Run'), h('p', { class: 'small muted' }, 'Save only, or save and run the pipeline now. Each step writes its artifacts under ', h('code', {}, `runs/${def.id || '<id>'}/`), '.')),
      h('fieldset', { style: { border: 0, margin: 0, padding: 0 }, class: 'stack-8' }, h('legend', { class: 'small strong', style: { padding: 0, marginBottom: '6px' } }, 'Steps'),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '4px 16px' } },
          PIPELINE.map(([key, label], i) => h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: steps.has(key) ? true : null,
            onChange: (e) => { def.run.steps = PIPELINE.map(([k]) => k).filter((k) => (k === key ? e.target.checked : steps.has(k))); ctx.changed(); ctx.redraw(); } }),
          h('span', { class: 'mono muted' }, i + 1), label)),
          h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: def.run.suggest ? true : null, onChange: (e) => { def.run.suggest = e.target.checked; ctx.changed(); ctx.redraw(); } }),
            h('span', { class: 'mono muted' }, '+'), 'Language model features (step 5)'))),
      h('div', { class: 'row', style: { padding: '16px', borderRadius: '6px', background: 'var(--tint)', alignItems: 'flex-end' } },
        h('label', { class: 'field', style: { flex: '1 1 200px' } }, 'Model for step 5', h('select', { class: 'input', onChange: (e) => { def.run.model = e.target.value; ctx.changed(); ctx.redraw(); } },
          [['', `Claude Code default${settings.model ? ` (LLM_MODEL=${settings.model})` : ''}`], ['opus', 'opus'], ['sonnet', 'sonnet']].map(([v, label]) => h('option', { value: v, selected: def.run.model === v ? true : null }, label)))),
        h('label', { class: 'field', style: { flex: '1 1 200px' } }, 'Features per request', h('input', { class: 'input', type: 'number', min: 1, max: 3, value: def.run.max_features,
          onChange: (e) => { def.run.max_features = Math.max(1, Math.min(3, Number(e.target.value) || 3)); ctx.changed(); ctx.redraw(); } })),
        h('p', { class: 'small muted', style: { flex: '1 1 100%' } }, settings.claude ? 'Step 5 runs only where the trees need a feature that is not in the data yet. Every proposal is parsed in the DSL and scored exactly, before and after.' :
          'Claude Code is not on the PATH of the server: step 5 will fail until `claude` is installed and logged in.')),
      tech('cli', 'Same on the command line', h('pre', { class: 'code' }, commands.join('\n')))),
    h('div', { class: 'row-between', style: { padding: '16px 0' } }, h('a', { class: 'btn', href: href(ctx, 'pairs') }, 'Back'),
      h('div', { class: 'row' },
        h('button', { type: 'button', class: 'btn', disabled: blocked ? true : null, onClick: () => save(false) }, 'Save definition'),
        h('button', { type: 'button', class: 'btn primary', disabled: blocked ? true : null, onClick: () => save(true) }, 'Save and run'))),
  ];
  return [main, [tech('json', `tasks/${def.id || '<id>'}.json`, h('pre', {}, JSON.stringify(definitionToSave(def), null, 2)), 'dark'),
    h('div', { class: 'card tight', style: { gap: '8px' } }, h('h3', {}, 'One file, versioned'),
      h('p', { class: 'small muted' }, 'The definition sits in ', h('code', {}, 'lab/tasks/'), ' next to ', h('code', {}, 'rules/'), ', so the pipeline, the agent of ', h('code', {}, 'lab agent'), ' and this page read the same task.'))]];
}

function summary(title, link, mono, line1, line2) {
  return h('section', { class: 'card tight', style: { gap: '8px' } },
    h('div', { class: 'row-between' }, h('h2', { style: { fontSize: '15px' } }, title), h('a', { href: link, class: 'small' }, 'Edit')),
    h('div', { class: 'mono small muted', style: { overflowWrap: 'anywhere' } }, mono), h('div', { class: 'small' }, line1), h('div', { class: 'small' }, line2));
}

function definitionToSave(def) {
  const copy = JSON.parse(JSON.stringify(def));
  if (copy.examples.use_target === false) copy.examples.target_file = { path: '', inputs: [] };
  delete copy.examples.use_target;
  for (const t of copy.legacy.tables) {
    for (const [c, spec] of Object.entries(t.columns || {})) if (!spec.type) delete t.columns[c];
  }
  return copy;
}
