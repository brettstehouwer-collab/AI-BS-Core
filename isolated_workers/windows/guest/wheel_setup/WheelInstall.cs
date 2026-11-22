using System;
using System.IO;
using System.Text.RegularExpressions;

internal static class WheelInstall {
    internal static void CommitVerified(WheelCompletion completion,WheelAttempt attempt,string reason){
        if(!completion.TryVerify(delegate{attempt.Complete("VERIFIED",reason);}))throw new IOException("CANCELLED_BEFORE_VERIFIED_COMMIT");
    }
    // Fixed Python snippets only. No manifest, UI, environment, or caller supplies code.
    internal const string RuntimeCode="import os,sys,struct,sysconfig,site; print('AIBS_RUNTIME|'+'.'.join(map(str,sys.version_info[:3]))+'|'+str(struct.calcsize('P')*8)+'|'+sys.executable+'|'+sys.prefix+'|'+sys.base_prefix+'|'+sysconfig.get_path('purelib')+'|'+sysconfig.get_path('platlib')+'|'+str(site.ENABLE_USER_SITE)+'|'+os.name)";
    internal const string PackagesCode="import importlib,importlib.metadata,os,sysconfig\nroot=os.path.normcase(os.path.realpath(sysconfig.get_path('platlib')))\nfor module,distribution,wanted in [('psutil','psutil','7.2.2'),('win32api','pywin32','312')]:\n try:\n  loaded=importlib.import_module(module); actual=importlib.metadata.version(distribution); source=os.path.normcase(os.path.realpath(loaded.__file__)); inside=os.path.commonpath([root,source])==root\n  print('AIBS_PACKAGE|'+distribution+'|'+('MATCH' if actual==wanted and inside else 'REMEDY_REQUIRED'))\n except (ModuleNotFoundError,importlib.metadata.PackageNotFoundError):\n  print('AIBS_PACKAGE|'+distribution+'|REMEDY_REQUIRED')";
    internal const string PipCode="import os,pip\nfrom pip._internal.configuration import Configuration\nc=Configuration(isolated=True); c.load()\nprint('AIBS_PIP_READY' if os.name=='nt' and os.devnull=='nul' and os.environ.get('PIP_CONFIG_FILE')==os.devnull and not list(c.items()) else 'AIBS_PIP_CONFIG_REFUSED')";
    static WheelProcessResult Probe(string python,string code,WheelBudget budget,Func<bool> cancel,WheelAttempt attempt,WheelStep step){
        // Encode fixed script as one physical argument: the quoting layer rejects CR/LF.
        string encoded=Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(code));
        var result=WheelProcess.Run(python,new string[]{"-I","-B","-c","exec(__import__('base64').b64decode('"+encoded+"'))"},10,4096,budget,cancel);
        attempt.RecordStep(step,result);return result;
    }
    static void RequireExited(WheelProcessResult r,string reason){if(r.State!="EXITED"||r.ExitCode!=0)throw new IOException(reason+"_"+r.State);}
    internal static void ValidateRuntime(WheelProcessResult r,string python){
        RequireExited(r,"RUNTIME_PROBE");if(r.Stderr.Length!=0)throw new IOException("RUNTIME_STDERR");string[] fields=r.Stdout.TrimEnd('\r','\n').Split('|');string prefix=Path.GetDirectoryName(python);
        if(fields.Length!=10||fields[0]!="AIBS_RUNTIME"||fields[1]!="3.13.17"||fields[2]!="64"||!WheelPaths.Equal(fields[3],python)||!WheelPaths.Equal(fields[4],prefix)||!WheelPaths.Equal(fields[5],prefix)||!WheelPaths.Equal(fields[6],Path.Combine(prefix,@"Lib\site-packages"))||!WheelPaths.Equal(fields[7],Path.Combine(prefix,@"Lib\site-packages"))||fields[8]!="False"||fields[9]!="nt")throw new IOException("EXACT_RUNTIME_PREFIX_VERSION_REQUIRED");
    }
    static bool PackagesMatch(WheelProcessResult r){
        RequireExited(r,"PACKAGE_PROBE");if(r.Stderr.Length!=0)throw new IOException("PACKAGE_STDERR");string[] lines=r.Stdout.TrimEnd('\r','\n').Replace("\r\n","\n").Split('\n');
        if(lines.Length!=2||!Regex.IsMatch(lines[0],@"^AIBS_PACKAGE\|psutil\|(MATCH|REMEDY_REQUIRED)$")||!Regex.IsMatch(lines[1],@"^AIBS_PACKAGE\|pywin32\|(MATCH|REMEDY_REQUIRED)$"))throw new IOException("PACKAGE_RESULT_UNCERTAIN");
        return lines[0].EndsWith("|MATCH",StringComparison.Ordinal)&&lines[1].EndsWith("|MATCH",StringComparison.Ordinal);
    }
    internal static string[] PipArguments(){return new string[]{"-I","-B","-m","pip","--isolated","--disable-pip-version-check","install","--no-index","--no-deps","--no-cache-dir","--no-compile",Path.Combine(WheelMedia.Root,WheelMedia.Psutil),Path.Combine(WheelMedia.Root,WheelMedia.Pywin)};}
    internal static WheelOutcome Execute(Action<string> log,WheelCompletion completion,string currentExe){
        Func<bool> cancel=delegate{return completion.IsCancellationRequested;};
        var budget=new WheelBudget(180);WheelGuard.Require();string python=WheelPaths.Python();WheelPaths.NoReparse(python);
        using(var media=WheelMedia.Open(currentExe))
        using(var interpreter=new FileStream(python,FileMode.Open,FileAccess.Read,FileShare.Read)){
            WheelPaths.NoReparse(python);WheelPaths.EnsureDirectory(WheelPaths.State());
            using(var attempt=WheelAttempt.Begin(WheelPaths.State(),python)){
                bool resultWritten=false;
                try{
                    log("Pinned D: CD-ROM media verified; all five files held read-only. Attempt intent flushed; replay disabled.");
                    ValidateRuntime(Probe(python,RuntimeCode,budget,cancel,attempt,WheelStep.RUNTIME_BEFORE),python);log("Exact Python 3.13.17 x64, executable and installation prefix verified.");
                    bool matching=PackagesMatch(Probe(python,PackagesCode,budget,cancel,attempt,WheelStep.PACKAGES_BEFORE));
                    if(matching){CommitVerified(completion,attempt,"ALREADY_MATCHING_NO_PIP_NEEDED");resultWritten=true;log("VERIFIED: psutil 7.2.2 and pywin32 312 imports already match in this interpreter. No pip mutation needed.");return WheelOutcome.Verified;}
                    log("At least one approved package needs remedy in this exact interpreter.");
                    var pip=Probe(python,PipCode,budget,cancel,attempt,WheelStep.PIP_PREFLIGHT);RequireExited(pip,"PIP_PREFLIGHT");
                    if(pip.Stderr.Length!=0||pip.Stdout.TrimEnd('\r','\n')!="AIBS_PIP_READY")throw new IOException("PIP_MISSING_OR_CONFIG_NOT_CLEAR");
                    log("pip available; configuration disabled and no effective config values. Starting the two fixed offline wheel paths once.");
                    WheelGuard.Require();if(cancel())throw new IOException("CANCELLED_BEFORE_PIP");
                    var installed=WheelProcess.Run(python,PipArguments(),120,16384,budget,cancel);
                    attempt.RecordStep(WheelStep.PIP_INSTALL,installed);
                    log("pip result: "+installed.State+"; exit="+installed.ExitCode);
                    if(installed.Stdout.Length>0)log(installed.Stdout.TrimEnd());if(installed.Stderr.Length>0)log(installed.Stderr.TrimEnd());
                    RequireExited(installed,"PIP_INSTALL");
                    ValidateRuntime(Probe(python,RuntimeCode,budget,cancel,attempt,WheelStep.RUNTIME_AFTER),python);
                    if(!PackagesMatch(Probe(python,PackagesCode,budget,cancel,attempt,WheelStep.PACKAGES_AFTER)))throw new IOException("POST_INSTALL_IMPORT_VERSION_MISMATCH");
                    CommitVerified(completion,attempt,"BOTH_APPROVED_IMPORTS_AND_VERSIONS_MATCH");resultWritten=true;
                    log("VERIFIED: psutil 7.2.2 and pywin32 312 imported from this Python installation. Task authority remains disabled.");
                    return WheelOutcome.Verified;
                }catch(Exception error){
                    string reason=error is IOException?error.Message:"ATTEMPT_UNCERTAIN";
                    if(!Regex.IsMatch(reason,@"^[A-Z0-9_ .-]{1,160}$"))reason="ATTEMPT_UNCERTAIN";
                    if(!resultWritten){try{attempt.Complete("QUARANTINED_NO_RETRY",reason);}catch{}}
                    log("QUARANTINED / NO RETRY: "+reason+". Retained intent blocks another attempt, even if the result could not be written.");
                    log("No bootstrap, alternate interpreter, network or host fallback exists. Client termination does not establish descendant containment.");
                    return reason.IndexOf("CANCELLED",StringComparison.Ordinal)>=0?WheelOutcome.Cancelled:WheelOutcome.Failed;
                }
            }
        }
    }
}
