using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Principal;

namespace AIBS.WorkerObservation {
    public sealed class WorkerTokenQueryException : Win32Exception {
        public string Stage { get; private set; }
        public int InformationClass { get; private set; }
        public int RequiredLength { get; private set; }
        public int SuppliedLength { get; private set; }
        public string LengthUnit { get; private set; }
        internal WorkerTokenQueryException(int error, string stage, int informationClass,
                                           int requiredLength, int suppliedLength, string unit)
            : base(error,stage) {
            Stage=stage;
            InformationClass=informationClass;
            RequiredLength=(requiredLength >= 0 && requiredLength <= 1048576) ? requiredLength : -1;
            SuppliedLength=(suppliedLength >= 0 && suppliedLength <= 1048576) ? suppliedLength : -1;
            LengthUnit=unit;
        }
    }
    public sealed class WorkerGroupMetadata {
        public string SID { get; internal set; }
        public uint Attributes { get; internal set; }
    }
    public sealed class WorkerPrivilegeMetadata {
        public string Name { get; internal set; }
        public uint Attributes { get; internal set; }
    }
    public sealed class WorkerObservationMetadata {
        public int ProcessId { get; internal set; }
        public long CreationFileTimeUtc { get; internal set; }
        public string Executable { get; internal set; }
        public string UserSID { get; internal set; }
        public string IntegritySID { get; internal set; }
        public int TokenType { get; internal set; }
        public int ElevationType { get; internal set; }
        public bool Elevated { get; internal set; }
        public uint SessionId { get; internal set; }
        public WorkerGroupMetadata[] Groups { get; internal set; }
        public WorkerPrivilegeMetadata[] Privileges { get; internal set; }
        public bool ActiveAfterRead { get; internal set; }
    }

    // Metadata only: no token duplication, impersonation, adjustment or reuse.
    public static class WorkerTokenObservation {
        public const string WorkerSID = "S-1-5-21-2133766663-4066672948-2456486318-1005";
        const uint QueryLimitedInformation = 0x1000, TokenQuery = 0x8;
        const int BufferBound = 1048576, GroupBound = 256, PrivilegeBound = 128;
        [StructLayout(LayoutKind.Sequential)] struct FileTime { public uint Low, High; }
        [StructLayout(LayoutKind.Sequential)] struct SidAttributes { public IntPtr SID; public uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] struct GroupsFirst { public uint Count; public SidAttributes Group; }
        [StructLayout(LayoutKind.Sequential)] struct Luid { public uint Low; public int High; }
        [StructLayout(LayoutKind.Sequential)] struct LuidAttributes { public Luid Luid; public uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] struct PrivilegesFirst { public uint Count; public LuidAttributes Privilege; }

