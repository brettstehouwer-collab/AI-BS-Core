# Fixed standard-host-account operation. No parameters or arbitrary command dispatch.
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
$plan=Get-Content -LiteralPath (Join-Path $root 'policy\provisioning.json') -Raw|ConvertFrom-Json
$identity=[Security.Principal.WindowsIdentity]::GetCurrent();$principal=[Security.Principal.WindowsPrincipal]$identity
if($identity.User.Value -cne $plan.dispatcher_sid -or $principal.IsInRole('Administrators')){throw 'EXACT_STANDARD_HOST_LAUNCHER_REQUIRED'}
if($plan.vm_uuid -eq '6c5a53da-ab80-4ecb-8be6-4059266f736e' -or $plan.vm_name -cne 'AI-BS-DisposableProbe-20261026'){throw 'INTEGRATION_GUEST_REFUSED'}
$env:VBOX_USER_HOME=$plan.vbox_user_home
$log=Join-Path $root 'worker_outputs\provisioning.jsonl'
function Log($object){[IO.File]::AppendAllText($log,(($object|ConvertTo-Json -Depth 8 -Compress)+"`n"),[Text.UTF8Encoding]::new($false))}
function VBox([string[]]$Arguments,[int]$Seconds=120){
 if((Get-FileHash -LiteralPath $plan.vbox_path).Hash.ToLowerInvariant() -cne $plan.vbox_sha256){throw 'HYPERVISOR_CHANGED'}
 $s=[Diagnostics.ProcessStartInfo]::new($plan.vbox_path);$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true
 foreach($a in $Arguments){$s.ArgumentList.Add($a)}
 $p=[Diagnostics.Process]::new();$p.StartInfo=$s
 Log ([ordered]@{phase='intent';utc=[DateTime]::UtcNow.ToString('o');arguments=$Arguments})
 if(-not $p.Start()){throw 'CHILD_START_FAILED'};$o=$p.StandardOutput.ReadToEndAsync();$e=$p.StandardError.ReadToEndAsync()
 if(-not $p.WaitForExit($Seconds*1000)){try{$p.Kill($true)}catch{};throw 'OWNED_VBOX_COMMAND_TIMEOUT'}
 $stdout=$o.GetAwaiter().GetResult();$stderr=$e.GetAwaiter().GetResult()
 if($stdout.Length+$stderr.Length -gt 1048576){throw 'VBOX_OUTPUT_LIMIT'}
 Log ([ordered]@{phase='result';utc=[DateTime]::UtcNow.ToString('o');arguments=$Arguments;exit=$p.ExitCode;stdout=$stdout;stderr=$stderr})
 if($p.ExitCode -ne 0){throw ('VBOX_FAILED_'+$p.ExitCode)};return $stdout
}
$lease=[IO.File]::Open((Join-Path $root 'worker_state\provision.lease'),'CreateNew','ReadWrite','None')
try{
 if((Get-PSDrive E).Free -lt 104GB){throw 'STORAGE_PROFILE_CHANGED'}
 $vms=VBox @('list','vms');if($vms.Trim()){throw 'NEW_REGISTRY_NOT_EMPTY'}
 $id=$plan.vm_uuid
 VBox @('createvm',('--name='+$plan.vm_name),'--platform-architecture=x86',('--basefolder='+$plan.store),'--ostype=Windows11_64',('--uuid='+$id),'--register')|Out-Null
 $args=@('modifyvm',$id,'--memory=8192','--cpus=4','--acpi=on','--ioapic=on','--firmware=efi','--tpm-type=2.0','--graphicscontroller=vboxsvga','--accelerate-3d=off','--vram=128','--mouse=ps2','--keyboard=ps2','--clipboard-mode=disabled','--clipboard-file-transfers=disabled','--drag-and-drop=disabled','--usb-ohci=off','--usb-ehci=off','--usb-xhci=off','--usb-card-reader=off','--audio-enabled=off','--audio-in=off','--audio-out=off','--vrde=off','--uart1=off','--uart2=off','--uart3=off','--uart4=off','--boot1=dvd','--boot2=disk','--boot3=none','--boot4=none')
 foreach($n in 1..8){$args+=('--nic'+$n+'=none')};VBox $args|Out-Null
 VBox @('modifynvram',$id,'inituefivarstore')|Out-Null
 VBox @('modifynvram',$id,'enrollmssignatures')|Out-Null
 VBox @('modifynvram',$id,'enrollorclpk')|Out-Null
 VBox @('modifynvram',$id,'secureboot','--enable')|Out-Null
 $disk=Join-Path $plan.store 'system.vdi'
 VBox @('createmedium','disk',('--filename='+$disk),'--size=65536','--format=VDI','--variant=Fixed') 1200|Out-Null
 if((Get-PSDrive E).Free -lt 40GB){throw 'STORAGE_RESERVE_FAILED'}
 VBox @('storagectl',$id,'--name=SATA','--add=sata','--controller=IntelAhci','--portcount=2','--bootable=on','--hostiocache=off')|Out-Null
 VBox @('storageattach',$id,'--storagectl=SATA','--port=0','--device=0','--type=hdd',('--medium='+$disk),'--nonrotational=on')|Out-Null
 VBox @('storageattach',$id,'--storagectl=SATA','--port=1','--device=0','--type=dvddrive',('--medium='+$plan.iso_path),'--passthrough=off')|Out-Null
 $info=VBox @('showvminfo',$id,'--machinereadable')
 [IO.File]::WriteAllText((Join-Path $root 'worker_outputs\prepared_vm.txt'),$info)
 Log ([ordered]@{state='NEW_VM_PREPARED_POWERED_OFF';vm_uuid=$id;host_sid=$identity.User.Value;standard_host_account=$true;disk_bytes=(Get-Item -LiteralPath $disk).Length;reserve_bytes=(Get-PSDrive E).Free;integration_modified=$false})
}catch{Log ([ordered]@{state='FAILED_RETAINED';error_type=$_.Exception.GetType().Name;message=$_.Exception.Message});throw}finally{$lease.Dispose()}
