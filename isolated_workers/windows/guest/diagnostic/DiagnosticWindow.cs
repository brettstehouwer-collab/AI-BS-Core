using System;
using System.Threading;
using System.Windows.Forms;
using System.Drawing;
internal sealed class GuestCheckWindow : Form {
    readonly TextBox report=new TextBox();volatile bool cancelled;
    internal GuestCheckWindow() {
        Text="AI-BS Guest Check - read-only";Width=900;Height=680;StartPosition=FormStartPosition.CenterScreen;
        report.Multiline=true;report.ReadOnly=true;report.ScrollBars=ScrollBars.Both;report.WordWrap=true;
        report.Dock=DockStyle.Fill;report.Font=new Font("Consolas",10);Controls.Add(report);
        var info=new Label();info.Text="Offline guest diagnostic | No setup changes | Close this window to stop";info.Dock=DockStyle.Top;info.Height=30;Controls.Add(info);
        FormClosing+=delegate{cancelled=true;};
        Shown+=delegate{ThreadPool.QueueUserWorkItem(delegate{
            try{DiagnosticCore.Collect(Append,delegate{return cancelled;});}
            catch(Exception e){Append("CHECK FAILED: "+e.GetType().Name+". Guest state remains unverified.");}
        });};
    }
    void Append(string text) {
        if(cancelled||IsDisposed)return;
        try{BeginInvoke(new Action(delegate{if(!IsDisposed&&report.TextLength<60000)report.AppendText(text+Environment.NewLine);}));}catch(InvalidOperationException){}
    }
}
internal static class GuestCheckApplication {
    [STAThread] static int Main(string[] args) {
        bool check=args.Length==1&&args[0]=="--check-identity";
        if(args.Length>0&&!check)return 64;
        bool allowed=false;try{allowed=DiagnosticCore.Allowed(DiagnosticCore.ReadFacts());}catch{}
        if(!allowed){if(!check)MessageBox.Show("Wrong guest. This tool refuses the host and any other VM. No runtime probes were started.","AI-BS Guest Check");return 2;}
        if(check)return 0;
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new GuestCheckWindow());return 0;
    }
}
