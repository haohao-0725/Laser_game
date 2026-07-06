// 手機版 Canvas 遊戲：渲染、觸控、雷射動畫、上一手高亮、hotseat / 對 AI。
(function () {
  var E = window.KhetEngine, AI = window.KhetAI;
  var canvas = document.getElementById('board');
  var ctx = canvas.getContext('2d');
  var statusEl = document.getElementById('status');

  var PIECE_FILES = {
    'PHARAOH_SILVER': 'silver_king.png', 'PHARAOH_RED': 'red_king.png',
    'SPHINX_SILVER': 'silver_emitter.png', 'SPHINX_RED': 'red_emitter.png',
    'PYRAMID_SILVER': 'silver_mirror.png', 'PYRAMID_RED': 'red_mirror.png',
    'SCARAB_SILVER': 'silver_twinmirror.png', 'SCARAB_RED': 'red_twinmirror.png',
    'ANUBIS_SILVER': 'silver_shield.png', 'ANUBIS_RED': 'red_shield.png'
  };
  var images = {};
  function loadImages(cb) {
    var names = Object.keys(PIECE_FILES).map(function (k) { return PIECE_FILES[k]; });
    ['board_bg.png', 'tile_red_only.png', 'tile_silver_only.png', 'tile_normal.png',
      'laser_hit.png', 'laser_reflect.png', 'laser_muzzle.png'].forEach(function (n) { names.push(n); });
    var left = names.length;
    if (!left) return cb();
    names.forEach(function (n) {
      var img = new Image();
      img.onload = img.onerror = function () { left--; if (left === 0) cb(); };
      img.src = 'assets/' + n;
      images[n] = img;
    });
  }
  function img(name) { var i = images[name]; return (i && i.complete && i.naturalWidth) ? i : null; }

  // ---- 遊戲狀態 ----
  var COLOR_NAMES = { SILVER: '銀方', RED: '紅方' };
  var AI_NAMES = { easy: '簡單', medium: '中等', hard: '困難' };
  var state, history, aiDifficulty = null, aiColor = 'RED';
  var selected = null, targets = [], lastMove = [], pulse = 0;
  var anim = null, animTimer = null, pulseTimer = null, locked = false;

  function newGame(layout) {
    state = E.initialState(layout || currentLayout);
    currentLayout = layout || currentLayout;
    history = [state];
    selected = null; targets = []; lastMove = []; pulse = 0; locked = false;
    stopTimers();
    render(); updateStatus();
  }
  var currentLayout = 'classic';

  function stopTimers() {
    if (animTimer) { clearInterval(animTimer); animTimer = null; }
    if (pulseTimer) { clearInterval(pulseTimer); pulseTimer = null; }
    anim = null;
  }

  // ---- 幾何 ----
  function geom() {
    var W = canvas.width, H = canvas.height, m = 6;
    var cs = Math.min((W - 2 * m) / 10, (H - 2 * m) / 8);
    return { ox: (W - cs * 10) / 2, oy: (H - cs * 8) / 2, cs: cs };
  }
  function cellRect(c, r) { var g = geom(); return { x: g.ox + c * g.cs, y: g.oy + r * g.cs, s: g.cs }; }
  function cellAt(px, py) {
    var g = geom();
    var c = Math.floor((px - g.ox) / g.cs), r = Math.floor((py - g.oy) / g.cs);
    if (c >= 0 && c < 10 && r >= 0 && r < 8 && px >= g.ox && py >= g.oy) return [c, r];
    return null;
  }

  // ---- 渲染 ----
  function render() {
    if (!state) return;
    var W = canvas.width, H = canvas.height, g = geom();
    ctx.fillStyle = '#10141c'; ctx.fillRect(0, 0, W, H);
    var bg = img('board_bg.png');
    if (bg) ctx.drawImage(bg, g.ox, g.oy, g.cs * 10, g.cs * 8);

    for (var c = 0; c < 10; c++) for (var r = 0; r < 8; r++) {
      var rect = cellRect(c, r), key = E.cellKey(c, r);
      if (E.RESTRICTED.RED.has(key)) drawTile(rect, 'tile_red_only.png', 'rgba(255,70,40,0.18)', 'rgba(255,100,60,0.45)');
      else if (E.RESTRICTED.SILVER.has(key)) drawTile(rect, 'tile_silver_only.png', 'rgba(0,210,255,0.14)', 'rgba(0,220,255,0.4)');
    }
    ctx.strokeStyle = 'rgba(56,66,86,0.9)'; ctx.lineWidth = 1;
    for (var i = 0; i <= 10; i++) line(g.ox + i * g.cs, g.oy, g.ox + i * g.cs, g.oy + 8 * g.cs);
    for (var j = 0; j <= 8; j++) line(g.ox, g.oy + j * g.cs, g.ox + 10 * g.cs, g.oy + j * g.cs);

    drawLastMove();
    drawPieces();
    drawSelection();
    drawTargets();
    if (anim) drawBeam();
  }
  function line(x1, y1, x2, y2) { ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); }
  function drawTile(rect, name, fill, border) {
    var im = img(name);
    if (im) { ctx.drawImage(im, rect.x, rect.y, rect.s, rect.s); return; }
    ctx.fillStyle = fill; ctx.fillRect(rect.x + 2, rect.y + 2, rect.s - 4, rect.s - 4);
    ctx.strokeStyle = border; ctx.lineWidth = 2; ctx.strokeRect(rect.x + 2, rect.y + 2, rect.s - 4, rect.s - 4);
  }

  function piecesToDraw() {
    if (anim && anim.hit && anim.progress >= anim.path.length && anim.explosion < 6)
      return state.pieces.concat([anim.hit]);
    return state.pieces;
  }
  function drawPieces() {
    piecesToDraw().forEach(function (p) {
      var rect = cellRect(p[2], p[3]), im = img(PIECE_FILES[p[0] + '_' + p[1]]);
      ctx.save();
      ctx.translate(rect.x + rect.s / 2, rect.y + rect.s / 2);
      ctx.rotate(p[4] * Math.PI / 2);
      var sz = rect.s * 0.92;
      if (im) ctx.drawImage(im, -sz / 2, -sz / 2, sz, sz);
      else { ctx.fillStyle = p[1] === 'SILVER' ? '#e1e4eb' : '#961e19'; ctx.fillRect(-sz / 2, -sz / 2, sz, sz); }
      ctx.restore();
    });
  }
  function drawSelection() {
    if (!selected) return;
    var rect = cellRect(selected[0], selected[1]);
    ctx.strokeStyle = '#ffe650'; ctx.lineWidth = 3;
    ctx.strokeRect(rect.x + 2, rect.y + 2, rect.s - 4, rect.s - 4);
  }
  function drawTargets() {
    targets.forEach(function (t) {
      var rect = cellRect(t.c, t.r);
      ctx.beginPath();
      ctx.arc(rect.x + rect.s / 2, rect.y + rect.s / 2, rect.s * 0.3, 0, 2 * Math.PI);
      ctx.fillStyle = t.kind === 'swap' ? 'rgba(160,120,255,0.45)' : 'rgba(90,255,140,0.4)';
      ctx.fill();
      ctx.strokeStyle = t.kind === 'swap' ? '#a078ff' : '#5aff8c'; ctx.lineWidth = 2; ctx.stroke();
    });
  }
  function drawLastMove() {
    if (!lastMove.length) return;
    var a = 0.13 + 0.35 * pulse, b = 0.6 + 0.4 * pulse, w = 2.5 + 4 * pulse;
    lastMove.forEach(function (cell) {
      var rect = cellRect(cell[0], cell[1]);
      ctx.fillStyle = 'rgba(120,245,255,' + a + ')';
      ctx.fillRect(rect.x + 2, rect.y + 2, rect.s - 4, rect.s - 4);
      ctx.strokeStyle = 'rgba(120,245,255,' + b + ')'; ctx.lineWidth = w;
      ctx.strokeRect(rect.x + 2, rect.y + 2, rect.s - 4, rect.s - 4);
    });
  }
  function drawBeam() {
    var g = geom(), pts = anim.path.slice(0, anim.progress).map(function (c) {
      var rc = cellRect(c[0], c[1]); return [rc.x + rc.s / 2, rc.y + rc.s / 2];
    });
    if (pts.length >= 2) {
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.strokeStyle = 'rgba(255,110,40,0.5)'; ctx.lineWidth = g.cs * 0.3;
      poly(pts);
      ctx.strokeStyle = 'rgba(255,235,190,0.95)'; ctx.lineWidth = g.cs * 0.09;
      poly(pts);
    }
    if (anim.event === 'hit' && anim.progress >= anim.path.length && anim.explosion > 0) {
      var last = anim.path[anim.path.length - 1], rc = cellRect(last[0], last[1]);
      var scale = 0.5 + 0.7 * (anim.explosion / 6), im = img('laser_hit.png');
      var cx = rc.x + rc.s / 2, cy = rc.y + rc.s / 2, s = rc.s * scale;
      if (im) ctx.drawImage(im, cx - s / 2, cy - s / 2, s, s);
      else { ctx.fillStyle = 'rgba(255,200,80,0.8)'; ctx.beginPath(); ctx.arc(cx, cy, s * 0.4, 0, 2 * Math.PI); ctx.fill(); }
    }
  }
  function poly(pts) { ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]); ctx.stroke(); }

  // ---- 互動 ----
  function actionCells(a) {
    var cells = [[a.col, a.row]];
    if (a.kind === 'move' || a.kind === 'swap') cells.push([a.col + a.dcol, a.row + a.drow]);
    return cells;
  }
  function selectPiece(c, r) {
    selected = [c, r]; targets = [];
    E.legalActions(state).forEach(function (a) {
      if (a.col === c && a.row === r && (a.kind === 'move' || a.kind === 'swap'))
        targets.push({ c: c + a.dcol, r: r + a.drow, kind: a.kind, action: a });
    });
    updateRotateButtons();
    render();
  }
  function updateRotateButtons() {
    var cw = document.getElementById('btn-cw'), ccw = document.getElementById('btn-ccw');
    var acts = selected ? E.legalActions(state).filter(function (a) {
      return a.kind === 'rotate' && a.col === selected[0] && a.row === selected[1];
    }) : [];
    var hasCW = acts.some(function (a) { return a.cw; });
    var hasCCW = acts.some(function (a) { return !a.cw; });
    cw.disabled = !hasCW; ccw.disabled = !hasCCW;
    cw._action = acts.find(function (a) { return a.cw; });
    ccw._action = acts.find(function (a) { return !a.cw; });
  }

  function onTap(px, py) {
    if (locked || anim || E.winner(state) !== null) return;
    var cell = cellAt(px, py);
    if (!cell) { selected = null; targets = []; updateRotateButtons(); render(); return; }
    // 點到行動目標 → 執行
    for (var i = 0; i < targets.length; i++) {
      if (targets[i].c === cell[0] && targets[i].r === cell[1]) { commit(targets[i].action, false); return; }
    }
    var occ = E.boardMap(state.pieces), p = occ[E.cellKey(cell[0], cell[1])];
    if (p && p[1] === state.player) selectPiece(cell[0], cell[1]);
    else { selected = null; targets = []; updateRotateButtons(); render(); }
  }

  function commit(action, pulseAfter) {
    var res = E.applyAction(state, action);
    state = res.state; history.push(state);
    selected = null; targets = []; updateRotateButtons();
    lastMove = actionCells(action); pulse = 0;
    anim = { path: res.path, event: res.event, hit: res.hit, progress: 1, explosion: 0, pulseAfter: pulseAfter };
    if (animTimer) clearInterval(animTimer);
    animTimer = setInterval(animTick, 35);
    render();
  }
  function animTick() {
    if (anim.progress < anim.path.length) anim.progress++;
    else if (anim.event === 'hit' && anim.explosion < 6) anim.explosion++;
    else {
      clearInterval(animTimer); animTimer = null;
      var pulseAfter = anim.pulseAfter; anim = null;
      if (pulseAfter) startPulse();
      render(); afterTurn(); return;
    }
    render();
  }
  function startPulse() {
    pulse = 1.0;
    var hold = 15;                 // 先維持全亮 ~0.6 秒，再淡出 ~2.0 秒（總長 ~2.6 秒）
    if (pulseTimer) clearInterval(pulseTimer);
    pulseTimer = setInterval(function () {
      if (hold > 0) { hold--; }
      else { pulse -= 0.02; if (pulse <= 0) { pulse = 0; clearInterval(pulseTimer); pulseTimer = null; } }
      render();
    }, 40);
  }

  function afterTurn() {
    updateStatus();
    var w = E.winner(state);
    if (w !== null) {
      var msg = aiDifficulty ? (w !== aiColor ? '你獲勝了！' : 'AI（' + AI_NAMES[aiDifficulty] + '）獲勝！')
        : (COLOR_NAMES[w] + ' 獲勝！');
      setTimeout(function () { if (confirm(msg + '\n\n再來一局？')) newGame(currentLayout); }, 100);
      return;
    }
    maybeStartAI();
  }
  function maybeStartAI() {
    if (aiDifficulty && state.player === aiColor && E.winner(state) === null) {
      locked = true; statusEl.textContent = 'AI（' + AI_NAMES[aiDifficulty] + '）思考中…';
      setTimeout(function () {
        var action = AI.chooseAction(state, aiDifficulty);
        locked = false; commit(action, true);
      }, 30);
    }
  }

  function undo() {
    if (locked || anim) return;
    var steps = aiDifficulty ? 2 : 1;
    while (steps-- > 0 && history.length > 1) { history.pop(); state = history[history.length - 1]; }
    selected = null; targets = []; lastMove = []; updateRotateButtons(); render(); updateStatus();
  }

  function updateStatus() {
    var mode = aiDifficulty ? ('人機（AI：' + AI_NAMES[aiDifficulty] + '）') : '雙人對戰';
    statusEl.textContent = mode + '　｜　輪到 ' + COLOR_NAMES[state.player];
  }

  // ---- 綁定 ----
  function resize() {
    var wrap = document.getElementById('board-wrap');
    var w = wrap.clientWidth, h = Math.min(wrap.clientHeight, w * 0.8);
    var dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr; canvas.height = (w * 0.8) * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = (w * 0.8) + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // 用 CSS 像素座標，故把 canvas 邏輯尺寸換回 CSS
    canvas.width = w; canvas.height = w * 0.8;
    render();
  }
  canvas.addEventListener('click', function (e) {
    var rect = canvas.getBoundingClientRect();
    onTap(e.clientX - rect.left, e.clientY - rect.top);
  });
  canvas.addEventListener('touchstart', function (e) {
    e.preventDefault();
    var t = e.touches[0], rect = canvas.getBoundingClientRect();
    onTap(t.clientX - rect.left, t.clientY - rect.top);
  }, { passive: false });

  document.getElementById('btn-cw').addEventListener('click', function () {
    if (this._action) commit(this._action, false);
  });
  document.getElementById('btn-ccw').addEventListener('click', function () {
    if (this._action) commit(this._action, false);
  });
  document.getElementById('btn-undo').addEventListener('click', undo);
  document.getElementById('btn-menu').addEventListener('click', function () {
    document.getElementById('menu').classList.toggle('hidden');
  });
  document.querySelectorAll('[data-mode]').forEach(function (b) {
    b.addEventListener('click', function () {
      var m = this.getAttribute('data-mode');
      aiDifficulty = (m === 'pvp') ? null : m;
      document.getElementById('menu').classList.add('hidden');
      newGame(currentLayout);
    });
  });
  document.querySelectorAll('[data-layout]').forEach(function (b) {
    b.addEventListener('click', function () {
      currentLayout = this.getAttribute('data-layout');
      document.getElementById('menu').classList.add('hidden');
      newGame(currentLayout);
    });
  });
  window.addEventListener('resize', resize);

  loadImages(function () { newGame('classic'); resize(); });
})();
