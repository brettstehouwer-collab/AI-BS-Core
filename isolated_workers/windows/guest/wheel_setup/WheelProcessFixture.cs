using System;
using System.Threading;
internal static class WheelProcessFixture {
    static int Main(string[] args){
        if(args.Length==1&&args[0]=="overflow"){Console.Write(new string('x',32768));Console.Error.Write(new string('y',32768));return 0;}
        if(args.Length==1&&args[0]=="sleep"){Thread.Sleep(10000);return 0;}
        if(args.Length==3&&args[0]=="normal"){Console.Write(args[1]+"|"+args[2]);Console.Error.Write("fixture error");return 7;}
        return 64;
    }
}
