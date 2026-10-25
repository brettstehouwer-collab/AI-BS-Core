# Windows evaluation review for the isolated test worker

October 23, 2026 | Documentation review; application remains v5.329.19

## Decision so far

The user selected Review the evaluation option and then said confirm. This confirms proceeding with review of the evaluation route. It does not establish acceptance of unseen Microsoft terms, professional eligibility, registration completion or a permanent license. The separately asked VirtualBox driver-installation question has no explicit answer recorded. No purchases are authorized or needed for this review.

## What Microsoft currently states

[Evaluation Center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise) offers a 90-day Enterprise evaluation aimed at professional organizational evaluation. Registration and activation are required; no product key is needed. Its guidance says Microsoft-account sign-in is required. An expired/unactivated installation shuts down hourly. This is temporary evaluation access, not permanent entitlement.

The [registration landing page](https://info.microsoft.com/ww-landing-windows-11-enterprise.html) loaded but its actual form requires JavaScript. No registration fields, personal details or final license text were submitted or accepted. Final terms and applicability to this developer's intended use remain unverified. Do not describe the evaluation as an unrestricted production runtime or guaranteed eligibility.

## Recommended AI-BS decision

Use this route only if its actual terms permit the intended limited worker evaluation. It can support a temporary isolation prototype; it cannot by itself complete a permanently licensed, distributed Windows product. Resolve long-term guest rights before representing Phase6 Windows distribution or continuous operation as delivered. If terms do not fit, retain the Windows plan and review a legitimate alternative; never silently substitute Linux/WSL for the required Windows guest.

## Next human review

Open the official registration page, inspect the form and license conditions, and confirm whether your evaluation use qualifies. Enter your own account and registration information manually. Do not paste account passwords, activation secrets or license keys into chat. Save or provide the applicable public terms for technical review before acceptance is relied on. No host Windows replacement or Installation Assistant is part of this plan.

VirtualBox installation remains governed by WINDOWS_VM_INSTALL_REVIEW.md: pinned package and checksum, publisher verification before execution, reviewed driver installation, no automatic reboot or optional networking components. Evaluation-review confirmation alone does not settle that separate host-change question.

## Controller requirements if evaluation is chosen

Keep the activation/provisioning session separate from generated-code runs. Any required maintenance-network access must be bounded and reviewed, with no task code active. Never use an account-connected guest as the task base image until credentials/tokens, browser profiles and integration channels have been excluded and tested; the secure provisioning procedure is still unresolved. A temporary dedicated evaluation identity, if allowed by the actual terms, requires separate review rather than assuming personal-account use is safe.

Record a trusted activation/start timestamp and allowed expiry outside disposable snapshots. Reject an expired or unactivated base image as ISOLATION_UNAVAILABLE. No clock rollback, snapshot resetting or clone rotation to extend the evaluation. Preserve task evidence and originals through expiry; do not erase them. Confirm activation/licensing status and disabled networking before every task admission. None of these VM expiry/provisioning behaviors is implemented or tested yet.

## Verification and limits

Official overview and registration landing page were read. No ISO or installer downloaded; no registration, terms acceptance, account login, activation, VM creation, driver installation, host restart or purchase occurred. Earlier pure-validator tests and live unavailable-worker checks do not prove this evaluation is provisioned or usable offline. Final guest-media version/hash, platform compatibility, complete terms and all 14 VM acceptance cases remain pending.

## October 24 maintenance checkpoint: actual Notification/F009 evidence

Source v5.329.48, plan1.63. The existing VM has now reached a real desktop with Oracle Guest Additions7.2.22r175245 and MouseIntegrationOn. Host and guest runtime media were reviewed and preserved in earlier checkpoints. This supersedes only the earlier installation-status descriptions; it does not grant new licensing, maintenance-network, publication or purchase authority.

The actual guest diagnostic reports Microsoft Windows11EnterpriseEvaluation10.0.26300, LicenseStatus5(Notification), GraceMinutes0, LicenseStatusReason3221549065/0xC004F009 and EvaluationEndDateUTC1601-01-01T00:00:00.0000000Z. The expired Windows watermark remains visible. Nodev24.22.1/Python3.13.17 now have real successful version probes; Pythonpsutil is still missing. No task admission follows from runtime setup.

Microsoft's [F009 activation-error reference](https://learn.microsoft.com/en-us/troubleshoot/windows-server/licensing-and-activation/troubleshoot-activation-error-codes#0xc004f009-the-software-protection-service-reported-that-the-grace-period-expired) identifies an expired activation grace period and directs applicable users to Licensing Activation Centers. That table lists MAK context; it does not establish MAK entitlement or an applicable activation command for this exact evaluation SKU. The [WMI property schema](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/sppwmi/softwarelicensingproduct) defines the reported fields. The1601timestamp coincides with the [FILETIME epoch](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-filetime), but no reviewed Microsoft source defines that exact value's sentinel meaning for EvaluationEndDate. Record the raw value; actual evaluation expiry remains UNKNOWN. Neither exhaustion of the90dayevaluation nor ability to convert it with a retail key is established.

The next licensing decision must use a supported Microsoft or licensing-administrator route for this exact EnterpriseEval installation, or an appropriately licensed guest image/entitlement. Keys, account credentials and private registration data stay with the operator; never paste them into chat, task payloads, logs or cloud ledger. No evaluation rearm, clock rollback, snapshot/clone rotation, unapproved SKU conversion or bypass is part of the plan. Preserve the existing VM and evidence if another image becomes necessary.

Any maintenance internet session still requires separate explicit authorization and a concrete reviewed network/preservation/restoration procedure. No generated code may run connected; existing host services remain loopback-only, and no clipboard/sharedfolder/USB or host-data exposure is authorized. NAT by itself is not task isolation. Do not activate a general network connection under the earlier offline provisioning approval, or claim an account-connected maintenance image is a clean accepted task base. After supported activation, require actual LicenseStatus1 and an externally pinned trustworthy expiry bound if evaluation licensing applies, credential exclusion, disabled adapters and full controller/transport acceptance before task admission.

This checkpoint is read-only licensing review. No activation, registration/contact submission, network setting, clock, product key, account, reset, purchase or publication action was performed. The original evaluation-review decision/terms limitations remain preserved above.
