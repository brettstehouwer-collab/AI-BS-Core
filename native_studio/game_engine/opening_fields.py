"""Bounded authored reading/seat data; never gameplay outcome commands.

Observation extensions are deliberately separate from the exact legacy17-field
CreateFixture geometry component. The native owner remains final authority.
"""
from .creator_payload import PayloadError
INSPECTION_CAPABILITY='chapter-authored-inspections-v1'
INITIAL_VIEW_CAPABILITY='chapter-initial-view-v1'
INITIAL_VIEW_FIELD='hint.view.initial_target'
INSPECTION_FIELDS=('inspection_text','inspection_source','inspection_action')
INSPECTION_LIMITS={'inspection_text':2048,'inspection_source':512,'inspection_action':4}

def inspection_value(field,value):
    if field not in INSPECTION_LIMITS or type(value)is not str:
        raise PayloadError('Inspection fields require bounded text')
    try:encoded=value.encode('utf-8',errors='strict')
    except UnicodeError as error:raise PayloadError('Invalid inspection UTF-8')from error
    if len(encoded)>INSPECTION_LIMITS[field] or any(ord(c)<32 and c not in '\n\r\t'for c in value):
        raise PayloadError('Inspection text exceeds its byte limit or contains a forbidden control')
    if field=='inspection_action'and value not in ('','read','seat'):
        raise PayloadError('Inspection action must be read or seat; no outcome commands')
    return value

def validate_inspection_state(name,fields):
    values={key:inspection_value(key,fields.get(key,''))for key in INSPECTION_FIELDS}
    if not any(values.values()):return values
    if not all(values.values()):raise PayloadError('Inspection requires a complete text, source and action group, or all three empty')
    try:encoded=name.encode('utf-8',errors='strict')if type(name)is str else b''
    except UnicodeError as error:raise PayloadError('Invalid inspection title UTF-8')from error
    if not encoded or len(encoded)>256 or any(ord(c)<32 and c not in '\n\r\t'for c in name):
        raise PayloadError('A bound inspection requires a title of at most 256 UTF-8 bytes')
    if fields.get('selectable',True)is not True:raise PayloadError('A bound inspection fixture must remain selectable')
    return values

def fixture_inspection_fields(row):
    """Validate legacy17, inspection20, or the explicit true Workshop21 row.

    This does not change CreateFixture's binary decoder or append strings to its
    geometry payload. Legacy rows have no inspection keys and return {}.
    """
    from .content_commands import CreateFixture,_fixture_fields
    if row.type_id!='authoring.Fixture':raise PayloadError('Inspection fields belong to an authored fixture')
    try:fields=dict(row.fields)
    except (ValueError,TypeError)as error:raise PayloadError('Invalid fixture observation')from error
    geometry=set(dict(_fixture_fields(CreateFixture(row.uuid,'Observation schema'))))
    keys=set(fields)
    from .workshop_fields import WORKSHOP_ROLE_FIELD
    workshop=geometry|set(INSPECTION_FIELDS)|{WORKSHOP_ROLE_FIELD}
    if len(fields)!=len(row.fields)or keys not in (geometry,geometry|set(INSPECTION_FIELDS),workshop):
        raise PayloadError('Fixture observation requires geometry17 or geometry17 plus inspection strings3')
    if keys==geometry:return {}
    values=validate_inspection_state(fields['name'],fields)
    if keys==workshop and (fields[WORKSHOP_ROLE_FIELD]is not True or any(values.values()) or fields.get('selectable')is not True):
        raise PayloadError('Workshop fixtures require boolean true, selectable geometry and empty inspection strings')
    return values

def validate_inspection_edits(rows,edits):
    """Validate only touched inspection groups against the current owned rows."""
    from .content_commands import SetField,CreateFixture,EraseFixture,_fixture_fields
    states={row.uuid:dict(row.fields)for row in rows if row.type_id=='authoring.Fixture'}
    touched=set()
    for edit in edits:
        if isinstance(edit,CreateFixture):states[edit.uuid]=dict(_fixture_fields(edit))
        elif isinstance(edit,EraseFixture):states.pop(edit.uuid,None);touched.discard(edit.uuid)
        elif isinstance(edit,SetField):
            relevant=edit.field in INSPECTION_FIELDS
            if relevant and edit.uuid not in states:raise PayloadError('Inspection edits require an owned fixture')
            if edit.uuid not in states:continue
            if relevant:inspection_value(edit.field,edit.value);touched.add(edit.uuid)
            elif edit.field in ('name','selectable')and any(states[edit.uuid].get(key,'')for key in INSPECTION_FIELDS):touched.add(edit.uuid)
            states[edit.uuid][edit.field]=edit.value
    for identity in touched:
        fields=states[identity];validate_inspection_state(fields.get('name'),fields)

