"""
AI-BS Matrix Screenwriting Engine — Local Fountain-based screenplay IDE
Decouples plaintext parsing from rendering, implements Git branching, Beat Board tracking
"""

import shutil
import json
import html
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False

try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Fountain element types


@dataclass
class FountainElement:
    # Scene Heading, Action, Character, Dialogue, Parenthetical, etc.
    element_type: str
    element_text: str
    line_number: int
    page_estimate: float = 0.0
    character_name: Optional[str] = None


class FountainParser:
    """Parse plaintext Fountain screenwriting syntax into structured AST"""

    # Fountain syntax regex patterns
    PATTERNS = {
        'scene_heading': r'^(INT|EXT|EST|INT\/EXT|I\/E)\.?\s+(.+?)(\s+[-–]\s+(.+))?$',
        'character': r'^(\*{0,3})([A-Z\s\(\)]+?)(\*{0,3})$',
        'parenthetical': r'^\s*\((.+)\)\s*$',
        'dialogue': r'^(?![\(\[])[A-Za-z\s\-\']+$',
        'action': r'^[A-Za-z]',
        'transition': r'^(CUT TO:|FADE|DISSOLVE|SMASH CUT|J CUT)[\s:]*(.*)$',
        'page_break': r'^===+$',
        'comment': r'^\/\*(.+?)\*\/$',
        'boneyard': r'^\[\[(.+?)\]\]$',
    }

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split('\n')
        self.elements: List[FountainElement] = []
        self.parse()

    def parse(self):
        """Main parsing loop — consume lines and emit structured elements"""
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # Scene heading (must be uppercase and match pattern)
            if re.match(self.PATTERNS['scene_heading'], stripped):
                match = re.match(self.PATTERNS['scene_heading'], stripped)
                heading = f"{match.group(1)}. {match.group(2)}"
                if match.group(4):
                    heading += f" - {match.group(4)}"
                self.elements.append(
                    FountainElement(
                        'Scene Heading', heading, i))
                i += 1

            # Page break
            elif re.match(self.PATTERNS['page_break'], stripped):
                self.elements.append(FountainElement('Page Break', '', i))
                i += 1

            # Comment (boneyard)
            elif stripped.startswith('[[') and stripped.endswith(']]'):
                content = stripped[2:-2].strip()
                self.elements.append(FountainElement('Boneyard', content, i))
                i += 1

            # Transition
            elif re.match(self.PATTERNS['transition'], stripped):
                match = re.match(self.PATTERNS['transition'], stripped)
                self.elements.append(
                    FountainElement(
                        'Transition', stripped, i))
                i += 1

            # Character (all caps, optionally preceded by asterisks for
            # emphasis)
            elif stripped.isupper() and len(stripped.split()) <= 3 and not any(c.isdigit() for c in stripped):
                char_name = stripped.replace('*', '')
                self.elements.append(
                    FountainElement(
                        'Character',
                        char_name,
                        i,
                        character_name=char_name))
                i += 1

            # Parenthetical
            elif re.match(self.PATTERNS['parenthetical'], stripped):
                match = re.match(self.PATTERNS['parenthetical'], stripped)
                self.elements.append(
                    FountainElement(
                        'Parenthetical',
                        match.group(1),
                        i))
                i += 1

            # Dialogue (follows character, not in parens, starts with alpha)
            elif self.elements and self.elements[-1].element_type in ['Character', 'Parenthetical']:
                if stripped and not stripped.startswith('('):
                    self.elements.append(
                        FountainElement(
                            'Dialogue', stripped, i))
                    i += 1
                else:
                    i += 1

            # Action (default fallback)
            else:
                if stripped:
                    self.elements.append(
                        FountainElement(
                            'Action', stripped, i))
                i += 1

    def estimate_pages(self):
        """Rough page count estimation using industry standard (55 lines per page)"""
        page = 1.0
        lines_on_page = 0

        for elem in self.elements:
            if elem.element_type == 'Page Break':
                page += 1
                lines_on_page = 0
            else:
                # Count wrapped lines (rough estimate)
                text_lines = max(1, len(elem.element_text) // 80 + 1)
                lines_on_page += text_lines

                if lines_on_page > 55:
                    page += 1
                    lines_on_page = text_lines

                elem.page_estimate = page

    def to_html(self) -> str:
        """Compile AST to styled HTML for browser rendering"""
        self.estimate_pages()
        html = '<div class="screenplay" style="font-family: Courier New, monospace; max-width: 8.5in; margin: 0 auto; padding: 1in;">'

        for elem in self.elements:
            if elem.element_type == 'Scene Heading':
                html += f'<h3 style="font-weight: bold; text-transform: uppercase; margin-top: 1em; margin-bottom: 0.5em;">{
                    elem.element_text}</h3>'
            elif elem.element_type == 'Action':
                html += f'<p style="margin: 0.5em 0; text-align: justify;">{
                    elem.element_text}</p>'
            elif elem.element_type == 'Character':
                html += f'<div style="margin-left: 2.5in; font-weight: bold; text-transform: uppercase; margin-top: 0.5em;">{
                    elem.element_text}</div>'
            elif elem.element_type == 'Parenthetical':
                html += f'<div style="margin-left: 2in; margin-right: 1.5in; font-style: italic;">({
                    elem.element_text})</div>'
            elif elem.element_type == 'Dialogue':
                html += f'<div style="margin-left: 1.5in; margin-right: 1in;">{
                    elem.element_text}</div>'
            elif elem.element_type == 'Transition':
                html += f'<p style="text-align: right; font-weight: bold; text-transform: uppercase; margin: 1em 0;">{
                    elem.element_text}</p>'
            elif elem.element_type == 'Page Break':
                html += '<div style="page-break-after: always; margin: 2em 0; border-top: 1px dashed #ccc;"></div>'

        html += '</div>'
        return html

    def to_pdf(self, title: str = "Untitled",
               author: str = "Unknown",
               watermark: str = None) -> bytes:
        """Compile AST to PDF, using WeasyPrint if available, otherwise falling back to ReportLab."""
        if WEASYPRINT_AVAILABLE:
            try:
                return self._to_pdf_weasyprint(title, author)
            except Exception as e:
                print(f"WeasyPrint failed ({e}), falling back to ReportLab...")

        if REPORTLAB_AVAILABLE:
            return self._to_pdf_reportlab(title, author, watermark)

        raise Exception(
            "No PDF generation libraries available. Install weasyprint or reportlab.")

    def _to_pdf_reportlab(self, title: str, author: str, watermark: str = None) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=1 * inch,
            leftMargin=1.5 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch
        )

        styles = getSampleStyleSheet()

        # Screenplay Styles
        scene_heading_style = ParagraphStyle(
            'SceneHeading',
            parent=styles['Normal'],
            fontName='Courier-Bold',
            fontSize=12,
            leading=12,
            spaceBefore=12,
            spaceAfter=12)
        action_style = ParagraphStyle(
            'Action', parent=styles['Normal'],
            fontName='Courier', fontSize=12, leading=12, spaceBefore=12
        )
        character_style = ParagraphStyle(
            'Character',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=12,
            spaceBefore=12,
            leftIndent=2 * inch,
            rightIndent=1 * inch)
        parenthetical_style = ParagraphStyle(
            'Parenthetical',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=12,
            leftIndent=1.5 * inch,
            rightIndent=1.5 * inch)
        dialogue_style = ParagraphStyle(
            'Dialogue',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=12,
            leftIndent=1 * inch,
            rightIndent=1 * inch)
        transition_style = ParagraphStyle(
            'Transition',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=12,
            spaceBefore=12,
            spaceAfter=12,
            alignment=TA_RIGHT)

        story = []

        # Title Page
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Normal'],
            fontName='Courier-Bold',
            fontSize=24,
            alignment=TA_CENTER,
            spaceBefore=3 * inch,
            spaceAfter=0.5 * inch)
        author_style = ParagraphStyle(
            'Author',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=12,
            alignment=TA_CENTER)
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"by<br/>{author}", author_style))
        story.append(PageBreak())

        for elem in self.elements:
            if elem.element_type == 'Scene Heading':
                story.append(Paragraph(elem.element_text, scene_heading_style))
            elif elem.element_type == 'Action':
                story.append(Paragraph(elem.element_text, action_style))
            elif elem.element_type == 'Character':
                story.append(Paragraph(elem.element_text, character_style))
            elif elem.element_type == 'Parenthetical':
                story.append(
                    Paragraph(f"({elem.element_text})", parenthetical_style))
            elif elem.element_type == 'Dialogue':
                story.append(Paragraph(elem.element_text, dialogue_style))
            elif elem.element_type == 'Transition':
                story.append(Paragraph(elem.element_text, transition_style))
            elif elem.element_type == 'Page Break':
                story.append(PageBreak())

        def draw_watermark(canvas, doc):
            if watermark:
                canvas.saveState()
                canvas.setFont('Helvetica-Bold', 60)
                canvas.setFillGray(0.5, 0.2)
                canvas.translate(4.25 * inch, 5.5 * inch)
                canvas.rotate(45)
                canvas.drawCentredString(0, 0, watermark)
                canvas.restoreState()

        doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
        return buffer.getvalue()

    def _to_pdf_weasyprint(self, title: str, author: str) -> bytes:
        raw_html = self.to_html()

        css = """
        @page {
            size: letter;
            margin-top: 1in;
            margin-bottom: 1in;
            margin-left: 1.5in;
            margin-right: 1in;
            @top-right {
                content: counter(page) ".";
                font-family: "Courier Prime", "Courier New", Courier, monospace;
                font-size: 12pt;
                padding-top: 0.5in;
            }
        }
        @page:first {
            @top-right { content: normal; }
        }
        body {
            font-family: "Courier Prime", "Courier New", Courier, monospace;
            font-size: 12pt;
            line-height: 1.2;
            color: black;
            background: white;
        }
        .screenplay {
            padding: 0 !important;
            margin: 0 !important;
            max-width: none !important;
        }
        """

        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{html.escape(title)}</title>
            <style>{css}</style>
        </head>
        <body>
            <div style="text-align: center; margin-top: 40vh; page-break-after: always;">
                <h1>{html.escape(title)}</h1>
                <p>by<br>{html.escape(author)}</p>
            </div>
            {raw_html}
        </body>
        </html>
        """

        pdf_bytes = weasyprint.HTML(string=styled_html).write_pdf()
        return pdf_bytes

    def to_fdx(self, title: str = "Untitled", author: str = "Unknown") -> str:
        """Convert AST to Final Draft XML (.fdx) format"""
        # Mapping Fountain types to Final Draft types
        type_mapping = {
            'Scene Heading': 'Scene Heading',
            'Action': 'Action',
            'Character': 'Character',
            'Dialogue': 'Dialogue',
            'Parenthetical': 'Parenthetical',
            'Transition': 'Transition'
        }

        element_settings = """
  <ElementSettings Type="Scene Heading">
    <FontSpec Font="Courier" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="1.5" LeftIndent="1.5" RightIndent="7.5" SpaceBefore="24" Spacing="1" StartsNewPage="No"/>
    <Behavior PaginateAs="Scene Heading" ReturnCreates="Action" TabCreates="Scene Heading"/>
  </ElementSettings>
  <ElementSettings Type="Action">
    <FontSpec Font="Courier" Size="12" Style=""/>
    <ParagraphSpec Alignment="Left" FirstIndent="1.5" LeftIndent="1.5" RightIndent="7.5" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior PaginateAs="Action" ReturnCreates="Action" TabCreates="Character"/>
  </ElementSettings>
  <ElementSettings Type="Character">
    <FontSpec Font="Courier" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="3.7" LeftIndent="3.7" RightIndent="7.5" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior PaginateAs="Character" ReturnCreates="Dialogue" TabCreates="Transition"/>
  </ElementSettings>
  <ElementSettings Type="Dialogue">
    <FontSpec Font="Courier" Size="12" Style=""/>
    <ParagraphSpec Alignment="Left" FirstIndent="2.5" LeftIndent="2.5" RightIndent="6.5" SpaceBefore="0" Spacing="1" StartsNewPage="No"/>
    <Behavior PaginateAs="Dialogue" ReturnCreates="Action" TabCreates="Parenthetical"/>
  </ElementSettings>
  <ElementSettings Type="Parenthetical">
    <FontSpec Font="Courier" Size="12" Style=""/>
    <ParagraphSpec Alignment="Left" FirstIndent="3.1" LeftIndent="3.1" RightIndent="5.5" SpaceBefore="0" Spacing="1" StartsNewPage="No"/>
    <Behavior PaginateAs="Parenthetical" ReturnCreates="Dialogue" TabCreates="Dialogue"/>
  </ElementSettings>
  <ElementSettings Type="Transition">
    <FontSpec Font="Courier" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Right" FirstIndent="5.5" LeftIndent="5.5" RightIndent="7.5" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior PaginateAs="Transition" ReturnCreates="Scene Heading" TabCreates="Scene Heading"/>
  </ElementSettings>
