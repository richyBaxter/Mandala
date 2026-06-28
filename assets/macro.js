/* houtini · Mandala — shared macro story helpers.
   Exposes window.Macro with Chart.js helpers + scroll scaffolding so each
   data story is a thin file. Chart.js itself is loaded per-story (only story
   pages need it); the hub uses just the scroll/progress helpers. */
(function () {
  "use strict";
  const C = getComputedStyle(document.documentElement);
  const tok = n => C.getPropertyValue(n).trim();
  const T = {};
  ['--ink','--muted','--faint','--border','--btc','--buy','--fair','--sell','--sky','--violet','--pink','--danger']
    .forEach(k => { T[k.slice(2)] = tok(k); });
  // categorical series palette for multi-line / doughnut charts
  const SERIES = [T.sky, T.btc, T.buy, T.violet, T.fair, T.pink, T.sell];

  function hexA(hex, a) {
    const h = hex.replace('#', '');
    const n = parseInt(h.length === 3 ? h.split('').map(c => c + c).join('') : h, 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }
  // vertical gradient fill for area charts (pass the chart from a scriptable ctx)
  function vGrad(chart, color, a1) {
    const { ctx, chartArea } = chart;
    if (!chartArea) return hexA(color, a1 || .25);
    const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    g.addColorStop(0, hexA(color, a1 || .28)); g.addColorStop(1, hexA(color, 0));
    return g;
  }

  function registerChartDefaults() {
    if (!window.Chart || window.__macroChartReady) return;
    window.__macroChartReady = true;
    Chart.defaults.font.family = 'Inter, sans-serif';
    Chart.defaults.color = T.muted;
    Chart.defaults.plugins.legend.display = false;
    // horizontal dashed threshold lines via options.plugins.thresholds.lines
    Chart.register({
      id: 'thresholds',
      afterDatasetsDraw(chart) {
        const lines = (chart.options.plugins.thresholds || {}).lines || [];
        const { ctx, chartArea, scales } = chart; const y = scales.y; if (!y) return;
        lines.forEach(l => {
          const yy = y.getPixelForValue(l.value); if (yy < chartArea.top || yy > chartArea.bottom) return;
          ctx.save(); ctx.beginPath(); ctx.setLineDash([5, 5]); ctx.lineWidth = 1;
          ctx.strokeStyle = l.color || T.faint; ctx.moveTo(chartArea.left, yy); ctx.lineTo(chartArea.right, yy); ctx.stroke();
          if (l.label) { ctx.setLineDash([]); ctx.font = '600 11px Inter'; ctx.fillStyle = l.color || T.muted; ctx.textAlign = 'right'; ctx.fillText(l.label, chartArea.right - 6, yy - 5); }
          ctx.restore();
        });
      }
    });
  }

  function baseLine(extra) {
    return Object.assign({
      responsive: true, maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: { tooltip: { backgroundColor: '#0f141d', borderColor: T.border, borderWidth: 1, padding: 10 } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,.04)' }, ticks: { maxRotation: 0, autoSkipPadding: 16 } },
        y: { grid: { color: 'rgba(255,255,255,.05)' } }
      }
    }, extra || {});
  }

  async function loadJSON(path) { try { return await (await fetch(path)).json(); } catch (e) { return null; } }
  function setText(id, v) { const el = document.getElementById(id); if (el && v != null) el.textContent = v; }

  // Fill .ai blocks from a narrative.json {source, notes:{key:text}} object.
  function fillNarratives(narr) {
    if (!narr || !narr.notes) return;
    document.querySelectorAll('.ai[data-note]').forEach(block => {
      const txt = narr.notes[block.getAttribute('data-note')];
      if (txt) block.querySelector('p').textContent = txt;
      const src = block.querySelector('.src');
      if (src) src.textContent = narr.source === 'github-models' ? 'live · GitHub Models' : 'computed';
    });
  }

  // progress bar (needs <div class="progress" id="progress">)
  function wireProgress() {
    const prog = document.getElementById('progress'); if (!prog) return;
    const on = () => { const h = document.documentElement; const sc = h.scrollTop / (h.scrollHeight - h.clientHeight || 1); prog.style.width = (sc * 100) + '%'; };
    window.addEventListener('scroll', on, { passive: true }); on();
  }

  // reveal-on-scroll; calls render[id]() once when a .chapter/.reveal enters view
  function observeReveals(render) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        e.target.classList.add('in');
        const fn = render && render[e.target.id];
        if (fn) try { fn(); } catch (err) { console.warn('render', e.target.id, err); }
      });
    }, { threshold: .12 });
    document.querySelectorAll('.reveal, .chapter').forEach(s => io.observe(s));
  }

  window.Macro = { T, SERIES, hexA, vGrad, registerChartDefaults, baseLine, loadJSON, setText, fillNarratives, wireProgress, observeReveals };

  // auto-init the cheap scaffolding for any page that includes this file
  document.addEventListener('DOMContentLoaded', () => { wireProgress(); observeReveals(null); });
})();
