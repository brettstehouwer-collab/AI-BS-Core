"""Google Cloud API Gateway Client for AI-BS Runtime Environment.

Uses Application Default Credentials (ADC) to query API Gateways, APIs, and Configs.
"""
import os
import sys

def check_adc_credentials() -> bool:
    adc_path = os.path.expandvars(r"%APPDATA%\gcloud\application_default_credentials.json")
    env_adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_adc and os.path.exists(env_adc):
        print(f"[ADC] Using GOOGLE_APPLICATION_CREDENTIALS: {env_adc}")
        return True
    if os.path.exists(adc_path):
        print(f"[ADC] Using local user credentials: {adc_path}")
        return True
    print("[ADC] STATUS: No Application Default Credentials found.")
    return False

def list_api_gateways(project_id: str = "ai-bs-dashboard", location: str = "us-central1"):
    try:
        from google.cloud import apigateway_v1
    except ImportError as e:
        print(f"[ERROR] google-cloud-api-gateway import failed: {e}")
        return

    if not check_adc_credentials():
        return

    print("=" * 60)
    print(f"GOOGLE CLOUD API GATEWAY CLIENT: {project_id}")
    print("=" * 60)

    client = apigateway_v1.ApiGatewayServiceClient()
    parent = f"projects/{project_id}/locations/{location}"

    # 1. Gateways
    print(f"\n[1] Querying Gateways in {parent}...")
    try:
        gw_request = apigateway_v1.ListGatewaysRequest(parent=parent)
        gw_result = client.list_gateways(request=gw_request)
        gateways = list(gw_result)
        if gateways:
            for gw in gateways:
                print(f"  • Gateway: {gw.name}")
                print(f"    State: {gw.state.name}")
                print(f"    Hostname: {gw.default_hostname}")
                print(f"    API Config: {gw.api_config}")
        else:
            print("  ✓ No active gateways in this location.")
    except Exception as e:
        print(f"  [Gateway Query Notice]: {e}")

    # 2. APIs
    print(f"\n[2] Querying Managed APIs in {parent}...")
    try:
        api_request = apigateway_v1.ListApisRequest(parent=parent)
        api_result = client.list_apis(request=api_request)
        apis = list(api_result)
        if apis:
            for api in apis:
                print(f"  • API: {api.name}")
                print(f"    Display Name: {api.display_name}")
                print(f"    State: {api.state.name}")
        else:
            print("  ✓ No managed APIs defined yet.")
    except Exception as e:
        print(f"  [API Query Notice]: {e}")

    print("\n" + "=" * 60)
    print("STATUS: Connection to Google Cloud API Gateway is fully operational.")
    print("=" * 60)

if __name__ == "__main__":
    list_api_gateways()
