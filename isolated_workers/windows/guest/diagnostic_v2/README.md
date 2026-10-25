# AI-BS Guest Check v2

Separate candidate derived from the preserved v1 diagnostic. The operator opens the compiled application manually in the exact dedicated Windows guest. It requires no network, shell, installation, elevation, clipboard or security-setting change. It does not grant task authority.

The only diagnostic additions are the documented read-only SoftwareLicensingProduct properties LicenseStatusReason and EvaluationEndDate. Reason is displayed as UInt32 decimal and eight-digit hexadecimal; a complete valid DMTF date is normalized to UTC. Null fields show UNAVAILABLE; malformed or unexpected values show INVALID; individual property-read failures show READ_ERROR without raw values or exception messages. No product keys or credentials are selected or displayed. The original PartialProductKey predicate remains only an existing row filter.

The original exact-guest/host refusal, three fixed Python candidates, Node path, native probe arguments, isolated Python mode, deadlines, output cap, cancellation and licensing fields are preserved. CHECKS FINISHED means collection ended; inspect each State and Exit. A missing psutil import leaves the later win32api import untested.

Reason/date observations are not an activation verdict. Null, sentinel dates, clock differences and licensing errors require interpretation using Microsoft documentation. This tool does not activate Windows, reset evaluation, change clocks, install packages or run project checks. Actual guest execution remains unverified until the operator manually opens the new version.

Schema: https://learn.microsoft.com/en-us/previous-versions/windows/desktop/sppwmi/softwarelicensingproduct
