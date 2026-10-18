// Tasks: every target the lab knows, its definition, its last result; "New task" opens the four steps.
import { get, h, header, loading, mount, start, table, term } from '../lib/h.js';

export async function render(root) {
  loading(root, 'tasks');
  const { tasks } = await get('/api/tasks');
  mount(root, header('tasks'), h('div', { class: 'wrap' },
    h('div', { class: 'row-end' },
      h('div', { class: 'stack' }, h('h1', {}, 'Tasks'),
        h('p', { class: 'small muted' }, 'A task is a target file of the legacy system to reproduce to the cent. A definition says what it is, where it comes from and how to check it; without one, the pipeline infers everything.')),
      h('a', { class: 'btn primary', href: '#/tasks/new/legacy' }, 'New task')),
    h('ol', { class: 'guide', 'aria-label': 'How it works' },
      h('li', {}, h('span', {}, h('b', {}, 'Define'), h('span', { class: 'muted' }, 'Optional: tables, keys and test pairs of the task.'))),
      h('li', {}, h('span', {}, h('b', {}, 'Run'), h('span', { class: 'muted' }, 'The pipeline searches for the formula and scores every candidate.'))),
      h('li', {}, h('span', {}, h('b', {}, 'Review'), h('span', { class: 'muted' }, 'Open the last run: candidates, wrong rows, control flow.'))),
      h('li', {}, h('span', {}, h('b', {}, 'Freeze'), h('span', { class: 'muted' }, 'Write the winner into submission.py and score it.')))),
    h('section', { class: 'card flush' }, table([
      { label: 'Task', cell: (t) => h('span', { class: 'stack' }, h('span', { class: 'strong' }, t.id), t.title ? h('span', { class: 'small muted' }, t.title) : null) },
      { label: 'Definition', cell: (t) => (t.defined ? h('span', { class: 'chip', style: { background: 'var(--ok-bg)', color: 'var(--ok)' } }, 'saved') : h('span', { class: 'small muted' }, t.run ? 'inferred by the pipeline' : 'none')) },
      { label: 'Scoring', cell: (t) => h('span', { class: 'small' }, t.scored ? 'official (check.py)' : t.target ? 'lab only' : 'no target file') },
      { label: term('Holdout'), num: true, key: 'holdout' },
      { label: 'Submission', cell: (t) => h('span', { class: 'small muted' }, t.frozen) },
      { label: h('span', { class: 'sr' }, 'Actions'), cell: (t) => h('span', { class: 'actions' },
        h('a', { class: 'btn small', href: `#/tasks/${encodeURIComponent(t.id)}/legacy` }, t.defined ? 'Edit' : 'Define'),
        t.run ? h('a', { class: 'btn small', href: `#/runs/${encodeURIComponent(t.id)}` }, 'Last run') : null,
        h('button', { type: 'button', class: ['btn small', !t.run && t.target && 'primary'], disabled: t.target ? null : true,
          title: t.target ? `Run the pipeline on ${t.id}` : 'No target file to learn from', onClick: () => start('run', t.id) }, 'Run')) },
    ], tasks, { minWidth: '900px' }))));
}
