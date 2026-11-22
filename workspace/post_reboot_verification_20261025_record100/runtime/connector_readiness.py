"""Read only admitted user connector loopback readiness and aggregate HA counts."""
from datetime import datetime, timezone
import json, re
from pathlib import Path
import urllib.request
import psutil

OUT=Path(__file__).resolve().parent
receipt=json.loads((OUT/'runtime_receipt.json').read_text())
rows=[]
for connector in receipt['connectors']:
    if connector['kind'] not in {'publishing_user_config','scoped_api_config'}:continue
    row={'kind':connector['kind'],'pid':connector['pid'],'created_epoch':connector['created_epoch']}
    try:
        process=psutil.Process(connector['pid'])
        assert process.create_time()==connector['created_epoch']
        assert process.exe()==connector['exe']
        metrics=connector['metric_listeners']
        assert len(metrics)==1 and metrics[0]['ip']=='127.0.0.1'
        port=metrics[0]['port']
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/ready',timeout=5) as response:
            row['ready_http']=response.status
            response.read(2048)
        with opener.open(f'http://127.0.0.1:{port}/metrics',timeout=5) as response:
            row['metrics_http']=response.status
            body=response.read(1048577)
            assert len(body)<=1048576
            values=re.findall(rb'^cloudflared_tunnel_ha_connections(?:\{[^\n]*\})?\s+([0-9.eE+-]+)\s*$',body,re.M)
            row['ha_connections']=sum(float(value) for value in values) if values else None
        row['healthy']=row['ready_http']==200 and row['ha_connections']==4
    except Exception as error:row['error_type']=type(error).__name__;row['healthy']=False
    rows.append(row)
result={'actor':'/root/postboot_runtime','observed_utc':datetime.now(timezone.utc).isoformat(),'scope':'owned loopback /ready and aggregate HA gauge only; no raw metrics retained','connectors':rows,'all_healthy':all(row['healthy'] for row in rows) and len(rows)==2}
(OUT/'connector_readiness.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
