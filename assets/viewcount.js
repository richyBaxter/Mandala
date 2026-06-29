/* Standalone page-view counter for pages that don't load macro.js.
   Injects a privacy-respecting hit-counter badge (visitorbadge.io), counted per
   page URL, into a [data-views] element or the page footer. Degrades silently. */
(function () {
  var TMPL = 'https://api.visitorbadge.io/api/visitors?path={PATH}&label=views&labelColor=%230f141d&countColor=%23263247&style=flat-square';
  function add() {
    var host = document.querySelector('[data-views]');
    if (!host) {
      var f = document.querySelector('footer');
      if (!f) return;
      host = document.createElement('div');
      host.setAttribute('data-views', '');
      host.style.marginTop = '12px';
      f.appendChild(host);
    }
    if (host.querySelector('img')) return;
    var img = new Image();
    img.alt = 'page views';
    img.loading = 'lazy';
    img.style.height = '22px';
    img.style.borderRadius = '5px';
    img.style.opacity = '.85';
    img.style.verticalAlign = 'middle';
    img.onerror = function () { host.style.display = 'none'; };
    img.src = TMPL.replace('{PATH}', encodeURIComponent(location.origin + location.pathname));
    host.appendChild(img);
  }
  if (document.readyState !== 'loading') add();
  else document.addEventListener('DOMContentLoaded', add);
})();
