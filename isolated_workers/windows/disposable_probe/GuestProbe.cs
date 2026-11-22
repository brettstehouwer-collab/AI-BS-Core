// Fixed disposable-Windows diagnostic. No candidate loading, script engine or key.
// Image/VM arguments are reported claims; the host independently verifies them.
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Security.AccessControl;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using Microsoft.Win32;
using Microsoft.Win32.SafeHandles;

namespace AIBS.DisposableProbe {
    internal sealed class ProbeRejected : Exception { internal ProbeRejected(string code) : base(code) {} }
    internal sealed class Options {
        internal string Mode, Attempt, Challenge, WorkerSid, VmId, ImageHash;
        internal int TimeoutMs, OutputBytes, ParentPid;
        internal long ParentTicks;
        internal string ChildToken;
        internal bool IsChild { get { return ChildToken != null; } }
        internal string[] PublicArguments() {
            return new [] {"--mode",Mode,"--attempt",Attempt,"--challenge",Challenge,
                "--timeout-ms",TimeoutMs.ToString(CultureInfo.InvariantCulture),"--output-bytes",OutputBytes.ToString(CultureInfo.InvariantCulture),
                "--worker-sid",WorkerSid,"--vm-id",VmId,"--image-sha256",ImageHash};
        }
        internal static Options Parse(string[] args) {
            Require(args != null && (args.Length == 16 || args.Length == 22), "EXACT_ARGUMENTS_REQUIRED");
            string[] names = {"--mode","--attempt","--challenge","--timeout-ms","--output-bytes","--worker-sid","--vm-id","--image-sha256"};
            for (int i=0;i<names.Length;i++) Require(args[i*2] == names[i], "EXACT_ARGUMENT_ORDER_REQUIRED");
            var value = new Options {Mode=args[1],Attempt=args[3],Challenge=args[5],WorkerSid=args[11],VmId=args[13],ImageHash=args[15]};
            Require(value.Mode == "emit" || value.Mode == "sleep" || value.Mode == "overflow", "FIXED_MODE_REQUIRED");
            Require(Regex.IsMatch(value.Attempt ?? "", "\\A[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\\z"), "CANONICAL_ATTEMPT_REQUIRED");
            Require(Regex.IsMatch(value.VmId ?? "", "\\A[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\\z"), "CANONICAL_VM_REQUIRED");
            Require(IsHex(value.Challenge) && IsHex(value.ImageHash), "CANONICAL_DIGEST_REQUIRED");
            Require(Regex.IsMatch(value.WorkerSid ?? "", "\\AS-1-5-21-[0-9]{1,10}-[0-9]{1,10}-[0-9]{1,10}-[0-9]{1,10}\\z"), "WORKER_SID_REQUIRED");
            Require(value.WorkerSid != "S-1-5-21-2133766663-4066672948-2456486318-1005", "KNOWN_HOST_WORKER_REFUSED");
            value.TimeoutMs = Number(args[7],500,30000);
            value.OutputBytes = Number(args[9],4096,1048576);
            if(args.Length == 22) {
                Require(args[16] == "--child-token" && args[18] == "--parent-pid" && args[20] == "--parent-start-ticks", "EXACT_CHILD_ARGUMENTS_REQUIRED");
                Require(IsHex(args[17]), "CHILD_TOKEN_REQUIRED"); value.ChildToken=args[17];
                value.ParentPid=Number(args[19],1,Int32.MaxValue);
                Require(Regex.IsMatch(args[21] ?? "", "\\A[1-9][0-9]{0,18}\\z") && Int64.TryParse(args[21],out value.ParentTicks) && value.ParentTicks > 0, "PARENT_IDENTITY_REQUIRED");
            }
            return value;
        }
        internal static bool IsHex(string value) { return Regex.IsMatch(value ?? "", "\\A[0-9a-f]{64}\\z"); }
        internal static int Number(string value,int low,int high) {
            int result;
            Require(Regex.IsMatch(value ?? "", "\\A[1-9][0-9]{0,9}\\z") && Int32.TryParse(value,out result), "CANONICAL_INTEGER_REQUIRED");
            result=Int32.Parse(value,CultureInfo.InvariantCulture); Require(result>=low && result<=high,"INTEGER_BOUND_REQUIRED"); return result;
        }
        internal static void Require(bool condition,string code) { if(!condition) throw new ProbeRejected(code); }
    }

