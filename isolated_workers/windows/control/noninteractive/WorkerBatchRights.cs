// Targeted local-policy access. Only the existing worker's batch right can be added.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
namespace AIBS.WorkerBootstrap {
 public static class BatchRights {
  public const string WorkerSID="S-1-5-21-2133766663-4066672948-2456486318-1005";
  [StructLayout(LayoutKind.Sequential)] struct Attributes {public uint Length;public IntPtr RootDirectory,ObjectName;public uint Flags;public IntPtr SecurityDescriptor,SecurityQualityOfService;}
  [StructLayout(LayoutKind.Sequential)] struct Unicode {public ushort Length,MaximumLength;public IntPtr Buffer;}
  [DllImport("advapi32.dll")] static extern uint LsaOpenPolicy(IntPtr system,ref Attributes attrs,uint access,out IntPtr handle);
  [DllImport("advapi32.dll")] static extern uint LsaEnumerateAccountRights(IntPtr policy,IntPtr sid,out IntPtr rights,out uint count);
  [DllImport("advapi32.dll")] static extern uint LsaAddAccountRights(IntPtr policy,IntPtr sid,[In] Unicode[] rights,uint count);
  [DllImport("advapi32.dll")] static extern uint LsaClose(IntPtr handle);
  [DllImport("advapi32.dll")] static extern uint LsaFreeMemory(IntPtr buffer);
  [DllImport("advapi32.dll")] static extern uint LsaNtStatusToWinError(uint status);
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ConvertStringSidToSid(string text,out IntPtr sid);
  [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr ptr);
  static void Check(uint status){if(status!=0)throw new Win32Exception((int)LsaNtStatusToWinError(status));}
  static IntPtr Policy(bool add){var attrs=new Attributes();attrs.Length=(uint)Marshal.SizeOf(typeof(Attributes));IntPtr result;Check(LsaOpenPolicy(IntPtr.Zero,ref attrs,add?0x810u:0x800u,out result));return result;}
  static string[] Read(IntPtr policy,IntPtr sid){
   IntPtr values;uint count;uint status=LsaEnumerateAccountRights(policy,sid,out values,out count);
   if(status==0xC0000034u)return new string[0];Check(status);
   try{if(count>128)throw new InvalidOperationException("RIGHTS_BOUND");var result=new List<string>();int size=Marshal.SizeOf(typeof(Unicode));for(int i=0;i<count;i++){var item=(Unicode)Marshal.PtrToStructure(IntPtr.Add(values,i*size),typeof(Unicode));if(item.Length>256||(item.Length%2)!=0)throw new InvalidOperationException("RIGHT_NAME_BOUND");result.Add(Marshal.PtrToStringUni(item.Buffer,item.Length/2));}result.Sort(StringComparer.Ordinal);return result.ToArray();}
   finally{if(values!=IntPtr.Zero)LsaFreeMemory(values);}
  }
  public static string[] ReadWorker(){IntPtr policy=IntPtr.Zero,sid=IntPtr.Zero;try{if(!ConvertStringSidToSid(WorkerSID,out sid))throw new Win32Exception(Marshal.GetLastWin32Error());policy=Policy(false);return Read(policy,sid);}finally{if(policy!=IntPtr.Zero)LsaClose(policy);if(sid!=IntPtr.Zero)LocalFree(sid);}}
  public static string[] AddWorkerBatchOnly(){
   IntPtr policy=IntPtr.Zero,sid=IntPtr.Zero,text=IntPtr.Zero;
   try{
    if(!ConvertStringSidToSid(WorkerSID,out sid))throw new Win32Exception(Marshal.GetLastWin32Error());policy=Policy(true);
    var old=Read(policy,sid);if(Array.IndexOf(old,"SeDenyBatchLogonRight")>=0)throw new InvalidOperationException("EXPLICIT_BATCH_DENY_REQUIRES_REVIEW");
    string name="SeBatchLogonRight";text=Marshal.StringToHGlobalUni(name);var right=new Unicode{Length=(ushort)(name.Length*2),MaximumLength=(ushort)((name.Length+1)*2),Buffer=text};
    Check(LsaAddAccountRights(policy,sid,new Unicode[]{right},1));var after=Read(policy,sid);
    var expected=new HashSet<string>(old,StringComparer.Ordinal);expected.Add(name);if(!expected.SetEquals(after))throw new InvalidOperationException("UNEXPECTED_RIGHTS_CHANGE");return after;
   }finally{if(text!=IntPtr.Zero)Marshal.FreeHGlobal(text);if(policy!=IntPtr.Zero)LsaClose(policy);if(sid!=IntPtr.Zero)LocalFree(sid);}
  }
 }
}
