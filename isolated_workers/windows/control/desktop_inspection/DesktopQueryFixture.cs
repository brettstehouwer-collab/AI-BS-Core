using System;
using System.IO;
using System.Text;
using System.Threading;
#if !DESKTOP_QUERY_FIXTURE
using AIBS.DesktopInspection;
#endif
#if DESKTOP_QUERY_FIXTURE
internal static class DesktopQueryFixture {
    static void Out(string value){var b=new UTF8Encoding(false).GetBytes(value);var stream=Console.OpenStandardOutput();stream.Write(b,0,b.Length);stream.Flush();}
    static void Error(string value){var b=new UTF8Encoding(false).GetBytes(value);var stream=Console.OpenStandardError();stream.Write(b,0,b.Length);stream.Flush();}
    static int Main(string[] args){
        if(args.Length==3&&args[0]=="normal"){Out(args[1]+"|"+args[2]+"|"+Environment.GetEnvironmentVariable("VBOX_USER_HOME"));Error("fixture error");return 7;}
        if(args.Length==1&&args[0]=="stdout-cap"){Out(new string('x',1049600));return 0;}
        if(args.Length==1&&args[0]=="stderr-cap"){Error(new string('y',66560));return 0;}
        if(args.Length==1&&args[0]=="combined-cap"){Out(new string('x',100));Error(new string('y',60));return 0;}
        if(args.Length==1&&args[0]=="sleep"){Thread.Sleep(5000);return 0;}
        return 64;
    }
}
#else
internal static class DesktopQueryTests {
    static int passed;
    static void Check(string name,bool ok){if(!ok)throw new Exception("FAIL "+name);passed++;Console.WriteLine("PASS "+name);}
    static bool Throws(Action action){try{action();return false;}catch{return true;}}
    static int Main(string[] args){try{return Run(args);}catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}}
    static int Run(string[] args){
        string parent=Environment.GetEnvironmentVariable("VBOX_USER_HOME");
        string fixture=Path.GetFullPath(args[0]);
        var result=DesktopQuery.RunBounded(fixture,new string[]{"normal","a b\\","a\"b"},@"C:\Fixed Fixture Registry",null,3,512,128);
        Check("actual bounded fixture stdout stderr exit",result.State=="EXITED"&&result.ExitCode==7&&result.Stdout=="a b\\|a\"b|C:\\Fixed Fixture Registry"&&result.Stderr=="fixture error");
        DateTime creation;Check("actual client identity and numeric-exit facts",result.ExitCodeKnown&&result.PID>0&&DateTime.TryParse(result.CreationUtc,out creation)&&result.ElapsedMilliseconds>=0);
        Check("actual byte counts and advertised limits",result.OutputBytes==Encoding.UTF8.GetByteCount(result.Stdout+result.Stderr)&&result.ErrorBytes==Encoding.UTF8.GetByteCount(result.Stderr)&&result.CombinedLimitBytes==512&&result.StderrLimitBytes==128);
        Check("no descendant termination claim",!result.DescendantTerminationEstablished);
        Check("child VBOX_USER_HOME does not mutate parent",Environment.GetEnvironmentVariable("VBOX_USER_HOME")==parent);
        result=DesktopQuery.RunBounded(fixture,new string[]{"stdout-cap"},@"C:\Fixed Fixture Registry",null,3,1048576,65536);
        Check("actual 1MiB combined cap enforced during read",result.State=="OUTPUT_LIMIT"&&result.OutputCapped&&result.CombinedLimitReached&&result.OutputBytes<=1048576&&result.Stdout.Length+result.Stderr.Length<=1048576);
        result=DesktopQuery.RunBounded(fixture,new string[]{"stderr-cap"},@"C:\Fixed Fixture Registry",null,3,1048576,65536);
        Check("actual 64KiB stderr cap enforced during read",result.State=="OUTPUT_LIMIT"&&result.OutputCapped&&result.StderrLimitReached&&result.ErrorBytes<=65536&&result.Stderr.Length<=65536);
        result=DesktopQuery.RunBounded(fixture,new string[]{"combined-cap"},@"C:\Fixed Fixture Registry",null,3,128,64);
        Check("combined streams share one finite budget",result.State=="OUTPUT_LIMIT"&&result.OutputCapped&&result.CombinedLimitReached&&!result.StderrLimitReached&&result.OutputBytes<=128);
        var clock=System.Diagnostics.Stopwatch.StartNew();result=DesktopQuery.RunBounded(fixture,new string[]{"sleep"},@"C:\Fixed Fixture Registry",null,1,128,64);
        Check("actual monotonic deadline terminates only client",result.State=="TIMEOUT"&&result.TimedOut&&result.ClientKillRequested&&result.PID>0&&result.ElapsedMilliseconds>=900&&clock.Elapsed.TotalSeconds<3&&!result.DescendantTerminationEstablished);
        result=DesktopQuery.RunBounded(fixture,new string[]{"sleep"},@"C:\Fixed Fixture Registry",delegate{return true;},3,128,64);
        Check("cancel before start has no client",result.State=="CANCELLED"&&result.Cancelled&&result.PID==0&&!result.ExitCodeKnown);
        int calls=0;result=DesktopQuery.RunBounded(fixture,new string[]{"sleep"},@"C:\Fixed Fixture Registry",delegate{return ++calls>=4;},3,128,64);
        Check("cancel while running preserves client facts",result.State=="CANCELLED"&&result.Cancelled&&result.PID>0&&result.ClientKillRequested&&!result.DescendantTerminationEstablished);
        result=DesktopQuery.RunBounded(fixture,new string[]{"sleep"},@"C:\Fixed Fixture Registry",delegate{throw new InvalidOperationException();},3,128,64);
        Check("uncertain cancellation callback cannot launch",result.State=="PROCESS_UNCERTAIN"&&result.PID==0&&!result.ExitCodeKnown);
        Check("arbitrary operation refused before native dispatch",DesktopQuery.InvokeFixed("startvm",DesktopQuery.RegistryRoot,null).State=="REFUSED"&&DesktopQuery.InvokeFixed("startvm",DesktopQuery.RegistryRoot,null).PID==0);
        Check("registry override refused before native dispatch",DesktopQuery.InvokeFixed("VMInfo",DesktopQuery.RegistryRoot+"\\..",null).Reason=="EXACT_FIXED_REGISTRY_REQUIRED");
        Check("registry alias spelling refused",DesktopQuery.InvokeFixed("DiskInfo",DesktopQuery.RegistryRoot.ToLowerInvariant(),null).State=="REFUSED");
        Check("fixed VM arguments exact",String.Join("|",DesktopQuery.FixedArguments("VMInfo"))=="showvminfo|6c5a53da-ab80-4ecb-8be6-4059266f736e|--machinereadable");
        Check("fixed disk human-output arguments exact",String.Join("|",DesktopQuery.FixedArguments("DiskInfo"))=="showmediuminfo|disk|9e1efe57-9da5-49f8-acea-763429616968");
        Check("arbitrary operation cannot acquire arguments",Throws(delegate{DesktopQuery.FixedArguments("snapshot");}));
        Check("exact standard medium worker allowed",DesktopQuery.WorkerAllowed(DesktopQuery.WorkerSID,false,true,true));
        Check("operator account rejected",!DesktopQuery.WorkerAllowed("S-1-5-21-2133766663-4066672948-2456486318-1001",false,true,true));
        Check("administrator rejected",!DesktopQuery.WorkerAllowed(DesktopQuery.WorkerSID,true,true,true));
        Check("non-medium rejected",!DesktopQuery.WorkerAllowed(DesktopQuery.WorkerSID,false,false,true));
        Check("x86 rejected",!DesktopQuery.WorkerAllowed(DesktopQuery.WorkerSID,false,true,false));
        Check("unobserved worker rejected",!DesktopQuery.WorkerAllowed(null,false,true,true));
        Check("generic reader is internal only",typeof(DesktopQuery).GetMethod("RunBounded",System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Static)==null);
        Check("relative executable rejected",Throws(delegate{DesktopQuery.RunBounded("fixture.exe",new string[]{"sleep"},"fixed",null,1,128,64);}));
        Check("newline argument rejected",Throws(delegate{DesktopQuery.RunBounded(fixture,new string[]{"bad\nargument"},"fixed",null,1,128,64);}));
        Check("longer deadline rejected",Throws(delegate{DesktopQuery.RunBounded(fixture,new string[]{"sleep"},"fixed",null,21,128,64);}));
        Check("larger combined cap rejected",Throws(delegate{DesktopQuery.RunBounded(fixture,new string[]{"sleep"},"fixed",null,1,1048577,64);}));
        Check("larger stderr cap rejected",Throws(delegate{DesktopQuery.RunBounded(fixture,new string[]{"sleep"},"fixed",null,1,1048576,65537);}));
        Check("no parent VBOX_USER_HOME mutation after all paths",Environment.GetEnvironmentVariable("VBOX_USER_HOME")==parent);
        Console.WriteLine("RESULT "+passed+" trusted fixture checks; no VBoxManage or guest command executed.");return 0;
    }
}
#endif
