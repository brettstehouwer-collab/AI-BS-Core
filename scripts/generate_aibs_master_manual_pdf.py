"""
AI-BS Master Ecosystem User Manual PDF Generator (Publication-Grade Edition v2)
Compiles a polished, high-resolution, perfectly paginated PDF manual
covering the entire AI-BS ecosystem with custom NumberedCanvas pagination,
modern typography, clean formatted tables, and callouts.
"""

import os
import sys
import shutil
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# Output Paths
DOCS_DIR = r"C:\AI-BS\docs"
ARTIFACTS_DIR = r"C:\AI-BS\saved_data\artifacts"
OUTPUT_PDF = os.path.join(DOCS_DIR, "AI_BS_MASTER_ECOSYSTEM_USER_MANUAL.pdf")
TIMESTAMP = datetime.now().strftime("%Y%m%d")
ARCHIVE_PDF = os.path.join(ARTIFACTS_DIR, f"{TIMESTAMP}_AI_BS_Master_Ecosystem_User_Manual.pdf")

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and stamp total page count,
    running headers, footers, and sovereign document rules.
    """
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Skip running headers/footers on cover page
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running Header
        self.drawString(36, 756, "AI-BS MASTER ECOSYSTEM USER MANUAL")
        self.drawRightString(576, 756, "VERSION v5.285.5 • MASTER DIRECTIVE")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.75)
        self.line(36, 750, 576, 750)

        # Running Footer
        self.line(36, 40, 576, 40)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(36, 28, "STEHOUWER PUBLISHING LLC • SOVEREIGN OPERATIONAL ARCHITECTURE")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 28, page_str)
        self.restoreState()


def build_manual_pdf():
    # Page height = 792 pt, width = 612 pt. Margins = 36 pt (0.5 in). Usable width = 540 pt, usable height = 720 pt.
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Color Palette
    c_primary = colors.HexColor("#0f172a")     # Deep Slate
    c_accent = colors.HexColor("#0284c7")      # Sky Blue
    c_secondary = colors.HexColor("#334155")   # Slate
    c_emerald = colors.HexColor("#059669")     # Emerald Green
    c_dark = colors.HexColor("#1e293b")        # Dark text
    c_bg_light = colors.HexColor("#f8fafc")    # Table alternate BG
    c_border = colors.HexColor("#cbd5e1")      # Border grey

    cover_title_style = ParagraphStyle(
        'CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        alignment=TA_LEFT
    )

    cover_subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        alignment=TA_LEFT
    )

    h1_style = ParagraphStyle(
        'ChapterH1',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.white,
        spaceBefore=0,
        spaceAfter=0,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=c_primary,
        spaceBefore=7,
        spaceAfter=2,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyMain',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark,
        spaceAfter=4,
        alignment=TA_LEFT
    )

    bullet_style = ParagraphStyle(
        'BulletMain',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark,
        leftIndent=10,
        firstLineIndent=-6,
        spaceAfter=2
    )

    th_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#0f172a")
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b")
    )

    toc_item_style = ParagraphStyle(
        'TOCItem',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=c_primary
    )

    toc_sub_style = ParagraphStyle(
        'TOCSub',
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748b"),
        leftIndent=6
    )

    story = []

    def make_chapter_header(title, chapter_num):
        t = Table(
            [[Paragraph(f"CHAPTER {chapter_num}: {title.upper()}", h1_style)]],
            colWidths=[540]
        )
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_primary),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMBORDER', (0, 0), (-1, -1), 2, c_accent),
        ]))
        return t

    def make_callout(text, title="SYSTEM DIRECTIVE", border_color=c_accent, bg_color=colors.HexColor("#f0f9ff")):
        content = [
            Paragraph(f"<b>{title}:</b> {text}", callout_style)
        ]
        t = Table([[content]], colWidths=[540])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('LINELEFT', (0, 0), (0, -1), 3.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    def make_code_box(code_text):
        p = Paragraph(code_text.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)
        t = Table([[p]], colWidths=[540])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    # ─────────────────────────────────────────────────────────────────────────
    # COVER PAGE (Engineered to fit precisely on Page 1)
    # ─────────────────────────────────────────────────────────────────────────
    banner_table = Table([[""]], colWidths=[540], rowHeights=[4])
    banner_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), c_accent)]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("AI-BS MASTER ECOSYSTEM", cover_title_style))
    story.append(Paragraph("OPERATIONAL ARCHITECTURE & COMPLETE USER MANUAL", ParagraphStyle('CoverTitle2', parent=cover_title_style, fontSize=16, leading=20, textColor=c_accent)))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Autonomous Intelligence &amp; Build System &bull; Multi-Tenant Sovereign Operating Environment", cover_subtitle_style))
    story.append(Spacer(1, 10))

    cover_meta = [
        [Paragraph("<b>Document Version:</b>", body_style), Paragraph("v5.285.5 (Production Release)", body_style), Paragraph("<b>Host Baseline:</b>", body_style), Paragraph("Windows 11 Pro (WSL2 Dual Ubuntu)", body_style)],
        [Paragraph("<b>Primary Architect:</b>", body_style), Paragraph("Brett Stehouwer", body_style), Paragraph("<b>Hardware Compute:</b>", body_style), Paragraph("Ryzen 9 9950X &bull; RTX 4090 (24GB VRAM)", body_style)],
        [Paragraph("<b>Operator Contact:</b>", body_style), Paragraph("1-616-402-3628 (SMS / Voice Active)", body_style), Paragraph("<b>Operational Policy:</b>", body_style), Paragraph("Strict Zero-Cost Mandate (100% Free / Local)", body_style)],
        [Paragraph("<b>Operator Email:</b>", body_style), Paragraph("footballstar0325@gmail.com", body_style), Paragraph("<b>Live Dashboard:</b>", body_style), Paragraph("https://ai-bs-dashboard.web.app", body_style)],
    ]
    meta_table = Table(cover_meta, colWidths=[95, 175, 95, 175])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.75, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(make_callout(
        "This master manual serves as the immutable technical reference for the AI-BS ecosystem. "
        "It defines the 18-port collision matrix, 4-mirror frontend parity, background autonomous daemons, "
        "crypto swarms, live broadcast pipelines, 16-layer telemetry sentinel, and full recovery protocols.",
        "SOVEREIGN GOVERNANCE DIRECTIVE",
        c_emerald,
        colors.HexColor("#ecfdf5")
    ))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.75, color=c_border, spaceBefore=4, spaceAfter=8))
    
    # Table of Contents
    story.append(Paragraph("TABLE OF CONTENTS", h2_style))
    story.append(Spacer(1, 2))
    
    toc_data = [
        [Paragraph("1. Sovereign Architecture &amp; Host Baseline", toc_item_style), Paragraph("8. Unreal Engine 5 Pixel Streaming &amp; WebRTC", toc_item_style)],
        [Paragraph("&bull; WSL2 multi-tenancy, root authority &amp; zero-cost mandate", toc_sub_style), Paragraph("&bull; Port 8888 signaling, avatar sync &amp; input streams", toc_sub_style)],
        [Paragraph("2. The Immutable 18-Port Collision Matrix", toc_item_style), Paragraph("9. ComfyUI Screenplay &amp; Image Studio", toc_item_style)],
        [Paragraph("&bull; Static socket reservations, conflict prevention &amp; routing", toc_sub_style), Paragraph("&bull; Port 8189 standalone diffusion &amp; scene generation", toc_sub_style)],
        [Paragraph("3. Sovereign Web Dashboard &amp; 4-Mirror Parity", toc_item_style), Paragraph("10. Commercial Gateway &amp; Sovereign NDA Suite", toc_item_style)],
        [Paragraph("&bull; 4-mirror synchronization law &amp; Firebase CDN deploys", toc_sub_style), Paragraph("&bull; Stripe/PayPal/USDC, ReportLab PDF &amp; HMAC seals", toc_sub_style)],
        [Paragraph("4. Autonomous Background Daemons &amp; Agents", toc_item_style), Paragraph("11. Multi-Tenant Client Hubs &amp; Storefronts", toc_item_style)],
        [Paragraph("&bull; Research, Discord, Auto-Healer, Ingestors &amp; Workers", toc_sub_style), Paragraph("&bull; John Barr / The Simple Chef 7-rub catalog &amp; Venmo", toc_sub_style)],
        [Paragraph("5. Cognitive Memory &amp; ChromaDB Vector Stores", toc_item_style), Paragraph("12. 16-Layer Deep Web Telemetry Suite", toc_item_style)],
        [Paragraph("&bull; Partitioning, semantic recall &amp; context injection", toc_sub_style), Paragraph("&bull; Hardware fingerprinting, dwell tickers &amp; beaconing", toc_sub_style)],
        [Paragraph("6. Crypto Swarm &amp; Profit Compounding Engine", toc_item_style), Paragraph("13. Multi-Channel Presence &amp; Security Sentinel", toc_item_style)],
        [Paragraph("&bull; Port 8007 bot, micro-dip DCA &amp; Pearl mining watchdogs", toc_sub_style), Paragraph("&bull; Real-time Discord, SMS to 616-402-3628, Gmail &amp; TTS", toc_sub_style)],
        [Paragraph("7. Live Broadcast Studio &amp; VST3 Audio Bridge", toc_item_style), Paragraph("14. Disaster Recovery &amp; Cold-Start Protocols", toc_item_style)],
        [Paragraph("&bull; Ports 8088, 8013, 8010 NVENC video &amp; SHM telemetry", toc_sub_style), Paragraph("&bull; Checkpoint keywords, ledger tracking &amp; health scans", toc_sub_style)],
    ]
    toc_table = Table(toc_data, colWidths=[270, 270])
    toc_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(toc_table)

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 2: CHAPTER 1 & CHAPTER 2 (PORT MATRIX)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(make_chapter_header("Sovereign Architecture & Host Baseline", 1))
    story.append(Spacer(1, 4))

    story.append(Paragraph("1.1 Operational Environment Overview", h2_style))
    story.append(Paragraph(
        "The <b>AI-BS (Autonomous Intelligence &amp; Build System)</b> is a full-stack autonomous engineering, broadcast, "
        "and algorithmic compute operating system running natively on Windows 11 Pro host backed by dual WSL2 Linux tenant "
        "containers (<code>Ubuntu</code> for node/mining orchestration and <code>Ubuntu-24.04</code> for Vast.ai cloud compute).",
        body_style
    ))

    story.append(Paragraph("1.2 Infrastructure, Zero-Cost Mandate & Host Permissions", h2_style))
    story.append(Paragraph(
        "&bull; <b>Hardware Baseline:</b> AMD Ryzen 9 9950X (16 cores, 32 threads) + NVIDIA GeForce RTX 4090 (24GB GDDR6X VRAM).<br/>"
        "&bull; <b>Strict Zero-Cost Mandate:</b> Operates strictly on 100% free, local, open-source runtimes and local LLMs (no paid API charges).<br/>"
        "&bull; <b>Root Machine Authority:</b> Autonomous agent processes operate with unrestricted machine and network privileges.",
        bullet_style
    ))

    story.append(Spacer(1, 6))
    story.append(make_chapter_header("The Immutable 18-Port Collision Matrix", 2))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "To ensure zero socket collisions across all concurrent services, AI-BS statically reserves ports in an immutable matrix:",
        body_style
    ))

    port_rows = [
        [Paragraph("Port", th_style), Paragraph("Service / Subsystem", th_style), Paragraph("Protocol", th_style), Paragraph("Primary Function & Behavior", th_style)],
        [Paragraph("<b>80</b>", code_style), Paragraph("Nginx Gateway", body_style), Paragraph("HTTP / Proxy", body_style), Paragraph("Host ingress routing & multi-site domain dispatch", body_style)],
        [Paragraph("<b>3001</b>", code_style), Paragraph("Node.js Realtime Backend", body_style), Paragraph("REST / WS", body_style), Paragraph("Workspace state coordinator & inter-process messaging", body_style)],
        [Paragraph("<b>4455</b>", code_style), Paragraph("OBS WebSocket Bridge", body_style), Paragraph("WS (RPC)", body_style), Paragraph("Live broadcast scene switcher & audio cues", body_style)],
        [Paragraph("<b>5173</b>", code_style), Paragraph("Vite Dashboard Studio", body_style), Paragraph("HTTP / HMR", body_style), Paragraph("Primary AI-BS Web Dashboard development host", body_style)],
        [Paragraph("<b>5174</b>", code_style), Paragraph("Broadcast Studio App", body_style), Paragraph("HTTP / HMR", body_style), Paragraph("Broadcast UI and studio overlay control", body_style)],
        [Paragraph("<b>8000</b>", code_style), Paragraph("Go Core Engine", body_style), Paragraph("REST / Go", body_style), Paragraph("Go high-throughput data processing gateway", body_style)],
        [Paragraph("<b>8001/2</b>", code_style), Paragraph("ChromaDB Vector Stores", body_style), Paragraph("HTTP / Vector", body_style), Paragraph("Long-term cognitive memory & semantic embeddings", body_style)],
        [Paragraph("<b>8005</b>", code_style), Paragraph("Broadcast Daemon", body_style), Paragraph("TCP / Stream", body_style), Paragraph("Broadcast automation & session supervisor", body_style)],
        [Paragraph("<b>8006</b>", code_style), Paragraph("Social Hub (Twitch/IRC)", body_style), Paragraph("WS / IRC", body_style), Paragraph("Chat ingestion, moderation & Twitch live alert relay", body_style)],
        [Paragraph("<b>8007</b>", code_style), Paragraph("Crypto Swarm & Scalp Bot", body_style), Paragraph("WS / REST", body_style), Paragraph("CCXT Pro high-frequency trading & profit compounding", body_style)],
        [Paragraph("<b>8010</b>", code_style), Paragraph("SHM Telemetry Gateway", body_style), Paragraph("WS / SHM", body_style), Paragraph("Low-latency C++/Python shared memory telemetry pipe", body_style)],
        [Paragraph("<b>8013</b>", code_style), Paragraph("VST3 Audio Bridge", body_style), Paragraph("TCP / IPC", body_style), Paragraph("Real-time DSP, parametric EQ & audio stream routing", body_style)],
        [Paragraph("<b>8055</b>", code_style), Paragraph("WSL2 Isolated Storefront", body_style), Paragraph("HTTP / Nginx", body_style), Paragraph("Isolated client webroot hosting (The Simple Chef)", body_style)],
        [Paragraph("<b>8080</b>", code_style), Paragraph("FastAPI Core Engine", body_style), Paragraph("REST / OpenAPI", body_style), Paragraph("Commercial gateway, NDA suite, order & presence APIs", body_style)],
        [Paragraph("<b>8088</b>", code_style), Paragraph("Broadcast NVENC Kernel", body_style), Paragraph("NVENC / TCP", body_style), Paragraph("RTX 4090 hardware encoding & composite canvas pipe", body_style)],
        [Paragraph("<b>8089</b>", code_style), Paragraph("WSL HLS Ingest", body_style), Paragraph("HLS / Video", body_style), Paragraph("Linux video stream chunk segmentation & packaging", body_style)],
        [Paragraph("<b>8099</b>", code_style), Paragraph("Gemini MCP Server", body_style), Paragraph("JSON-RPC", body_style), Paragraph("Model Context Protocol tool routing bridge", body_style)],
        [Paragraph("<b>8189</b>", code_style), Paragraph("ComfyUI Studio", body_style), Paragraph("HTTP / WS", body_style), Paragraph("Diffusion generation, screenplay & art studio", body_style)],
        [Paragraph("<b>8888</b>", code_style), Paragraph("UE5 Signaling Server", body_style), Paragraph("WebRTC / WS", body_style), Paragraph("Unreal Engine 5 Pixel Streaming interactive bridge", body_style)],
        [Paragraph("<b>11434/5</b>", code_style), Paragraph("Ollama LLM Host", body_style), Paragraph("HTTP / OpenAI", body_style), Paragraph("Local neural models (Qwen2.5, Nomic, Llama)", body_style)],
    ]
    p_table = Table(port_rows, colWidths=[55, 140, 85, 260])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.2),
        ('TOPPADDING', (0,0), (-1,-1), 1.2),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
    ]))
    story.append(p_table)

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 3: CHAPTER 3 & CHAPTER 4 (DASHBOARD & DAEMONS)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(make_chapter_header("Sovereign Web Dashboard & 4-Mirror Parity", 3))
    story.append(Spacer(1, 4))

    story.append(Paragraph("3.1 The 4-Mirror Directory Synchronization Law", h2_style))
    story.append(Paragraph(
        "Under <b>Rule 1</b>, every component or stylesheet modification MUST update all 4 mirror trees simultaneously with 100% byte parity:<br/>"
        "1. <code>frontend/src/components/&lt;File&gt;</code> &bull; "
        "2. <code>frontend/components/&lt;File&gt;</code> &bull; "
        "3. <code>frontend/src/components/components/&lt;File&gt;</code> &bull; "
        "4. <code>frontend/components/components/&lt;File&gt;</code>",
        body_style
    ))

    story.append(Paragraph("3.2 Automated Build & Cloud Deployment Sequence", h2_style))
    story.append(make_code_box('powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"'))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "Deploys directly to Google Firebase CDN at <b>https://ai-bs-dashboard.web.app</b> with 0ms cold-start fallback schemas.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(make_chapter_header("Autonomous Background Daemons & Agents", 4))
    story.append(Spacer(1, 4))
    story.append(Paragraph("AI-BS orchestrates a continuous background swarm of specialized Python daemons:", body_style))

    daemon_rows = [
        [Paragraph("Daemon Script", th_style), Paragraph("Autonomous Function & Behavior", th_style)],
        [Paragraph("<code>research_agent_daemon.py</code>", code_style), Paragraph("Deep research agent continuously scraping and indexing technical topics into ChromaDB.", body_style)],
        [Paragraph("<code>discord_bot_daemon.py</code>", code_style), Paragraph("Discord bot listening for operator commands and dispatching system telemetry embed cards.", body_style)],
        [Paragraph("<code>auto_healer_daemon.py</code>", code_style), Paragraph("Self-healing watchdog checking 18 ports, detecting dead services, and reviving daemons.", body_style)],
        [Paragraph("<code>memory_daemon.py</code>", code_style), Paragraph("Manages short-term conversation compaction, sliding context windows, and SQLite sync.", body_style)],
        [Paragraph("<code>context_ingestor_daemon.py</code>", code_style), Paragraph("Real-time context ingestion engine feeding IDE file diffs and logs into vector memory.", body_style)],
        [Paragraph("<code>news_firehose_daemon.py</code>", code_style), Paragraph("Continuous multi-feed news collector aggregating global technology and market intelligence.", body_style)],
        [Paragraph("<code>ingest_finance_api.py</code>", code_style), Paragraph("Financial API scraper fetching live crypto prices, forex quotes, and pool metrics every 10s.", body_style)],
        [Paragraph("<code>ingest_news_rss.py</code>", code_style), Paragraph("RSS syndication engine aggregating industry newsfeeds and categorizing items.", body_style)],
        [Paragraph("<code>infinite_learning_loop.py</code>", code_style), Paragraph("Continuous cognitive synthesis engine extracting lessons from task history.", body_style)],
        [Paragraph("<code>bullshit_writer_daemon.py</code>", code_style), Paragraph("Creative writing engine transcribing raw unfiltered cognitive streams under Fidelitas Mandate.", body_style)],
        [Paragraph("<code>AI_BS_Master_Worker.py</code>", code_style), Paragraph("Master orchestration worker processing async jobs from SQLite queues with thread pools.", body_style)],
        [Paragraph("<code>AI_BS_Universal_Data_Ingestor.py</code>", code_style), Paragraph("Aggregates streaming telemetry, RF electromagnetic beacons, and local hardware sensory signals.", body_style)],
    ]
    d_table = Table(daemon_rows, colWidths=[175, 365])
    d_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
        ('TOPPADDING', (0,0), (-1,-1), 1.5),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
    ]))
    story.append(d_table)

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 4: CHAPTER 5 & CHAPTER 6 (COGNITIVE MEMORY & CRYPTO SWARM)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(make_chapter_header("Cognitive Memory & ChromaDB Vector Stores", 5))
    story.append(Spacer(1, 4))

    story.append(Paragraph("5.1 ChromaDB Topology & Partitioning", h2_style))
    story.append(Paragraph(
        "Cognitive long-term memory is partitioned across local ChromaDB vector instances on Ports 8001 &amp; 8002:<br/>"
        "&bull; <b><code>stehouwer_vector_memory</code>:</b> Core architecture, operating directives, operator profile, and session learnings.<br/>"
        "&bull; <b><code>chroma_db</code>:</b> General workspace index, documentation embeddings, and deep research summaries.<br/>"
        "&bull; <b><code>thesimplechef_analytics_bin</code>:</b> Anonymized visitor telemetry embeddings with 50,000 vector memory guards.",
        bullet_style
    ))

    story.append(Paragraph("5.2 Semantic Search & Context Injection", h2_style))
    story.append(Paragraph(
        "Incoming queries are vectorized via <code>nomic-embed-text</code>. Top-k semantic similarity matching retrieves "
        "relevant historical context and injects it directly into local LLM prompts for zero-latency memory continuity.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(make_chapter_header("Crypto Swarm & Profit Compounding Engine", 6))
    story.append(Spacer(1, 4))

    story.append(Paragraph("6.1 High-Frequency Scalping & Profit Compounding (Port 8007)", h2_style))
    story.append(Paragraph(
        "The algorithmic trading engine (<b><font color='#0284c7'>crypto_trader_bot.py</font></b>) runs on Port 8007:<br/>"
        "&bull; <b>Micro-Dip DCA Accumulation:</b> Detects 0.75% micro-dips on target pairs (e.g. CRO/USD) and executes small accumulation lots.<br/>"
        "&bull; <b>Fast-Scalp Profit Taking:</b> Sells profitable lots upon hitting 0.85% profit targets over short windows.<br/>"
        "&bull; <b>Automated Profit Compounding:</b> As soon as accumulated cycle profit reaches <b>$1.05</b> (exceeding Crypto.com's $1.00 minimum order notional limit), "
        "the bot automatically buys CRO from pure profit on hourly dips, sweeping the assets directly into the <code>long_term_vault</code> (pure house money).<br/>"
        "&bull; <b>Zero-Mock Real Money Rule:</b> Never display simulated or synthetic figures; all balances reflect verified on-chain and exchange states.",
        bullet_style
    ))

    story.append(Paragraph("6.2 GPU Compute Monetization & Remote Cluster Watchdogs", h2_style))
    story.append(Paragraph(
        "&bull; <b>Pearl Miner (<code>Mine_Pearl.bat</code>):</b> Hashes on RTX 4090 GPU at ~275 TH/s during compute idle windows.<br/>"
        "&bull; <b><code>pearl_payout_watcher.py</code>:</b> Continuously polls mining pool balances and confirms wallet deposits.<br/>"
        "&bull; <b><code>vast_clore_pearl_watchdog.py</code>:</b> Monitors remote compute instances across Vast.ai and Clore.ai clusters.",
        bullet_style
    ))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 5: CHAPTER 7, 8 & 9 (BROADCAST, UE5, COMFYUI)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(make_chapter_header("Live Broadcast Studio & VST3 Audio Bridge", 7))
    story.append(Spacer(1, 4))

    story.append(Paragraph("7.1 Broadcast Video Kernel & Audio Signal Processing", h2_style))
    story.append(Paragraph(
        "&bull; <b>Broadcast NVENC Kernel (Port 8088):</b> RTX 4090 hardware-accelerated video pipeline and OBS WebSocket bridge (Port 4455).<br/>"
        "&bull; <b>VST3 Audio Bridge (Port 8013):</b> Real-time DSP audio daemon running parametric EQ, noise suppression, and AES3 streaming.<br/>"
        "&bull; <b>SHM Telemetry Gateway (Port 8010):</b> Low-latency shared memory WebSocket bridge relaying real-time audio waveforms and GPU metrics.",
        bullet_style
    ))

    story.append(Spacer(1, 6))
    story.append(make_chapter_header("Unreal Engine 5 Pixel Streaming & WebRTC", 8))
    story.append(Spacer(1, 4))

    story.append(Paragraph("8.1 Interactive WebRTC Signaling Server (Port 8888)", h2_style))
    story.append(Paragraph(
        "AI-BS hosts a custom WebRTC signaling server (<b><font color='#0284c7'>AI_BS_Unreal_Signaling_Server.py</font></b>) "
        "streaming interactive Unreal Engine 5 avatars and virtual production sets directly into web browsers with sub-50ms latency "
        "and bi-directional user mouse/keyboard input streams.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(make_chapter_header("ComfyUI Screenplay & Image Studio", 9))
    story.append(Spacer(1, 4))

    story.append(Paragraph("9.1 Standalone Diffusion Engine (Port 8189)", h2_style))
    story.append(Paragraph(
        "Runs an isolated ComfyUI build on Port 8189. Agents programmatically submit prompt workflows to render cinematic storyboards, "
        "product mockups, and screenplay scene artwork with consistent character LoRAs and style conditioning.",
        body_style
    ))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 6: CHAPTER 10 & CHAPTER 11 (COMMERCIAL & CLIENT HUBS)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(make_chapter_header("Commercial Gateway & Sovereign NDA Suite", 10))
    story.append(Spacer(1, 4))

    story.append(Paragraph("10.1 Commercial Payments & Webhooks (Port 8080)", h2_style))
    story.append(Paragraph(
        "The commercial router handles Stripe, PayPal, Square, Venmo, and on-chain Polygon USDC wallet deposits with automated webhook validation.",
        body_style
    ))

    story.append(Paragraph("10.2 Sovereign NDA Suite & Anti-Tamper Security", h2_style))
    story.append(Paragraph(
        "The Sovereign NDA Suite (<b><font color='#0284c7'>NdaModuleTab.jsx</font></b>) provides:<br/>"
        "&bull; <b>8-Section 32-Clause Schema:</b> Complete legal protections governed under Michigan State &amp; Kent County law.<br/>"
        "&bull; <b>HTML5 Canvas Signature Pad:</b> Vector signature capture and 1-click field clearance.<br/>"
        "&bull; <b>Cryptographic Watermarked PDF:</b> ReportLab &amp; PyMuPDF PDF generation embedded with SHA-256 HMAC anti-tamper seals.",
        bullet_style
    ))

    story.append(Spacer(1, 6))
    story.append(make_chapter_header("Multi-Tenant Client Hubs & Storefronts", 11))
    story.append(Spacer(1, 4))

    story.append(Paragraph("11.1 Client Hub Architecture (JohnBarr.jsx)", h2_style))
    story.append(Paragraph(
        "Dedicated client portals in the master dashboard provide live order feeds, revenue KPIs, ChromaDB vector analytics, and 1-click executive briefing generators.",
        body_style
    ))

    story.append(Paragraph("11.2 The Simple Chef Storefront (thesimplechef.web.app)", h2_style))
    story.append(Paragraph(
        "&bull; <b>7 Signature Seasonings ($8.99 each):</b> Rub That Hiney, Yard Pimp Dust, Kelly's Calling, Buck Down, Gringo Curry, Original Salt Pepper, Citrus Pepper.<br/>"
        "&bull; <b>Slide-Over Kitchen Cart &amp; Checkout:</b> Dynamic cart drawer, flat $5.00 shipping, Venmo (<code>@John-Barr-1293</code>), Square, and local smokehouse pickup.<br/>"
        "&bull; <b>Multi-Channel Order Dispatch:</b> Dispatches instant SMS order texts, branded HTML receipts, and updates Google Sheets in real time.",
        bullet_style
    ))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 7: CHAPTER 12: 16-LAYER DEEP WEB TELEMETRY SUITE
    # ─────────────────────────────────────────────────────────────────────────
    story.append(make_chapter_header("16-Layer Deep Web Telemetry Suite", 12))
    story.append(Spacer(1, 4))

    story.append(Paragraph(
        "AI-BS deploys an automated 16-layer client-side telemetry engine (<b><font color='#0284c7'>analytics.js</font></b>) "
        "across all storefronts and dashboards, capturing comprehensive technical and behavioral metrics:",
        body_style
    ))

    layer_rows = [
        [Paragraph("Layer", th_style), Paragraph("Domain", th_style), Paragraph("Captured Technical Metrics & Telemetry Heuristics", th_style)],
        [Paragraph("<b>Layer 1</b>", code_style), Paragraph("Network Bandwidth", body_style), Paragraph("Downlink Mbps, round-trip time (RTT), effective connection type (4g/3g/wifi).", body_style)],
        [Paragraph("<b>Layer 2</b>", code_style), Paragraph("Navigation Timing", body_style), Paragraph("TTFB, DNS lookup, TCP connect, DOM interactive, full page load duration.", body_style)],
        [Paragraph("<b>Layer 3</b>", code_style), Paragraph("Hardware Depth", body_style), Paragraph("WebGL unmasked GPU renderer/vendor, logical CPU cores, RAM memory, Retina DPR.", body_style)],
        [Paragraph("<b>Layer 4</b>", code_style), Paragraph("Display &amp; Locale", body_style), Paragraph("Browser language, IANA timezone, screen resolution, color depth, orientation.", body_style)],
        [Paragraph("<b>Layer 5</b>", code_style), Paragraph("Campaign Attribution", body_style), Paragraph("UTM parameters (source, medium, campaign, term, content), gclid, fbclid, referrers.", body_style)],
        [Paragraph("<b>Layer 6</b>", code_style), Paragraph("Media Readiness", body_style), Paragraph("HLS video support, Media Source Extensions (MSE), MP4 playback capability.", body_style)],
        [Paragraph("<b>Layer 7</b>", code_style), Paragraph("Bot Velocity Scoring", body_style), Paragraph("Human interaction heuristics, mouse acceleration, scroll velocity, touch flags.", body_style)],
        [Paragraph("<b>Layer 8</b>", code_style), Paragraph("Core Web Vitals", body_style), Paragraph("Largest Contentful Paint (LCP) &amp; Cumulative Layout Shift (CLS) via PerformanceObserver.", body_style)],
        [Paragraph("<b>Layer 9</b>", code_style), Paragraph("Dwell Time Ticker", body_style), Paragraph("1-second precision active visibility dwell timer tracking true user attention.", body_style)],
        [Paragraph("<b>Layer 10</b>", code_style), Paragraph("Scroll Milestones", body_style), Paragraph("Automated 25%, 50%, 75%, and 100% viewport scroll milestone triggers.", body_style)],
        [Paragraph("<b>Layer 11</b>", code_style), Paragraph("Form Abandonment", body_style), Paragraph("Input focus/blur tracking, checkout funnel stage timing, form drop-off detection.", body_style)],
        [Paragraph("<b>Layer 12</b>", code_style), Paragraph("Outbound &amp; Downloads", body_style), Paragraph("Tracks outbound partner clicks and PDF document download milestones.", body_style)],
        [Paragraph("<b>Layer 13</b>", code_style), Paragraph("Client Error Logger", body_style), Paragraph("Global <code>window.onerror</code> and unhandled promise rejection telemetry captures.", body_style)],
        [Paragraph("<b>Layer 14</b>", code_style), Paragraph("Heatmap Coordinates", body_style), Paragraph("Absolute page (X, Y) click coordinates, targeted CSS selectors, and button IDs.", body_style)],
        [Paragraph("<b>Layer 15</b>", code_style), Paragraph("Heartbeat Keep-Alive", body_style), Paragraph("30-second periodic keep-alive telemetry pulses sustaining active sessions.", body_style)],
        [Paragraph("<b>Layer 16</b>", code_style), Paragraph("Zero-Loss Transport", body_style), Paragraph("<code>navigator.sendBeacon</code> and keepalive fetch ensuring zero data loss on page exit.", body_style)],
    ]
    l_table = Table(layer_rows, colWidths=[55, 125, 360])
    l_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.2),
        ('TOPPADDING', (0,0), (-1,-1), 1.2),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
    ]))
    story.append(l_table)

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 8: CHAPTER 13 & CHAPTER 14 (SENTINEL & RECOVERY)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(make_chapter_header("Multi-Channel Presence & Security Sentinel", 13))
    story.append(Spacer(1, 4))

    story.append(Paragraph("13.1 Real-Time User & Login Notification Engine", h2_style))
    story.append(Paragraph(
        "AI-BS features a multi-channel presence sentinel (<b><font color='#0284c7'>site_analytics_router.py</font></b>) "
        "that instantly alerts the operator whenever a user visits or authenticates on <b>https://ai-bs-dashboard.web.app</b>:<br/>"
        "&bull; <b>Discord Webhooks:</b> Rich embed cards (Sky Blue for active visitors, Emerald Green with sirens for logins) detailing user email, location, IP, and GPU specs.<br/>"
        "&bull; <b>Carrier SMS Gateway Dispatcher:</b> Dispatches individual, direct text messages to operator phone <b>1-616-402-3628</b> via major carrier SMS/MMS relays "
        "(Verizon <code>@vtext.com</code>/<code>@vzwpix.com</code>, AT&T <code>@txt.att.net</code>/<code>@mms.att.net</code>, T-Mobile <code>@tmomail.net</code>, Google Fi <code>@msg.fi.google.com</code>, Sprint, Boost, Cricket, US Cellular).<br/>"
        "&bull; <b>Authenticated Gmail SMTP Alert:</b> Sends instant email notifications to <code>footballstar0325@gmail.com</code>.<br/>"
        "&bull; <b>Local Host Voice Engine (TTS):</b> Triggers <code>bullshit_senses.speak_direct</code> for immediate spoken announcements on the workstation speakers.<br/>"
        "&bull; <b>Debounced Cooldown Protection:</b> 45-second cooldown for logins and 5-minute cooldown for pageviews preventing notification spam.",
        bullet_style
    ))

    story.append(Spacer(1, 6))
    story.append(make_chapter_header("Disaster Recovery & Cold-Start Protocols", 14))
    story.append(Spacer(1, 4))

    story.append(Paragraph("14.1 Cold-Start State Recovery Protocol", h2_style))
    story.append(Paragraph(
        "Upon system restart or context reset, AI-BS reads <code>C:\\AI-BS\\SAVED_CHECKPOINT.md</code> first. The active resume keyword "
        "(e.g. <code>RESUME_DASHBOARD_PRESENCE_SENTINEL_V5_285_5</code>) immediately restores operational state without parsing historical ledger archives.",
        body_style
    ))

    story.append(Paragraph("14.2 Continuous Documentation & Architectural Governance", h2_style))
    story.append(Paragraph(
        "1. <b>Version Parity:</b> Increment version in <code>frontend/package.json</code>, <code>version.txt</code>, and sweep UI badges.<br/>"
        "2. <b>Master Architectural Ledger:</b> Append structured entry to <code>AI_BS_MASTER_ARCHITECTURAL_LEDGER.md</code>.<br/>"
        "3. <b>Master Ecosystem Manual:</b> Update <code>docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md</code> and archive copy to <code>saved_data/artifacts/</code>.<br/>"
        "4. <b>Chronology Indexes:</b> Synchronize task, implementation plan, and handoff chronology files.",
        bullet_style
    ))

    story.append(Paragraph("14.3 Safety Guardrails & Fidelitas Mandate", h2_style))
    story.append(Paragraph(
        "&bull; <b>Safety Filters:</b> Categories S1, S3, and S4 are locked permanently in <code>backend/core/safety_guardrails.py</code>.<br/>"
        "&bull; <b>Fire Writing Fidelitas Mandate:</b> Raw manuscripts and unfiltered cognitive streams are transcribed verbatim with zero word smoothing or substitution, sequestered in <code>raw_source_payload</code> blocks.",
        bullet_style
    ))

    story.append(Spacer(1, 8))
    story.append(make_callout(
        "AI-BS Master Ecosystem User Manual v5.285.5 compilation verified complete. "
        "All 14 subsystems, 18-port collision matrix sockets, daemons, telemetry layers, and recovery protocols are active and enforced.",
        "END OF MASTER USER MANUAL DIRECTIVE",
        c_primary,
        colors.HexColor("#f8fafc")
    ))

    # Build Document
    print(f"Compiling publication-grade PDF document to {OUTPUT_PDF}...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Master User Manual PDF compiled successfully! Size: {os.path.getsize(OUTPUT_PDF)} bytes")

    # Copy to immutable archive
    shutil.copy2(OUTPUT_PDF, ARCHIVE_PDF)
    print(f"Archived immutable copy to {ARCHIVE_PDF}")


if __name__ == "__main__":
    build_manual_pdf()
