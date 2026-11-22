# PowerShell 7 only. Fixed infrastructure diagnostic; never a candidate executor.
# Invoke-WorkerTransport.ps1 is the separately registered limited-account entry.
# Broker functions run only as the pinned host controller and never launch VBox.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:Root = 'C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
$script:IntegrationUUID = '6c5a53da-ab80-4ecb-8be6-4059266f736e'
$script:WorkerUUID = 'e5a2fe34-7b90-460c-83af-903d51b4bb16'
$script:DispatcherSID = 'S-1-5-21-2133766663-4066672948-2456486318-1006'
$script:StorageRoot = 'E:\AI-BS-DisposableProbe-v1'
$script:ControllerSID = 'S-1-5-21-2133766663-4066672948-2456486318-1001'
$script:HostSIDPrefix = 'S-1-5-21-2133766663-4066672948-2456486318-'
$script:TrustedWriters = @('S-1-5-18','S-1-5-32-544',$script:ControllerSID)
$script:Held = [Collections.Generic.List[IDisposable]]::new()
if(-not ('AIBSProbeHost.Native' -as [type])){
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.Principal;
using Microsoft.Win32.SafeHandles;
namespace AIBSProbeHost {
 public static class Native {
  [StructLayout(LayoutKind.Sequential)] struct FileInfo { public uint Attributes; public System.Runtime.InteropServices.ComTypes.FILETIME Creation,Access,Write; public uint Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow; }
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle h,out FileInfo i);
  [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenProcessToken(IntPtr p,uint access,out SafeAccessTokenHandle token);
  [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetTokenInformation(SafeAccessTokenHandle token,int kind,IntPtr buffer,int length,out int needed);
  [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
  public static uint Links(SafeFileHandle handle){ FileInfo i; if(!GetFileInformationByHandle(handle,out i))throw new Win32Exception(); return i.Links; }
  public static string ProcessSID(IntPtr process){ SafeAccessTokenHandle token; if(!OpenProcessToken(process,8,out token))throw new Win32Exception(); using(token)using(var identity=new WindowsIdentity(token.DangerousGetHandle()))return identity.User.Value; }
  public static string IntegritySID(){ SafeAccessTokenHandle token; if(!OpenProcessToken(GetCurrentProcess(),8,out token))throw new Win32Exception(); using(token){ int size;GetTokenInformation(token,25,IntPtr.Zero,0,out size);IntPtr p=Marshal.AllocHGlobal(size);try{if(!GetTokenInformation(token,25,p,size,out size))throw new Win32Exception();return new SecurityIdentifier(Marshal.ReadIntPtr(p)).Value;}finally{Marshal.FreeHGlobal(p);}} }
 }
}
'@
}

function Fail([string]$Code) { throw [InvalidOperationException]::new($Code) }
function Require([bool]$Condition,[string]$Code) { if(-not $Condition){ Fail $Code } }
function Hash-Bytes([byte[]]$Bytes) { [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Bytes)).ToLowerInvariant() }
function Hash-Text([string]$Text) { Hash-Bytes ([Text.Encoding]::UTF8.GetBytes($Text)) }
function Is-Digest($Value) { $Value -is [string] -and $Value -cmatch '\A[0-9a-f]{64}\z' }
function Is-ID($Value) { $Value -is [string] -and $Value -cmatch '\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z' }
function Fixed-Path([string]$Relative) { Join-Path $script:Root $Relative }
function Canonical($Value) {
    if($Value -is [Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach($name in @($Value.Keys | Sort-Object -CaseSensitive)) { $ordered[$name] = Canonical $Value[$name] }
        return ,$ordered
    }
    if($null -ne $Value -and $Value -is [Collections.IEnumerable] -and $Value -isnot [string]) {
        $items = @(); foreach($item in $Value) { $items += ,(Canonical $item) }; return ,$items
    }
    return $Value
}
function JSON($Value) { ConvertTo-Json -InputObject (Canonical $Value) -Depth 24 -Compress }
function Read-StrictJSON([byte[]]$Bytes,[int]$Maximum=262144) {
    Require ($Bytes.Length -gt 0 -and $Bytes.Length -le $Maximum) 'JSON_SIZE_BOUND'
    $utf8 = [Text.UTF8Encoding]::new($false,$true)
    $raw = $utf8.GetString($Bytes)
    $doc = [Text.Json.JsonDocument]::Parse($raw)
    try {
        function Convert-Element($Element,[int]$Depth) {
            Require ($Depth -le 20) 'JSON_DEPTH_BOUND'
            switch($Element.ValueKind.ToString()) {
                Object {
                    $map = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
                    foreach($property in $Element.EnumerateObject()) {
                        Require (-not $map.ContainsKey($property.Name)) 'DUPLICATE_JSON_KEY'
                        $map.Add($property.Name,(Convert-Element $property.Value ($Depth+1)))
                    }
                    return ,$map
                }
                Array { $values=@(); foreach($item in $Element.EnumerateArray()){ $values += ,(Convert-Element $item ($Depth+1)) }; return ,$values }
                String { return $Element.GetString() }
                Number { $integer=0L; Require ($Element.TryGetInt64([ref]$integer)) 'INTEGER_JSON_REQUIRED'; return $integer }
                True { return $true }
                False { return $false }
                Null { return $null }
                default { Fail 'JSON_TYPE_REFUSED' }
            }
        }
        $result = Convert-Element $doc.RootElement 0
        Require ($result -is [Collections.IDictionary]) 'JSON_OBJECT_REQUIRED'
        return ,$result
    } finally { $doc.Dispose() }
}
function Assert-Fields($Value,[string[]]$Names,[string]$Code) {
    Require ($Value -is [Collections.IDictionary]) $Code
    Require (@($Value.Keys).Count -eq $Names.Count) $Code
    foreach($name in $Names){ Require (([Collections.IDictionary]$Value).Contains($name)) $Code }
}
function UTC($Value) {
    Require ($Value -is [string] -and $Value -cmatch '\A\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}Z\z') 'EXPLICIT_UTC_REQUIRED'
    return [DateTime]::ParseExact($Value,'yyyy-MM-ddTHH:mm:ss.fffffffZ',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::AdjustToUniversal -bor [Globalization.DateTimeStyles]::AssumeUniversal)
}
function Now-UTC { [DateTime]::UtcNow }
function New-File([string]$Path,[byte[]]$Bytes) {
    $stream = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $stream.Write($Bytes,0,$Bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}
function New-JSON([string]$Path,$Value) { New-File $Path ([Text.Encoding]::UTF8.GetBytes((JSON $Value))) }
function Read-Bytes([string]$Path,[long]$Maximum,[string]$ExpectedHash='') {
    $stream = [IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        Require ([AIBSProbeHost.Native]::Links($stream.SafeFileHandle) -eq 1) 'HARDLINK_REFUSED'
        Require ($stream.Length -ge 0 -and $stream.Length -le $Maximum) 'FILE_SIZE_BOUND'
        $buffer = [byte[]]::new([int]$stream.Length); $used=0
        while($used -lt $buffer.Length){ $read=$stream.Read($buffer,$used,$buffer.Length-$used); Require ($read -gt 0) 'SHORT_READ'; $used += $read }
        if($ExpectedHash){ Require ((Hash-Bytes $buffer) -ceq $ExpectedHash) 'PINNED_BYTES_CHANGED' }
        $script:Held.Add($stream); $stream=$null
        return ,$buffer
    } finally { if($null -ne $stream){ $stream.Dispose() } }
}
function Close-Held { foreach($stream in $script:Held){ $stream.Dispose() }; $script:Held.Clear() }

function Assert-Path([string]$Path,[string[]]$Writers=$script:TrustedWriters,[switch]$External) {
    Require ($Path -cmatch '\A[A-Z]:\\' -and [IO.Path]::GetFullPath($Path) -ceq $Path -and $Path.Substring(2) -notmatch '[:\x00\r\n]') 'CANONICAL_LOCAL_PATH_REQUIRED'
    if(-not $External){ Require ($Path -ceq $script:Root -or $Path.StartsWith($script:Root+'\',[StringComparison]::Ordinal)) 'FIXED_ROOT_REQUIRED' }
    $item = Get-Item -LiteralPath $Path -Force
    $current = $item
    while($null -ne $current) {
        Require (($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH_REFUSED'
        $acl = Get-Acl -LiteralPath $current.FullName
        $within = $current.FullName -ceq $script:Root -or $current.FullName.StartsWith($script:Root+'\',[StringComparison]::Ordinal)
        $allowed = if($within){ $Writers } else { @($script:TrustedWriters)+'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464' }
        Require ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cin $allowed) 'UNTRUSTED_PATH_OWNER'
        $mask = if($within -or $current.FullName -ceq $item.FullName){ 0xD0156L } else { 0xD0040L }
        # A volume root cannot itself be renamed/deleted. DELETE_CHILD/DACL/owner remain critical.
        if($current -is [IO.DirectoryInfo] -and $null -eq $current.Parent){$mask=$mask -band (-bnot 0x10000L)}
        foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
            if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){ continue }
            if($ace.AccessControlType -eq 'Allow' -and ([long]$ace.FileSystemRights -band $mask) -ne 0){
                Require ($ace.IdentityReference.Value -cin $allowed) 'UNTRUSTED_PATH_WRITER'
            }
        }
        $current = if($current -is [IO.FileInfo]){ $current.Directory }else{ $current.Parent }
    }
    return $item
}
function Assert-Principal([string]$SID,[switch]$Standard) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    Require ($identity.User.Value -ceq $SID -and [Environment]::Is64BitProcess) 'EXACT_X64_PRINCIPAL_REQUIRED'
    if($Standard){
        $principal=[Security.Principal.WindowsPrincipal]::new($identity)
        Require (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'STANDARD_DISPATCHER_REQUIRED'
        $groups=@($identity.Groups | ForEach-Object Value)
        Require ([AIBSProbeHost.Native]::IntegritySID() -ceq 'S-1-16-8192' -and 'S-1-5-32-544' -cnotin $groups -and 'S-1-5-114' -cnotin $groups) 'MEDIUM_NONADMIN_DISPATCHER_REQUIRED'
    }
}
function Assert-ProfileData($Profile) {
    $fields=@('schema_version','state','vm_uuid','image_id','image_base_path','image_base_sha256','system_disk_uuid','accepted_snapshot_uuid','vbox_path','vbox_sha256','vbox_user_home','guest_executable','guest_executable_sha256','guest_username','guest_sid','dispatcher_sid','controller_sid','vm_memory_mib','vm_cpus')
    Assert-Fields $Profile $fields 'PROFILE_SCHEMA'
    Require ($Profile.schema_version -is [long] -and $Profile.schema_version -eq 1 -and $Profile.state -ceq 'PROVISIONED') 'ISOLATION_UNAVAILABLE'
    foreach($field in @('vm_uuid','system_disk_uuid','accepted_snapshot_uuid')){ Require (Is-ID $Profile[$field]) 'PROFILE_IDENTITY_REQUIRED' }
    Require ($Profile.vm_uuid -cne $script:IntegrationUUID) 'INTEGRATION_VM_REFUSED'
    Require ($Profile.vm_uuid -ceq $script:WorkerUUID) 'EXACT_NEW_VM_REQUIRED'
    foreach($field in @('image_base_sha256','vbox_sha256','guest_executable_sha256')){ Require (Is-Digest $Profile[$field]) 'PROFILE_DIGEST_REQUIRED' }
    Require ($Profile.image_id -ceq ('aibs-fixed-probe-win11-eval-'+$script:WorkerUUID)) 'IMAGE_ID_REQUIRED'
    Require ($Profile.controller_sid -ceq $script:ControllerSID) 'PINNED_CONTROLLER_REQUIRED'
    Require ($Profile.dispatcher_sid -ceq $script:DispatcherSID) 'SEPARATE_DISPATCHER_REQUIRED'
    Require ($Profile.guest_username -ceq 'aibs_vm_worker' -and $Profile.guest_sid -is [string] -and $Profile.guest_sid -cmatch '\AS-1-5-21-\d+-\d+-\d+-\d+\z' -and -not $Profile.guest_sid.StartsWith($script:HostSIDPrefix,[StringComparison]::Ordinal)) 'SEPARATE_GUEST_ACCOUNT_REQUIRED'
    Require ($Profile.guest_executable -ceq 'C:\AIBSProbe\DiagnosticProbe.exe') 'FIXED_GUEST_EXECUTABLE_REQUIRED'
    Require ($Profile.vbox_path -ceq 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe') 'FIXED_VBOX_EXECUTABLE_REQUIRED'
    Require ($Profile.vbox_user_home -ceq (Fixed-Path 'vbox_home')) 'FIXED_VBOX_HOME_REQUIRED'
    Require ($Profile.vm_memory_mib -is [long] -and $Profile.vm_memory_mib -eq 4096 -and $Profile.vm_cpus -is [long] -and $Profile.vm_cpus -eq 4) 'REVIEWED_VM_PROFILE_REQUIRED'
}
function Read-Profile([string]$Path,[string]$ExpectedSHA256) {
    Require ($PSVersionTable.PSVersion.Major -ge 7 -and (Is-Digest $ExpectedSHA256)) 'POWERSHELL7_AND_PROFILE_PIN_REQUIRED'
    Require ($Path -ceq (Fixed-Path 'policy\profile.json') -and [IO.File]::Exists($Path)) 'ISOLATION_UNAVAILABLE'
    $null=Assert-Path $Path
    $profile=Read-StrictJSON (Read-Bytes $Path 32768 $ExpectedSHA256)
    Assert-ProfileData $profile
    return ,$profile
}
function Assert-Request($Request,$Profile,[string]$ProfileHash,[string]$AttemptID,[DateTime]$Now) {
    Assert-Fields $Request @('schema_version','purpose','task_id','attempt_id','challenge','mode','profile_sha256','issued_at','expires_at','guest_timeout_ms','output_bytes','transport_seconds','cancel_after_ms') 'REQUEST_SCHEMA'
    Require ($Request.schema_version -is [long] -and $Request.schema_version -eq 1 -and $Request.purpose -ceq 'fixed_disposable_diagnostic_v1') 'REQUEST_PURPOSE'
    Require (Is-ID $AttemptID) 'CANONICAL_ATTEMPT_REQUIRED'
    Require ($Request.attempt_id -ceq $AttemptID -and $Request.task_id -ceq 'first-disposable-diagnostic-v1' -and $Request.profile_sha256 -ceq $ProfileHash -and (Is-Digest $Request.challenge)) 'REQUEST_SCOPE_MISMATCH'
    Require ($Request.mode -cin @('success','timeout','cancel')) 'FIXED_MODE_REQUIRED'
    Require ($Request.guest_timeout_ms -is [long] -and $Request.guest_timeout_ms -eq 2000 -and $Request.output_bytes -is [long] -and $Request.output_bytes -eq 4096 -and $Request.transport_seconds -is [long] -and $Request.transport_seconds -eq 30) 'FIXED_DIAGNOSTIC_LIMITS_REQUIRED'
    Require ($Request.cancel_after_ms -is [long] -and (($Request.mode -ceq 'cancel' -and $Request.cancel_after_ms -eq 500) -or ($Request.mode -cne 'cancel' -and $Request.cancel_after_ms -eq 0))) 'FIXED_CANCELLATION_REQUIRED'
    $issued=UTC $Request.issued_at; $expires=UTC $Request.expires_at
    Require ($issued -le $Now -and $Now -lt $expires -and $expires -gt $issued -and ($expires-$issued).TotalSeconds -le 600) 'EXPIRED_OR_FUTURE_REQUEST'
}
function Read-Request($Profile,[string]$ProfileHash,[string]$AttemptID) {
    Require (Is-ID $AttemptID) 'CANONICAL_ATTEMPT_REQUIRED'
    $path=Fixed-Path ('requests\'+$AttemptID+'.json'); $null=Assert-Path $path
    $request=Read-StrictJSON (Read-Bytes $path 16384)
    Assert-Request $request $Profile $ProfileHash $AttemptID (Now-UTC)
    return ,$request
}
function Parse-VMInfo([string]$Text) {
    Require ([Text.Encoding]::UTF8.GetByteCount($Text) -le 131072) 'VM_INFO_BOUND'
    $map=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
    foreach($line in ($Text -split '\r?\n')){
        if(-not $line){ continue }
        if($line -cmatch '\A rec_screen[0-9]+\z'){ continue }
        Require ($line -cmatch '\A([^=\r\n]+)=(.*)\z') 'VM_INFO_MALFORMED'
        $name=$Matches[1]; $value=$Matches[2]
        if($name.StartsWith('"') -and $name.EndsWith('"')){ $name=$name.Substring(1,$name.Length-2) }
        Require (-not $map.ContainsKey($name)) 'DUPLICATE_VM_INFO'
        if($value.StartsWith('"') -and $value.EndsWith('"')){ $value=$value.Substring(1,$value.Length-2).Replace('\"','"').Replace('\\','\') }
        $map.Add($name,$value)
    }
    return ,$map
}
function Assert-VMInfo($Info,$Profile,[string]$ExpectedState) {
    foreach($key in @('UUID','VMState','memory','cpus','firmware','SecureBoot','clipboard','clipboard_file_transfers','draganddrop','vrde','usb','ehci','xhci','teleporterenabled','storagecontrollername0','CurrentSnapshotUUID','SATA-ImageUUID-0-0','audio','audio_in','audio_out')){ Require ($Info.ContainsKey($key)) 'INCOMPLETE_VM_INFO' }
    Require ($Info.UUID -ceq $Profile.vm_uuid -and $Info.UUID -cne $script:IntegrationUUID -and $Info.VMState -ceq $ExpectedState) 'VM_IDENTITY_OR_STATE_MISMATCH'
    Require ($Info.memory -ceq '4096' -and $Info.cpus -ceq '4' -and $Info.clipboard -ceq 'disabled' -and $Info.draganddrop -ceq 'disabled') 'VM_PROFILE_CHANGED'
    Require ($Info.CurrentSnapshotUUID -ceq $Profile.accepted_snapshot_uuid -and (Is-ID $Info['SATA-ImageUUID-0-0'])) 'VM_IMAGE_IDENTITY_CHANGED'
    foreach($index in 1..8){ Require ($Info.ContainsKey('nic'+$index) -and $Info['nic'+$index] -ceq 'none') 'VM_NETWORK_NOT_DISABLED' }
    foreach($index in 1..4){Require ($Info.ContainsKey('uart'+$index) -and $Info['uart'+$index] -ceq 'off') 'VM_UART_NOT_DISABLED'}
    Require ($Info.firmware -ceq 'EFI' -and $Info.SecureBoot -ceq 'on' -and $Info.audio -ceq 'none' -and $Info.audio_in -ceq 'off' -and $Info.audio_out -ceq 'off') 'VM_BOOT_OR_AUDIO_PROFILE_CHANGED'
    foreach($key in @('clipboard_file_transfers','vrde','usb','ehci','xhci','teleporterenabled')){Require ($Info[$key] -ceq 'off') 'VM_EXTRA_CHANNEL_ENABLED'}
    Require ($Info.storagecontrollername0 -ceq 'SATA' -and @($Info.Keys|Where-Object {$_ -cmatch '\Astoragecontrollername[1-9][0-9]*\z'}).Count -eq 0) 'VM_EXTRA_STORAGE_CONTROLLER'
    foreach($key in $Info.Keys){if($key -cmatch '\ASATA-([0-9]+)-([0-9]+)\z' -and $key -cne 'SATA-0-0'){Require ($Info[$key] -cin @('none','emptydrive')) 'VM_EXTRA_MEDIA_ATTACHED'}}
    Require (@($Info.Keys | Where-Object { $_ -cmatch '\ASharedFolder' }).Count -eq 0) 'VM_SHARED_FOLDER_REFUSED'
}
function Invoke-BoundedProcess([string]$Executable,[string[]]$Arguments,[string]$VBoxHome,[string]$WorkingDirectory,[int]$Seconds,[int]$OutputBytes,[int]$CancelAfterMS=0,[Security.SecureString]$Credential=$null,[string]$ExpectedSID='') {
    $maximum=if($null -ne $Credential){1200}else{30}
    Require ($Seconds -ge 1 -and $Seconds -le $maximum -and $OutputBytes -ge 1024 -and $OutputBytes -le 131072) 'PROCESS_LIMITS_REFUSED'
    $process=[Diagnostics.Process]::new(); $out=[IO.MemoryStream]::new(); $err=[IO.MemoryStream]::new()
    $result=[ordered]@{state='NOT_STARTED';pid=$null;started_utc=$null;exit_code=$null;stdout='';stderr='';combined_output_bytes=0;owned_process_termination_confirmed=$false;elapsed_ms=0}
    try {
        $info=[Diagnostics.ProcessStartInfo]::new(); $info.FileName=$Executable; $info.WorkingDirectory=$WorkingDirectory
        $info.UseShellExecute=$false; $info.CreateNoWindow=$true; $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true; $info.RedirectStandardInput=$true
        foreach($argument in $Arguments){ Require ($null -ne $argument -and $argument.IndexOfAny([char[]]@([char]0,[char]10,[char]13)) -lt 0) 'PROCESS_ARGUMENT_REFUSED'; $info.ArgumentList.Add($argument) }
        $info.Environment.Clear()
        foreach($name in @('SystemRoot','WINDIR')){ $info.Environment[$name]='C:\Windows' }
        $info.Environment['TEMP']=Fixed-Path 'worker_state'; $info.Environment['TMP']=Fixed-Path 'worker_state'; $info.Environment['VBOX_USER_HOME']=$VBoxHome
        $info.Environment['PATH']='C:\Windows\System32;C:\Windows'
        if($null -ne $Credential){
            Require ($ExpectedSID -ceq $script:DispatcherSID) 'FIXED_DISPATCHER_CREDENTIAL_REQUIRED'
            $info.UserName='aibs_probe_host';$info.Domain='AI-BS';$info.Password=$Credential;$info.LoadUserProfile=$true
            $info.Environment['PSModulePath']=Fixed-Path 'deployment\pwsh\Modules'
        }
        $process.StartInfo=$info; $timer=[Diagnostics.Stopwatch]::StartNew()
        Require ($process.Start()) 'PROCESS_START_FAILED'; $process.StandardInput.Close()
        $result.pid=$process.Id; $result.started_utc=$process.StartTime.ToUniversalTime().ToString('o'); $result.state='RUNNING'
        if($ExpectedSID){ Require ([AIBSProbeHost.Native]::ProcessSID($process.Handle) -ceq $ExpectedSID) 'LAUNCHED_OWNER_SID_MISMATCH'; $result['owner_sid']=$ExpectedSID }
        $ob=[byte[]]::new(4096); $eb=[byte[]]::new(4096)
        $os=$process.StandardOutput.BaseStream; $es=$process.StandardError.BaseStream
        $ot=$os.ReadAsync($ob,0,$ob.Length); $et=$es.ReadAsync($eb,0,$eb.Length); $oo=$true; $eo=$true
        while($oo -or $eo -or -not $process.HasExited){
            if($CancelAfterMS -gt 0 -and $timer.ElapsedMilliseconds -ge $CancelAfterMS){ $result.state='CANCELLED'; break }
            if($timer.Elapsed.TotalSeconds -ge $Seconds){ $result.state='TIMED_OUT'; break }
            foreach($streamName in @('out','err')){
                $task=if($streamName -ceq 'out'){$ot}else{$et}; $open=if($streamName -ceq 'out'){$oo}else{$eo}
                if($open -and $task.IsCompleted){
                    $read=$task.GetAwaiter().GetResult()
                    if($read -eq 0){ if($streamName -ceq 'out'){$oo=$false}else{$eo=$false} }
                    else {
                        if($out.Length+$err.Length+$read -gt $OutputBytes){ $result.state='OUTPUT_LIMIT'; break }
                        if($streamName -ceq 'out'){ $out.Write($ob,0,$read); $ot=$os.ReadAsync($ob,0,$ob.Length) }
                        else { $err.Write($eb,0,$read); $et=$es.ReadAsync($eb,0,$eb.Length) }
                    }
                }
            }
            if($result.state -ceq 'OUTPUT_LIMIT'){ break }; Start-Sleep -Milliseconds 10
        }
        if($result.state -ceq 'RUNNING'){ $result.state='EXITED' }
        if(-not $process.HasExited){ $process.Kill(); $null=$process.WaitForExit(2000) }
        $result.owned_process_termination_confirmed=$process.HasExited
        if($process.HasExited){ $result.exit_code=$process.ExitCode }
        $result.stdout=[Text.UTF8Encoding]::new($false,$true).GetString($out.ToArray()); $result.stderr=[Text.UTF8Encoding]::new($false,$true).GetString($err.ToArray())
        $result.combined_output_bytes=$out.Length+$err.Length; $result.elapsed_ms=$timer.ElapsedMilliseconds
        return ,$result
    } finally {
        if($null -ne $result.pid -and -not $process.HasExited){ try{$process.Kill();$null=$process.WaitForExit(2000)}catch{} }
        $process.Dispose(); $out.Dispose(); $err.Dispose()
    }
}
function VBox-Arguments([string]$Operation,$Profile,$Request) {
    switch($Operation){
        Inspect { return ,@('showvminfo',$Profile.vm_uuid,'--machinereadable') }
        Start { return ,@('startvm',$Profile.vm_uuid,'--type','headless') }
        PowerOff { return ,@('controlvm',$Profile.vm_uuid,'poweroff') }
        Restore { return ,@('snapshot',$Profile.vm_uuid,'restore',$Profile.accepted_snapshot_uuid) }
        Readiness { return ,@('guestproperty','get',$Profile.vm_uuid,'/VirtualBox/GuestAdd/RunLevel') }
        Run {
            $mode=if($Request.mode -ceq 'success'){'emit'}else{'sleep'}
            return ,(@('guestcontrol',$Profile.vm_uuid,'run','--exe',$Profile.guest_executable,'--username',$Profile.guest_username,'--passwordfile',(Fixed-Path 'credentials\guest.txt'),'--wait-stdout','--wait-stderr','--timeout','25000','--cwd','C:\AIBSProbe','--')+(Guest-Arguments $Profile $Request))
        }
        default { Fail 'FIXED_OPERATION_REQUIRED' }
    }
}
function Assert-StorageLocation([string]$Path) {
    Require ($Path -is [string] -and $Path.StartsWith($script:StorageRoot+'\',[StringComparison]::Ordinal) -and [IO.Path]::GetFullPath($Path) -ceq $Path -and $Path.Substring(2) -notmatch '[:\x00\r\n]') 'OUTSIDE_DISPOSABLE_STORAGE'
    $item=Get-Item -LiteralPath $Path -Force
    while($null -ne $item){ Require (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_STORAGE_REFUSED'; $item=if($item -is [IO.FileInfo]){$item.Directory}else{$item.Parent} }
}
function Assert-ClaimPolicy($Profile) {
    $path=Fixed-Path 'worker_claims'; $acl=Get-Acl -LiteralPath $path; $ownerRights=$false
    foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
        if($ace.IdentityReference.Value -ceq 'S-1-3-4' -and $ace.AccessControlType -eq 'Allow' -and ([long]$ace.FileSystemRights -band 0x20000) -ne 0 -and ($ace.InheritanceFlags -band [Security.AccessControl.InheritanceFlags]::ObjectInherit) -ne 0){ $ownerRights=$true }
        if($ace.IdentityReference.Value -ceq $Profile.dispatcher_sid -and $ace.AccessControlType -eq 'Allow'){
            Require (([long]$ace.FileSystemRights -band 0xD0040) -eq 0) 'CLAIM_REPLAY_PROTECTION_DACL'
        }
    }
    Require $ownerRights 'CLAIM_OWNER_RIGHTS_RESTRICTION_REQUIRED'
}
function Guest-Arguments($Profile,$Request) {
    $mode=if($Request.mode -ceq 'success'){'emit'}else{'sleep'}
    return ,@('--mode',$mode,'--attempt',$Request.attempt_id,'--challenge',$Request.challenge,'--timeout-ms','2000','--output-bytes','4096','--worker-sid',$Profile.guest_sid,'--vm-id',$Profile.vm_uuid,'--image-sha256',$Profile.image_base_sha256)
}
function Invoke-Operation([string]$Operation,$Profile,$Request,[string]$AttemptRoot,[int]$Sequence,[int]$CancelAfterMS=0,[string]$DiskUUID='') {
    if($Operation -ceq 'InspectDisk'){ Require (Is-ID $DiskUUID) 'DISK_UUID_REQUIRED'; $arguments=@('showmediuminfo','disk',$DiskUUID) }
    else { $arguments=VBox-Arguments $Operation $Profile $Request }
    $intent=[ordered]@{schema_version=1;operation=$Operation;sequence=$Sequence;vm_uuid=$Profile.vm_uuid;attempt_id=$Request.attempt_id;arguments_sha256=(Hash-Text (JSON $arguments));intent_utc=(Now-UTC).ToString('o')}
    New-JSON (Join-Path $AttemptRoot ('{0:D3}_{1}_intent.json' -f $Sequence,$Operation)) $intent
    $result=Invoke-BoundedProcess $Profile.vbox_path $arguments $Profile.vbox_user_home (Fixed-Path 'deployment') 30 131072 $CancelAfterMS
    New-JSON (Join-Path $AttemptRoot ('{0:D3}_{1}_result.json' -f $Sequence,$Operation)) $result
    return ,$result
}
function Assert-ImageChain($Info,$Profile,$Request,[string]$AttemptRoot,[ref]$Sequence) {
    $current=$Info['SATA-ImageUUID-0-0']; $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal); $chain=@()
    foreach($depth in 0..7){
        Require ((Is-ID $current) -and $seen.Add($current)) 'DISK_CHAIN_INVALID'
        $Sequence.Value++; $disk=Invoke-Operation InspectDisk $Profile $Request $AttemptRoot $Sequence.Value 0 $current; Successful-Operation $disk
        $medium=Parse-MediumInfo $disk.stdout
        foreach($field in @('UUID','ParentUUID','Location','StorageFormat','Capacity')){ Require ($medium.ContainsKey($field)) 'INCOMPLETE_DISK_INFO' }
        Require ($medium.UUID -ceq $current -and $medium.StorageFormat -ceq 'VDI' -and $medium.Capacity -ceq '65536') 'DISK_PROFILE_CHANGED'
        Assert-StorageLocation $medium.Location
        $chain += ,$medium
        if($current -ceq $Profile.system_disk_uuid){
            Require ($medium.ParentUUID -cin @('base','00000000-0000-0000-0000-000000000000') -and $medium.Location -ceq $Profile.image_base_path -and $depth -ge 1) 'SEALED_BASE_NOT_SNAPSHOT_PARENT'
            return (Hash-Text (JSON $chain))
        }
        $current=$medium.ParentUUID
    }
    Fail 'DISK_CHAIN_TOO_DEEP'
}
function Parse-MediumInfo([string]$Text) {
    Require ([Text.Encoding]::UTF8.GetByteCount($Text) -le 131072) 'MEDIUM_INFO_BOUND'
    $result=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
    $names=@{'UUID'='UUID';'Parent UUID'='ParentUUID';'Location'='Location';'Storage format'='StorageFormat';'Capacity'='Capacity'}
    foreach($line in ($Text -split '\r?\n')){
        if(-not $line){continue}
        if($line -cmatch '\A([^:\r\n]+):\s*(.*)\z'){
            $name=$Matches[1].TrimEnd();$value=$Matches[2].TrimEnd()
            if($names.ContainsKey($name)){
                $key=$names[$name];Require (-not $result.ContainsKey($key)) 'DUPLICATE_MEDIUM_INFO'
                if($key -ceq 'Capacity'){Require ($value -cmatch '\A([0-9]+) MBytes\z') 'DISK_CAPACITY_UNIT';$value=$Matches[1]}
                $result.Add($key,$value)
            }
        }
    }
    return ,$result
}
function Assert-StorageReserve { Require ([IO.DriveInfo]::new('E:\').AvailableFreeSpace -ge 42949672960L) 'DISPOSABLE_STORAGE_RESERVE_REQUIRED' }
function Assert-HostMemoryReserve { Require ([long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024L -ge 6442450944L) 'CURRENT_RAM_UNAVAILABLE' }
function Successful-Operation($Result) { Require ($Result.state -ceq 'EXITED' -and $Result.exit_code -eq 0 -and $Result.owned_process_termination_confirmed) 'VBOX_OPERATION_FAILED' }
function Assert-GuestReport($Report,$Profile,$Request) {
    foreach($field in @('schema_version','attempt_id','challenge','mode','guest_sid','guest_username','standard_account','administrator_group_present','medium_integrity','executable_sha256','image_sha256','vm_id','state','child_exit_code','stdout_base64','stderr_base64','combined_output_bytes','output_limit_bytes','termination_confirmed','self_hash_revalidated','resource_profile','input_sha256')){ Require (([Collections.IDictionary]$Report).Contains($field)) 'INCOMPLETE_GUEST_REPORT' }
    foreach($field in @('standard_account','administrator_group_present','medium_integrity','termination_confirmed','self_hash_revalidated')){ Require ($Report[$field] -is [bool]) 'GUEST_BOOLEAN_TYPE_REQUIRED' }
    Require ($Report.schema_version -is [long] -and $Report.schema_version -eq 1 -and $Report.attempt_id -ceq $Request.attempt_id -and $Report.challenge -ceq $Request.challenge -and $Report.vm_id -ceq $Profile.vm_uuid -and $Report.image_sha256 -ceq $Profile.image_base_sha256 -and $Report.executable_sha256 -ceq $Profile.guest_executable_sha256) 'GUEST_REPORT_BINDING_FAILED'
    Require ($Report.guest_sid -ceq $Profile.guest_sid -and $Report.guest_username -ceq 'aibs_vm_worker' -and $Report.standard_account -ceq $true -and $Report.administrator_group_present -ceq $false -and $Report.medium_integrity -ceq $true -and $Report.termination_confirmed -ceq $true -and $Report.self_hash_revalidated -ceq $true) 'GUEST_STANDARD_IDENTITY_OR_TERMINATION_FAILED'
    Require ($Report.input_sha256 -ceq (Hash-Text ((Guest-Arguments $Profile $Request) -join "`n"))) 'GUEST_INPUT_DIGEST_MISMATCH'
    $stdout=[Convert]::FromBase64String($Report.stdout_base64); $stderr=[Convert]::FromBase64String($Report.stderr_base64)
    Require ($stdout.Length+$stderr.Length -le 4096 -and $Report.combined_output_bytes -eq $stdout.Length+$stderr.Length -and $Report.output_limit_bytes -eq 4096) 'GUEST_OUTPUT_BOUND_FAILED'
    Assert-Fields $Report.resource_profile @('process_limit','job_memory_bytes','cpu_rate_percent','elapsed_limit_ms') 'GUEST_RESOURCE_PROFILE_REQUIRED'
    Require ($Report.resource_profile.process_limit -eq 1 -and $Report.resource_profile.job_memory_bytes -eq 268435456 -and $Report.resource_profile.cpu_rate_percent -eq 25 -and $Report.resource_profile.elapsed_limit_ms -eq 2000) 'GUEST_RESOURCE_PROFILE_CHANGED'
    if($Request.mode -ceq 'success'){
        Require ($Report.mode -ceq 'emit' -and $Report.state -ceq 'COMPLETED' -and $Report.child_exit_code -eq 7 -and [Text.Encoding]::UTF8.GetString($stdout) -ceq "probe`n" -and [Text.Encoding]::UTF8.GetString($stderr) -ceq "diagnostic`n") 'FIXED_PROBE_RESULT_MISMATCH'
    } elseif($Request.mode -ceq 'timeout') { Require ($Report.mode -ceq 'sleep' -and $Report.state -ceq 'TIMED_OUT') 'GUEST_TIMEOUT_NOT_DEMONSTRATED' }
}

function Invoke-AIBSWorkerProbe {
    [CmdletBinding()]param([Parameter(Mandatory)][string]$ProfilePath,[Parameter(Mandatory)][string]$ExpectedProfileSHA256,[Parameter(Mandatory)][string]$AttemptID)
    $lease=$null; $claim=$false; $started=$false; $profile=$null; $request=$null; $attemptRoot=$null; $sequence=0
    $result=[ordered]@{schema_version=1;attempt_id=$AttemptID;state='BLOCKED';error_code='ISOLATION_UNAVAILABLE';worker_observed=@{};guest_reported=$null;worker_admitted=$false;candidate_execution_authorized=$false;apply_authorized=$false;full_containment_accepted=$false}
    try {
        $profile=Read-Profile $ProfilePath $ExpectedProfileSHA256; Assert-Principal $profile.dispatcher_sid -Standard
        $request=Read-Request $profile $ExpectedProfileSHA256 $AttemptID
        foreach($relative in @('worker_state','worker_outputs','worker_claims','vbox_home')){ $null=Assert-Path (Fixed-Path $relative) (@($script:TrustedWriters)+$profile.dispatcher_sid) }
        Assert-ClaimPolicy $profile
        $null=Assert-Path (Fixed-Path 'credentials\guest.txt'); $null=Read-Bytes (Fixed-Path 'credentials\guest.txt') 1024
        $null=Assert-Path $profile.vbox_path $script:TrustedWriters -External; $null=Read-Bytes $profile.vbox_path 67108864 $profile.vbox_sha256
        # Sealed base is trusted evidence of prelaunch guest executable bytes. It must not be writable by the dispatcher.
        $null=Assert-Path $profile.image_base_path $script:TrustedWriters -External
        $base=[IO.File]::Open($profile.image_base_path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        try { Require ([AIBSProbeHost.Native]::Links($base.SafeFileHandle) -eq 1) 'HARDLINK_REFUSED'; Require ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($base)).ToLowerInvariant() -ceq $profile.image_base_sha256) 'ACCEPTED_IMAGE_BYTES_CHANGED'; $script:Held.Add($base); $base=$null } finally { if($null -ne $base){$base.Dispose()} }
        $lease=[IO.File]::Open((Fixed-Path 'worker_state\vm.lease'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        # This root must deny dispatcher deletion/DACL changes. Claim files are permanent, including failures.
        $claimPath=Fixed-Path ('worker_claims\'+$AttemptID+'.claim')
        New-JSON $claimPath ([ordered]@{attempt_id=$AttemptID;request_sha256=(Hash-Text (JSON $request));claimed_utc=(Now-UTC).ToString('o')}); $claim=$true
        $attemptRoot=Fixed-Path ('worker_outputs\'+$AttemptID); Require (-not [IO.Directory]::Exists($attemptRoot)) 'EXISTING_ATTEMPT_OUTPUT_REFUSED'; $null=[IO.Directory]::CreateDirectory($attemptRoot)
        $sequence++; $before=Invoke-Operation Inspect $profile $request $attemptRoot $sequence; Successful-Operation $before
        $beforeInfo=Parse-VMInfo $before.stdout; Assert-VMInfo $beforeInfo $profile 'poweroff'
        Assert-StorageReserve
        Assert-HostMemoryReserve
        $sequence++; $restore=Invoke-Operation Restore $profile $request $attemptRoot $sequence; Successful-Operation $restore
        $sequence++; $restored=Invoke-Operation Inspect $profile $request $attemptRoot $sequence; Successful-Operation $restored
        $beforeInfo=Parse-VMInfo $restored.stdout; Assert-VMInfo $beforeInfo $profile 'poweroff'
        $beforeChain=Assert-ImageChain $beforeInfo $profile $request $attemptRoot ([ref]$sequence)
        # Expiry is sampled again after hashing and waiting for the lease, immediately before VM launch.
        Assert-Request $request $profile $ExpectedProfileSHA256 $AttemptID (Now-UTC)
        $started=$true; $sequence++; $start=Invoke-Operation Start $profile $request $attemptRoot $sequence; Successful-Operation $start
        $sequence++; $running=Invoke-Operation Inspect $profile $request $attemptRoot $sequence; Successful-Operation $running; $runningInfo=Parse-VMInfo $running.stdout; Assert-VMInfo $runningInfo $profile 'running'
        $ready=$false; $readyDeadline=(Now-UTC).AddSeconds(180)
        while((Now-UTC) -lt $readyDeadline){
            Assert-Request $request $profile $ExpectedProfileSHA256 $AttemptID (Now-UTC)
            $sequence++; $readiness=Invoke-Operation Readiness $profile $request $attemptRoot $sequence
            if($readiness.state -ceq 'EXITED' -and $readiness.exit_code -eq 0 -and $readiness.stdout -cmatch '\AValue: [23]\r?\n?\z'){ $ready=$true; break }
            Start-Sleep -Seconds 3
        }
        Require $ready 'GUEST_ADDITIONS_NOT_READY'
        Assert-Request $request $profile $ExpectedProfileSHA256 $AttemptID (Now-UTC)
        $sequence++; $run=Invoke-Operation Run $profile $request $attemptRoot $sequence ([int]$request.cancel_after_ms)
        $guest=$null
        if($request.mode -ceq 'cancel'){ Require ($run.state -ceq 'CANCELLED' -and $run.owned_process_termination_confirmed) 'HOST_CANCEL_NOT_DEMONSTRATED' }
        else { Successful-Operation $run; $guest=Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes($run.stdout)) 65536; Assert-GuestReport $guest $profile $request }
        $result.state=if($request.mode -ceq 'cancel'){'CANCELLED'}else{'PASSED'}; $result.error_code=''
        $result.worker_observed=[ordered]@{dispatcher_sid=$profile.dispatcher_sid;profile_sha256=$ExpectedProfileSHA256;request_sha256=(Hash-Text (JSON $request));image_base_sha256=$profile.image_base_sha256;vbox_sha256=$profile.vbox_sha256;before_config_sha256=(Hash-Text (JSON $beforeInfo));before_disk_chain_sha256=$beforeChain;running_config_sha256=(Hash-Text (JSON $runningInfo));probe_process=$run}
        $result.guest_reported=$guest
    } catch { $result.state='BLOCKED'; $result.error_code=if($_.Exception -is [InvalidOperationException]){$_.Exception.Message}else{'TRANSPORT_ERROR_'+$_.Exception.GetType().Name} }
    finally {
        if($started -and $null -ne $profile -and $null -ne $request -and $null -ne $attemptRoot){
            try {
                $sequence++; $off=Invoke-Operation PowerOff $profile $request $attemptRoot $sequence
                $sequence++; $terminal=Invoke-Operation Inspect $profile $request $attemptRoot $sequence; Successful-Operation $terminal; $offInfo=Parse-VMInfo $terminal.stdout; Assert-VMInfo $offInfo $profile 'poweroff'
                $sequence++; $reset=Invoke-Operation Restore $profile $request $attemptRoot $sequence; Successful-Operation $reset
                $sequence++; $clean=Invoke-Operation Inspect $profile $request $attemptRoot $sequence; Successful-Operation $clean; $cleanInfo=Parse-VMInfo $clean.stdout; Assert-VMInfo $cleanInfo $profile 'poweroff'
                $result.worker_observed['terminal_disk_chain_sha256']=Assert-ImageChain $cleanInfo $profile $request $attemptRoot ([ref]$sequence)
                $result.worker_observed['terminal_state']='poweroff'; $result.worker_observed['accepted_snapshot_restored']=$true; $result.worker_observed['terminal_config_sha256']=Hash-Text (JSON $cleanInfo)
            } catch { $result.state='QUARANTINED'; $result.error_code='VM_TERMINATION_UNCONFIRMED' }
        }
        $result['permanent_attempt_claimed']=$claim; $result['completed_utc']=(Now-UTC).ToString('o')
        if($null -ne $attemptRoot){ try{ New-JSON (Join-Path $attemptRoot 'result.json') $result }catch{ $result.state='QUARANTINED';$result.error_code='RESULT_PERSISTENCE_UNCERTAIN' } }
        if($null -ne $lease){ $lease.Dispose() }; Close-Held
    }
    return ,$result
}

function New-AIBSProbeRequest {
    [CmdletBinding()]param([Parameter(Mandatory)][string]$ProfilePath,[Parameter(Mandatory)][string]$ExpectedProfileSHA256,[Parameter(Mandatory)][ValidateSet('success','timeout','cancel')][string]$Mode,[Parameter(Mandatory)][string]$AttemptID)
    $lease=$null
    try {
        Assert-Principal $script:ControllerSID
        $profile=Read-Profile $ProfilePath $ExpectedProfileSHA256
        Require (Is-ID $AttemptID) 'CANONICAL_ATTEMPT_REQUIRED'
        foreach($relative in @('state','requests','receipts')){ $null=Assert-Path (Fixed-Path $relative) }
        $lease=[IO.File]::Open((Fixed-Path 'state\controller.lease'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        Assert-NoPendingAttempt
        $now=Now-UTC
        $request=[ordered]@{schema_version=1;purpose='fixed_disposable_diagnostic_v1';task_id='first-disposable-diagnostic-v1';attempt_id=$AttemptID;challenge=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant();mode=$Mode;profile_sha256=$ExpectedProfileSHA256;issued_at=$now.ToString('o');expires_at=$now.AddMinutes(10).ToString('o');guest_timeout_ms=2000;output_bytes=4096;transport_seconds=30;cancel_after_ms=$(if($Mode -ceq 'cancel'){500}else{0})}
        # Permanent reservation precedes publication; a partial failure is never retried under a new scope.
        New-JSON (Fixed-Path ('state\'+$AttemptID+'.reservation.json')) ([ordered]@{schema_version=1;attempt_id=$AttemptID;request=$request;status='RESERVED_NO_AUTOMATIC_REPLAY'})
        New-JSON (Fixed-Path ('requests\'+$AttemptID+'.json')) $request
        return ,$request
    } finally { if($null -ne $lease){$lease.Dispose()}; Close-Held }
}
function Assert-NoPendingAttempt {
    $reservations=@(Get-ChildItem -LiteralPath (Fixed-Path 'state') -Filter '*.reservation.json' -File)
    Require ($reservations.Count -le 1024) 'ATTEMPT_INDEX_REVIEW_REQUIRED'
    $key=$null
    try{
        if($reservations.Count -gt 0){$key=Read-ReceiptKey}
        foreach($item in $reservations){
            $id=$item.Name.Replace('.reservation.json',''); Require (Is-ID $id) 'MALFORMED_ATTEMPT_INDEX'
            $receiptPath=Fixed-Path ('receipts\'+$id+'.json')
            Require ([IO.File]::Exists($receiptPath)) 'PENDING_ATTEMPT_RECONCILIATION_REQUIRED'
            $null=Assert-Path $receiptPath; $receipt=Read-StrictJSON (Read-Bytes $receiptPath 524288)
            Assert-ReceiptAuthentication $receipt $key $id $receipt.body.profile_sha256
            Require ($receipt.body.state -cin @('PASSED','CANCELLED') -and $receipt.body.worker_reported.worker_observed.accepted_snapshot_restored -is [bool] -and $receipt.body.worker_reported.worker_observed.accepted_snapshot_restored) 'UNCERTAIN_ATTEMPT_RECONCILIATION_REQUIRED'
        }
    }finally{if($null -ne $key){[Array]::Clear($key,0,$key.Length)}}
}
function Assert-PrivateReaders([string]$Path) {
    $acl=Get-Acl -LiteralPath $Path
    foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
        if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
        if($ace.AccessControlType -eq 'Allow' -and ([long]$ace.FileSystemRights -band 1) -ne 0){Require ($ace.IdentityReference.Value -cin $script:TrustedWriters) 'PRIVATE_FILE_READER_REFUSED'}
    }
}
function Read-ReceiptKey {
    $path=Fixed-Path 'private\receipt.key';$null=Assert-Path $path;Assert-PrivateReaders $path
    $key=Read-Bytes $path 32;Require ($key.Length -eq 32) 'RECEIPT_KEY_SIZE';return ,$key
}
function Start-AIBSProbeTransport {
    [CmdletBinding()]param([Parameter(Mandatory)][string]$ProfilePath,[Parameter(Mandatory)][string]$ExpectedProfileSHA256,[Parameter(Mandatory)][string]$ExpectedTransportPolicySHA256,[Parameter(Mandatory)][string]$AttemptID)
    $credential=$null;$lease=$null
    try {
        Assert-Principal $script:ControllerSID
        $profile=Read-Profile $ProfilePath $ExpectedProfileSHA256
        $request=Read-Request $profile $ExpectedProfileSHA256 $AttemptID
        Require (Is-Digest $ExpectedTransportPolicySHA256) 'TRANSPORT_POLICY_PIN_REQUIRED'
        $path=Fixed-Path 'policy\transport.json';$null=Assert-Path $path
        $policy=Read-StrictJSON (Read-Bytes $path 8192 $ExpectedTransportPolicySHA256)
        Assert-Fields $policy @('schema_version','module_sha256','entry_sha256','pwsh_sha256') 'TRANSPORT_POLICY_SCHEMA'
        Require ($policy.schema_version -is [long] -and $policy.schema_version -eq 1) 'TRANSPORT_POLICY_VERSION'
        foreach($name in @('module_sha256','entry_sha256','pwsh_sha256')){Require (Is-Digest $policy[$name]) 'TRANSPORT_EXECUTABLE_PIN_REQUIRED'}
        $entry=Fixed-Path 'deployment\host\Invoke-WorkerTransport.ps1';$module=Fixed-Path 'deployment\host\DisposableProbe.psm1';$pwsh=Fixed-Path 'deployment\pwsh\pwsh.exe'
        foreach($pin in @(@($entry,$policy.entry_sha256),@($module,$policy.module_sha256),@($pwsh,$policy.pwsh_sha256))){$null=Assert-Path $pin[0];$null=Read-Bytes $pin[0] 16777216 $pin[1]}
        $secret=Fixed-Path 'private\host_credential.dpapi';$null=Assert-Path $secret;Assert-PrivateReaders $secret
        $encrypted=[Text.UTF8Encoding]::new($false,$true).GetString((Read-Bytes $secret 16384)).Trim()
        $credential=ConvertTo-SecureString -String $encrypted
        Require ($credential.Length -ge 24) 'DISPATCHER_CREDENTIAL_REQUIRED'
        $null=Assert-Path (Fixed-Path 'state')
        $lease=[IO.File]::Open((Fixed-Path 'state\dispatch.lease'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        $journalPath=Fixed-Path ('state\'+$AttemptID+'.dispatch_intent.json')
        New-JSON $journalPath ([ordered]@{attempt_id=$AttemptID;profile_sha256=$ExpectedProfileSHA256;transport_policy_sha256=$ExpectedTransportPolicySHA256;request_sha256=(Hash-Text (JSON $request));dispatcher_sid=$script:DispatcherSID;intent_utc=(Now-UTC).ToString('o')})
        $arguments=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$entry,'-ProfilePath',$ProfilePath,'-ExpectedProfileSHA256',$ExpectedProfileSHA256,'-AttemptID',$AttemptID)
        $launch=Invoke-BoundedProcess $pwsh $arguments $profile.vbox_user_home (Fixed-Path 'deployment') 1200 131072 0 $credential $script:DispatcherSID
        # A killed transport is uncertain: no substitute host VM calls or replay is allowed.
        New-JSON (Fixed-Path ('state\'+$AttemptID+'.dispatch_result.json')) $launch
        return ,$launch
    } finally {if($null -ne $credential){$credential.Dispose()};if($null -ne $lease){$lease.Dispose()};Close-Held}
}
function Complete-AIBSProbeRequest {
    [CmdletBinding()]param([Parameter(Mandatory)][string]$ProfilePath,[Parameter(Mandatory)][string]$ExpectedProfileSHA256,[Parameter(Mandatory)][string]$AttemptID)
    $lease=$null
    try {
        Assert-Principal $script:ControllerSID; $profile=Read-Profile $ProfilePath $ExpectedProfileSHA256
        Require (Is-ID $AttemptID) 'CANONICAL_ATTEMPT_REQUIRED'
        foreach($relative in @('state','receipts','private')){ $null=Assert-Path (Fixed-Path $relative) }
        $lease=[IO.File]::Open((Fixed-Path 'state\controller.lease'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        $requestPath=Fixed-Path ('requests\'+$AttemptID+'.json');$null=Assert-Path $requestPath
        $request=Read-StrictJSON (Read-Bytes $requestPath 16384)
        # Collection may occur after request expiry; no new execution is authorized here.
        Assert-Request $request $profile $ExpectedProfileSHA256 $AttemptID (UTC $request.issued_at)
        $reservationPath=Fixed-Path ('state\'+$AttemptID+'.reservation.json');$null=Assert-Path $reservationPath
        $reservation=Read-StrictJSON (Read-Bytes $reservationPath 32768)
        Require ((JSON $reservation.request) -ceq (JSON $request)) 'RESERVATION_SCOPE_MISMATCH'
        $resultPath=Fixed-Path ('worker_outputs\'+$AttemptID+'\result.json')
        $null=Assert-Path $resultPath (@($script:TrustedWriters)+$profile.dispatcher_sid)
        $worker=Read-StrictJSON (Read-Bytes $resultPath 262144)
        Require ($worker.attempt_id -ceq $AttemptID -and $worker.permanent_attempt_claimed -ceq $true) 'WORKER_RESULT_SCOPE_FAILED'
        if($worker.state -cin @('PASSED','CANCELLED')){
            Require ($worker.worker_observed.dispatcher_sid -ceq $profile.dispatcher_sid -and $worker.worker_observed.profile_sha256 -ceq $ExpectedProfileSHA256 -and $worker.worker_observed.request_sha256 -ceq (Hash-Text (JSON $request)) -and $worker.worker_observed.terminal_state -ceq 'poweroff' -and $worker.worker_observed.accepted_snapshot_restored -is [bool] -and $worker.worker_observed.accepted_snapshot_restored) 'WORKER_OBSERVATION_BINDING_FAILED'
            Require (($request.mode -ceq 'cancel' -and $worker.state -ceq 'CANCELLED') -or ($request.mode -cne 'cancel' -and $worker.state -ceq 'PASSED')) 'WORKER_RESULT_MODE_MISMATCH'
            if($request.mode -cne 'cancel'){ Assert-GuestReport $worker.guest_reported $profile $request }
        }
        $key=Read-ReceiptKey
        $body=[ordered]@{schema_version=1;domain='AI-BS/host-fixed-probe-receipt/v1';attempt_id=$AttemptID;task_id=$request.task_id;challenge=$request.challenge;mode=$request.mode;profile_sha256=$ExpectedProfileSHA256;request_sha256=(Hash-Text (JSON $request));vm_uuid=$profile.vm_uuid;image_id=$profile.image_id;image_base_sha256=$profile.image_base_sha256;guest_executable_sha256=$profile.guest_executable_sha256;sealed_utc=(Now-UTC).ToString('o');state=$worker.state;controller_observed=@{reservation_retained=$true;worker_result_sha256=(Hash-Text (JSON $worker));worker_result_provenance='limited_host_dispatcher_report';guest_report_provenance='guest_reported_not_independent_image_attestation'};worker_reported=$worker;general_admission_enabled=$false;candidate_execution_authorized=$false;apply_authorized=$false;full_containment_accepted=$false}
        try { $tag=Receipt-Tag $body $key } finally { [Array]::Clear($key,0,$key.Length) }
        $receipt=[ordered]@{body=$body;hmac_sha256=$tag}
        New-JSON (Fixed-Path ('receipts\'+$AttemptID+'.json')) $receipt
        return ,$receipt
    } finally { if($null -ne $lease){$lease.Dispose()}; Close-Held }
}
function Receipt-Tag($Body,[byte[]]$Key) {
    Require ($Key.Length -eq 32) 'RECEIPT_KEY_SIZE'
    $hmac=[Security.Cryptography.HMACSHA256]::new($Key)
    try{return [Convert]::ToHexString($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes("AI-BS/host-fixed-probe-receipt/v1`0"+(JSON $Body)))).ToLowerInvariant()}finally{$hmac.Dispose()}
}
function Assert-ReceiptAuthentication($Receipt,[byte[]]$Key,[string]$AttemptID,[string]$ProfileHash) {
    Assert-Fields $Receipt @('body','hmac_sha256') 'RECEIPT_SCHEMA'
    Require ((Is-Digest $Receipt.hmac_sha256) -and $Receipt.body.domain -ceq 'AI-BS/host-fixed-probe-receipt/v1' -and $Receipt.body.attempt_id -ceq $AttemptID -and $Receipt.body.profile_sha256 -ceq $ProfileHash) 'RECEIPT_SCOPE_FAILED'
    Require ([Security.Cryptography.CryptographicOperations]::FixedTimeEquals([Convert]::FromHexString($Receipt.hmac_sha256),[Convert]::FromHexString((Receipt-Tag $Receipt.body $Key)))) 'RECEIPT_AUTHENTICATION_FAILED'
}
function Test-AIBSProbeReceipt {
    [CmdletBinding()]param([Parameter(Mandatory)][string]$ProfilePath,[Parameter(Mandatory)][string]$ExpectedProfileSHA256,[Parameter(Mandatory)][string]$AttemptID)
    try{
        Assert-Principal $script:ControllerSID;$null=Read-Profile $ProfilePath $ExpectedProfileSHA256;Require (Is-ID $AttemptID) 'CANONICAL_ATTEMPT_REQUIRED'
        $path=Fixed-Path ('receipts\'+$AttemptID+'.json');$null=Assert-Path $path;$receipt=Read-StrictJSON (Read-Bytes $path 524288)
        $key=Read-ReceiptKey
        try{Assert-ReceiptAuthentication $receipt $key $AttemptID $ExpectedProfileSHA256}finally{[Array]::Clear($key,0,$key.Length)}
        return [ordered]@{authenticated=$true;attempt_id=$AttemptID;profile_sha256=$ExpectedProfileSHA256;state=$receipt.body.state;evidence_class='authenticated_collection_of_explicitly_attributed_worker_reports';candidate_execution_authorized=$false;full_containment_accepted=$false}
    }finally{Close-Held}
}
Export-ModuleMember -Function Invoke-AIBSWorkerProbe,New-AIBSProbeRequest,Start-AIBSProbeTransport,Complete-AIBSProbeRequest,Test-AIBSProbeReceipt
