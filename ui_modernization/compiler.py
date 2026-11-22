"""Deterministic, standard-library-only design-token compiler. No import I/O."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

class TokenError(ValueError):pass

GROUPS={
 'colors':('canvas','surface','raised','hover','border','divider','text','muted','cyan','violet','ready','warning','error','unavailable'),
 'spacing':('xs','sm','md','lg','xl','xxl'),
 'radius':('control','card','pill'),
 'typography':('body','caption','section','title','metric'),
 'density':('normal','mom'),
 'layout':('rail','rail_expanded','content_max','focus','control_height'),
}

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise TokenError('Duplicate token key: '+key)
        result[key]=value
    return result

def load_tokens(path):
    try:
        raw=Path(path).read_bytes()
        if len(raw)>65536:raise TokenError('Token file exceeds 64 KiB')
        return json.loads(raw,object_pairs_hook=_pairs,
                          parse_constant=lambda _:(_ for _ in ()).throw(TokenError('Non-finite token')))
    except (OSError,UnicodeError,json.JSONDecodeError) as error:
        raise TokenError('Cannot read a complete token specification') from error

def contrast(a,b):
    def luminance(color):
        channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
        return sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)

def validate(tokens):
    expected={'schema_version','name','font_family',*GROUPS}
    if type(tokens) is not dict or set(tokens)!=expected:raise TokenError('Unexpected or missing token group')
    if type(tokens['schema_version']) is not int or tokens['schema_version']!=1:raise TokenError('Unsupported schema version')
    if tokens['name']!='aibs-fluent-zinc':raise TokenError('Unknown theme name')
    if type(tokens['font_family']) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9 ]{1,50}',tokens['font_family']):
        raise TokenError('Unsafe font family')
    for group,keys in GROUPS.items():
        values=tokens[group]
        if type(values) is not dict or set(values)!=set(keys):raise TokenError('Unexpected or missing '+group+' token')
        for key,value in values.items():
            if group=='colors':
                valid=type(value) is str and re.fullmatch(r'#[0-9A-Fa-f]{6}',value)
            elif group=='density':
                valid=type(value) in (int,float) and math.isfinite(value) and (value==1 if key=='normal' else 1.2<=value<=1.5)
            else:valid=type(value) is int and 1<=value<=1600
            if not valid:raise TokenError('Invalid token: '+group+'.'+key)
    colors=tokens['colors']
    for fg in ('text','muted'):
        for bg in ('canvas','surface','raised'):
            if contrast(colors[fg],colors[bg])<4.5:raise TokenError('Insufficient text contrast: '+fg+'/'+bg)
    if not tokens['layout']['rail']<tokens['layout']['rail_expanded']<tokens['layout']['content_max']:
        raise TokenError('Invalid navigation dimensions')
    return tokens

def compile_tokens(tokens):
    validate(tokens)
    canonical=json.dumps(tokens,sort_keys=True,separators=(',',':')).encode()
    sha=hashlib.sha256(canonical).hexdigest()
    c=tokens['colors'];s=tokens['spacing'];r=tokens['radius'];t=tokens['typography'];l=tokens['layout']
    mom={key:round(value*tokens['density']['mom']) for key,value in t.items()}
    css=['/* Generated from tokens.json; do not edit. */',':root[data-aibs-ui="fluent"] {']
    for group in ('colors','spacing','radius','typography','layout'):
        stem={'colors':'color','spacing':'space','typography':'type'}.get(group,group)
        for key,value in sorted(tokens[group].items()):
            css.append(f'  --aibs-{stem}-{key.replace("_","-")}: {value}{"" if group=="colors" else "px"};')
    css.extend([f'  --aibs-font-family: "{tokens["font_family"]}";','}',
                ':root[data-aibs-ui="fluent"][data-density="mom"] {'])
    css.extend(f'  --aibs-type-{key}: {value}px;' for key,value in sorted(mom.items()))
    css.extend([f'  --aibs-layout-control-height: {round(l["control_height"]*tokens["density"]["mom"])}px;','}',''])
    qss=[]
    def rule(selector,declarations):qss.append(selector+' { '+declarations+' }')
    root='QWidget#aibsUiPreview'
    def child(selector):return root+' '+selector
    rule(root,f'background:{c["canvas"]}; color:{c["text"]}; font-family:"{tokens["font_family"]}"; font-size:{t["body"]}px;')
    rule(child('QLabel'),f'background:transparent; color:{c["text"]}; font-size:{t["body"]}px;')
    rule(child('QLabel[aibsRole="muted"]'),f'color:{c["muted"]}; font-size:{t["caption"]}px;')
    rule(child('QLabel[aibsRole="eyebrow"]'),f'color:{c["cyan"]}; font-size:{t["caption"]}px; font-weight:600;')
    rule(child('QLabel[aibsRole="pageTitle"]'),f'font-size:{t["title"]}px; font-weight:700;')
    rule(child('QLabel[aibsRole="sectionTitle"]'),f'font-size:{t["section"]}px; font-weight:600;')
    rule(child('QLabel[aibsRole="metricValue"]'),f'font-size:{t["metric"]}px; font-weight:700; color:{c["cyan"]};')
    rule(child('QLabel[aibsAccent="violet"]'),f'color:{c["violet"]};')
    for state,color in [('ready','ready'),('held','warning'),('warning','violet'),('unavailable','unavailable')]:
        rule(child(f'QLabel[aibsState="{state}"]'),f'color:{c[color]}; background:{c["raised"]}; border:1px solid {c["divider"]}; border-radius:{r["pill"]}px; padding:5px 9px; font-size:{t["caption"]}px;')
    rule(child('QFrame[aibsRole="card"]'),f'background:{c["surface"]}; border:1px solid {c["divider"]}; border-radius:{r["card"]}px;')
    rule(child('QFrame[aibsRole="rail"]'),f'background:{c["surface"]}; border:0; border-right:1px solid {c["divider"]};')
    rule(child('QScrollArea'),f'background:{c["canvas"]}; border:0;')
    rule(child('QScrollArea > QWidget > QWidget'),f'background:{c["canvas"]};')
    for selector in ('QPushButton','QLineEdit','QComboBox'):
        rule(child(selector),f'background:{c["raised"]}; color:{c["text"]}; font-size:{t["body"]}px; border:1px solid {c["border"]}; border-radius:{r["control"]}px; padding:{s["sm"]}px {s["md"]}px; min-height:{l["control_height"]-18}px;')
        rule(child(selector+':focus'),f'border:{l["focus"]}px solid {c["cyan"]};')
    rule(child('QPushButton:hover'),f'background:{c["hover"]};')
    rule(child('QPushButton:checked'),f'border:1px solid {c["cyan"]}; color:{c["cyan"]};')
    rule(child('QPushButton[aibsRole="nav"]'),f'background:transparent; border:1px solid transparent; text-align:left;')
    rule(child('QPushButton[aibsRole="nav"]:checked'),f'border:1px solid {c["cyan"]}; background:{c["raised"]}; color:{c["cyan"]};')
    rule(child('QPushButton[aibsRole="primary"]'),f'background:{c["cyan"]}; color:{c["canvas"]}; border:1px solid {c["cyan"]}; font-weight:600;')
    rule(child('QPushButton:disabled'),f'color:{c["muted"]}; background:{c["surface"]}; border-color:{c["divider"]};')
    rule(child('QTableWidget'),f'background:{c["surface"]}; alternate-background-color:{c["raised"]}; color:{c["text"]}; border:0; gridline-color:{c["divider"]}; selection-background-color:{c["hover"]};')
    rule(child('QHeaderView::section'),f'background:{c["surface"]}; color:{c["muted"]}; border:0; border-bottom:1px solid {c["divider"]}; padding:{s["sm"]}px; text-align:left;')
    rule(child('QCheckBox'),f'color:{c["text"]}; font-size:{t["body"]}px; spacing:{s["sm"]}px;')
    rule(child('QCheckBox::indicator'),f'width:18px; height:18px; border:1px solid {c["border"]}; border-radius:4px; background:{c["raised"]};')
    rule(child('QCheckBox::indicator:checked'),f'background:{c["cyan"]}; border-color:{c["cyan"]};')
    momroot=root+'[aibsDensity="mom"]'
    rule(momroot,f'font-size:{mom["body"]}px;')
    for selector in ('QLabel','QPushButton','QLineEdit','QComboBox','QCheckBox','QTableWidget','QHeaderView::section'):
        rule(momroot+' '+selector,f'font-size:{mom["body"]}px;')
    rule(momroot+' QLabel[aibsState]',f'font-size:{mom["caption"]}px;')
    for role,size in [('muted','caption'),('eyebrow','caption'),('pageTitle','title'),('sectionTitle','section'),('metricValue','metric')]:
        rule(momroot+f' QLabel[aibsRole="{role}"]',f'font-size:{mom[size]}px;')
    native=['# Generated from tokens.json; do not edit.',f'TOKEN_SHA256 = {sha!r}',
            f'COLORS = {dict(sorted(c.items()))!r}',f'SPACING = {dict(sorted(s.items()))!r}',
            f'RADIUS = {dict(sorted(r.items()))!r}',f'TYPOGRAPHY = {dict(sorted(t.items()))!r}',
            f'MOM_TYPOGRAPHY = {dict(sorted(mom.items()))!r}',f'LAYOUT = {dict(sorted(l.items()))!r}',
            f'FONT_FAMILY = {tokens["font_family"]!r}','']
    files={'tokens.css':'\n'.join(css).encode(),'theme_tokens.qss':('\n'.join(qss)+'\n').encode(),
           'native_palette.py':'\n'.join(native).encode()}
    manifest={'schema_version':1,'token_sha256':sha,
              'outputs':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}}
    files['token_manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    return files

def write_outputs(tokens,destination,protected_root=Path('C:/AI-BS')):
    files=compile_tokens(tokens)
    target=Path(destination).resolve();protected=Path(protected_root).resolve()
    if target==protected or protected in target.parents:raise TokenError('Refusing to write into the active workspace')
    target.mkdir(parents=True,exist_ok=True)
    for name in ('tokens.css','theme_tokens.qss','native_palette.py','token_manifest.json'):
        with tempfile.NamedTemporaryFile(dir=target,delete=False) as handle:
            temporary=Path(handle.name);handle.write(files[name]);handle.flush();os.fsync(handle.fileno())
        try:temporary.replace(target/name)
        finally:temporary.unlink(missing_ok=True)
    return files

def main():
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:files=write_outputs(load_tokens(args.source),args.output)
    except TokenError as error:parser.exit(2,str(error)+'\n')
    print(json.dumps({'files':sorted(files),'output':str(args.output.resolve())}))

if __name__=='__main__':main()
