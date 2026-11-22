using System;
using System.IO;
using System.Diagnostics;
using System.Text;
using System.Collections.Generic;
using System.Web.Script.Serialization;
internal static class WheelSetupTests {
    static int passed;
    static void Check(string name,bool value){if(!value)throw new Exception("FAIL "+name);passed++;Console.WriteLine("PASS "+name);}
    static bool Throws(Action action){try{action();return false;}catch{return true;}}
    static WheelGuestFacts Facts(){return new WheelGuestFacts{UUID="6c5a53da-ab80-4ecb-8be6-4059266f736e",Manufacturer="innotek GmbH",Model="VirtualBox",SID="S-1-5-21-100-200-300-1000",Is64Bit=true,MediumIntegrity=true,EnabledNics=0};}
    static int Main(string[] args){
        var completion=new WheelCompletion();Check("close before Install is unverified nonzero",completion.ExitCode==3);
        Check("first human action admitted once",completion.Start()&&!completion.Start());completion.Complete(WheelOutcome.Failed);Check("failed GUI close returns nonzero",completion.ExitCode==1);
        Check("completed outcome cannot be replaced",Throws(delegate{completion.Complete(WheelOutcome.Verified);}));
        completion=new WheelCompletion();Check("cannot report verified without Install action",Throws(delegate{completion.Complete(WheelOutcome.Verified);})&&completion.ExitCode!=0);
        completion=new WheelCompletion();completion.Start();completion.Complete(WheelOutcome.Cancelled);Check("cancelled GUI close returns nonzero",completion.ExitCode==4);
        completion=new WheelCompletion();completion.Start();completion.TryVerify(delegate{});Check("only verified GUI close reports success",completion.ExitCode==0);
        Check("exact offline guest admitted",WheelGuard.Allowed(Facts()));
        Check("null rejected",!WheelGuard.Allowed(null));
        var f=Facts();f.UUID="00000000-0000-0000-0000-000000000000";Check("wrong UUID",!WheelGuard.Allowed(f));
        f=Facts();f.UUID="bad";Check("malformed UUID",!WheelGuard.Allowed(f));
        f=Facts();f.Model="Desktop";Check("host model",!WheelGuard.Allowed(f));
        f=Facts();f.Manufacturer="Unknown";Check("unknown manufacturer",!WheelGuard.Allowed(f));
        f=Facts();f.Manufacturer="Oracle Corporation";Check("Oracle VirtualBox",WheelGuard.Allowed(f));
        f=Facts();f.SID="S-1-5-21-2133766663-4066672948-2456486318-1005";Check("host worker SID",!WheelGuard.Allowed(f));
        f=Facts();f.SID="S-1-5-21-2133766663-4066672948-2456486318-1001";Check("host operator SID",!WheelGuard.Allowed(f));
        f=Facts();f.SID=null;Check("missing SID",!WheelGuard.Allowed(f));
        f=Facts();f.Is64Bit=false;Check("x86 rejected",!WheelGuard.Allowed(f));
        f=Facts();f.MediumIntegrity=false;Check("non-medium rejected",!WheelGuard.Allowed(f));
        f=Facts();f.EnabledNics=1;Check("enabled NIC rejected",!WheelGuard.Allowed(f));
        f=Facts();f.EnabledNics=-1;Check("unobserved NICs rejected",!WheelGuard.Allowed(f));
        string fixture=Path.GetFullPath(args[0]);var budget=new WheelBudget(20);
        var r=WheelProcess.Run(fixture,new string[]{"normal","a b\\","a\"b"},3,512,budget,null);
        Check("actual stdout stderr exit",r.State=="EXITED"&&r.ExitCode==7&&r.Stdout=="a b\\|a\"b"&&r.Stderr=="fixture error");
        var normalResult=r;Check("actual normal result facts retained",r.ExitCodeKnown&&r.OutputBytes==Encoding.UTF8.GetByteCount(r.Stdout+r.Stderr)&&r.OutputLimit==512&&r.DeadlineSeconds==3&&r.ElapsedMilliseconds>=0);
        r=WheelProcess.Run(fixture,new string[]{"overflow"},3,128,budget,null);Check("combined bytes bounded",r.State=="OUTPUT_LIMIT"&&Encoding.UTF8.GetByteCount(r.Stdout)+Encoding.UTF8.GetByteCount(r.Stderr)<=128);
        var overflowResult=r;Check("actual output cap fact retained",r.OutputCapped&&r.OutputBytes<=r.OutputLimit);
        var sw=Stopwatch.StartNew();r=WheelProcess.Run(fixture,new string[]{"sleep"},1,128,budget,null);Check("actual monotonic deadline",r.State=="TIMEOUT"&&sw.Elapsed.TotalSeconds<5);
        var timeoutResult=r;Check("actual timeout fact retained",r.TimedOut&&r.DeadlineSeconds==1&&r.ElapsedMilliseconds>=900);
        r=WheelProcess.Run(fixture,new string[]{"sleep"},3,128,budget,delegate{return true;});Check("cancel before start",r.State=="CANCELLED"&&r.PID==0);
        var exhausted=new WheelBudget(1);System.Threading.Thread.Sleep(1050);r=WheelProcess.Run(fixture,new string[]{"normal","x","y"},3,128,exhausted,null);Check("overall monotonic budget refuses new process",r.State=="OVERALL_TIMEOUT"&&r.PID==0);
        Check("newline args rejected",Throws(delegate{WheelProcess.Run(fixture,new string[]{"bad\nargument"},3,128,budget,null);}));
        Check("relative executable rejected",Throws(delegate{WheelProcess.Run("fixture.exe",new string[]{"normal"},3,128,budget,null);}));
        string root=Path.GetFullPath(args[1]);Directory.CreateDirectory(root);
        string state=Path.Combine(root,"state");Directory.CreateDirectory(state);
        using(var lease=WheelAttempt.Begin(state,"fixed target")){
            Check("exclusive intent retained",File.Exists(Path.Combine(state,"attempt.intent.json")));
            Check("real exclusive lease",Throws(delegate{using(var blocked=WheelAttempt.Begin(state,"fixed target")){};}));
            Check("kernel lease denies competing filesystem handle",Throws(delegate{using(var blocked=new FileStream(Path.Combine(state,"attempt.lease"),FileMode.Open,FileAccess.ReadWrite,FileShare.None)){};}));
            lease.RecordStep(WheelStep.RUNTIME_BEFORE,normalResult);lease.RecordStep(WheelStep.PACKAGES_BEFORE,overflowResult);lease.RecordStep(WheelStep.PIP_PREFLIGHT,timeoutResult);
            var parser=new JavaScriptSerializer();var native=(Dictionary<string,object>)parser.DeserializeObject(File.ReadAllText(Path.Combine(state,"step-01-RUNTIME_BEFORE.json")));
            Check("durable exact stdout stderr numeric exit",(string)native["stdout"]==normalResult.Stdout&&(string)native["stderr"]==normalResult.Stderr&&(int)native["exit_code"]==7&&(bool)native["exit_code_known"]);
            Check("durable bounded local-only evidence",(int)native["captured_output_bytes"]==normalResult.OutputBytes&&(int)native["output_limit_bytes"]==512&&(bool)native["raw_local_only"]&&!(bool)native["descendant_containment_established"]);
            native=(Dictionary<string,object>)parser.DeserializeObject(File.ReadAllText(Path.Combine(state,"step-02-PACKAGES_BEFORE.json")));Check("durable overflow fact",(bool)native["output_limit_reached"]&&(string)native["state"]=="OUTPUT_LIMIT");
            native=(Dictionary<string,object>)parser.DeserializeObject(File.ReadAllText(Path.Combine(state,"step-03-PIP_PREFLIGHT.json")));Check("durable timeout and deadline facts",(bool)native["timed_out"]&&(int)native["deadline_seconds"]==1&&(string)native["state"]=="TIMEOUT");
            Check("overbound evidence rejected before file creation",Throws(delegate{lease.RecordStep(WheelStep.PIP_INSTALL,new WheelProcessResult{State="EXITED",Stdout=new string('x',129),OutputBytes=129,OutputLimit=128,DeadlineSeconds=1});})&&!File.Exists(Path.Combine(state,"step-04-PIP_INSTALL.json")));
            lease.Complete("VERIFIED", "FIXED_RESULT");
        }
        Check("flushed result retained",File.ReadAllText(Path.Combine(state,"attempt.result.json")).Contains("FIXED_RESULT"));
        Check("released lease still prohibits replay",Throws(delegate{using(var blocked=WheelAttempt.Begin(state,"fixed target")){};}));
        string corrupt=Path.Combine(root,"corrupt");Directory.CreateDirectory(corrupt);File.WriteAllText(Path.Combine(corrupt,"attempt.intent.json"),"broken");
        Check("corrupt intent prohibits replay",Throws(delegate{using(var blocked=WheelAttempt.Begin(corrupt,"fixed target")){};}));
        string cancelledState=Path.Combine(root,"cancelBeforeCommit");Directory.CreateDirectory(cancelledState);
        using(var attempt=WheelAttempt.Begin(cancelledState,"FIXED_TARGET")){
            completion=new WheelCompletion();completion.Start();Check("cancellation before commit accepted",completion.RequestCancel()&&completion.IsCancellationRequested);
            Check("shared production success commit refuses accepted cancellation",Throws(delegate{WheelInstall.CommitVerified(completion,attempt,"FIXED_VERIFIED_REASON");})&&completion.ExitCode!=0&&!File.Exists(Path.Combine(cancelledState,"attempt.result.json")));
            attempt.Complete("QUARANTINED_NO_RETRY","CANCELLED_BEFORE_VERIFIED_COMMIT");completion.Complete(WheelOutcome.Cancelled);
            Check("accepted cancel persists quarantine and nonzero",completion.ExitCode==4&&File.ReadAllText(Path.Combine(cancelledState,"attempt.result.json")).Contains("QUARANTINED_NO_RETRY"));
        }
        string completedState=Path.Combine(root,"commitBeforeCancel");Directory.CreateDirectory(completedState);
        using(var attempt=WheelAttempt.Begin(completedState,"FIXED_TARGET")){
            completion=new WheelCompletion();completion.Start();WheelInstall.CommitVerified(completion,attempt,"FIXED_VERIFIED_REASON");
            Check("durable commit completes before later close request",completion.ExitCode==0&&completion.IsFinished&&!completion.RequestCancel()&&!completion.IsCancellationRequested&&File.ReadAllText(Path.Combine(completedState,"attempt.result.json")).Contains("VERIFIED"));
        }
        string overlappedState=Path.Combine(root,"overlappedCommit");Directory.CreateDirectory(overlappedState);
        using(var attempt=WheelAttempt.Begin(overlappedState,"FIXED_TARGET"))
        using(var entered=new System.Threading.ManualResetEvent(false))
        using(var release=new System.Threading.ManualResetEvent(false))
        using(var cancelStarted=new System.Threading.ManualResetEvent(false))
        using(var cancelFinished=new System.Threading.ManualResetEvent(false)){
            var shared=new WheelCompletion();shared.Start();bool committed=false,accepted=true;Exception commitError=null;
            var writer=new System.Threading.Thread(delegate(){try{committed=shared.TryVerify(delegate{entered.Set();if(!release.WaitOne(3000))throw new IOException("TEST_RELEASE_TIMEOUT");attempt.Complete("VERIFIED","ATOMIC_OVERLAP_TEST");});}catch(Exception error){commitError=error;}});writer.IsBackground=true;writer.Start();
            var closer=new System.Threading.Thread(delegate(){cancelStarted.Set();accepted=shared.RequestCancel();cancelFinished.Set();});closer.IsBackground=true;
            try{Check("commit entered shared completion boundary",entered.WaitOne(2000));closer.Start();Check("close request reached shared boundary",cancelStarted.WaitOne(2000));Check("overlapping close cannot interrupt durable commit",!cancelFinished.WaitOne(50));}
            finally{release.Set();writer.Join(2000);if(closer.ThreadState!=System.Threading.ThreadState.Unstarted)closer.Join(2000);}
            Check("overlapping commit yields durable VERIFIED without accepted cancel",commitError==null&&committed&&!accepted&&shared.ExitCode==0&&File.ReadAllText(Path.Combine(overlappedState,"attempt.result.json")).Contains("ATOMIC_OVERLAP_TEST"));
        }
        string payload=Path.Combine(root,"payload.bin");File.WriteAllBytes(payload,new byte[]{1,2,3,4});
        string sha="9F64A747E1B97F131FABB6B447296C9B6F0201E79FB3C5356E6C77E89B6A806A";
        using(var held=WheelMedia.OpenPinned(payload,4,sha)){
            Check("actual size hash pin",held.Length==4);
            Check("held media forbids writes",Throws(delegate{using(var writer=new FileStream(payload,FileMode.Open,FileAccess.Write,FileShare.ReadWrite)){};}));
        }
        Check("wrong size rejected",Throws(delegate{using(var held=WheelMedia.OpenPinned(payload,5,sha)){};}));
        Check("wrong hash rejected",Throws(delegate{using(var held=WheelMedia.OpenPinned(payload,4,new string('0',64))){};}));
        Check("reparse attribute rejected",Throws(delegate{WheelPaths.CheckAttributes(FileAttributes.ReparsePoint|FileAttributes.Directory);}));
        Check("actual filesystem junction rejected",Throws(delegate{WheelPaths.NoReparse(Path.Combine(root,"reparseLink"));}));
        Check("actual ordinary path accepted",!Throws(delegate{WheelPaths.NoReparse(Path.Combine(root,"reparseTarget"));}));
        var sizes=new Dictionary<string,long>{{WheelMedia.Helper,4096},{WheelMedia.Psutil,137737},{WheelMedia.Pywin,6914298},{"README.txt",123}};
        var hashes=new Dictionary<string,string>{{WheelMedia.Helper,new string('1',64)},{WheelMedia.Psutil,WheelMedia.PsutilSHA},{WheelMedia.Pywin,WheelMedia.PywinSHA},{"README.txt",new string('2',64)}};
        string manifest="{\"schema\":1,\"volume_label\":\"AIBS_WHEELS_V1\",\"files\":[";bool first=true;
        foreach(string name in new string[]{WheelMedia.Helper,WheelMedia.Psutil,WheelMedia.Pywin,"README.txt"}){if(!first)manifest+=",";first=false;manifest+="{\"name\":\""+name+"\",\"length\":"+sizes[name]+",\"sha256\":\""+hashes[name]+"\"}";}manifest+="]}";
        Check("strict fixed manifest accepted",!Throws(delegate{WheelMedia.ValidateManifest(manifest,sizes,hashes);}));
        Check("manifest label rejected",Throws(delegate{WheelMedia.ValidateManifest(manifest.Replace("AIBS_WHEELS_V1","OTHER"),sizes,hashes);}));
        Check("manifest path rejected",Throws(delegate{WheelMedia.ValidateManifest(manifest.Replace("README.txt","..\\\\README.txt"),sizes,hashes);}));
        Check("manifest wheel hash rejected",Throws(delegate{WheelMedia.ValidateManifest(manifest.Replace(WheelMedia.PsutilSHA,new string('0',64)),sizes,hashes);}));
        Check("manifest arbitrary command rejected",Throws(delegate{WheelMedia.ValidateManifest(manifest.Replace("\"schema\":1","\"schema\":1,\"command\":\"anything\""),sizes,hashes);}));
        Check("manifest duplicate key rejected",Throws(delegate{WheelMedia.ValidateManifest(manifest.Replace("\"schema\":1","\"schema\":1,\"schema\":1"),sizes,hashes);}));
        string target=@"C:\Trusted Profile\Programs\Python\Python313\python.exe",prefix=Path.GetDirectoryName(target);
        string runtime="AIBS_RUNTIME|3.13.17|64|"+target+"|"+prefix+"|"+prefix+"|"+Path.Combine(prefix,@"Lib\site-packages")+"|"+Path.Combine(prefix,@"Lib\site-packages")+"|False|nt\r\n";
        Check("exact runtime response accepted",!Throws(delegate{WheelInstall.ValidateRuntime(new WheelProcessResult{State="EXITED",ExitCode=0,Stdout=runtime},target);}));
        Check("other Python version refused",Throws(delegate{WheelInstall.ValidateRuntime(new WheelProcessResult{State="EXITED",ExitCode=0,Stdout=runtime.Replace("3.13.17","3.13.16")},target);}));
        Check("other Python prefix refused",Throws(delegate{WheelInstall.ValidateRuntime(new WheelProcessResult{State="EXITED",ExitCode=0,Stdout=runtime.Replace(prefix+"|"+prefix,prefix+"|C:\\OtherPython")},target);}));
        Check("runtime uncertainty refused",Throws(delegate{WheelInstall.ValidateRuntime(new WheelProcessResult{State="TIMEOUT",ExitCode=0,Stdout=runtime},target);}));
        var pipArgs=WheelInstall.PipArguments();Check("fixed no-network pip arguments",String.Join("|",pipArgs)=="-I|-B|-m|pip|--isolated|--disable-pip-version-check|install|--no-index|--no-deps|--no-cache-dir|--no-compile|D:\\"+WheelMedia.Psutil+"|D:\\"+WheelMedia.Pywin);
        Check("pip preflight contains os.devnull and no configuration dump",WheelInstall.PipCode.Contains("os.environ.get('PIP_CONFIG_FILE')==os.devnull")&&WheelInstall.PipCode.Contains("not list(c.items())")&&!WheelInstall.PipCode.Contains("print(c"));
        Console.WriteLine("RESULT "+passed+" trusted infrastructure checks passed; no pip, Python, Node, installer, or project runtime executed.");return 0;
    }
}
