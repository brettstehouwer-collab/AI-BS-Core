"""CPU-only real cooker processes. All speech/review declarations are synthetic."""
from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, struct, subprocess, uuid
ID='265a23aa-7368-470a-80e0-934643b328e2'
DECLARATION='Human-supplied listening review declarations validated; this tool did not listen or verify spoken wording.'
def sha(body):return hashlib.sha256(body).hexdigest()
def wave(pcm):
 fmt=struct.pack('<HHIIHH',1,2,44100,176400,4,16)
 body=b'WAVEJUNK'+struct.pack('<I',3)+b'xyz\0'+b'fmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(pcm))+pcm
 return b'RIFF'+struct.pack('<I',len(body))+body
def document(wav,frames):
 return {'schema_version':1,'status':'LISTENING_REVIEW_VALIDATED_FOR_NATIVE_ATTACHMENT','caption_review':'checked','source_sha256':sha(wav),'source_caption_draft_sha256':sha(b'synthetic draft'),'review_export_sha256':sha(b'synthetic declared review'),'sample_rate':44100,'channels':2,'frame_count':frames,'caption_count':2,'captions':[{'start_frame':0,'end_frame':frames//2,'text':'Synthetic cue one.\nExact second line.'},{'start_frame':frames//2,'end_frame':frames,'text':'Synthetic snowman \u2603 and rocket \U0001f680.'}],'reviewer':'Synthetic review fixture','reviewed_at_utc':'2026-11-02T00:00:00.123Z','automatic_approval':False,'declaration':DECLARATION,'native_attachment_status':'not_supported_by_current_audio_cooker_cli'}
def parse(encoded):
 assert encoded[:12]==b'AIBAudio2\0\0\0'
 assert struct.unpack_from('<II',encoded,12)==(2,len(encoded)-52)
 assert encoded[20:52]==hashlib.sha256(encoded[52:]).digest()
 position=52
 def string():
  nonlocal position
  n,=struct.unpack_from('<I',encoded,position);position+=4
  s=encoded[position:position+n].decode('utf-8');position+=n;return s
 strings=[string()for _ in range(3)]
 rate,channels,bits,reserved,frames,count=struct.unpack_from('<IIIIQQ',encoded,position);position+=32
 pcm=encoded[position:position+count];position+=count
 review,cues=struct.unpack_from('<II',encoded,position);position+=8
 captions=[]
 for _ in range(cues):
  begin,end=struct.unpack_from('<QQ',encoded,position);position+=16
  captions.append({'start_frame':begin,'end_frame':end,'text':string()})
 assert position==len(encoded)
 return {'strings':strings,'format':(rate,channels,bits,reserved,frames),'pcm':pcm,'review':review,'captions':captions}
def verify(exe,output,baseline=None,adapter=None):
 output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
 work=output/('reviewed-cooker-'+str(uuid.uuid4()));work.mkdir();checks=[];processes=[]
 result={'status':'failed','family_audio_loaded':False,'actual_listening_review_performed':False,'gpu_used':False,'work':str(work)}
 def check(v,label):
  if not v:raise AssertionError(label)
  checks.append(label)
 def run(*args,success=True,binary=None):
  p=subprocess.run([str(Path(binary or exe).resolve()),*map(str,args)],capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  n=len(processes);(work/f'{n:03}.stdout.log').write_bytes(p.stdout);(work/f'{n:03}.stderr.log').write_bytes(p.stderr)
  processes.append({'args':list(map(str,args)),'binary':str(binary or exe),'returncode':p.returncode,'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr),'joined':True})
  check((p.returncode==0)==success,'Real process expected result '+str(n))
  return json.loads(p.stdout)if success else None
 def tree(p):return {q.name:sha(q.read_bytes())for q in p.iterdir()if q.is_file()}
 try:
  pcm=bytes(range(256))*16;wav=wave(pcm);frames=len(pcm)//4
  source=work/'synthetic.wav';source.write_bytes(wav);rights=work/'rights.txt';rights.write_text('Synthetic test silence only; no family audio.\n',encoding='utf-8')
  doc=document(wav,frames);sidecar=work/'reviewed.json';sidecar.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
  def args(dest,review=sidecar):
   a=['--cook-audio','--source',source,'--asset-id',ID,'--name','Synthetic reviewed source','--license',rights,'--output',dest]
   return a+(['--captions-reviewed',review]if review else [])
  cooked=work/'cooked';receipt=run(*args(cooked));payload=cooked/(receipt['sha256']+'.aibaud');encoded=payload.read_bytes();data=parse(encoded)
  check(data['format']==(44100,2,16,0,frames)and data['pcm']==pcm,'Entire exact source-rate stereo PCM preserved')
  check(data['strings']==[ID,'Synthetic reviewed source',sha(wav)],'Complete RIFF hash includes skipped chunks')
  check(data['review']==1 and data['captions']==doc['captions'],'Independent v2 decode retains exact checked text/source-frame cues')
  check(receipt['caption_review']=='checked'and receipt['caption_count']==2,'Receipt exposes checked review/count')
  check(set(tree(cooked))=={'catalog.aibcat','LICENSE.txt','provenance.json',payload.name},'Same four-file typed audio pack')
  provenance_bytes=(cooked/'provenance.json').read_bytes();provenance=json.loads(provenance_bytes)
  check(provenance['caption_review']['sidecar_sha256']==sha(sidecar.read_bytes())and provenance['caption_review']['review_export_sha256']==doc['review_export_sha256'],'Review provenance pins exact sidecar and review bytes')
  check(provenance['caption_review']['automatic_approval']is False and provenance['caption_review']['declaration']==DECLARATION,'Cooker does not imply listening or automatic approval')
  check(str(work).encode()not in provenance_bytes and str(sidecar).encode()not in provenance_bytes,'No host input/output paths in provenance')
  original=tree(cooked)
  inspected=run('--inspect',cooked)['assets'][0];check(inspected['caption_review']=='checked'and inspected['caption_count']==2,'Independent typed pack inspector sees reviewed metadata')
  # A legacy WAV-only invocation must remain byte-identical, including provenance.
  draft=work/'draft';draft_receipt=run(*args(draft,None));draft_data=parse((draft/(draft_receipt['sha256']+'.aibaud')).read_bytes())
  check(draft_data['review']==0 and not draft_data['captions']and draft_data['pcm']==pcm,'WAV-only remains empty draft with exact PCM')
  if baseline:
   old=work/'baseline-draft';run(*args(old,None),binary=baseline);check(tree(old)==tree(draft),'WAV-only all four file bytes unchanged versus old assetc')
  run(*args(cooked),success=False);check(tree(cooked)==original,'Existing reviewed output never overwritten')
  # Corruption/incomplete reviews reject before a stage/final pack appears.
  cases=[]
  def change(label,key,value):
   c=copy.deepcopy(doc);c[key]=value;cases.append((label,json.dumps(c).encode()))
  change('draft','caption_review','draft');change('draftstatus','status','DRAFT_REQUIRES_LISTENING_REVIEW');change('inprogress','status','DRAFT_LISTENING_REVIEW_IN_PROGRESS');change('automatic','automatic_approval',True)
  change('mismatchsha','source_sha256','a'*64);change('mismatchrate','sample_rate',48000);change('mismatchchannels','channels',1);change('mismatchframes','frame_count',frames-1);change('count','caption_count',1);change('fraction','caption_count',2.0);change('bool','schema_version',True)
  change('draftsha','source_caption_draft_sha256','not-a-hash');change('reviewsha','review_export_sha256','A'*64);change('reviewer','reviewer','');change('time','reviewed_at_utc','2026-02-30T00:00:00Z');change('zone','reviewed_at_utc','2026-11-02T00:00:00+01:00');change('decl','declaration','Automatic review completed')
  c=copy.deepcopy(doc);del c['reviewer'];cases.append(('missing',json.dumps(c).encode()))
  c=copy.deepcopy(doc);c['new_field']=0;cases.append(('unknown',json.dumps(c).encode()))
  for label,key,value in [('overlap','start_frame',1),('outside','end_frame',frames+1),('nul','text','bad\0text'),('empty','text',' '),('surrogate','text','\ud800')]:
   c=copy.deepcopy(doc);c['captions'][1][key]=value;cases.append((label,json.dumps(c).encode()))
  c=copy.deepcopy(doc);c['captions'].reverse();cases.append(('reorder',json.dumps(c).encode()))
  c=copy.deepcopy(doc);c['captions']*=1025;c['caption_count']=len(c['captions']);cases.append(('cue-limit',json.dumps(c).encode()))
  c=copy.deepcopy(doc);c['captions'][1]['text']='x'*(256*1024);cases.append(('text-limit',json.dumps(c).encode()))
  cases.extend([('duplicate',sidecar.read_bytes().replace(b'"schema_version": 1',b'"schema_version": 1,"schema_version": 1',1)),('escapedduplicate',sidecar.read_bytes().replace(b'"schema_version": 1',b'"schema_version": 1,"schema_versio\\u006e": 1',1)),('invalidutf8',b'\xff'),('trailing',sidecar.read_bytes()+b'{}'),('json-limit',b' '*(1024*1024+1)),('truncated',sidecar.read_bytes()[:-1])])
  for label,raw in cases:
   path=work/(label+'.json');path.write_bytes(raw);destination=work/('reject-'+label);run(*args(destination,path),success=False)
   check(not destination.exists(),'Rejected '+label+' publishes no final directory');check(tree(cooked)==original,'Rejected '+label+' retains prior reviewed output bytes')
  # A changed RIFF ancillary chunk with identical PCM is still a distinct source.
  source.write_bytes(wav.replace(b'xyz',b'abc'));run(*args(work/'riff-mismatch'),success=False);check(not(work/'riff-mismatch').exists(),'Whole WAV mismatch rejected despite identical PCM');source.write_bytes(wav)
  duplicate=args(work/'duplicate-option')+['--captions-reviewed',sidecar];run(*duplicate,success=False);check(not(work/'duplicate-option').exists(),'Duplicate reviewed option does not publish')
  bom=work/'bom.json';bom.write_bytes(b'\xef\xbb\xbf'+sidecar.read_bytes());b=run(*args(work/'bom',bom));check(b['sha256']==receipt['sha256'],'BOM/newline JSON representation does not alter cooked audio/captions')
  # Exact immutable store transport survives deleting the import sidecar/WAV.
  store=work/'store';store.mkdir();adopted=run('--adopt',cooked,'--store',store);ref=['--ref',adopted['asset_id'],adopted['asset_sha256'],adopted['pack_sha256']]
  run('--inspect-store',store,*ref,success=False);run('--inspect-store',store,'--profile','warm-beginning',*ref)
  private=work/'private';run('--stage-store',store,'--output',private,'--profile','warm-beginning',*ref)
  check((private/adopted['pack_sha256']/payload.name).read_bytes()==encoded,'Private stage owns identical reviewed payload')
  source.unlink();sidecar.unlink();run('--inspect-store',private,'--profile','warm-beginning',*ref);check((private/adopted['pack_sha256']/payload.name).read_bytes()==encoded,'No source/sidecar fallback after removal')
  if adapter:
   # Run the existing source-specific adapter's pure builder with synthetic text,
   # matching its62-cue/complete-frame schema. No original path/audio is opened.
   spec=importlib.util.spec_from_file_location('reviewed_adapter_fixture',adapter);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   large_pcm=bytes(8684544*4);large_wav=wave(large_pcm);large=work/'adapter-synthetic.wav';large.write_bytes(large_wav)
   rows=[{'start_sample':i*100,'end_sample':(i+1)*100,'text':f'Synthetic adapter cue {i+1}'}for i in range(62)]
   d={'status':'DRAFT_REQUIRES_LISTENING_REVIEW','source_sha256':sha(large_wav),'sample_rate':44100,'channels':2,'sample_frames':8684544,'model':'synthetic fixture','segments':rows}
   rv=copy.deepcopy(d);rv.update(status='LISTENING_REVIEW_COMPLETED',reviewer='Synthetic review fixture',reviewed_at_utc='2026-11-02T00:00:00Z',reviewed_segment_count=62)
   for row in rv['segments']:row['listening_reviewed']=True
   one_false=copy.deepcopy(rv);one_false['segments'][31]['listening_reviewed']=False
   one_missing=copy.deepcopy(rv);del one_missing['segments'][61]['listening_reviewed']
   for partial in (d,{**rv,'status':'DRAFT_LISTENING_REVIEW_IN_PROGRESS'},one_false,one_missing,{**rv,'reviewed_segment_count':61}):
    rejected=False
    try:m.build_caption_export(partial,d,sha(large_wav),draft_sha256=sha(b'synthetic draft'),review_sha256=sha(b'synthetic review'))
    except ValueError:rejected=True
    check(rejected,'Actual adapter rejects draft/incomplete synthetic review')
   checked=m.build_caption_export(rv,d,sha(large_wav),draft_sha256=sha(b'synthetic draft'),review_sha256=sha(b'synthetic review'));review=work/'adapter-export.json';review.write_text(json.dumps(checked),encoding='utf-8')
   ar=run('--cook-audio','--source',large,'--asset-id',ID,'--name','Synthetic adapter review','--license',rights,'--output',work/'adapter-cooked','--captions-reviewed',review)
   decoded=parse((work/'adapter-cooked'/(ar['sha256']+'.aibaud')).read_bytes());check(decoded['pcm']==large_pcm and decoded['captions']==checked['captions']and decoded['review']==1,'Actual adapter schema cooks complete synthetic196.928-second PCM and all62 cues')
  check(not any('.staging-'in p.name for p in work.iterdir()),'Invalid sidecars create no staging residue')
  result.update(status='passed',cooked_sha256=sha(encoded),pcm_sha256=sha(pcm),negative_cases=len(cases),checked_ref=adopted,adapter_exercised=bool(adapter),baseline_compared=bool(baseline))
 except Exception as error:result['error']=str(error)
 result.update(check_count=len(checks),checks=checks,processes=processes,all_owned_children_joined=all(p['joined']for p in processes));report=work/'verification.json';report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':result['status'],'checks':len(checks),'report':str(report),'error':result.get('error')}));return 0 if result['status']=='passed'else 1
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('assetc',type=Path);p.add_argument('output',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--adapter',type=Path);a=p.parse_args();raise SystemExit(verify(a.assetc,a.output,a.baseline,a.adapter))
