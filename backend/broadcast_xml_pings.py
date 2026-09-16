import requests
import xmlrpc.client
import sys

sys.stdout.reconfigure(encoding='utf-8')

site_name = "Stehouwer Publishing L.L.C."
site_url = "https://stehouwer-publishing.com"
check_url = "https://stehouwer-publishing.com/library"

rpc_services = [
    "http://rpc.pingomatic.com",
    "http://ping.blo.gs/",
    "http://rpc.weblogs.com/RPC2"
]

print(f"Broadcasting XML-RPC Web Ping for: {site_url}")

for svc in rpc_services:
    try:
        server = xmlrpc.client.ServerProxy(svc, allow_none=True)
        response = server.weblogUpdates.ping(site_name, site_url, check_url)
        print(f"Service: {svc} -> Response: {response}")
    except Exception as e:
        print(f"Service: {svc} -> Status: {e}")

print("Broadcasting finished.")
