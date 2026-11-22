"""Fresh bounded output directories for native recording contracts and decoding."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import uuid


def run(command, root, label, timeout=60):
    with (root / (label + '.stdout.log')).open('xb') as out, (root / (label + '.stderr.log')).open('xb') as err:
        child = subprocess.Popen([str(x) for x in command], stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            code = child.wait(timeout=timeout)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
        if code:
            raise AssertionError(f'{label} exited {code}: ' + (root / (label + '.stderr.log')).read_text(errors='replace')[-2000:])
    return {'label': label, 'pid': child.pid, 'exit_code': code, 'joined': child.poll() is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('encoder', 'readback'))
    for key in ('executable', 'ffmpeg', 'ffprobe', 'artifacts'):
        parser.add_argument(key, type=Path)
    parser.add_argument('--mock', type=Path)
    parser.add_argument('--shaders', type=Path)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=True)
    work = root / ('r' + uuid.uuid4().hex[:8])
    work.mkdir()
    result = {'status': 'failed', 'kind': args.kind, 'processes': [], 'audio_streams': None}
    try:
        if args.kind == 'encoder':
            assert args.mock is not None
            command = [args.executable, args.ffmpeg, args.mock, work]
            filename = "synthetic space & apostrophe's.mp4"
            report_name = 'synthetic.json'
        else:
            assert args.shaders is not None
            command = [args.executable, args.shaders, args.ffmpeg, work]
            filename = 'own-window-1080p.mp4'
            report_name = 'own-window.json'
        result['processes'].append(run(command, work, 'native', timeout=60))
        native = json.loads((work / report_name).read_text())
        movie = work / filename
        assert native['finished'] and not native['failed'] and not native['quarantined']
        result['processes'].append(run([args.ffprobe, '-v', 'error', '-show_streams', '-show_format',
                                       '-show_frames', '-of', 'json', movie], work, 'probe'))
        probe = json.loads((work / 'probe.stdout.log').read_text())
        assert len(probe['streams']) == 1
        stream = probe['streams'][0]
        assert stream['codec_type'] == 'video' and stream['codec_name'] == 'h264'
        assert (stream['width'], stream['height']) == (native['width'], native['height'])
        frames = probe['frames']
        assert len(frames) == native['frames_written']
        pts = [float(f['best_effort_timestamp_time']) for f in frames]
        assert all(b > a for a, b in zip(pts, pts[1:]))
        stamps = native['timestamps']
        expected = [t['write_complete_seconds'] - stamps[0]['write_complete_seconds'] for t in stamps]
        error = max(abs(a-b) for a, b in zip(pts, expected))
        assert error < .12
        duration = float(probe['format']['duration'])
        assert abs(duration - expected[-1]) < .15
        assert max(b-a for a,b in zip(pts,pts[1:])) > .15
        assert native['encoder_frame_capacity'] + native['producer_frame_capacity_peak'] <= 64*1024*1024
        hashes = []
        for index in (0, len(frames)//2, len(frames)-1):
            result['processes'].append(run([args.ffmpeg, '-v', 'error', '-i', movie, '-vf',
                f'select=eq(n\\,{index}),scale=160:90', '-frames:v', '1', '-f', 'rawvideo',
                '-pix_fmt', 'rgb24', 'pipe:1'], work, 'pixels-' + str(index)))
            pixels = (work / ('pixels-' + str(index) + '.stdout.log')).read_bytes()
            assert len(pixels) == 160*90*3
            colored = sum(max(pixels[i:i+3])-min(pixels[i:i+3]) > 12 and max(pixels[i:i+3]) > 20
                          for i in range(0,len(pixels),3))
            assert colored > 100, 'Decoded frame must contain visible rendered colors'
            hashes.append(hashlib.sha256(pixels).hexdigest())
        if args.kind == 'readback':
            assert len(set(hashes)) > 1
        result.update(status='passed', decoded_frames=len(frames), duration_seconds=duration,
                      decoded_fps=len(frames)/duration, maximum_pts_error_seconds=error,
                      audio_streams=0, actual_frame_hashes=hashes, video_bytes=movie.stat().st_size,
                      video_sha256=hashlib.sha256(movie.read_bytes()).hexdigest())
    finally:
        result['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
        (work / 'verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        print(work / 'verification.json')


if __name__ == '__main__':
    main()
