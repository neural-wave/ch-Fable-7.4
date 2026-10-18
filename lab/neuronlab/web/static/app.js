// Ergo: hash routes -> views. Each view module exports render(root, params) and may return a cleanup function.
import { failure } from './lib/h.js';

const routes = [
  [/^#\/runs\/?$/, 'runs', () => ({})],
  [/^#\/runs\/([^/]+)\/clusters$/, 'clusters', (m) => ({ run: decodeURIComponent(m[1]) })],
  [/^#\/runs\/([^/]+)\/trees$/, 'trees', (m) => ({ run: decodeURIComponent(m[1]) })],
  [/^#\/runs\/([^/]+)\/flow$/, 'flow', (m) => ({ run: decodeURIComponent(m[1]) })],
  [/^#\/runs\/([^/#]+)(?:#(\w+))?$/, 'run', (m) => ({ run: decodeURIComponent(m[1]), anchor: m[2] })],
  [/^#\/jobs\/([^/]+)$/, 'live', (m) => ({ job: decodeURIComponent(m[1]) })],
  [/^#\/tasks\/?$/, 'tasks', () => ({})],
  [/^#\/tasks\/([^/]+)\/(legacy|task|pairs|review)$/, 'wizard', (m) => ({ task: decodeURIComponent(m[1]), step: m[2] })],
];

let cleanup = null;
let generation = 0;

function parseQuery() {
  const [hash, query] = location.hash.split('?');
  return { hash, query: new URLSearchParams(query || '') };
}

async function route() {
  const root = document.getElementById('app');
  const { hash, query } = parseQuery();
  const found = routes.find(([pattern]) => pattern.test(hash));
  if (!found) {
    location.replace('#/runs');
    return;
  }
  const [pattern, name, params] = found;
  const mine = ++generation;
  if (typeof cleanup === 'function') cleanup();
  cleanup = null;
  try {
    const view = await import(`./views/${name}.js`);
    if (mine !== generation) return;
    cleanup = await view.render(root, { ...params(hash.match(pattern)), query });
  } catch (e) {
    console.error(e);
    if (mine === generation) failure(root, ['tasks', 'wizard'].includes(name) ? 'tasks' : 'runs', e);
  }
  if (!location.hash.includes('#candidates') && !location.hash.includes('#residuals')) window.scrollTo(0, 0);
}

window.addEventListener('hashchange', route);
route();
