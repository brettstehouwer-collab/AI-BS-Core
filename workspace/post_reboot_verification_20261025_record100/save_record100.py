"""Retain local evidence and append recovery checkpoint; no runtime changes."""
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(r'C:\AI-BS')
EVIDENCE=Path(__file__).resolve().parent
BACKUP=ROOT/'backups/post_reboot_verification_20261025_record100'
BACKUP.mkdir(parents=True,exist_ok=True)
now=datetime.now(timezone.utc)
eastern=now.astimezone(timezone(timedelta(hours=-4)))

def read_json(file):
    return json.loads(Path(file).read_text(encoding='utf-8-sig'))

def sha(data):
    return hashlib.sha256(data).hexdigest()

samples=[read_json(EVIDENCE/name) for name in ('sample1.json','sample2.json','final.json')]
last=samples[-1]
followup=read_json(EVIDENCE/'pagefile_followup.json')
runtime=read_json(EVIDENCE/'runtime/runtime_receipt.json')
tasks=read_json(EVIDENCE/'runtime/task_receipt.json')
http=read_json(EVIDENCE/'http_acceptance.json')
connectors=read_json(EVIDENCE/'runtime/connector_readiness.json')
network=read_json(EVIDENCE/'network_readonly.json')
assert http['http_all_pass'] and http['static_all_pass']
assert runtime['core_loopback_only'] and runtime['unreal_8888_off'] and runtime['paired_core_pin_matches']
assert not runtime['errors'] and all(v['admitted'] for v in runtime['core'].values())
assert all(v['matches_record99'] for v in runtime['configs'].values())
assert all(all(v['six_false_controls'].values()) for v in runtime['core'].values() if 'six_false_controls' in v)
assert all(t['state']=='Running' and t['principal']=='footb' for t in tasks['tasks'])
assert connectors['all_healthy']
assert (ROOT/'version.txt').read_text().strip()=='v5.329.70'
main_codex=[max(s['codex'],key=lambda p:p['private_bytes']) for s in samples]
assert len({(p['pid'],p['created_utc']) for p in main_codex})==1
gib=lambda n: round(n/2**30,3)
commit=last['committed_bytes']/last['commit_limit_bytes']*100
c_free=gib(followup['c_free_bytes'])
private=gib(main_codex[-1]['private_bytes'])

