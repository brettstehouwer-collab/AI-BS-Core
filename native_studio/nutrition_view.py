"""Clinical Nutrition & Detox Engine View for AI-BS Native Studio (Subtab: nutrition_subsystem).

1:1 visual & functional parity with NutritionSubsystemLedger.jsx:
- Complete 6-Section Clinical Protocol:
  1. Daily Juice Schedule & Hybrid Formulations (5 Servings/Day Table)
  2. 14-Day Inventory Consolidation & Staggered Requisition (Field Stocks & Fruit Stocks)
  3. Extraction Mechanics & Equipment SOP (Sterilization, Comminution, Mastication, Emulsification)
  4. Ketogenic Compensatory Snack Protocols (<3g Net Carbs Table)
  5. High-Satiety Ketogenic Meal Blueprints (Wild Sockeye Filet & Basted Ribeye)
  6. Stepped Refeeding & Metabolic Phase-Shift (Days 15-18 Protocol & Daily Electrolytes)
- 1-Click Copy Protocol JSON Payload Engine
"""

from __future__ import annotations

import json
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE


RAW_PROTOCOL_PAYLOAD = {
    "system_target": "Clinical Juice and Keto Subsystem",
    "protocol_duration_days": 14,
    "refeeding_duration_days": 4,
    "hydration_base_total_cucumbers": 70,
    "hydration_base_total_celery_bunches": 32,
    "core_antioxidants": [
        "cyanidin-3-glucoside",
        "punicalagins",
        "betalains",
        "bromelain",
        "hesperidin",
        "naringin",
    ],
    "viscosity_agents": [
        "organic_psyllium_husk",
        "milled_chia_seed",
        "acacia_senegal_gum",
    ],
    "ketogenic_macronutrient_ratios": {
        "fat_percentage": 75,
        "protein_percentage": 20,
        "carbohydrate_net_percentage": 5,
    },
    "electrolytes_target_mg_daily": {
        "elemental_sodium": 5000,
        "elemental_potassium": 1000,
        "elemental_magnesium": 300,
    },
}

JUICE_SCHEDULE = [
    ("07:30", "Anthocyanin Green Ignition", "1 English cucumber, 2 stalks Tuscan kale, 1 rib celery, 1/2 lemon", "1/2 cup wild blueberries, 1/4 cup blackberries, 1 tbsp milled chia", "Cyanidin-3-glucoside, chlorophyll, lutein; lipid-delayed fructose entry", "#38bdf8"),
    ("10:30", "Betalain & Nitric Surge", "1 red beet, 2 carrots, 1 in ginger root, 1 in turmeric root", "1/2 cup pomegranate arils, 1/2 cup red grapes, 1 tsp psyllium husk, cracked pepper", "Punicalagins, betanin, eNOS activation, piperine-assisted curcuminoid transport", "#ec4899"),
    ("13:30", "Cruciferous Proteolytic Shield", "1/4 green cabbage head, 1 cup baby spinach, 1 English cucumber, 1 lime", "3/4 cup fresh pineapple (core intact), 2 tbsp virgin cucumber pulp", "Sulforaphane precursors, glucosinolates, proteolytic bromelain isolation", "#10b981"),
    ("16:30", "Bioflavonoid Osmolyte Matrix", "1 ruby red grapefruit, 1/2 fennel bulb, 1 English cucumber", "1 blood orange (albedo pith retained), 1/3 cup diced mango, 5g acacia fiber", "Hesperidin, naringin, provitamin A carotenoids, cecal butyrate fuel", "#f59e0b"),
    ("19:30", "Nocturnal Mineral Restorative", "1 bunch Swiss chard, 1 English cucumber, 1/2 cup mint leaves, 1/2 lemon", "1/2 cup pitted tart cherries, 1 pinch pink Himalayan salt", "Proanthocyanidins, exogenous melatonin, baseline Na+/K+ replenishment", "#a855f7"),
]

