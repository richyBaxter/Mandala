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
  // live token read (re-evaluated each draw so charts follow the active theme)
  const live = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const gridColor = () => live('--grid');
  const tickColor = () => live('--muted');

  // --- analytics config ---------------------------------------------------
  // Visit counter. Two options, both degrade gracefully (the stats slot hides
  // itself if nothing is configured or the service is unreachable):
  //
  // 1) HIT_BADGE (default): a zero-setup hit-counter badge image, counted by
  //    page URL. {PATH} is replaced with the encoded page URL. No account.
  // 2) GOATCOUNTER: set to "https://YOURCODE.goatcounter.com/count" to instead
  //    show styled per-page / site-wide count pills and load privacy-friendly
  //    (cookieless) pageview tracking. Takes precedence over HIT_BADGE.
  const GOATCOUNTER = '';
  const HIT_BADGE = 'https://api.visitorbadge.io/api/visitors?path={PATH}&label=views&labelColor=%230f141d&countColor=%23263247&style=flat-square';

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
    Chart.defaults.color = tickColor();
    Chart.defaults.plugins.legend.display = false;
    // horizontal dashed threshold lines; l.tok = live token name, l.color = fixed colour
    Chart.register({
      id: 'thresholds',
      afterDatasetsDraw(chart) {
        const lines = (chart.options.plugins.thresholds || {}).lines || [];
        const { ctx, chartArea, scales } = chart; const y = scales.y; if (!y) return;
        lines.forEach(l => {
          const col = l.tok ? live(l.tok) : (l.color || live('--faint'));
          const yy = y.getPixelForValue(l.value); if (yy < chartArea.top || yy > chartArea.bottom) return;
          ctx.save(); ctx.beginPath(); ctx.setLineDash([5, 5]); ctx.lineWidth = 1;
          ctx.strokeStyle = col; ctx.moveTo(chartArea.left, yy); ctx.lineTo(chartArea.right, yy); ctx.stroke();
          if (l.label) { ctx.setLineDash([]); ctx.font = '600 11px Inter'; ctx.fillStyle = col; ctx.textAlign = 'right'; ctx.fillText(l.label, chartArea.right - 6, yy - 5); }
          ctx.restore();
        });
      }
    });
  }

  // re-theme every live chart after a theme switch
  function retheme() {
    if (!window.Chart) return;
    Chart.defaults.color = tickColor();
    Object.values(Chart.instances || {}).forEach(c => { try { c.update('none'); } catch (e) {} });
  }

  function baseLine(extra) {
    extra = extra || {};
    const base = {
      responsive: true, maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: { tooltip: { backgroundColor: () => live('--panel'), borderColor: () => live('--border'), borderWidth: 1, padding: 10, titleColor: () => live('--ink'), bodyColor: () => live('--ink') } },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: tickColor, maxRotation: 0, autoSkipPadding: 16 } },
        y: { grid: { color: gridColor }, ticks: { color: tickColor } }
      }
    };
    const out = Object.assign({}, base, extra);
    out.plugins = Object.assign({}, base.plugins, extra.plugins);
    out.plugins.tooltip = Object.assign({}, base.plugins.tooltip, extra.plugins && extra.plugins.tooltip);
    out.scales = Object.assign({}, base.scales, extra.scales);
    return out;
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

  // ---------- share bar ----------
  // Renders into any <div class="share" data-share>. Reads title/url from the
  // page (override with data-title / data-url on the element).
  const ICONS = {
    x: '<svg viewBox="0 0 24 24"><path d="M18.244 2H21.5l-7.5 8.57L22.5 22h-6.59l-5.16-6.74L4.8 22H1.54l8.02-9.17L1.5 2h6.75l4.67 6.17L18.244 2Zm-1.16 18h1.83L7.01 3.9H5.05L17.084 20Z"/></svg>',
    linkedin: '<svg viewBox="0 0 24 24"><path d="M4.98 3.5A2.5 2.5 0 1 0 5 8.5a2.5 2.5 0 0 0-.02-5ZM3 9h4v12H3V9Zm6 0h3.8v1.7h.05c.53-1 1.83-2.05 3.77-2.05 4.03 0 4.78 2.65 4.78 6.1V21h-4v-5.4c0-1.29-.02-2.95-1.8-2.95-1.8 0-2.08 1.4-2.08 2.85V21H9V9Z"/></svg>',
    reddit: '<svg viewBox="0 0 24 24"><path d="M22 12a2.06 2.06 0 0 0-3.5-1.45 10.2 10.2 0 0 0-5.27-1.67l.9-4.24 2.95.63a1.5 1.5 0 1 0 .16-.98l-3.3-.7a.5.5 0 0 0-.59.38l-1 4.7a10.2 10.2 0 0 0-5.34 1.66 2.06 2.06 0 1 0-2.27 3.4 4 4 0 0 0-.05.62c0 3.14 3.66 5.69 8.18 5.69s8.18-2.55 8.18-5.69a4 4 0 0 0-.05-.62A2.06 2.06 0 0 0 22 12ZM8.5 13.5a1.25 1.25 0 1 1 1.25 1.25A1.25 1.25 0 0 1 8.5 13.5Zm6.93 3.64a4.6 4.6 0 0 1-2.93.86 4.6 4.6 0 0 1-2.93-.86.4.4 0 0 1 .5-.62 3.9 3.9 0 0 0 2.43.66 3.9 3.9 0 0 0 2.43-.66.4.4 0 1 1 .5.62Zm-.18-2.39a1.25 1.25 0 1 1 1.25-1.25 1.25 1.25 0 0 1-1.25 1.25Z"/></svg>',
    facebook: '<svg viewBox="0 0 24 24"><path d="M22 12a10 10 0 1 0-11.56 9.88v-6.99H7.9V12h2.54V9.8c0-2.5 1.49-3.89 3.78-3.89 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56V12h2.78l-.44 2.89h-2.34v6.99A10 10 0 0 0 22 12Z"/></svg>',
    link: '<svg viewBox="0 0 24 24"><path d="M10.59 13.41a1 1 0 0 0 1.42 0l4-4a3 3 0 1 0-4.24-4.24l-1.3 1.3a1 1 0 1 0 1.42 1.41l1.3-1.29a1 1 0 1 1 1.41 1.41l-4 4a1 1 0 0 0 0 1.42Zm2.82-2.82a1 1 0 0 0-1.42 0l-4 4a3 3 0 1 0 4.24 4.24l1.3-1.3a1 1 0 0 0-1.42-1.41l-1.3 1.29a1 1 0 1 1-1.41-1.41l4-4a1 1 0 0 0 0-1.42Z"/></svg>',
    share: '<svg viewBox="0 0 24 24"><path d="M18 16a3 3 0 0 0-2.4 1.2l-6.7-3.9a3 3 0 0 0 0-2.6l6.7-3.9a3 3 0 1 0-.9-1.6L7.9 9.1a3 3 0 1 0 0 5.8l6.8 3.9A3 3 0 1 0 18 16Z"/></svg>'
  };
  function renderShare(el) {
    const url = el.getAttribute('data-url') || location.href;
    const title = el.getAttribute('data-title') || document.title;
    const u = encodeURIComponent(url), t = encodeURIComponent(title);
    const open = href => window.open(href, '_blank', 'noopener,width=600,height=520');
    const targets = [
      ['x', `https://twitter.com/intent/tweet?text=${t}&url=${u}`, 'Share on X'],
      ['linkedin', `https://www.linkedin.com/sharing/share-offsite/?url=${u}`, 'Share on LinkedIn'],
      ['reddit', `https://www.reddit.com/submit?url=${u}&title=${t}`, 'Share on Reddit'],
      ['facebook', `https://www.facebook.com/sharer/sharer.php?u=${u}`, 'Share on Facebook']
    ];
    el.innerHTML = '<span class="lbl">Share</span>';
    targets.forEach(([k, href, label]) => {
      const b = document.createElement('button'); b.title = label; b.setAttribute('aria-label', label);
      b.innerHTML = ICONS[k]; b.onclick = () => open(href); el.appendChild(b);
    });
    if (navigator.share) {
      const b = document.createElement('button'); b.title = 'Share…'; b.setAttribute('aria-label', 'Share');
      b.innerHTML = ICONS.share; b.onclick = () => navigator.share({ title, url }).catch(() => {}); el.appendChild(b);
    }
    const cp = document.createElement('button'); cp.title = 'Copy link'; cp.setAttribute('aria-label', 'Copy link');
    cp.innerHTML = ICONS.link;
    const note = document.createElement('span'); note.className = 'copied'; note.textContent = 'Copied';
    cp.onclick = () => navigator.clipboard?.writeText(url).then(() => { note.classList.add('show'); setTimeout(() => note.classList.remove('show'), 1600); });
    el.appendChild(cp); el.appendChild(note);
  }

  // ---------- page stats (GoatCounter visitor counts) ----------
  function injectGoatCounter() {
    if (!GOATCOUNTER) return;
    const s = document.createElement('script');
    s.async = true; s.src = '//gc.zgo.at/count.js';
    s.setAttribute('data-goatcounter', GOATCOUNTER);
    document.body.appendChild(s);
  }
  async function renderStats() {
    const nodes = document.querySelectorAll('[data-views]');
    if (!nodes.length) return;
    // Option 2: GoatCounter styled count pills (takes precedence).
    if (GOATCOUNTER) {
      const base = GOATCOUNTER.replace(/\/count$/, '');
      const get = async path => { try { const r = await fetch(`${base}/counter/${encodeURIComponent(path)}.json`); return (await r.json()).count; } catch (e) { return null; } };
      const total = await get('TOTAL');
      const page = await get(location.pathname);
      nodes.forEach(n => {
        if (total == null && page == null) { n.style.display = 'none'; return; }
        n.innerHTML = '';
        const pill = (label, val) => { const p = document.createElement('span'); p.className = 'pill'; p.innerHTML = `<span class="dot"></span><b>${val}</b> ${label}`; return p; };
        if (page != null) n.appendChild(pill('views this page', page));
        if (total != null) n.appendChild(pill('views across the site', total));
      });
      return;
    }
    // Option 1: zero-setup hit-counter badge image (counts by page URL).
    if (!HIT_BADGE) { nodes.forEach(n => { n.style.display = 'none'; }); return; }
    const path = encodeURIComponent(location.origin + location.pathname);
    nodes.forEach(n => {
      n.innerHTML = '';
      const img = document.createElement('img');
      img.className = 'hitbadge'; img.alt = 'page views'; img.loading = 'lazy';
      img.src = HIT_BADGE.replace('{PATH}', path);
      img.onerror = () => { n.style.display = 'none'; };
      n.appendChild(img);
    });
  }

  // ---------- light / dark ----------
  const SUN = '<svg viewBox="0 0 24 24"><path d="M12 17a5 5 0 1 1 0-10 5 5 0 0 1 0 10Zm0-13a1 1 0 0 1-1-1V1a1 1 0 1 1 2 0v2a1 1 0 0 1-1 1Zm0 19a1 1 0 0 1-1-1v-2a1 1 0 1 1 2 0v2a1 1 0 0 1-1 1ZM4.2 5.6 2.8 4.2a1 1 0 1 1 1.4-1.4l1.4 1.4A1 1 0 0 1 4.2 5.6Zm15.6 15.6-1.4-1.4a1 1 0 0 1 1.4-1.4l1.4 1.4a1 1 0 0 1-1.4 1.4ZM1 13a1 1 0 1 1 0-2h2a1 1 0 1 1 0 2H1Zm20 0a1 1 0 1 1 0-2h2a1 1 0 1 1 0 2h-2ZM4.2 18.4a1 1 0 0 1 1.4 1.4l-1.4 1.4a1 1 0 1 1-1.4-1.4l1.4-1.4ZM18.4 19.8a1 1 0 0 1 1.4-1.4l1.4 1.4a1 1 0 0 1-1.4 1.4l-1.4-1.4Z"/></svg>';
  const MOON = '<svg viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>';
  const curTheme = () => document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
  let themeBtn = null;
  function setTheme(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('mandala-theme', t); } catch (e) {}
    if (themeBtn) themeBtn.innerHTML = t === 'light' ? MOON : SUN;
    retheme();
  }
  function initTheme() {
    if (!document.documentElement.dataset.theme) {
      let t = 'dark';
      try { t = localStorage.getItem('mandala-theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'); } catch (e) {}
      document.documentElement.dataset.theme = t;
    }
    themeBtn = document.createElement('button');
    themeBtn.className = 'theme-toggle'; themeBtn.id = 'theme-toggle';
    themeBtn.setAttribute('aria-label', 'Toggle light or dark mode');
    themeBtn.innerHTML = curTheme() === 'light' ? MOON : SUN;
    themeBtn.addEventListener('click', () => setTheme(curTheme() === 'light' ? 'dark' : 'light'));
    document.body.appendChild(themeBtn);
  }

  window.Macro = { T, SERIES, live, gridColor, tickColor, hexA, vGrad, registerChartDefaults, baseLine, retheme, loadJSON, setText, fillNarratives, wireProgress, observeReveals, renderShare, renderStats, setTheme, curTheme };

  // auto-init the cheap scaffolding for any page that includes this file
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    wireProgress();
    observeReveals(null);
    document.querySelectorAll('.share[data-share]').forEach(renderShare);
    injectGoatCounter();
    renderStats();
  });
})();
