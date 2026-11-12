"""Render non-destructive motion-poster films and original synthesized scores.

Poster sources stay untouched. Generated composites, clips and QA frames live in
work/; finished H.264/AAC files and original WAV scores live in videos/.
"""
from __future__ import annotations

import concurrent.futures
import json
import math
import subprocess
import time
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
VIDEOS = ROOT / "videos"
FPS = 24
SIZE = (1080, 1920)
SR = 48000
SPEC = json.loads((ROOT / "generation-prompts.json").read_text(encoding="utf-8-sig"))
POSTERS = {p["id"]: p for p in SPEC["posters"]}
FILMS = [
    {"id": "01-all-the-versions", "title": "All the versions", "seconds": 4.75,
     "posters": [p["id"] for p in SPEC["posters"]], "music": "warm", "bpm": 88},
    {"id": "02-chaos-and-comedy", "title": "Chaos and comedy", "seconds": 4.75,
     "posters": ["02-animation", "03-comical", "07-dark-humor", "06-frustrating"],
     "music": "comic", "bpm": 104},
    {"id": "03-still-here", "title": "Still here", "seconds": 5.5,
     "posters": ["05-emotional", "04-supportive", "01-realistic", "08-underdogs", "09-contemporary"],
     "music": "ambient", "bpm": 72},
]
for folder in [WORK, WORK / "canvases", WORK / "clips", WORK / "logs", WORK / "qa", VIDEOS]:
    folder.mkdir(parents=True, exist_ok=True)


def run(args, log_name):
    with (WORK / "logs" / log_name).open("w", encoding="utf-8") as log:
        p = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=False)
    if p.returncode:
        tail = (WORK / "logs" / log_name).read_text(encoding="utf-8", errors="replace")[-5000:]
        raise RuntimeError(f"Command failed ({p.returncode}): {tail}")


def canvas(poster_id):
    target = WORK / "canvases" / (poster_id + "-v2.png")
    source = ROOT / (poster_id + ".png")
    if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        return target
    art = Image.open(source).convert("RGB")
    # Soft reflected color supplies atmosphere without competing with the art.
    reflected = art.resize((180, 320), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(26))
    reflected = reflected.resize((2160, 3840), Image.Resampling.BICUBIC)
    reflected = Image.blend(reflected, Image.new("RGB", reflected.size, "#101318"), .82)
    c = reflected.convert("RGBA")
    factor = min(2000 / art.width, 3000 / art.height)
    art = art.resize((round(art.width * factor), round(art.height * factor)), Image.Resampling.LANCZOS)
    x, y = (2160 - art.width) // 2, 380 + (3000 - art.height) // 2
    shadow = Image.new("RGBA", c.size)
    sd = ImageDraw.Draw(shadow)
    sd.rectangle((x - 8, y + 16, x + art.width + 8, y + art.height + 40), fill=(0, 0, 0, 180))
    c = Image.alpha_composite(c, shadow.filter(ImageFilter.GaussianBlur(28)))
    c.paste(art, (x, y))
    d = ImageDraw.Draw(c)
    d.rectangle((x - 3, y - 3, x + art.width + 2, y + art.height + 2), outline=(223, 213, 191, 170), width=3)
    bold = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 68)
    light = ImageFont.truetype("C:/Windows/Fonts/segoeuil.ttf", 55)
    small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 43)
    d.text((1080, 145), "SEAN + BRETT", font=bold, anchor="mm", fill="#e6dbc7")
    d.line((890, 235, 1270, 235), fill="#a99473", width=3)
    label = POSTERS[poster_id]["category"].upper()
    d.text((1080, 3515), label, font=light, anchor="mm", fill="#eee6d8")
    d.text((1080, 3640), "EVERY VERSION. SAME BROTHERHOOD.", font=small, anchor="mm", fill="#baaf9c")
    c.convert("RGB").save(target)
    return target


