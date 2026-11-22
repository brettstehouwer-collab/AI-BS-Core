"""Prepare an isolated full Python layout for the strict native package builder.

Copies the already used Python core without site-packages, then installs only
declared packaging/client dependencies. No global interpreter/PATH/registry edits.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('C:/AI-BS')
DEST=Path('C:/Users/Administrator/AppData/Local/AI-BS/packaging_python_20261111_v03')
QT=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages'


def require(value,message):
    if not value:raise RuntimeError(message)


def plain(path):
    for member in (path,*path.parents):
        require(not member.is_symlink() and not member.is_junction(),'Redirected packaging runtime path')


def run(command,label):
    with (DEST/(label+'.stdout.log')).open('xb') as out,(DEST/(label+'.stderr.log')).open('xb') as err:
        env={k:os.environ[k] for k in ('SystemRoot','WINDIR','TEMP','TMP') if k in os.environ}
        env.update(PATH=str(DEST)+';'+str(DEST/'Scripts')+';C:\\Windows\\System32',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
        child=subprocess.Popen(list(map(str,command)),env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        (DEST/(label+'.started.json')).write_text(json.dumps({'pid':child.pid,'command':list(map(str,command))}))
        start=time.monotonic()
        while child.poll() is None:time.sleep(.2)
        (DEST/(label+'.process.json')).write_text(json.dumps({'pid':child.pid,'terminal':True,'exit_code':child.returncode,'wall_seconds':time.monotonic()-start}))
        require(child.returncode==0,label+' failed; preserve logs/runtime without retrying')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true',required=True);parser.parse_args()
    source=Path(sys.base_prefix).resolve(strict=True);plain(source);plain(DEST)
    require(not DEST.exists(),'Preserve prior packaging runtime; destination must be new')
    files=[];total=0
    for here,dirs,names in os.walk(source,followlinks=False):
        dirs[:]=[n for n in dirs if n not in ('site-packages','__pycache__','.git')]
        for name in dirs:plain(Path(here)/name)
        for name in names:
            path=Path(here)/name;plain(path);relative=path.relative_to(source)
            total+=path.stat().st_size
            require(len(files)<12000 and total<512*1024**2,'Base Python copy exceeds bounded budget')
            files.append((relative,path))
    require((source/'python.exe').is_file() and (source/'Lib/os.py').is_file(),'Expected complete verified Python layout')
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.mkdir();rows={}
    for relative,path in files:
        raw=path.read_bytes();target=DEST/relative;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(raw)
        rows[relative.as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        require(hashlib.sha256(target.read_bytes()).hexdigest()==rows[relative.as_posix()]['sha256'],'Python core copy mismatch')
    (DEST/'core-copy.json').write_text(json.dumps({'source':str(source),'files':rows,'bytes':total},indent=2))
    probe='import sys,json;from pathlib import Path;root=Path(sys.executable).parent;assert Path(sys.prefix)==root and Path(sys.base_prefix)==root;assert all(not p or Path(p).is_relative_to(root) for p in sys.path);print(json.dumps({"version":sys.version,"prefix":sys.prefix,"paths":sys.path}))'
    run([DEST/'python.exe','-I','-B','-c',probe],'layout-probe')
    requirements=[]
    qt_versions={d.metadata['Name'].lower().replace('_','-'):d.version for d in metadata.distributions(path=[str(QT)])}
    for name in ('PyQt6','PyQt6-Qt6','PyQt6-sip'):
        require(name.lower() in qt_versions,'Reviewed isolated Qt distribution missing')
        requirements.append(name+'=='+qt_versions[name.lower()])
    for name in ('pyinstaller','pywin32','psutil','httpx','numpy','nvidia-ml-py','sounddevice','pyqtgraph','dearpygui'):
        try:version=metadata.version(name)
        except metadata.PackageNotFoundError:version=None
        requirements.append(name+('=='+version if version else ''))
    # This existing project requirement governs protected PDF source imports.
    writer=(ROOT/'native_studio/requirements-writer.txt').read_text()
    require('pypdf==6.14.2' in writer,'Reviewed writer requirement changed')
    requirements.append('pypdf==6.14.2')
    (DEST/'requirements.in').write_text('\n'.join(requirements)+'\n')
    run([DEST/'python.exe','-I','-B','-m','ensurepip','--upgrade'],'ensurepip')
    run([DEST/'python.exe','-I','-B','-m','pip','install','--disable-pip-version-check','--no-input',
         '--report',DEST/'install-report.json','-r',DEST/'requirements.in'],'install')
    run([DEST/'python.exe','-I','-B','-m','pip','freeze','--all'],'freeze')
    run([DEST/'python.exe','-I','-B','-c',probe],'final-layout-probe')
    (DEST/'preparation.json').write_text(json.dumps({'status':'PREPARED_ISOLATED_PACKAGING_PYTHON','source':str(source),'python':str(DEST/'python.exe'),'core_files':len(rows),'original_runtime_modified':False,'global_settings_modified':False},indent=2))
    print('PREPARED_ISOLATED_PACKAGING_PYTHON',flush=True)


if __name__=='__main__':main()
