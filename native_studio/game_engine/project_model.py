"""Explicit local project definitions; never infer schemas from player saves."""
from dataclasses import dataclass
from pathlib import Path
import json
import math
import os
import tempfile

DEFAULT_FIELDS=(('capacity',0.,100.),('half_x',.01,100.),('half_y',.01,100.),
                ('half_z',.01,100.),('x',-200.,200.),('y',-50.,100.),('z',-200.,200.))
NAME='.aibs-project.json'
LIMIT=65536


class ProjectError(ValueError):pass


def _text(value):
    if type(value) is not str or not value or len(value)>4096 or '\0' in value:
        raise ProjectError('Project identifiers must be nonempty text')
    try:
        if len(value.encode('utf-8'))>4096:raise ProjectError('Project text exceeds byte limit')
    except UnicodeError as error:raise ProjectError('Invalid project text') from error
    return value


def _fields(values):
    if type(values) not in (list,tuple) or not 1<=len(values)<=64:raise ProjectError('Invalid project schema count')
    result=[];names=set()
    for entry in values:
        if type(entry) not in (list,tuple) or len(entry)!=3:raise ProjectError('Invalid field definition')
        name,low,high=entry;_text(name)
        if name in names or type(low) not in (int,float) or type(high) not in (int,float):raise ProjectError('Invalid or duplicate field')
        try:
            if not math.isfinite(low) or not math.isfinite(high) or low>high:raise ProjectError('Invalid field bounds')
        except OverflowError as error:raise ProjectError('Field exceeds numeric range') from error
        names.add(name);result.append((name,float(low),float(high)))
    return tuple(sorted(result))


def _pairs(values):
    result={}
    for key,value in values:
        if key in result:raise ProjectError('Duplicate project JSON key')
        result[key]=value
    return result


@dataclass(frozen=True)
class ProjectDefinition:
    directory: Path
    project: str
    branch: str
    fields: tuple

    @property
    def path(self):return self.directory/NAME

    @classmethod
    def create(cls,directory,project,branch='main',fields=DEFAULT_FIELDS):
        try:
            root=Path(directory).resolve(strict=True)
            if not root.is_dir():raise ProjectError('Select an existing project directory')
            target=root/NAME;world=root/'world.aibs'
            if target.exists() or target.is_symlink() or world.exists() or world.is_symlink():
                raise ProjectError('Project metadata or a world already exists; open the existing project')
            result=cls(root,_text(project),_text(branch),_fields(fields))
            data=(json.dumps({'version':1,'project':result.project,'branch':result.branch,'fields':result.fields},ensure_ascii=False,indent=2)+'\n').encode('utf-8')
            if len(data)>LIMIT:raise ProjectError('Project definition exceeds 64 KiB')
            fd,name=tempfile.mkstemp(prefix='.aibs-definition-',suffix='.tmp',dir=root)
            temporary=Path(name)
            try:
                with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
                # Exclusive atomic publication: never replace an existing file.
                # Unsupported filesystems reject instead of using unsafe fallback.
                os.link(temporary,target)
            finally:temporary.unlink(missing_ok=True)
            return result
        except (OSError,UnicodeError) as error:raise ProjectError('Could not create project definition: '+str(error)) from error

    @classmethod
    def load(cls,directory):
        try:
            root=Path(directory).resolve(strict=True);target=root/NAME
            if not root.is_dir() or target.is_symlink() or target.resolve().parent!=root:raise ProjectError('Invalid project metadata path')
            with target.open('rb') as stream:data=stream.read(LIMIT+1)
            if len(data)>LIMIT:raise ProjectError('Project definition exceeds 64 KiB')
            value=json.loads(data.decode('utf-8-sig'),object_pairs_hook=_pairs)
            if type(value) is not dict or set(value)!= {'version','project','branch','fields'} or type(value['version']) is not int or value['version']!=1:
                raise ProjectError('Unsupported project definition')
            return cls(root,_text(value['project']),_text(value['branch']),_fields(value['fields']))
        except (OSError,UnicodeError,json.JSONDecodeError) as error:raise ProjectError('Could not read project definition: '+str(error)) from error
