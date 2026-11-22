using System;
using System.IO;
using System.ComponentModel;
using System.Runtime.InteropServices;

namespace AIBS.HostProtection118 {
 public static class AtomicDirectory {
  const string Target = @"C:\ProgramData\AI-BS-WorkerControl";
  const string Fixture = @"C:\AI-BS\backups\host_protection_candidate_20261026_record118\native_fixture";
  [StructLayout(LayoutKind.Sequential)] struct SecurityAttributes {
   public int Length;
   public IntPtr Descriptor;
   [MarshalAs(UnmanagedType.Bool)] public bool InheritHandle;
  }
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  [return: MarshalAs(UnmanagedType.Bool)]
  static extern bool CreateDirectoryW(string name, ref SecurityAttributes security);

  public static void CreateNew(string path, byte[] descriptor) {
   if(Environment.OSVersion.Platform!=PlatformID.Win32NT)throw new IOException("WINDOWS_REQUIRED");
   if(path==null||path.IndexOf('/')>=0||Path.GetFullPath(path)!=path||
      !(path==Target||path.StartsWith(Target+"\\",StringComparison.Ordinal)||
        path.StartsWith(Fixture+"\\",StringComparison.Ordinal)))
    throw new IOException("FIXED_PROVISIONING_SCOPE_REQUIRED");
   if(descriptor==null||descriptor.Length<20||descriptor.Length>65536)
    throw new IOException("BOUNDED_SECURITY_DESCRIPTOR_REQUIRED");
   DirectoryInfo parent=new DirectoryInfo(path).Parent;
   while(parent!=null) {
    if(!parent.Exists||(parent.Attributes&FileAttributes.ReparsePoint)!=0)
     throw new IOException("EXISTING_REGULAR_ANCESTORS_REQUIRED");
    parent=parent.Parent;
   }
   GCHandle pin=GCHandle.Alloc(descriptor,GCHandleType.Pinned);
   try {
    SecurityAttributes security=new SecurityAttributes();
    security.Length=Marshal.SizeOf(typeof(SecurityAttributes));
    security.Descriptor=pin.AddrOfPinnedObject();security.InheritHandle=false;
    // CreateDirectory returns ERROR_ALREADY_EXISTS without adopting the object.
    // The final descriptor is provided at creation, not applied afterward.
    if(!CreateDirectoryW(path,ref security))throw new Win32Exception(Marshal.GetLastWin32Error());
   } finally {pin.Free();}
  }
 }
}
