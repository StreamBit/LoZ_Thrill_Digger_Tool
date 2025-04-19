import sys, os, ctypes
from ctypes import c_int, c_float, POINTER
from PyQt5 import QtWidgets, QtGui, QtCore

# load our C++ solver DLL
dll = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "minesolver.dll"))
dll.ms_init.argtypes            = (c_int, c_int, c_int, c_int)
dll.ms_set_sample_count.argtypes= (c_int,)
dll.ms_set_cell.argtypes        = (c_int, c_int, c_int)
dll.ms_solve.argtypes           = (POINTER(c_float),)
dll.ms_solve_exact.argtypes     = (POINTER(c_float),)
dll.ms_cleanup.argtypes         = ()

class ToggleSwitch(QtWidgets.QFrame):
    """A simple on/off slide switch."""
    toggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None, width=50, height=24,
                 bg_off=QtGui.QColor("#ccc"), bg_on=QtGui.QColor("#66bb6a"),
                 circle_color=QtGui.QColor("white")):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._checked = False
        self._bg_off = bg_off
        self._bg_on = bg_on
        self._circle_color = circle_color
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()
        # background track
        p.setBrush(self._bg_on if self._checked else self._bg_off)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(r, r.height()/2, r.height()/2)
        # thumb
        diameter = r.height() - 4
        y = 2
        x = (r.width() - diameter - 2) if self._checked else 2
        thumb = QtCore.QRectF(x, y, diameter, diameter)
        p.setBrush(self._circle_color)
        p.drawEllipse(thumb)
        p.end()

    def isChecked(self):
        return self._checked

