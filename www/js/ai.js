// 手機版 AI：negamax + alpha-beta，深度調低（行動端效能）。評估函數與 Python 版對齊。
(function () {
  var E = (typeof window !== 'undefined') ? window.KhetEngine : require('./engine.js');
  var WIN = 1000000;
  var PIECE_VALUE = { PHARAOH: 0, SPHINX: 0, SCARAB: 0, ANUBIS: 900, PYRAMID: 500 };
  var GUARD = 40, THREAT_PHARAOH = 5000;

  function evaluate(state) {
    var player = state.player, pieces = state.pieces;
    var occ = E.boardMap(pieces);
    var score = { RED: 0, SILVER: 0 };
    var pharaohs = {};
    pieces.forEach(function (p) {
      score[p[1]] += PIECE_VALUE[p[0]];
      if (p[0] === 'PHARAOH') pharaohs[p[1]] = p;
    });
    ['RED', 'SILVER'].forEach(function (color) {
      var ph = pharaohs[color]; if (!ph) return;
      var guard = 0;
      for (var dc = -1; dc <= 1; dc++) for (var dr = -1; dr <= 1; dr++) {
        if (dc === 0 && dr === 0) continue;
        var q = occ[E.cellKey(ph[2] + dc, ph[3] + dr)];
        if (q && q[1] === color) guard++;
      }
      score[color] += guard * GUARD;
    });
    ['RED', 'SILVER'].forEach(function (color) {
      var res = E.resolveLaser(pieces, color);
      if (res.event === 'hit') {
        var v = res.hit[0] === 'PHARAOH' ? THREAT_PHARAOH : ((PIECE_VALUE[res.hit[0]] / 2 | 0) + 50);
        score[res.hit[1]] -= v;
      }
    });
    return score[player] - score[E.other(player)];
  }

  function negamax(state, depth, alpha, beta, ply) {
    var w = E.winner(state);
    if (w !== null) return (w === state.player) ? (WIN - ply) : -(WIN - ply);
    if (depth === 0) return evaluate(state);
    var best = -WIN * 2;
    var actions = E.legalActions(state);
    for (var i = 0; i < actions.length; i++) {
      var child = E.applyAction(state, actions[i]).state;
      var val = -negamax(child, depth - 1, -beta, -alpha, ply + 1);
      if (val > best) best = val;
      if (val > alpha) alpha = val;
      if (alpha >= beta) break;
    }
    return best;
  }

  function chooseAction(state, difficulty) {
    var cfg = { easy: { depth: 2, noise: 250 }, medium: { depth: 3, noise: 0 }, hard: { depth: 4, noise: 0 } };
    var c = cfg[difficulty] || cfg.medium;
    var actions = E.legalActions(state);
    // 洗牌避免決定性
    for (var i = actions.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = actions[i]; actions[i] = actions[j]; actions[j] = t;
    }
    var bestVal = -WIN * 3, bestAct = actions[0], alpha = -WIN * 2, beta = WIN * 2;
    for (var k = 0; k < actions.length; k++) {
      var child = E.applyAction(state, actions[k]).state;
      var val = -negamax(child, c.depth - 1, -beta, -alpha, 1);
      if (c.noise) val += (Math.random() * 2 - 1) * c.noise;
      if (val > bestVal) { bestVal = val; bestAct = actions[k]; }
      if (val > alpha) alpha = val;
    }
    return bestAct;
  }

  var API = { evaluate: evaluate, chooseAction: chooseAction };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  if (typeof window !== 'undefined') window.KhetAI = API;
})();
