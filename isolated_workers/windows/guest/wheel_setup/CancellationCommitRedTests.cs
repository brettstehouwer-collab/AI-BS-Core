using System;
using System.IO;
internal static class CancellationCommitRedTests {
    static int Main(string[] args){
        string root=Path.GetFullPath(args[0]);Directory.CreateDirectory(root);var completion=new WheelCompletion();completion.Start();completion.RequestCancel();
        using(var attempt=WheelAttempt.Begin(root,"FIXED_TEST_TARGET")){
            bool refused=false;try{WheelInstall.CommitVerified(completion,attempt,"FIXED_VERIFIED_REASON");}catch(IOException){refused=true;}
            if(!refused||completion.ExitCode==0||File.Exists(Path.Combine(root,"attempt.result.json"))){Console.WriteLine("RED: accepted cancellation did not prevent the shared production VERIFIED commit.");return 1;}
        }
        Console.WriteLine("GREEN: accepted cancellation prevents shared production VERIFIED commit.");return 0;
    }
}
