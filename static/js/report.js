/* ==========================================================================
   The Creator Report — Analytics & UI
   ========================================================================== */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // UTM extraction
  // ---------------------------------------------------------------------------
  function getUTM() {
    const params = new URLSearchParams(window.location.search);
    return {
      utm_source: params.get('utm_source') || '',
      utm_medium: params.get('utm_medium') || '',
      utm_campaign: params.get('utm_campaign') || '',
    };
  }

  // ---------------------------------------------------------------------------
  // Track event
  // ---------------------------------------------------------------------------
  function track(event, extra) {
    const data = Object.assign({
      event: event,
      slug: getSlug(),
      category: getCategory(),
      referrer: document.referrer || '',
    }, getUTM(), extra || {});

    fetch('/api/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).catch(function () { /* silent fail */ });
  }

  function getSlug() {
    var el = document.querySelector('[data-slug]');
    return el ? el.getAttribute('data-slug') : window.location.pathname;
  }

  function getCategory() {
    var el = document.querySelector('[data-category]');
    return el ? el.getAttribute('data-category') : '';
  }

  // ---------------------------------------------------------------------------
  // Pageview
  // ---------------------------------------------------------------------------
  track('pageview');

  // ---------------------------------------------------------------------------
  // Scroll depth tracking
  // ---------------------------------------------------------------------------
  var scrollMarkers = { 25: false, 50: false, 75: false, 100: false };

  function checkScroll() {
    var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    var docHeight = document.documentElement.scrollHeight - window.innerHeight;
    if (docHeight <= 0) return;
    var pct = Math.round((scrollTop / docHeight) * 100);

    [25, 50, 75, 100].forEach(function (marker) {
      if (pct >= marker && !scrollMarkers[marker]) {
        scrollMarkers[marker] = true;
        track('scroll_depth', { value: String(marker) });
      }
    });
  }

  var scrollTimer;
  window.addEventListener('scroll', function () {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(checkScroll, 200);
  }, { passive: true });

  // ---------------------------------------------------------------------------
  // Reading progress bar
  // ---------------------------------------------------------------------------
  var progressBar = document.getElementById('readingProgress');
  if (progressBar) {
    window.addEventListener('scroll', function () {
      var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      var docHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (docHeight <= 0) return;
      var pct = Math.min((scrollTop / docHeight) * 100, 100);
      progressBar.style.width = pct + '%';
    }, { passive: true });
  }

  // ---------------------------------------------------------------------------
  // CTA click tracking
  // ---------------------------------------------------------------------------
  document.addEventListener('click', function (e) {
    var cta = e.target.closest('.vault-cta-btn, .btn-vault, .nav-cta');
    if (cta) {
      var placement = cta.getAttribute('data-cta') || 'unknown';
      track('cta_click', { value: placement });
    }
  });

  // ---------------------------------------------------------------------------
  // Time on page
  // ---------------------------------------------------------------------------
  var pageStart = Date.now();

  window.addEventListener('beforeunload', function () {
    var seconds = Math.round((Date.now() - pageStart) / 1000);
    // Use sendBeacon for reliability
    var data = JSON.stringify({
      event: 'time_on_page',
      slug: getSlug(),
      category: getCategory(),
      value: String(seconds),
      referrer: document.referrer || '',
    });
    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/track', new Blob([data], { type: 'application/json' }));
    }
  });

})();
