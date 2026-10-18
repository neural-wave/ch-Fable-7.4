// Tasks: every target the lab knows, its definition, its last result; "New task" opens the four steps.
import { get, h, header, loading, mount, start, table } from '../lib/h.js';

export async function render(root) {
  loading(root, 'tasks');
  const { tasks } = await get('/api/tasks');
  mount(root, header('tasks'), h('div', { class: 'wrap' },
    h('div', { class: 'row-end' },
      h('div', { class: 'stack' }, h('h1', {}, 'Tasks'),
        h('p', { class: 'small muted' }, 'A task is a target file of the legacy system to reproduce to the cent. A definition says what it is, where it comes from and how to check it; without one, the pipeline infers everything.')),
      h('a', { class: 'btn primary', href: '#/tasks/new/legacy' }, 'New task')),
    h('section', { class: 'card flush' }, table([
      { label: 'Task', cell: (t) => h('span', { class: 'stack' }, h('span', { class: 'mono strong' }, t.id), t.title ? h('span', { class: 'small muted' }, t.title) : null) },
      { label: 'Definition', cell: (t) => (t.defined ? h('span', { class: 'chip', style: { background: 'var(--ok-bg)', color: 'var(--ok)' } }, 'saved') : h('span', { class: 'small muted' }, t.run ? 'inferred by the pipeline' : 'none')) },
      { label: 'Scoring', cell: (t) => h('span', { class: 'small' }, t.scored ? 'official (check.py)' : t.target ? 'lab only' : 'no target file') },
      { label: 'Holdout', num: true, key: 'holdout' },
      { label: 'Submission', cell: (t) => h('span', { class: 'small muted' }, t.frozen) },
      { label: h('span', { class: 'sr' }, 'Actions'), cell: (t) => h('span', { class: 'row', style: { gap: '6px', justifyContent: 'flex-end' } },
        h('a', { class: 'btn small', href: `#/tasks/${encodeURIComponent(t.id)}/legacy` }, t.defined ? 'Edit' : 'Define'),
        t.run ? h('a', { class: 'btn small', href: `#/runs/${encodeURIComponent(t.id)}` }, 'Last run') : null,
        t.target ? h('button', { type: 'button', class: 'btn small', onClick: () => start('run', t.id) }, 'Run') : null) },
    ], tasks, { minWidth: '900px' }))));
}
