import os
import sys
import time
import json
import argparse
import traceback

def main():
    parser = argparse.ArgumentParser(description="Demucs CUDA Stem Separation Worker")
    parser.add_argument("--input", required=True, help="Input audio file path")
    parser.add_argument("--output-dir", required=True, help="Target folder for stems")
    parser.add_argument("--session-id", required=True, help="Session ID string")
    parser.add_argument("--model", default="htdemucs", help="Model name (htdemucs, htdemucs_ft, mdx_extra_q)")
    parser.add_argument("--device", default="auto", help="Device (cuda, cpu, auto)")
    parser.add_argument("--shifts", type=int, default=1, help="Equivariant shifts")
    parser.add_argument("--segment", type=int, default=None, help="Segment length")
    parser.add_argument("--two-stems", default=None, help="Two stems target e.g. vocals")

    args = parser.parse_args()

    input_file = os.path.abspath(args.input)
    target_folder = os.path.abspath(args.output_dir)
    os.makedirs(target_folder, exist_ok=True)

    if not os.path.exists(input_file):
        print(json.dumps({"status": "error", "error": f"Input file not found: {input_file}"}))
        sys.exit(1)

    try:
        import torch
        import demucs.api

        if args.device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device = args.device

        start_time = time.time()
        separator = demucs.api.Separator(
            model=args.model,
            device=device,
            segment=args.segment,
            shifts=args.shifts
        )

        origin_name = os.path.splitext(os.path.basename(input_file))[0]
        origin, separated = separator.separate_audio_file(input_file)

        stems_exported = {}
        for stem_name, stem_tensor in separated.items():
            out_stem_path = os.path.join(target_folder, f"{stem_name}.wav")
            demucs.api.save_audio(stem_tensor, out_stem_path, samplerate=separator.samplerate)
            stems_exported[stem_name] = {
                "path": out_stem_path,
                "filename": f"{stem_name}.wav",
                "size_bytes": os.path.getsize(out_stem_path),
                "url": f"/api/v1/audio/demucs/file/{args.session_id}/{stem_name}.wav"
            }

        # Composite instrumental (drums + bass + other)
        if "drums" in separated and "bass" in separated and "other" in separated:
            try:
                instrumental_tensor = separated["drums"] + separated["bass"] + separated["other"]
                inst_path = os.path.join(target_folder, "instrumental.wav")
                demucs.api.save_audio(instrumental_tensor, inst_path, samplerate=separator.samplerate)
                stems_exported["instrumental"] = {
                    "path": inst_path,
                    "filename": "instrumental.wav",
                    "size_bytes": os.path.getsize(inst_path),
                    "url": f"/api/v1/audio/demucs/file/{args.session_id}/instrumental.wav"
                }
            except Exception as e:
                pass

        elapsed_sec = round(time.time() - start_time, 2)
        gpu_name = torch.cuda.get_device_name(0) if (device == "cuda" and torch.cuda.is_available()) else "CPU"

        result = {
            "status": "success",
            "session_id": args.session_id,
            "source_file": input_file,
            "origin_name": origin_name,
            "target_folder": target_folder,
            "model": args.model,
            "device": device,
            "gpu_name": gpu_name,
            "elapsed_seconds": elapsed_sec,
            "stems_count": len(stems_exported),
            "stems": list(stems_exported.keys()),
            "stems_detail": stems_exported
        }
        print("JSON_RESULT_START")
        print(json.dumps(result))
        print("JSON_RESULT_END")
        sys.exit(0)

    except Exception as e:
        err_msg = str(e)
        stack = traceback.format_exc()
        print("JSON_RESULT_START")
        print(json.dumps({"status": "error", "error": err_msg, "traceback": stack}))
        print("JSON_RESULT_END")
        sys.exit(1)

if __name__ == "__main__":
    main()
