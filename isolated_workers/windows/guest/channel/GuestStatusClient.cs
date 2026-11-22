using System;
using System.IO;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;

namespace AIBS.GuestChannel {
 public static class GuestStatusClient {
  const int MaximumJson=16384;
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static void Require(bool ok,string code){if(!ok)throw new InvalidOperationException(code);}
  static bool Hash(string value){return value!=null&&Regex.IsMatch(value,@"\A[a-f0-9]{64}\z");}
  static long Now(){return (long)Math.Floor((DateTime.UtcNow-new DateTime(1970,1,1,0,0,0,DateTimeKind.Utc)).TotalSeconds);}
  static string Fingerprint(X509Certificate certificate){using(SHA256 hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(certificate.GetRawCertData())).Replace("-","").ToLowerInvariant();}
  static Dictionary<string,object> Parse(string json) {
   Require(json!=null&&Utf8.GetByteCount(json)<=MaximumJson,"JSON_BOUND");
   try {
    JavaScriptSerializer parser=new JavaScriptSerializer();parser.MaxJsonLength=MaximumJson;parser.RecursionLimit=12;
    Dictionary<string,object> value=parser.DeserializeObject(json) as Dictionary<string,object>;
    Require(value!=null,"JSON_OBJECT_REQUIRED");return value;
   }catch(InvalidOperationException){throw;}catch{throw new InvalidOperationException("JSON_REJECTED");}
  }
  static string Text(Dictionary<string,object> data,string name){object value;Require(data.TryGetValue(name,out value)&&value is string,"STRING_FIELD_REQUIRED");return (string)value;}
  static void Fields(Dictionary<string,object> data,string[] expected) {
   Require(data.Count==expected.Length,"FIELDS_REFUSED");
   foreach(string key in expected)Require(data.ContainsKey(key),"FIELDS_REFUSED");
  }
  static string Quote(string value) {
   StringBuilder s=new StringBuilder("\"");
   foreach(char c in value) {
    switch(c) {
     case '"':s.Append("\\\"");break;case '\\':s.Append("\\\\");break;
     case '\b':s.Append("\\b");break;case '\f':s.Append("\\f");break;
     case '\n':s.Append("\\n");break;case '\r':s.Append("\\r");break;case '\t':s.Append("\\t");break;
     default:if(c<32)s.Append("\\u"+((int)c).ToString("x4",CultureInfo.InvariantCulture));else s.Append(c);break;
    }
   }
   return s.Append('"').ToString();
  }
  static string Canonical(object value,int depth) {
   Require(depth<=12,"JSON_DEPTH_BOUND");
   if(value==null)return "null";if(value is string)return Quote((string)value);if(value is bool)return (bool)value?"true":"false";
   if(value is int||value is long)return Convert.ToString(value,CultureInfo.InvariantCulture);
   Dictionary<string,object> map=value as Dictionary<string,object>;
   if(map!=null) {
    List<string> keys=new List<string>(map.Keys);keys.Sort(StringComparer.Ordinal);StringBuilder output=new StringBuilder("{");bool first=true;
    foreach(string key in keys){if(!first)output.Append(',');first=false;output.Append(Quote(key)).Append(':').Append(Canonical(map[key],depth+1));}
    return output.Append('}').ToString();
   }
   object[] array=value as object[];
   if(array!=null){StringBuilder output=new StringBuilder("[");for(int i=0;i<array.Length;i++){if(i>0)output.Append(',');output.Append(Canonical(array[i],depth+1));}return output.Append(']').ToString();}
   throw new InvalidOperationException("JSON_TYPE_REFUSED");
  }
  static Dictionary<string,object> Recipe(string json,long now) {
   Dictionary<string,object> r=Parse(json);
   Fields(r,new string[]{"host","port","server_certificate_sha256","guest_certificate_sha256","base_sha256","channel_epoch","worker","owner","expires_unix"});
   Require(Text(r,"host")=="10.0.2.2","FIXED_HOST_REQUIRED");
   object port=r["port"];Require(port is int&&(int)port==18443,"FIXED_PORT_REQUIRED");
   foreach(string name in new string[]{"server_certificate_sha256","guest_certificate_sha256","base_sha256","channel_epoch"})Require(Hash(Text(r,name)),"SHA256_OR_EPOCH_REQUIRED");
   string worker=Text(r,"worker"),owner=Text(r,"owner");
   Require(worker=="guest:"+Text(r,"guest_certificate_sha256"),"CERTIFICATE_WORKER_BINDING_REQUIRED");
   Require(Regex.IsMatch(owner,@"\A[A-Za-z0-9_:.-]{1,128}\z"),"OWNER_REQUIRED");
   object expiry=r["expires_unix"];Require(expiry is int||expiry is long||expiry is double||expiry is decimal,"EXPIRY_REQUIRED");
   double seconds=Convert.ToDouble(expiry,CultureInfo.InvariantCulture);
   Require(!Double.IsNaN(seconds)&&!Double.IsInfinity(seconds)&&seconds>now&&seconds<=now+1805,"FRESH_BOUNDED_RECIPE_REQUIRED");
   return r;
  }
  static void Operation(string operation){Require(operation=="status"||operation=="gateway_health"||operation=="model_version","OPERATION_REFUSED");}
  public static string BuildRequest(string recipeJson,string operation,long issued,string nonce) {
   Dictionary<string,object> r=Recipe(recipeJson,issued);Operation(operation);
   Require(Regex.IsMatch(nonce??"", @"\A[a-f0-9]{32}\z"),"NONCE_REQUIRED");
   Dictionary<string,object> body=new Dictionary<string,object>();
   body.Add("base_sha256",Text(r,"base_sha256"));body.Add("channel_epoch",Text(r,"channel_epoch"));
   body.Add("issued",issued);body.Add("nonce",nonce);body.Add("operation",operation);body.Add("version",1);
   return Canonical(body,0);
  }
  static void False(Dictionary<string,object> data,string name){object value;Require(data.TryGetValue(name,out value)&&value is bool&&!(bool)value,"AUTHORITY_REFUSED");}
  public static string ValidateResponse(string recipeJson,string operation,string nonce,string response,long now) {
   Dictionary<string,object> r=Recipe(recipeJson,now),data=Parse(response);Operation(operation);
   Fields(data,new string[]{"base_sha256","channel_epoch","operation","request_nonce","worker","owner","result","worker_admitted","execution_authorized","apply_authorized"});
   Require(response==Canonical(data,0),"NONCANONICAL_RESPONSE");
   Require(Text(data,"request_nonce")==nonce&&Text(data,"operation")==operation,"RESPONSE_CORRELATION_REFUSED");
   foreach(string name in new string[]{"worker","owner","base_sha256","channel_epoch"})Require(Text(data,name)==Text(r,name),"RESPONSE_SCOPE_REFUSED");
   foreach(string name in new string[]{"worker_admitted","execution_authorized","apply_authorized"})False(data,name);
   Dictionary<string,object> result=data["result"] as Dictionary<string,object>;Require(result!=null&&result.Count<=16,"RESULT_OBJECT_REQUIRED");
   foreach(string name in new string[]{"worker_admitted","execution_authorized","apply_authorized"})if(result.ContainsKey(name))False(result,name);
   if(result.ContainsKey("verification_status"))Require(Text(result,"verification_status")=="not_run","VERIFICATION_AUTHORITY_REFUSED");
   return Canonical(data,0);
  }
  static X509Certificate2 ClientCertificate(string expected) {
   using(X509Store store=new X509Store(StoreName.My,StoreLocation.CurrentUser)) {
    store.Open(OpenFlags.ReadOnly|OpenFlags.OpenExistingOnly);X509Certificate2 selected=null;
    Require(store.Certificates.Count<=1000,"CERTIFICATE_STORE_BOUND");
    foreach(X509Certificate2 certificate in store.Certificates) {
     if(Fingerprint(certificate)==expected){Require(selected==null,"AMBIGUOUS_CLIENT_CERTIFICATE");selected=certificate;}
    }
    Require(selected!=null&&selected.HasPrivateKey,"DEDICATED_CLIENT_CERTIFICATE_REQUIRED");
    Require(selected.NotBefore.ToUniversalTime()<=DateTime.UtcNow&&selected.NotAfter.ToUniversalTime()>DateTime.UtcNow,"CLIENT_CERTIFICATE_EXPIRED");
    ECDsa privateKey=ECDsaCertificateExtensions.GetECDsaPrivateKey(selected);
    try{ECDsaCng cng=privateKey as ECDsaCng;Require(cng!=null&&cng.Key.ExportPolicy==CngExportPolicies.None,"NONEXPORTABLE_CNG_KEY_REQUIRED");}
    finally{if(privateKey!=null)privateKey.Dispose();}
    return selected;
   }
  }
  static bool ServerCertificate(object sender,X509Certificate certificate,X509Chain chain,SslPolicyErrors errors,string expected) {
   if(certificate==null||(errors&SslPolicyErrors.RemoteCertificateNameMismatch)!=0||(errors&SslPolicyErrors.RemoteCertificateNotAvailable)!=0)return false;
   try{using(X509Certificate2 c=new X509Certificate2(certificate)){return Fingerprint(c)==expected&&c.NotBefore.ToUniversalTime()<=DateTime.UtcNow&&c.NotAfter.ToUniversalTime()>DateTime.UtcNow;}}catch{return false;}
  }
  static string Line(Stream stream,ref int total) {
   StringBuilder output=new StringBuilder();
   while(true){int b=stream.ReadByte();Require(b>=0,"SHORT_HTTP_HEADER");total++;Require(total<=8192&&b<=127,"HTTP_HEADER_BOUND");if(b==10){Require(output.Length>0&&output[output.Length-1]=='\r',"HTTP_LINE_END_REQUIRED");return output.ToString(0,output.Length-1);}output.Append((char)b);}
  }
  public static string Send(string recipeJson,string operation) {
   long issued=Now();Dictionary<string,object> recipe=Recipe(recipeJson,issued);string nonce=Guid.NewGuid().ToString("N"),body=BuildRequest(recipeJson,operation,issued,nonce);
   using(X509Certificate2 certificate=ClientCertificate(Text(recipe,"guest_certificate_sha256")))
   using(TcpClient tcp=new TcpClient())
   using(Timer deadline=new Timer(delegate(object state){try{tcp.Close();}catch{}},null,4000,Timeout.Infinite)) {
    IAsyncResult connect=tcp.BeginConnect("10.0.2.2",18443,null,null);
    using(WaitHandle wait=connect.AsyncWaitHandle){Require(wait.WaitOne(3000),"CONNECT_TIMEOUT");tcp.EndConnect(connect);}
    tcp.ReceiveTimeout=3000;tcp.SendTimeout=3000;
    using(SslStream tls=new SslStream(tcp.GetStream(),false,delegate(object sender,X509Certificate remote,X509Chain chain,SslPolicyErrors errors){return ServerCertificate(sender,remote,chain,errors,Text(recipe,"server_certificate_sha256"));})) {
     tls.ReadTimeout=3000;tls.WriteTimeout=3000;X509CertificateCollection clients=new X509CertificateCollection();clients.Add(certificate);
     tls.AuthenticateAsClient("10.0.2.2",clients,SslProtocols.Tls12,false);Require(tls.IsAuthenticated&&tls.IsMutuallyAuthenticated&&tls.IsEncrypted,"MUTUAL_TLS_REQUIRED");
     byte[] bytes=Utf8.GetBytes(body);
     byte[] headers=Encoding.ASCII.GetBytes("POST /v1/guest-message HTTP/1.0\r\nHost: 10.0.2.2:18443\r\nContent-Type: application/json\r\nContent-Length: "+bytes.Length.ToString(CultureInfo.InvariantCulture)+"\r\nConnection: close\r\n\r\n");
     tls.Write(headers,0,headers.Length);tls.Write(bytes,0,bytes.Length);tls.Flush();
     int total=0;string status=Line(tls,ref total);Require(Regex.IsMatch(status,@"\AHTTP/1\.[01] 200(?: |$)"),"CHANNEL_HTTP_STATUS_REFUSED");
     int length=-1;bool json=false;
     while(true){string line=Line(tls,ref total);if(line.Length==0)break;int colon=line.IndexOf(':');Require(colon>0,"HTTP_HEADER_REFUSED");string name=line.Substring(0,colon).ToLowerInvariant(),value=line.Substring(colon+1).Trim();
      if(name=="content-length"){Require(length<0&&Regex.IsMatch(value,@"\A[0-9]{1,5}\z"),"HTTP_LENGTH_REFUSED");length=Int32.Parse(value,CultureInfo.InvariantCulture);}
      if(name=="content-type"){Require(!json&&value=="application/json","JSON_CONTENT_TYPE_REQUIRED");json=true;}
      Require(name!="transfer-encoding"&&name!="content-encoding","HTTP_ENCODING_REFUSED");
     }
     Require(json&&length>0&&length<=MaximumJson,"HTTP_BODY_BOUND");
     byte[] response=new byte[length];int read=0;
     while(read<length){int n=tls.Read(response,read,length-read);Require(n>0,"SHORT_HTTP_BODY");read+=n;}
     return ValidateResponse(recipeJson,operation,nonce,Utf8.GetString(response),Now());
    }
   }
  }
 }
}