def render_clip(poster_id, seconds):
    frames = round(seconds * FPS)
    target = WORK / "clips" / f"{poster_id}-{frames}-v2.mp4"
    source = ROOT / (poster_id + ".png")
    if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        return target
    source_canvas = canvas(poster_id)
    direction = 1 if int(poster_id[:2]) % 2 else -1
    # All edges remain in-frame: maximum zoom is 1.012, under the safe margins.
    z = f"1+0.012*(1-cos(PI*on/{frames-1}))/2"
    xx = f"iw/2-iw/zoom/2+{direction}*5*sin(PI*on/{frames-1})"
    yy = f"ih/2-ih/zoom/2+3*sin(PI*on/{frames-1})"
    vf = (f"zoompan=z='{z}':x='{xx}':y='{yy}':d={frames}:s=1080x1920:fps={FPS},"
          f"fade=t=in:st=0:d=0.25,fade=t=out:st={seconds-.25}:d=0.25,format=yuv420p")
    run(["ffmpeg", "-hide_banner", "-y", "-threads", "2", "-i", str(source_canvas),
         "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264",
         "-preset", "fast", "-crf", "18", "-threads", "2", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(target)], f"{poster_id}-{frames}.log")
    print(f"CLIP_READY {poster_id} {seconds}s", flush=True)
    return target


def score(film, seconds):
    """A new deterministic composition: additive pads/plucks and light percussion."""
    target = VIDEOS / (film["id"] + "-original-score.wav")
    n = math.ceil(seconds * SR)
    out = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(20261102 + int(film["id"][:2]))
    mode, bpm = film["music"], film["bpm"]
    beat = 60 / bpm
    # Original phrase over F(add9), Dm7, Bb(add9), C(add6).
    chords = [[53, 57, 60, 67], [50, 57, 60, 65], [46, 53, 60, 65], [48, 55, 57, 64]]

    def note(start, length, midi, amp, kind="pluck", pan=0):
        first = max(0, int(start * SR))
        count = min(n - first, max(1, int(length * SR)))
        if count <= 0:
            return
        t = np.arange(count, dtype=np.float64) / SR
        f = 440 * 2 ** ((midi - 69) / 12)
        if kind == "pad":
            env = np.minimum(t / 1.1, 1) * np.minimum(np.maximum(length - t, 0) / 1.4, 1)
            a = np.sin(2 * np.pi * f * t) + .17 * np.sin(2 * np.pi * f * 2 * t)
            b = np.sin(2 * np.pi * f * 1.0012 * t) + .17 * np.sin(2 * np.pi * f * 1.999 * t)
            out[first:first+count, 0] += amp * env * a
            out[first:first+count, 1] += amp * env * b
            return
        if kind == "bass":
            env = (1 - np.exp(-70 * t)) * np.exp(-4.0 * t)
            s = .9 * np.sin(2 * np.pi * f * t) + .1 * np.sin(2 * np.pi * 2 * f * t)
        else:
            decay = 5.5 if mode == "comic" else 2.7
            env = (1 - np.exp(-100 * t)) * np.exp(-decay * t)
            s = (np.sin(2 * np.pi * f * t) + .28 * np.sin(2 * np.pi * f * 2.01 * t)
                 + .09 * np.sin(2 * np.pi * f * 3.0 * t))
        env *= np.minimum(np.maximum(length - t, 0) / .06, 1)
        left = math.sqrt((1-pan)/2)
        right = math.sqrt((1+pan)/2)
        out[first:first+count, 0] += amp * env * s * left
        out[first:first+count, 1] += amp * env * s * right

    chord_seconds = beat * 8
    for k, start in enumerate(np.arange(0, seconds, chord_seconds)):
        chord = chords[k % len(chords)]
        for pitch in chord:
            note(float(start), chord_seconds + 1.5, pitch, .032 if mode != "comic" else .018, "pad")
    motif = [0, 2, 1, 3, 2, 1, 0, 2]
    subdivision = 1.0 if mode == "ambient" else .5
    for k, start in enumerate(np.arange(.18, seconds - .5, beat * subdivision)):
        chord = chords[int(start // chord_seconds) % len(chords)]
        pitch = chord[motif[k % len(motif)]] + 12
        if mode == "ambient" and k % 3 == 2:
            continue
        if mode == "warm" and k % 4 == 3:
            continue
        note(float(start), 2.1, pitch, .045 if mode == "ambient" else .055, pan=(-.35 if k % 2 else .35))
        if mode != "ambient" and k % 2 == 0:
            note(float(start), .7, chord[0] - 12, .075, "bass")
    if mode in ("comic", "warm"):
        for k, start in enumerate(np.arange(0, seconds-.2, beat)):
            first = int(start * SR)
            count = min(int(.12*SR), n-first)
            t = np.arange(count) / SR
            # Gentle hand-tap / shaker made entirely from seeded noise and sine.
            noise = rng.standard_normal(count)
            tap = noise * np.exp(-t*70) * (.012 if mode == "comic" else .005)
            if k % 2 == 0:
                tap += np.sin(2*np.pi*(82*t - 60*t*t)) * np.exp(-t*35) * .05
            out[first:first+count] += tap[:, None]
    # A quiet stereo reflection supplies space, not an external sampled effect.
    delay = int(.27 * SR)
    out[delay:] += .12 * out[:-delay, ::-1].copy()
    fade_in = np.minimum(np.arange(n) / (SR * .7), 1)
    fade_out = np.minimum(np.arange(n)[::-1] / (SR * 1.6), 1)
    out *= (fade_in * fade_out)[:, None]
    peak = float(np.max(np.abs(out)))
    out *= .76 / max(peak, 1e-12)
    with wave.open(str(target), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(out, -1, 1)*32767).astype("<i2").tobytes())
    return target


def render_brett_stinger():
    """Authorized real video appears only as a clearly labeled Brett solo coda."""
    target = WORK / "clips" / "brett-off-script-90.mp4"
    source = Path("C:/Users/footb/AppData/Local/Temp/Snapchat-1618072376.mp4")
    overlay = WORK / "canvases" / "brett-off-script-label.png"
    label = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    d = ImageDraw.Draw(label)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 36)
    d.text((540, 61), "BRETT / OFF SCRIPT", font=font, anchor="mm", fill="#e6dbc7")
    label.save(overlay)
    vf = ("[0:v]fps=24,scale=960:1706:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x101318[base];"
          "[base][1:v]overlay=0:0,fade=t=in:st=0:d=0.25,"
          "fade=t=out:st=3.5:d=0.25,format=yuv420p[v]")
    run(["ffmpeg", "-hide_banner", "-y", "-threads", "2", "-i", str(source), "-i", str(overlay),
         "-filter_complex", vf, "-map", "[v]", "-frames:v", "90", "-an", "-c:v", "libx264",
         "-preset", "fast", "-crf", "18", "-threads", "2", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(target)], "brett-off-script.log")
    return target


