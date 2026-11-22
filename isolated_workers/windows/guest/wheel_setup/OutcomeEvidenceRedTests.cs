using System;
using System.IO;
internal static class OutcomeEvidenceRedTests {
    static int Main(string[] args){
        int failures=0;var completion=new WheelCompletion();
        if(completion.ExitCode==0){Console.WriteLine("RED: close before Install incorrectly reports success.");failures++;}
        string root=Path.GetFullPath(args[0]);Directory.CreateDirectory(root);
        using(var attempt=WheelAttempt.Begin(root,"FIXED_TEST_TARGET")){
            attempt.RecordStep(WheelStep.RUNTIME_BEFORE,new WheelProcessResult{State="EXITED",ExitCode=7,ExitCodeKnown=true,Stdout="bounded stdout",Stderr="bounded stderr",OutputBytes=28,OutputLimit=128,DeadlineSeconds=1});
            if(!File.Exists(Path.Combine(root,"step-01-RUNTIME_BEFORE.json"))){Console.WriteLine("RED: bounded native result was not persisted.");failures++;}
        }
        Console.WriteLine("Behavioral red failures="+failures);return failures==2?1:0;
    }
}
