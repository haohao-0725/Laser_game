# 雷射對決 Laser Duel v1.2.1（Windows／Android）

本次版本將桌面 v1.2.0 的 AI v2 完整同步到 Android，並維持 Windows 桌面版相同棋力。

## Android AI v2

- 同步迭代加深 PVS、aspiration window、置換表、killer/history heuristic。
- 搜尋樹完整處理三次同形；手機對局第三次同形後會鎖定為正式和局。
- 同步 quiescence、自傷逃脫、法老光路壓力與少子局面搜尋延伸。
- 悔棋會重建局面出現次數，AI 每回合收到完整對局歷史。
- 新增 Web Worker，3–5 秒 AI 搜尋不再阻塞 Canvas 動畫與觸控。

## 版本與驗證

- Android：`versionCode 3`、`versionName 1.2.1`，使用與舊版相同的 debug 簽章。
- pytest：118 passed。
- Python／JavaScript 規則一致性：400/400 PASS。
- JavaScript AI 一步殺、三次同形、已和局拒搜與跨語言評估測試通過。
- Playwright 手機視窗實測背景 AI 正常回手。
- Windows one-file 與 Android APK 均重新建置並驗證封裝。

## 已知限制

- 本次環境沒有連接 ADB 裝置，Android 實機完整對局仍待驗收。
- Android 提供的是 debug-signed APK；簽章與本專案先前 APK 相同，可直接覆蓋更新。
