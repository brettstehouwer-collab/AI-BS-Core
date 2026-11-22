# Trusted controller/primitive infrastructure tests only. Never invokes GuestProbe.Main.
[CmdletBinding()]
param([string]$EvidenceRoot)
$ErrorActionPreference='Stop'
if(-not $EvidenceRoot){$EvidenceRoot=Join-Path 'C:\AI-BS\backups' ('disposable_probe_infrastructure_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'_'+[Guid]::NewGuid().ToString('N'))}
if(Test-Path -LiteralPath $EvidenceRoot){throw 'EXISTING_EVIDENCE_PRESERVED'}
$null=New-Item -ItemType Directory -Path $EvidenceRoot
$source=Join-Path $PSScriptRoot 'GuestProbe.cs'
$compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$guestExe=Join-Path $EvidenceRoot 'GuestProbe.COMPILE_ONLY.exe'
$harnessSource=Join-Path $EvidenceRoot 'TrustedInfrastructureHarness.cs'
$harnessExe=Join-Path $EvidenceRoot 'TrustedInfrastructureHarness.exe'
$code=@'
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Diagnostics;
using System.Threading;
using System.Collections.Generic;
using System.Globalization;
using AIBS.DisposableProbe;
public static class TrustedInfrastructureHarness {
    static int checks;
    static void Check(bool okay,string label){if(!okay)throw new Exception("ASSERTION_FAILED:"+label);checks++;Console.WriteLine("PASS "+label);}
    static void Reject(Action action,string label){try{action();}catch(ProbeRejected){Check(true,label);return;}throw new Exception("EXPECTED_REJECTION:"+label);}
    static string[] Valid(){return new[]{"--mode","emit","--attempt","20111111-2222-4333-8444-555555555555","--challenge",new String('a',64),"--timeout-ms","1000","--output-bytes","4096","--worker-sid","S-1-5-21-111-222-333-1001","--vm-id","30111111-2222-4333-8444-555555555555","--image-sha256",new String('b',64)};}
    static void Bad(int index,string value,string label){var args=Valid();args[index]=value;Reject(()=>Options.Parse(args),label);}
    static int Fixture(string mode){
        if(mode=="emit"){Console.Out.Write("trusted-probe\n");Console.Error.Write("trusted-diagnostic\n");return 7;}
        if(mode=="sleep"){Thread.Sleep(10000);return 0;}
        if(mode=="overflow"){byte[] block=Enumerable.Repeat((byte)'X',4096).ToArray();using(var output=Console.OpenStandardOutput())using(var error=Console.OpenStandardError())for(int i=0;i<512;i++)(i%2==0?output:error).Write(block,0,block.Length);return 0;}
        return 92;
    }
    public static int Main(string[] args){
        // Separate trusted fixture entry. The actual guest entry point is never called.
        if(args.Length==2 && args[0]=="--trusted-fixture")return Fixture(args[1]);
        if(args.Length!=0)return 93;
        try{
            var parsed=Options.Parse(Valid());Check(parsed.Mode=="emit" && parsed.TimeoutMs==1000 && parsed.OutputBytes==4096,"canonical CLI");
            Check(parsed.PublicArguments().SequenceEqual(Valid()),"canonical public argument round trip");
            Reject(()=>Options.Parse(null),"null argument vector refused");
            Reject(()=>Options.Parse(Valid().Take(14).ToArray()),"missing argument refused");
            Reject(()=>Options.Parse(Valid().Concat(new[]{"--command","cmd.exe"}).ToArray()),"unknown command refused");
            Bad(0,"--Mode","argument case exact");Bad(1,"powershell","arbitrary mode refused");Bad(1,"emit\ncmd","injected command refused");
            Bad(2,"--mode","duplicate option refused");Bad(3,"20111111222243338444555555555555","GUID N refused");Bad(3,"20111111-2222-4333-8444-55555555555A","uppercase attempt refused");
            Bad(5,new String('A',64),"uppercase challenge refused");Bad(5,new String('a',63),"short challenge refused");Bad(5,new String('a',64)+"\n","newline digest refused");
            Bad(7,"0","zero deadline refused");Bad(7,"499","below minimum deadline refused");Bad(7,"30001","over maximum deadline refused");Bad(7,"01000","noncanonical deadline refused");Bad(7,"2147483648","overflow deadline refused");
            Bad(9,"4095","below minimum output refused");Bad(9,"1048577","over 1MiB combined ceiling refused");Bad(9,"4096.0","fractional output refused");
            Bad(11,"S-1-5-18","SYSTEM SID refused");Bad(11,"S-1-5-21-2133766663-4066672948-2456486318-1005","known host worker refused");Bad(13,"not-a-vm","VM identity syntax refused");Bad(15,"../../image","image digest required");
            var child=Valid().Concat(new[]{"--child-token",new String('c',64),"--parent-pid","1","--parent-start-ticks","123"}).ToArray();Check(Options.Parse(child).IsChild,"exact fixed child CLI");child[20]="--command";Reject(()=>Options.Parse(child),"child command option refused");
            string sid="S-1-5-21-111-222-333-1001",name=@"GUEST\aibs_vm_worker";
            Check(GuestIdentity.Policy(sid,sid,name,"GUEST",true,false,false,true,true),"standard virtual guest identity accepted by policy");
            Check(!GuestIdentity.Policy(sid,sid,name,"GUEST",true,true,false,true,true),"administrator membership refused including filtered membership");
            Check(!GuestIdentity.Policy(sid,sid,name,"GUEST",true,false,true,true,true),"elevated token refused");
            Check(!GuestIdentity.Policy(sid,sid,name,"GUEST",false,false,false,true,true),"nonmedium token refused");
            Check(!GuestIdentity.Policy(sid,sid,name,"GUEST",true,false,false,true,false),"nonVirtualBox machine refused");
            Check(!GuestIdentity.Policy(sid,sid,@"DOMAIN\aibs_vm_worker","GUEST",true,false,false,true,true),"domain identity refused");
            Check(!GuestIdentity.Policy(sid,sid,@"GUEST\ai_bs guest","GUEST",true,false,false,true,true),"integration guest account refused");
            Check(!GuestIdentity.Policy(sid,sid+"0",name,"GUEST",true,false,false,true,true),"SID mismatch refused");
            var output=new OutputBuffer(5);output.Add(false,Encoding.ASCII.GetBytes("abc"),3);output.Add(true,Encoding.ASCII.GetBytes("de"),2);Check(output.Count==5 && !output.Overflow,"exact combined byte boundary");output.Add(true,new byte[]{88},1);Check(output.Count==5 && output.Overflow && Encoding.ASCII.GetString(output.Error)=="de","combined stdout stderr overflow bounded");
            Reject(()=>new OutputBuffer(1048577),"buffer cannot exceed contract");
            Check(FixedRunner.Quote(@"C:\path with spaces\file.exe")=="\"C:\\path with spaces\\file.exe\"","fixed Windows path quoting");
            Check(FixedRunner.Quote("x\\")=="\"x\\\\\"","trailing slash quoting");Reject(()=>FixedRunner.Quote("x\ncmd"),"argument newline refused");
            using(var job=new Job()) {var limits=job.Read<Native.EXTENDED_LIMIT>(9);var cpu=job.Read<Native.CPU_RATE>(15);Check(limits.Basic.ActiveLimit==1 && limits.Basic.Flags==Job.LimitFlags && limits.JobMemory.ToUInt64()==268435456,"native Job Object limits readback");Check(cpu.Flags==5 && cpu.Rate==2500,"native hard CPU cap readback");Check(job.Empty,"fresh job has no processes");}
            string self=Process.GetCurrentProcess().MainModule.FileName;string windows=Environment.GetFolderPath(Environment.SpecialFolder.Windows);var env=new Dictionary<string,string>{{"SYSTEMROOT",windows},{"WINDIR",windows}};
            var completed=FixedRunner.Run(self,new[]{"--trusted-fixture","emit"},5000,4096,env,null);
            Check(completed.State=="COMPLETED" && completed.ExitCode==7 && completed.TerminationConfirmed,"trusted fixed fixture exit status and empty job");
            Check(Encoding.UTF8.GetString(completed.Output.Out)=="trusted-probe\n" && Encoding.UTF8.GetString(completed.Output.Error)=="trusted-diagnostic\n","trusted fixed fixture separate streams retained");
            var timeout=FixedRunner.Run(self,new[]{"--trusted-fixture","sleep"},500,4096,env,null);Check(timeout.State=="TIMED_OUT" && timeout.TerminationConfirmed && timeout.Elapsed<5000,"trusted fixture timeout and confirmed job empty");
            bool gone=false;try{using(var p=Process.GetProcessById(completed.Pid))gone=p.HasExited;}catch(ArgumentException){gone=true;}Check(gone,"completed child no longer running");
            var clock=Stopwatch.StartNew();var cancelled=FixedRunner.Run(self,new[]{"--trusted-fixture","sleep"},5000,4096,env,()=>clock.ElapsedMilliseconds>=150);Check(cancelled.State=="CANCELLED" && cancelled.TerminationConfirmed && cancelled.Elapsed<5000,"trusted fixture cancellation and confirmed job empty");
            var overflow=FixedRunner.Run(self,new[]{"--trusted-fixture","overflow"},5000,4096,env,null);Check(overflow.State=="OUTPUT_LIMIT" && overflow.Output.Count==4096 && overflow.TerminationConfirmed,"trusted fixture aggregate output ceiling and termination");
            var top=FixedRunner.Run(self,new[]{"--trusted-fixture","overflow"},5000,1048576,env,null);Check(top.State=="OUTPUT_LIMIT" && top.Output.Count==1048576 && top.TerminationConfirmed,"trusted fixture maximum 1MiB combined ceiling");
            Console.WriteLine("INFRASTRUCTURE_CHECKS_PASSED="+checks);Console.WriteLine("GUEST_ENTRY_EXECUTED=false");Console.WriteLine("VM_ACCEPTANCE_CHECKS=0");return 0;
        }catch(Exception error){Console.Error.WriteLine(error.ToString());return 1;}
    }
}
'@
[IO.File]::WriteAllText($harnessSource,$code,[Text.UTF8Encoding]::new($false))
$compileArgs=@('/nologo','/target:exe','/platform:x64','/optimize+','/reference:System.Web.Extensions.dll',('/out:'+$guestExe),$source)
& $compiler @compileArgs 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceRoot 'guest_compile.txt')
if($LASTEXITCODE-ne 0){throw 'GUEST_COMPILE_FAILED'}
$compileArgs=@('/nologo','/target:exe','/platform:x64','/optimize+','/reference:System.Web.Extensions.dll','/main:TrustedInfrastructureHarness',('/out:'+$harnessExe),$source,$harnessSource)
& $compiler @compileArgs 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceRoot 'harness_compile.txt')
if($LASTEXITCODE-ne 0){throw 'TRUSTED_HARNESS_COMPILE_FAILED'}
& $harnessExe 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceRoot 'infrastructure_results.txt')
$exit=$LASTEXITCODE
Get-FileHash -LiteralPath $source,$guestExe,$harnessSource,$harnessExe -Algorithm SHA256 | Select-Object Path,Hash | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $EvidenceRoot 'hashes.json') -Encoding UTF8
[ordered]@{schema_version=1;infrastructure_exit_code=$exit;guest_entry_executed=$false;guest_executable_compiled_only=$true;vm_acceptance_checks=0;evidence_root=$EvidenceRoot;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $EvidenceRoot 'result.json') -Encoding UTF8
if($exit-ne 0){throw ('TRUSTED_INFRASTRUCTURE_FAILED evidence='+$EvidenceRoot)}
Write-Host ('Evidence: '+$EvidenceRoot)
