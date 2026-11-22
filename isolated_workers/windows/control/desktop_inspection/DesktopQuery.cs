using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using System.Collections;
using System.Collections.Generic;
namespace AIBS.DesktopInspection {
    public sealed class DesktopQueryResult {
        public string State {get;internal set;}
        public string Reason {get;internal set;}
        public int ExitCode {get;internal set;}
        public bool ExitCodeKnown {get;internal set;}
        public int PID {get;internal set;}
        public string CreationUtc {get;internal set;}
        public string Stdout {get;internal set;}
        public string Stderr {get;internal set;}
        public bool TimedOut {get;internal set;}
        public bool OutputCapped {get;internal set;}
        public long ElapsedMilliseconds {get;internal set;}
        public int OutputBytes {get;internal set;}
        public int ErrorBytes {get;internal set;}
        public int CombinedLimitBytes {get;internal set;}
        public int StderrLimitBytes {get;internal set;}
        public string Operation {get;internal set;}
        public bool Cancelled {get;internal set;}
        public bool ClientKillRequested {get;internal set;}
        public bool DescendantTerminationEstablished {get{return false;}}
        public bool StderrLimitReached {get;internal set;}
        public bool CombinedLimitReached {get;internal set;}
    }
    public static class DesktopQuery {
        public const string RegistryRoot=@"C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vbox_config";
        public const string ExecutablePath=@"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe";
        public const string ExecutableSHA256="178E016ED38CB6E369A5C17C6C960C176674B9C864030D8CE0AD2867613BECFF";
        public const string WorkerSID="S-1-5-21-2133766663-4066672948-2456486318-1005";
        public const string VMUUID="6c5a53da-ab80-4ecb-8be6-4059266f736e",DiskUUID="9e1efe57-9da5-49f8-acea-763429616968";
        const int QuerySeconds=20,CombinedCap=1048576,ErrorCap=65536;
        static DesktopQueryResult Empty(string operation){return new DesktopQueryResult{Operation=operation,State="UNKNOWN",Reason="",ExitCode=-1,Stdout="",Stderr="",CreationUtc="",CombinedLimitBytes=CombinedCap,StderrLimitBytes=ErrorCap};}
        static DesktopQueryResult Refuse(string operation,string reason){var r=Empty(operation);r.State="REFUSED";r.Reason=reason;return r;}
        internal static string[] FixedArguments(string operation){
            if(operation=="VMInfo")return new string[]{"showvminfo",VMUUID,"--machinereadable"};
            // Oracle manual 8.29: showmediuminfo [disk|dvd|floppy] <uuid|filename>.
            // No unverified machine-readable flag is used for the disk query.
            if(operation=="DiskInfo")return new string[]{"showmediuminfo","disk",DiskUUID};
            throw new ArgumentException("FIXED_OPERATION_REQUIRED");
        }
        internal static bool WorkerAllowed(string sid,bool administrator,bool medium,bool x64){return sid==WorkerSID&&!administrator&&medium&&x64;}
        [DllImport("advapi32.dll",SetLastError=true)]static extern bool GetTokenInformation(IntPtr token,int info,IntPtr buffer,int length,out int required);
        [DllImport("advapi32.dll")]static extern IntPtr GetSidSubAuthorityCount(IntPtr sid);
        [DllImport("advapi32.dll")]static extern IntPtr GetSidSubAuthority(IntPtr sid,uint index);
        static bool Medium(WindowsIdentity identity){
            int length;IntPtr value=Marshal.AllocHGlobal(4);
            try{if(!GetTokenInformation(identity.Token,20,value,4,out length)||Marshal.ReadInt32(value)!=0)return false;}finally{Marshal.FreeHGlobal(value);}
            GetTokenInformation(identity.Token,25,IntPtr.Zero,0,out length);if(length<IntPtr.Size||length>1024)return false;
            value=Marshal.AllocHGlobal(length);
            try{if(!GetTokenInformation(identity.Token,25,value,length,out length))return false;IntPtr sid=Marshal.ReadIntPtr(value);byte count=Marshal.ReadByte(GetSidSubAuthorityCount(sid));return count>0&&Marshal.ReadInt32(GetSidSubAuthority(sid,(uint)(count-1)))==8192;}finally{Marshal.FreeHGlobal(value);}
        }
        internal static bool ActualWorkerAllowed(){
            using(var identity=WindowsIdentity.GetCurrent()){
                if(identity.User==null||identity.User.Value!=WorkerSID)return false;
                return WorkerAllowed(identity.User.Value,new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator),Medium(identity),Environment.Is64BitProcess&&Environment.Is64BitOperatingSystem);
            }
        }
        internal static void NoReparse(string path){
            if(!Path.IsPathRooted(path)||path.StartsWith(@"\\",StringComparison.Ordinal))throw new IOException("ABSOLUTE_LOCAL_PATH_REQUIRED");
            for(string current=Path.GetFullPath(path);!String.IsNullOrEmpty(current);current=Path.GetDirectoryName(current))if((File.GetAttributes(current)&FileAttributes.ReparsePoint)!=0)throw new IOException("REPARSE_PATH_REFUSED");
        }
        /// <summary>
        /// Fixed read-only native queries only; this API grants no task or VM-control authority.
        /// Caller must already hold its private inspection lease and durable query intent, and
        /// freshly verify the exact pinned binary's Valid Oracle Authenticode signature.
        /// No retry occurs here. Caller must quarantine any uncertain/native nonzero result.
        /// cancelled must be a nonblocking trusted flag reader, not an arbitrary user callback.
        /// </summary>
        public static DesktopQueryResult InvokeFixed(string operation,string registryRoot,Func<bool> cancelled){
            if(operation!="VMInfo"&&operation!="DiskInfo")return Refuse("","FIXED_OPERATION_REQUIRED");
            if(!String.Equals(registryRoot,RegistryRoot,StringComparison.Ordinal))return Refuse(operation,"EXACT_FIXED_REGISTRY_REQUIRED");
            bool queryEntered=false;
            try{
                if(!ActualWorkerAllowed())return Refuse(operation,"EXACT_STANDARD_MEDIUM_WORKER_REQUIRED");
                NoReparse(ExecutablePath);NoReparse(RegistryRoot);if(!Directory.Exists(RegistryRoot))return Refuse(operation,"FIXED_REGISTRY_MISSING");
                using(var held=new FileStream(ExecutablePath,FileMode.Open,FileAccess.Read,FileShare.Read)){
                    NoReparse(ExecutablePath);string hash;
                    using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(held)).Replace("-","");
                    if(held.Length!=2601824||hash!=ExecutableSHA256)return Refuse(operation,"PINNED_ORACLE_BINARY_REQUIRED");
                    // Repeat real identity immediately before starting the fixed native child.
                    if(!ActualWorkerAllowed())return Refuse(operation,"WORKER_GUARD_CHANGED");
                    queryEntered=true;var r=RunBounded(ExecutablePath,FixedArguments(operation),RegistryRoot,cancelled,QuerySeconds,CombinedCap,ErrorCap);r.Operation=operation;return r;
                }
            }catch{if(queryEntered){var uncertain=Empty(operation);uncertain.State="PROCESS_UNCERTAIN";uncertain.Reason="QUERY_WRAPPER_UNCERTAIN";return uncertain;}return Refuse(operation,"READ_ONLY_PRECHECK_FAILED");}
        }
        internal static string Quote(string value){
            if(value==null||value.IndexOfAny(new char[]{'\0','\r','\n'})>=0)throw new ArgumentException("INVALID_FIXED_ARGUMENT");
            var text=new StringBuilder("\"");int slashes=0;
            foreach(char item in value){if(item=='\\'){slashes++;continue;}if(item=='"')text.Append('\\',slashes*2+1);else text.Append('\\',slashes);text.Append(item);slashes=0;}
            text.Append('\\',slashes*2);text.Append('"');return text.ToString();
        }
        // Trusted same-assembly fixtures use this internal method with only the fixed test child.
        // It is not a public command endpoint and does not grant authority to execute anything.
        internal static DesktopQueryResult RunBounded(string executable,string[] args,string childHome,Func<bool> cancelled,int seconds,int combinedLimit,int errorLimit){
            if(!Path.IsPathRooted(executable)||Path.GetExtension(executable)!=".exe"||args==null||childHome==null||seconds<1||seconds>20||combinedLimit<128||combinedLimit>CombinedCap||errorLimit<16||errorLimit>ErrorCap||errorLimit>combinedLimit)throw new ArgumentException("INVALID_BOUNDED_FIXED_PROCESS");
            var quoted=new string[args.Length];for(int i=0;i<args.Length;i++)quoted[i]=Quote(args[i]);
            var r=Empty("");r.CombinedLimitBytes=combinedLimit;r.StderrLimitBytes=errorLimit;
            var timer=Stopwatch.StartNew();
            try{if(cancelled!=null&&cancelled()){r.State="CANCELLED";r.Cancelled=true;return r;}}catch{r.State="PROCESS_UNCERTAIN";r.Reason="CANCEL_CHECK_FAILED";return r;}
            using(var process=new Process())using(var output=new MemoryStream())using(var error=new MemoryStream()){
                process.StartInfo=new ProcessStartInfo(executable,String.Join(" ",quoted));process.StartInfo.UseShellExecute=false;process.StartInfo.CreateNoWindow=true;
                process.StartInfo.RedirectStandardOutput=true;process.StartInfo.RedirectStandardError=true;process.StartInfo.WorkingDirectory=Path.GetDirectoryName(executable);
                var remove=new List<string>();foreach(DictionaryEntry entry in process.StartInfo.EnvironmentVariables)if(((string)entry.Key).StartsWith("VBOX_",StringComparison.OrdinalIgnoreCase))remove.Add((string)entry.Key);
                foreach(string key in remove)process.StartInfo.EnvironmentVariables.Remove(key);
                process.StartInfo.EnvironmentVariables["VBOX_USER_HOME"]=childHome;
                bool started=false;
                try{
                    if(!process.Start())throw new IOException("FIXED_CHILD_NOT_STARTED");started=true;r.PID=process.Id;r.CreationUtc=process.StartTime.ToUniversalTime().ToString("o");
                    var ob=new byte[4096];var eb=new byte[4096];var os=process.StandardOutput.BaseStream;var es=process.StandardError.BaseStream;
                    var ot=os.ReadAsync(ob,0,ob.Length);var et=es.ReadAsync(eb,0,eb.Length);bool oo=true,eo=true;
                    while(oo||eo||!process.HasExited){
                        if(cancelled!=null&&cancelled()){r.State="CANCELLED";r.Cancelled=true;break;}
                        if(timer.Elapsed.TotalSeconds>=seconds){r.State="TIMEOUT";r.TimedOut=true;break;}
                        bool progress=false;
                        if(oo&&ot.IsCompleted){progress=true;int n=ot.GetAwaiter().GetResult();if(n==0)oo=false;else{if(output.Length+error.Length+n>combinedLimit){r.State="OUTPUT_LIMIT";r.OutputCapped=true;r.CombinedLimitReached=true;break;}output.Write(ob,0,n);ot=os.ReadAsync(ob,0,ob.Length);}}
                        if(eo&&et.IsCompleted){progress=true;int n=et.GetAwaiter().GetResult();if(n==0)eo=false;else{if(error.Length+n>errorLimit||output.Length+error.Length+n>combinedLimit){r.State="OUTPUT_LIMIT";r.OutputCapped=true;r.StderrLimitReached=error.Length+n>errorLimit;r.CombinedLimitReached=output.Length+error.Length+n>combinedLimit;break;}error.Write(eb,0,n);et=es.ReadAsync(eb,0,eb.Length);}}
                        if(!progress){int wait=Math.Min(10,Math.Max(0,seconds*1000-(int)timer.ElapsedMilliseconds));if(oo&&eo)Task.WaitAny(new Task[]{ot,et},wait);else if(oo)ot.Wait(wait);else if(eo)et.Wait(wait);else Thread.Sleep(1);}
                    }
                    if(r.State=="UNKNOWN"&&process.HasExited)r.State="EXITED";
                }catch{r.State="PROCESS_UNCERTAIN";r.Reason="FIXED_NATIVE_QUERY_UNCERTAIN";}
                finally{
                    if(started){
                        try{
                            if(!process.HasExited){r.ClientKillRequested=true;process.Kill();int remaining=Math.Max(0,seconds*1000-(int)timer.ElapsedMilliseconds);process.WaitForExit(Math.Min(1000,remaining));}
                            if(process.HasExited){r.ExitCode=process.ExitCode;r.ExitCodeKnown=true;}
                        }catch{r.Reason="CLIENT_TERMINATION_UNCERTAIN";if(r.State=="EXITED"||r.State=="UNKNOWN")r.State="PROCESS_UNCERTAIN";}
                    }
                    r.OutputBytes=checked((int)(output.Length+error.Length));r.ErrorBytes=checked((int)error.Length);
                    r.Stdout=Encoding.UTF8.GetString(output.ToArray());r.Stderr=Encoding.UTF8.GetString(error.ToArray());timer.Stop();r.ElapsedMilliseconds=timer.ElapsedMilliseconds;
                    // Only this spawned client is targeted. VBoxSVC and descendant termination
                    // or containment are never established by this result, even after exit 0.
                }
            }
            return r;
        }
    }
}
