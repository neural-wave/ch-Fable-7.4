// A pan-and-zoom canvas for a laid-out diagram (coordinates from layout.py).
// Drag or arrow keys move it; Ctrl/⌘ + wheel, a trackpad pinch, double click or +/- zoom; 0 fits it.
// The element persists across redraws of its page: setContent() only swaps the diagram inside.
import { h, s } from './h.js';

const MIN = 0.2;
const MAX = 3;
const PAD = 32;
const MOD = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘' : 'Ctrl';

const icon = (...d) => s('svg', { width: 16, height: 16, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round', 'aria-hidden': 'true' },
  d.map((p) => s('path', { d: p })));

export function zoomCanvas(label) {
  const view = { x: 0, y: 0, k: 1, size: null, fitted: false };
  const stage = h('div', { class: 'canvas-stage' });
  const level = h('button', { type: 'button', class: 'canvas-btn canvas-level', title: 'Actual size (1)', onClick: () => zoomTo(1) }, '100%');
  const hint = h('div', { class: 'canvas-hint', 'aria-hidden': 'true' }, `${MOD} + scroll to zoom`);
  const viewport = h('div', { class: 'canvas-viewport', tabindex: '0', role: 'region',
    'aria-label': `${label}: drag or use the arrow keys to move, plus and minus to zoom, 0 to fit` }, stage, hint);
  const fullscreen = h('button', { type: 'button', class: 'canvas-btn', title: 'Full screen', 'aria-label': 'Full screen', onClick: toggleFullscreen },
    icon('M2.5 6V2.5H6', 'M10 2.5h3.5V6', 'M13.5 10v3.5H10', 'M6 13.5H2.5V10'));
  const root = h('div', { class: 'canvas' }, viewport,
    h('div', { class: 'canvas-tools', role: 'toolbar', 'aria-label': 'Zoom' },
      h('button', { type: 'button', class: 'canvas-btn', title: 'Zoom out (−)', 'aria-label': 'Zoom out', onClick: () => zoomBy(1 / 1.25) }, icon('M3.5 8h9')),
      level,
      h('button', { type: 'button', class: 'canvas-btn', title: 'Zoom in (+)', 'aria-label': 'Zoom in', onClick: () => zoomBy(1.25) }, icon('M3.5 8h9', 'M8 3.5v9')),
      h('span', { class: 'canvas-sep', 'aria-hidden': 'true' }),
      h('button', { type: 'button', class: 'canvas-btn canvas-text', title: 'Fit to view (0)', onClick: fit }, 'Fit'),
      fullscreen),
    h('div', { class: 'canvas-help', 'aria-hidden': 'true' }, `Drag to move · ${MOD} + scroll to zoom`));

  function apply() {
    stage.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`;
    level.textContent = `${Math.round(view.k * 100)}%`;
  }

  function center() {
    const r = viewport.getBoundingClientRect();
    return [r.width / 2, r.height / 2];
  }

  // Zoom keeping the point (cx, cy) of the viewport still.
  function zoomAt(factor, cx, cy) {
    const k = Math.min(MAX, Math.max(MIN, view.k * factor));
    view.x = cx - (cx - view.x) * (k / view.k);
    view.y = cy - (cy - view.y) * (k / view.k);
    view.k = k;
    apply();
  }

  function zoomBy(factor) { zoomAt(factor, ...center()); }
  function zoomTo(k) { zoomAt(k / view.k, ...center()); }

  function fit() {
    const r = viewport.getBoundingClientRect();
    if (!view.size || !r.width) return;
    view.k = Math.min(1, Math.max(MIN, Math.min((r.width - 2 * PAD) / view.size.w, (r.height - 2 * PAD) / view.size.h)));
    view.x = (r.width - view.size.w * view.k) / 2;
    view.y = Math.max(PAD, (r.height - view.size.h * view.k) / 2);
    apply();
  }

  // As tall as the diagram once it fits the width, between 240 px and most of the window.
  function sizeViewport() {
    const width = viewport.getBoundingClientRect().width;
    const k = width ? Math.min(1, Math.max(MIN, (width - 2 * PAD) / view.size.w)) : 1;
    viewport.style.height = `${Math.round(Math.max(240, Math.min(view.size.h * k + 2 * PAD, window.innerHeight * 0.72)))}px`;
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else root.requestFullscreen?.();
  }
  root.addEventListener('fullscreenchange', () => requestAnimationFrame(fit));

  // Drag: listeners on window, so a redraw of the page during a drag does not drop it.
  // A drag that starts on a clickable node (a leaf of the tree) must not click it when it ends.
  let dragged = false;
  viewport.addEventListener('click', (e) => { if (dragged) { e.stopPropagation(); e.preventDefault(); } }, true);
  viewport.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    const start = { px: e.clientX, py: e.clientY, x: view.x, y: view.y };
    dragged = false;
    viewport.classList.add('grabbing');
    const move = (ev) => {
      if (Math.abs(ev.clientX - start.px) + Math.abs(ev.clientY - start.py) > 4) dragged = true;
      view.x = start.x + ev.clientX - start.px; view.y = start.y + ev.clientY - start.py; apply();
    };
    const up = () => { viewport.classList.remove('grabbing'); window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  });

  // Ctrl/⌘ + wheel and trackpad pinches (they arrive as wheel + ctrlKey) zoom; a plain wheel scrolls the page.
  let hintTimer = null;
  viewport.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) {
      hint.classList.add('on');
      clearTimeout(hintTimer);
      hintTimer = setTimeout(() => hint.classList.remove('on'), 1200);
      return;
    }
    e.preventDefault();
    const r = viewport.getBoundingClientRect();
    const delta = Math.max(-50, Math.min(50, e.deltaY));
    zoomAt(2 ** (-delta * 0.01), e.clientX - r.left, e.clientY - r.top);
  }, { passive: false });

  viewport.addEventListener('dblclick', (e) => {
    const r = viewport.getBoundingClientRect();
    zoomAt(1.6, e.clientX - r.left, e.clientY - r.top);
  });

  viewport.addEventListener('keydown', (e) => {
    const pan = { ArrowLeft: [60, 0], ArrowRight: [-60, 0], ArrowUp: [0, 60], ArrowDown: [0, -60] }[e.key];
    if (pan) { view.x += pan[0]; view.y += pan[1]; apply(); } else if (e.key === '+' || e.key === '=') zoomBy(1.25);
    else if (e.key === '-') zoomBy(1 / 1.25);
    else if (e.key === '0') fit();
    else if (e.key === '1') zoomTo(1);
    else return;
    e.preventDefault();
  });

  return {
    el: root,
    // Swap the diagram; it is fitted once on the page, and again when its size changes (tables added to a task).
    setContent(node, size) {
      stage.replaceChildren(node);
      const resized = !view.size || view.size.w !== size.w || view.size.h !== size.h;
      view.size = size;
      if (resized) view.fitted = false;
      if (!view.fitted) {
        sizeViewport();
        requestAnimationFrame(() => {
          if (!viewport.isConnected) return;
          sizeViewport();
          fit();
          view.fitted = true;
        });
      }
      apply();
    },
    // Pan just enough to bring a box of the diagram into view (the node the replay is on).
    reveal(box) {
      const r = viewport.getBoundingClientRect();
      if (!r.width || !view.fitted) return;
      const left = view.x + box.x * view.k;
      const top = view.y + box.y * view.k;
      const right = left + box.w * view.k;
      const bottom = top + box.h * view.k;
      let dx = 0;
      let dy = 0;
      if (left < PAD) dx = PAD - left; else if (right > r.width - PAD) dx = r.width - PAD - right;
      if (top < PAD) dy = PAD - top; else if (bottom > r.height - PAD) dy = r.height - PAD - bottom;
      if (!dx && !dy) return;
      view.x += dx;
      view.y += dy;
      stage.classList.add('gliding');
      apply();
      setTimeout(() => stage.classList.remove('gliding'), 260);
    },
  };
}
