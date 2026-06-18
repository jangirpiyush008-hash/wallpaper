// Infinite scroll loader for homepage + category pages.
// Reads a JSON manifest (`window.__cards`) of all card data and appends 30 at a time as user scrolls.
(function () {
  if (!window.__cards) return;
  var BATCH = 30;
  var rendered = 0;
  var grid = document.querySelector('.home-grid');
  if (!grid) return;
  var loader = document.getElementById('infinite-loader');

  function escapeHtml(s) {
    return (s || '').replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function renderBatch() {
    var slice = window.__cards.slice(rendered, rendered + BATCH);
    if (slice.length === 0) {
      if (loader) loader.style.display = 'none';
      window.removeEventListener('scroll', onScroll);
      return;
    }
    var html = '';
    slice.forEach(function (c) {
      html += '<a class="card" href="article-' + c.s + '.html">' +
        '<img class="card-img" src="' + c.i + '" alt="' + escapeHtml(c.t) + '" loading="lazy">' +
        '<div class="card-title">' + escapeHtml(c.t) + '</div>' +
        '</a>';
    });
    grid.insertAdjacentHTML('beforeend', html);
    rendered += slice.length;
    if (rendered >= window.__cards.length) {
      if (loader) loader.style.display = 'none';
      window.removeEventListener('scroll', onScroll);
    }
  }

  function onScroll() {
    if (rendered >= window.__cards.length) return;
    var doc = document.documentElement;
    var scrollPos = window.scrollY + window.innerHeight;
    var threshold = doc.scrollHeight - 800;
    if (scrollPos >= threshold) renderBatch();
  }

  // Initial render
  renderBatch();
  window.addEventListener('scroll', onScroll, { passive: true });
})();
