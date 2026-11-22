import sys
import os
import zipfile
import json
sys.path.append(r"C:\AI-BS\native_studio")
from xbox_tier4_deployer import AppxPackageInspector

test_pkg = r"C:\AI-BS\scratch\test_sample.appx"
manifest_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10">
  <Identity Name="RetroArch.XboxOne" Version="1.19.1.0" Publisher="CN=Libretro" ProcessorArchitecture="x64" />
  <Dependencies>
    <PackageDependency Name="Microsoft.VCLibs.x64.14.00" MinVersion="14.0.30035.0" />
  </Dependencies>
  <Capabilities>
    <Capability Name="internetClientServer" />
  </Capabilities>
</Package>"""

with zipfile.ZipFile(test_pkg, "w") as z:
    z.writestr("AppxManifest.xml", manifest_xml)

info = AppxPackageInspector.inspect_package(test_pkg)
print("=" * 65)
print(" [*] APPX / MSIX PACKAGE PRE-FLIGHT INSPECTION TEST")
print("=" * 65)
print(f" Package File: {info['filename']}")
print(f" App Name:     {info['identity'].get('Name')}")
print(f" Version:      {info['identity'].get('Version')}")
print(f" Architecture: {info['identity'].get('ProcessorArchitecture')}")
print(f" Dependencies: {info['dependencies']}")
print(f" Capabilities: {info['capabilities']}")
print("=" * 65)

if os.path.exists(test_pkg):
    os.remove(test_pkg)
