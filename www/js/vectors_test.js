// 規則一致性向量測試（Node 與瀏覽器共用核心 runVectors）。
// Node：node www/js/vectors_test.js  → 讀 www/test_vectors.json 逐一比對 engine.js。
// 瀏覽器：vectors_test.html 載入後呼叫 runVectors(vectors) 顯示 N/N PASS。
(function () {
  function normPieces(pieces) {
    // 與 engine 的排序一致，序列化成可比字串
    var arr = pieces.map(function (p) { return [p[0], p[1], p[2], p[3], p[4]]; });
    arr.sort(function (a, b) {
      if (a[0] < b[0]) return -1; if (a[0] > b[0]) return 1;
      if (a[1] < b[1]) return -1; if (a[1] > b[1]) return 1;
      if (a[2] !== b[2]) return a[2] - b[2];
      if (a[3] !== b[3]) return a[3] - b[3];
      return a[4] - b[4];
    });
    return JSON.stringify(arr);
  }

  function runVectors(vectors, Engine) {
    var pass = 0, fails = [];
    for (var i = 0; i < vectors.length; i++) {
      var v = vectors[i];
      var stateIn = { player: v.state_in.player, pieces: Engine.sortPieces(v.state_in.pieces) };
      var out = Engine.applyAction(stateIn, v.action);

      var okState = out.state.player === v.state_out.player &&
        normPieces(out.state.pieces) === normPieces(v.state_out.pieces);
      var okEvent = out.event === v.event;
      var okPath = JSON.stringify(out.path) === JSON.stringify(v.path);
      var okHit = JSON.stringify(out.hit) === JSON.stringify(v.hit);

      if (okState && okEvent && okPath && okHit) {
        pass++;
      } else {
        fails.push({ index: i, okState: okState, okEvent: okEvent, okPath: okPath, okHit: okHit, vector: v });
      }
    }
    return { total: vectors.length, pass: pass, fails: fails };
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runVectors: runVectors };
    if (require.main === module) {
      var fs = require('fs'), path = require('path');
      var Engine = require('./engine.js');
      var vectors = JSON.parse(fs.readFileSync(
        path.join(__dirname, '..', 'test_vectors.json'), 'utf8'));
      var r = runVectors(vectors, Engine);
      console.log('規則一致性向量：' + r.pass + '/' + r.total + ' PASS');
      if (r.fails.length) {
        console.log('前 3 個失敗：');
        r.fails.slice(0, 3).forEach(function (f) {
          console.log('  #' + f.index, 'state=' + f.okState, 'event=' + f.okEvent,
            'path=' + f.okPath, 'hit=' + f.okHit);
          console.log('   action=', JSON.stringify(f.vector.action));
        });
        process.exit(1);
      }
      process.exit(0);
    }
  }
  if (typeof window !== 'undefined') window.runVectors = runVectors;
})();
