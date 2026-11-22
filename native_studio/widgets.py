"""Shared reusable widgets for AI-BS Native Studio."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from native_studio.theme import PALETTE, severity_color


class Card(QFrame):
    """Container card with subtle border and dark background."""

    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout_box = QVBoxLayout(self)
        self.layout_box.setContentsMargins(14, 12, 14, 14)
        self.layout_box.setSpacing(8)

        if title:
            lbl = QLabel(title.upper())
            lbl.setObjectName("CardTitle")
            self.layout_box.addWidget(lbl)

    def setContentLayout(self, layout) -> None:
        self.layout_box.addLayout(layout)

    def addWidget(self, widget: QWidget) -> None:
        self.layout_box.addWidget(widget)


class MetricCard(Card):
    """Key Performance Indicator card with large primary value and subtitle."""

    def __init__(
        self,
        title: str,
        initial: str = "--",
        subtext: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent)
        self.val_lbl = QLabel(initial)
        self.val_lbl.setStyleSheet(f"font-size: 20pt; font-weight: 700; color: {PALETTE['cyan']};")
        self.sub_lbl = QLabel(subtext)
        self.sub_lbl.setStyleSheet(f"color: {PALETTE['muted']}; font-size: 9pt;")
        self.layout_box.addWidget(self.val_lbl)
        self.layout_box.addWidget(self.sub_lbl)

    def set_value(self, text: str, color: str | None = None, sub: str | None = None) -> None:
        self.val_lbl.setText(text)
        if color:
            self.val_lbl.setStyleSheet(f"font-size: 20pt; font-weight: 700; color: {color};")
        if sub is not None:
            self.sub_lbl.setText(sub)

    def set_summary(self, text: str) -> None:
        self.sub_lbl.setText(text)


class GaugeCard(Card):
    """Metric card paired with a progress bar and high/warn threshold colors."""

    def __init__(
        self,
        title: str,
        warn_at: float = 75.0,
        crit_at: float = 90.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent)
        self.warn_at, self.crit_at = warn_at, crit_at

        hdr = QHBoxLayout()
        self.val_lbl = QLabel("--")
        self.val_lbl.setStyleSheet(f"font-size: 14pt; font-weight: 700; color: {PALETTE['cyan']};")
        self.aux_lbl = QLabel("")
        self.aux_lbl.setStyleSheet(f"color: {PALETTE['muted']}; font-size: 9pt;")
        hdr.addWidget(self.val_lbl)
        hdr.addStretch()
        hdr.addWidget(self.aux_lbl)
        self.layout_box.addLayout(hdr)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.layout_box.addWidget(self.bar)

    def set_value(self, pct: float | None, text: str | None = None, aux: str | None = None) -> None:
        if pct is None:
            self.val_lbl.setText("--")
            self.bar.setValue(0)
            return

        clamped = max(0, min(100, int(round(pct))))
        self.bar.setValue(clamped)
        color = severity_color(pct, self.warn_at, self.crit_at)
        display = text if text is not None else f"{pct:.1f}%"
        self.val_lbl.setText(display)
        self.val_lbl.setStyleSheet(f"font-size: 14pt; font-weight: 700; color: {color};")
        if aux is not None:
            self.aux_lbl.setText(aux)


class StatusBadge(QLabel):
    """Pill badge showing ONLINE / OFFLINE / STANDBY with dot indicator."""

    def __init__(self, initial_online: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_online(initial_online)

    def set_online(self, online: bool, label: str | None = None) -> None:
        if self.property("aibsVisualVariant") == "fluent":
            from ui_modernization.components.native_badge import badge_style

            text = label or ("ONLINE" if online else "OFFLINE")
            self.setText(f"● {text}")
            style_key = (bool(online), self.property("aibsDensity") == "mom")
            if getattr(self, "_aibs_badge_style_key", None) != style_key:
                self.setStyleSheet(badge_style(*style_key))
                self._aibs_badge_style_key = style_key
            return

        self._aibs_badge_style_key = None
        color = PALETTE["emerald"] if online else PALETTE["muted"]
        bg = "rgba(52, 211, 153, 0.15)" if online else "rgba(139, 155, 180, 0.12)"
        text = label or ("ONLINE" if online else "OFFLINE")
        self.setText(f"● {text}")
        self.setStyleSheet(
            f"color: {color}; background-color: {bg}; border: 1px solid {color}; "
            "border-radius: 10px; padding: 2px 8px; font-size: 8pt; font-weight: 600;"
        )


# Export web parity components
from native_studio.widgets_web_parity import FilterPillBar, InteractiveLaunchCard

