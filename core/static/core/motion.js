// Motion for the public dashboard: reveal on scroll, count-ups, the half-life map, the live decay
// ticker, and the "revived" moment after an HTMX Mark revised. Every effect has a reduced-motion
// path that jumps straight to the final state.
(function () {
  var still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var ease = function (t) { return 1 - Math.pow(1 - t, 3); };

  function tween(ms, step) {
    if (still) return step(1);
    var t0 = performance.now();
    requestAnimationFrame(function frame(now) {
      var t = Math.min(1, (now - t0) / ms);
      step(ease(t));
      if (t < 1) requestAnimationFrame(frame);
    });
  }

  function countUp(el, from, to, suffix) {
    var dec = +(el.dataset.decimals || 0);
    tween(900, function (k) { el.textContent = (from + (to - from) * k).toFixed(dec) + (suffix || ''); });
  }

  // Half-life map, same geometry as core.dashboard.half_life_map: x in half-lives, y = 0.5 ** n.
  var X = function (n) { return 44 + Math.min(n, 4) * 125; };
  var Y = function (n) { return 210 - Math.pow(0.5, n) * 180; };
  var pins = function () { return document.querySelectorAll('#hlmap .pin'); };

  function place(pin, x, y) {
    pin.setAttribute('transform', 'translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ')');
  }
  function where(pin) {
    var m = /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(pin.getAttribute('transform'));
    return [+m[1], +m[2]];
  }

  // Slide a pin along the curve from n = a to n = b, easing its stack offset from da to db.
  function travel(pin, a, b, da, db, delay) {
    place(pin, X(a), Y(a) + da);
    setTimeout(function () {
      tween(1300, function (k) {
        var n = a + (b - a) * k;
        place(pin, X(n), Y(n) + da + (db - da) * k);
      });
    }, still ? 0 : delay);
  }

  function launch() {
    var i = 0;
    pins().forEach(function (pin) {
      if (pin.dataset.n === '') return;  // flatline pins drop in with CSS
      travel(pin, 0, +pin.dataset.n, 0, +pin.dataset.dy, Math.min(i++, 15) * 70);
    });
  }

  function tooltip(svg) {
    var tip = svg.querySelector('#hl-tip'), box = tip.querySelector('rect'), text = tip.querySelector('text');
    function show(e) {
      var pin = e.target.closest && e.target.closest('.pin');
      if (!pin) return;
      text.textContent = pin.dataset.name + ' · ' + (pin.dataset.n === '' ? 'no proof' : pin.dataset.pct + '%');
      text.setAttribute('x', 8);
      var w = text.getComputedTextLength() + 16, p = where(pin);
      var x = Math.max(2, Math.min(638 - w, p[0] - w / 2)), y = p[1] - 36;
      if (y < 0) y = p[1] + 12;
      box.setAttribute('width', w);
      tip.setAttribute('transform', 'translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ')');
      tip.classList.add('on');
    }
    function hide(e) {
      var pin = e.target.closest && e.target.closest('.pin');
      if (pin && e.relatedTarget && pin.contains(e.relatedTarget)) return;
      tip.classList.remove('on');
    }
    svg.addEventListener('pointerover', show); svg.addEventListener('focusin', show);
    svg.addEventListener('pointerout', hide); svg.addEventListener('focusout', hide);
  }

  // Live ticker: freshness the whole ledger has lost since this page opened. It only runs while
  // the tile is on screen and the tab is visible; the total is from t0, so it catches up on resume.
  function ticker(el) {
    var perDay = +el.dataset.perDay, t0 = Date.now(), onScreen = true, timer = null;
    if (!perDay) return;
    function tick() { el.textContent = '−' + (perDay * (Date.now() - t0) / 864e5).toFixed(6) + ' since you arrived'; }
    function sync() {
      var run = onScreen && !document.hidden;
      if (run && !timer) { tick(); timer = setInterval(tick, still ? 1000 : 120); }
      if (!run && timer) { clearInterval(timer); timer = null; }
    }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) { onScreen = entries[0].isIntersecting; sync(); }).observe(el);
    }
    document.addEventListener('visibilitychange', sync);
    sync();
  }

  // Reveal sections as they scroll in; count-ups and the map launch play on reveal.
  function reveal(el) {
    el.classList.add('in');
    el.querySelectorAll('[data-count]').forEach(function (b) { countUp(b, 0, +b.dataset.count); });
    if (el.querySelector('#hlmap')) launch();
  }
  var io = !still && 'IntersectionObserver' in window && new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { io.unobserve(e.target); reveal(e.target); }
    });
  }, { rootMargin: '0px 0px -10% 0px' });

  var svg = document.getElementById('hlmap');
  if (svg) {
    tooltip(svg);
    // Park pins at the top of the curve so the launch starts from "just revised".
    if (io) pins().forEach(function (pin) { if (pin.dataset.n !== '') place(pin, X(0), Y(0)); });
  }
  var tick = document.getElementById('ticker');
  if (tick) ticker(tick);
  document.querySelectorAll('.reveal').forEach(function (el) { io ? io.observe(el) : reveal(el); });

  // Proof wall: the first few cards show, "Show all" expands to every proof, and the filter and
  // kind chips narrow it. Cards that come into view re-run their pop-in, staggered by --i.
  var list = document.getElementById('proof-list');
  if (list && document.getElementById('proof-tools')) {
    var cards = [].slice.call(list.querySelectorAll('li[data-kind]'));
    var preview = +list.dataset.preview, open = false, kind = '';
    var q = document.getElementById('proof-q'), more = document.getElementById('proof-more');
    var empty = document.getElementById('proof-empty'), chips = document.querySelectorAll('.chip');
    var apply = function () {
      var term = q.value.trim().toLowerCase(), shown = 0, matched = 0;
      cards.forEach(function (li) {
        var match = (!kind || li.dataset.kind === kind) && (!term || li.dataset.text.indexOf(term) > -1);
        var show = match && (open || term || kind || matched < preview);
        if (match) matched++;
        if (show && li.hidden) li.style.setProperty('--i', shown);
        li.hidden = !show;
        if (show) shown++;
      });
      empty.hidden = matched > 0;
      if (more) {
        more.hidden = !!(term || kind) || matched <= preview;
        more.setAttribute('aria-expanded', open);
        more.textContent = open ? 'Show fewer' : 'Show all ' + cards.length;
      }
    };
    document.getElementById('proof-tools').hidden = false;
    q.addEventListener('input', apply);
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        kind = chip.dataset.kind;
        chips.forEach(function (c) { c.setAttribute('aria-pressed', c === chip); });
        apply();
      });
    });
    if (more) more.addEventListener('click', function () { open = !open; apply(); });
    apply();
  }

  // Mark revised: the row's percent counts up, a +N chip floats off, and the skill's pin on the
  // half-life map slides back up the curve to "now". The bar refill is a CSS transition that
  // HTMX's settle step triggers (the bar keeps its id, so it starts at the old width).
  var before = {};
  document.addEventListener('htmx:beforeSwap', function (e) {
    var row = e.detail.target;
    if (row && row.dataset.pct) before[row.id] = +row.dataset.pct;
  });
  document.addEventListener('htmx:afterSettle', function (e) {
    var row = e.target;
    if (!row.id || !(row.id in before)) return;
    var old = before[row.id], now = +row.dataset.pct, gain = now - old;
    delete before[row.id];
    countUp(row.querySelector('.pct'), old, now, '%');
    if (gain > 0 && !still) {
      var chip = document.createElement('span');
      chip.className = 'gain'; chip.textContent = '+' + gain; chip.setAttribute('aria-hidden', 'true');
      chip.addEventListener('animationend', function () { chip.remove(); });
      row.appendChild(chip);
    }
    var pin = document.getElementById('pin-' + row.id.replace('skill-', ''));
    if (!pin) return;
    var flat = pin.dataset.n === '', from = where(pin);
    pin.setAttribute('class', 'pin ' + row.querySelector('.bar i').className);
    pin.setAttribute('aria-label', pin.dataset.name + ': ' + now + '% fresh, revised today');
    if (flat) {
      tween(1100, function (k) { place(pin, from[0] + (X(0) - from[0]) * k, from[1] + (Y(0) - from[1]) * k); });
    } else {
      travel(pin, +pin.dataset.n, 0, +pin.dataset.dy, 0, 0);
    }
    pin.dataset.n = 0; pin.dataset.dy = 0; pin.dataset.pct = now;
  });

  // Reached only if nothing above threw; the inline head script un-hides .reveal otherwise.
  window.motionReady = true;
})();
