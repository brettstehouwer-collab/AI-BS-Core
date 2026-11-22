using System;
using System.Collections.Generic;
internal static class LicensingFieldsTests {
    static int passed;
    static void Check(string name,bool ok){if(!ok)throw new Exception(name);passed++;Console.WriteLine("PASS "+name);}
    static void Same(string name,string actual,string expected){Check(name,actual==expected);}
    sealed class UnsafeObject {public override string ToString(){throw new Exception("PRIVATE_VALUE_MUST_NOT_ESCAPE");}}
    static int Main(){
        Same("zero reason retained",LicensingFields.Reason((uint)0),"0 (0x00000000)");
        Same("HRESULT high bit retained",LicensingFields.Reason((uint)0xC004F074),"3221549172 (0xC004F074)");
        Same("UInt32 max retained",LicensingFields.Reason(UInt32.MaxValue),"4294967295 (0xFFFFFFFF)");
        Same("null reason unavailable",LicensingFields.Reason(null),"UNAVAILABLE");
        Same("DBNull reason unavailable",LicensingFields.Reason(DBNull.Value),"UNAVAILABLE");
        Same("negative reason invalid",LicensingFields.Reason(-1),"INVALID");
        Same("overflow reason invalid",LicensingFields.Reason((long)UInt32.MaxValue+1),"INVALID");
        Same("string reason cannot leak",LicensingFields.Reason("PRIVATE_VALUE\r\nINJECTED"),"INVALID");
        Same("object reason cannot call ToString",LicensingFields.Reason(new UnsafeObject()),"INVALID");
        Same("UTC date normalized",LicensingFields.EndDate("20261024121530.123456+000"),"2026-10-24T12:15:30.123456Z");
        Same("positive offset normalized",LicensingFields.EndDate("20261024121530.123456+120"),"2026-10-24T10:15:30.123456Z");
        Same("negative offset normalized",LicensingFields.EndDate("20261024121530.123456-300"),"2026-10-24T17:15:30.123456Z");
        Same("null date unavailable",LicensingFields.EndDate(null),"UNAVAILABLE");
        Same("DBNull date unavailable",LicensingFields.EndDate(DBNull.Value),"UNAVAILABLE");
        Same("wildcard date rejected",LicensingFields.EndDate("**************.******+***"),"INVALID");
        Same("bad calendar date rejected",LicensingFields.EndDate("20260230121530.123456+000"),"INVALID");
        Same("oversized date rejected",LicensingFields.EndDate(new string('x',4096)),"INVALID");
        Same("injected date cannot leak",LicensingFields.EndDate("PRIVATE_VALUE\nINJECTED"),"INVALID");
        Same("unsupported offset rejected",LicensingFields.EndDate("20261024121530.123456+999"),"INVALID");
        Same("object date cannot call ToString",LicensingFields.EndDate(new UnsafeObject()),"INVALID");
        var keys=new List<string>();
        var line=LicensingFields.ExtraFields(delegate(string key){keys.Add(key);return key=="LicenseStatusReason"?(object)(uint)0:"20261024121530.123456+000";});
        Same("fixed safe field labels",line," | LicenseStatusReason=0 (0x00000000) | EvaluationEndDateUTC=2026-10-24T12:15:30.123456Z");
        Check("only requested properties read",keys.Count==2&&keys[0]=="LicenseStatusReason"&&keys[1]=="EvaluationEndDate");
        line=LicensingFields.ExtraFields(delegate(string key){if(key=="LicenseStatusReason")throw new Exception("PRIVATE_REASON");return "20261024121530.123456+000";});
        Same("reason error preserves date",line," | LicenseStatusReason=READ_ERROR | EvaluationEndDateUTC=2026-10-24T12:15:30.123456Z");
        line=LicensingFields.ExtraFields(delegate(string key){if(key=="EvaluationEndDate")throw new Exception("PRIVATE_DATE");return (uint)0;});
        Same("date error preserves reason",line," | LicenseStatusReason=0 (0x00000000) | EvaluationEndDateUTC=READ_ERROR");
        line=LicensingFields.ExtraFields(delegate(string key){throw new Exception("PRIVATE_VALUE");});
        Check("field errors leak no payload",!line.Contains("PRIVATE")&&line.Contains("READ_ERROR"));
        var select=LicensingFields.Query.Split(new string[]{" FROM "},StringSplitOptions.None)[0];
        Check("query selects only five sanitized fields",select=="SELECT Name,LicenseStatus,GracePeriodRemaining,LicenseStatusReason,EvaluationEndDate");
        Check("original Windows filter retained",LicensingFields.Query.EndsWith("FROM SoftwareLicensingProduct WHERE Name LIKE 'Windows%' AND PartialProductKey IS NOT NULL",StringComparison.Ordinal));
        Console.WriteLine("RESULT "+passed+" licensing-field tests passed; no guest/host licensing probes executed.");return 0;
    }
}
