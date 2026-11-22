"""Secret-free controls for the viewer reaction overlay. Import performs no I/O."""
import re
import uuid


def defaults():
    return {'version':1,'enabled':False,'screen_events':True,'chat_enabled':False,'channel':'brettstehouwer'}


def validate(config):
    if type(config) is not dict or set(config)!=set(defaults()): raise ValueError('Invalid overlay settings')
    if type(config['version']) is not int or config['version']!=1: raise ValueError('Unsupported overlay version')
    if any(type(config[key]) is not bool for key in ('enabled','screen_events','chat_enabled')):
        raise ValueError('Choose an explicit overlay state')
    if type(config['channel']) is not str or not re.fullmatch('[a-z0-9_]{3,25}',config['channel']):
        raise ValueError('Enter a Twitch channel name without a URL')
    return dict(config)


def path(kind):
    from native_studio.broadcast_ipc import ipc_paths
    if kind not in {'config','status'}: raise ValueError('Unknown overlay record')
    return ipc_paths()['status'].with_name('live_overlay_'+kind+'.json')


def load():
    from native_studio.broadcast_ipc import read_private_json
    target=path('config')
    if not target.exists(): return defaults()
    return validate(read_private_json(target,max_bytes=4096))


def save(config):
    from native_studio.broadcast_ipc import write_private_json
    write_private_json(path('config'),validate(config),max_bytes=4096)


def status():
    from native_studio.broadcast_ipc import read_private_json
    target=path('status')
    if not target.exists(): return {'state':'waiting_for_broadcast'}
    import time
    if not -1<=time.time()-target.stat().st_mtime<=4: return {'state':'waiting_for_broadcast'}
    return read_private_json(target,max_bytes=8192)


def valid_command(value):
    return (type(value) is dict and set(value)=={'version','id','kind'} and
            type(value['version']) is int and value['version']==1 and
            type(value['id']) is str and re.fullmatch('[a-f0-9]{32}',value['id']) is not None and
            value['kind'] in {'hype','poll'})


def send(kind):
    from native_studio.broadcast_ipc import ensure_private_ipc,write_private_json
    if kind not in {'hype','poll'}: raise ValueError('Choose hype or a poll')
    root=ensure_private_ipc()['status'].parent
    if len(list(root.glob('overlay_event_*.json')))>=32: raise ValueError('Overlay command queue is busy')
    identifier=uuid.uuid4().hex
    write_private_json(root/('overlay_event_'+identifier+'.json'),
                       {'version':1,'id':identifier,'kind':kind},max_bytes=1024)
    return identifier
