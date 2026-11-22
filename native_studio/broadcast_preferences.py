"""Secret-free audio and per-destination encoding settings. Import performs no I/O."""
import copy
import math

# H.264 profiles. YouTube uses the game's 1440p source without upscaling.
# https://support.google.com/youtube/answer/2853702
# https://help.twitch.tv/s/article/broadcasting-guidelines
# https://help.kick.com/ (1080p60, CBR up to 8000 kbps)
# Facebook preserves this project's existing 8000 kbps/128 kbps limits.
PROFILES = {
    'youtube': dict(width=2560, height=1440, fps=60, video_kbps=24000, audio_kbps=256),
    'twitch': dict(width=1920, height=1080, fps=60, video_kbps=6000, audio_kbps=160),
    'kick': dict(width=1920, height=1080, fps=60, video_kbps=8000, audio_kbps=160),
    'facebook': dict(width=1920, height=1080, fps=60, video_kbps=8000, audio_kbps=128),
}
LIMITS = {'youtube': (3840, 2160, 51000, 320), 'twitch': (1920, 1080, 6000, 160),
          'kick': (1920, 1080, 8000, 160), 'facebook': (1920, 1080, 8000, 128)}


def defaults():
    return {'schema': 1, 'mode': 'shared', 'upload_mbps': 100,
            'audio': {role: {'enabled': False, 'device': 'default', 'gain': 1.0}
                      for role in ('desktop_audio', 'mic')},
            'outputs': copy.deepcopy(PROFILES)}


def maximum_preferences(upload_mbps):
    result = defaults()
    result.update(mode='per_platform', upload_mbps=upload_mbps)
    return result


def required_upload_mbps(preferences, targets=None):
    targets = tuple(targets) if targets is not None else tuple(PROFILES)
    total = sum(preferences['outputs'][target]['video_kbps'] +
                preferences['outputs'][target]['audio_kbps'] for target in targets)
    return round(total * 1.25 / 1000, 3)


def validate(preferences):
    if type(preferences) is not dict or set(preferences) != {'schema','mode','upload_mbps','audio','outputs'}:
        raise ValueError('Invalid broadcast settings')
    if type(preferences['schema']) is not int or preferences['schema'] != 1 or preferences['mode'] not in {'shared','per_platform'}:
        raise ValueError('Unsupported broadcast settings')
    upload = preferences['upload_mbps']
    if type(upload) not in (int,float) or not math.isfinite(upload) or not 1 <= upload <= 10000:
        raise ValueError('Enter the measured upload speed')
    if type(preferences['audio']) is not dict or set(preferences['audio']) != {'desktop_audio','mic'}:
        raise ValueError('Invalid audio routing')
    for route in preferences['audio'].values():
        if type(route) is not dict or set(route) != {'enabled','device','gain'}:
            raise ValueError('Invalid audio input')
        if type(route['enabled']) is not bool or type(route['device']) is not str or not 1 <= len(route['device']) <= 256 or any(ord(c)<32 for c in route['device']):
            raise ValueError('Choose an audio input')
        gain = route['gain']
        if type(gain) not in (int,float) or not math.isfinite(gain) or not 0 <= gain <= 2:
            raise ValueError('Audio gain must be between 0 and 2')
    outputs = preferences['outputs']
    if type(outputs) is not dict or set(outputs) != set(PROFILES): raise ValueError('Invalid output profiles')
    for target, profile in outputs.items():
        if type(profile) is not dict or set(profile) != {'width','height','fps','video_kbps','audio_kbps'}:
            raise ValueError('Output profiles contain numeric settings only')
        if any(type(value) is not int for value in profile.values()): raise ValueError('Output values must be whole numbers')
        width, height, bitrate, audio = LIMITS[target]
        if not (320 <= profile['width'] <= width and 180 <= profile['height'] <= height and
                profile['width'] % 2 == profile['height'] % 2 == 0 and
                profile['fps'] in {24,25,30,50,60} and 500 <= profile['video_kbps'] <= bitrate and
                64 <= profile['audio_kbps'] <= audio):
            raise ValueError('Output exceeds the selected service profile')
    if preferences['mode'] == 'per_platform' and required_upload_mbps(preferences) > upload:
        raise ValueError('Combined outputs exceed the upload speed including 25% headroom')
    return copy.deepcopy(preferences)


def _path():
    from native_studio.broadcast_ipc import ipc_paths
    return ipc_paths()['status'].with_name('broadcast_preferences.json')


def load():
    from native_studio.broadcast_ipc import read_private_json
    path = _path()
    if not path.exists(): return defaults()
    return validate(read_private_json(path, max_bytes=32768))


def save(preferences):
    from native_studio.broadcast_ipc import write_private_json
    write_private_json(_path(), validate(preferences), max_bytes=32768)
