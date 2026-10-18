// Run · in progress: the seven steps as they happen, the log, the queue, the agent. Server-sent events drive it.
import { get, h, header, icons, loading, mount, pill, post, tech, toast } from '../lib/h.js';

const DOT = {
  done: { background: 'var(--ok-dot)', color: '#fff', border: '0' },
  skipped: { background: '#fff', color: 'var(--muted)', border: '1px dashed var(--faint)' },
  running: { background: 'var(--ink)', color: '#fff', border: '0' },
  waiting: { background: '#fff', color: 'var(--muted)', border: '1px solid var(--line)' },
  failed: { background: 'var(--accent)', color: '#fff', border: '0' },
  cancelled: { background: 'var(--accent)', color: '#fff', border: '0' },
};
const STATE_TEXT = { done: 'Done', skipped: 'Reused or not in this run', running: 'Running', waiting: 'Waiting', failed: 'Failed', cancelled: 'Cancelled' };

export async function render(root, { job: id }) {
  loading(root, 'runs');
  let view = await get(`/api/jobs/${encodeURIComponent(id)}`);
  let follow = true;
  let source = null;
  let pending = null;

  const draw = () => {
    const { job, steps, progress, log } = view;
    const live = ['running', 'queued'].includes(job.status);
    const current = steps.find((st) => st.state === 'running');
    const doneCount = steps.filter((st) => st.state === 'done').length;
    const logBox = h('div', { role: 'log', 'aria-live': 'polite', class: 'log' }, log.map(logLine));
    mount(root, header('runs'), h('div', { class: 'wrap' },
      h('div', { class: 'row-end' },
        h('div', { class: 'stack-8' },
          h('div', { class: 'crumbs' }, h('a', { href: '#/runs' }, 'Runs'), ` / ${job.run}`),
          h('div', { class: 'row' }, h('h1', { class: 'mono' }, job.run), pill(job.status)),
          h('div', { class: 'small muted' }, `${job.kind} · ${job.status === 'queued' ? 'queued' : `started ${job.started_text.toLowerCase()}`} · ${live ? 'running for' : 'took'} ${job.took}${job.origin === 'page' ? '' : ` · ${job.origin}`}`)),
        h('div', { class: 'row' },
          view.agent?.trace ? h('a', { class: 'btn', href: `/files/${encodeURIComponent(job.run)}/${view.agent.trace}` }, 'Open the agent trace') : null,
          live ? h('button', { type: 'button', class: 'btn danger', onClick: cancel }, job.status === 'queued' ? 'Remove from queue' : 'Cancel run') :
            h('a', { class: 'btn primary', href: `#/runs/${encodeURIComponent(job.run)}` }, 'Open the run'))),
      ['failed', 'interrupted', 'cancelled'].includes(job.status) ? h('div', { class: 'banner bad', role: 'alert' }, icons.info(),
        h('span', {}, job.status === 'failed' ? `The job stopped with exit code ${job.exit}: the log below says why.` :
          job.status === 'cancelled' ? 'The job was cancelled.' : 'The server stopped while this job ran.')) : null,
      job.status === 'done' ? h('div', { class: 'banner ok', role: 'status' }, icons.check(), h('span', {}, 'Done. '), h('a', { href: `#/runs/${encodeURIComponent(job.run)}` }, 'See the results')) : null,
      h('section', { class: 'card tight', 'aria-label': 'Progress' },
        h('div', { class: 'row-between' },
          h('span', { class: 'strong' }, current ? `Step ${current.n} of 7 · ${current.name}` : (live ? 'Starting…' : `${doneCount} steps done`)),
          progress?.best ? h('span', { class: 'small muted' }, 'Best so far, discovery only: ', h('b', { class: 'mono', style: { fontWeight: 500, color: 'var(--ink)' } }, pct(progress.best))) : null),
        h('div', { class: 'progress7', role: 'progressbar', 'aria-label': 'Pipeline progress', 'aria-valuemin': 0, 'aria-valuemax': 7, 'aria-valuenow': doneCount },
          steps.map((st) => h('span', { class: st.state }, st.state === 'running' ? h('i', { style: { width: `${fraction(st) * 100}%` } }) : null)))),
      h('div', { class: 'columns' },
        h('main', { class: 'main' },
          h('section', { class: 'card', style: { gap: '8px' } }, h('h2', { style: { marginBottom: '8px' } }, 'Steps'),
            h('ol', { style: { listStyle: 'none', margin: 0, padding: 0 } }, steps.map((st) => h('li', { class: 'row', style: { gap: '16px', alignItems: 'flex-start', padding: '12px 0', borderTop: '1px solid var(--divider)', flexWrap: 'nowrap' } },
              h('span', { 'aria-hidden': 'true', style: { flex: 'none', width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--mono)', fontSize: '13px', boxSizing: 'border-box', ...DOT[st.state] } }, st.n),
              h('span', { class: 'stack', style: { flex: '1 1 auto', minWidth: 0 } },
                h('span', { class: 'row-between', style: { gap: '4px 16px' } }, h('span', { class: 'strong' }, st.name),
                  h('span', { class: 'small', style: { fontWeight: 500, color: st.state === 'done' ? 'var(--ok)' : 'var(--muted)' } }, STATE_TEXT[st.state] + (st.secs ? ` · ${st.secs} s` : ''))),
                st.files?.length ? h('span', { class: 'small muted mono' }, st.files.join(' · ')) : null,
                st.progress ? h('span', { class: 'row', style: { gap: '12px', marginTop: '4px' } },
                  h('span', { class: 'bar', style: { height: '6px' } }, h('i', { style: { width: `${fraction(st) * 100}%`, height: '6px', background: 'var(--ink)' } })),
                  h('span', { class: 'mono small' }, `${st.progress.done} / ${st.progress.total}`)) : null))))),
          h('section', { class: 'dark', style: { padding: '20px 24px' } },
            h('div', { class: 'row-between' }, h('h2', {}, 'Log'),
              h('label', { class: 'check', style: { color: 'var(--code-fg)', fontSize: '13px' } }, h('input', { type: 'checkbox', checked: follow ? true : null, onChange: (e) => { follow = e.target.checked; } }), 'Follow')),
            logBox)),
        h('aside', { class: 'aside', 'aria-label': 'Queue and agent' },
          h('section', { class: 'card tight' },
            h('div', { class: 'stack' }, h('h3', {}, 'Queue'), h('p', { class: 'small muted' }, 'Jobs run one after the other: they write into the same run folders and the agent edits submission.py.')),
            h('ol', { style: { listStyle: 'none', margin: 0, padding: 0 } },
              h('li', { class: 'row-between', style: { padding: '10px 0', borderTop: '1px solid var(--divider)' } }, h('span', { class: 'mono strong' }, `${job.task} · ${job.kind}`), pill(job.status)),
              view.queue.map((q) => h('li', { class: 'row-between', style: { padding: '10px 0', borderTop: '1px solid var(--divider)' } },
                h('a', { href: `#/jobs/${q.id}`, class: 'mono' }, `${q.task} · ${q.kind}`), h('span', { class: 'small muted' }, 'Queued')))),
            tech('cli', 'Command line', h('pre', { class: 'code', style: { whiteSpace: 'pre-wrap' } }, (job.commands || []).join('\n'))),
            view.queue.length ? h('button', { type: 'button', class: 'btn small', onClick: stopQueue }, 'Stop after this job') : null),
          view.agent ? h('section', { class: 'card tight' },
            h('div', { class: 'stack' }, h('h3', {}, 'Agent'), h('p', { class: 'small muted' }, 'Claude Code with the rule-discovery skill', view.agent.trace ? [' · trace in ', h('code', {}, view.agent.trace)] : ' · waiting for its trace')),
            h('ol', { class: 'stack-8', style: { listStyle: 'none', margin: 0, padding: 0, fontSize: '14px' } }, view.agent.items.map((it) => h('li', { class: 'row', style: { gap: '10px', flexWrap: 'nowrap', alignItems: 'flex-start' } },
              h('span', { class: 'mono tiny muted', style: { paddingTop: '2px', minWidth: '44px' } }, it.tool), h('span', { style: { overflowWrap: 'anywhere' } }, it.what))))) : null,
          h('section', { class: 'card tight' }, h('h3', {}, 'Written so far'),
            view.written.length ? view.written.filter((f) => !f.endsWith('.parquet')).map((f) => h('a', { href: `/files/${encodeURIComponent(job.run)}/${f}`, class: 'mono small' }, f)) :
              h('p', { class: 'small muted' }, 'Nothing yet.'))))));
    if (follow) logBox.scrollTop = logBox.scrollHeight;
  };

  const refresh = () => {
    if (pending) return;
    pending = setTimeout(async () => {
      pending = null;
      view = await get(`/api/jobs/${encodeURIComponent(id)}`).catch(() => view);
      draw();
    }, 400);
  };

  async function cancel() {
    try {
      await post(`/api/jobs/${encodeURIComponent(id)}/cancel`);
      toast('Cancelled');
      refresh();
    } catch (e) {
      toast(e.message, true);
    }
  }

  async function stopQueue() {
    const result = await post('/api/queue/stop').catch((e) => toast(e.message, true));
    if (result) toast(`${result.cancelled} queued job${result.cancelled === 1 ? '' : 's'} removed`);
    refresh();
  }

  draw();
  if (['running', 'queued'].includes(view.job.status)) {
    source = new EventSource(`/api/jobs/${encodeURIComponent(id)}/events`);
    source.addEventListener('events', refresh);
    source.addEventListener('log', refresh);
    source.addEventListener('end', () => { source.close(); refresh(); });
  }
  const poll = setInterval(() => { if (view.job.status === 'queued') refresh(); }, 3000);
  return () => { source?.close(); clearInterval(poll); clearTimeout(pending); };
}

function logLine(text) {
  const m = text.match(/^(\w+)\s+(\S+)\s+([\d.]+s)$/);
  if (m) return h('div', {}, h('span', { class: 's' }, m[1]), `${m[2]}  ${m[3]}`);
  return h('div', {}, text);
}

function fraction(st) {
  if (!st.progress || !st.progress.total) return st.state === 'running' ? 0.15 : 0;
  return st.progress.done / st.progress.total;
}

function pct(pair) {
  return pair && pair[1] ? `${(100 * pair[0] / pair[1]).toFixed(2)} %` : '—';
}
