// Capacitor／瀏覽器背景 AI：避免 3–5 秒搜尋阻塞觸控與渲染。
importScripts('rules_data.js', 'engine.js', 'ai.js');

self.onmessage = function (event) {
  var data = event.data;
  try {
    var historyCounts = new Map(data.historyCounts || []);
    var action = self.KhetAI.chooseAction(data.state, data.difficulty, {
      historyCounts: historyCounts
    });
    self.postMessage({ id: data.id, action: action });
  } catch (error) {
    self.postMessage({ id: data.id, error: error && error.message ? error.message : String(error) });
  }
};