summary=f'''POST-REBOOT RECOVERY — RECORD100
Saved {now.isoformat()} / {eastern.isoformat()} Eastern
Boot verified {last['last_boot_utc']}; Windows user footb.

Publishing root/www and public API health are HTTP200 after real reboot/logon. Local backend/gateway/frontend/Ollama read-only checks also pass. 17 bounded rawGET checks pass including8expected404private/tracking paths;19reviewed site files exactly match the prior manifest. NoJavaScript/forms/analytics/model jobs were executed. This accepts startup/basicavailability, not full business/media/device workflows.

Fresh runtime: backend35908, gateway35916, frontend35992, Ollama35964, Nginxmaster14176/worker26640, publishingconnector14092 and scopedAPIconnector36028. Owner/executable/creation/arguments/config inspected; core and origin loopbackonly; sixcontrolsfalse;8888off. BothpublishingtasksRunning asfootb. Eachreviewed connectorreadiness200/fourHAconnections. ThreeRecord99source/config hashes and pairedcorepin match. SYSTEMconnector6180 preserved. PIDs remain dated evidence and must be rediscovered before any action.

RESOURCE FINDINGS: restart relieved earlier critical pressure but did not establish a fixed Codex issue. At22:25:02UTC Codex30896private{gib(main_codex[0]['private_bytes'])}GiB;22:25:44UTC{gib(main_codex[1]['private_bytes'])}GiB;22:27:10UTC{private}GiB. Same creation identity22:13:50UTC. A37secondintermediate sample was flat, followed by anotherlargejump; do not call stable or prove an unboundedleak/codepath from this short observation. Systemcommit at22:27:10UTC{commit:.2f}% ({gib(last['committed_bytes'])}GiB), RAMused{gib(last['total_physical_bytes']-last['free_physical_bytes'])}GiB. WSLalsoholds{gib(next(p['private_bytes'] for p in last['top_processes'] if p['name']=='vmmemWSL'))}GiBprivate; noWSL/VMchangesperformed.

C:146.568GiBfree at22:25:02UTC,133.989GiB at22:27:10UTC, then{c_free}GiB at22:27:34UTC. Lastvalue is about{c_free-124.69:.2f}GiBmorethan lastpreboot124.69GiB; about{c_free-40.307:.2f}GiBabove earlierlow40.307GiB. Do notattribute allrecoveredspace to reboot: substantialrecovery precededrestart. The temporarydip/rebound is observed; causeunattributed. Pagefilelengthstayed{gib(followup['pagefile_file_bytes'])}GiB; WMI63126MBallocated/0MBused/0peak in retainedsnapshots. GlobalautomaticFalse withperdrive0/0 remains unchanged. Pagefilecapacity is distinct from currentuse. No files deleted, cache/modelscan, dump, processstop, reboot, pagingchange orcleanup.

NETWORK: primaryEthernet2 2.5Gbps/DHCP192.168.4.35/22 via192.168.4.1; separateEthernet1Gbps/static192.168.10.50/24/noGW; IPEnableRouter0. NewUDP67ownerSYSTEMSharedAccess5736 at192.168.137.1 mapsWi-Fi4, not primaryEthernetpath. ICS COMreturned6connections sharingdisabled but omittedWi-Fi4; householdforwarding remainsunverified. Do notenableICSorforcehistoricaltopology. No networkmutations.

DECISION: recoverycheckscomplete; memorygrowthunresolved. Preserve state and keepmajorworkdeferred. Safest next troubleshooting step is close/reopenCodex afteractiveworkends, then start a small fresh task from this checkpoint to compare boundedidle/active readings. This is a suggested diagnostic, not a confirmedfix. Noapprestart/update/settingchange ornewtaskcreated. OfficialOpenAIDocs reviewed: https://learn.chatgpt.com/docs/reference/troubleshooting (restart recovery, focusedfreshchat, reviewlogprivacy; doesnotestablishspecificmemorybug). No bugreport orlogs sent.

Deferred site items: privacy-safeanalytics;135px390pxoverflow; missingbackground/threePDFs; completeguestbook/API/HLS/native/deviceacceptance. CreationSuite documentraces/recovery/losslessedits/longblocks/print/theatricalpolicy andVM/security gatesremainopen. Automaticgoalremainspaused. No cloudledger/globalmemorywrites.

Evidence: {EVIDENCE}
Checkpoint: {BACKUP}
'''
(EVIDENCE/'Recovery_Report.txt').write_text(summary,encoding='utf-8')
(EVIDENCE/'NEXT_SESSION.txt').write_text('Resume C:/AI-BS/docs/CODEX_HANDOFF.md Record100 and workspace/post_reboot_verification_20261025_record100/Recovery_Report.txt. Keep work bounded to Codex memory/resource diagnosis first; the site/API recovered after reboot. Rediscover all current process identities. No automatic cleanup/paging/network/VM changes or beta monitor. Do not replay transcripts. Read fresh resource measurements before major work.\n',encoding='utf-8')

relative_files=['AGENTS.md','docs/CODEX_HANDOFF.md','docs/CODEX_TASKS.md','docs/CODEX_JOURNAL.md','docs/CODEX_DECISIONS.md','docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md','docs/engineering_ledger/cloud_index.json']
originals={rel:(ROOT/rel).read_bytes() for rel in relative_files}
before={}
for rel,data in originals.items():
    target=BACKUP/'before'/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        raise RuntimeError('Checkpoint already has before evidence; inspect before repeating')
    target.write_bytes(data)
    before[rel]={'sha256':sha(data),'bytes':len(data)}
(BACKUP/'before_manifest.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')

