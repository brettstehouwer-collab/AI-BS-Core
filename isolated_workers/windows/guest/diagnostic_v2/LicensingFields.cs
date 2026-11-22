using System;
using System.Globalization;
using System.Text.RegularExpressions;
internal static class LicensingFields {
    internal const string Query="SELECT Name,LicenseStatus,GracePeriodRemaining,LicenseStatusReason,EvaluationEndDate FROM SoftwareLicensingProduct WHERE Name LIKE 'Windows%' AND PartialProductKey IS NOT NULL";
    internal static string Reason(object value) {
        if(value==null||value==DBNull.Value)return "UNAVAILABLE";
        uint reason;
        if(value is uint)reason=(uint)value;
        else if(value is int&&(int)value>=0)reason=(uint)(int)value;
        else if(value is long&&(long)value>=0&&(long)value<=UInt32.MaxValue)reason=(uint)(long)value;
        else if(value is ushort)reason=(ushort)value;
        else if(value is byte)reason=(byte)value;
        else return "INVALID";
        return reason.ToString(CultureInfo.InvariantCulture)+" (0x"+reason.ToString("X8",CultureInfo.InvariantCulture)+")";
    }
    internal static string EndDate(object value) {
        if(value==null||value==DBNull.Value)return "UNAVAILABLE";
        var text=value as string;
        if(text==null||text.Length!=25||!Regex.IsMatch(text,@"^[0-9]{14}\.[0-9]{6}[+-][0-9]{3}$"))return "INVALID";
        DateTime date;int minutes;
        if(!DateTime.TryParseExact(text.Substring(0,21),"yyyyMMddHHmmss.ffffff",CultureInfo.InvariantCulture,DateTimeStyles.None,out date)||
           !Int32.TryParse(text.Substring(22,3),NumberStyles.None,CultureInfo.InvariantCulture,out minutes)||minutes>840)return "INVALID";
        if(text[21]=='-')minutes=-minutes;
        try{return new DateTimeOffset(DateTime.SpecifyKind(date,DateTimeKind.Unspecified),TimeSpan.FromMinutes(minutes)).UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'",CultureInfo.InvariantCulture);}
        catch(ArgumentException){return "INVALID";}
    }
    static string Read(Func<string,object> read,string name,Func<object,string> format) {
        try{return format(read(name));}catch(Exception){return "READ_ERROR";}
    }
    internal static string ExtraFields(Func<string,object> read) {
        return " | LicenseStatusReason="+Read(read,"LicenseStatusReason",Reason)+" | EvaluationEndDateUTC="+Read(read,"EvaluationEndDate",EndDate);
    }
}
