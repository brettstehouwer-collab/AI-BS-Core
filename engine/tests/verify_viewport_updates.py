"""Real mode2 publication; bounded publisher recovery is retained as evidence."""
from pathlib import Path
import json,os,queue,subprocess,sys,tempfile,threading,time,uuid
from verify_chapter_viewport import verify
from native_studio.game_engine.creator_payload import _Reader,_Writer
from native_studio.game_engine.creator_viewport import _replace_snapshot

def stress(host,viewport,output):
    output.mkdir(parents=True,exist_ok=True)
    proof=verify(host,output/'export')
    source=(output/'export/chapter-preview.aibv').read_bytes();r=_Reader(source);r.read(7)
    r.text();project,branch,world,checkpoint=r.text(),r.text(),r.text(),r.text();r.number('Q');r.text();content=r.read(r.number('I'))
    def packet(revision):
        identity=str(uuid.uuid4());w=_Writer();w.append(b'AIBV');w.number(1,'H');w.number(2,'B')
        for value in (identity,project,branch,world,checkpoint):w.text(value)
        w.number(revision,'Q');w.text('');w.number(len(content),'I');return identity,bytes(w.data)+content
    with tempfile.TemporaryDirectory(prefix='aibs-viewport-updates-') as temporary:
        root=Path(temporary);scene=root/'scene.aibv';stop=root/'stop';identity,data=packet(1);scene.write_bytes(data)
        process=subprocess.Popen([str(viewport),'--snapshot',str(scene),'--stop-file',str(stop)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        messages=queue.Queue();errors=[];ready=[];stderr=[];recoveries=[]
        def read_out():
            for line in iter(process.stdout.readline,b''):messages.put(line.decode('ascii',errors='replace').strip())
        def read_err():
            for line in iter(process.stderr.readline,b''):stderr.append(line.decode('utf-8',errors='replace').strip())
        readers=[threading.Thread(target=read_out),threading.Thread(target=read_err)]
        for thread in readers:thread.start()
        def pump():
            while True:
                try:line=messages.get_nowait()
                except queue.Empty:break
                if line.startswith('AIBV1 READY '):ready.append(line)
        def wait_ready(identity,revision,seconds=15):
            until=time.monotonic()+seconds;line=f'AIBV1 READY {identity} {world} {revision}'
            while time.monotonic()<until and line not in ready and process.poll() is None:pump();time.sleep(.003)
            pump()
            if line not in ready:raise AssertionError(f'Final native update missing: {line}; stderr={stderr}; ready={ready[-3:]}')
        try:
            wait_ready(identity,1)
            accepted=(identity,1)
            # Debug's canonical chapter validation holds the file for long enough
            # to overlap many replacements; Release is stressed the same way.
            for revision in range(2,302):
                identity,data=packet(revision);pending=root/'scene.tmp'
                with pending.open('wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
                try:
                    publication=_replace_snapshot(pending,scene);accepted=(identity,revision)
                    if publication.get('transient_errors'):
                        recoveries.append({'revision':revision,**publication})
                except OSError as error:errors.append({'revision':revision,'winerror':getattr(error,'winerror',None),'errno':error.errno,'message':str(error),
                    'attempts':getattr(error,'publication_attempts',1),'publication_errors':getattr(error,'publication_errors',[])})
                finally:pending.unlink(missing_ok=True)
                pump();time.sleep(.003)
            wait_ready(*accepted)
        finally:
            stop.write_bytes(b'stop')
            try:process.wait(timeout=10)
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=5)
                for thread in readers:thread.join(timeout=3)
                process.stdout.close();process.stderr.close();pump()
        result={'status':'passed' if not errors and process.returncode==0 and len(ready)>=3 else 'failed','publications':300,'replacement_errors':errors,'bounded_publication_recoveries':recoveries,'native_ready_count':len(ready),'final_ready':ready[-1] if ready else None,'native_stderr':stderr,'native_exit_code':process.returncode,'export_fingerprint':proof['content_fingerprint']}
        (output/'viewport-updates.json').write_text(json.dumps(result,indent=2)+'\n')
        if result['status']!='passed':raise AssertionError(json.dumps(result,indent=2))
        return result
if __name__=='__main__':print(json.dumps(stress(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3])),indent=2))
