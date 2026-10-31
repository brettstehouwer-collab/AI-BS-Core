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
    problems = []
    labels={'twitch':'Twitch','youtube':'YouTube','facebook':'Facebook','kick':'Kick','tiktok':'TikTok','sovereign_srt':'Local SRT'}
    for name, destination in config.get('destinations', {}).items():
        if destination.get('enabled') is not True:
            continue
        label=labels.get(name,'Destination')
        url = destination.get('url', '')
        if not isinstance(url,str):
            problems.append(label+': invalid server URL.');continue
        url=url.strip()
        try:parsed = urlsplit(url)
        except ValueError:
            problems.append(label+': invalid server URL.');continue
        if parsed.scheme in {'srt','hls'}:
            problems.append(label+': SRT/HLS output is not supported by this RTMP broadcaster. Disable it or use its dedicated output.');continue
        if parsed.scheme not in {'rtmp', 'rtmps'} or not parsed.hostname or parsed.username or parsed.password:
            problems.append(label+': enter a valid RTMP/RTMPS server URL.');continue
        key = destination.get('key', '')
        if not isinstance(key,str) or not key.strip():
            problems.append(label+': stream key missing. Add it in Setup Keys or disable this destination.');continue
        key=key.strip()
        endpoints.append({'name':name, 'url':url, 'key':key, 'enabled':True})
    if problems:
        raise ValueError(' '.join(problems))
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
    """Route native broadcast intent to the same coordinator; never fallback."""
    if kind not in {'stream','record'} or type(starting) is not bool:
        raise ValueError('Unknown broadcast command.')
    if kind == 'record':
        return {'status':'archive_accompanies_broadcast'}
    from native_studio import broadcast_secondary_control as coordinator
    return coordinator.start_broadcast(payload) if starting else coordinator.stop_broadcast()
