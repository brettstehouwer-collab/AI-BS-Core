"""Theatrical Lexicon Engine Dashboard View for AI-BS Native Studio (Subtab: lexicon_dashboard).

1:1 visual & functional parity with LexiconTheatricalDashboard.jsx:
- Semantic Expansion Simulator (Live Stream Simulator input & enrichment analysis)
- Expansion Map with visual word badges, synonym sets, and persona trigger weights
- Raw Lexicon Lookup with instant local search
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE


LOCAL_LEXICON_VAULT: Dict[str, List[str]] = {
    "synergize": ["coordinate", "harmonize", "synchronize", "integrate", "cooperate"],
    "paradigm": ["model", "archetype", "framework", "standard", "prototype"],
    "optimal": ["peak", "supreme", "flawless", "consummate", "unrivaled"],
    "roi": ["yield", "dividends", "capital return", "margin", "surplus"],
    "sovereign": ["autonomous", "independent", "unrestricted", "self-governing", "absolute"],
    "matrix": ["network", "lattice", "grid", "topology", "infrastructure"],
    "telemetry": ["surveillance", "metrics", "diagnostics", "readouts", "auditing"],
    "screenplay": ["script", "manuscript", "libretto", "teleplay", "scenario"],
    "theater": ["stage", "arena", "coliseum", "amphitheater", "proscenium"],
    "apex": ["pinnacle", "zenith", "summit", "acme", "crest"],
}


class LexiconNativeView(QWidget):
    """Theatrical Lexicon Engine Dashboard View."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: #070b12;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # 1. Header Bar
        hdr = QFrame()
        hdr.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 12px;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(8, 6, 8, 6)

        title = QLabel("🎭  Theatrical Lexicon Engine & <span style='color: #38bdf8;'>Persona Triggers</span>")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #f8fafc;")
        h_lay.addWidget(title)
        h_lay.addStretch()

        badge = QLabel("REAL-TIME SEMANTIC EXPANSION ACTIVE")
        badge.setStyleSheet("background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid #7e22ce; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 8pt;")
        h_lay.addWidget(badge)
        layout.addWidget(hdr)

        # 2. Main Two-Column Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1e293b; width: 2px; }")

        # Left Column: Semantic Expansion Simulator
        left_card = QFrame()
        left_card.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 14px;")
        l_lay = QVBoxLayout(left_card)
        l_lay.setContentsMargins(10, 8, 10, 8)
        l_lay.setSpacing(10)

        l_lay.addWidget(QLabel("💬 <b>Semantic Expansion (Live Stream Simulator)</b>"))

        self.txt_input = QTextEdit("We need to synergize our paradigms for optimal ROI.")
        self.txt_input.setFixedHeight(75)
        self.txt_input.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 8px; border-radius: 4px; font-size: 9pt;")
        l_lay.addWidget(self.txt_input)

        btn_row = QHBoxLayout()
        self.btn_enrich = QPushButton("✨ Enrich & Expand Semantics")
        self.btn_enrich.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981); color: #ffffff; border-radius: 4px; padding: 8px 18px; font-weight: bold; font-size: 8.5pt; }"
            "QPushButton:hover { background: #059669; }"
        )
        self.btn_enrich.clicked.connect(self._enrich_text)
        btn_row.addWidget(self.btn_enrich)
        btn_row.addStretch()
        l_lay.addLayout(btn_row)

        # Analyzed Output Card
        self.output_card = QFrame()
        self.output_card.setStyleSheet("background: #070b12; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        self.oc_lay = QVBoxLayout(self.output_card)
        self.oc_lay.setSpacing(8)

        self.lbl_orig = QLabel("Original Text: <i>We need to synergize our paradigms for optimal ROI.</i>")
        self.lbl_orig.setStyleSheet("color: #94a3b8; font-size: 8pt;")
        self.oc_lay.addWidget(self.lbl_orig)

        self.oc_lay.addWidget(QLabel("<b>Analyzed Expansion Map:</b>"))

        self.expansion_cards_lay = QVBoxLayout()
        self.expansion_cards_lay.setSpacing(6)
        self.oc_lay.addLayout(self.expansion_cards_lay)

        l_lay.addWidget(self.output_card)
        l_lay.addStretch()
        splitter.addWidget(left_card)

        # Right Column: Raw Lexicon Lookup
        right_card = QFrame()
        right_card.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 14px;")
        r_lay = QVBoxLayout(right_card)
        r_lay.setContentsMargins(10, 8, 10, 8)
        r_lay.setSpacing(10)

        r_lay.addWidget(QLabel("🔍 <b>Raw Lexicon Lookup</b>"))

        # Search bar
        s_row = QHBoxLayout()
        self.txt_word = QLineEdit("synergize")
        self.txt_word.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        self.txt_word.returnPressed.connect(self._lookup_word)
        s_row.addWidget(self.txt_word, 1)

        btn_lookup = QPushButton("Lookup")
        btn_lookup.setStyleSheet("background: #2563eb; color: #ffffff; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 8pt;")
        btn_lookup.clicked.connect(self._lookup_word)
        s_row.addWidget(btn_lookup)
        r_lay.addLayout(s_row)

        # Lookup result card
        self.lookup_res_card = QFrame()
        self.lookup_res_card.setStyleSheet("background: #070b12; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        lrc_lay = QVBoxLayout(self.lookup_res_card)
        lrc_lay.setSpacing(4)

        self.lbl_lookup_word = QLabel("Word: <b>synergize</b>")
        self.lbl_lookup_word.setStyleSheet("color: #38bdf8; font-size: 9pt;")
        lrc_lay.addWidget(self.lbl_lookup_word)

        self.lbl_lookup_syns = QLabel("Synonyms in Vault:\n• coordinate\n• harmonize\n• synchronize\n• integrate\n• cooperate")
        self.lbl_lookup_syns.setStyleSheet("color: #cbd5e1; font-family: monospace; font-size: 8pt; line-height: 1.4;")
        lrc_lay.addWidget(self.lbl_lookup_syns)
        r_lay.addWidget(self.lookup_res_card)

        r_lay.addStretch()
        splitter.addWidget(right_card)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)

        layout.addWidget(splitter, 1)

        scroll.setWidget(container)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

        # Seed initial expansion
        self._enrich_text()

    def _enrich_text(self) -> None:
        text = self.txt_input.toPlainText().strip()
        self.lbl_orig.setText(f"Original Text: <i>{text}</i>")

        # Clear existing expansion cards
        while self.expansion_cards_lay.count():
            item = self.expansion_cards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Tokenize and match against local lexicon vault
        words = re.findall(r"\b\w+\b", text.lower())
        hits = 0
        for w in words:
            if w in LOCAL_LEXICON_VAULT:
                hits += 1
                card = QFrame()
                card.setStyleSheet("background: #090d14; border: 1px solid #334155; border-left: 3px solid #ec4899; border-radius: 4px; padding: 6px 10px;")
                c_lay = QHBoxLayout(card)
                c_lay.setContentsMargins(4, 2, 4, 2)

                lbl_w = QLabel(f"<b>{w.upper()}</b>")
                lbl_w.setStyleSheet("color: #ec4899; font-size: 8.5pt;")
                c_lay.addWidget(lbl_w)

                syns = ", ".join(LOCAL_LEXICON_VAULT[w])
                lbl_s = QLabel(f"Synonyms: <span style='color: #38bdf8;'>{syns}</span>")
                lbl_s.setStyleSheet("color: #94a3b8; font-size: 8pt;")
                c_lay.addWidget(lbl_s)
                c_lay.addStretch()

                self.expansion_cards_lay.addWidget(card)

        if hits == 0:
            lbl_none = QLabel("No specific high-theatrical triggers found. Try adding words like 'synergize', 'paradigm', 'optimal', 'sovereign'.")
            lbl_none.setStyleSheet("color: #64748b; font-size: 8pt; font-style: italic;")
            self.expansion_cards_lay.addWidget(lbl_none)

    def _lookup_word(self) -> None:
        word = self.txt_word.text().strip().lower()
        self.lbl_lookup_word.setText(f"Word: <b>{word}</b>")
        if word in LOCAL_LEXICON_VAULT:
            syns = "\n".join(f"• {s}" for s in LOCAL_LEXICON_VAULT[word])
            self.lbl_lookup_syns.setText(f"Synonyms in Vault:\n{syns}")
            self.lbl_lookup_syns.setStyleSheet("color: #cbd5e1; font-family: monospace; font-size: 8pt; line-height: 1.4;")
        else:
            self.lbl_lookup_syns.setText(f"No entry found in Lexicon Vault for '{word}'. Available words:\n" + ", ".join(LOCAL_LEXICON_VAULT.keys()))
            self.lbl_lookup_syns.setStyleSheet("color: #64748b; font-size: 8pt; font-style: italic;")


