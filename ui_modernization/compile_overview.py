"""Compile page-scoped overview tokens for both actual application surfaces."""
from pathlib import Path
from ui_modernization.compiler import load_tokens,validate

ROOT=Path(__file__).resolve().parents[1]

def compile_overview():
    tokens=validate(load_tokens(ROOT/'ui_modernization/tokens.json'))
    c=tokens['colors'];t=tokens['typography'];root='QWidget#aibsStudioOverview'
    rules=[]
    def rule(selector,body):rules.append(selector+' { '+body+' }')
    def child(selector):return root+' '+selector
    rule(root,f'background:{c["canvas"]}; color:{c["text"]}; font-family:"Segoe UI"; font-size:14px;')
    rule(child('QWidget[overviewSurface="content"]'),f'background:{c["canvas"]};')
    rule(child('QLabel'),f'background:transparent; color:{c["text"]}; font-size:14px;')
    rule(child('QLabel[overviewRole="title"]'),f'font-size:{t["title"]}px; font-weight:700;')
    rule(child('QLabel[overviewRole="eyebrow"]'),f'color:{c["cyan"]}; font-size:12px; font-weight:600;')
    rule(child('QLabel[overviewRole="muted"]'),f'color:{c["muted"]}; font-size:12px;')
    rule(child('QFrame#Card'),f'background:{c["surface"]}; border:1px solid {c["divider"]}; border-radius:16px;')
    rule(child('QLabel#CardTitle'),f'color:{c["muted"]}; font-size:13px; font-weight:600; border:0;')
    rule(child('QLabel[overviewRole="metric"]'),f'color:{c["cyan"]}; font-size:28px; font-weight:700;')
    for item in ('QPushButton','QLineEdit','QComboBox'):
        rule(child(item),f'background:{c["raised"]}; color:{c["text"]}; border:1px solid {c["border"]}; border-radius:8px; padding:8px 12px; font-size:14px; min-height:20px;')
        rule(child(item+':focus'),f'border:2px solid {c["cyan"]};')
    rule(child('QPushButton:hover'),f'background:{c["hover"]};')
    rule(child('QPushButton:checked'),f'border-color:{c["cyan"]}; color:{c["cyan"]};')
    rule(child('QPushButton:disabled'),f'color:{c["muted"]}; background:{c["surface"]};')
    rule(child('QPushButton[overviewRole="primary"]'),f'background:{c["cyan"]}; color:{c["canvas"]}; font-weight:600;')
    rule(child('QPushButton[overviewRole="halt"]'),f'border-color:{c["error"]}; color:{c["error"]};')
    for item in ('QPlainTextEdit','QTableWidget'):
        rule(child(item),f'background:{c["canvas"]}; color:{c["text"]}; border:1px solid {c["divider"]}; border-radius:8px; padding:8px; font-size:14px; selection-background-color:{c["hover"]};')
    rule(child('QHeaderView::section'),f'background:{c["surface"]}; color:{c["muted"]}; padding:8px; border:0; font-size:12px; text-align:left;')
    rule(child('QScrollArea'),f'background:{c["canvas"]}; border:0;')
    rule(child('QScrollBar:vertical'),f'background:{c["canvas"]}; width:10px; margin:0; border:0;')
    rule(child('QScrollBar::handle:vertical'),f'background:{c["border"]}; min-height:30px; border-radius:5px;')
    rule(child('QScrollBar::add-line:vertical'), 'height:0;')
    rule(child('QScrollBar::sub-line:vertical'), 'height:0;')
    rule(child('QPushButton[overviewRole="secondary"]'),f'border-color:{c["violet"]}; color:{c["violet"]};')
    rule(child('QSplitter::handle'),f'background:{c["divider"]};')
    qss=ROOT/'ui_modernization/generated/studio_overview.qss';text='\n'.join(rules)+'\n';qss.write_text(text,encoding='utf-8',newline='\n')
    qss.with_suffix('.py').write_text('# Generated from tokens.json; static import supports frozen native builds.\nOVERVIEW_QSS = '+repr(text)+'\n',encoding='utf-8',newline='\n')
    lines=['/* Generated from ui_modernization/tokens.json; page scope only. */','.aibs-studio-overview {']
    for key,value in c.items():lines.append(f'  --overview-{key}: {value};')
    lines.append('}')
    css='\n'.join(lines)+'\n'
    for prefix in ('src/components','components','src/components/components','components/components'):
        (ROOT/'frontend'/prefix/'StudioOverview.tokens.css').write_text(css,encoding='utf-8',newline='\n')

if __name__=='__main__':compile_overview()
