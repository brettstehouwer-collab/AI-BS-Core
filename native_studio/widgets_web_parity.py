"""Universal Web-Parity Interactive Widgets for AI-BS Native Studio.

Provides Direct2D hardware-accelerated PyQt6 equivalents of the React/Tailwind
interactive cards, category filter pills, context budget bars, and collapsible
split-view headers across all 46 native subtabs.
"""

from __future__ import annotations

from typing import Callable, List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class InteractiveLaunchCard(QFrame):
    """Web-style clickable mission/tool card with hover glow and 'Click to Launch' link."""

    clicked = pyqtSignal(str, str)  # (card_id, prompt_or_action)

    def __init__(
        self,
        card_id: str,
        icon: str,
        title: str,
        description: str,
        action_payload: str,
        category: str = "All",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.card_id = card_id
        self.action_payload = action_payload
        self.category = category
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_style(hovered=False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(5)

        hdr = QLabel(f"{icon}  <b>{title}</b>")
        hdr.setStyleSheet("color: #f8fafc; font-size: 9pt; background: transparent; border: none;")
        lay.addWidget(hdr)

        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 7.8pt; line-height: 1.35; background: transparent; border: none;")
        lay.addWidget(desc, 1)

        cta = QLabel("⚡ <span style='color: #38bdf8; font-weight: bold;'>Click to Launch →</span>")
        cta.setStyleSheet("font-size: 7.8pt; background: transparent; border: none; padding-top: 2px;")
        lay.addWidget(cta)

    def _apply_style(self, hovered: bool) -> None:
        if hovered:
            self.setStyleSheet(
                "InteractiveLaunchCard {"
                "  background-color: rgba(30, 41, 59, 0.94);"
                "  border: 1px solid #38bdf8;"
                "  border-radius: 10px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "InteractiveLaunchCard {"
                "  background-color: rgba(15, 23, 42, 0.82);"
                "  border: 1px solid rgba(51, 65, 85, 0.65);"
                "  border-radius: 10px;"
                "}"
            )

    def enterEvent(self, event) -> None:
        self._apply_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style(hovered=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.card_id, self.action_payload)
        super().mousePressEvent(event)


class FilterPillBar(QWidget):
    """Web-style rounded category filter pill bar (All, Missions, Host IDE, Oversight, etc.)."""

    category_selected = pyqtSignal(str)

    def __init__(self, pills: List[Tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}
        self._active_key = pills[0][0] if pills else "All"

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addStretch()

        for key, label in pills:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, k=key: self.set_active(k))
            self._buttons[key] = btn
            lay.addWidget(btn)

        lay.addStretch()
        self.set_active(self._active_key)

    def set_active(self, key: str) -> None:
        self._active_key = key
        for k, btn in self._buttons.items():
            if k == key:
                btn.setStyleSheet(
                    "QPushButton { background: #3b82f6; color: #ffffff; border: 1px solid #60a5fa; "
                    "border-radius: 12px; padding: 4px 12px; font-size: 8pt; font-weight: bold; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: rgba(15, 23, 42, 0.85); color: #94a3b8; "
                    "border: 1px solid rgba(51, 65, 85, 0.7); border-radius: 12px; padding: 4px 12px; font-size: 8pt; }"
                    "QPushButton:hover { background: rgba(30, 41, 59, 0.95); color: #f8fafc; border-color: #38bdf8; }"
                )
        self.category_selected.emit(key)
