"""One submitted video job, accurate completion and no automatic fallback jobs."""
from .video_workflows import build_core_wan_graph


async def generate_video(arguments, *, info=None, submit=None, wait=None):
    prompt_id = None
    try:
        if info is None:
            import httpx
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                response = await client.get('http://127.0.0.1:8189/object_info')
                response.raise_for_status()
                info = response.json()
        if arguments.get('reference_image'):
            raise ValueError('This Wan route accepts text-to-video. Select LTX image-to-video for a reference image.')
        width = int(arguments.get('width', 832))
        height = int(arguments.get('height', 480))
        fps = int(arguments.get('fps', 16))
        duration = float(arguments.get('duration_seconds', 3))
        frames = int(arguments.get('num_frames', round((duration * fps - 1) / 4) * 4 + 1))
        steps = int(arguments.get('steps', 8))
        seed = int(arguments.get('seed', 42))
        if seed < 0:
            import secrets
            seed = secrets.randbits(32)
        graph = build_core_wan_graph(arguments.get('prompt', ''), info,
            negative_prompt=arguments.get('negative_prompt', 'blurry, low quality, static'),
            width=width, height=height, length=frames, fps=fps, steps=steps,
            cfg=float(arguments.get('cfg', 6)), seed=seed)
        from comfy_bridge import queue_comfyui_workflow, await_generation_result, extract_output_media
        prompt_id = await (submit or queue_comfyui_workflow)(graph)
        entry = await (wait or await_generation_result)(prompt_id)
        status = entry.get('status', {})
        if not status.get('completed') or status.get('status_str') != 'success':
            return {'status': 'error', 'prompt_id': prompt_id, 'message': 'The video job did not complete successfully. Its history is retained.'}
        media = extract_output_media(entry)
        if not str(media.get('filename', '')).lower().endswith('.mp4'):
            return {'status': 'error', 'prompt_id': prompt_id, 'message': 'The job produced no completed MP4 video.'}
        return {'status': 'success', 'prompt_id': prompt_id, **media, 'width': width,
                'height': height, 'num_frames': frames, 'fps': fps,
                'duration_seconds': frames / fps, 'seed': seed, 'engine': 'wan21_core',
                'upscaled': False}
    except TimeoutError:
        if not prompt_id:
            return {'status':'error','execution_status':'unknown','message':'Video submission was not confirmed. Inspect the queue before retrying; no fallback job was submitted.'}
        return {'status': 'pending', 'prompt_id': prompt_id,
                'message': 'The submitted video job is still unconfirmed. Inspect this job before submitting another.'}
    except ValueError as error:
        return {'status': 'error', 'prompt_id': prompt_id, 'message': str(error)}
    except Exception:
        return {'status': 'error', 'prompt_id': prompt_id,
                'message': ('Video job failed or its completion could not be confirmed. Inspect its retained history before retrying.'
                            if prompt_id else 'Video submission was not confirmed. Inspect the queue before retrying; no fallback job was submitted.')}
