"""Passive Phase 4 prerequisites. No logon, VM query/start or task execution.

Session inventory uses documented read-only WTS APIs. Only the designated worker
session is exported; other users' names and process arguments are not retained.
"""
from __future__ import annotations
import argparse,ctypes,hashlib,json,os,sys
from ctypes import wintypes as W
from datetime import datetime,timezone
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parents[1]
WORKER_SID='S-1-5-21-2133766663-4066672948-2456486318-1005'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def worker_context_status(actor_is_worker,account_matches,desktop_present,shell_present):
 """Describe context evidence without treating a desktop logon as mandatory.

 A normal authenticated RunAs shell can provide the worker identity. The real
 entry still enforces nonadministrator/medium-integrity and all other guards.
 """
 if not account_matches:return 'EXPECTED_WORKER_ACCOUNT_NOT_VERIFIED'
 if actor_is_worker:return 'WORKER_ENTRY_ADMISSION_REQUIRED'
 if shell_present:return 'WORKER_SHELL_PRESENT_ENTRY_ADMISSION_REQUIRED'
 if desktop_present:return 'WORKER_DESKTOP_PRESENT_ENTRY_ADMISSION_REQUIRED'
 return 'AUTHENTICATED_WORKER_CONTEXT_REQUIRED'

def account_sid(name):
 adv=ctypes.WinDLL('advapi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 lookup=adv.LookupAccountNameW;lookup.argtypes=[W.LPCWSTR,W.LPCWSTR,W.LPVOID,ctypes.POINTER(W.DWORD),W.LPWSTR,ctypes.POINTER(W.DWORD),ctypes.POINTER(W.DWORD)];lookup.restype=W.BOOL
 size=W.DWORD();domain_size=W.DWORD();use=W.DWORD()
 lookup(None,name,None,ctypes.byref(size),None,ctypes.byref(domain_size),ctypes.byref(use))
 if not size.value:return {'found':False,'win32_error':ctypes.get_last_error()}
 sid=ctypes.create_string_buffer(size.value);domain=ctypes.create_unicode_buffer(domain_size.value)
 if not lookup(None,name,sid,ctypes.byref(size),domain,ctypes.byref(domain_size),ctypes.byref(use)):raise ctypes.WinError(ctypes.get_last_error())
 convert=adv.ConvertSidToStringSidW;convert.argtypes=[W.LPVOID,ctypes.POINTER(W.LPWSTR)];convert.restype=W.BOOL
 value=W.LPWSTR()
 if not convert(sid,ctypes.byref(value)):raise ctypes.WinError(ctypes.get_last_error())
 try:return {'found':True,'sid':value.value,'matches_expected':value.value==WORKER_SID}
 finally:
  kernel.LocalFree.argtypes=[W.LPVOID];kernel.LocalFree.restype=W.LPVOID;kernel.LocalFree(ctypes.cast(value,W.LPVOID))

def sessions():
 class Session(ctypes.Structure):_fields_=[('id',W.DWORD),('station',W.LPWSTR),('state',ctypes.c_int)]
 api=ctypes.WinDLL('wtsapi32',use_last_error=True);enum=api.WTSEnumerateSessionsW
 enum.argtypes=[W.HANDLE,W.DWORD,W.DWORD,ctypes.POINTER(ctypes.POINTER(Session)),ctypes.POINTER(W.DWORD)];enum.restype=W.BOOL
 query=api.WTSQuerySessionInformationW;query.argtypes=[W.HANDLE,W.DWORD,ctypes.c_int,ctypes.POINTER(W.LPWSTR),ctypes.POINTER(W.DWORD)];query.restype=W.BOOL
 free=api.WTSFreeMemory;free.argtypes=[W.LPVOID];free.restype=None
 buffer=ctypes.POINTER(Session)();count=W.DWORD()
 if not enum(None,0,1,ctypes.byref(buffer),ctypes.byref(count)):raise ctypes.WinError(ctypes.get_last_error())
 states={0:'active',1:'connected',2:'connect_query',3:'shadow',4:'disconnected',5:'idle',6:'listen',7:'reset',8:'down',9:'init'}
 found=[];unknown=0
 try:
  if count.value>256:raise RuntimeError('WTS session bound exceeded')
  for i in range(count.value):
   item=buffer[i];name=W.LPWSTR();length=W.DWORD()
   if not query(None,item.id,5,ctypes.byref(name),ctypes.byref(length)):unknown+=1;continue
   try:
    if name.value and name.value.casefold()=='aibs_vm_worker':found.append({'session_id':item.id,'state':states.get(item.state,'unknown'),'worker_account':True})
   finally:free(ctypes.cast(name,W.LPVOID))
 finally:free(buffer)
 return {'enumerated':True,'session_count':count.value,'unreadable_session_names':unknown,'worker_sessions':found,'other_names_exported':False}

def inspect():
 if os.name!='nt':raise RuntimeError('Windows required')
 actor=account_sid(psutil.Process().username());worker=account_sid('aibs_vm_worker');session=sessions()
 processes=[];vms=[];unreadable=0
 for p in psutil.process_iter(['pid','name','username']):
  try:
   if (p.info['username'] or '').casefold().endswith('\\aibs_vm_worker'):processes.append({'pid':p.pid,'name':p.name(),'created':p.create_time()})
   if (p.info['name'] or '').casefold() in {'virtualbox.exe','virtualboxvm.exe','vboxheadless.exe','vboxsvc.exe'}:vms.append({'pid':p.pid,'name':p.name(),'created':p.create_time()})
  except psutil.Error:unreadable+=1
 control=ROOT/'isolated_workers/windows/control';entry=control/'Inspect-CurrentWorkerDesktop.ps1'
 source={p.relative_to(ROOT).as_posix():digest(p) for p in [entry,control/'desktop_inspection/DesktopProfile.ps1',control/'desktop_inspection/DesktopQuery.cs',ROOT/'backend/core/run_phase4_controller.ps1',ROOT/'backend/core/coding_workflow.py']}
 # Secure XML parser from the pinned inspection module is exercised separately;
 # this passive report uses no XML-derived value as execution authority.
 vm=ROOT/'isolated_workers/windows/runtime/base_preparation_v2/vms/AI-BS-Eval-Base-20261023/AI-BS-Eval-Base-20261023.vbox'
 info={'config_exists':vm.is_file(),'config_sha256':digest(vm) if vm.is_file() else None,'actual_hypervisor_state':'not_queried','starts_or_changes_requested':False}
 ready=worker.get('matches_expected',False) and any(s['state']=='active' for s in session['worker_sessions'])
 shells=[p for p in processes if p['name'].casefold() in {'powershell.exe','pwsh.exe'}]
 actor_matches=actor.get('sid')==WORKER_SID
 status=worker_context_status(actor_matches,worker.get('matches_expected',False),ready,bool(shells))
 return {'utc':datetime.now(timezone.utc).isoformat(),'mode':'PASSIVE_HOST_PREREQUISITES_ONLY','actor_is_designated_worker':actor_matches,'worker_account':worker,'sessions':session,'worker_processes':processes,'worker_shell_processes':shells,'worker_shell_context_present':bool(shells),'vm_processes':vms,'unreadable_processes':unreadable,'worker_interactive_session_present':ready,'actor_identity_matches_entry_account':actor_matches,'entry_admission_status':'not_run; medium integrity, admin exclusion and all other entry gates still required','prerequisite_status':status,'vm_config':info,'source_sha256':source,'resources':{'ram_total_gib':round(psutil.virtual_memory().total/2**30,2),'ram_available_gib':round(psutil.virtual_memory().available/2**30,2),'c_free_gib':round(psutil.disk_usage('C:\\').free/2**30,2)},'TaskAuthority':False,'ProviderAccepted':False,'RuntimeVerified':False,'LicensingVerified':False,'actual_containment_cases_run':0,'logon_attempted':False,'token_impersonation_or_alternate_account_launch':False,'vm_query_or_start':False,'credential_values_exported':False}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 dest=args.output.resolve()
 if not dest.is_relative_to((ROOT/'backups').resolve()) or not dest.parent.is_dir():raise RuntimeError('Existing workspace backup directory required')
 result=inspect()
 with dest.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['prerequisite_status','worker_interactive_session_present','worker_shell_context_present','actor_is_designated_worker','actual_containment_cases_run','vm_query_or_start','resources']}))
