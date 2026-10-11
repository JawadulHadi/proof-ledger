// Interactive freshness curve: freshness = exp(-ln2 * days / halfLife), the same formula as Skill.freshness().
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var curve = $('curve');
  if (!curve) return;
  var fr = function (d, h) { return Math.exp(-Math.LN2 * d / h); };
  var X = function (d) { return 40 + d * 3; }, Y = function (f) { return 210 - f * 180; };
  var tier = function (f) { return f >= 0.6 ? 'fresh' : f >= 0.3 ? 'fading' : 'stale'; };
  var color = { fresh: '--fresh', fading: '--warn', stale: '--stale' };
  var day = $('day'), half = $('half');
  function draw() {
    var d = +day.value, h = +half.value, f = fr(d, h), t = tier(f), p = '';
    for (var i = 0; i <= 180; i += 3) p += (i ? 'L' : 'M') + X(i) + ' ' + Y(fr(i, h)).toFixed(1) + ' ';
    curve.setAttribute('d', p);
    $('area').setAttribute('d', p + 'L580 210 L40 210 Z');
    $('dot').setAttribute('cx', X(d)); $('dot').setAttribute('cy', Y(f));
    $('dot').style.fill = 'var(' + color[t] + ')';
    var drop = $('drop');
    drop.setAttribute('x1', X(d)); drop.setAttribute('x2', X(d)); drop.setAttribute('y1', Y(f));
    $('dayOut').textContent = d; $('halfOut').textContent = h;
    $('readout').textContent = 'After ' + d + ' days with a ' + h + '-day half-life, freshness is ' +
      Math.round(f * 100) + '% (' + t + ').';
  }
  day.addEventListener('input', draw);
  half.addEventListener('input', draw);
  draw();
})();
