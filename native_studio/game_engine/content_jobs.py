"""Controller-owned contexts for asynchronous authoring jobs, without inference."""
from dataclasses import dataclass
import copy,json,math,uuid,threading
from .content_proposals import ProposalContext,encode_proposal,COMPANION_MODEL_REFERENCE_FIELDS,MEMORY_AUDIO_REFERENCE_FIELDS
from .project_assets import ASSET_REFERENCE_FIELDS
from .opening_fields import INSPECTION_CAPABILITY,INSPECTION_FIELDS,validate_inspection_edits
from .workshop_fields import WORKSHOP_BINDING_FIELD,WORKSHOP_ROLE_FIELD,validate_workshop_edits

@dataclass(frozen=True)
class _Job:
    context:ProposalContext
    scope:tuple
    generation:int
    bytes:int

class ContentProposalJobs:
    def __init__(self,client,current_context):
        self.client=client;self.current_context=current_context;self._jobs={};self._thread=threading.get_ident()
        if hasattr(client,'closed'):client.closed.connect(lambda *_:self.cancel_all())

    @property
    def pending_count(self):return len(self._jobs)

    def _check_thread(self):
        if threading.get_ident()!=self._thread:raise RuntimeError('Authoring jobs must be used on the client owner thread')

    def _state(self):
        if self.client.state!='ready' or self.client.head is None:raise ValueError('Chapter owner is unavailable')
        if self.client.pending_count:raise ValueError('Wait for the pending chapter operation')
        current=self.current_context()
        if current is None:raise ValueError('Wait for a coherent loaded chapter')
        return current

    @staticmethod
    def _scope(head):
        s=head.scope;return (s.project,s.branch,s.world_id,s.host_epoch)

    def begin(self,entity_ids=None):
        self._check_thread()
        definition,fingerprint,rows=self._state()
        if len(self._jobs)>=8:raise ValueError('Authoring job count limit')
        selected=None if entity_ids is None else frozenset(entity_ids)
        fields=[];objects=[]
        for row in rows:
            if selected is not None and row.uuid not in selected:continue
            values={}
            for key,value in (row.fields.items() if hasattr(row.fields,'items') else row.fields):
                if key in INSPECTION_FIELDS and (row.type_id!='authoring.Fixture' or INSPECTION_CAPABILITY not in getattr(self.client,'capabilities',())):continue
                if row.type_id=='authoring.AssetPlacement' and key in ASSET_REFERENCE_FIELDS:continue
                if row.type_id=='authoring.CompanionBinding' and key in COMPANION_MODEL_REFERENCE_FIELDS:continue
                if row.type_id=='authoring.MemoryBinding' and key in MEMORY_AUDIO_REFERENCE_FIELDS:continue
                if key in (WORKSHOP_BINDING_FIELD,WORKSHOP_ROLE_FIELD):continue
                if row.type_id=='authoring.ChapterSettings' and key=='asset_profile':continue
                if type(value) is bool:kind='boolean'
                elif type(value) is float and math.isfinite(value):kind='number'
                elif type(value) is str:kind='text'
                else:continue  # Integer tool exposure requires an explicit codec contract.
                fields.append([row.uuid,key,kind]);values[key]=value
            objects.append({'uuid':row.uuid,'name':row.name,'type':row.type_id,'fields':values})
        head=self.client.head;s=head.scope
        context=ProposalContext.from_dict({'project':s.project,'branch':s.branch,'world_id':s.world_id,'definition_id':definition,
            'revision':head.head_revision,'fingerprint':fingerprint,'fields':fields})
        job=str(uuid.uuid4())
        prompt={'job_id':job,'context':{'project':s.project,'branch':s.branch,'world_id':s.world_id,'definition_id':definition,
            'revision':head.head_revision,'fingerprint':fingerprint},'objects':objects,
            'response_format':{'version':1,'label':'Describe the proposed change','edits':[{'entity_id':'allowed UUID','field':'allowed field','value':'matching typed value'}]}}
        encoded=json.dumps(prompt,ensure_ascii=False,allow_nan=False).encode('utf-8')
        if len(encoded)>256*1024 or len(encoded)+sum(j.bytes for j in self._jobs.values())>1024*1024:raise ValueError('Authoring job context byte limit')
        self._jobs[job]=_Job(context,self._scope(head),self.client.generation,len(encoded))
        return job,copy.deepcopy(prompt)

    def consume(self,job_id,source):
        self._check_thread()
        job=self._jobs.get(job_id)
        if job is None:raise ValueError('Authoring job is unknown, cancelled or already consumed')
        if self.client.state!='ready' or self.client.generation!=job.generation or self.client.head is None or self._scope(self.client.head)!=job.scope:
            self._jobs.pop(job_id,None);raise ValueError('Authoring job belongs to a closed/replaced owner')
        definition,fingerprint,_=self._state()
        if self.client.head.head_revision!=job.context.revision or definition!=job.context.definition_id or fingerprint!=job.context.fingerprint:
            self._jobs.pop(job_id,None);raise ValueError('Authoring job context is stale')
        packet=encode_proposal(source,job.context,'ai-job-'+job_id)
        from .content_commands import decode_scoped_edit
        edits=decode_scoped_edit(packet).edits
        validate_inspection_edits(self._state()[2],edits)
        validate_workshop_edits(self._state()[2],edits)
        del self._jobs[job_id]
        return packet

    def cancel(self,job_id):self._check_thread();self._jobs.pop(job_id,None)
    def cancel_all(self):self._check_thread();self._jobs.clear()
