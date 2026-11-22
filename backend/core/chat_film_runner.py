"""Sequential durable Comfy jobs and local MP4 assembly, without submission replay."""
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import threading
import time
import httpx
from .chat_film_store import FilmStore
from .coding_locks import record_lock
from .video_workflows import build_core_wan_graph

COMFY = 'http://127.0.0.1:8189'
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'ComfyUI/ComfyUI/output'
FFMPEG = ROOT / 'ComfyUI/python_embeded/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
_threads = {}
_guard = threading.Lock()


def start(owner, film_id, store=None):
    store = store or FilmStore()
    key = (str(store.root), owner, film_id)
    with _guard:
        if key in _threads and _threads[key].is_alive():
            return
        thread = threading.Thread(target=run, args=(owner,film_id,store), daemon=True)
        _threads[key] = thread
        thread.start()


def output_path(descriptor, prefix):
    if descriptor.get('type') != 'output':
        raise ValueError('Comfy result is not a saved output')
    path = (OUTPUT / descriptor.get('subfolder','') / descriptor['filename']).resolve()
    if not path.is_relative_to(OUTPUT.resolve()) or path.suffix.lower() != '.mp4' or not path.name.startswith(prefix):
        raise ValueError('Unexpected Comfy output path')
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('Comfy output missing or empty')
    return path


def assemble(owner, film, store):
    folder = store.directory(owner, film['id'])
    if not FFMPEG.is_file():
        raise ValueError('FFmpeg is unavailable')
    # Each output name is service-generated; never interpolate script text in commands.
    clips = []
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
    for shot in film['shots']:
        source = Path(shot['output'])
        if not source.resolve().is_relative_to(OUTPUT.resolve()) or hashlib.sha256(source.read_bytes()).hexdigest() != shot['sha256']:
            raise ValueError('Retained clip changed; assembly stopped')
        clip = folder / f"trim-{shot['number']}-{film['revision']}.mp4"
        subprocess.run([str(FFMPEG),'-nostdin','-v','error','-n','-i',str(source),'-t',str(shot['seconds']),'-an','-vf','fps=16,format=yuv420p','-c:v','libx264',str(clip)],check=True,timeout=180,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=flags)
        clips.append(clip)
    listing = folder / f"concat-{film['revision']}.txt"
    listing.write_text(''.join(f"file '{clip.name}'\n" for clip in clips),encoding='utf-8')
    destination = folder / f"film-{film['revision']}.mp4"
    subprocess.run([str(FFMPEG),'-nostdin','-v','error','-n','-f','concat','-safe','1','-i',str(listing),'-c','copy','-movflags','+faststart',str(destination)],check=True,timeout=180,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=flags)
    if not destination.is_file() or destination.stat().st_size == 0:
        raise ValueError('Assembly produced no output')
    return str(destination)


def run(owner, film_id, store):
    try:
        with record_lock(store.root/'render-worker.lock'):
            with httpx.Client(timeout=20,trust_env=False,follow_redirects=False) as client:
                while True:
                    film = store.get(owner,film_id)
                    if not film['run_requested']:
                        return
                    shot = next((s for s in film['shots'] if s['state'] != 'complete'),None)
                    if shot is None:
                        if film['assemble_requested']:
                            film['state']='assembling';store.save(owner,film)
                            destination=assemble(owner,film,store)
                            film=store.get(owner,film_id)
                            film.update(state='complete',output=destination,run_requested=False,error=None)
                        else:
                            film.update(state='clips_ready',run_requested=False,error=None)
                        store.save(owner,film);return
                    index=shot['number']-1
                    prefix=f"film_{film_id}_{shot['number']}"
                    if shot['state'] in ('submitting','uncertain'):
                        raise ValueError('Submission outcome uncertain; reconcile Comfy history before resubmitting')
                    if shot['state']=='planned':
                        info=client.get(COMFY+'/object_info');info.raise_for_status()
                        graph=build_core_wan_graph(shot['prompt'],info.json(),length=shot['seconds']*16+1,prefix=prefix,seed=42+index)
                        shot['state']='submitting';film['state']='rendering';store.save(owner,film)
                        # The durable submitting marker precedes the sole POST. Never auto-replay it.
                        response=client.post(COMFY+'/prompt',json={'prompt':graph,'client_id':film_id,'extra_data':{'aibs_film':film_id,'shot':index+1}})
                        response.raise_for_status();prompt_id=response.json().get('prompt_id')
                        if not isinstance(prompt_id,str) or not prompt_id:
                            raise ValueError('Comfy did not return a job ID')
                        film=store.get(owner,film_id);shot=film['shots'][index]
                        shot.update(state='queued',prompt_id=prompt_id);store.save(owner,film)
                    deadline=time.monotonic()+3600
                    while time.monotonic()<deadline:
                        film=store.get(owner,film_id);shot=film['shots'][index]
                        if not film['run_requested']:
                            return  # Current remote render is retained; do not interrupt another user's GPU work.
                        response=client.get(COMFY+'/history/'+shot['prompt_id']);response.raise_for_status()
                        history=response.json().get(shot['prompt_id'])
                        if history:
                            if history.get('status',{}).get('status_str')=='error':
                                raise ValueError('Comfy reported a render error; retained job requires inspection')
                            candidates=[d for node in history.get('outputs',{}).values() for field in ('images','videos','gifs') for d in node.get(field,[]) if str(d.get('filename','')).lower().endswith('.mp4')]
                            if not candidates:
                                raise ValueError('Comfy finished without a saved MP4')
                            path=output_path(candidates[0],prefix)
                            shot.update(state='complete',output=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                            store.save(owner,film);break
                        time.sleep(2)
                    else:
                        raise ValueError('Render observation timed out; job ID retained for status/resume')
    except Exception as error:
        try:
            film=store.get(owner,film_id)
            film.update(state='held',run_requested=False,error=str(error)[:500] if isinstance(error,ValueError) else type(error).__name__)
            store.save(owner,film)
        except Exception:
            logging.getLogger(__name__).exception('Film failure receipt could not be saved; durable job markers retained')
