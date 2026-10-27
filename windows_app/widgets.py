"""مكوّنات واجهة صغيرة قابلة لإعادة الاستخدام في سراج."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
    QWidgetItem,
)


class FlowLayout(QLayout):
    """تخطيط يلف الأدوات تلقائيًا عند تصغير النافذة مثل شريط أوامر حديث."""

    def __init__(self, parent=None, margin=0, h_spacing=8, v_spacing=8):
        super().__init__(parent)
        self._items = []
        self._h_space = h_spacing
        self._v_space = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.takeAt(0):
            pass

    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def addWidget(self, widget):  # noqa: N802
        self.addChildWidget(widget)
        self.addItem(QWidgetItem(widget))

    def count(self):
        return len(self._items)

    def itemAt(self, index):  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        return self._layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._layout(rect, test_only=False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _layout(self, rect, test_only=False):
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        parent = self.parentWidget()
        rtl = bool(parent and parent.layoutDirection() == Qt.LayoutDirection.RightToLeft)
        x = effective.right() + 1 if rtl else effective.x()
        y, line_height = effective.y(), 0
        for item in self._items:
            widget = item.widget()
            # isVisible() يكون False قبل إظهار النافذة كلها؛ نتجاهل فقط ما أُخفي صراحةً.
            if widget is not None and widget.isHidden():
                continue
            hint = item.sizeHint()
            if rtl:
                item_x = x - hint.width()
                if line_height and item_x < effective.left():
                    x = effective.right() + 1
                    y += line_height + self._v_space
                    item_x = x - hint.width()
                    line_height = 0
                if not test_only:
                    item.setGeometry(QRect(QPoint(item_x, y), hint))
                x = item_x - self._h_space
            else:
                next_x = x + hint.width() + self._h_space
                if line_height and next_x - self._h_space > effective.right() + 1:
                    x = effective.x()
                    y += line_height + self._v_space
                    next_x = x + hint.width() + self._h_space
                    line_height = 0
                if not test_only:
                    item.setGeometry(QRect(QPoint(x, y), hint))
                x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


class IndexPopup(QFrame):
    """فهرس منسدل لا يحجز مساحة دائمة من صفحة المصحف."""

    def __init__(self, surahs, juz_count, arabic_number, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("indexPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(390)
        self.setMaximumWidth(520)
        outer = QGridLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setHorizontalSpacing(10)
        outer.setVerticalSpacing(7)

        title = QLabel("الفهرس والانتقال السريع")
        title.setObjectName("popupTitle")
        close = QPushButton("×")
        close.setObjectName("iconButton")
        close.setFixedSize(34, 32)
        close.clicked.connect(self.hide)
        header = QHBoxLayout()
        header.addWidget(title, 1)
        header.addWidget(close)
        outer.addLayout(header, 0, 0, 1, 3)

        self.combo_surah = QComboBox()
        self.combo_surah.setObjectName("indexCombo")
        self.combo_surah.setEditable(True)
        self.combo_surah.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for surah in surahs:
            self.combo_surah.addItem(f'{surah["number"]}. {surah["name"]}', surah["number"])
        if self.combo_surah.completer():
            self.combo_surah.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.combo_surah.completer().setFilterMode(Qt.MatchFlag.MatchContains)

        self.combo_juz = QComboBox()
        self.combo_juz.setObjectName("indexCombo")
        for index in range(juz_count):
            self.combo_juz.addItem(f"الجزء {arabic_number(index + 1)}", index)

        self.combo_ayah = QComboBox()
        self.combo_ayah.setObjectName("indexCombo")

        for col, (label, combo) in enumerate(
            (("السورة", self.combo_surah), ("الجزء", self.combo_juz), ("الآية", self.combo_ayah))
        ):
            text = QLabel(label)
            text.setObjectName("muted")
            outer.addWidget(text, 1, col)
            combo.setMinimumWidth(105 if col else 170)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            outer.addWidget(combo, 2, col)

    def show_below(self, button: QWidget):
        window = button.window()
        available = window.screen().availableGeometry() if window.screen() else window.geometry()
        width = min(520, max(360, window.width() - 48))
        self.resize(width, self.sizeHint().height())
        anchor = button.mapToGlobal(QPoint(button.width(), button.height() + 6))
        x = anchor.x() - self.width()
        y = anchor.y()
        if x < available.left() + 8:
            x = available.left() + 8
        if x + self.width() > available.right() - 8:
            x = available.right() - self.width() - 8
        if y + self.height() > available.bottom() - 8:
            y = button.mapToGlobal(QPoint(0, -self.height() - 6)).y()
        self.move(x, y)
        self.show()
        self.raise_()
        self.combo_surah.setFocus()
