using System;
using System.IO;
using System.Diagnostics;
internal static class GuestDiagnosticsTests {
    static int passed;
    static void Check(string name, bool ok) { if(!ok) throw new Exception(name); passed++; Console.WriteLine("PASS "+name); }
    static GuestFacts Facts() { return new GuestFacts { UUID="6c5a53da-ab80-4ecb-8be6-4059266f736e", Model="VirtualBox", Manufacturer="innotek GmbH", SID="S-1-5-21-100-200-300-1000", Is64Bit=true }; }
    static int Main(string[] args) {
        Check("exact guest admitted", DiagnosticCore.Allowed(Facts()));
        var f=Facts(); f.UUID="00000000-0000-0000-0000-000000000000"; Check("other UUID rejected",!DiagnosticCore.Allowed(f));
        f=Facts();f.Model="Desktop";Check("host model rejected",!DiagnosticCore.Allowed(f));
        f=Facts();f.Manufacturer="Unknown";Check("unknown manufacturer rejected",!DiagnosticCore.Allowed(f));
        f=Facts();f.SID="S-1-5-21-2133766663-4066672948-2456486318-1001";Check("host operator rejected",!DiagnosticCore.Allowed(f));
        f=Facts();f.SID="S-1-5-21-2133766663-4066672948-2456486318-1005";Check("host worker rejected",!DiagnosticCore.Allowed(f));
        f=Facts();f.Is64Bit=false;Check("32-bit process rejected",!DiagnosticCore.Allowed(f));
        Check("missing facts rejected",!DiagnosticCore.Allowed(null));
        f=Facts();f.SID=null;Check("missing account observation rejected",!DiagnosticCore.Allowed(f));
        f=Facts();f.UUID="{6C5A53DA-AB80-4ECB-8BE6-4059266F736E}";Check("equivalent UUID representation admitted",DiagnosticCore.Allowed(f));
        f=Facts();f.Manufacturer="Oracle Corporation";Check("known Oracle identity admitted",DiagnosticCore.Allowed(f));
        var r=DiagnosticCore.Run(args[0],new string[]{"normal"},5,512,null);
        Check("actual nonzero exit retained",r.State=="EXITED"&&r.ExitCode==7);
        Check("actual streams retained",r.Stdout=="probe"&&r.Stderr=="diagnostic");
        r=DiagnosticCore.Run(args[0],new string[]{"overflow"},5,128,null);
        Check("actual combined output bound",r.State=="OUTPUT_LIMIT"&&r.Stdout.Length+r.Stderr.Length<=128);
        var sw=Stopwatch.StartNew();r=DiagnosticCore.Run(args[0],new string[]{"sleep"},1,128,null);
        Check("actual deadline enforced",r.State=="TIMEOUT"&&sw.Elapsed.TotalSeconds<5);
        r=DiagnosticCore.Run(args[0],new string[]{"sleep"},5,128,delegate{return true;});
        Check("cancellation refuses execution",r.State=="CANCELLED");
        bool rejected=false;try{DiagnosticCore.Run(args[0],new string[]{"bad\"argument"},5,128,null);}catch(ArgumentException){rejected=true;}
        Check("unsafe argument rejected",rejected);
        Console.WriteLine("RESULT "+passed+" infrastructure tests passed; no runtime installers or project checks executed.");return 0;
    }
}
