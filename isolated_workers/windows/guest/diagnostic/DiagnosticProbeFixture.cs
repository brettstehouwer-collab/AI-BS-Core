using System;
using System.Threading;
internal static class DiagnosticProbeFixture {
    static int Main(string[] args) {
        if(args[0]=="sleep"){Thread.Sleep(10000);return 0;}
        if(args[0]=="overflow"){Console.Write(new string('x',10000));return 0;}
        Console.Write("probe");Console.Error.Write("diagnostic");return 7;
    }
}
