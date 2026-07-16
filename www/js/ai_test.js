// Node 測試：手機 AI v2 的戰術、三次同形與 Python 評估一致性入口。
var fs = require('fs');
var E = require('./engine.js');
var AI = require('./ai.js');

function assert(condition, message) { if (!condition) throw new Error(message); }
function fixedRng() { return 0.5; }

function runSelfTests() {
  ['classic', 'imhotep', 'dynasty'].forEach(function (layout) {
    assert(AI.evaluate(E.initialState(layout)) === 0, layout + ' 開局評估不對稱');
  });

  var mateState = {
    player: 'SILVER',
    pieces: E.sortPieces([
      ['SPHINX', 'SILVER', 9, 7, 0],
      ['SPHINX', 'RED', 0, 0, 1],
      ['PHARAOH', 'RED', 5, 7, 0],
      ['PHARAOH', 'SILVER', 4, 6, 0],
      ['PYRAMID', 'SILVER', 2, 4, 0]
    ])
  };
  var mate = AI.search(mateState, { maxDepth: 1, timeLimit: 2, rng: fixedRng });
  assert(E.winner(E.applyAction(mateState, mate.action).state) === 'SILVER', 'AI 沒找到一步殺');

  var state = E.initialState('classic');
  var actions = E.legalActions(state), repeatedAction = null, child = null;
  for (var i = 0; i < actions.length; i++) {
    var applied = E.applyAction(state, actions[i]);
    if (applied.event !== 'hit') { repeatedAction = actions[i]; child = applied.state; break; }
  }
  var counts = new Map();
  counts.set(E.stateKey(state), 1); counts.set(E.stateKey(child), 2);
  var repetition = AI.search(state, {
    maxDepth: 1, timeLimit: 2, rng: fixedRng, historyCounts: counts
  });
  var repeatedScore = repetition.info.rootScores.find(function (entry) {
    return JSON.stringify(entry.action) === JSON.stringify(repeatedAction);
  });
  assert(repeatedScore && repeatedScore.score === 0, '第三次同形沒有評為和局');

  counts = new Map(); counts.set(E.stateKey(state), 3);
  var rejected = false;
  try { AI.search(state, { maxDepth: 1, historyCounts: counts }); }
  catch (error) { rejected = /三次同形/.test(error.message); }
  assert(rejected, '已和局的局面仍可繼續搜尋');
  assert(repetition.info.qnodes > 0, '搜尋沒有進入 quiescence');
  console.log('手機 AI v2：戰術／三次同形 PASS');
}

if (process.argv[2]) {
  var states = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  console.log(JSON.stringify(states.map(function (state) { return AI.evaluate(state); })));
} else {
  runSelfTests();
}