    internal sealed class IdentityObservation {
        internal string Sid, Identity, Machine;
        internal bool Medium, AdministratorGroup, Standard;
    }
    internal static class GuestIdentity {
        [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetTokenInformation(IntPtr token,int kind,IntPtr buffer,int length,out int required);
        internal static bool Policy(string actualSid,string boundSid,string identity,string machine,bool medium,bool admin,bool elevated,bool x64,bool virtualBox) {
            return actualSid == boundSid && actualSid != "S-1-5-21-2133766663-4066672948-2456486318-1005" &&
                String.Equals(identity,machine+@"\aibs_vm_worker",StringComparison.OrdinalIgnoreCase) && medium && !admin && !elevated && x64 && virtualBox;
        }
        static bool Medium(WindowsIdentity identity) {
            int needed; GetTokenInformation(identity.Token,25,IntPtr.Zero,0,out needed);
            if(needed<IntPtr.Size || needed>1024) return false;
            IntPtr buffer=Marshal.AllocHGlobal(needed);
            try { if(!GetTokenInformation(identity.Token,25,buffer,needed,out needed)) return false;
                var sid=new SecurityIdentifier(Marshal.ReadIntPtr(buffer)); return sid.Value=="S-1-16-8192";
            } finally { Marshal.FreeHGlobal(buffer); }
        }
        static bool Elevated(WindowsIdentity identity) {
            int needed; IntPtr buffer=Marshal.AllocHGlobal(4);
            try { return !GetTokenInformation(identity.Token,20,buffer,4,out needed) || Marshal.ReadInt32(buffer)!=0; }
            finally { Marshal.FreeHGlobal(buffer); }
        }
        internal static IdentityObservation Read(string boundSid) {
            Options.Require(Environment.OSVersion.Platform == PlatformID.Win32NT,"WINDOWS_REQUIRED");
            using(var identity=WindowsIdentity.GetCurrent()) {
                var r=new IdentityObservation {Sid=identity.User==null?"":identity.User.Value,Identity=identity.Name,Machine=Environment.MachineName,Medium=Medium(identity)};
                r.AdministratorGroup=identity.Groups.Cast<IdentityReference>().Any(g=>g.Value=="S-1-5-32-544" || g.Value=="S-1-5-114");
                bool virtualBox=String.Equals(Convert.ToString(Registry.GetValue(@"HKEY_LOCAL_MACHINE\HARDWARE\DESCRIPTION\System\BIOS","SystemProductName","")),"VirtualBox",StringComparison.Ordinal);
                r.Standard=Policy(r.Sid,boundSid,r.Identity,r.Machine,r.Medium,r.AdministratorGroup,Elevated(identity),Environment.Is64BitProcess && Environment.Is64BitOperatingSystem,virtualBox);
                Options.Require(identity.IsAuthenticated && !identity.IsSystem && r.Standard,"EXACT_STANDARD_DISPOSABLE_GUEST_REQUIRED"); return r;
            }
        }
    }

    internal sealed class OutputBuffer {
        readonly object gate=new object(); readonly int maximum;
        readonly MemoryStream stdout=new MemoryStream(),stderr=new MemoryStream();
        internal bool LimitHit {get;private set;}
        internal OutputBuffer(int maximum) { Options.Require(maximum>=1 && maximum<=1048576,"OUTPUT_BOUND_REQUIRED"); this.maximum=maximum; }
        internal void Add(bool error,byte[] block,int length) {
            lock(gate) { int remaining=maximum-(int)(stdout.Length+stderr.Length); int take=Math.Min(remaining,length);
                (error?stderr:stdout).Write(block,0,take); if(take<length) LimitHit=true; }
        }
        internal byte[] Out {get {lock(gate) return stdout.ToArray();}}
        internal byte[] Error {get {lock(gate) return stderr.ToArray();}}
        internal int Count {get {lock(gate) return (int)(stdout.Length+stderr.Length);}}
        internal bool Overflow {get {lock(gate) return LimitHit;}}
    }

