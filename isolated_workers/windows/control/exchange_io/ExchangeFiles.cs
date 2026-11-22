using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using Microsoft.Win32.SafeHandles;

namespace AIBS.ExchangeIO {
 public sealed class FileReceipt {
  public string Path {get;internal set;}
  public long Length {get;internal set;}
  public string SHA256 {get;internal set;}
  public string FileIdentity {get;internal set;}
  public bool ExecutionAuthorized {get{return false;}}
  public bool ApplyAuthorized {get{return false;}}
 }
 public sealed class ExchangeRoot : IDisposable {
  const uint Sync=0x100000,ReadAttributes=0x80,Directory=0x10,Reparse=0x400;
  const uint OpenReparse=0x200000,SyncIO=0x20,DirectoryFile=1,NonDirectoryFile=0x40;
  readonly List<SafeFileHandle> roots=new List<SafeFileHandle>();
  readonly HashSet<string> allowed=new HashSet<string>(StringComparer.Ordinal);
  readonly object gate=new object();
  bool disposed;
  [StructLayout(LayoutKind.Sequential)] struct UnicodeString {public ushort Length,MaximumLength;public IntPtr Buffer;}
  [StructLayout(LayoutKind.Sequential)] struct ObjectAttributes {public int Length;public IntPtr RootDirectory,ObjectName;public uint Attributes;public IntPtr SecurityDescriptor,SecurityQualityOfService;}
  [StructLayout(LayoutKind.Sequential)] struct IOStatus {public IntPtr Status;public UIntPtr Information;}
  [StructLayout(LayoutKind.Sequential)] struct Info {
   public uint Attributes;public System.Runtime.InteropServices.ComTypes.FILETIME Creation,Access,Write;
   public uint VolumeSerial,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;
  }
  [DllImport("ntdll.dll")] static extern int NtCreateFile(out IntPtr handle,uint access,ref ObjectAttributes attributes,out IOStatus status,IntPtr allocation,uint fileAttributes,uint share,uint disposition,uint options,IntPtr ea,uint eaLength);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFileW(string path,uint access,uint share,IntPtr security,uint disposition,uint flags,IntPtr template);
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle handle,out Info info);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool GetVolumeInformationByHandleW(SafeFileHandle handle,StringBuilder label,uint labelLength,out uint serial,out uint maxComponent,out uint flags,StringBuilder filesystem,uint filesystemLength);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern uint GetDriveTypeW(string path);
  static void Require(bool condition,string code){if(!condition)throw new IOException(code);}
  static Info Details(SafeFileHandle h,bool directory) {
   Info info;Require(GetFileInformationByHandle(h,out info),"FILE_INFORMATION_UNAVAILABLE");
   Require((info.Attributes&Reparse)==0,"REPARSE_REFUSED");
   Require(((info.Attributes&Directory)!=0)==directory,"FILE_TYPE_MISMATCH");
   if(!directory)Require(info.Links==1,"MULTIPLE_LINKS_REFUSED");return info;
  }
  static string Identity(Info info){return info.VolumeSerial.ToString("x8")+":"+info.IndexHigh.ToString("x8")+info.IndexLow.ToString("x8");}
  static void Segment(string name) {
   Require(name!=null&&Regex.IsMatch(name,@"\A[A-Za-z0-9_. -]{1,96}\z")&&name!="."&&name!=".."&&!name.EndsWith(".")&&!name.EndsWith(" "),"CANONICAL_COMPONENT_REQUIRED");
   string stem=name.Split('.')[0].ToUpperInvariant();Require(!Regex.IsMatch(stem,@"\A(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])\z"),"DEVICE_NAME_REFUSED");
  }
  static string[] Relative(string path) {
   Require(path!=null&&path.Length<=192,"RELATIVE_PATH_BOUND");string[] parts=path.Split('/');
   Require(parts.Length>=2&&parts.Length<=16&&(parts[0]=="inputs"||parts[0]=="outputs"),"EXCHANGE_ROOT_REQUIRED");
   foreach(string part in parts){Segment(part);Require(Regex.IsMatch(part,@"\A[A-Za-z0-9_]"),"HIDDEN_OR_ALIAS_REFUSED");
    Require(!Regex.IsMatch(part,@"\.(?:db|sqlite|sqlite3|db-wal|db-shm|pem|key|pfx|vdi|gguf|safetensors)\z",RegexOptions.IgnoreCase),"PRIVATE_STORE_TYPE_REFUSED");}
   return parts;
  }
  static SafeFileHandle Child(SafeFileHandle parent,string name,bool directory,bool create) {
   Segment(name);IntPtr buffer=IntPtr.Zero,unicode=IntPtr.Zero;
   try {
    buffer=Marshal.StringToHGlobalUni(name);UnicodeString u=new UnicodeString();u.Length=checked((ushort)(name.Length*2));u.MaximumLength=checked((ushort)(u.Length+2));u.Buffer=buffer;
    unicode=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(UnicodeString)));Marshal.StructureToPtr(u,unicode,false);
    ObjectAttributes a=new ObjectAttributes();a.Length=Marshal.SizeOf(typeof(ObjectAttributes));a.RootDirectory=parent.DangerousGetHandle();a.ObjectName=unicode;a.Attributes=0x40|0x1000; // CASE_INSENSITIVE | DONT_REPARSE
    IOStatus io;IntPtr raw;uint access=directory?(ReadAttributes|Sync):(create?0xC0100080:0x80100080);
    int status=NtCreateFile(out raw,access,ref a,out io,IntPtr.Zero,directory?Directory:0x80,directory?3U:1U,create?2U:1U,OpenReparse|SyncIO|(directory?DirectoryFile:NonDirectoryFile)|(create?2U:0U),IntPtr.Zero,0);
    Require(status>=0,"RELATIVE_OPEN_REFUSED_"+unchecked((uint)status).ToString("x8"));
    SafeFileHandle h=new SafeFileHandle(raw,true);
    try {Details(h,directory);return h;}catch{h.Dispose();throw;}
   } finally {if(unicode!=IntPtr.Zero)Marshal.FreeHGlobal(unicode);if(buffer!=IntPtr.Zero)Marshal.FreeHGlobal(buffer);}
  }
  static List<SafeFileHandle> RootHandles(string path) {
   Require(path!=null&&path.Length<=1024&&Regex.IsMatch(path,@"\A[A-Za-z]:\\"),"FIXED_LOCAL_ROOT_REQUIRED");
   Require(path==System.IO.Path.GetFullPath(path)&&!path.EndsWith("\\"),"CANONICAL_ROOT_REQUIRED");
   string drive=path.Substring(0,3);Require(GetDriveTypeW(drive)==3,"FIXED_VOLUME_REQUIRED");
   string[] parts=path.Substring(3).Split('\\');Require(parts.Length>=2,"DEDICATED_ROOT_REQUIRED");foreach(string part in parts)Segment(part);
   List<SafeFileHandle> handles=new List<SafeFileHandle>();
   try {
    SafeFileHandle h=CreateFileW("\\\\?\\"+drive,ReadAttributes|Sync,3,IntPtr.Zero,3,0x02000000|OpenReparse,IntPtr.Zero);
    Require(!h.IsInvalid,"VOLUME_ROOT_UNAVAILABLE");handles.Add(h);Details(h,true);
    StringBuilder filesystem=new StringBuilder(32),label=new StringBuilder(128);uint serial,maximum,flags;
    Require(GetVolumeInformationByHandleW(h,label,128,out serial,out maximum,out flags,filesystem,32)&&filesystem.ToString()=="NTFS","NTFS_REQUIRED");
    foreach(string part in parts){h=Child(h,part,true,false);handles.Add(h);}return handles;
   }catch{for(int i=handles.Count-1;i>=0;i--)handles[i].Dispose();throw;}
  }
  public static string Describe(string path){List<SafeFileHandle> h=RootHandles(path);try{return Identity(Details(h[h.Count-1],true));}finally{for(int i=h.Count-1;i>=0;i--)h[i].Dispose();}}
  public static ExchangeRoot Open(string path,string expectedIdentity,string[] approvedPaths) {
   Require(expectedIdentity!=null&&Regex.IsMatch(expectedIdentity,@"\A[a-f0-9]{8}:[a-f0-9]{16}\z"),"ROOT_IDENTITY_REQUIRED");
   Require(approvedPaths!=null&&approvedPaths.Length<=64,"APPROVED_PATHS_REQUIRED");
   ExchangeRoot session=new ExchangeRoot();HashSet<string> aliases=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   try{
    foreach(string relative in approvedPaths){Relative(relative);Require(aliases.Add(relative),"PATH_ALIAS_COLLISION");session.allowed.Add(relative);}
    session.roots.AddRange(RootHandles(path));Require(Identity(Details(session.roots[session.roots.Count-1],true))==expectedIdentity,"ROOT_IDENTITY_MISMATCH");return session;
   }catch{session.Dispose();throw;}
  }
  List<SafeFileHandle> Parents(string relative) {
   Require(!disposed,"DISPOSED_EXCHANGE");Relative(relative);Require(allowed.Contains(relative),"UNAPPROVED_PATH");
   string[] parts=relative.Split('/');List<SafeFileHandle> parents=new List<SafeFileHandle>();SafeFileHandle parent=roots[roots.Count-1];
   try {for(int i=0;i<parts.Length-1;i++){parent=Child(parent,parts[i],true,false);parents.Add(parent);}return parents;}
   catch{for(int i=parents.Count-1;i>=0;i--)parents[i].Dispose();throw;}
  }
  static string Hash(byte[] data){using(SHA256 hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(data)).Replace("-","").ToLowerInvariant();}
  static void Digest(string digest){Require(digest!=null&&Regex.IsMatch(digest,@"\A[a-f0-9]{64}\z"),"SHA256_REQUIRED");}
  public FileReceipt Publish(string relative,byte[] bytes,string digest) {
   lock(gate){return PublishLocked(relative,bytes,digest);}
  }
  FileReceipt PublishLocked(string relative,byte[] bytes,string digest) {
   Require(bytes!=null&&bytes.Length<=1048576,"FILE_BYTE_BOUND");Digest(digest);Require(Hash(bytes)==digest,"INPUT_HASH_MISMATCH");
   List<SafeFileHandle> parents=Parents(relative);
   try {
    string[] parts=relative.Split('/');using(SafeFileHandle file=Child(parents[parents.Count-1],parts[parts.Length-1],false,true)) {
     // CREATE, never overwrite/open-if. Any interrupted partial file remains
     // evidence, is not a successful receipt and is never silently retried.
     using(FileStream stream=new FileStream(file,FileAccess.ReadWrite,4096,false)) {
      stream.Write(bytes,0,bytes.Length);stream.Flush(true);stream.Position=0;
      byte[] check=new byte[bytes.Length];int used=0;while(used<check.Length){int n=stream.Read(check,used,check.Length-used);Require(n>0,"SHORT_READ");used+=n;}
      Require(stream.ReadByte()==-1&&Hash(check)==digest,"PUBLISHED_BYTES_MISMATCH");Info info=Details(file,false);
      return new FileReceipt{Path=relative,Length=bytes.Length,SHA256=digest,FileIdentity=Identity(info)};
     }
    }
   }finally{for(int i=parents.Count-1;i>=0;i--)parents[i].Dispose();}
  }
  public byte[] ReadVerified(string relative,int expectedLength,string digest) {
   lock(gate){return ReadLocked(relative,expectedLength,digest);}
  }
  byte[] ReadLocked(string relative,int expectedLength,string digest) {
   Require(expectedLength>=0&&expectedLength<=1048576,"FILE_LENGTH_BOUND");Digest(digest);List<SafeFileHandle> parents=Parents(relative);
   try {string[] parts=relative.Split('/');using(SafeFileHandle file=Child(parents[parents.Count-1],parts[parts.Length-1],false,false)) {
    Info info=Details(file,false);Require(info.SizeHigh==0&&info.SizeLow==(uint)expectedLength,"FILE_LENGTH_MISMATCH");
    using(FileStream stream=new FileStream(file,FileAccess.Read,4096,false)){byte[] bytes=new byte[expectedLength];int used=0;while(used<bytes.Length){int n=stream.Read(bytes,used,bytes.Length-used);Require(n>0,"SHORT_READ");used+=n;}Require(stream.ReadByte()==-1&&Hash(bytes)==digest,"FILE_HASH_MISMATCH");Details(file,false);return bytes;}
   }}finally{for(int i=parents.Count-1;i>=0;i--)parents[i].Dispose();}
  }
  public void Dispose(){lock(gate){if(disposed)return;disposed=true;for(int i=roots.Count-1;i>=0;i--)roots[i].Dispose();}}
 }
}