class HighlightDelegate(QtWidgets.QStyledItemDelegate):
    """Draws a red border around the two safest cells."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if (index.row(), index.column()) in self.parent.best_moves:
            painter.save()
            pen = QtGui.QPen(QtGui.QColor(255, 0, 0), 3)
            painter.setPen(pen)
            painter.drawRect(option.rect.adjusted(1,1,-1,-1))
            painter.restore()

class MinesweeperSolver(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LoZ_ThrillDiggerTool")

        # board configurations: (rows, cols, bombs)
        self.mode_cfg = {
            "Easy":         (4, 5, 4),
            "Intermediate": (5, 6, 8),
            "Expert":       (5, 8,16),
        }
        # default Monte Carlo samples
        self.sample_count = 250_000

        # dropdown choices
        self.items = [
            "Green   (0 nearby)",
            "Blue    (1–2 nearby)",
            "Red     (3–4 nearby)",
            "Silver  (5–6 nearby)",
            "Gold    (7–8 nearby)",
            "Bomb    (revealed)",
            "C", #Clear - return to unknown state
        ]

        # — Toolbar: mode selector, reset, bombs-left, help —
        top = QtWidgets.QHBoxLayout()
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(self.mode_cfg.keys())
        self.mode_combo.currentTextChanged.connect(self.new_board)
        top.addWidget(QtWidgets.QLabel("Mode:"))
        top.addWidget(self.mode_combo)

        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_board)
        top.addWidget(self.reset_btn)

        self.bombs_left_label = QtWidgets.QLabel("")
        top.addWidget(self.bombs_left_label)

        self.help_btn = QtWidgets.QPushButton("How to")
        self.help_btn.setToolTip("Show usage instructions")
        self.help_btn.clicked.connect(self.show_usage_dialog)
        top.addWidget(self.help_btn)

        top.addStretch()

        # — Table & highlighting delegate —
        self.table = QtWidgets.QTableWidget()
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.setItemDelegate(HighlightDelegate(self))

        # — Exact vs Monte Carlo switch, sample spinbox, and Info button —
        self.exact_switch = ToggleSwitch()
        self.exact_switch.toggled.connect(self.on_exact_toggled)
        switch_label = QtWidgets.QLabel("Exact Solver Mode:")

        self.sample_spin = QtWidgets.QSpinBox()
        self.sample_spin.setRange(10_000, 10_000_000)
        self.sample_spin.setSingleStep(10_000)
        self.sample_spin.setValue(self.sample_count)
        self.sample_spin.valueChanged.connect(self.on_samples_changed)

        self.info_btn = QtWidgets.QPushButton("info")
        self.info_btn.setToolTip("Explain solver modes and sample count")
        self.info_btn.clicked.connect(self.show_info_dialog)

        sw_layout = QtWidgets.QHBoxLayout()
        sw_layout.addWidget(switch_label)
        sw_layout.addWidget(self.exact_switch)
        sw_layout.addSpacing(20)
        sw_layout.addWidget(QtWidgets.QLabel("Monte Carlo Samples:"))
        sw_layout.addWidget(self.sample_spin)
        sw_layout.addWidget(self.info_btn)
        sw_layout.addStretch()

        # — Main layout assembly —
        main = QtWidgets.QVBoxLayout(self)
        main.addLayout(top)
        main.addWidget(self.table)
        main.addLayout(sw_layout)

        # create colored‐dot icons & brushes
        self._make_dot_icons()

        # initialize first board
        self.new_board(self.mode_combo.currentText())

    def _make_dot_icons(self):
        colors = [
            QtGui.QColor(  0,255,   0),  # green
            QtGui.QColor(  0,  0, 255),  # blue
            QtGui.QColor(255,   0,   0),  # red
            QtGui.QColor(192, 192, 192),  # silver
            QtGui.QColor(255, 215,   0),  # gold
            QtGui.QColor( 80,  80,  80),  # bomb
        ]
        size = 24
        self.dot_icons = []
        self.text_brushes = []
        for col in colors:
            pix = QtGui.QPixmap(size, size)
            pix.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pix)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setBrush(col)
            painter.setPen(QtCore.Qt.NoPen)
            r = size//2 - 2
            painter.drawEllipse(QtCore.QPoint(size//2, size//2), r, r)
            painter.end()
            self.dot_icons.append(QtGui.QIcon(pix))
            self.text_brushes.append(QtGui.QBrush(col))

    def new_board(self, mode):
        dll.ms_cleanup()
        self.rows, self.cols, self.bombs = self.mode_cfg[mode]
        dll.ms_init(self.rows, self.cols, self.bombs, self.sample_count)
        self.revealed = [[-1]*self.cols for _ in range(self.rows)]
        self.best_moves = []

        self.table.clear()
        self.table.setRowCount(self.rows)
        self.table.setColumnCount(self.cols)
        for r in range(self.rows):
            for c in range(self.cols):
                itm = QtWidgets.QTableWidgetItem("")
                itm.setTextAlignment(QtCore.Qt.AlignCenter)
                self.table.setItem(r, c, itm)

        self.update_probs()

    def reset_board(self):
        self.new_board(self.mode_combo.currentText())

    def on_exact_toggled(self, enabled):
        self.sample_spin.setEnabled(not enabled)
        dll.ms_set_sample_count(self.sample_spin.value())
        self.update_probs()

    def on_samples_changed(self, v):
        self.sample_count = v
        dll.ms_set_sample_count(v)
        if not self.exact_switch.isChecked():
            self.update_probs()

    def show_usage_dialog(self):
        QtWidgets.QMessageBox.information(
            self, "How to Use LoZ Thrill Digger Tool",
            "<b>Usage Instructions:</b><ul>"
            "<li>Select the board mode (Easy, Intermediate, Expert).</li>"
            "<li>Use the Reset button to start a fresh board.</li>"
            "<li>Click any cell to enter its revealed value or mark a bomb.</li>"
            "<li>Unrevealed cells display live bomb‐probabilities.</li>"
            "<li>Red borders highlight the two safest moves.</li>"
            "<li>Toggle Exact mode to switch between enumeration and Monte Carlo.</li>"
            "<li>Adjust the Monte Carlo sample count for speed vs. accuracy.</li>"
            "</ul>"
        )

    def show_info_dialog(self):
        QtWidgets.QMessageBox.information(
            self, "Solver Modes & Samples",
            "<b>Exact Solver Mode</b><br>"
            "When ON, the solver enumerates <i>all</i> valid bomb placements for "
            "100%‑accurate probabilities (fast on small boards, but slows down considerably as board size increases).<br><br>"
            "<b>Monte Carlo Samples</b><br>"
            "When Exact mode is OFF, the solver runs a Monte Carlo simulation "
            "using the sample count below. Increasing samples reduces noise but "
            "increases compute time.<br><br>"
            "If you don't know what sample size to choose, the default of <u>250,000 samples</u> is a good sweet spot (~0.1 % error vs. speed)."
        )

    def on_cell_clicked(self, r, c):
        combo = QtWidgets.QComboBox(self.table)
        for i, txt in enumerate(self.items):
            combo.addItem(txt)
            if i < len(self.dot_icons):
                combo.setItemIcon(i, self.dot_icons[i])
                combo.setItemData(i, self.text_brushes[i], QtCore.Qt.ForegroundRole)
        cur = self.revealed[r][c]
        combo.setCurrentIndex(cur if cur >= 0 else len(self.items)-1)
        self.table.setCellWidget(r, c, combo)
        combo.showPopup()
        combo.activated.connect(lambda idx, rr=r, cc=c: self._finish_combo(rr, cc, idx))

    def _finish_combo(self, r, c, idx):
        val = idx if idx < len(self.items)-1 else -1
        self.revealed[r][c] = val
        dll.ms_set_cell(r, c, val)
        self.table.removeCellWidget(r, c)
        self.update_probs()

    def update_probs(self):
        # update bombs-remaining label
        flagged = sum(v==5 for row in self.revealed for v in row)
        self.bombs_left_label.setText(f"Bombs left: {self.bombs-flagged}")

        # blank-board shortcut when using Monte Carlo
        flat = sum(self.revealed, [])
        if all(v==-1 for v in flat) and not self.exact_switch.isChecked():
            uniform = self.bombs / (self.rows * self.cols)
            for r in range(self.rows):
                for c in range(self.cols):
                    itm = self.table.item(r, c)
                    itm.setText(f"{int(uniform*100)}%")
                    itm.setIcon(QtGui.QIcon())
                    hue = (1-uniform)*120
                    itm.setBackground(QtGui.QColor.fromHsvF(hue/360,1,1))
            self.best_moves = []
            self.table.viewport().update()
            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            return

        # solve
        N = self.rows * self.cols
        arr = (c_float * N)()
        if self.exact_switch.isChecked():
            dll.ms_solve_exact(arr)
        else:
            dll.ms_solve(arr)

        # fill grid and collect options
        candidates = []
        for r in range(self.rows):
            for c in range(self.cols):
                itm = self.table.item(r, c)
                v = self.revealed[r][c]
                if v != -1:
                    itm.setText(""); itm.setIcon(self.dot_icons[v])
                    itm.setBackground(QtGui.QColor("white"))
                else:
                    p = arr[r*self.cols + c]
                    itm.setText(f"{int(p*100)}%"); itm.setIcon(QtGui.QIcon())
                    hue = (1-p)*120
                    itm.setBackground(QtGui.QColor.fromHsvF(hue/360,1,1))
                    candidates.append((p, (r,c)))

        # highlight two safest
        candidates.sort(key=lambda x: x[0])
        self.best_moves = [pos for _, pos in candidates[:2]]
        self.table.viewport().update()
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def closeEvent(self, e):
        dll.ms_cleanup()
        super().closeEvent(e)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    solver = MinesweeperSolver()
    solver.show()
    sys.exit(app.exec_())
