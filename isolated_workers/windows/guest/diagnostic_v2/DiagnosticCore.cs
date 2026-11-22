using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Management;
using System.Security.Principal;
using System.Text.RegularExpressions;
using System.Threading;

internal sealed class GuestFacts {
    internal string UUID, Manufacturer, Model, SID;
    internal bool Is64Bit;
}
internal sealed class ProbeResult {
    internal string State="UNKNOWN",Stdout="",Stderr="";
    internal int PID,ExitCode=-1;
}
internal static class DiagnosticCore {
    internal static bool Allowed(GuestFacts f) {
        Guid id;
        return f!=null && Guid.TryParse(f.UUID,out id) && id==new Guid("6c5a53da-ab80-4ecb-8be6-4059266f736e") &&
            f.Model=="VirtualBox" && (f.Manufacturer=="innotek GmbH"||f.Manufacturer=="Oracle Corporation") && f.Is64Bit &&
            f.SID!=null && Regex.IsMatch(f.SID,@"^S-1-5-21-\d+-\d+-\d+-\d+$") &&
            !f.SID.StartsWith("S-1-5-21-2133766663-4066672948-2456486318-",StringComparison.Ordinal);
    }
    internal static ManagementObjectSearcher Search(string query) {
        var s=new ManagementObjectSearcher(query);s.Options.Timeout=TimeSpan.FromSeconds(5);return s;
    }
    internal static GuestFacts ReadFacts() {
        var f=new GuestFacts();int count=0;
        using(var search=Search("SELECT UUID FROM Win32_ComputerSystemProduct"))
        using(var rows=search.Get())foreach(ManagementObject row in rows)using(row){f.UUID=Convert.ToString(row["UUID"]);count++;}
        if(count!=1)throw new InvalidOperationException("Ambiguous system identity.");count=0;
        using(var search=Search("SELECT Manufacturer,Model FROM Win32_ComputerSystem"))
        using(var rows=search.Get())foreach(ManagementObject row in rows)using(row){f.Manufacturer=Convert.ToString(row["Manufacturer"]);f.Model=Convert.ToString(row["Model"]);count++;}
        if(count!=1)throw new InvalidOperationException("Ambiguous hardware identity.");
        using(var identity=WindowsIdentity.GetCurrent())f.SID=identity.User.Value;
        f.Is64Bit=Environment.Is64BitProcess;return f;
    }
    static string Quote(string value) {
        if(value==null||value.IndexOfAny(new char[]{'"','\0','\r','\n'})>=0)throw new ArgumentException("Unsafe probe argument.");
        return "\""+Regex.Replace(value,@"(\\+)$","$1$1")+"\"";
    }
    internal static ProbeResult Run(string executable,string[] args,int seconds,int outputLimit,Func<bool> cancel) {
        if(seconds<1||seconds>15||outputLimit<128||outputLimit>8192||!Path.IsPathRooted(executable)||Path.GetExtension(executable).ToLowerInvariant()!=".exe")throw new ArgumentException("Invalid fixed probe.");
        var quoted=new string[args.Length];for(int i=0;i<args.Length;i++)quoted[i]=Quote(args[i]);
        var r=new ProbeResult();if(cancel!=null&&cancel()){r.State="CANCELLED";return r;}
        using(var p=new Process())using(var stdout=new MemoryStream())using(var stderr=new MemoryStream()) {
            p.StartInfo=new ProcessStartInfo(executable,String.Join(" ",quoted));
            p.StartInfo.UseShellExecute=false;p.StartInfo.CreateNoWindow=true;
            p.StartInfo.RedirectStandardOutput=true;p.StartInfo.RedirectStandardError=true;
            p.StartInfo.EnvironmentVariables.Remove("PYTHONPATH");p.StartInfo.EnvironmentVariables.Remove("PYTHONHOME");
            p.StartInfo.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"]="1";
            var timer=Stopwatch.StartNew();bool started=false;
            try {
                if(!p.Start())throw new InvalidOperationException("Probe did not start.");started=true;r.PID=p.Id;
                var ob=new byte[1024];var eb=new byte[1024];var os=p.StandardOutput.BaseStream;var es=p.StandardError.BaseStream;
                var ot=os.ReadAsync(ob,0,ob.Length);var et=es.ReadAsync(eb,0,eb.Length);bool oo=true,eo=true;
                while(oo||eo||!p.HasExited) {
                    if(cancel!=null&&cancel()){r.State="CANCELLED";break;}
                    if(timer.Elapsed.TotalSeconds>=seconds){r.State="TIMEOUT";break;}
                    if(oo&&ot.IsCompleted) {
                        int n=ot.GetAwaiter().GetResult();if(n==0)oo=false;
                        else {if(stdout.Length+stderr.Length+n>outputLimit){r.State="OUTPUT_LIMIT";break;}stdout.Write(ob,0,n);ot=os.ReadAsync(ob,0,ob.Length);}
                    }
                    if(eo&&et.IsCompleted) {
                        int n=et.GetAwaiter().GetResult();if(n==0)eo=false;
                        else {if(stdout.Length+stderr.Length+n>outputLimit){r.State="OUTPUT_LIMIT";break;}stderr.Write(eb,0,n);et=es.ReadAsync(eb,0,eb.Length);}
                    }
                    Thread.Sleep(10);
                }
                if(r.State=="UNKNOWN"&&p.WaitForExit(1000)){r.State="EXITED";r.ExitCode=p.ExitCode;}
            } finally {
                if(started&&!p.HasExited){try{p.Kill();p.WaitForExit(1000);}catch{}}
                r.Stdout=Encoding.UTF8.GetString(stdout.ToArray());r.Stderr=Encoding.UTF8.GetString(stderr.ToArray());
                timer.Stop();
            }
        }return r;
    }
    static void EmitProbe(Action<string> log,string name,string path,string[] args,Func<bool> cancel) {
        log(name+": "+path);
        if(!File.Exists(path)){log("  NOT FOUND");return;}
        var node=new FileInfo(path);for(FileSystemInfo current=node;current!=null;) {
            if((current.Attributes&FileAttributes.ReparsePoint)!=0){log("  REJECTED: linked path");return;}
            current=current is FileInfo?((FileInfo)current).Directory:((DirectoryInfo)current).Parent;
        }
        var r=Run(path,args,10,8192,cancel);log("  State="+r.State+"; Exit="+r.ExitCode);
        if(r.Stdout.Length>0)log(r.Stdout.TrimEnd());if(r.Stderr.Length>0)log(r.Stderr.TrimEnd());
        if(r.State!="EXITED")log("  Probe failed; descendant termination and task authority are not established.");
    }
    internal static void Collect(Action<string> log,Func<bool> cancel) {
        // Recheck real identity immediately before any native runtime probe.
        if(!Allowed(ReadFacts()))throw new InvalidOperationException("Wrong guest.");
        log("AI-BS GUEST CHECK v2 | "+DateTime.UtcNow.ToString("o"));
        log("Read-only checks. No installation, activation, network or security-setting changes.");
        log("Exact dedicated guest identity: matched. Task admission: DISABLED.");
        using(var s=Search("SELECT Caption,Version,BuildNumber FROM Win32_OperatingSystem"))
        using(var rows=s.Get())foreach(ManagementObject row in rows)using(row)log("OS: "+row["Caption"]+" | "+row["Version"]+" | build "+row["BuildNumber"]);
        EmitProbe(log,"NODE","C:\\Program Files\\nodejs\\node.exe",new string[]{"--version"},cancel);
        string[] paths={@"C:\Program Files\Python313\python.exe",@"C:\Program Files\AIBSPython313\python.exe",Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"Programs\Python\Python313\python.exe")};
        int found=0;
        foreach(var path in paths) {
            if(cancel())return;if(!File.Exists(path))continue;found++;
            EmitProbe(log,"PYTHON VERSION",path,new string[]{"-I","-B","--version"},cancel);
            EmitProbe(log,"WHEEL IMPORTS",path,new string[]{"-I","-B","-c","import sys, psutil, win32api; from importlib.metadata import version; print('Python='+sys.version.split()[0]+'; pywin32='+version('pywin32')+'; psutil='+version('psutil'))"},cancel);
        }
        if(found==0)log("PYTHON: NOT FOUND in the three expected locations.");
        if(found>1)log("Multiple Python locations found: reconcile before selecting a worker runtime.");
        if(cancel())return;log("WINDOWS LICENSING (raw status; no keys collected/displayed):");int licenseRows=0;
        using(var s=Search(LicensingFields.Query))
        using(var rows=s.Get())foreach(ManagementObject row in rows)using(row){licenseRows++;log(Convert.ToString(row["Name"])+" | LicenseStatus="+row["LicenseStatus"]+" | GraceMinutes="+row["GracePeriodRemaining"]+LicensingFields.ExtraFields(delegate(string name){return row[name];}));}
        if(licenseRows==0)log("No matching licensing row. Activation/licensing remains UNVERIFIED.");
        log("CHECKS FINISHED. Results do not establish containment acceptance or task authority.");
    }
}