record='\n\n## Record100 — Post-reboot recovery accepted; Codex memory growth remains open ('+eastern.strftime('%Y-%m-%d %H:%M:%S UTC-04:00')+')\n'+summary+'\nHelpers: /root/postboot_runtime performed read-only identity/config/task/connector and boundedUDP67clarification; /root/postboot_review checked scope/acceptance/privacy. Bothfinished; no service/config/sourcechanges. Their reports are evidence, not hidden reasoning. Localrecords86-100pendingcloudsync; lastverifiedcloud85/receipt38unchanged.\n'
append_files=['docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md']
for rel in append_files:
    if (ROOT/rel).read_bytes()!=originals[rel]:
        raise RuntimeError('Document changed before append: '+rel)
    with (ROOT/rel).open('ab') as stream:
        stream.write(record.encode('utf-8'))
    assert (ROOT/rel).read_bytes().startswith(originals[rel])

decisions='docs/CODEX_DECISIONS.md'
adr='\n\n## ADR-049: Startup availability and recurring resource growth are separate results\nA real reboot/logon with fresh owned identities, admitted configuration, rawHTTP success and unchanged reviewed static bytes accepts startup/basicavailability only. Continued process privatecommit growth after restart leaves its underlying cause unresolved; do not infer a leak codepath, stablefix or attribute every diskdelta to paging. Keep majorwork deferred, retain short sanitized samples and use a focused fresh session for the next diagnostic. Preserve pagefile capacity/settings, credentials, originals and workingservices; do not submit logs or restart/update the app automatically.\n'
assert (ROOT/decisions).read_bytes()==originals[decisions]
with (ROOT/decisions).open('ab') as stream:
    stream.write(adr.encode('utf-8'))

tasks_file='docs/CODEX_TASKS.md'
tasks_text=originals[tasks_file].decode('utf-8-sig')
start=tasks_text.index('<!-- AUTO_CHECKPOINT_SUMMARY_START -->')
end=tasks_text.index('<!-- AUTO_CHECKPOINT_SUMMARY_END -->',start)+len('<!-- AUTO_CHECKPOINT_SUMMARY_END -->')
new_summary=f'''<!-- AUTO_CHECKPOINT_SUMMARY_START -->
## Current Authoritative Checkpoint Summary
- Record100: actual reboot/logon startup/basicavailability VERIFIED; sourcev5.329.70. Automaticgoalremainspaused. CodexmemorygrowthisUNRESOLVED; defermajorwork.
- Root/wwwPublishing andpublicAPIhealth200;17boundedrawGETchecks and19staticfilehashchecks pass. NoJS/forms/visitorwrites/modeljobs. Fullguestbook/media/deviceacceptance remainsopen.
- Freshidentity/config/task checks pass: backend35908,gateway35916,frontend35992,Ollama35964,Nginx14176/26640,userconnector14092,scoped36028. Core/originloopback;6false;8888off;2publishingtasksRunningasfootb;bothconnectors4HA. Rediscoverbeforeaction; savedPIDsaredated.
- Codex30896private4.28->8.30->{private:.2f}GiBfrom22:25:02to22:27:10UTC. Systemcommit{commit:.2f}% atlastfullsample. Do notclaimfixed/stable/unboundedleakcodepath.
- Latestdiskfollowup22:27:34UTC C:free{c_free:.2f}GiB;pagefilefile{gib(followup['pagefile_file_bytes']):.3f}GiB,WMI63126MBallocated/0used. Settings0/0unchanged. Earlier133.989GiBfree transientdip retained; causeunknown. No cleanup/paging/modelcachedeletion.
- PrimaryEthernet2 2.5Gbps/DHCP192.168.4.35/22via192.168.4.1;otherEthernet1Gbps/static192.168.10.50/noGW;IPEnableRouter0. UDP67SharedAccessonWi-Fi4hasincompleteICSvisibility, notproofoldhouseholdICS. No networkchanges.
- Next: save/finishactivework, operator may close/reopenCodex and startsmallfreshtaskfromworkspace/post_reboot_verification_20261025_record100/NEXT_SESSION.txt for boundedidle/activecomparisons. Noautomaticrestart/update/newtask.
- Do notautobetaMonitor(sync/capture/scan);privacy-safeanalytics/mobilebackground/PDFs andCreationSuite/VM/securitygatesremainopen. Local86-100pendingcloudsync; lastverified85/receipt38. Noexternal/globalmemorywrite.
<!-- AUTO_CHECKPOINT_SUMMARY_END -->'''
tasks_text=tasks_text[:start]+new_summary+tasks_text[end:]
tasks_text=tasks_text.replace('- [ ] Operator computer restart (not performed by agent).','- [x] Operator computer restart verified Record100 (boot22:12:53UTC; performed by operator).')
tasks_text+='\n\n## Record100 — Actual reboot verification\n- [x] Read-only resource samples/settings/all-drivefree and fresh owned runtime/config/task/connector identity checks.\n- [x] Publishing root/www/API basicavailability after realreboot/logon;17rawHTTP checks and19sitehashchecks pass.\n- [x] Coreloopback/sixfalse/8888off; preserveSYSTEM andallworkingprocesses.\n- [x] Save recurringCodexgrowth, temporarydiskdip, read-onlyUDP67clarification andbefore/finalhashes withoutrootcauseclaims.\n- [ ] ResolveCodexmemorygrowth in boundedfreshsession beforemajorwork; noautomaticapprestart/cleanup/pagingchange.\n- [ ] Earlier site/CreationSuite/VM/security/devicegates andseparatelyauthorizedcloudsync remainpending.\n'
assert (ROOT/tasks_file).read_bytes()==originals[tasks_file]
(ROOT/tasks_file).write_text(tasks_text,encoding='utf-8',newline='')