KETO_SNACKS = [
    ("Avocado-MCT Salt Pod", "1 medium Hass Avocado, 1 tbsp Pure C8 MCT Oil, coarse sea salt, black pepper", "Bisect pericarp, remove seed, inject C8 oil into cavity, top with 1g NaCl. Eat with spoon.", "28g Fat | 3g Protein | 2g Net Carb"),
    ("Crisped Parmesan Seed Discs", "1 cup aged Parmesan (micro-planed), 2 tbsp raw pepitas, 1 tbsp chia, 1/4 tsp smoked paprika", "Form 50mm circles on parchment. Heat at 375°F (190°C) for 420s until maillard reactions appear. Cool 300s.", "18g Fat | 14g Protein | 1g Net Carb"),
    ("Macadamia Cacao Fat Cluster", "1/2 cup Macadamia nut paste, 2 tbsp virgin coconut oil, 1 tbsp unsweetened cacao nibs", "Liquefy coconut oil, fold into paste with salt, transfer to silicone matrix, top with nibs, flash-freeze 1200s.", "22g Fat | 2g Protein | 1.5g Net Carb"),
]


class NutritionNativeView(QWidget):
    """Clinical Nutrition & Detox Engine View matching NutritionSubsystemLedger.jsx."""

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
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # 1. Header Bar
        hdr = QFrame()
        hdr.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 8px 14px;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(4, 4, 4, 4)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("🥗 Clinical Nutrition & <span style='color: #10b981;'>Detox Subsystem Ledger</span>")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #f8fafc;")
        sub = QLabel("Hybrid Cold-Press Mechanical Extraction • Whole Pigment Blender Suspension • Ketogenic Phase Shift")
        sub.setStyleSheet("font-size: 8pt; color: #8b949e;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        h_lay.addLayout(title_box)
        h_lay.addStretch()

        self.btn_copy_payload = QPushButton("📋 Copy Protocol JSON Payload")
        self.btn_copy_payload.setStyleSheet(
            "background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; border-radius: 6px; padding: 7px 16px; font-weight: bold; font-size: 8pt;"
        )
        self.btn_copy_payload.clicked.connect(self._copy_payload)
        h_lay.addWidget(self.btn_copy_payload)

        layout.addWidget(hdr)

        # 2. Workflow Banner
        wf_banner = QFrame()
        wf_banner.setStyleSheet("background: #1a1608; border: 1px solid #78350f; border-radius: 6px; padding: 8px 14px;")
        wf_lay = QHBoxLayout(wf_banner)
        wf_lbl = QLabel(
            "⚠️ <b>ENGINE WORKFLOW:</b> Masticate base (40-80 RPM) ➔ Transfer liquid to blender carafe ➔ Introduce whole pigments + functional fiber ➔ Pulse 25s ➔ Consume &lt;300s."
        )
        wf_lbl.setStyleSheet("color: #f59e0b; font-size: 8pt;")
        wf_lay.addWidget(wf_lbl)
        layout.addWidget(wf_banner)

        # 3. Section 1: Daily Juice Schedule Table
        sec1 = QFrame()
        sec1.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        s1_lay = QVBoxLayout(sec1)
        s1_lay.setContentsMargins(6, 6, 6, 6)
        s1_lay.setSpacing(8)

        s1_hdr = QHBoxLayout()
        s1_title = QLabel("1. <b>DAILY JUICE SCHEDULE & HYBRID FORMULATIONS</b>")
        s1_title.setStyleSheet("font-size: 9pt; color: #f1f5f9;")
        s1_badge = QLabel("5 Servings / Day")
        s1_badge.setStyleSheet("background: rgba(56, 189, 248, 0.15); color: #38bdf8; border-radius: 4px; padding: 2px 8px; font-size: 7.5pt; font-weight: bold;")
        s1_hdr.addWidget(s1_title)
        s1_hdr.addStretch()
        s1_hdr.addWidget(s1_badge)
        s1_lay.addLayout(s1_hdr)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Time", "Designation", "Cold-Press Mechanical Base", "Blender Suspension", "Biochemical Target"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        table.setFixedHeight(220)
        table.setStyleSheet(
            "QTableWidget { background: #05080f; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; font-size: 8pt; }"
            "QHeaderView::section { background: #0f141f; color: #94a3b8; font-weight: bold; border: 1px solid #1e293b; padding: 5px; }"
        )

        table.setRowCount(len(JUICE_SCHEDULE))
        for i, (t_time, desig, base, susp, target, color) in enumerate(JUICE_SCHEDULE):
            t_item = QTableWidgetItem(t_time)
            t_item.setForeground(QColor(color))
            t_item.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            d_item = QTableWidgetItem(desig)
            d_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            table.setItem(i, 0, t_item)
            table.setItem(i, 1, d_item)
            table.setItem(i, 2, QTableWidgetItem(base))
            table.setItem(i, 3, QTableWidgetItem(susp))
            table.setItem(i, 4, QTableWidgetItem(target))

        s1_lay.addWidget(table)
        layout.addWidget(sec1)

        # 4. Section 2: 14-Day Inventory Logistics
        sec2 = QFrame()
        sec2.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        s2_lay = QVBoxLayout(sec2)
        s2_lay.setContentsMargins(6, 6, 6, 6)
        s2_lay.setSpacing(8)

        s2_hdr = QHBoxLayout()
        s2_title = QLabel("2. <b>14-DAY INVENTORY CONSOLIDATION & STAGGERED REQUISITION</b>")
        s2_title.setStyleSheet("font-size: 9pt; color: #f1f5f9;")
        s2_badge = QLabel("4 Grocery Cadences (Day 1, 4, 8, 11)")
        s2_badge.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #10b981; border-radius: 4px; padding: 2px 8px; font-size: 7.5pt; font-weight: bold;")
        s2_hdr.addWidget(s2_title)
        s2_hdr.addStretch()
        s2_hdr.addWidget(s2_badge)
        s2_lay.addLayout(s2_hdr)

        grid2 = QGridLayout()
        grid2.setSpacing(10)

        c1 = self._build_info_card("🍏 Perishable Produce: Field Stocks", [
            "• English Cucumbers: 70 units (5 / day)",
            "• Celery: 32 bunches (~9 ribs / day)",
            "• Tuscan (Lacinato) Kale: 8 bunches",
            "• Swiss Chard: 14 bunches (1 bunch / day)",
            "• Dandelion Greens: 7 bunches (1 cup / day)",
            "• Baby Spinach: 14 cups (~4 large 16oz tubs)",
            "• Red Cabbage: 3 medium heads | Green Cabbage: 2 heads",
            "• Fennel Bulbs: 7 medium bulbs | Red Beets: 14 units",
            "• Carrots: 42 medium (~10-12 lbs)",
            "• Ginger Root: ~2.0 lbs bulk | Turmeric Root: ~1.5 lbs bulk",
        ], "#10b981")

        c2 = self._build_info_card("🌾 Fruit Stocks & Viscosity Agents", [
            "• Meyer Lemons: 35 units | Limes: 14 units",
            "• Grapefruits: 14 units | Blood Oranges: 14 units",
            "• Whole Pineapples: 4 units (cores utilized)",
            "• Pomegranates: 14 units (or 7 lbs arils)",
            "• Wild Blueberries (Frozen): 7 lbs | Blackberries: 7 half-pints",
            "• Dark Tart Cherries (Frozen, Pitted): 7 lbs",
            "• Milled Organic Chia Seeds: 1 lb bag",
            "• Organic Psyllium Husk (Whole): 1 lb container",
            "• Acacia Senegal Gum Fiber / Inulin: 250g powder",
            "• Distilled White Vinegar: 2 gallons (Wash Base)",
        ], "#38bdf8")

        grid2.addWidget(c1, 0, 0)
        grid2.addWidget(c2, 0, 1)
        s2_lay.addLayout(grid2)
        layout.addWidget(sec2)

        # 5. Section 3: Extraction Mechanics & Equipment SOP
        sec3 = QFrame()
        sec3.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        s3_lay = QVBoxLayout(sec3)
        s3_lay.setContentsMargins(6, 6, 6, 6)
        s3_lay.setSpacing(8)

        s3_title = QLabel("3. <b>EXTRACTION MECHANICS & EQUIPMENT SOP (Cold-Press & Shear)</b>")
        s3_title.setStyleSheet("font-size: 9pt; color: #f1f5f9;")
        s3_lay.addWidget(s3_title)

        s3_grid = QGridLayout()
        s3_grid.setSpacing(8)

        sop_steps = [
            ("STEP 01: STERILIZATION", "Submerge inventory in a 1:4 acetic acid (white vinegar) solution for 600s to degrade agrochemicals. Retain epidermal layer on carrots/beets/cucumbers. Remove citrus flavedo to eliminate bitterness, retain internal albedo pith.", "#f59e0b"),
            ("STEP 02: COMMINUTION", "Section fibrous stalks (celery, kale stems) into <50mm cross-sections to eliminate long fibers tangling the auger axis. Slice roots into uniform 25mm cubes.", "#38bdf8"),
            ("STEP 03: SLOW MASTICATION", "Run auger at 40-80 RPM. Feed sequence: 20% cucumber volume (lubricate screen) ➔ dense greens/roots ➔ 80% remaining high-water volume. Collect liquid yield.", "#10b981"),
            ("STEP 04: EMULSIFICATION", "Deposit cold-press extract into blender carafe. Add whole fruit fractions and dry fiber (chia/psyllium/acacia). Pulse 25s at medium velocity. Consume <300s prior to gelation.", "#ec4899"),
        ]

        for s_idx, (s_head, s_text, s_col) in enumerate(sop_steps):
            sc = QFrame()
            sc.setStyleSheet(f"background: #070b14; border: 1px solid #1e293b; border-left: 3px solid {s_col}; border-radius: 6px; padding: 8px;")
            s_l = QVBoxLayout(sc)
            s_l.setContentsMargins(4, 2, 4, 2)
            lbl_h = QLabel(f"<b>[{s_head}]</b>")
            lbl_h.setStyleSheet(f"color: {s_col}; font-size: 8pt; font-family: monospace;")
            lbl_t = QLabel(s_text)
            lbl_t.setStyleSheet("color: #cbd5e1; font-size: 7.5pt;")
            lbl_t.setWordWrap(True)
            s_l.addWidget(lbl_h)
            s_l.addWidget(lbl_t)
            s3_grid.addWidget(sc, s_idx // 2, s_idx % 2)

        s3_lay.addLayout(s3_grid)
        layout.addWidget(sec3)

        # 6. Section 4: Ketogenic Compensatory Snacks (<3g Net Carbs)
        sec4 = QFrame()
        sec4.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        s4_lay = QVBoxLayout(sec4)
        s4_lay.setContentsMargins(6, 6, 6, 6)
        s4_lay.setSpacing(8)

        s4_hdr = QHBoxLayout()
        s4_title = QLabel("4. <b>KETOGENIC COMPENSATORY SNACK PROTOCOLS (&lt;3g NET CARBS)</b>")
        s4_title.setStyleSheet("font-size: 9pt; color: #f1f5f9;")
        s4_badge = QLabel("&lt;3g Net Carbs")
        s4_badge.setStyleSheet("background: rgba(239, 68, 68, 0.15); color: #f87171; border-radius: 4px; padding: 2px 8px; font-size: 7.5pt; font-weight: bold;")
        s4_hdr.addWidget(s4_title)
        s4_hdr.addStretch()
        s4_hdr.addWidget(s4_badge)
        s4_lay.addLayout(s4_hdr)

        table_snack = QTableWidget()
        table_snack.setColumnCount(4)
        table_snack.setHorizontalHeaderLabels(["Subsystem Item", "Stoichiometry (Ingredients)", "Preparation Process", "Macronutrient Profile"])
        table_snack.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table_snack.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table_snack.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table_snack.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table_snack.setFixedHeight(150)
        table_snack.setStyleSheet(
            "QTableWidget { background: #05080f; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; font-size: 8pt; }"
            "QHeaderView::section { background: #0f141f; color: #94a3b8; font-weight: bold; border: 1px solid #1e293b; padding: 5px; }"
        )

        table_snack.setRowCount(len(KETO_SNACKS))
        for r_idx, (s_name, s_ing, s_proc, s_macros) in enumerate(KETO_SNACKS):
            item_name = QTableWidgetItem(s_name)
            item_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            item_macro = QTableWidgetItem(s_macros)
            item_macro.setForeground(QColor("#10b981"))
            item_macro.setFont(QFont("Consolas", 8, QFont.Weight.Bold))

            table_snack.setItem(r_idx, 0, item_name)
            table_snack.setItem(r_idx, 1, QTableWidgetItem(s_ing))
            table_snack.setItem(r_idx, 2, QTableWidgetItem(s_proc))
            table_snack.setItem(r_idx, 3, item_macro)

        s4_lay.addWidget(table_snack)
        layout.addWidget(sec4)

        # 7. Section 5: High-Satiety Ketogenic Meal Blueprints
        sec5 = QFrame()
        sec5.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        s5_lay = QVBoxLayout(sec5)
        s5_lay.setContentsMargins(6, 6, 6, 6)
        s5_lay.setSpacing(8)

        s5_hdr = QHBoxLayout()
        s5_title = QLabel("5. <b>HIGH-SATIETY KETOGENIC MEAL BLUEPRINTS</b>")
        s5_title.setStyleSheet("font-size: 9pt; color: #f1f5f9;")
        s5_badge = QLabel("Mitochondrial Beta-Oxidation")
        s5_badge.setStyleSheet("background: rgba(168, 85, 247, 0.15); color: #a855f7; border-radius: 4px; padding: 2px 8px; font-size: 7.5pt; font-weight: bold;")
        s5_hdr.addWidget(s5_title)
        s5_hdr.addStretch()
        s5_hdr.addWidget(s5_badge)
        s5_lay.addLayout(s5_hdr)

        meals = [
            ("MEAL 01: Wild Sockeye Filet with Charred Brassica in Tallow", "45g Lipid | 38g Protein | 3g Net Carb", "Sear 6 oz dry sockeye filet skin-down in 1 tbsp rendered grass-fed tallow for 240s in high-heat cast iron. Flip, cook for 120s. Extract to board. Drop 1.5 cups diced broccoli florets and 1 minced garlic clove into pan with 1 tbsp secondary tallow. Char aggressively at high heat for 200s. Deglaze surface with 15mL lemon juice. Pour lipid residue over protein."),
            ("MEAL 02: Basted Prime Ribeye Strip with Garlic Butter Wilted Chard", "55g Lipid | 42g Protein | 2g Net Carb", "Temper 8 oz prime ribeye to 20°C ambient. Salt heavily. Sear in dry cast iron smoking-hot for 150s per face. Drop 30g pasture-raised butter, crushed allium clove, and rosemary; arrose (spoon baste) continuously for 120s. Extract steak; allow 360s muscle relaxation. Drop 2 cups chopped Swiss chard into pan drippings. Sauté for 90s. Serve beneath sliced steak."),
        ]

        for m_title, m_mac, m_exec in meals:
            m_box = QFrame()
            m_box.setStyleSheet("background: #070b14; border: 1px solid #1e293b; border-left: 3px solid #f59e0b; border-radius: 6px; padding: 8px;")
            m_lay = QVBoxLayout(m_box)
            m_top = QHBoxLayout()
            m_head = QLabel(f"<b>{m_title}</b>")
            m_head.setStyleSheet("color: #f59e0b; font-size: 8pt;")
            m_pill = QLabel(m_mac)
            m_pill.setStyleSheet("color: #10b981; font-family: Consolas; font-size: 7.5pt; font-weight: bold;")
            m_top.addWidget(m_head)
            m_top.addStretch()
            m_top.addWidget(m_pill)
            m_lay.addLayout(m_top)
            m_desc = QLabel(f"<b>Execution:</b> {m_exec}")
            m_desc.setStyleSheet("color: #cbd5e1; font-size: 7.5pt;")
            m_desc.setWordWrap(True)
            m_lay.addWidget(m_desc)
            s5_lay.addWidget(m_box)

        layout.addWidget(sec5)

        # 8. Section 6: Stepped Refeeding & Daily Electrolytes
        sec6 = QFrame()
        sec6.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        s6_lay = QVBoxLayout(sec6)
        s6_lay.setContentsMargins(6, 6, 6, 6)
        s6_lay.setSpacing(8)

        s6_hdr = QHBoxLayout()
        s6_title = QLabel("6. <b>STEPPED REFEEDING & METABOLIC PHASE-SHIFT (DAYS 15-18)</b>")
        s6_title.setStyleSheet("font-size: 9pt; color: #f1f5f9;")
        s6_badge = QLabel("Prevent Refeeding Syndrome")
        s6_badge.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #10b981; border-radius: 4px; padding: 2px 8px; font-size: 7.5pt; font-weight: bold;")
        s6_hdr.addWidget(s6_title)
        s6_hdr.addStretch()
        s6_hdr.addWidget(s6_badge)
        s6_lay.addLayout(s6_hdr)

        grid6 = QGridLayout()
        grid6.setSpacing(8)

        refeed_phases = [
            ("PHASE 01 (DAY 15 - ENZYME RESTORATION)", "Maintain Juice 01 at 07:30. At 13:00 consume 350mL warm bovine bone broth with 5g salt and 1/2 mashed avocado. At 18:00 ingest steamed zucchini and puréed cauliflower with 15mL extra virgin olive oil. ZERO solid muscle meat.", "#f59e0b"),
            ("PHASE 02 (DAY 16 - LIPID & ALBUMIN ACCLIMATION)", "Morning Juice 04. Midday meal: 2 poached pastured whole eggs with 1/2 sliced avocado and 250mL broth. Evening meal: 120g steamed white fish (halibut/cod) over wilted spinach in 15g grass-fed butter.", "#f59e0b"),
            ("PHASE 03 (DAY 17 - SKELETAL MYOSIN INTEGRATION)", "Morning: Avocado-MCT Salt Pod with black coffee. Midday: Sockeye Salmon Blueprint (Half Portion). Evening: 120g pasture-raised 80/20 ground beef browned in tallow over raw arugula with extra virgin olive oil.", "#f59e0b"),
            ("PHASE 04 (DAY 18+ - HARD METABOLIC STATE TRANSITION)", "Cut liquid sugars. Deploy full ketogenic targets: 70-75% Lipid, 20-25% Protein, <5% Net Carbohydrates. Maintain strict exogenous electrolytes: 5000mg Na+, 1000mg K+, 300mg Mg-glycinate daily to prevent natriuresis shock.", "#10b981"),
        ]

        for p_idx, (p_head, p_text, p_col) in enumerate(refeed_phases):
            card = QFrame()
            card.setStyleSheet(f"background: #070b14; border: 1px solid #1e293b; border-left: 3px solid {p_col}; border-radius: 6px; padding: 8px;")
            lay = QVBoxLayout(card)
            lbl_h = QLabel(f"<b>{p_head}</b>")
            lbl_h.setStyleSheet(f"color: {p_col}; font-size: 8pt;")
            lbl_t = QLabel(p_text)
            lbl_t.setStyleSheet("color: #cbd5e1; font-size: 7.5pt;")
            lbl_t.setWordWrap(True)
            lay.addWidget(lbl_h)
            lay.addWidget(lbl_t)
            grid6.addWidget(card, p_idx // 2, p_idx % 2)

        s6_lay.addLayout(grid6)
        layout.addWidget(sec6)

        layout.addStretch()
        scroll.setWidget(container)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

    def _build_info_card(self, title: str, items: list[str], color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"background: #070b12; border: 1px solid #1e293b; border-left: 3px solid {color}; border-radius: 6px; padding: 10px;")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        lbl = QLabel(f"<b>{title}</b>")
        lbl.setStyleSheet(f"color: {color}; font-size: 8.5pt;")
        lay.addWidget(lbl)

        for it in items:
            it_lbl = QLabel(it)
            it_lbl.setStyleSheet("color: #cbd5e1; font-size: 7.5pt; font-family: monospace;")
            lay.addWidget(it_lbl)

        return card

    def _copy_payload(self) -> None:
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(json.dumps(RAW_PROTOCOL_PAYLOAD, indent=2))
            self.btn_copy_payload.setText("✅ Payload Copied to Clipboard!")
            self.btn_copy_payload.setStyleSheet("background: #059669; color: #ffffff; border-radius: 6px; padding: 7px 16px; font-weight: bold; font-size: 8pt;")
            QTimer.singleShot(2000, self._reset_copy_btn)

    def _reset_copy_btn(self) -> None:
        self.btn_copy_payload.setText("📋 Copy Protocol JSON Payload")
        self.btn_copy_payload.setStyleSheet("background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; border-radius: 6px; padding: 7px 16px; font-weight: bold; font-size: 8pt;")