def verify(film, target, seconds):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target)],
                       capture_output=True, text=True, check=True)
    probe = json.loads(p.stdout)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    assert (video["width"], video["height"]) == SIZE
    assert video["r_frame_rate"] == "24/1"
    assert video["pix_fmt"] == "yuv420p"
    assert video["codec_name"] == "h264" and audio["codec_name"] == "aac"
    assert audio["channels"] == 2
    assert int(audio["sample_rate"]) == SR
    assert abs(float(probe["format"]["duration"]) - seconds) < .15
    # Decode the entire deliverable to catch broken/truncated bitstreams.
    run(["ffmpeg", "-hide_banner", "-v", "error", "-threads", "2", "-i", str(target),
         "-f", "null", "-"], film["id"] + "-decode.log")
    frames = []
    for k, point in enumerate([1.5, seconds / 2, seconds - 1.5]):
        still = WORK / "qa" / f"{film['id']}-{k+1}.png"
        run(["ffmpeg", "-hide_banner", "-y", "-threads", "2", "-ss", str(point), "-i", str(target),
             "-frames:v", "1", "-update", "1", str(still)], film["id"] + f"-frame-{k+1}.log")
        im = Image.open(still)
        assert im.size == SIZE and np.asarray(im).std() > 10
        frames.append({"timestamp": point, "path": str(still)})
    # Two actual decoded frames within a chapter must differ: genuine camera motion.
    motion_frames = []
    for point in [.6, 3.5]:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-ss", str(point), "-i", str(target),
                              "-frames:v", "1", "-vf", "scale=270:480", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        motion_frames.append(np.frombuffer(raw, dtype=np.uint8).astype(np.float32))
    motion_delta = float(np.mean(np.abs(motion_frames[0] - motion_frames[1])))
    assert motion_delta > .2, f"No visible motion detected: {motion_delta}"
    return {"id": film["id"], "title": film["title"], "output": str(target),
            "duration_seconds": float(probe["format"]["duration"]), "resolution": list(SIZE),
            "fps": 24, "video_codec": video["codec_name"], "pixel_format": video["pix_fmt"],
            "audio_codec": audio["codec_name"], "audio_channels": audio["channels"],
            "audio_sample_rate": int(audio["sample_rate"]), "bytes": target.stat().st_size,
            "poster_order": film["posters"], "full_decode": "passed",
            "live_action_stinger": ({"subject": "Brett only", "duration": 3.75, "caption": "BRETT / OFF SCRIPT",
                                    "source": "C:/Users/footb/AppData/Local/Temp/Snapchat-1618072376.mp4",
                                    "source_audio": "muted; original instrumental score only"}
                                   if film["id"] == "02-chaos-and-comedy" else None),
            "camera_motion_pixel_delta": motion_delta, "decoded_qa_frames": frames,
            "visual_qa": "pending human-style visual inspection of decoded QA frames",
            "audio": {"composition": "Original locally synthesized instrumental; no external samples or voices",
                      "style": film["music"], "bpm": film["bpm"], "source": str(VIDEOS / (film["id"] + "-original-score.wav"))},
            "source_policy": "Original PNGs unmodified. Artistic friendship illustrations, not historical event footage.",
            "render": {"camera_zoom_range": [1.0, 1.012], "transition": ".25s fade-out / .25s fade-in through dark",
                       "encoder": "libx264, CRF18, fast, yuv420p; AAC192k; faststart", "max_concurrent_encoders": 2}}


