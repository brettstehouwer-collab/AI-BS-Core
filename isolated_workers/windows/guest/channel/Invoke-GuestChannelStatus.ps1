param(
 [Parameter(Mandatory=$true)][string]$RecipePath,
 [ValidateSet('status','gateway_health','model_version')][string]$Operation='status'
)
$ErrorActionPreference='Stop'
try {
 $computer=Get-CimInstance Win32_ComputerSystem
 $bios=Get-CimInstance Win32_BIOS
 if(($computer.Model+' '+$computer.Manufacturer+' '+$bios.Manufacturer)-notmatch 'VirtualBox|innotek|Oracle'){throw 'VIRTUALBOX_GUEST_REQUIRED'}
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 $principal=New-Object Security.Principal.WindowsPrincipal($identity)
 if($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'NON_ELEVATED_GUEST_REQUIRED'}
 $recipe=Get-Item -LiteralPath $RecipePath -Force
 if($recipe.PSIsContainer-or $recipe.Length-le 0-or $recipe.Length-gt 16384){throw 'PUBLIC_RECIPE_FILE_REQUIRED'}
 $node=$recipe
 while($null-ne $node){
  if($node.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_RECIPE_REFUSED'}
  $node=if($node-is [IO.FileInfo]){$node.Directory}else{$node.Parent}
 }
 $source=Join-Path $PSScriptRoot 'GuestStatusClient.cs'
 $sourceNode=Get-Item -LiteralPath $source -Force
 if($sourceNode.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_CLIENT_SOURCE_REFUSED'}
 if(-not ('AIBS.GuestChannel.GuestStatusClient' -as [type])){
  Add-Type -Path $source -ReferencedAssemblies @('System.dll','System.Core.dll','System.Security.dll','System.Web.Extensions.dll')
 }
 $json=[IO.File]::ReadAllText($recipe.FullName)
 Write-Output ([AIBS.GuestChannel.GuestStatusClient]::Send($json,$Operation))
} catch {
 $message=$_.Exception.GetBaseException().Message
 if($message-cnotmatch '^[A-Z0-9_]+$'){$message='GUEST_CHANNEL_STATUS_FAILED'}
 Write-Error -Message $message -ErrorAction Continue
 exit 2
}
