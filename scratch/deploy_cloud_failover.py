import json
import os
import subprocess
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ENV_PATH = Path(r"C:\AI-BS\.env")
STATE_PATH = Path(r"C:\AI-BS\saved_data\structural_dip_state.json")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if "=" in s and not s.startswith("#"):
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def test_cloudflare_worker_deploy(env: dict[str, str]) -> dict:
    token = env.get("CLOUDFLARE_API_TOKEN", "")
    acc = env.get("CLOUDFLARE_ACCOUNT_ID", "")
    script_name = "aibs-24x7-cloud-failover"

    worker_js = """
export class AIBSFailoverState {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
  }
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === 'POST' && url.pathname === '/api/heartbeat') {
      const payload = await request.json();
      payload.cloud_received_utc = new Date().toISOString();
      await this.ctx.storage.put('latest_telemetry', payload);
      return new Response(JSON.stringify({ status: 'synced', cloud_received_utc: payload.cloud_received_utc }), {
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }
    const stored = (await this.ctx.storage.get('latest_telemetry')) || {
      status: 'CLOUD_STANDBY',
      instrument: 'CRO_USDT',
      strategy: 'STRUCTURAL_DIP_GRID',
      scenario_mode: 'HYBRID_SPLIT'
    };
    return new Response(JSON.stringify(stored), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
      });
    }
    const url = new URL(request.url);
    if (url.pathname === '/api/health') {
      return new Response(JSON.stringify({ status: 'online', mode: 'cloudflare_24x7_edge_failover', utc: new Date().toISOString() }), {
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }
    if (env.FAILOVER_STATE) {
      const id = env.FAILOVER_STATE.idFromName('global-cro-usdt');
      const stub = env.FAILOVER_STATE.get(id);
      return stub.fetch(request);
    }
    return new Response(JSON.stringify({ status: 'online', service: 'aibs-24x7-cloud-failover' }), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }
};
"""
    boundary = "----AIBSBoundary" + uuid.uuid4().hex
    meta = {
        "main_module": "index.mjs",
        "compatibility_date": "2026-07-31",
        "bindings": [
            {
                "type": "durable_object_namespace",
                "name": "FAILOVER_STATE",
                "class_name": "AIBSFailoverState",
            }
        ],
        "migrations": {
            "tag": "v1",
            "new_sqlite_classes": ["AIBSFailoverState"],
        },
    }
    parts = [
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="metadata"; filename="metadata.json"\r\n'
        "Content-Type: application/json\r\n\r\n"
        f"{json.dumps(meta)}\r\n",
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="index.mjs"; filename="index.mjs"\r\n'
        "Content-Type: application/javascript+module\r\n\r\n"
        f"{worker_js}\r\n"
        f"--{boundary}--\r\n",
    ]
    body = "".join(parts).encode("utf-8")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/workers/scripts/{script_name}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="PUT",
    )
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
        # Also enable workers.dev subdomain route for this script
        sub_url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/workers/scripts/{script_name}/subdomain"
        sub_req = urllib.request.Request(
            sub_url,
            data=json.dumps({"enabled": True}).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            sub_res = json.loads(urllib.request.urlopen(sub_req, timeout=10).read().decode("utf-8"))
        except Exception as se:
            sub_res = {"err": str(se)}
        return {"ok": True, "script": script_name, "result": res.get("result", {}).get("id"), "subdomain": sub_res}
    except urllib.error.HTTPError as e:
        return {"ok": False, "code": e.code, "body": e.read().decode("utf-8", errors="ignore")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    env = load_env()
    out = test_cloudflare_worker_deploy(env)
    print(json.dumps(out, indent=2))