        [DllImport("kernel32.dll", SetLastError=true)]
        static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
        [DllImport("advapi32.dll", SetLastError=true)]
        static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
        [DllImport("kernel32.dll", SetLastError=true)]
        static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError=true)]
        static extern bool GetProcessTimes(IntPtr process, out FileTime creation, out FileTime exit, out FileTime kernel, out FileTime user);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern bool QueryFullProcessImageNameW(IntPtr process, uint flags, StringBuilder image, ref uint size);
        [DllImport("kernel32.dll", SetLastError=true)]
        static extern bool GetExitCodeProcess(IntPtr process, out uint code);
        [DllImport("advapi32.dll", SetLastError=true)]
        static extern bool GetTokenInformation(IntPtr token, int kind, IntPtr buffer, int size, out int needed);
        [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern bool LookupPrivilegeNameW(string system, ref Luid luid, StringBuilder name, ref int characters);

        static void Require(bool value, string code) { if (!value) throw new IOException(code); }
        static void NativeFailure(string stage) {
            throw new WorkerTokenQueryException(Marshal.GetLastWin32Error(),stage,0,0,0,"none");
        }
        static long Timestamp(FileTime value) { return unchecked(((long)value.High << 32) | value.Low); }

        sealed class TokenBuffer : IDisposable {
            public IntPtr Value;
            public int Length;
            public TokenBuffer(IntPtr token, int kind) {
                int needed;
                bool queried = GetTokenInformation(token, kind, IntPtr.Zero, 0, out needed);
                int error = Marshal.GetLastWin32Error();
                if (queried) throw new IOException("TOKEN_BUFFER_SIZE_QUERY_UNEXPECTED_SUCCESS");
                if (error != 122) throw new WorkerTokenQueryException(error,"TOKEN_BUFFER_SIZE_QUERY_FAILED",kind,needed,0,"bytes");
                Require(needed > 0 && needed <= BufferBound, "TOKEN_BUFFER_BOUND");
                Value = Marshal.AllocHGlobal(needed);
                try {
                    int returned;
                    if (!GetTokenInformation(token, kind, Value, needed, out returned))
                        throw new WorkerTokenQueryException(Marshal.GetLastWin32Error(),"TOKEN_INFORMATION_QUERY_FAILED",kind,returned,needed,"bytes");
                    Require(returned > 0 && returned <= needed, "TOKEN_BUFFER_RETURN_LENGTH");
                    Length = returned;
                } catch { Dispose(); throw; }
            }
            public void Range(int offset, int count) {
                Require(offset >= 0 && count >= 0 && offset <= Length && count <= Length - offset, "TOKEN_BUFFER_RANGE");
            }
            public IntPtr At(int offset, int count) { Range(offset,count); return IntPtr.Add(Value,offset); }
            public string SID(IntPtr pointer) {
                long start = Value.ToInt64(), address = pointer.ToInt64();
                Require(address >= start && address - start <= Length - 8, "TOKEN_SID_POINTER_RANGE");
                int offset = checked((int)(address - start));
                Range(offset,8);
                int revision = Marshal.ReadByte(pointer,0), count = Marshal.ReadByte(pointer,1);
                Require(revision == 1 && count <= 15, "TOKEN_SID_HEADER");
                int length = checked(8 + count * 4);
                Range(offset,length);
                byte[] bytes = new byte[length];
                Marshal.Copy(pointer,bytes,0,length);
                return new SecurityIdentifier(bytes,0).Value;
            }
            public void Dispose() { if (Value != IntPtr.Zero) { Marshal.FreeHGlobal(Value); Value=IntPtr.Zero; } }
        }

        static uint Number(IntPtr token, int kind) {
            // Known DWORD/enum classes have a fixed four-byte result. In
            // particular, TokenElevation may reject a NULL/0 sizing probe
            // with ERROR_BAD_LENGTH instead of ERROR_INSUFFICIENT_BUFFER.
            Require(kind == 8 || kind == 12 || kind == 18 || kind == 20,"FIXED_TOKEN_SCALAR_CLASS_REQUIRED");
            IntPtr buffer=Marshal.AllocHGlobal(4);
            try {
                int returned;
                if (!GetTokenInformation(token,kind,buffer,4,out returned))
                    throw new WorkerTokenQueryException(Marshal.GetLastWin32Error(),"TOKEN_SCALAR_QUERY_FAILED",kind,returned,4,"bytes");
                Require(returned == 4,"TOKEN_SCALAR_RETURN_LENGTH");
                return unchecked((uint)Marshal.ReadInt32(buffer));
            } finally { Marshal.FreeHGlobal(buffer); }
        }
        static string TokenSID(IntPtr token, int kind) {
            using (TokenBuffer buffer = new TokenBuffer(token,kind)) {
                IntPtr first = buffer.At(0,Marshal.SizeOf(typeof(SidAttributes)));
                return buffer.SID(Marshal.ReadIntPtr(first));
            }
        }
        static WorkerGroupMetadata[] ReadGroups(IntPtr token) {
            using (TokenBuffer buffer = new TokenBuffer(token,2)) {
                uint count = unchecked((uint)Marshal.ReadInt32(buffer.At(0,4)));
                Require(count <= GroupBound, "TOKEN_GROUP_COUNT_BOUND");
                int offset = Marshal.OffsetOf(typeof(GroupsFirst),"Group").ToInt32();
                int width = Marshal.SizeOf(typeof(SidAttributes));
                buffer.Range(offset,checked((int)count * width));
                WorkerGroupMetadata[] groups = new WorkerGroupMetadata[count];
                for (int i=0; i<groups.Length; i++) {
                    IntPtr item = buffer.At(checked(offset + i * width),width);
                    groups[i] = new WorkerGroupMetadata {
                        SID=buffer.SID(Marshal.ReadIntPtr(item)),
                        Attributes=unchecked((uint)Marshal.ReadInt32(item,IntPtr.Size))
                    };
                }
                return groups;
            }
        }
        static string PrivilegeName(Luid luid) {
            int characters = 0;
            bool queried = LookupPrivilegeNameW(null,ref luid,null,ref characters);
            int error = Marshal.GetLastWin32Error();
            if (queried) throw new IOException("PRIVILEGE_NAME_SIZE_QUERY_UNEXPECTED_SUCCESS");
            if (error != 122) throw new WorkerTokenQueryException(error,"PRIVILEGE_NAME_SIZE_QUERY_FAILED",3,characters,0,"characters");
            Require(characters > 0 && characters <= 256,"PRIVILEGE_NAME_BOUND");
            StringBuilder name = new StringBuilder(characters+1);
            int capacity = characters+1;
            if (!LookupPrivilegeNameW(null,ref luid,name,ref capacity))
                throw new WorkerTokenQueryException(Marshal.GetLastWin32Error(),"PRIVILEGE_NAME_QUERY_FAILED",3,capacity,characters+1,"characters");
            Require(capacity > 0 && capacity <= characters && name.Length == capacity,"PRIVILEGE_NAME_RETURN_LENGTH");
            return name.ToString();
        }
        static WorkerPrivilegeMetadata[] ReadPrivileges(IntPtr token) {
            using (TokenBuffer buffer = new TokenBuffer(token,3)) {
                uint count = unchecked((uint)Marshal.ReadInt32(buffer.At(0,4)));
                Require(count <= PrivilegeBound,"TOKEN_PRIVILEGE_COUNT_BOUND");
                int offset = Marshal.OffsetOf(typeof(PrivilegesFirst),"Privilege").ToInt32();
                int width = Marshal.SizeOf(typeof(LuidAttributes));
                buffer.Range(offset,checked((int)count * width));
                WorkerPrivilegeMetadata[] privileges = new WorkerPrivilegeMetadata[count];
                HashSet<string> names = new HashSet<string>(StringComparer.Ordinal);
                for (int i=0; i<privileges.Length; i++) {
                    LuidAttributes item = (LuidAttributes)Marshal.PtrToStructure(buffer.At(checked(offset+i*width),width),typeof(LuidAttributes));
                    string name = PrivilegeName(item.Luid);
                    Require(names.Add(name),"DUPLICATE_TOKEN_PRIVILEGE");
                    privileges[i] = new WorkerPrivilegeMetadata {Name=name,Attributes=item.Attributes};
                }
                return privileges;
            }
        }
        static bool PinProcess(IntPtr process, long expectedCreation, string expectedExe, out string image) {
            FileTime creation,exit,kernel,user;
            if (!GetProcessTimes(process,out creation,out exit,out kernel,out user)) NativeFailure("PROCESS_TIMES_QUERY_FAILED");
            Require(Timestamp(creation) == expectedCreation,"PROCESS_CREATION_IDENTITY_MISMATCH");
            StringBuilder path = new StringBuilder(32768);
            uint length = 32768;
            if (!QueryFullProcessImageNameW(process,0,path,ref length)) NativeFailure("PROCESS_IMAGE_QUERY_FAILED");
            Require(length > 0 && length < 32768 && path.Length == length,"PROCESS_IMAGE_LENGTH");
            image = path.ToString();
            Require(String.Equals(image,expectedExe,StringComparison.OrdinalIgnoreCase),"PROCESS_EXECUTABLE_MISMATCH");
            uint code;
            if (!GetExitCodeProcess(process,out code)) NativeFailure("PROCESS_EXIT_QUERY_FAILED");
            return Timestamp(exit) == 0 && code == 259;
        }

        public static WorkerObservationMetadata ObserveWorker(int pid, long expectedCreationFileTimeUtc, string expectedExe) {
            Require(pid > 0,"WORKER_PROCESS_ID_REQUIRED");
            Require(expectedCreationFileTimeUtc > 0,"PROCESS_CREATION_IDENTITY_REQUIRED");
            Require(Environment.Is64BitProcess,"X64_OBSERVER_REQUIRED");
            Require(expectedExe != null && expectedExe.Length > 3 && expectedExe.Length < 32768 &&
                    expectedExe.IndexOfAny(new char[]{'\0','\r','\n'}) < 0 &&
                    Char.IsLetter(expectedExe[0]) && expectedExe[1] == ':' && expectedExe[2] == '\\' &&
                    String.Equals(expectedExe,Path.GetFullPath(expectedExe),StringComparison.OrdinalIgnoreCase),
                    "CANONICAL_LOCAL_EXECUTABLE_REQUIRED");
            IntPtr process = OpenProcess(QueryLimitedInformation,false,pid);
            if (process == IntPtr.Zero) NativeFailure("PROCESS_QUERY_ACCESS_FAILED");
            try {
                string image;
                Require(PinProcess(process,expectedCreationFileTimeUtc,expectedExe,out image),"PROCESS_NOT_ACTIVE_BEFORE_READ");
                IntPtr token;
                if (!OpenProcessToken(process,TokenQuery,out token)) NativeFailure("TOKEN_QUERY_ACCESS_FAILED");
                WorkerObservationMetadata result;
                try {
                    string user = TokenSID(token,1);
                    int caller;
                    using (Process current = Process.GetCurrentProcess()) { caller=current.Id; }
                    Require(user == WorkerSID && pid != caller,"EXACT_EXTERNAL_WORKER_REQUIRED");
                    result = new WorkerObservationMetadata {
                        ProcessId=pid,CreationFileTimeUtc=expectedCreationFileTimeUtc,Executable=image,UserSID=user,
                        TokenType=checked((int)Number(token,8)),ElevationType=checked((int)Number(token,18)),
                        Elevated=Number(token,20) != 0,SessionId=Number(token,12),IntegritySID=TokenSID(token,25),
                        Groups=ReadGroups(token),Privileges=ReadPrivileges(token)
                    };
                } finally { CloseHandle(token); }
                string finalImage;
                result.ActiveAfterRead=PinProcess(process,expectedCreationFileTimeUtc,expectedExe,out finalImage);
                Require(String.Equals(image,finalImage,StringComparison.Ordinal),"PROCESS_IMAGE_CHANGED_DURING_READ");
                return result;
            } finally { CloseHandle(process); }
        }
    }
}
