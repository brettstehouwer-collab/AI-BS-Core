param([Parameter(Mandatory=$true)][string]$OutputRoot)
# Trusted host packaging infrastructure. Never mounts media or executes any guest payload.
$ErrorActionPreference='Stop'
$expectedPrefix='C:\AI-BS\backups\phase4_wheel_setup_media_'
$root=[IO.Path]::GetFullPath($OutputRoot)
if($root -notmatch '^C:\\AI-BS\\backups\\phase4_wheel_setup_media_\d{8}T\d{6,}Z$' -or -not $root.StartsWith($expectedPrefix,[StringComparison]::OrdinalIgnoreCase)) {throw 'A fresh, timestamped wheel media backup folder is required.'}
if(Test-Path -LiteralPath $root){throw 'Refusing an existing output folder.'}
function Assert-NoReparse([string]$Path) {
    $candidate=[IO.Path]::GetFullPath($Path)
    while($candidate) {
        if(([IO.File]::GetAttributes($candidate) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse path rejected.'}
        $parent=[IO.Directory]::GetParent($candidate)
        $candidate=if($parent){$parent.FullName}else{$null}
    }
}
Assert-NoReparse ([IO.Path]::GetDirectoryName($root))
$helper=Join-Path $PSScriptRoot 'build\AI-BS Wheel Setup.exe'
$readme=Join-Path $PSScriptRoot 'Media-README.txt'
$original='C:\AI-BS\saved_data\phase4_offline_media\AIBS_Windows_Guest_Provisioning_v1.iso'
foreach($source in @($helper,$readme,$original)){Assert-NoReparse $source;if(-not [IO.File]::Exists($source)){throw 'Required fixed source file is missing.'}}
$native=@'
using System;
using System.IO;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class WheelMediaInfra {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateDirectory(string name,IntPtr security);
 public static void FreshDirectory(string path) { if(!CreateDirectory(path,IntPtr.Zero))throw new IOException("Cannot create fresh directory: "+Marshal.GetLastWin32Error()); }
 public static string Hash(Stream input) { long old=input.Position;input.Position=0;try{using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(input)).Replace("-","");}finally{input.Position=old;} }
 public static FileStream CopyRange(Stream source,long offset,long length,string path) {
  if(offset<0||length<1||offset>source.Length||length>source.Length-offset)throw new IOException("Invalid source range");
  var target=new FileStream(path,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.Read);
  try {source.Position=offset;byte[] buffer=new byte[65536];long left=length;while(left>0){int n=source.Read(buffer,0,(int)Math.Min(buffer.Length,left));if(n<=0)throw new EndOfStreamException();target.Write(buffer,0,n);left-=n;}target.Flush(true);target.Dispose();return new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);}
  catch{target.Dispose();throw;}
 }
 public static FileStream WriteBytes(byte[] bytes,string path) {using(var input=new MemoryStream(bytes,false))return CopyRange(input,0,bytes.Length,path);}
 public static void SaveIso(object value,string path) {
  IStream input=(IStream)value;
  using(var target=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read)) {
   byte[] buffer=new byte[65536];IntPtr count=Marshal.AllocHGlobal(4);long total=0;
   try {while(true){input.Read(buffer,buffer.Length,count);int n=Marshal.ReadInt32(count);if(n<0||n>buffer.Length)throw new IOException("Invalid IMAPI byte count");if(n==0)break;total+=n;if(total>33554432)throw new IOException("Media exceeds bound");target.Write(buffer,0,n);}target.Flush(true);}
   finally{Marshal.FreeHGlobal(count);}
  }
 }
}
'@
Add-Type -TypeDefinition $native
[WheelMediaInfra]::FreshDirectory($root)
$media=Join-Path $root 'media'
[WheelMediaInfra]::FreshDirectory($media)
$workerSID=New-Object Security.Principal.SecurityIdentifier('S-1-5-21-2133766663-4066672948-2456486318-1005')
$aclReceipt=New-Object 'System.Collections.Generic.List[object]'
function Grant-NewMediaReadExecute([string]$Path,[bool]$Directory) {
    $acl=Get-Acl -LiteralPath $Path
    $matches=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|Where-Object {$_.IdentityReference.Value -eq $workerSID.Value})
    $need=[Security.AccessControl.FileSystemRights]::ReadAndExecute
    if(@($matches|Where-Object {$_.AccessControlType -eq [Security.AccessControl.AccessControlType]::Deny -and ($_.FileSystemRights -band $need) -ne 0}).Count){throw 'Existing worker denial is a prerequisite blocker; no ACL changed.'}
    $allows=@($matches|Where-Object {$_.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow})
    if($allows.Count) {
        if(-not @($allows|Where-Object {($_.FileSystemRights -band $need) -eq $need}).Count){throw 'Existing worker ACL is insufficient; refusing to broaden it.'}
        $aclReceipt.Add([ordered]@{path=$Path;action='existing worker allow retained; no broadening';rules=@($allows|ForEach-Object {$_.FileSystemRights.ToString()})})
        return
    }
    $inherit=if($Directory){[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'}else{[Security.AccessControl.InheritanceFlags]::None}
    $rule=New-Object Security.AccessControl.FileSystemAccessRule($workerSID,$need,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow)
    $null=$acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
    $aclReceipt.Add([ordered]@{path=$Path;action='new media worker ReadAndExecute allow';rules=@('ReadAndExecute')})
}
$held=New-Object 'System.Collections.Generic.List[System.IDisposable]'
$records=New-Object 'System.Collections.Generic.List[object]'
$utf8=New-Object Text.UTF8Encoding($false)
$iso=Join-Path $root 'AI-BS_Wheels_v1.iso'
try {
    $originalHandle=New-Object IO.FileStream($original,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $held.Add($originalHandle)
    if($originalHandle.Length -ne 70387712 -or [WheelMediaInfra]::Hash($originalHandle) -ne '50F4AC4E873BDEAF088B7AE57160CB438F08269F401D811F84053F3A725A33F0'){throw 'Original retained media pin mismatch.'}
    $sources=@(
        [ordered]@{name='AI-BS Wheel Setup.exe';path=$helper;offset=0;length=0;sha=$null},
        [ordered]@{name='psutil-7.2.2-cp37-abi3-win_amd64.whl';path=$original;offset=33390592;length=137737;sha='EB7E81434C8D223EC4A219B5FC1C47D0417B12BE7EA866E24FB5AD6E84B3D988'},
        [ordered]@{name='pywin32-312-cp313-cp313-win_amd64.whl';path=$original;offset=63471616;length=6914298;sha='C53E878D15A1C44788082BFE712A905433473AA38F86375B7CF8B45E3ACBAAF9'},
        [ordered]@{name='README.txt';path=$readme;offset=0;length=0;sha=$null}
    )
    foreach($record in $sources) {
        $inputHandle=$originalHandle
        if($record.path -ne $original){$inputHandle=New-Object IO.FileStream($record.path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);$held.Add($inputHandle);$record.length=$inputHandle.Length;$record.sha=[WheelMediaInfra]::Hash($inputHandle)}
        if($record.name -eq 'AI-BS Wheel Setup.exe' -and ($record.length -le 0 -or $record.length -gt 1048576)){throw 'Helper size rejected.'}
        if($record.name -eq 'README.txt' -and ($record.length -le 0 -or $record.length -gt 8192)){throw 'README size rejected.'}
        $target=[WheelMediaInfra]::CopyRange($inputHandle,$record.offset,$record.length,(Join-Path $media $record.name))
        $held.Add($target)
        $sha=[WheelMediaInfra]::Hash($target)
        if($record.sha -and $record.sha -ne $sha){throw 'Approved wheel payload pin mismatch.'}
        $records.Add([ordered]@{name=$record.name;length=[long]$target.Length;sha256=$sha})
    }
    $manifest=[ordered]@{schema=1;volume_label='AIBS_WHEELS_V1';files=$records.ToArray()}
    $manifestBytes=$utf8.GetBytes(($manifest|ConvertTo-Json -Depth 5)+[Environment]::NewLine)
    if($manifestBytes.Length -gt 8192){throw 'Manifest bound exceeded.'}
    $manifestHandle=[WheelMediaInfra]::WriteBytes($manifestBytes,(Join-Path $media 'manifest.json'))
    $held.Add($manifestHandle)
    $entries=@(Get-ChildItem -LiteralPath $media -Force)
    if($entries.Count -ne 5 -or @($entries|Where-Object {$_.PSIsContainer -or ($_.Attributes -band [IO.FileAttributes]::ReparsePoint)}).Count){throw 'Unexpected media entries.'}
    Grant-NewMediaReadExecute $media $true
    $image=New-Object -ComObject IMAPI2FS.MsftFileSystemImage
    $image.FileSystemsToCreate=3
    $image.VolumeName='AIBS_WHEELS_V1'
    $image.Root.AddTree($media,$false)
    $result=$image.CreateResultImage()
    [WheelMediaInfra]::SaveIso($result.ImageStream,$iso)
    Grant-NewMediaReadExecute $iso $false
    [IO.File]::SetAttributes($iso,([IO.File]::GetAttributes($iso) -bor [IO.FileAttributes]::ReadOnly))
    $record=[ordered]@{created_utc=[DateTime]::UtcNow.ToString('o');media_root=$media;iso_path=$iso;iso_length=(Get-Item -LiteralPath $iso).Length;iso_sha256=(Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash;volume_label='AIBS_WHEELS_V1';original_iso_sha256='50F4AC4E873BDEAF088B7AE57160CB438F08269F401D811F84053F3A725A33F0';files=$records.ToArray();manifest_sha256=[WheelMediaInfra]::Hash($manifestHandle);worker_acl=$aclReceipt.ToArray();mounted_or_launched=$false;independent_verification='REQUIRED: run Verify-WheelISO.py against this ISO and media root'}
    $receipt=[WheelMediaInfra]::WriteBytes($utf8.GetBytes(($record|ConvertTo-Json -Depth 8)+[Environment]::NewLine),(Join-Path $root 'build_receipt.json'))
    $receipt.Dispose()
    Write-Output "CREATED $iso"
    Write-Output "SHA256 $($record.iso_sha256)"
    Write-Output 'Independent raw ISO verification remains required. Nothing mounted or launched.'
} finally {
    foreach($handle in $held){$handle.Dispose()}
}
