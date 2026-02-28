"""Custom Qt widgets for SP Workshop."""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen


class OutlinedLabel(QLabel):
    """QLabel with text outline effect."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = self.font()
        painter.setFont(font)
        text = self.text()
        pen = QPen(Qt.black, 2, Qt.SolidLine)
        painter.setPen(pen)
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dx, dy in offsets:
            painter.drawText(self.rect().adjusted(dx, dy, dx, dy), Qt.AlignCenter, text)
        pen.setColor(Qt.white)
        painter.setPen(pen)
        painter.drawText(self.rect(), Qt.AlignCenter, text)
