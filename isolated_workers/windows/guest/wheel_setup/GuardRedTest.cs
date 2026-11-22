using System;
internal static class GuardRedTest {
    static int Main(){var facts=new WheelGuestFacts{UUID="6c5a53da-ab80-4ecb-8be6-4059266f736e",Manufacturer="innotek GmbH",Model="VirtualBox",SID="S-1-5-21-100-200-300-1000",Is64Bit=true,MediumIntegrity=true,EnabledNics=0};if(!WheelGuard.Allowed(facts)){Console.WriteLine("RED: exact offline medium-integrity guest must be admitted; guard stub rejected it.");return 1;}return 0;}
}
