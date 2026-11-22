using System;
using System.IO;
using System.Text;
using System.Security.Cryptography;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

internal sealed class WheelMedia : IDisposable {
    internal const string Volume="AIBS_WHEELS_V1",Root=@"D:\",Helper="AI-BS Wheel Setup.exe";
    internal const string Psutil="psutil-7.2.2-cp37-abi3-win_amd64.whl",Pywin="pywin32-312-cp313-cp313-win_amd64.whl";
    internal const string PsutilSHA="EB7E81434C8D223EC4A219B5FC1C47D0417B12BE7EA866E24FB5AD6E84B3D988",PywinSHA="C53E878D15A1C44788082BFE712A905433473AA38F86375B7CF8B45E3ACBAAF9";
    readonly Dictionary<string,FileStream> handles=new Dictionary<string,FileStream>(StringComparer.Ordinal);
    WheelMedia(){}
    internal static string Hash(Stream file){file.Position=0;using(var sha=SHA256.Create()){string hash=BitConverter.ToString(sha.ComputeHash(file)).Replace("-","");file.Position=0;return hash;}}
    internal static FileStream OpenPinned(string path,long length,string hash){
        WheelPaths.NoReparse(path);var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);
        try{WheelPaths.NoReparse(path);if(file.Length!=length||!String.Equals(Hash(file),hash,StringComparison.OrdinalIgnoreCase))throw new IOException("MEDIA_PIN_MISMATCH");return file;}catch{file.Dispose();throw;}
    }
    static Dictionary<string,object> Map(object value,string[] keys){
        var map=value as Dictionary<string,object>;if(map==null||map.Count!=keys.Length)throw new IOException("MANIFEST_FIELDS");
        foreach(string key in keys)if(!map.ContainsKey(key))throw new IOException("MANIFEST_FIELDS");return map;
    }
    static long Number(object value){if(!(value is int)&&!(value is long))throw new IOException("MANIFEST_NUMBER");return Convert.ToInt64(value);}
    internal static void ValidateManifest(string text,Dictionary<string,long> sizes,Dictionary<string,string> hashes){
        if(text.Length>16384||Regex.Matches(text,"\"(?:[^\"\\\\]|\\\\.)*\"\\s*:").Count!=15)throw new IOException("MANIFEST_SHAPE");
        var serializer=new JavaScriptSerializer();serializer.MaxJsonLength=16384;serializer.RecursionLimit=5;
        var root=Map(serializer.DeserializeObject(text),new string[]{"schema","volume_label","files"});
        if(Number(root["schema"])!=1||!Object.Equals(root["volume_label"],Volume))throw new IOException("MANIFEST_VERSION");
        var files=root["files"] as object[];if(files==null||files.Length!=4)throw new IOException("MANIFEST_FILE_COUNT");
        var seen=new HashSet<string>(StringComparer.Ordinal);
        foreach(object value in files){
            var item=Map(value,new string[]{"name","length","sha256"});string name=item["name"] as string,hash=item["sha256"] as string;
            if(name==null||!sizes.ContainsKey(name)||!seen.Add(name)||Number(item["length"])!=sizes[name]||hash==null||!Regex.IsMatch(hash,@"^[0-9a-fA-F]{64}$")||!String.Equals(hash,hashes[name],StringComparison.OrdinalIgnoreCase))throw new IOException("MANIFEST_PIN_MISMATCH");
        }
    }
    internal static WheelMedia Open(string currentExe){
        if(!WheelPaths.Equal(currentExe,Path.Combine(Root,Helper)))throw new IOException("LAUNCH_FROM_FIXED_D_MEDIA_REQUIRED");
        var drive=new DriveInfo(Root);if(drive.DriveType!=DriveType.CDRom||!drive.IsReady||drive.VolumeLabel!=Volume)throw new IOException("FIXED_READONLY_CDROM_REQUIRED");
        WheelPaths.NoReparse(Root);var expected=new HashSet<string>(new string[]{Helper,Psutil,Pywin,"README.txt","manifest.json"},StringComparer.Ordinal);
        var entries=new DirectoryInfo(Root).GetFileSystemInfos();if(entries.Length!=5)throw new IOException("UNEXPECTED_MEDIA_FILES");
        foreach(var entry in entries){WheelPaths.CheckAttributes(entry.Attributes);if((entry.Attributes&FileAttributes.Directory)!=0||!expected.Remove(entry.Name))throw new IOException("UNEXPECTED_MEDIA_FILES");}
        if(expected.Count!=0)throw new IOException("MISSING_MEDIA_FILES");
        var media=new WheelMedia();
        try{
            foreach(string name in new string[]{Helper,Psutil,Pywin,"README.txt","manifest.json"}){
                string path=Path.Combine(Root,name);WheelPaths.NoReparse(path);media.handles.Add(name,new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read));WheelPaths.NoReparse(path);
            }
            if(media.handles[Psutil].Length!=137737||Hash(media.handles[Psutil])!=PsutilSHA||media.handles[Pywin].Length!=6914298||Hash(media.handles[Pywin])!=PywinSHA)throw new IOException("WHEEL_PIN_MISMATCH");
            if(media.handles[Helper].Length<1024||media.handles[Helper].Length>1048576||media.handles["README.txt"].Length<1||media.handles["README.txt"].Length>8192||media.handles["manifest.json"].Length<1||media.handles["manifest.json"].Length>16384)throw new IOException("MEDIA_SIZE_BOUND");
            var sizes=new Dictionary<string,long>(StringComparer.Ordinal);var hashes=new Dictionary<string,string>(StringComparer.Ordinal);
            foreach(string name in new string[]{Helper,Psutil,Pywin,"README.txt"}){sizes[name]=media.handles[name].Length;hashes[name]=Hash(media.handles[name]);}
            string text;using(var reader=new StreamReader(media.handles["manifest.json"],new UTF8Encoding(false,true),false,1024,true))text=reader.ReadToEnd();
            ValidateManifest(text,sizes,hashes);return media;
        }catch{media.Dispose();throw;}
    }
    public void Dispose(){foreach(var handle in handles.Values)handle.Dispose();handles.Clear();}
}