"""

        fdx = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>',
            '<FinalDraft DocumentType="Script" Template="No" Version="1">',
            element_settings,
            '  <Content>'
        ]

        for elem in self.elements:
            fd_type = type_mapping.get(
                elem.element_type, 'Action')  # fallback to Action
            text = html.escape(elem.element_text)

            # Simple conversion
            paragraph = f'    <Paragraph Type="{fd_type}">\n      <Text>{text}</Text>\n    </Paragraph>'
            fdx.append(paragraph)

        fdx.append('  </Content>')
        fdx.append('</FinalDraft>')

        return "\n".join(fdx)

    def extract_characters(self) -> List[str]:
        """Return unique character names in order of appearance"""
        chars = []
        seen = set()
        for elem in self.elements:
            if elem.element_type == 'Character' and elem.character_name and elem.character_name not in seen:
                chars.append(elem.character_name)
                seen.add(elem.character_name)
        return chars

    def extract_beats(self) -> List[Dict[str, Any]]:
        """Extract narrative beats (scene headings + action summary) for Beat Board"""
        beats = []
        current_beat = None

        for i, elem in enumerate(self.elements):
            if elem.element_type == 'Scene Heading':
                if current_beat:
                    current_beat['end_line'] = elem.line_number - 1
                    beats.append(current_beat)
                current_beat = {
                    'id': f"beat_{len(beats)}",
                    'heading': elem.element_text,
                    'page': elem.page_estimate,
                    'summary': '',
                    'characters': [],
                    'emoji': '🎬',
                    'start_line': elem.line_number
                }
            elif elem.element_type == 'Action' and current_beat:
                # Include the full action text instead of truncating to 100 chars
                # We separate paragraphs with a newline for better readability
                current_beat['summary'] += elem.element_text + '\n\n'
            elif elem.element_type == 'Character' and current_beat:
                if elem.character_name not in current_beat['characters']:
                    current_beat['characters'].append(elem.character_name)

        if current_beat:
            current_beat['end_line'] = len(self.lines) - 1
            beats.append(current_beat)

        return beats


class ScreenplayProject:
    """Manages a screenwriting project with Git branching, sprints, and file I/O"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(exist_ok=True)
        self.screenplay_file = self.project_dir / "screenplay.fountain"
        self.metadata_file = self.project_dir / "project.json"
        self.sprints_file = self.project_dir / "sprints.json"

        # Initialize git repo if not exists
        if not (self.project_dir / ".git").exists():
            subprocess.run(["git", "init"],
                           cwd=self.project_dir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "AI-BS"],
                           cwd=self.project_dir, capture_output=True)
            subprocess.run(["git",
                            "config",
                            "user.email",
                            "matrix@ai-bs.local"],
                           cwd=self.project_dir,
                           capture_output=True)

        self.load_metadata()

    def load_metadata(self):
        """Load or initialize project metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                'title': 'Untitled Screenplay',
                'author': 'Brett Adam Stehouwer',
                'created': datetime.now().isoformat(),
                'current_branch': 'main',
                'word_count': 0,
                'page_count': 0,
                'beat_videos': {}
            }
            self.save_metadata()

        # Ensure legacy projects get the beat_videos dictionary and characters array
        if 'beat_videos' not in self.metadata:
            self.metadata['beat_videos'] = {}
            self.save_metadata()
            
        if 'characters' not in self.metadata:
            self.metadata['characters'] = []
            self.save_metadata()

    def save_metadata(self):
        """Persist project metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def map_video_to_beat(self, beat_id: str, video_url: str):
        """Map a generated video stream URL to a specific beat/scene"""
        self.metadata['beat_videos'][beat_id] = video_url
        self.save_metadata()
        return True

    def read_screenplay(self) -> str:
        """Read current screenplay content"""
        if self.screenplay_file.exists():
            return self.screenplay_file.read_text(encoding='utf-8')
        return ""

    def write_screenplay(self, content: str) -> bool:
        """Write screenplay content and auto-commit"""
        try:
            self.screenplay_file.write_text(content, encoding='utf-8')

            # Generate and save FDX automatically
            parser = FountainParser(content)
            parser.estimate_pages()
            fdx_content = parser.to_fdx(
                self.metadata.get(
                    'title', 'Untitled'), self.metadata.get(
                    'author', 'Unknown'))

            fdx_file = self.project_dir / f"{self.project_dir.name}.fdx"
            fdx_file.write_text(fdx_content, encoding='utf-8')

            # Auto-commit with timestamp
            subprocess.run(
                ["git", "add", "screenplay.fountain", fdx_file.name],
                cwd=self.project_dir,
                capture_output=True,
                check=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"Auto-save: {datetime.now().isoformat()}"],
                cwd=self.project_dir,
                capture_output=True
            )

            # Update metadata
            self.metadata['word_count'] = len(content.split())
            self.metadata['page_count'] = int(
                parser.elements[-1].page_estimate) if parser.elements else 0
            self.save_metadata()

            return True
        except Exception as e:
            print(f"Write screenplay error: {e}")
            return False

    def reorder_beats(self, source_index: int, target_index: int) -> bool:
        """Reorder beats natively in the plaintext screenplay"""
        content = self.read_screenplay()
        parser = FountainParser(content)
        beats = parser.extract_beats()

        if source_index < 0 or source_index >= len(
                beats) or target_index < 0 or target_index >= len(beats):
            return False

        source_beat = beats[source_index]

        lines = content.split('\n')
        # Extract the source chunk
        source_chunk = lines[source_beat['start_line']
            :source_beat['end_line'] + 1]

        # Remove source chunk from lines
        del lines[source_beat['start_line']:source_beat['end_line'] + 1]

        # We need to re-evaluate the target line because removing the source chunk shifts lines.
        # So we recalculate the target insertion point.
        # Alternatively, parse the modified lines again and insert before the
        # target beat.
        new_content = '\n'.join(lines)
        new_parser = FountainParser(new_content)
        new_beats = new_parser.extract_beats()

        # If target_index was after source_index, the target beat's index in
        # the new list is target_index - 1
        adjusted_target = target_index if source_index > target_index else target_index

        if adjusted_target >= len(new_beats):
            # Insert at the end
            lines.extend(source_chunk)
        else:
            target_beat = new_beats[adjusted_target]
            insertion_point = target_beat['start_line']
            lines[insertion_point:insertion_point] = source_chunk

        return self.write_screenplay('\n'.join(lines))

    def create_branch(self, branch_name: str) -> Dict[str, str]:
        """Create a non-linear editing branch"""
        try:
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            self.metadata['current_branch'] = branch_name
            self.save_metadata()
            return {"status": "success", "branch": branch_name,
                    "message": f"Branch '{branch_name}' created"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": e.stderr}

    def list_branches(self) -> List[str]:
        """List all branches"""
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            branches = [b.strip().lstrip('* ')
                        for b in result.stdout.split('\n') if b.strip()]
            return branches
        except BaseException:
            return []

    def merge_branch(self, branch_name: str) -> Dict[str, str]:
        """Merge a branch into current branch"""
        try:
            result = subprocess.run(
                ["git", "merge", branch_name],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return {"status": "success", "message": f"Merged '{branch_name}'"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": e.stderr}

    def get_git_log(self) -> List[Dict[str, str]]:
        """Get commit history"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-20"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    commits.append(
                        {"hash": parts[0], "message": parts[1] if len(parts) > 1 else ""})
            return commits
        except BaseException:
            return []

    def start_sprint(self, sprint_name: str,
                     target_pages: int = 10) -> Dict[str, Any]:
        """Start a writing sprint with page target"""
        sprints = self.load_sprints()
        sprint = {
            'id': f"sprint_{len(sprints)}",
            'name': sprint_name,
            'created': datetime.now().isoformat(),
            'target_pages': target_pages,
            'start_page': self.metadata['page_count'],
            'end_page': None,
            'duration_minutes': 0,
            'completed': False,
        }
        sprints.append(sprint)
        self.save_sprints(sprints)
        return sprint

    def end_sprint(self, sprint_id: str) -> Dict[str, Any]:
        """End current sprint"""
        sprints = self.load_sprints()
        sprint = next((s for s in sprints if s['id'] == sprint_id), None)
        if sprint:
            sprint['end_page'] = self.metadata['page_count']
            sprint['completed'] = True
            self.save_sprints(sprints)
            return sprint
        return {}

    def load_sprints(self) -> List[Dict[str, Any]]:
        """Load sprint history"""
        if self.sprints_file.exists():
            with open(self.sprints_file) as f:
                return json.load(f)
        return []

    def save_sprints(self, sprints: List[Dict[str, Any]]):
        """Save sprint history"""
        with open(self.sprints_file, 'w') as f:
            json.dump(sprints, f, indent=2)


# Global state
SCREENWRITING_PROJECT = None
PROJECTS_DIR = Path("C:/AI-BS/screenplay_projects")
PROJECTS_DIR.mkdir(exist_ok=True, parents=True)


def list_projects() -> List[str]:
    """Return a list of all project folder names"""
    if not PROJECTS_DIR.exists():
        return []
    return [d.name for d in PROJECTS_DIR.iterdir() if d.is_dir()]


def init_project(project_name: str = None) -> ScreenplayProject:
    """Initialize or switch to a screenwriting project"""
    global SCREENWRITING_PROJECT

    # Handle legacy migration
    legacy_dir = Path.cwd() / "screenplay_project"
    if legacy_dir.exists() and not list_projects():
        try:
            shutil.move(str(legacy_dir), str(PROJECTS_DIR / "Default Project"))
        except Exception:
            pass

    projects = list_projects()
    if not project_name:
        if projects:
            project_name = projects[0]
        else:
            project_name = "Default Project"

    project_path = PROJECTS_DIR / project_name
    SCREENWRITING_PROJECT = ScreenplayProject(project_path)
    return SCREENWRITING_PROJECT


def import_project(project_name: str, content: str) -> ScreenplayProject:
    global SCREENWRITING_PROJECT
    project_path = PROJECTS_DIR / project_name
    project = ScreenplayProject(project_path)
    project.write_screenplay(content)
    SCREENWRITING_PROJECT = project
    return project