    internal static class Native {
        [StructLayout(LayoutKind.Sequential)] internal struct SECURITY_ATTRIBUTES {internal int Length;internal IntPtr Descriptor;[MarshalAs(UnmanagedType.Bool)]internal bool Inherit;}
        [StructLayout(LayoutKind.Sequential)] internal struct STARTUPINFO { internal int cb;internal IntPtr reserved,desktop,title;internal uint x,y,xs,ys,xc,yc,fill,flags;internal ushort show,reserved2;internal IntPtr reservedPtr,stdin,stdout,stderr; }
        [StructLayout(LayoutKind.Sequential)] internal struct STARTUPINFOEX {internal STARTUPINFO Startup;internal IntPtr Attributes;}
        [StructLayout(LayoutKind.Sequential)] internal struct PROCESS_INFORMATION {internal IntPtr Process,Thread;internal uint Pid,Tid;}
        [StructLayout(LayoutKind.Sequential)] internal struct BASIC_LIMIT {internal long ProcessTime,JobTime;internal uint Flags;internal UIntPtr MinWorking,MaxWorking;internal uint ActiveLimit;internal UIntPtr Affinity;internal uint Priority,Scheduling;}
        [StructLayout(LayoutKind.Sequential)] internal struct IO_COUNTERS {internal ulong ReadOps,WriteOps,OtherOps,ReadBytes,WriteBytes,OtherBytes;}
        [StructLayout(LayoutKind.Sequential)] internal struct EXTENDED_LIMIT {internal BASIC_LIMIT Basic;internal IO_COUNTERS Io;internal UIntPtr ProcessMemory,JobMemory,PeakProcessMemory,PeakJobMemory;}
        [StructLayout(LayoutKind.Sequential)] internal struct CPU_RATE {internal uint Flags,Rate;}
        [StructLayout(LayoutKind.Sequential)] internal struct ACCOUNTING {internal long User,Kernel,PeriodUser,PeriodKernel;internal uint PageFaults,TotalProcesses,ActiveProcesses,TerminatedProcesses;}
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern IntPtr CreateJobObjectW(IntPtr sa,string name);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool SetInformationJobObject(IntPtr job,int kind,IntPtr data,uint length);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool QueryInformationJobObject(IntPtr job,int kind,IntPtr data,uint length,IntPtr returned);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool IsProcessInJob(IntPtr process,IntPtr job,out bool answer);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool TerminateJobObject(IntPtr job,uint code);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool CloseHandle(IntPtr value);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool CreatePipe(out IntPtr read,out IntPtr write,ref SECURITY_ATTRIBUTES security,uint size);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool SetHandleInformation(IntPtr handle,uint mask,uint value);
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] internal static extern IntPtr CreateFileW(string name,uint access,uint share,ref SECURITY_ATTRIBUTES sa,uint create,uint flags,IntPtr template);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool InitializeProcThreadAttributeList(IntPtr list,int count,uint flags,ref IntPtr bytes);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool UpdateProcThreadAttribute(IntPtr list,uint flags,IntPtr attribute,IntPtr value,IntPtr size,IntPtr previous,IntPtr returned);
        [DllImport("kernel32.dll")] internal static extern void DeleteProcThreadAttributeList(IntPtr list);
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] internal static extern bool CreateProcessW(string app,StringBuilder command,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr environment,string cwd,ref STARTUPINFOEX startup,out PROCESS_INFORMATION info);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern uint ResumeThread(IntPtr thread);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool GetExitCodeProcess(IntPtr handle,out uint exit);
        [DllImport("kernel32.dll",SetLastError=true)] internal static extern bool TerminateProcess(IntPtr handle,uint exit);
        internal static void Require(bool okay) {if(!okay) throw new ProbeRejected("NATIVE_PROCESS_CONTROL_FAILED");}
        internal static void Close(ref IntPtr handle) {if(handle!=IntPtr.Zero && handle!=new IntPtr(-1)) CloseHandle(handle); handle=IntPtr.Zero;}
    }

    internal sealed class Job : IDisposable {
        internal const ulong MemoryBytes=268435456;
        internal const uint LimitFlags=0x2000|0x200|0x8; // Kill on close, aggregate job memory, active process count.
        internal IntPtr Handle;
        internal Job() {
            Handle=Native.CreateJobObjectW(IntPtr.Zero,null); Native.Require(Handle!=IntPtr.Zero);
            try {
                var limits=new Native.EXTENDED_LIMIT(); limits.Basic.Flags=LimitFlags; limits.Basic.ActiveLimit=1; limits.JobMemory=new UIntPtr(MemoryBytes);
                Set(9,limits); Set(15,new Native.CPU_RATE{Flags=5,Rate=2500});
                var actual=Read<Native.EXTENDED_LIMIT>(9); var cpu=Read<Native.CPU_RATE>(15);
                Options.Require(actual.Basic.Flags==LimitFlags && actual.Basic.ActiveLimit==1 && actual.JobMemory.ToUInt64()==MemoryBytes && cpu.Flags==5 && cpu.Rate==2500,"JOB_PROFILE_READBACK_FAILED");
            } catch {Dispose();throw;}
        }
        void Set<T>(int kind,T value) {IntPtr p=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(T)));try {Marshal.StructureToPtr(value,p,false);Native.Require(Native.SetInformationJobObject(Handle,kind,p,(uint)Marshal.SizeOf(typeof(T))));}finally{Marshal.FreeHGlobal(p);}}
        internal T Read<T>(int kind) {IntPtr p=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(T)));try {Native.Require(Native.QueryInformationJobObject(Handle,kind,p,(uint)Marshal.SizeOf(typeof(T)),IntPtr.Zero));return (T)Marshal.PtrToStructure(p,typeof(T));}finally{Marshal.FreeHGlobal(p);}}
        internal bool Empty {get{return Read<Native.ACCOUNTING>(1).ActiveProcesses==0;}}
        internal bool StopAndConfirm() {Native.Require(Native.TerminateJobObject(Handle,124));var timer=Stopwatch.StartNew();while(timer.ElapsedMilliseconds<2000){if(Empty)return true;Thread.Sleep(10);}return Empty;}
        public void Dispose(){Native.Close(ref Handle);}
    }

    internal sealed class RunResult {
        internal string State="PROCESS_UNCERTAIN",Error=""; internal int? ExitCode;
        internal int Pid;internal string StartedUtc=""; internal long Elapsed;
        internal bool TerminationConfirmed;internal OutputBuffer Output;
    }
    internal static class FixedRunner {
        internal static string Quote(string text) {
            Options.Require(text!=null && text.IndexOfAny(new[]{'\0','\r','\n'})<0,"UNSAFE_ARGUMENT_REQUIRED");
            var b=new StringBuilder("\"");int slashes=0;
            foreach(char c in text){if(c=='\\'){slashes++;continue;}if(c=='\"'){b.Append('\\',slashes*2+1);b.Append(c);}else{b.Append('\\',slashes);b.Append(c);}slashes=0;}
            b.Append('\\',slashes*2);b.Append('"');return b.ToString();
        }
        // Internal primitive: production entry only passes its held own executable and fixed child arguments.
        // Infrastructure harness may pass its separately compiled, trusted fixed fixture.
        internal static RunResult Run(string executable,string[] args,int timeout,int cap,IDictionary<string,string> environment,Func<bool> cancelled) {
            var r=new RunResult {Output=new OutputBuffer(cap)};var timer=Stopwatch.StartNew();
            var pi=new Native.PROCESS_INFORMATION();IntPtr readOut=IntPtr.Zero,writeOut=IntPtr.Zero,readErr=IntPtr.Zero,writeErr=IntPtr.Zero,input=IntPtr.Zero,attributes=IntPtr.Zero,handles=IntPtr.Zero,env=IntPtr.Zero;
            Task[] readers=null;bool assigned=false,created=false,attributesReady=false;
            using(var job=new Job())try {
                var sa=new Native.SECURITY_ATTRIBUTES {Length=Marshal.SizeOf(typeof(Native.SECURITY_ATTRIBUTES)),Inherit=true};
                Native.Require(Native.CreatePipe(out readOut,out writeOut,ref sa,0));Native.Require(Native.CreatePipe(out readErr,out writeErr,ref sa,0));
                Native.Require(Native.SetHandleInformation(readOut,1,0));Native.Require(Native.SetHandleInformation(readErr,1,0));
                input=Native.CreateFileW("NUL",0x80000000,3,ref sa,3,0,IntPtr.Zero);Native.Require(input!=new IntPtr(-1));
                IntPtr size=IntPtr.Zero;Native.InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);
                Options.Require(size.ToInt64()>0 && size.ToInt64()<65536,"ATTRIBUTE_LIST_BOUND");attributes=Marshal.AllocHGlobal(size);
                Native.Require(Native.InitializeProcThreadAttributeList(attributes,1,0,ref size));attributesReady=true;
                handles=Marshal.AllocHGlobal(IntPtr.Size*3);Marshal.WriteIntPtr(handles,0,input);Marshal.WriteIntPtr(handles,IntPtr.Size,writeOut);Marshal.WriteIntPtr(handles,IntPtr.Size*2,writeErr);
                Native.Require(Native.UpdateProcThreadAttribute(attributes,0,new IntPtr(0x20002),handles,new IntPtr(IntPtr.Size*3),IntPtr.Zero,IntPtr.Zero));
                var startup=new Native.STARTUPINFOEX();startup.Startup.cb=Marshal.SizeOf(typeof(Native.STARTUPINFOEX));startup.Startup.flags=0x100;startup.Startup.stdin=input;startup.Startup.stdout=writeOut;startup.Startup.stderr=writeErr;startup.Attributes=attributes;
                string block=String.Join("\0",environment.OrderBy(e=>e.Key,StringComparer.OrdinalIgnoreCase).Select(e=>e.Key+"="+e.Value))+"\0\0";env=Marshal.StringToHGlobalUni(block);
                string command=Quote(executable)+" "+String.Join(" ",args.Select(Quote));
                Native.Require(Native.CreateProcessW(executable,new StringBuilder(command),IntPtr.Zero,IntPtr.Zero,true,0x08000000|0x00000004|0x00000400|0x00080000,env,Path.GetDirectoryName(executable),ref startup,out pi));created=true;r.Pid=(int)pi.Pid;
                using(var child=Process.GetProcessById(r.Pid))r.StartedUtc=child.StartTime.ToUniversalTime().ToString("o");
                Native.Require(Native.AssignProcessToJobObject(job.Handle,pi.Process));assigned=true;bool inside;Native.Require(Native.IsProcessInJob(pi.Process,job.Handle,out inside)&&inside);
                Native.Close(ref writeOut);Native.Close(ref writeErr);Native.Close(ref input);
                var stdout=new FileStream(new SafeFileHandle(readOut,true),FileAccess.Read,4096,false);readOut=IntPtr.Zero;
                var stderr=new FileStream(new SafeFileHandle(readErr,true),FileAccess.Read,4096,false);readErr=IntPtr.Zero;
                readers=new[]{Task.Factory.StartNew(()=>Consume(stdout,false,r.Output)),Task.Factory.StartNew(()=>Consume(stderr,true,r.Output))};
                Native.Require(Native.ResumeThread(pi.Thread)!=UInt32.MaxValue);
                while(true) {
                    if(cancelled!=null && cancelled()){r.State="CANCELLED";break;}
                    if(r.Output.Overflow){r.State="OUTPUT_LIMIT";break;}
                    uint wait=Native.WaitForSingleObject(pi.Process,10);
                    if(wait==0){r.State="COMPLETED";break;}Native.Require(wait==258);
                    if(timer.ElapsedMilliseconds>=timeout){r.State="TIMED_OUT";break;}
                }
                r.TerminationConfirmed=job.StopAndConfirm();
                Native.Require(Native.WaitForSingleObject(pi.Process,2000)==0);uint code;Native.Require(Native.GetExitCodeProcess(pi.Process,out code));r.ExitCode=unchecked((int)code);
                if(!Task.WaitAll(readers,2500) || readers.Any(t=>t.IsFaulted) || !r.TerminationConfirmed){r.State="PROCESS_UNCERTAIN";r.Error="TERMINATION_OR_DRAIN_UNCONFIRMED";}
                else if(r.Output.Overflow && r.State=="COMPLETED")r.State="OUTPUT_LIMIT";
            }catch {r.State="PROCESS_UNCERTAIN";r.Error="NATIVE_PROCESS_CONTROL_FAILED";
                try {if(assigned)r.TerminationConfirmed=job.StopAndConfirm();else if(created){Native.TerminateProcess(pi.Process,125);r.TerminationConfirmed=Native.WaitForSingleObject(pi.Process,2000)==0;}}catch {r.TerminationConfirmed=false;}
            }finally {
                Native.Close(ref writeOut);Native.Close(ref writeErr);Native.Close(ref input);Native.Close(ref readOut);Native.Close(ref readErr);
                if(readers!=null)try{Task.WaitAll(readers,2500);}catch{r.State="PROCESS_UNCERTAIN";r.Error="OUTPUT_DRAIN_FAILED";}
                Native.Close(ref pi.Thread);Native.Close(ref pi.Process);
                if(attributesReady)Native.DeleteProcThreadAttributeList(attributes);if(attributes!=IntPtr.Zero)Marshal.FreeHGlobal(attributes);if(handles!=IntPtr.Zero)Marshal.FreeHGlobal(handles);if(env!=IntPtr.Zero)Marshal.FreeHGlobal(env);
                r.Elapsed=timer.ElapsedMilliseconds;
            }
            return r;
        }
        static void Consume(Stream stream,bool error,OutputBuffer output){using(stream){var block=new byte[4096];int count;while((count=stream.Read(block,0,block.Length))>0)output.Add(error,block,count);}}
    }

    internal static class Program {
        static string Hash(byte[] bytes){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        static string Hash(Stream stream){stream.Position=0;using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
        static string Executable(){using(var p=Process.GetCurrentProcess())return p.MainModule.FileName;}
        static void NoLinks(string path) {for(string p=path;!String.IsNullOrEmpty(p);p=Path.GetDirectoryName(p))Options.Require((File.GetAttributes(p)&FileAttributes.ReparsePoint)==0,"LINKED_EXECUTABLE_PATH_REFUSED");}
        static void Parent(Options options,string executable) {
            Options.Require(Environment.GetEnvironmentVariable("AIBS_FIXED_PROBE_CHILD_TOKEN")==options.ChildToken,"CHILD_CONTEXT_REQUIRED");
            using(var parent=Process.GetProcessById(options.ParentPid)) {
                Options.Require(parent.StartTime.ToUniversalTime().Ticks==options.ParentTicks && String.Equals(parent.MainModule.FileName,executable,StringComparison.OrdinalIgnoreCase),"EXACT_PARENT_REQUIRED");
            }
        }
        static int Child(Options options,string executable) {
            Parent(options,executable);
            if(options.Mode=="emit") {Console.Out.Write("probe\n");Console.Error.Write("diagnostic\n");return 7;}
            if(options.Mode=="sleep") {Thread.Sleep(10000);return 0;}
            byte[] block=Enumerable.Repeat((byte)'X',4096).ToArray();
            using(Stream stdout=Console.OpenStandardOutput())using(Stream stderr=Console.OpenStandardError())for(int i=0;i<512;i++){(i%2==0?stdout:stderr).Write(block,0,block.Length);}
            return 0;
        }
        public static int Main(string[] args) {
            Options options=null;var report=new Dictionary<string,object>();
            try {
                options=Options.Parse(args);var identity=GuestIdentity.Read(options.WorkerSid);string executable=Executable();NoLinks(executable);
                using(var held=new FileStream(executable,FileMode.Open,FileAccess.Read,FileShare.Read)) {
                    string before=Hash(held);if(options.IsChild)return Child(options,executable);
                    string token;using(var random=RandomNumberGenerator.Create()){byte[] bytes=new byte[32];random.GetBytes(bytes);token=BitConverter.ToString(bytes).Replace("-","").ToLowerInvariant();}
                    long ticks;using(var current=Process.GetCurrentProcess())ticks=current.StartTime.ToUniversalTime().Ticks;
                    var childArgs=new List<string>(options.PublicArguments());childArgs.AddRange(new[]{"--child-token",token,"--parent-pid",Process.GetCurrentProcess().Id.ToString(CultureInfo.InvariantCulture),"--parent-start-ticks",ticks.ToString(CultureInfo.InvariantCulture)});
                    string windows=Environment.GetFolderPath(Environment.SpecialFolder.Windows);
                    var env=new Dictionary<string,string>{{"SYSTEMROOT",windows},{"WINDIR",windows},{"AIBS_FIXED_PROBE_CHILD_TOKEN",token}};
                    var result=FixedRunner.Run(executable,childArgs.ToArray(),options.TimeoutMs,options.OutputBytes,env,null);
                    report["schema_version"]=1;report["attempt_id"]=options.Attempt;report["challenge"]=options.Challenge;report["mode"]=options.Mode;
                    report["guest_sid"]=identity.Sid;report["guest_username"]="aibs_vm_worker";report["standard_account"]=identity.Standard;report["administrator_group_present"]=identity.AdministratorGroup;report["medium_integrity"]=identity.Medium;
                    bool unchanged=Hash(held)==before;if(!unchanged){result.State="PROCESS_UNCERTAIN";result.Error="EXECUTABLE_CHANGED";}
                    report["guest_machine"]=identity.Machine;report["guest_identity"]=identity.Identity;report["executable_sha256"]=before;report["self_hash_revalidated"]=unchanged;
                    report["image_sha256"]=options.ImageHash;report["vm_id"]=options.VmId;report["input_sha256"]=Hash(Encoding.UTF8.GetBytes(String.Join("\n",options.PublicArguments())));
                    report["state"]=result.State;report["error_code"]=result.Error;report["child_exit_code"]=result.ExitCode;report["stdout_base64"]=Convert.ToBase64String(result.Output.Out);report["stderr_base64"]=Convert.ToBase64String(result.Output.Error);
                    report["combined_output_bytes"]=result.Output.Count;report["output_limit_bytes"]=options.OutputBytes;report["elapsed_ms"]=result.Elapsed;report["termination_confirmed"]=result.TerminationConfirmed;
                    report["child_process_id"]=result.Pid;report["child_started_utc"]=result.StartedUtc;report["process_id"]=Process.GetCurrentProcess().Id;report["process_started_utc"]=new DateTime(ticks,DateTimeKind.Utc).ToString("o");
                    report["resource_profile"]=new Dictionary<string,object>{{"process_limit",1},{"job_memory_bytes",Job.MemoryBytes},{"cpu_rate_percent",25},{"elapsed_limit_ms",options.TimeoutMs}};
                    Write(report);return result.State=="PROCESS_UNCERTAIN"?3:0;
                }
            }catch(ProbeRejected error){report.Clear();report["schema_version"]=1;report["state"]="REFUSED";report["error_code"]=error.Message;Write(report);return 2;}
            catch{report.Clear();report["schema_version"]=1;report["state"]="REFUSED";report["error_code"]="PROBE_PRECHECK_FAILED";Write(report);return 2;}
        }
        static void Write(Dictionary<string,object> report) {
            var serializer=new JavaScriptSerializer {MaxJsonLength=1500000};string json=serializer.Serialize(report);
            Options.Require(Encoding.UTF8.GetByteCount(json)<=1500000,"REPORT_BOUND_REQUIRED");Console.Out.WriteLine(json);
        }
    }
}
