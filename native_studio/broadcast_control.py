"""Explicit broadcast commands. Importing this module performs no I/O."""
from __future__ import annotations

import json
from urllib.parse import urlsplit
import urllib.request


def stream_payload(config: dict) -> dict:
    """Build the daemon contract from saved settings, never invented credentials."""
    network = config.get('network', {})
    if network.get('stream_delay_sec', 0):
        raise ValueError('Broadcast delay is not enforced by the connected daemon; start held.')
    endpoints = []
    for name, destination in config.get('destinations', {}).items():
        if destination.get('enabled') is not True:
            continue
        url = destination.get('url', '').strip()
        parsed = urlsplit(url)
        if parsed.scheme not in {'rtmp', 'rtmps'} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('An enabled destination needs a valid RTMP/RTMPS URL.')
        key = destination.get('key', '').strip()
        if not key:
            raise ValueError('An enabled destination is missing its stream key.')
        endpoints.append({'name':name, 'url':url, 'key':key, 'enabled':True})
    if not endpoints:
        raise ValueError('Configure and enable a destination before starting a broadcast.')
    encoder = config.get('encoder', {})
    codec = str(encoder.get('codec', '')).lower()
    choice = 'av1_nvenc' if 'av1' in codec else 'hevc_nvenc' if 'hevc' in codec else 'libx264' if 'cpu' in codec or 'x264' in codec else 'h264_nvenc'
    # Facebook accepts AVC; preserve the user's URL, including session ingest hosts.
    if any(ep['name'] == 'facebook' for ep in endpoints):
        choice = 'libx264' if choice == 'libx264' else 'h264_nvenc'
    return {'endpoints':endpoints, 'fps':int(encoder.get('fps',60)),
            'resolution':encoder.get('resolution','1920x1080'),
            'video_bitrate':str(int(encoder.get('bitrate_kbps',6000)))+'k',
            'audio_bitrate':str(min(128,int(encoder.get('audio_bitrate_kbps',160))) if any(ep['name']=='facebook' for ep in endpoints) else int(encoder.get('audio_bitrate_kbps',160)))+'k',
            'encoder':choice, 'preset':'p5'}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def send_broadcast_command(kind: str, starting: bool, payload: dict) -> dict:
    """One fixed local command, no fallback/retry that could duplicate a start."""
    if kind not in {'stream','record'} or type(starting) is not bool:
        raise ValueError('Unknown broadcast command.')
    suffix = 'start' if starting else 'stop'
    url = f'http://127.0.0.1:8005/stream/{suffix}' if kind=='stream' else f'http://127.0.0.1:8088/api/kernel/record/{suffix}'
    request = urllib.request.Request(url, data=json.dumps(payload,allow_nan=False).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    with opener.open(request, timeout=5) as response:
        if response.status != 200:
            raise ValueError('Broadcast command was not acknowledged.')
        raw=response.read(65537)
    if len(raw)>65536:
        raise ValueError('Oversized broadcast response.')
    data=json.loads(raw)
    if not isinstance(data,dict):
        raise ValueError('Invalid broadcast acknowledgement.')
    # Never return backend error text or paths containing credentials to the UI.
    return {'status':data.get('status')}
