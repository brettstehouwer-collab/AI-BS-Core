using System;
using System.Drawing;
using System.Threading;
using System.Windows.Forms;

internal sealed class WheelSetupWindow : Form {
    readonly TextBox report=new TextBox();readonly Button install=new Button();
    readonly WheelCompletion completion=new WheelCompletion();
    bool running,closeRequested,outputFull;
    internal int ExitCode {get{return completion.ExitCode;}}
    internal WheelSetupWindow(){
        Text="AI-BS Offline Wheel Setup v1";Width=960;Height=710;StartPosition=FormStartPosition.CenterScreen;
        var layout=new TableLayoutPanel();layout.Dock=DockStyle.Fill;layout.ColumnCount=1;layout.RowCount=3;
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,112));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,44));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));Controls.Add(layout);
        var info=new Label();info.AutoSize=false;info.Dock=DockStyle.Fill;
        info.Text="Target: "+WheelPaths.Python()+Environment.NewLine+"Required: Python 3.13.17 x64 | psutil 7.2.2 | pywin32 312"+Environment.NewLine+
            "Offline D: CD-ROM only. One human-started attempt; retained intent blocks replay."+Environment.NewLine+"No elevation, Python/Node reinstall, task admission, network or Windows-setting changes.";
        info.Padding=new Padding(10);layout.Controls.Add(info,0,0);
        install.Text="Install approved wheels once";install.Dock=DockStyle.Fill;layout.Controls.Add(install,0,1);
        report.Multiline=true;report.ReadOnly=true;report.ScrollBars=ScrollBars.Both;report.WordWrap=true;report.Dock=DockStyle.Fill;
        report.Font=new Font("Consolas",10);report.MaxLength=36000;layout.Controls.Add(report,0,2);
        install.Click+=delegate{
            if(!completion.Start())return;install.Enabled=false;running=true;
            Append("Human Install action received. Checking the exact offline guest, target and pinned media.");
            ThreadPool.QueueUserWorkItem(delegate{
                WheelOutcome outcome=WheelOutcome.Failed;
                try{outcome=WheelInstall.Execute(Append,completion,Application.ExecutablePath);}
                catch(Exception){Append("REFUSED before native setup: guest/media/profile/lease prerequisite failed. No automatic retry is available. Preserve the displayed report for review.");}
                finally{var finalOutcome=outcome;try{BeginInvoke(new Action(delegate{if(!completion.IsFinished)completion.Complete(finalOutcome);running=false;if(closeRequested)Close();}));}catch(InvalidOperationException){}}
            });
        };
        FormClosing+=delegate(object sender,FormClosingEventArgs e){if(running&&completion.RequestCancel()){closeRequested=true;e.Cancel=true;Append("Cancellation accepted before verified commit. Stopping the client; the attempt remains quarantined. Waiting for bounded shutdown.");}};
    }
    void Append(string text){
        if(IsDisposed)return;
        try{BeginInvoke(new Action(delegate{
            if(IsDisposed||outputFull)return;int remaining=35000-report.TextLength;
            string line=text+Environment.NewLine;
            if(line.Length>remaining){report.AppendText(line.Substring(0,Math.Max(0,remaining)));report.AppendText(Environment.NewLine+"[Display limit reached; no further output displayed.]");outputFull=true;}
            else report.AppendText(line);
        }));}catch(InvalidOperationException){}
    }
}
internal static class WheelSetupApplication {
    [STAThread] static int Main(string[] args){
        bool identityOnly=args.Length==1&&args[0]=="--check-identity";
        if(args.Length!=0&&!identityOnly)return 64;
        // Every production route uses only real machine facts. There is no injected identity,
        // path, command, test bypass, or GUI on a refused host. No application writes precede this.
        bool allowed=false;try{allowed=WheelGuard.Allowed(WheelGuard.ReadFacts());}catch{}
        if(!allowed)return 2;if(identityOnly)return 0;
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        using(var window=new WheelSetupWindow()){Application.Run(window);return window.ExitCode;}
    }
}