index_file='docs/engineering_ledger/cloud_index.json'
index=read_json(ROOT/index_file)
ledger_before=index['ledger'].copy()
index['pending_local_records']=list(dict.fromkeys(index.get('pending_local_records',[])+[100]))
index['pending_local_note']='Record100 local post-reboot availability/resource evidence saved; local86-100pendingcloudsync. Lastverifiedcloud85/receipt38unchanged. No upload.'
assert (ROOT/index_file).read_bytes()==originals[index_file]
(ROOT/index_file).write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
assert read_json(ROOT/index_file)['ledger']==ledger_before
assert (ROOT/'AGENTS.md').read_bytes()==originals['AGENTS.md']

final_docs={rel:{'sha256':sha((ROOT/rel).read_bytes()),'bytes':(ROOT/rel).stat().st_size} for rel in relative_files}
for rel in append_files+[decisions]:
    assert (ROOT/rel).read_bytes().startswith(originals[rel])
evidence={str(f.relative_to(EVIDENCE)).replace('\\','/'):{'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size} for f in EVIDENCE.rglob('*') if f.is_file()}
checkpoint={'record':100,'source_version':'v5.329.70','saved_utc':now.isoformat(),'saved_eastern':eastern.isoformat(),'status':'post_reboot_basic_availability_verified_memory_growth_unresolved','automatic_goal':'left paused','runtime_changes':False,'application_source_changes':False,'deletion_or_paging_changes':False,'network_changes':False,'external_upload':False,'global_memory_update':False,'http_checks':len(http['checks']),'static_hash_checks':len(http['static_hash_checks']),'all_basic_availability_pass':True,'codex_last_private_gib':private,'last_full_sample_utc':last['observed_utc'],'last_commit_percent':round(commit,2),'latest_disk_followup_utc':followup['observed_utc'],'latest_c_free_gib':c_free,'before_manifest':'before_manifest.json','final_document_hashes':final_docs,'evidence_hashes':evidence,'next':'Bounded Codex memory/resource troubleshooting with fresh identities; no majorwork or automatic apprestart/cleanup/paging/network/VM actions'}
(BACKUP/'checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
assert read_json(BACKUP/'checkpoint.json')['final_document_hashes']==final_docs
assert 'Record100' in (ROOT/'docs/CODEX_HANDOFF.md').read_text(encoding='utf-8-sig')
print(json.dumps({'status':checkpoint['status'],'checkpoint':str(BACKUP/'checkpoint.json'),'documents_verified':len(final_docs),'evidence_files_hashed':len(evidence),'report':str(EVIDENCE/'Recovery_Report.txt'),'c_free_gib':c_free,'codex_private_gib':private}))
