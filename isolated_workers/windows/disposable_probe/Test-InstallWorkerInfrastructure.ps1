# Read/parse/pure-transform infrastructure checks. No VM, account or ACL mutations.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$checks=0
function Check([bool]$Condition,[string]$Name){if(-not $Condition){throw ('FAILED_'+$Name)};$script:checks++;Write-Output ('PASS '+$Name)}
$install=Join-Path $PSScriptRoot 'Install-WorkerOS.ps1'
$bootstrap=Join-Path $PSScriptRoot 'Bootstrap-GuestProbe.ps1'
$asts=@()
foreach($path in @($install,$bootstrap)){
 $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
 Check (@($errors).Count -eq 0) ('parse_'+[IO.Path]::GetFileName($path));$asts+=,$ast
}
# Import only the three pure validation functions; neither script entry runs.
$pure=@('Require','Machine-Map','Verify-NewMachine')
foreach($name in $pure){
 $node=$asts[0].Find({param($a)$a -is [Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -ceq $name},$true)
 Check ($null -ne $node) ('pure_function_'+$name)
 . ([scriptblock]::Create($node.Extent.Text))
}
$vm='e5a2fe34-7b90-460c-83af-903d51b4bb16'
$fixture=@(('UUID="'+$vm+'"'),'name="AI-BS-DisposableProbe-20261026"','VMState="poweroff"','memory=4096','cpus=4','firmware="EFI"','SecureBoot="on"','clipboard="disabled"','clipboard_file_transfers="off"','draganddrop="disabled"','vrde="off"','usb="off"','audio="none"','audio_in="off"','audio_out="off"')
foreach($n in 1..8){$fixture+='nic'+$n+'="none"'};foreach($n in 1..4){$fixture+='uart'+$n+'="off"'}
$text=$fixture -join "`n";$map=Machine-Map $text;Verify-NewMachine $map;Check $true 'exact_offline_machine_profile'
foreach($mutation in @(@('UUID',$vm,'6c5a53da-ab80-4ecb-8be6-4059266f736e'),@('VMState','poweroff','running'),@('memory','4096','8192'),@('SecureBoot','on','off'),@('nic1','none','nat'),@('clipboard','disabled','bidirectional'),@('clipboard_file_transfers','off','on'),@('uart1','off','server'),@('usb','off','on'),@('audio','none','was'))){
 $bad=Machine-Map $text;$bad[$mutation[0]]=$mutation[2];$rejected=$false
 try{Verify-NewMachine $bad}catch{$rejected=$true}
 Check $rejected ('reject_changed_'+$mutation[0])
}
$bad=Machine-Map $text;$bad.Add('SharedFolderNameMachineMapping1','private');$rejected=$false;try{Verify-NewMachine $bad}catch{$rejected=$true};Check $rejected 'reject_shared_folder'
$rejected=$false;try{$null=Machine-Map ($text+"`nUUID=`"$vm`"")}catch{$rejected=$true};Check $rejected 'reject_duplicate_machine_property'
$template='C:\Program Files\Oracle\VirtualBox\UnattendedTemplates\win_nt6_unattended.xml'
$digest=(Get-FileHash -LiteralPath $template -Algorithm SHA256).Hash.ToLowerInvariant()
Check ($digest -ceq '312555562d8b55e550ee22a71e33eb25133b3217e527a2df94a78a1702064970') 'reviewed_oracle_template_pin'
[xml]$xml=[IO.File]::ReadAllText($template);$ns=[Xml.XmlNamespaceManager]::new($xml.NameTable);$ns.AddNamespace('u','urn:schemas-microsoft-com:unattend')
$nodes=@($xml.SelectNodes('//u:RunAsynchronous[u:RunAsynchronousCommand/u:Path[contains(text(),"LabConfig")]]',$ns));Check ($nodes.Count -eq 2) 'two_original_bypass_blocks'
Check (@($xml.SelectNodes('//u:Path[contains(text(),"Bypass")]',$ns)).Count -eq 10) 'ten_original_bypass_commands'
foreach($node in $nodes){$null=$node.ParentNode.RemoveChild($node)}
Check ($xml.OuterXml -notmatch 'Bypass(CPU|RAM|SecureBoot|Storage|TPM)Check|LabConfig') 'all_hardware_bypasses_removed'
Check (@($xml.SelectNodes('//u:WillWipeDisk',$ns)).Count -eq 1) 'new_disposable_disk_install_retained'
Check ([regex]::Matches($xml.OuterXml,'@@VBOX_').Count -eq 32) 'virtualbox_substitution_tokens_preserved'
$count=$xml.CreateElement('LogonCount','urn:schemas-microsoft-com:unattend');$count.InnerText='1';$null=$xml.SelectSingleNode('//u:AutoLogon',$ns).AppendChild($count)
Check ($xml.SelectSingleNode('//u:AutoLogon/u:LogonCount',$ns).InnerText -ceq '1') 'one_bootstrap_auto_logon'
# Parse the generated fixed guest setup snippets without invoking them.
$snippets=@($asts[0].FindAll({param($a)$a -is [Management.Automation.Language.StringConstantExpressionAst] -and $a.Value.StartsWith('powershell.exe -NoProfile -NonInteractive -Command "')},$true))
Check ($snippets.Count -eq 2) 'two_fixed_guest_setup_snippets'
foreach($snippet in $snippets){$raw=$snippet.Value;$start=$raw.IndexOf(' -Command "')+11;$code=$raw.Substring($start,$raw.Length-$start-1);$tokens=$null;$errors=$null;[Management.Automation.Language.Parser]::ParseInput($code,[ref]$tokens,[ref]$errors)|Out-Null;Check (@($errors).Count -eq 0) 'guest_setup_snippet_parses';Check ($raw.Length -lt 8191) 'guest_setup_command_line_bound'}
$bytes=[IO.File]::ReadAllBytes($bootstrap);$encoded=[Convert]::ToBase64String($bytes);$parts=@();for($i=0;$i -lt $encoded.Length;$i+=120){$parts+=$encoded.Substring($i,[Math]::Min(120,$encoded.Length-$i))}
Check ([Convert]::ToBase64String([Convert]::FromBase64String(($parts -join "`r`n"))) -ceq $encoded) 'chunked_bootstrap_bytes_roundtrip'
Check (@($parts|Where-Object{$_.Length -gt 120}).Count -eq 0) 'chunked_media_lines_bounded'
[pscustomobject]@{schema_version=1;infrastructure_checks_passed=$checks;guest_bootstrap_executed=$false;installer_entry_executed=$false;vm_operations=0;account_mutations=0;acl_mutations=0}|ConvertTo-Json
