using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Management;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Threading;
using System.Collections;
using System.Collections.Generic;
using System.Web.Script.Serialization;

internal sealed class WheelGuestFacts {
    internal string UUID,Manufacturer,Model,SID;
    internal bool Is64Bit,MediumIntegrity;
    internal int EnabledNics=-1;
}
internal static class WheelGuard {
    internal const string HostDomain="S-1-5-21-2133766663-4066672948-2456486318";
    internal static bool HostSID(string sid){return sid==HostDomain||(sid!=null&&sid.StartsWith(HostDomain+"-",StringComparison.Ordinal));}
    internal static bool Allowed(WheelGuestFacts f){
        Guid id;
        return f!=null&&Guid.TryParse(f.UUID,out id)&&id==new Guid("6c5a53da-ab80-4ecb-8be6-4059266f736e")&&
            f.Model=="VirtualBox"&&(f.Manufacturer=="innotek GmbH"||f.Manufacturer=="Oracle Corporation")&&
            f.Is64Bit&&f.MediumIntegrity&&f.EnabledNics==0&&f.SID!=null&&
            Regex.IsMatch(f.SID,@"^S-1-5-21-\d+-\d+-\d+-\d+$")&&!HostSID(f.SID);
    }
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetTokenInformation(IntPtr token,int info,IntPtr buffer,int length,out int required);
    [DllImport("advapi32.dll")] static extern IntPtr GetSidSubAuthorityCount(IntPtr sid);
    [DllImport("advapi32.dll")] static extern IntPtr GetSidSubAuthority(IntPtr sid,uint index);
    static bool Medium(WindowsIdentity identity){
        int length;IntPtr elevation=Marshal.AllocHGlobal(4);
        try{if(!GetTokenInformation(identity.Token,20,elevation,4,out length)||Marshal.ReadInt32(elevation)!=0)return false;}
        finally{Marshal.FreeHGlobal(elevation);}
        GetTokenInformation(identity.Token,25,IntPtr.Zero,0,out length);
        if(length< IntPtr.Size||length>1024)return false;
        IntPtr buffer=Marshal.AllocHGlobal(length);
        try{
            if(!GetTokenInformation(identity.Token,25,buffer,length,out length))return false;
            IntPtr sid=Marshal.ReadIntPtr(buffer);byte count=Marshal.ReadByte(GetSidSubAuthorityCount(sid));
            return count>0&&Marshal.ReadInt32(GetSidSubAuthority(sid,(uint)(count-1)))==8192;
        }finally{Marshal.FreeHGlobal(buffer);}
    }
    static ManagementObjectSearcher Search(string query){var s=new ManagementObjectSearcher(query);s.Options.Timeout=TimeSpan.FromSeconds(5);return s;}
    internal static WheelGuestFacts ReadFacts(){
        var f=new WheelGuestFacts();f.Is64Bit=Environment.Is64BitProcess&&Environment.Is64BitOperatingSystem;
        using(var identity=WindowsIdentity.GetCurrent()){
            if(identity.User==null)return f;f.SID=identity.User.Value;
            // Refuse real host accounts before WMI, GUI, runtime probes, or application writes.
            if(HostSID(f.SID))return f;f.MediumIntegrity=Medium(identity);
        }
        if(!f.Is64Bit||!f.MediumIntegrity)return f;
        int count=0;
        using(var search=Search("SELECT UUID FROM Win32_ComputerSystemProduct"))
        using(var rows=search.Get())foreach(ManagementObject row in rows)using(row){f.UUID=Convert.ToString(row["UUID"]);count++;}
        if(count!=1)throw new InvalidOperationException("AMBIGUOUS_IDENTITY");count=0;
        using(var search=Search("SELECT Manufacturer,Model FROM Win32_ComputerSystem"))
        using(var rows=search.Get())foreach(ManagementObject row in rows)using(row){f.Manufacturer=Convert.ToString(row["Manufacturer"]);f.Model=Convert.ToString(row["Model"]);count++;}
        if(count!=1)throw new InvalidOperationException("AMBIGUOUS_HARDWARE");
        count=0;
        using(var search=Search("SELECT DeviceID FROM Win32_NetworkAdapter WHERE NetEnabled=TRUE"))
        using(var rows=search.Get())foreach(ManagementObject row in rows)using(row){count++;}
        f.EnabledNics=count;return f;
    }
    internal static void Require(){if(!Allowed(ReadFacts()))throw new InvalidOperationException("GUEST_IDENTITY_OR_OFFLINE_GUARD_FAILED");}
}
internal static class WheelPaths {
    internal static string LocalRoot(){string root=Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);if(String.IsNullOrEmpty(root)||!Path.IsPathRooted(root)||root.StartsWith(@"\\",StringComparison.Ordinal))throw new IOException("LOCAL_PROFILE_REQUIRED");return Path.GetFullPath(root);}
    internal static string Python(){return Path.Combine(LocalRoot(),@"Programs\Python\Python313\python.exe");}
    internal static string State(){return Path.Combine(LocalRoot(),@"AI-BS\OfflineWheelSetup\v1");}
    internal static void CheckAttributes(FileAttributes attributes){if((attributes&FileAttributes.ReparsePoint)!=0)throw new IOException("REPARSE_PATH_REFUSED");}
    internal static void NoReparse(string path){
        string full=Path.GetFullPath(path);if(!Path.IsPathRooted(full)||full.StartsWith(@"\\",StringComparison.Ordinal))throw new IOException("LOCAL_PATH_REQUIRED");
        for(string current=full;!String.IsNullOrEmpty(current);current=Path.GetDirectoryName(current)){
            if(File.Exists(current)||Directory.Exists(current))CheckAttributes(File.GetAttributes(current));
            else throw new IOException("EXPECTED_PATH_MISSING");
        }
    }
    internal static void EnsureDirectory(string path){
        string full=Path.GetFullPath(path);string parent=Path.GetDirectoryName(full);
        if(!Directory.Exists(full)){if(String.IsNullOrEmpty(parent))throw new IOException("PROFILE_PARENT_MISSING");EnsureDirectory(parent);Directory.CreateDirectory(full);}
        NoReparse(full);
    }
    internal static bool Equal(string a,string b){return String.Equals(Path.GetFullPath(a).TrimEnd('\\'),Path.GetFullPath(b).TrimEnd('\\'),StringComparison.OrdinalIgnoreCase);}
}
internal sealed class WheelBudget {
    readonly Stopwatch clock=Stopwatch.StartNew();readonly int seconds;
    internal WheelBudget(int value){if(value<1||value>180)throw new ArgumentException("BUDGET");seconds=value;}
    internal double Remaining {get{return seconds-clock.Elapsed.TotalSeconds;}}
}
internal enum WheelOutcome { Verified=0,Failed=1,Refused=2,Unverified=3,Cancelled=4 }
internal enum WheelStep { RUNTIME_BEFORE,PACKAGES_BEFORE,PIP_PREFLIGHT,PIP_INSTALL,RUNTIME_AFTER,PACKAGES_AFTER }
internal sealed class WheelCompletion {
    readonly object gate=new object();int outcome=(int)WheelOutcome.Unverified;bool started,finished,cancelled;
    internal int ExitCode {get{lock(gate)return outcome;}}
    internal bool IsFinished {get{lock(gate)return finished;}}
    internal bool Start(){lock(gate){if(started)return false;started=true;return true;}}
    internal bool IsCancellationRequested {get{lock(gate)return cancelled;}}
    internal bool RequestCancel(){lock(gate){if(!started||finished)return false;cancelled=true;return true;}}
    internal bool TryVerify(Action durableCommit){
        lock(gate){
            if(!started||finished||durableCommit==null)throw new InvalidOperationException("INVALID_VERIFIED_COMMIT");
            if(cancelled)return false;
            // This is the shared linearization boundary: accepted cancellation wins before
            // this lock, or the flushed durable commit completes before a later close request.
            durableCommit();outcome=(int)WheelOutcome.Verified;finished=true;return true;
        }
    }
    internal void Complete(WheelOutcome value){
        lock(gate){
            if(!started||finished||!Enum.IsDefined(typeof(WheelOutcome),value)||value==WheelOutcome.Unverified||value==WheelOutcome.Verified)throw new InvalidOperationException("INVALID_COMPLETION");
            outcome=(int)(cancelled?WheelOutcome.Cancelled:value);finished=true;
        }
    }
}
internal sealed class WheelProcessResult {internal string State="UNKNOWN",Stdout="",Stderr="";internal int ExitCode=-1,PID;internal bool ExitCodeKnown,TimedOut,OutputCapped,Cancelled;internal int OutputBytes,OutputLimit=128,DeadlineSeconds=1;internal long ElapsedMilliseconds;}
internal static class WheelProcess {
    internal static string Quote(string value){
        if(value==null||value.IndexOfAny(new char[]{'\0','\r','\n'})>=0)throw new ArgumentException("INVALID_FIXED_ARGUMENT");
        var b=new StringBuilder("\"");int slashes=0;
        foreach(char c in value){if(c=='\\'){slashes++;continue;}if(c=='\"'){b.Append('\\',slashes*2+1);b.Append(c);}else{b.Append('\\',slashes);b.Append(c);}slashes=0;}
        b.Append('\\',slashes*2);b.Append('"');return b.ToString();
    }
    internal static WheelProcessResult Run(string executable,string[] args,int seconds,int limit,WheelBudget budget,Func<bool> cancelled){
        if(seconds<1||seconds>120||limit<128||limit>16384||budget==null||!Path.IsPathRooted(executable)||Path.GetExtension(executable)!=".exe")throw new ArgumentException("INVALID_FIXED_PROCESS");
        var arguments=new string[args.Length];for(int i=0;i<args.Length;i++)arguments[i]=Quote(args[i]);
        var r=new WheelProcessResult{OutputLimit=limit,DeadlineSeconds=seconds};if(cancelled!=null&&cancelled()){r.State="CANCELLED";r.Cancelled=true;return r;}if(budget.Remaining<=0){r.State="OVERALL_TIMEOUT";r.TimedOut=true;return r;}
        using(var p=new Process())using(var stdout=new MemoryStream())using(var stderr=new MemoryStream()){
            p.StartInfo=new ProcessStartInfo(executable,String.Join(" ",arguments));p.StartInfo.UseShellExecute=false;p.StartInfo.CreateNoWindow=true;
            p.StartInfo.RedirectStandardOutput=true;p.StartInfo.RedirectStandardError=true;p.StartInfo.WorkingDirectory=Path.GetDirectoryName(executable);
            // Configuration/env cannot select a destination, URL, dependency, or alternate executable.
            var remove=new System.Collections.Generic.List<string>();
            foreach(DictionaryEntry item in p.StartInfo.EnvironmentVariables){string key=(string)item.Key;if(key.StartsWith("PIP_",StringComparison.OrdinalIgnoreCase)||key.StartsWith("PYTHON",StringComparison.OrdinalIgnoreCase)||key=="VIRTUAL_ENV"||key=="__PYVENV_LAUNCHER__")remove.Add(key);}
            foreach(string key in remove)p.StartInfo.EnvironmentVariables.Remove(key);
            p.StartInfo.EnvironmentVariables["PIP_CONFIG_FILE"]="nul";p.StartInfo.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"]="1";
            p.StartInfo.EnvironmentVariables["PYTHONIOENCODING"]="utf-8";
            var timer=Stopwatch.StartNew();bool started=false;
            try{
                if(!p.Start())throw new IOException("PROCESS_START_FAILED");started=true;r.PID=p.Id;
                var ob=new byte[1024];var eb=new byte[1024];var os=p.StandardOutput.BaseStream;var es=p.StandardError.BaseStream;
                var ot=os.ReadAsync(ob,0,ob.Length);var et=es.ReadAsync(eb,0,eb.Length);bool oo=true,eo=true;
                while(oo||eo||!p.HasExited){
                    if(cancelled!=null&&cancelled()){r.State="CANCELLED";r.Cancelled=true;break;}
                    if(budget.Remaining<=0){r.State="OVERALL_TIMEOUT";r.TimedOut=true;break;}
                    if(timer.Elapsed.TotalSeconds>=seconds){r.State="TIMEOUT";r.TimedOut=true;break;}
                    if(oo&&ot.IsCompleted){int n=ot.GetAwaiter().GetResult();if(n==0)oo=false;else{if(stdout.Length+stderr.Length+n>limit){r.State="OUTPUT_LIMIT";r.OutputCapped=true;break;}stdout.Write(ob,0,n);ot=os.ReadAsync(ob,0,ob.Length);}}
                    if(eo&&et.IsCompleted){int n=et.GetAwaiter().GetResult();if(n==0)eo=false;else{if(stdout.Length+stderr.Length+n>limit){r.State="OUTPUT_LIMIT";r.OutputCapped=true;break;}stderr.Write(eb,0,n);et=es.ReadAsync(eb,0,eb.Length);}}
                    Thread.Sleep(10);
                }
                if(r.State=="UNKNOWN"&&p.HasExited){r.State="EXITED";r.ExitCode=p.ExitCode;r.ExitCodeKnown=true;}
            }catch{r.State="PROCESS_UNCERTAIN";}
            finally{
                if(started){try{if(!p.HasExited){p.Kill();p.WaitForExit(1000);}if(p.HasExited){r.ExitCode=p.ExitCode;r.ExitCodeKnown=true;}}catch{r.State="PROCESS_UNCERTAIN";}}
                // Killing a client is not evidence that descendants are contained or stopped.
                r.Stdout=Encoding.UTF8.GetString(stdout.ToArray());r.Stderr=Encoding.UTF8.GetString(stderr.ToArray());r.OutputBytes=checked((int)(stdout.Length+stderr.Length));timer.Stop();r.ElapsedMilliseconds=timer.ElapsedMilliseconds;
            }
        }return r;
    }
}
internal sealed class WheelAttempt : IDisposable {
    readonly string directory;FileStream lease,intent;bool completed;int records;
    WheelAttempt(string root){directory=root;}
    static void Write(FileStream file,string text){var bytes=new UTF8Encoding(false).GetBytes(text);file.Write(bytes,0,bytes.Length);file.Flush(true);}
    internal static WheelAttempt Begin(string directory,string target){
        WheelPaths.NoReparse(directory);var a=new WheelAttempt(directory);
        try{
            string leasePath=Path.Combine(directory,"attempt.lease");
            if(File.Exists(leasePath)||Directory.Exists(leasePath))WheelPaths.NoReparse(leasePath);
            a.lease=new FileStream(leasePath,FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);
            WheelPaths.NoReparse(directory);WheelPaths.NoReparse(Path.Combine(directory,"attempt.lease"));
            string intent=Path.Combine(directory,"attempt.intent.json");
            if(File.Exists(intent)||Directory.Exists(intent))throw new IOException("PRIOR_INTENT_NO_REPLAY");
            if(File.Exists(Path.Combine(directory,"attempt.result.json"))||Directory.Exists(Path.Combine(directory,"attempt.result.json")))throw new IOException("PRIOR_RESULT_NO_REPLAY");
            a.intent=new FileStream(intent,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None);
            Write(a.intent,"{\"schema\":1,\"attempt\":\""+Guid.NewGuid().ToString("D")+"\",\"utc\":\""+DateTime.UtcNow.ToString("o")+"\",\"status\":\"INTENT_NO_REPLAY\",\"target\":\""+target.Replace("\\","\\\\").Replace("\"","\\\"")+"\"}\n");
            return a;
        }catch{a.Dispose();throw;}
    }
    internal void Complete(string state,string reason){
        if(completed)throw new IOException("RESULT_ALREADY_RECORDED");
        // Only fixed reason codes are persisted; no process output/config/environment secrets.
        if(!Regex.IsMatch(state,@"^[A-Z_]{1,40}$")||!Regex.IsMatch(reason,@"^[A-Z0-9_ .-]{1,160}$"))throw new IOException("INVALID_RESULT_CODE");
        string path=Path.Combine(directory,"attempt.result.json");
        using(var result=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None))Write(result,"{\"schema\":1,\"utc\":\""+DateTime.UtcNow.ToString("o")+"\",\"state\":\""+state+"\",\"reason\":\""+reason+"\"}\n");
        completed=true;
    }
    internal void RecordStep(WheelStep step,WheelProcessResult r){
        if(completed||intent==null||records>=6||!Enum.IsDefined(typeof(WheelStep),step)||r==null||r.Stdout==null||r.Stderr==null||!Regex.IsMatch(r.State,@"^[A-Z_]{1,40}$")||r.OutputLimit<128||r.OutputLimit>16384||r.OutputBytes<0||r.OutputBytes>r.OutputLimit||r.Stdout.Length+r.Stderr.Length>r.OutputBytes||r.DeadlineSeconds<1||r.DeadlineSeconds>120||r.ElapsedMilliseconds<0)throw new IOException("INVALID_BOUNDED_STEP_EVIDENCE");
        var value=new Dictionary<string,object>{
            {"schema",1},{"sequence",records+1},{"stage",step.ToString()},{"utc",DateTime.UtcNow.ToString("o")},
            {"state",r.State},{"exit_code",r.ExitCode},{"exit_code_known",r.ExitCodeKnown},{"pid",r.PID},
            {"timed_out",r.TimedOut},{"output_limit_reached",r.OutputCapped},{"cancelled",r.Cancelled},
            {"captured_output_bytes",r.OutputBytes},{"output_limit_bytes",r.OutputLimit},{"deadline_seconds",r.DeadlineSeconds},{"elapsed_ms",r.ElapsedMilliseconds},
            {"stdout",r.Stdout},{"stderr",r.Stderr},{"raw_local_only",true},{"descendant_containment_established",false}
        };
        var serializer=new JavaScriptSerializer();serializer.MaxJsonLength=131072;serializer.RecursionLimit=5;
        string text=serializer.Serialize(value)+"\n";if(new UTF8Encoding(false).GetByteCount(text)>131072)throw new IOException("STEP_EVIDENCE_SIZE_LIMIT");
        WheelPaths.NoReparse(directory);string path=Path.Combine(directory,"step-"+(records+1).ToString("00")+"-"+step.ToString()+".json");
        using(var file=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None))Write(file,text);
        records++;
    }
    public void Dispose(){if(intent!=null){intent.Dispose();intent=null;}if(lease!=null){lease.Dispose();lease=null;}}
}
