$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$source = Get-Content "$root/app/src/main/java/com/stehouwerpublishing/bschat/MainActivity.java" -Raw
$manifest = Get-Content "$root/app/src/main/AndroidManifest.xml" -Raw
$gradle = Get-Content "$root/app/build.gradle" -Raw
$checks = [ordered]@{
    application_id = $gradle.Contains("applicationId 'com.stehouwerpublishing.bschat'")
    chat_endpoint = $source.Contains('https://ai-bs-dashboard.web.app/chat')
    no_backup = $manifest.Contains('android:allowBackup="false"')
    no_cleartext = $manifest.Contains('android:usesCleartextTraffic="false"')
    no_mixed_content = $source.Contains('WebSettings.MIXED_CONTENT_NEVER_ALLOW')
    no_file_content_access = $source.Contains('setAllowFileAccess(false)') -and $source.Contains('setAllowContentAccess(false)')
    no_native_bridge = -not $source.Contains('addJavascriptInterface')
    ssl_cancel = $source.Contains('handler.cancel()') -and -not $source.Contains('handler.proceed()')
    javascript_dom = $source.Contains('setJavaScriptEnabled(true)') -and $source.Contains('setDomStorageEnabled(true)')
    host_and_scheme_policy = $source.Contains('"https".equalsIgnoreCase(uri.getScheme())') -and $source.Contains('"ai-bs-dashboard.web.app".equalsIgnoreCase(uri.getHost())')
    error_retry = $source.Contains('request.isForMainFrame()') -and $source.Contains('Retry BS Chat')
    lifecycle_and_back = $source.Contains('web.destroy()') -and $source.Contains('registerOnBackInvokedCallback') -and $source.Contains('web.onPause()')
}
$receipt = [ordered]@{ scope = '12 source-policy smoke checks; not device/runtime qualification'; checks = $checks; passed = @($checks.Values | Where-Object { $_ }).Count; total = $checks.Count }
$receipt | ConvertTo-Json -Depth 4 | Set-Content "$PSScriptRoot/smoke.json"
$receipt | ConvertTo-Json -Depth 4
if ($receipt.passed -ne $receipt.total) { exit 1 }