def inspection_schema(field):
    if field not in INSPECTION_FIELDS:return None
    result={'type':'string','maxLength':INSPECTION_LIMITS[field]}
    if field=='inspection_action':result['enum']=['','read','seat']
    return result

def authored_inspections_from_rows(rows):
    """Derive the reader requirement from the same pinned typed observations."""
    return any(any(fixture_inspection_fields(row).values())for row in rows if row.type_id=='authoring.Fixture')

def initial_view_authored_from_rows(rows,asset_profile=None):
    """Derive the requirement from the same pinned native typed observations.

    The native owner alone validates CLOSED-scene visibility/traversal. Python
    validates bounded metadata and ownership without decoding AIBD or geometry.
    Older chapter rows omit this key and retain their existing readers.
    """
    from .creator_payload import _uuid
    if asset_profile not in (None,'legacy_v1','warm-beginning'):
        raise PayloadError('Invalid initial view asset profile')
    rows=tuple(rows)
    metadata=[row for row in rows if any(key==INITIAL_VIEW_FIELD for key,_ in row.fields)]
    if not metadata:return False
    settings=[row for row in rows if row.type_id=='authoring.ChapterSettings']
    if len(metadata)!=1 or len(settings)!=1 or metadata[0]is not settings[0]:
        raise PayloadError('Initial view requires one owned chapter settings observation')
    row=settings[0];values=dict(row.fields)
    if len(values)!=len(row.fields):raise PayloadError('Duplicate initial view settings fields')
    if values.get('asset_profile')!='warm_beginning' or asset_profile=='legacy_v1':
        raise PayloadError('Initial view metadata requires AIBD3 Warm Beginning content')
    target=_uuid(values[INITIAL_VIEW_FIELD],optional=True)
    if not target:return False
    owned=[item for item in rows if item.uuid==target]
    if len(owned)!=1 or owned[0].type_id!='authoring.Fixture':
        raise PayloadError('Initial view target must be an owned inspection fixture UUID')
    inspection=fixture_inspection_fields(owned[0])
    if not inspection or not all(inspection.values()):
        raise PayloadError('Initial view target requires a complete selectable inspection')
    return True


def require_inspection_reader(executable,snapshot):
    flag=getattr(snapshot,'authored_inspections',False)
    initial=getattr(snapshot,'initial_view_authored',False)
    if type(flag)is not bool:raise ValueError('Invalid authored inspection snapshot requirement')
    if type(initial)is not bool:raise ValueError('Invalid authored initial view snapshot requirement')
    if initial and getattr(snapshot,'asset_profile',None)!='warm-beginning':
        raise ValueError('Authored initial view requires a Warm Beginning snapshot')
    from .workshop_fields import WORKSHOP_CAPABILITY
    workshop=getattr(snapshot,'opening_workshop_authored',False)
    if type(workshop)is not bool:raise ValueError('Invalid Opening Workshop snapshot requirement')
    if workshop and getattr(snapshot,'asset_profile',None)!='warm-beginning':raise ValueError('Opening Workshop requires a Warm Beginning snapshot')
    if not flag and not initial and not workshop:return
    from native_studio.game_build_monitor import read_native_player_capabilities
    features=read_native_player_capabilities(executable).get('features',{})
    if workshop and features.get(WORKSHOP_CAPABILITY)is not True:
        raise ValueError('This native reader does not support Opening Workshop; upgrade it before Preview or Play')
    if flag and features.get(INSPECTION_CAPABILITY)is not True:
        raise ValueError('This native reader does not support authored inspections; upgrade it before Preview or Play')
    if initial and features.get(INITIAL_VIEW_CAPABILITY)is not True:
        raise ValueError('This native reader does not support the authored initial view; upgrade it before Preview or Play')
