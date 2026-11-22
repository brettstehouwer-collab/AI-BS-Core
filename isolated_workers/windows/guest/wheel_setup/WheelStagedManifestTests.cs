using System;
using System.IO;
using System.Collections.Generic;
internal static class WheelStagedManifestTests {
    static int Main(string[] args){
        string root=Path.GetFullPath(args[0]);WheelPaths.NoReparse(root);
        var sizes=new Dictionary<string,long>(StringComparer.Ordinal);var hashes=new Dictionary<string,string>(StringComparer.Ordinal);
        var held=new List<FileStream>();
        try{
            foreach(string name in new string[]{WheelMedia.Helper,WheelMedia.Psutil,WheelMedia.Pywin,"README.txt"}){
                string path=Path.Combine(root,name);WheelPaths.NoReparse(path);var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);held.Add(stream);
                sizes[name]=stream.Length;hashes[name]=WheelMedia.Hash(stream);
            }
            WheelMedia.ValidateManifest(File.ReadAllText(Path.Combine(root,"manifest.json")),sizes,hashes);
            if(sizes[WheelMedia.Psutil]!=137737||hashes[WheelMedia.Psutil]!=WheelMedia.PsutilSHA||sizes[WheelMedia.Pywin]!=6914298||hashes[WheelMedia.Pywin]!=WheelMedia.PywinSHA)throw new IOException("Approved wheel pins differ.");
            Console.WriteLine("PASS actual staged manifest accepted by the production strict parser; both independent wheel pins matched; no guest/media entry or runtime invoked.");return 0;
        }finally{foreach(var stream in held)stream.Dispose();}
    }
}