def render_film(film, pool):
    print(f"FILM_START {film['id']}", flush=True)
    pending = []
    for poster_id in film["posters"]:
        source = ROOT / (poster_id + ".png")
        reported = False
        while not source.exists():
            if not reported:
                print(f"WAITING_SOURCE {poster_id}", flush=True)
                reported = True
            time.sleep(5)
        pending.append(pool.submit(render_clip, poster_id, film["seconds"]))
    clips = [job.result() for job in pending]
    seconds = len(clips) * film["seconds"]
    if film["id"] == "02-chaos-and-comedy":
        clips.append(render_brett_stinger())
        seconds += 3.75
    original_score = score(film, seconds)
    concat_file = WORK / (film["id"] + "-concat.txt")
    concat_file.write_text("".join("file '" + clip.as_posix().replace("'", "'\\''") + "'\n" for clip in clips), encoding="utf-8")
    target = VIDEOS / (film["id"] + ".mp4")
    run(["ffmpeg", "-hide_banner", "-y", "-threads", "2", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-i", str(original_score), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-18:TP=-1.5:LRA=8", "-ar", str(SR),
         "-t", str(seconds), "-movflags", "+faststart", str(target)], film["id"] + "-mux.log")
    receipt = verify(film, target, seconds)
    (VIDEOS / (film["id"] + ".receipt.json")).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("FILM_READY " + json.dumps(receipt), flush=True)
    return receipt


if __name__ == "__main__":
    receipts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Complete the quiet film while the final comedy source may still render.
        for film in sorted(FILMS, key=lambda f: (f["id"] != "03-still-here", f["id"])):
            receipts.append(render_film(film, executor))
    receipts.sort(key=lambda r: r["id"])
    (VIDEOS / "video-receipt.json").write_text(json.dumps({"films": receipts}, indent=2), encoding="utf-8")
    print("ALL_FILMS_COMPLETE", flush=True)
