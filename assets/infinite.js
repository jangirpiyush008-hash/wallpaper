// Hybrid loader: auto-load on scroll for a few batches, then show "Load More" button.
// Click button -> auto-load a few more batches, then button reappears.
// Lets the footer be reachable instead of endlessly pushed down.
(function () {
  if (!window.__cards) return;
  var BATCH = 30;
  var AUTO_BATCHES = 3; // auto-load this many scroll-triggered batches before stopping
  var rendered = 0;
  var autoCount = 0;
  var grid = document.querySelector('.home-grid');
  if (!grid) return;
  var loader = document.getElementById('infinite-loader');
  var btn = document.getElementById('load-more-btn');

  function escapeHtml(s) {
    return (s || '').replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function renderBatch() {
    var slice = window.__cards.slice(rendered, rendered + BATCH);
    if (slice.length === 0) return false;
    var html = '';
    slice.forEach(function (c) {
      html += '<a class="card" href="article-' + c.s + '.html">' +
        '<img class="card-img" src="' + c.i + '" alt="' + escapeHtml(c.t) + '" loading="lazy">' +
        '<div class="card-title">' + escapeHtml(c.t) + '</div>' +
        '</a>';
    });
    grid.insertAdjacentHTML('beforeend', html);
    rendered += slice.length;
    return true;
  }

  function updateUi() {
    var done = rendered >= window.__cards.length;
    if (done) {
      if (loader) loader.style.display = 'none';
      if (btn) btn.style.display = 'none';
      window.removeEventListener('scroll', onScroll);
      return;
    }
    if (autoCount >= AUTO_BATCHES) {
      // Pause auto-load, show button
      if (loader) loader.style.display = 'none';
      if (btn) btn.style.display = 'inline-block';
    } else {
      if (loader) loader.style.display = 'block';
      if (btn) btn.style.display = 'none';
    }
  }

  function onScroll() {
    if (rendered >= window.__cards.length) return;
    if (autoCount >= AUTO_BATCHES) return; // wait for button click
    var doc = document.documentElement;
    var scrollPos = window.scrollY + window.innerHeight;
    var threshold = doc.scrollHeight - 600;
    if (scrollPos >= threshold) {
      if (renderBatch()) {
        autoCount += 1;
        updateUi();
      }
    }
  }

  if (btn) {
    btn.addEventListener('click', function () {
      autoCount = 0; // reset auto-load window
      renderBatch(); // immediate batch on click
      updateUi();
    });
  }

  // Initial render
  renderBatch();
  updateUi();
  window.addEventListener('scroll', onScroll, { passive: true });
})();
