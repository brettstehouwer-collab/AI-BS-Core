using System;
using System.IO;
using System.Text;
using System.Xml;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
internal static class WheelManifestTests {
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr LoadLibraryEx(string file,IntPtr reserved,uint flags);
    [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr FindResource(IntPtr module,IntPtr name,IntPtr type);
    [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr LoadResource(IntPtr module,IntPtr resource);
    [DllImport("kernel32.dll",SetLastError=true)]static extern uint SizeofResource(IntPtr module,IntPtr resource);
    [DllImport("kernel32.dll")]static extern IntPtr LockResource(IntPtr resource);
    [DllImport("kernel32.dll")]static extern bool FreeLibrary(IntPtr module);
    static int Main(string[] args){
        // Data/resource-only mapping: never invokes the guest executable entry point.
        IntPtr module=LoadLibraryEx(Path.GetFullPath(args[0]),IntPtr.Zero,0x20|0x40);
        if(module==IntPtr.Zero)throw new IOException("Cannot read PE as resource-only data.");
        try{
            IntPtr resource=FindResource(module,new IntPtr(1),new IntPtr(24));if(resource==IntPtr.Zero)throw new IOException("Missing embedded Win32 manifest.");
            uint count=SizeofResource(module,resource);if(count<1||count>16384)throw new IOException("Unexpected manifest size.");
            IntPtr data=LockResource(LoadResource(module,resource));if(data==IntPtr.Zero)throw new IOException("Cannot read manifest.");
            var bytes=new byte[count];Marshal.Copy(data,bytes,0,bytes.Length);
            var document=new XmlDocument();document.XmlResolver=null;
            var settings=new XmlReaderSettings();settings.DtdProcessing=DtdProcessing.Prohibit;settings.XmlResolver=null;
            using(var stream=new MemoryStream(bytes,false))using(var reader=XmlReader.Create(stream,settings))document.Load(reader);
            var nodes=document.SelectNodes("//*[local-name()='requestedExecutionLevel']");
            if(nodes.Count!=1||nodes[0].Attributes["level"]==null||nodes[0].Attributes["level"].Value!="asInvoker"||nodes[0].Attributes["uiAccess"]==null||nodes[0].Attributes["uiAccess"].Value!="false")throw new IOException("Embedded manifest does not explicitly prohibit elevation/UI access.");
            Console.WriteLine("PASS actual embedded RT_MANIFEST/1 level=asInvoker uiAccess=false; resource-only read, no entry point invoked.");
            using(var sha=SHA256.Create())Console.WriteLine("Embedded manifest bytes="+bytes.Length+" SHA256="+BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-",""));
            Console.WriteLine(Encoding.UTF8.GetString(bytes));return 0;
        }finally{FreeLibrary(module);}
    }
}
