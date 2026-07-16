// 手機版 AI v2：三次同形感知的迭代加深 PVS／alpha-beta 搜尋。
(function () {
  var E = (typeof globalThis !== 'undefined' && globalThis.KhetEngine)
    ? globalThis.KhetEngine : require('./engine.js');

  var WIN = 1000000, DRAW = 0, MATE_THRESHOLD = WIN - 10000, INF = WIN * 2;
  var PIECE_VALUE = { PHARAOH: 0, SPHINX: 0, SCARAB: 0, ANUBIS: 900, PYRAMID: 500 };
  var GUARD_BONUS = 40, PHARAOH_ESCAPE_BONUS = 8, SCARAB_SWAP_BONUS = 4;
  var BEAM_REFLECTION_BONUS = 2, BEAM_PRESSURE_BONUS = 12;
  var BEAM_NEAR_PHARAOH = 60, SELF_HIT_PENALTY = 300;
  var THREAT_PHARAOH = 5000, ABSORB_PRESSURE = 20;
  var EXACT = 0, LOWER = 1, UPPER = 2;
  var ASPIRATION = 350, Q_DEPTH = 1, Q_MAX_MOVES = 12;
  var ROOT_REPEAT_PENALTY = 120, TT_MAX = 250000, CACHE_MAX = 512;
  var TIMEOUT = { timeout: true };
  var POSITION_CACHE = new Map();

  function nowMs() {
    return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  }
  function inBoard(c, r) { return c >= 0 && c < E.COLS && r >= 0 && r < E.ROWS; }
  function canOccupy(color, c, r) { return !E.RESTRICTED[E.other(color)].has(E.cellKey(c, r)); }
  function actionKey(action) { return JSON.stringify(action); }
  function sameAction(a, b) { return a !== null && b !== null && actionKey(a) === actionKey(b); }
  function mapDropFirst(map) { var first = map.keys().next(); if (!first.done) map.delete(first.value); }

  function chebyshevToPath(cell, path) {
    if (!path.length) return 99;
    var best = 99;
    for (var i = 0; i < path.length; i++) {
      best = Math.min(best, Math.max(Math.abs(cell[0] - path[i][0]), Math.abs(cell[1] - path[i][1])));
    }
    return best;
  }

  function positionScores(pieces) {
    var cacheKey = JSON.stringify(pieces);
    var cached = POSITION_CACHE.get(cacheKey);
    if (cached) return cached;

    var occ = E.boardMap(pieces);
    var scores = { RED: 0, SILVER: 0 }, pharaohs = {};
    var scarabSwaps = { RED: 0, SILVER: 0 }, pharaohEscapes = { RED: 0, SILVER: 0 };
    var i, d;
    for (i = 0; i < pieces.length; i++) {
      var piece = pieces[i];
      scores[piece[1]] += PIECE_VALUE[piece[0]];
      if (piece[0] === 'PHARAOH') pharaohs[piece[1]] = piece;
    }

    for (i = 0; i < pieces.length; i++) {
      var p = pieces[i], type = p[0], color = p[1], col = p[2], row = p[3];
      if (type !== 'PHARAOH' && type !== 'SCARAB') continue;
      for (d = 0; d < E.MOVE_VECTORS.length; d++) {
        var nc = col + E.MOVE_VECTORS[d][0], nr = row + E.MOVE_VECTORS[d][1];
        if (!inBoard(nc, nr)) continue;
        var target = occ[E.cellKey(nc, nr)];
        if (target === undefined && canOccupy(color, nc, nr)) {
          if (type === 'PHARAOH') pharaohEscapes[color]++;
        } else if (type === 'SCARAB' && target !== undefined &&
                   (target[0] === 'PYRAMID' || target[0] === 'ANUBIS') &&
                   canOccupy(color, nc, nr) && canOccupy(target[1], col, row)) {
          scarabSwaps[color]++;
        }
      }
    }

    ['RED', 'SILVER'].forEach(function (side) {
      var ph = pharaohs[side];
      if (!ph) return;
      scores[side] += scarabSwaps[side] * SCARAB_SWAP_BONUS;
      scores[side] += pharaohEscapes[side] * PHARAOH_ESCAPE_BONUS;
      var guard = 0;
      for (var dc = -1; dc <= 1; dc++) for (var dr = -1; dr <= 1; dr++) {
        if (dc === 0 && dr === 0) continue;
        var neighbour = occ[E.cellKey(ph[2] + dc, ph[3] + dr)];
        if (neighbour && neighbour[1] === side) guard++;
      }
      scores[side] += guard * GUARD_BONUS;
    });

    var volatilePosition = false;
    ['RED', 'SILVER'].forEach(function (side) {
      var enemy = E.other(side), result = E.resolveLaser(pieces, side);
      var path = result.path.slice(1), reflections = 0;
      for (var j = 0; j < path.length - 1; j++) {
        var reflector = occ[E.cellKey(path[j][0], path[j][1])];
        if (reflector && (reflector[0] === 'PYRAMID' || reflector[0] === 'SCARAB')) reflections++;
      }
      scores[side] += reflections * BEAM_REFLECTION_BONUS;

      var enemyPharaoh = pharaohs[enemy];
      if (enemyPharaoh) {
        var distance = chebyshevToPath([enemyPharaoh[2], enemyPharaoh[3]], path);
        scores[enemy] -= Math.max(0, 8 - distance) * BEAM_PRESSURE_BONUS;
        if (distance <= 2) scores[enemy] -= (3 - distance) * BEAM_NEAR_PHARAOH;
        if (distance <= 1) volatilePosition = true;
      }

      if (result.event === 'hit') {
        volatilePosition = true;
        var victim = result.hit;
        var value = victim[0] === 'PHARAOH' ? THREAT_PHARAOH : ((PIECE_VALUE[victim[0]] / 2 | 0) + 50);
        scores[victim[1]] -= value;
        if (victim[1] === side) scores[side] -= SELF_HIT_PENALTY;
      } else if (result.event === 'absorb' && result.path.length) {
        var last = result.path[result.path.length - 1];
        var blocker = occ[E.cellKey(last[0], last[1])];
        if (blocker && blocker[1] === enemy) scores[enemy] -= ABSORB_PRESSURE;
      }
    });

    var value = { red: scores.RED, silver: scores.SILVER, volatile: volatilePosition };
    if (POSITION_CACHE.size >= 50000) POSITION_CACHE.clear();
    POSITION_CACHE.set(cacheKey, value);
    return value;
  }

  function evaluate(state) {
    var value = positionScores(state.pieces);
    return state.player === 'RED' ? value.red - value.silver : value.silver - value.red;
  }
  function terminalScore(state, victor, ply) { return victor === state.player ? WIN - ply : -(WIN - ply); }
  function scoreToTT(score, ply) {
    if (score >= MATE_THRESHOLD) return score + ply;
    if (score <= -MATE_THRESHOLD) return score - ply;
    return score;
  }
  function scoreFromTT(score, ply) {
    if (score >= MATE_THRESHOLD) return score - ply;
    if (score <= -MATE_THRESHOLD) return score + ply;
    return score;
  }
  function historySignature(counts) {
    var repeated = [];
    counts.forEach(function (count, key) { if (count >= 2) repeated.push(key + '=' + count); });
    repeated.sort();
    return repeated.join('\n');
  }

  function Searcher(deadline) {
    this.deadline = deadline;
    this.tt = new Map(); this.killers = {}; this.history = new Map();
    this.actionCache = new Map(); this.evalCache = new Map();
    this.nodes = 0; this.qnodes = 0; this.ttHits = 0; this.cutoffs = 0;
  }
  Searcher.prototype.checkTime = function () { if (nowMs() > this.deadline) throw TIMEOUT; };
  Searcher.prototype.tick = function () {
    this.nodes++;
    if (this.nodes % 128 === 0) this.checkTime();
  };
  Searcher.prototype.evaluate = function (state) {
    var key = E.stateKey(state), value = this.evalCache.get(key);
    if (value === undefined) {
      value = evaluate(state);
      if (this.evalCache.size >= 50000) this.evalCache.clear();
      this.evalCache.set(key, value);
    }
    return value;
  };
  Searcher.prototype.actions = function (state) {
    var key = E.stateKey(state), cached = this.actionCache.get(key);
    if (cached) return cached;
    var actions = E.legalActions(state);
    this.actionCache.set(key, actions);
    if (this.actionCache.size > CACHE_MAX) mapDropFirst(this.actionCache);
    return actions;
  };
  Searcher.prototype.forcingEntries = function (state) {
    var player = state.player, pieces = state.pieces, occ = E.boardMap(pieces);
    var current = E.resolveLaser(pieces, player), beamCells = new Set();
    current.path.forEach(function (cell) { beamCells.add(E.cellKey(cell[0], cell[1])); });
    var mustEvade = current.event === 'hit' && current.hit[1] === player;
    var candidates = [], representative = null, actions = E.legalActions(state);
    for (var i = 0; i < actions.length; i++) {
      var action = actions[i], source = E.cellKey(action.col, action.row), target = source;
      if (action.kind === 'move' || action.kind === 'swap')
        target = E.cellKey(action.col + action.dcol, action.row + action.drow);
      var piece = occ[source];
      var affects = piece[0] === 'SPHINX' || beamCells.has(source) || beamCells.has(target);
      if (affects) candidates.push(action);
      else if (current.event === 'hit' && representative === null) representative = action;
    }
    if (representative !== null) candidates.push(representative);

    var forcing = [];
    for (var j = 0; j < candidates.length; j++) {
      if (j % 12 === 0) this.checkTime();
      var applied = E.applyAction(state, candidates[j]);
      var evades = mustEvade && !(applied.event === 'hit' && applied.hit[1] === player);
      if (applied.event === 'hit' || E.winner(applied.state) !== null || evades)
        forcing.push({ action: candidates[j], state: applied.state, laser: applied });
    }
    return forcing;
  };
  Searcher.prototype.orderActions = function (state, actions, ttBest, ply) {
    var self = this, player = state.player, killers = this.killers[ply] || [];
    var laser = E.resolveLaser(state.pieces, player), beamCells = new Set();
    laser.path.forEach(function (cell) { beamCells.add(E.cellKey(cell[0], cell[1])); });
    return actions.slice().sort(function (a, b) {
      function priority(action) {
        var key = player + '|' + actionKey(action), score = self.history.get(key) || 0;
        if (sameAction(action, ttBest)) score += 4000000000;
        if (killers.some(function (killer) { return sameAction(action, killer); })) score += 3000000000;
        var source = E.cellKey(action.col, action.row), target = source;
        if (action.kind === 'move' || action.kind === 'swap')
          target = E.cellKey(action.col + action.dcol, action.row + action.drow);
        var changesBeam = beamCells.has(source) || beamCells.has(target);
        if (laser.event === 'hit' && !changesBeam) {
          var victim = laser.hit, value = PIECE_VALUE[victim[0]] + 100;
          score += victim[1] !== player ? 2000000000 + value : -2000000000 - value;
        } else if (changesBeam) score += 1000000;
        score += action.kind === 'swap' ? 300 : (action.kind === 'move' ? 200 : 100);
        return score;
      }
      return priority(b) - priority(a);
    });
  };
  Searcher.prototype.orderEntries = function (state, entries) {
    var self = this, player = state.player;
    return entries.slice().sort(function (a, b) {
      function priority(entry) {
        if (E.winner(entry.state) === player) return 4000000000;
        if (entry.laser.event === 'hit') {
          var victim = entry.laser.hit, value = PIECE_VALUE[victim[0]] + 100;
          return victim[1] !== player ? 3000000000 + value : -1000000000 - value;
        }
        return self.history.get(player + '|' + actionKey(entry.action)) || 0;
      }
      return priority(b) - priority(a);
    });
  };
  Searcher.prototype.descend = function (child, laser, callback, counts) {
    var key = E.stateKey(child);
    if (laser.event === 'hit') {
      var reset = new Map(); reset.set(key, 1);
      return callback(reset);
    }
    var oldCount = counts.get(key) || 0;
    counts.set(key, oldCount + 1);
    try { return callback(counts); }
    finally { if (oldCount) counts.set(key, oldCount); else counts.delete(key); }
  };
  Searcher.prototype.storeTT = function (key, depth, score, flag, action, ply) {
    if (this.tt.size >= TT_MAX && !this.tt.has(key)) mapDropFirst(this.tt);
    this.tt.set(key, { depth: depth, score: scoreToTT(score, ply), flag: flag, action: action });
  };
  Searcher.prototype.negamax = function (state, depth, alpha, beta, ply, counts) {
    this.tick();
    var victor = E.winner(state), stateKey = E.stateKey(state);
    if (victor !== null) return terminalScore(state, victor, ply);
    if ((counts.get(stateKey) || 0) >= 3) return DRAW;
    if (depth <= 0) {
      if (positionScores(state.pieces).volatile) return this.qsearch(state, alpha, beta, ply, Q_DEPTH, counts);
      return this.evaluate(state);
    }

    var alphaOrig = alpha, betaOrig = beta, key = stateKey + '#' + historySignature(counts);
    var entry = this.tt.get(key), ttBest = null;
    if (entry) {
      ttBest = entry.action;
      var stored = scoreFromTT(entry.score, ply);
      if (entry.depth >= depth) {
        this.ttHits++;
        if (entry.flag === EXACT) return stored;
        if (entry.flag === LOWER) alpha = Math.max(alpha, stored); else beta = Math.min(beta, stored);
        if (alpha >= beta) return stored;
      }
    }

    var self = this, best = -INF, bestAction = null;
    var ordered = this.orderActions(state, this.actions(state), ttBest, ply);
    for (var i = 0; i < ordered.length; i++) {
      var action = ordered[i], applied = E.applyAction(state, action), value;
      var full = function (childCounts) {
        return -self.negamax(applied.state, depth - 1, -beta, -alpha, ply + 1, childCounts);
      };
      if (i === 0) value = this.descend(applied.state, applied, full, counts);
      else {
        var scout = function (childCounts) {
          return -self.negamax(applied.state, depth - 1, -alpha - 1, -alpha, ply + 1, childCounts);
        };
        value = this.descend(applied.state, applied, scout, counts);
        if (alpha < value && value < beta) value = this.descend(applied.state, applied, full, counts);
      }
      if (value > best) { best = value; bestAction = action; }
      if (value > alpha) alpha = value;
      if (alpha >= beta) {
        this.cutoffs++;
        var killers = this.killers[ply] || [];
        if (!killers.some(function (killer) { return sameAction(killer, action); }))
          this.killers[ply] = [action].concat(killers.slice(0, 1));
        var historyKey = state.player + '|' + actionKey(action);
        this.history.set(historyKey, (this.history.get(historyKey) || 0) + depth * depth);
        break;
      }
    }
    var flag = best <= alphaOrig ? UPPER : (best >= betaOrig ? LOWER : EXACT);
    this.storeTT(key, depth, best, flag, bestAction, ply);
    return best;
  };
  Searcher.prototype.qsearch = function (state, alpha, beta, ply, qdepth, counts) {
    this.qnodes++; this.checkTime();
    var victor = E.winner(state), key = E.stateKey(state);
    if (victor !== null) return terminalScore(state, victor, ply);
    if ((counts.get(key) || 0) >= 3) return DRAW;
    var standPat = this.evaluate(state), current = E.resolveLaser(state.pieces, state.player);
    var mustEvade = current.event === 'hit' && current.hit[1] === state.player;
    if (qdepth <= 0) return standPat;
    if (!mustEvade && standPat >= beta) return standPat;
    if (!mustEvade && standPat > alpha) alpha = standPat;
    var forcing = this.forcingEntries(state);
    if (!forcing.length) return standPat;
    var self = this, best = mustEvade ? -INF : standPat;
    var ordered = this.orderEntries(state, forcing).slice(0, Q_MAX_MOVES);
    for (var i = 0; i < ordered.length; i++) {
      var entry = ordered[i];
      var value = this.descend(entry.state, entry.laser, function (childCounts) {
        return -self.qsearch(entry.state, -beta, -alpha, ply + 1, qdepth - 1, childCounts);
      }, counts);
      if (value > best) best = value;
      if (value > alpha) alpha = value;
      if (alpha >= beta) { this.cutoffs++; break; }
    }
    return best;
  };

  function prepareHistory(state, historyCounts) {
    var counts = new Map();
    if (historyCounts instanceof Map) historyCounts.forEach(function (count, key) { if (count > 0) counts.set(key, count); });
    else if (historyCounts) Object.keys(historyCounts).forEach(function (key) { if (historyCounts[key] > 0) counts.set(key, historyCounts[key]); });
    var key = E.stateKey(state);
    counts.set(key, Math.max(1, counts.get(key) || 0));
    return counts;
  }

  function searchRoot(searcher, state, depth, alpha, beta, entries, counts) {
    var scores = new Map(), bestScore = -INF, bestAction = null, timedOut = false;
    var rootAlpha = alpha;
    try {
      for (var i = 0; i < entries.length; i++) {
        var entry = entries[i], value;
        var full = function (childCounts) {
          return -searcher.negamax(entry.state, depth - 1, -beta, -rootAlpha, 1, childCounts);
        };
        if (i === 0) value = searcher.descend(entry.state, entry.laser, full, counts);
        else {
          var scout = function (childCounts) {
            return -searcher.negamax(entry.state, depth - 1, -rootAlpha - 1, -rootAlpha, 1, childCounts);
          };
          value = searcher.descend(entry.state, entry.laser, scout, counts);
          if (rootAlpha < value && value < beta)
            value = searcher.descend(entry.state, entry.laser, full, counts);
        }
        if ((counts.get(E.stateKey(entry.state)) || 0) === 1 && Math.abs(value) < MATE_THRESHOLD)
          value -= ROOT_REPEAT_PENALTY;
        scores.set(actionKey(entry.action), value);
        if (value > bestScore) { bestScore = value; bestAction = entry.action; }
        if (value > rootAlpha) rootAlpha = value;
        if (rootAlpha >= beta) { searcher.cutoffs++; break; }
      }
    } catch (error) {
      if (error !== TIMEOUT) throw error;
      timedOut = true;
    }
    return { score: bestScore, action: bestAction, scores: scores, timedOut: timedOut };
  }

  function search(state, options) {
    options = options || {};
    var maxDepth = options.maxDepth === undefined ? 4 : options.maxDepth;
    var timeLimit = options.timeLimit === undefined ? 3.0 : options.timeLimit;
    var noise = options.noise || 0, rng = options.rng || Math.random;
    var counts = prepareHistory(state, options.historyCounts);
    if ((counts.get(E.stateKey(state)) || 0) >= 3) throw new Error('目前局面已因三次同形判和');
    var searcher = new Searcher(nowMs() + timeLimit * 1000);
    var rootEntries = searcher.actions(state).map(function (action) {
      var applied = E.applyAction(state, action);
      return { action: action, state: applied.state, laser: applied };
    });
    if (!rootEntries.length) throw new Error('無合法行動');
    for (var i = rootEntries.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1)), temp = rootEntries[i]; rootEntries[i] = rootEntries[j]; rootEntries[j] = temp;
    }

    var bestAction = rootEntries[0].action, bestScore = 0, completedDepth = 0;
    var completedScores = new Map(), previousScores = new Map();
    var targetDepth = maxDepth;
    if (maxDepth >= 3) targetDepth += state.pieces.length <= 10 ? 2 : (state.pieces.length <= 16 ? 1 : 0);

    for (var depth = 1; depth <= targetDepth; depth++) {
      var ordered = rootEntries.slice().sort(function (a, b) {
        return (previousScores.get(actionKey(b.action)) || 0) - (previousScores.get(actionKey(a.action)) || 0);
      });
      var alpha = completedDepth ? bestScore - ASPIRATION : -INF;
      var beta = completedDepth ? bestScore + ASPIRATION : INF;
      var result = searchRoot(searcher, state, depth, alpha, beta, ordered, counts);
      if (result.action !== null) bestAction = result.action;
      if (result.timedOut) break;
      if (result.score <= alpha || result.score >= beta) {
        result = searchRoot(searcher, state, depth, -INF, INF, ordered, counts);
        if (result.action !== null) bestAction = result.action;
        if (result.timedOut) break;
      }
      bestScore = result.score; previousScores = result.scores;
      completedScores = result.scores; completedDepth = depth;
      if (noise && result.scores.size) {
        var noisyBest = -INF;
        result.scores.forEach(function (score, key) {
          var candidate = score + (rng() * 2 - 1) * noise;
          if (candidate > noisyBest) {
            noisyBest = candidate;
            for (var n = 0; n < rootEntries.length; n++)
              if (actionKey(rootEntries[n].action) === key) bestAction = rootEntries[n].action;
          }
        });
      } else if (result.action !== null) bestAction = result.action;
      if (bestScore >= WIN - depth - 1) break;
    }

    var rootScores = [];
    completedScores.forEach(function (score, key) {
      rootScores.push({ action: JSON.parse(key), score: score });
    });
    return {
      action: bestAction,
      info: {
        depth: completedDepth, score: bestScore, targetDepth: targetDepth,
        nodes: searcher.nodes, qnodes: searcher.qnodes,
        ttHits: searcher.ttHits, cutoffs: searcher.cutoffs, rootScores: rootScores
      }
    };
  }

  var DIFFICULTIES = {
    easy: { maxDepth: 2, timeLimit: 1.0, noise: 250 },
    medium: { maxDepth: 4, timeLimit: 3.0, noise: 0 },
    hard: { maxDepth: 7, timeLimit: 5.0, noise: 0 }
  };
  function chooseAction(state, difficulty, options) {
    var cfg = DIFFICULTIES[difficulty] || DIFFICULTIES.medium;
    options = options || {};
    return search(state, {
      maxDepth: cfg.maxDepth,
      timeLimit: options.timeLimit === undefined ? cfg.timeLimit : options.timeLimit,
      noise: cfg.noise,
      rng: options.rng,
      historyCounts: options.historyCounts
    }).action;
  }

  var API = { evaluate: evaluate, search: search, chooseAction: chooseAction, DIFFICULTIES: DIFFICULTIES };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  if (typeof globalThis !== 'undefined') globalThis.KhetAI = API;
})();
