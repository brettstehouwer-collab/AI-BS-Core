"""Explicit chat controls for saved multi-shot films; history never authorizes work."""
import asyncio
import re
from .chat_film_store import FilmStore
from .personal_memory_scope import current_memory_principal

HELP = ('Film commands: `film plan 45: your description or script`, `film status`, '
        '`film shot 3: revised prompt`, `film render`, `film pause`, '
        '`film resume`, `film assemble`. Use `film open ID` to recover an older film. '
        'Rendering uses native 832×480 Wan clips at 16 fps; assembly produces silent MP4.')


def describe(film):
    lines=[f"Film `{film['id']}` · revision {film['revision']} · {film['state']}",
           f"Target: {film['seconds']} seconds, {len(film['shots'])} shots. Original script retained."]
    lines += [f"{s['number']}. {s['seconds']}s · {s['state']} · {s['prompt'][:500]}" for s in film['shots']]
    if film.get('error'):lines.append('Attention: '+film['error'])
    if film.get('output'):lines.append(f"[Download assembled MP4](/api/chat/films/{film['id']}/download)")
    lines.append(HELP)
    return '\n\n'.join(lines)


def command(text, owner, store=None, launch=None):
    match=re.match(r'^/?film\s+(.*)$',text.strip(),re.I|re.S)
    natural=re.match(r'^(?:please\s+)?(?:plan|create|make|generate)\s+(?:a\s+)?(\d+)\s*[- ]?second\s+(?:cinematic\s+)?(?:Wan2\.1\s+)?(?:video|film)\s+(.*)$',text.strip(),re.I|re.S)
    if not match and not natural:return None
    if not owner:raise PermissionError('Sign in before creating or accessing saved films')
    store=store or FilmStore()
    if launch is None:
        from .chat_film_runner import start
        launch=start
    action=match.group(1).strip() if match else f'plan {natural.group(1)}: {natural.group(2)}'
    plan=re.fullmatch(r'plan\s+(\d+)\s*:\s*(.+)',action,re.I|re.S)
    if plan:
        return describe(store.create(owner,plan.group(2),int(plan.group(1))))+'\n\nPlan saved. Say `film render` to execute the shots and assemble them.'
    opened=re.fullmatch(r'open\s+([0-9a-f]{32})',action,re.I)
    film=store.get(owner,opened.group(1).lower() if opened else None)
    if opened:
        store.select(owner,film['id'])
        return describe(film)
    edit=re.fullmatch(r'shot\s+(\d+)\s*:\s*(.+)',action,re.I|re.S)
    if edit:
        if film['run_requested'] or any(s['state']!='planned' for s in film['shots']):
            raise ValueError('Revise shots before rendering; create a new plan to preserve existing takes')
        number=int(edit.group(1));prompt=edit.group(2)
        if not 1<=number<=len(film['shots']) or len(prompt)>8000:raise ValueError('Invalid shot or prompt length')
        film['shots'][number-1]['prompt']=prompt;store.save(owner,film)
    elif action.lower()=='pause':
        if film['state']=='complete':return describe(film)
        film.update(run_requested=False,state='paused');store.save(owner,film)
        return describe(film)+'\n\nFurther shots paused. An already submitted Comfy render can finish and will be recovered on resume.'
    elif action.lower() in ('render','resume','assemble'):
        if film['state']=='complete':return describe(film)
        if action.lower()=='assemble' and any(s['state']!='complete' for s in film['shots']):
            raise ValueError('Finish the clips before requesting assembly')
        if any(s['state'] in ('submitting','uncertain') for s in film['shots']):
            raise ValueError('A submission has an unknown outcome. Inspect its Comfy history; no automatic retry was sent')
        film.update(run_requested=True,assemble_requested=True,error=None)
        store.save(owner,film);launch(owner,film['id'],store)
    elif action.lower()=='status':
        # Explicit status may resume observing a previously authorized durable job.
        if film['run_requested']:launch(owner,film['id'],store)
    else:return HELP
    return describe(store.get(owner,film['id']))


async def reply(text):
    try:
        return await asyncio.to_thread(command,text,current_memory_principal())
    except (ValueError,PermissionError) as error:
        return str(error)+'\n\n'+HELP
