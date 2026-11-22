"""Typed creator-process commands; no process launch or default save selection."""
from dataclasses import dataclass
from enum import IntEnum
import math
from .creator_payload import _Writer, _Reader, _uuid, _write_double, PayloadError, Scope, Create


class Status(IntEnum):
    OK=0
    PREPARED=1
    APPLIED=2
    DUPLICATE=3
    UNDONE=4
    REDONE=5
    SAVED=6
    PLAYING=7
    STOPPED=8
    REJECTED=100


@dataclass(frozen=True)
class Response:
    status: Status
    message: str
    scope: Scope
    head_revision: int
    checkpoint_id: str
    operation_revision: int
    token: str
    play_epoch: str
    save_compatible: bool
    save_bytes: int
    save_message: str
    world_count: int
    undo_depth: int
    redo_depth: int
    body: bytes


def _scope_writer(scope):
    w=_Writer()
    w.number(1,'H')
    for value in (scope.project,scope.branch,_uuid(scope.world_id),_uuid(scope.host_epoch)):
        w.text(value,True)
    return w


def scoped(scope):
    return bytes(_scope_writer(scope).data)


def open_document(project,branch,schemas,create=False):
    if type(create) is not bool or not 1<=len(schemas)<=64:
        raise PayloadError('Invalid Open mode/schema count')
    if len({s[0] for s in schemas})!=len(schemas):
        raise PayloadError('Duplicate schema field')
    w=_Writer();w.number(1,'H');w.text(project,True);w.text(branch,True);w.number(create,'B');w.number(len(schemas),'I')
    for name,low,high in schemas:
        if low>high:
            raise PayloadError('Invalid schema range')
        w.text(name,True);_write_double(w,low);_write_double(w,high)
    return bytes(w.data)


def prepared_handle(scope,handle):
    w=_scope_writer(scope);w.text(_uuid(handle),True);return bytes(w.data)


def history(scope,operation_id,redo):
    if type(redo) is not bool:
        raise PayloadError('Invalid history direction')
    w=_scope_writer(scope);w.text(operation_id,True);w.number(redo,'B');return bytes(w.data)


def snapshot_page(scope,checkpoint,after='',limit=64):
    if type(limit) is not int or not 1<=limit<=64:
        raise PayloadError('Invalid page count')
    w=_scope_writer(scope);w.text(_uuid(checkpoint,True));w.text(after);w.number(limit,'I');return bytes(w.data)


def decode_response(data):
    r=_Reader(data)
    if r.number('H')!=1:
        raise PayloadError('Unsupported response version')
    try:
        status=Status(r.number('H'))
    except ValueError as error:
        raise PayloadError('Unknown response status') from error
    message=r.text();host_epoch=r.text();project=r.text();branch=r.text();world=r.text()
    _uuid(host_epoch,True);_uuid(world,True)
    revision=r.number('Q');checkpoint=_uuid(r.text(),True);operation=r.number('Q')
    token=_uuid(r.text(),True);play=_uuid(r.text(),True);compatible=r.number('B')
    if compatible not in (0,1):
        raise PayloadError('Invalid compatibility flag')
    size=r.number('Q');save_message=r.text();count=r.number('I');undo=r.number('Q');redo=r.number('Q');body_size=r.number('I')
    if count>10000 or body_size>512*1024:
        raise PayloadError('Response count/body limit')
    body=r.read(body_size)
    if r.offset!=len(data):
        raise PayloadError('Trailing response bytes')
    return Response(status,message,Scope(project,branch,world,host_epoch),revision,checkpoint,operation,token,play,
                    bool(compatible),size,save_message,count,undo,redo,body)


def decode_page(data):
    r=_Reader(data);cursor=r.text();more=r.number('B');count=r.number('I')
    if more not in (0,1) or count>64:
        raise PayloadError('Invalid page bounds')
    rows=[];aliases=set();uuids=set()
    for _ in range(count):
        alias,name,uuid=r.text(True),r.text(),_uuid(r.text(True));fields_count=r.number('I')
        if alias in aliases or uuid in uuids or fields_count>64:
            raise PayloadError('Duplicate entity or oversized fields')
        aliases.add(alias);uuids.add(uuid);fields=[];keys=set()
        for _ in range(fields_count):
            key,value=r.text(True),r.number('d')
            if key in keys or not math.isfinite(value):
                raise PayloadError('Duplicate field or invalid number')
            keys.add(key);fields.append((key,value))
        rows.append(Create(alias,name,uuid,tuple(fields)))
    if r.offset!=len(data):
        raise PayloadError('Trailing page bytes')
    return tuple(rows),cursor,bool(more)


def decode_description(data):
    r=_Reader(data);count=r.number('I')
    if not 1<=count<=64:
        raise PayloadError('Invalid schema count')
    fields=[];keys=set()
    for _ in range(count):
        key,low,high=r.text(True),r.number('d'),r.number('d')
        if key in keys or not math.isfinite(low) or not math.isfinite(high) or low>high:
            raise PayloadError('Invalid or duplicate schema field')
        keys.add(key);fields.append((key,low,high))
    if r.offset!=len(data):
        raise PayloadError('Trailing schema bytes')
    return tuple(fields)
