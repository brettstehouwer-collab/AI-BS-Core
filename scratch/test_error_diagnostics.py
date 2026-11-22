from backend.routers.operations_audit_router import get_error_diagnostics
res = get_error_diagnostics('stehouwer_publishing')
print("Total log files found:", res['total_log_files'])
print("Total recent errors extracted:", res['total_recent_errors_extracted'])
print("\nDaemons in UI Diagnostics:")
for d in res['daemons'][:15]:
    print(f"- {d['logfile']:32} | Status: {d['status']:20} | Errs: {d['error_count_in_tail']} | Size: {d['size_kb']} KB")
