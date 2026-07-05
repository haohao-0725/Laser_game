"""棋盤 widget：渲染、選取/行動操作、雷射動畫。規則一律問 khet 引擎。"""
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from khet.engine import (
    Move, Rotate, Swap, RESTRICTED, board_map, legal_actions,
)
from gui.assets import play_sound, store

# 顏色配置（深色科幻風，與素材一致）
C_BG = QColor(16, 20, 28)
C_GRID = QColor(56, 66, 86)
C_TILE = QColor(28, 34, 46)
C_RED_TILE = QColor(255, 70, 40, 46)
C_RED_TILE_BORDER = QColor(255, 100, 60, 110)
C_SILVER_TILE = QColor(0, 210, 255, 36)
C_SILVER_TILE_BORDER = QColor(0, 220, 255, 100)
C_SELECT = QColor(255, 230, 80)
C_TARGET = QColor(90, 255, 140, 190)
C_SWAP = QColor(160, 120, 255, 210)
C_BEAM_GLOW = QColor(255, 110, 40, 70)
C_BEAM_CORE = QColor(255, 235, 190, 235)

ANIM_INTERVAL_MS = 35
EXPLOSION_TICKS = 6


class BoardWidget(QWidget):
    turn_finished = pyqtSignal(object)      # 參數：LaserResult

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setMinimumSize(760, 620)
        self.mode = "idle"                  # idle | selected | animating
        self.input_locked = False           # AI 思考中鎖定人類輸入
        self.selected: tuple | None = None  # (col, row)
        self.overlay: list = []             # [(QRectF, action, kind)]
        # 動畫狀態
        self.anim_result = None
        self.anim_progress = 0
        self.explosion_tick = 0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(ANIM_INTERVAL_MS)
        self.anim_timer.timeout.connect(self._anim_tick)

    # ------------------------------------------------------------ 對外
    def set_controller(self, controller) -> None:
        self.anim_timer.stop()
        self.controller = controller
        self.mode = "idle"
        self.input_locked = False
        self.selected = None
        self.overlay = []
        self.anim_result = None
        self.update()

    def play_action(self, action) -> None:
        """程式化走一手（AI 用），與人類點擊走同一條動畫路徑。"""
        if self.mode != "animating":
            self._commit(action)

    # ------------------------------------------------------------ 幾何
    def _geometry(self) -> tuple[float, float, float]:
        """回傳 (ox, oy, cell_size)。棋盤 10:8 置中。"""
        margin = 16.0
        w, h = self.width() - 2 * margin, self.height() - 2 * margin
        cs = min(w / 10.0, h / 8.0)
        ox = (self.width() - cs * 10) / 2
        oy = (self.height() - cs * 8) / 2
        return ox, oy, cs

    def _cell_rect(self, col: int, row: int) -> QRectF:
        ox, oy, cs = self._geometry()
        return QRectF(ox + col * cs, oy + row * cs, cs, cs)

    def _cell_center(self, col: int, row: int) -> QPointF:
        return self._cell_rect(col, row).center()

    def _cell_at(self, pos: QPointF) -> tuple | None:
        ox, oy, cs = self._geometry()
        col = int((pos.x() - ox) // cs)
        row = int((pos.y() - oy) // cs)
        if 0 <= col < 10 and 0 <= row < 8 and pos.x() >= ox and pos.y() >= oy:
            return (col, row)
        return None

    # ------------------------------------------------------------ 互動
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if (self.mode == "animating" or self.input_locked
                or self.controller.winner() is not None):
            return
        pos = event.position()

        # 1) 先看是否點中行動鈕
        for rect, action, _kind in self.overlay:
            if rect.contains(pos):
                play_sound("click")
                self._commit(action)
                return

        # 2) 點自己的棋 → 選取；其他 → 取消選取
        cell = self._cell_at(pos)
        player, pieces = self.controller.state
        if cell is not None:
            piece = board_map(pieces).get(cell)
            if piece is not None and piece[1] == player:
                self.selected = cell
                self.mode = "selected"
                self._build_overlay()
                self.update()
                return
        self.selected = None
        self.overlay = []
        self.mode = "idle"
        self.update()

    def _build_overlay(self) -> None:
        """為選中的棋子建立行動鈕（目標格 + 旋轉鈕）與命中區域。"""
        self.overlay = []
        if self.selected is None:
            return
        col, row = self.selected
        _, _, cs = self._geometry()
        sel_rect = self._cell_rect(col, row)
        acts = [a for a in legal_actions(self.controller.state)
                if (a.col, a.row) == (col, row)]
        rotates = [a for a in acts if isinstance(a, Rotate)]
        for a in acts:
            if isinstance(a, (Move, Swap)):
                target = self._cell_rect(col + a.dcol, row + a.drow)
                shrink = cs * 0.18
                self.overlay.append((target.adjusted(shrink, shrink, -shrink, -shrink),
                                     a, "swap" if isinstance(a, Swap) else "move"))
        btn = cs * 0.40
        if len(rotates) == 1:      # SPHINX / SCARAB：單顆切換鈕（置中下方）
            r = QRectF(sel_rect.center().x() - btn / 2, sel_rect.bottom() - btn, btn, btn)
            self.overlay.append((r, rotates[0], "rotate_cw"))
        elif rotates:              # PYRAMID / ANUBIS：順逆兩顆（左下/右下）
            for a in rotates:
                if a.cw:
                    r = QRectF(sel_rect.right() - btn, sel_rect.bottom() - btn, btn, btn)
                    self.overlay.append((r, a, "rotate_cw"))
                else:
                    r = QRectF(sel_rect.left(), sel_rect.bottom() - btn, btn, btn)
                    self.overlay.append((r, a, "rotate_ccw"))

    def _commit(self, action) -> None:
        result = self.controller.do_action(action)
        play_sound("laser")
        self.selected = None
        self.overlay = []
        self.anim_result = result
        self.anim_progress = 1
        self.explosion_tick = 0
        self.mode = "animating"
        self.anim_timer.start()
        self.update()

    def _anim_tick(self) -> None:
        res = self.anim_result
        if self.anim_progress < len(res.path):
            self.anim_progress += 1
        elif res.event == "hit" and self.explosion_tick < EXPLOSION_TICKS:
            if self.explosion_tick == 0:
                play_sound("hit")
            self.explosion_tick += 1
        else:
            self.anim_timer.stop()
            self.mode = "idle"
            self.update()
            self.turn_finished.emit(res)
            return
        self.update()

    # ------------------------------------------------------------ 繪製
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), C_BG)

        ox, oy, cs = self._geometry()
        board_rect = QRectF(ox, oy, cs * 10, cs * 8)
        self._draw_board(painter, board_rect, cs)
        self._draw_pieces(painter, cs)
        self._draw_selection(painter)
        self._draw_overlay(painter, cs)
        if self.mode == "animating":
            self._draw_beam(painter, cs)
        painter.end()

    def _draw_board(self, painter, board_rect, cs) -> None:
        bg = store().image("board_bg.png")
        if bg is not None:
            painter.drawPixmap(board_rect, bg, QRectF(bg.rect()))
        else:
            painter.fillRect(board_rect, C_TILE)

        tile_n = store().image("tile_normal.png")
        tile_r = store().image("tile_red_only.png")
        tile_s = store().image("tile_silver_only.png")
        for col in range(10):
            for row in range(8):
                rect = self._cell_rect(col, row)
                cell = (col, row)
                if cell in RESTRICTED["RED"]:
                    if tile_r is not None:
                        painter.drawPixmap(rect, tile_r, QRectF(tile_r.rect()))
                    else:
                        painter.fillRect(rect, C_RED_TILE)
                        painter.setPen(QPen(C_RED_TILE_BORDER, 2))
                        painter.drawRect(rect.adjusted(2, 2, -2, -2))
                elif cell in RESTRICTED["SILVER"]:
                    if tile_s is not None:
                        painter.drawPixmap(rect, tile_s, QRectF(tile_s.rect()))
                    else:
                        painter.fillRect(rect, C_SILVER_TILE)
                        painter.setPen(QPen(C_SILVER_TILE_BORDER, 2))
                        painter.drawRect(rect.adjusted(2, 2, -2, -2))
                elif tile_n is not None:
                    painter.drawPixmap(rect, tile_n, QRectF(tile_n.rect()))
        painter.setPen(QPen(C_GRID, 1))
        for col in range(11):
            painter.drawLine(QPointF(board_rect.left() + col * cs, board_rect.top()),
                             QPointF(board_rect.left() + col * cs, board_rect.bottom()))
        for row in range(9):
            painter.drawLine(QPointF(board_rect.left(), board_rect.top() + row * cs),
                             QPointF(board_rect.right(), board_rect.top() + row * cs))

    def _pieces_to_draw(self):
        """動畫中：被擊中的棋在爆炸結束前仍要畫出來。"""
        _, pieces = self.controller.state
        if (self.mode == "animating" and self.anim_result is not None
                and self.anim_result.hit_piece is not None
                and self.explosion_tick < EXPLOSION_TICKS):
            return pieces + (self.anim_result.hit_piece,)
        return pieces

    def _draw_pieces(self, painter, cs) -> None:
        for piece in self._pieces_to_draw():
            ptype, color, col, row, ori = piece
            rect = self._cell_rect(col, row)
            painter.save()
            painter.translate(rect.center())
            painter.rotate(ori * 90)
            size = cs * 0.92
            local = QRectF(-size / 2, -size / 2, size, size)
            pm = store().piece(ptype, color)
            if pm is not None:
                painter.drawPixmap(local, pm, QRectF(pm.rect()))
            else:
                self._draw_placeholder(painter, local, ptype, color)
            painter.restore()

    def _draw_placeholder(self, painter, r, ptype, color) -> None:
        """素材缺檔時的幾何佔位圖形（orientation 0 姿態，外層已旋轉）。"""
        body = QColor(225, 228, 235) if color == "SILVER" else QColor(150, 30, 25)
        glow = QColor(0, 220, 255) if color == "SILVER" else QColor(255, 150, 60)
        painter.setPen(QPen(QColor(0, 0, 0, 160), 2))
        if ptype == "PHARAOH":
            painter.setBrush(body)
            painter.drawEllipse(r.adjusted(r.width() * 0.12, r.width() * 0.12,
                                           -r.width() * 0.12, -r.width() * 0.12))
            painter.setBrush(glow)
            painter.drawEllipse(r.center(), r.width() * 0.14, r.width() * 0.14)
        elif ptype == "SPHINX":
            painter.setBrush(body)
            painter.drawEllipse(r.adjusted(r.width() * 0.2, r.width() * 0.2,
                                           -r.width() * 0.2, -r.width() * 0.2))
            painter.setPen(QPen(glow, r.width() * 0.14, cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(0, 0), QPointF(0, r.top() + r.width() * 0.06))
        elif ptype == "PYRAMID":
            painter.setBrush(body)
            pts = [r.topLeft(), r.bottomRight(), r.bottomLeft()]
            from PyQt6.QtGui import QPolygonF
            painter.drawPolygon(QPolygonF(pts))
            painter.setPen(QPen(glow, r.width() * 0.09))
            painter.drawLine(r.topLeft(), r.bottomRight())
        elif ptype == "SCARAB":
            painter.setPen(QPen(body, r.width() * 0.2, cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(r.topLeft(), r.bottomRight())
            painter.setPen(QPen(glow, r.width() * 0.06))
            painter.drawLine(r.topLeft(), r.bottomRight())
        elif ptype == "ANUBIS":
            painter.setBrush(body)
            painter.drawRect(r.adjusted(r.width() * 0.18, r.width() * 0.24,
                                        -r.width() * 0.18, -r.width() * 0.1))
            painter.setBrush(glow)
            painter.drawRect(QRectF(r.left() + r.width() * 0.1, r.top() + r.width() * 0.06,
                                    r.width() * 0.8, r.width() * 0.16))

    def _draw_selection(self, painter) -> None:
        if self.selected is None:
            return
        rect = self._cell_rect(*self.selected)
        painter.setPen(QPen(C_SELECT, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect.adjusted(2, 2, -2, -2))

    def _draw_overlay(self, painter, cs) -> None:
        icon_cw = store().image("icon_rotate_cw.png")
        icon_ccw = store().image("icon_rotate_ccw.png")
        icon_swap = store().image("icon_swap.png")
        for rect, _action, kind in self.overlay:
            if kind == "move":
                painter.setPen(QPen(C_TARGET, 2))
                painter.setBrush(QColor(90, 255, 140, 60))
                painter.drawEllipse(rect)
            elif kind == "swap":
                painter.setPen(QPen(C_SWAP, 2))
                painter.setBrush(QColor(160, 120, 255, 60))
                painter.drawEllipse(rect)
                if icon_swap is not None:
                    painter.drawPixmap(rect, icon_swap, QRectF(icon_swap.rect()))
            else:
                painter.setPen(QPen(QColor(240, 240, 255, 220), 2))
                painter.setBrush(QColor(30, 40, 60, 200))
                painter.drawEllipse(rect)
                icon = icon_cw if kind == "rotate_cw" else icon_ccw
                if icon is not None:
                    pad = rect.width() * 0.12
                    painter.drawPixmap(rect.adjusted(pad, pad, -pad, -pad),
                                       icon, QRectF(icon.rect()))
                else:
                    painter.setPen(QPen(QColor(255, 255, 255), 2))
                    painter.setFont(QFont("Segoe UI", int(rect.height() * 0.4)))
                    label = "↻" if kind == "rotate_cw" else "↺"
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_beam(self, painter, cs) -> None:
        res = self.anim_result
        pts = [self._cell_center(c, r) for c, r in res.path[:self.anim_progress]]
        if len(pts) < 1:
            return
        # 光暈 + 核心兩層線
        if len(pts) >= 2:
            painter.setPen(QPen(C_BEAM_GLOW, cs * 0.30,
                                cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
            painter.drawPolyline(*pts)
            painter.setPen(QPen(C_BEAM_CORE, cs * 0.09,
                                cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
            painter.drawPolyline(*pts)
        # 砲口充能
        muzzle = store().image("laser_muzzle.png")
        if muzzle is not None:
            mr = QRectF(0, 0, cs * 0.9, cs * 0.9)
            mr.moveCenter(pts[0])
            painter.drawPixmap(mr, muzzle, QRectF(muzzle.rect()))
        # 轉折閃光
        glint = store().image("laser_reflect.png")
        path = res.path
        for i in range(1, min(self.anim_progress, len(path) - 1)):
            (c0, r0), (c1, r1), (c2, r2) = path[i - 1], path[i], path[i + 1]
            if (c1 - c0, r1 - r0) != (c2 - c1, r2 - r1):     # 方向改變 = 反射點
                center = self._cell_center(c1, r1)
                if glint is not None:
                    gr = QRectF(0, 0, cs * 0.6, cs * 0.6)
                    gr.moveCenter(center)
                    painter.drawPixmap(gr, glint, QRectF(glint.rect()))
                else:
                    painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
                    painter.drawEllipse(center, cs * 0.1, cs * 0.1)
        # 命中爆閃（漸放大）
        if (res.event == "hit" and self.anim_progress >= len(path)
                and self.explosion_tick > 0):
            center = self._cell_center(*path[-1])
            scale = 0.5 + 0.7 * (self.explosion_tick / EXPLOSION_TICKS)
            hit = store().image("laser_hit.png")
            if hit is not None:
                hr = QRectF(0, 0, cs * scale, cs * scale)
                hr.moveCenter(center)
                painter.drawPixmap(hr, hit, QRectF(hit.rect()))
            else:
                painter.setBrush(QColor(255, 200, 80, 200))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(center, cs * 0.4 * scale, cs * 0.4 * scale)
