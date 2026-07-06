// 雷射棋規則引擎（JS 版）——khet/engine.py 的逐函式移植。
// state = {player, pieces}；pieces = 排序後的陣列，每個元素 [type,color,col,row,ori]。
// 排序、方向、朝向、雷射解算必須與 Python 版位元級一致（由向量測試把關）。
(function () {
  var RULES = (typeof window !== 'undefined') ? window.RULES_DATA
                                              : require('./rules_data.js');
  var LASER = RULES.laser_table;
  var LAYOUTS = RULES.layouts;
  var COLS = LAYOUTS.board.cols;      // 10
  var ROWS = LAYOUTS.board.rows;      // 8
  var SPHINX_INFO = LAYOUTS.sphinx;
  var FIRST_PLAYER = LAYOUTS.first_player;

  // 限制格 → Set，key "col,row"
  function cellKey(c, r) { return c + ',' + r; }
  var RESTRICTED = { RED: new Set(), SILVER: new Set() };
  LAYOUTS.restricted.RED.forEach(function (c) { RESTRICTED.RED.add(cellKey(c[0], c[1])); });
  LAYOUTS.restricted.SILVER.forEach(function (c) { RESTRICTED.SILVER.add(cellKey(c[0], c[1])); });

  // 方向 0=N 1=E 2=S 3=W
  var DIR_VECTORS = [[0, -1], [1, 0], [0, 1], [-1, 0]];
  var MOVE_VECTORS = [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]];
  var MAX_BEAM_STEPS = 500;

  function other(p) { return p === 'SILVER' ? 'RED' : 'SILVER'; }

  // 與 Python sorted() 對 tuple 的字典序一致：type,color(字串) → col,row,ori(數字)
  function pieceCmp(a, b) {
    if (a[0] < b[0]) return -1; if (a[0] > b[0]) return 1;
    if (a[1] < b[1]) return -1; if (a[1] > b[1]) return 1;
    if (a[2] !== b[2]) return a[2] - b[2];
    if (a[3] !== b[3]) return a[3] - b[3];
    return a[4] - b[4];
  }
  function sortPieces(arr) { arr = arr.slice(); arr.sort(pieceCmp); return arr; }

  function boardMap(pieces) {
    var m = {};
    for (var i = 0; i < pieces.length; i++) m[cellKey(pieces[i][2], pieces[i][3])] = pieces[i];
    return m;
  }
  function inBoard(c, r) { return c >= 0 && c < COLS && r >= 0 && r < ROWS; }
  function canOccupy(color, c, r) { return !RESTRICTED[other(color)].has(cellKey(c, r)); }

  function initialState(layout) {
    layout = layout || 'classic';
    var pieces = LAYOUTS.layouts[layout].map(function (p) {
      var ori = p.type === 'SCARAB' ? (p.orientation % 2) : (p.orientation % 4);
      return [p.type, p.color, p.col, p.row, ori];
    });
    return { player: FIRST_PLAYER, pieces: sortPieces(pieces) };
  }

  // 行動：{kind:'move'|'swap'|'rotate', col,row, dcol,drow | cw}
  function legalActions(state) {
    var player = state.player, pieces = state.pieces, occ = boardMap(pieces);
    var actions = [];
    for (var i = 0; i < pieces.length; i++) {
      var p = pieces[i], type = p[0], color = p[1], col = p[2], row = p[3];
      if (color !== player) continue;
      if (type === 'SPHINX') {
        actions.push({ kind: 'rotate', col: col, row: row, cw: true });
      } else if (type === 'SCARAB') {
        actions.push({ kind: 'rotate', col: col, row: row, cw: true });
      } else if (type === 'PYRAMID' || type === 'ANUBIS') {
        actions.push({ kind: 'rotate', col: col, row: row, cw: true });
        actions.push({ kind: 'rotate', col: col, row: row, cw: false });
      }
      // PHARAOH 不給旋轉（與 Python 一致）
      if (type === 'SPHINX') continue;
      for (var d = 0; d < MOVE_VECTORS.length; d++) {
        var dcol = MOVE_VECTORS[d][0], drow = MOVE_VECTORS[d][1];
        var nc = col + dcol, nr = row + drow;
        if (!inBoard(nc, nr)) continue;
        var target = occ[cellKey(nc, nr)];
        if (target === undefined) {
          if (canOccupy(color, nc, nr))
            actions.push({ kind: 'move', col: col, row: row, dcol: dcol, drow: drow });
        } else if (type === 'SCARAB' && (target[0] === 'PYRAMID' || target[0] === 'ANUBIS')) {
          if (canOccupy(color, nc, nr) && canOccupy(target[1], col, row))
            actions.push({ kind: 'swap', col: col, row: row, dcol: dcol, drow: drow });
        }
      }
    }
    return actions;
  }

  function rotatePiece(p, cw) {
    var type = p[0], color = p[1], col = p[2], row = p[3], ori = p[4], no;
    if (type === 'SPHINX') {
      var legal = SPHINX_INFO[color].legal_orientations;
      no = (ori === legal[0]) ? legal[1] : legal[0];
    } else if (type === 'SCARAB') {
      no = (ori + 1) % 2;
    } else {
      no = ((ori + (cw ? 1 : -1)) % 4 + 4) % 4;
    }
    return [type, color, col, row, no];
  }

  function applyActionNoLaser(state, a) {
    var pieces = state.pieces, occ = boardMap(pieces), np = [];
    var i, p;
    if (a.kind === 'rotate') {
      var tgt = occ[cellKey(a.col, a.row)];
      for (i = 0; i < pieces.length; i++) { p = pieces[i]; if (p !== tgt) np.push(p); }
      np.push(rotatePiece(tgt, a.cw));
    } else if (a.kind === 'move') {
      var t = occ[cellKey(a.col, a.row)];
      for (i = 0; i < pieces.length; i++) { p = pieces[i]; if (p !== t) np.push(p); }
      np.push([t[0], t[1], a.col + a.dcol, a.row + a.drow, t[4]]);
    } else if (a.kind === 'swap') {
      var pa = occ[cellKey(a.col, a.row)];
      var pb = occ[cellKey(a.col + a.dcol, a.row + a.drow)];
      for (i = 0; i < pieces.length; i++) { p = pieces[i]; if (p !== pa && p !== pb) np.push(p); }
      np.push([pa[0], pa[1], pb[2], pb[3], pa[4]]);
      np.push([pb[0], pb[1], pa[2], pa[3], pb[4]]);
    } else {
      throw new Error('unknown action ' + JSON.stringify(a));
    }
    return { player: state.player, pieces: sortPieces(np) };
  }

  function resolveLaser(pieces, player) {
    var occ = boardMap(pieces), info = SPHINX_INFO[player];
    var sphinx = occ[cellKey(info.col, info.row)];
    var col = sphinx[2], row = sphinx[3], dir = sphinx[4];
    var path = [[col, row]];
    for (var step = 0; step < MAX_BEAM_STEPS; step++) {
      col += DIR_VECTORS[dir][0]; row += DIR_VECTORS[dir][1];
      if (!inBoard(col, row)) return { pieces: pieces, path: path, event: 'exit', hit: null };
      path.push([col, row]);
      var piece = occ[cellKey(col, row)];
      if (piece === undefined) continue;
      var outcome = LASER[piece[0]][piece[4]][dir];
      if (outcome.result === 'reflect') {
        dir = outcome.dir;
      } else if (outcome.result === 'absorb') {
        return { pieces: pieces, path: path, event: 'absorb', hit: null };
      } else {
        var np = [];
        for (var i = 0; i < pieces.length; i++) if (pieces[i] !== piece) np.push(pieces[i]);
        return { pieces: sortPieces(np), path: path, event: 'hit', hit: piece };
      }
    }
    throw new Error('laser exceeded MAX_BEAM_STEPS');
  }

  function applyAction(state, a) {
    var mid = applyActionNoLaser(state, a);
    var res = resolveLaser(mid.pieces, mid.player);
    return {
      state: { player: other(state.player), pieces: res.pieces },
      path: res.path, event: res.event, hit: res.hit
    };
  }

  function winner(state) {
    var alive = { RED: false, SILVER: false };
    state.pieces.forEach(function (p) { if (p[0] === 'PHARAOH') alive[p[1]] = true; });
    if (!alive.RED) return 'SILVER';
    if (!alive.SILVER) return 'RED';
    return null;
  }

  // 規範序列化（向量比對用）：pieces 已排序，直接 JSON
  function stateKey(state) { return state.player + '|' + JSON.stringify(state.pieces); }

  var API = {
    COLS: COLS, ROWS: ROWS, RESTRICTED: RESTRICTED, SPHINX_INFO: SPHINX_INFO,
    FIRST_PLAYER: FIRST_PLAYER, MOVE_VECTORS: MOVE_VECTORS,
    other: other, cellKey: cellKey, boardMap: boardMap, sortPieces: sortPieces,
    initialState: initialState, legalActions: legalActions,
    applyAction: applyAction, resolveLaser: resolveLaser, winner: winner,
    stateKey: stateKey
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  if (typeof window !== 'undefined') window.KhetEngine = API;
})();
