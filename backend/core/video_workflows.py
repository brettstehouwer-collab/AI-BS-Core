"""Video graphs for the observed ComfyUI core contract; no model downloads."""
from copy import deepcopy
import math

WAN_MODELS = ('wan2.1_t2v_1.3b.safetensors', 'wan2.1-t2v-1.3B.safetensors')
WAN_CLIPS = ('umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'umt5_xxl_fp16.safetensors')
WAN_VAES = ('wan_2.1_vae.safetensors', 'Wan2_1_VAE_bf16.safetensors')
WAN_NODES = {'UNETLoader', 'CLIPLoader', 'VAELoader', 'CLIPTextEncode',
             'EmptyHunyuanLatentVideo', 'ModelSamplingSD3', 'KSampler',
             'VAEDecode', 'CreateVideo', 'SaveVideo'}
LTX_NODES = {'CheckpointLoaderSimple', 'CLIPLoader', 'CLIPTextEncode',
             'LTXVConditioning', 'LoadImage', 'LTXVImgToVideo', 'LTXVScheduler',
             'KSamplerSelect', 'SamplerCustom', 'VAEDecode', 'CreateVideo', 'SaveVideo'}


def _options(info, node, field):
    spec = info.get(node, {}).get('input', {}).get('required', {}).get(field, [])
    if spec and isinstance(spec[0], list):
        return spec[0]
    return spec[1].get('options', []) if len(spec) > 1 and isinstance(spec[1], dict) else []


def _choose(info, node, field, candidates):
    options = _options(info, node, field)
    return next((name for name in candidates if name in options), None)


def video_capabilities(info):
    wan_missing = sorted(WAN_NODES - set(info))
    for node, field, names in [('UNETLoader', 'unet_name', WAN_MODELS),
                                ('CLIPLoader', 'clip_name', WAN_CLIPS),
                                ('VAELoader', 'vae_name', WAN_VAES)]:
        if not _choose(info, node, field, names):
            wan_missing.append(f'{node}.{field}: installed Wan model required')
    if 'wan' not in _options(info, 'CLIPLoader', 'type'):
        wan_missing.append('CLIPLoader: Wan encoder support required')
    ltx_missing = sorted(LTX_NODES - set(info))
    for node, field, names in [('CheckpointLoaderSimple', 'ckpt_name', ('ltx-video-2b-v0.9.1.safetensors',)),
                                ('CLIPLoader', 'clip_name', ('t5xxl_fp16.safetensors',))]:
        if not _choose(info, node, field, names):
            ltx_missing.append(f'{node}.{field}: installed LTX model required')
    return {'wan_t2v': {'ready': not wan_missing, 'missing': wan_missing},
            'ltx_i2v': {'ready': not ltx_missing, 'missing': ltx_missing}}


def validate_graph(graph, info):
    """Check required ports, links and enum values before queue submission."""
    problems = []
    for node_id, node in graph.items():
        kind = node['class_type']
        if kind not in info:
            problems.append(f'{node_id}: unavailable node {kind}')
            continue
        inputs = node.get('inputs', {})
        for field, spec in info[kind].get('input', {}).get('required', {}).items():
            if field not in inputs:
                problems.append(f'{node_id}: missing {kind}.{field}')
                continue
            value = inputs[field]
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                source = graph.get(value[0])
                if source is None or not isinstance(value[1], int) or value[1] < 0:
                    problems.append(f'{node_id}: invalid source for {field}')
                elif source['class_type'] in info and value[1] >= len(info[source['class_type']].get('output', [])):
                    problems.append(f'{node_id}: invalid output slot for {field}')
            else:
                choices = _options(info, kind, field)
                if choices and value not in choices:
                    problems.append(f'{node_id}: unsupported {kind}.{field}')
    return problems


def core_video_output(graph):
    """Keep decoded frames while replacing the optional VHS encoder with core MP4."""
    result = deepcopy(graph)
    for node_id, node in list(result.items()):
        if node['class_type'] != 'VHS_VideoCombine':
            continue
        inputs = node['inputs']
        create_id = f'{node_id}_core_video'
        if create_id in result:
            raise ValueError('Video node identifier collision')
        result[create_id] = {'class_type': 'CreateVideo', 'inputs': {
            'images': inputs['images'], 'fps': float(inputs.get('frame_rate', 16))}}
        result[node_id] = {'class_type': 'SaveVideo', 'inputs': {
            'video': [create_id, 0], 'filename_prefix': inputs.get('filename_prefix', 'AIBS_Video'),
            'format': 'mp4', 'codec': 'h264'}}
    return result


def build_core_wan_graph(prompt, info, *, negative_prompt='blurry, low quality, static',
                         width=832, height=480, length=49, fps=16, steps=8,
                         cfg=6.0, seed=42, prefix='AI_BS_Wan_Core'):
    missing = video_capabilities(info)['wan_t2v']['missing']
    if missing:
        raise ValueError('Wan video unavailable: ' + '; '.join(missing))
    if (not all(type(v) is int for v in (width, height, length, fps, steps, seed))
            or width < 64 or height < 64 or max(width, height) > 960
            or width * height > 832 * 480 or width % 16 or height % 16
            or not 9 <= length <= 129 or (length - 1) % 4
            or not 1 <= fps <= 60 or not 1 <= steps <= 50 or seed < 0):
        raise ValueError('Invalid or unsupported native video dimensions, frames or sampling parameters')
    if not isinstance(cfg, (int, float)) or isinstance(cfg, bool) or not math.isfinite(cfg) or not 0 <= cfg <= 20:
        raise ValueError('Invalid video guidance scale')
    if not prefix or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in prefix):
        raise ValueError('Invalid video output prefix')
    graph = {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': _choose(info, 'UNETLoader', 'unet_name', WAN_MODELS), 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': _choose(info, 'CLIPLoader', 'clip_name', WAN_CLIPS), 'type': 'wan', 'device': 'cpu'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': _choose(info, 'VAELoader', 'vae_name', WAN_VAES)}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': str(prompt), 'clip': ['2', 0]}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'text': str(negative_prompt), 'clip': ['2', 0]}},
        '6': {'class_type': 'EmptyHunyuanLatentVideo', 'inputs': {'width': width, 'height': height, 'length': length, 'batch_size': 1}},
        '7': {'class_type': 'ModelSamplingSD3', 'inputs': {'model': ['1', 0], 'shift': 8.0}},
        '8': {'class_type': 'KSampler', 'inputs': {'model': ['7', 0], 'seed': seed, 'steps': steps, 'cfg': float(cfg), 'sampler_name': 'uni_pc', 'scheduler': 'simple', 'positive': ['4', 0], 'negative': ['5', 0], 'latent_image': ['6', 0], 'denoise': 1.0}},
        '9': {'class_type': 'VAEDecode', 'inputs': {'samples': ['8', 0], 'vae': ['3', 0]}},
        '10': {'class_type': 'CreateVideo', 'inputs': {'images': ['9', 0], 'fps': float(fps)}},
        '11': {'class_type': 'SaveVideo', 'inputs': {'video': ['10', 0], 'filename_prefix': prefix, 'format': 'mp4', 'codec': 'h264'}},
    }
    problems = validate_graph(graph, info)
    if problems:
        raise ValueError('Video graph unavailable: ' + '; '.join(problems))
    return graph
