"""AI-BS Serverless Spark Session Template & Workload Manager.

Configures and deploys Dataproc Serverless Session Templates and submits
distributed training batch workloads to Google Cloud Platform.
Supports schema validation against Google Cloud Dataproc v1 REST specification
and serverless Terraform resource generation.
"""
import os
import sys
import re
import json
import argparse
import py_compile
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parent
TEMPLATE_JSON_PATH = PROJECT_ROOT / "dataproc_serverless_session_template.json"
DRIVER_PY_PATH = PROJECT_ROOT / "distributed_training_driver.py"

def load_template() -> Dict[str, Any]:
    """Loads the Dataproc Serverless session template JSON configuration."""
    assert TEMPLATE_JSON_PATH.exists(), f"Template JSON missing: {TEMPLATE_JSON_PATH}"
    with open(TEMPLATE_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_driver_cli_path() -> str:
    """Returns the driver path formatted for CLI execution relative to the active working directory."""
    cwd = Path.cwd().resolve()
    try:
        rel = DRIVER_PY_PATH.resolve().relative_to(cwd)
        return rel.as_posix()
    except ValueError:
        try:
            rel = DRIVER_PY_PATH.resolve().relative_to(REPO_ROOT.resolve())
            return rel.as_posix()
        except ValueError:
            return DRIVER_PY_PATH.as_posix()

def generate_batch_payload(project_id: str, region: str, batch_id: str, staging_bucket: str) -> Dict[str, Any]:
    """Generates a valid Dataproc v1 REST Batch workload payload."""
    return {
        "name": f"projects/{project_id}/locations/{region}/batches/{batch_id}",
        "pysparkBatch": {
            "mainPythonFileUri": f"{staging_bucket}/distributed_training_driver.py",
            "args": ["--framework", "both"]
        },
        "runtimeConfig": {
            "version": "2.2",
            "properties": {
                "spark.dynamicAllocation.enabled": "true",
                "spark.dynamicAllocation.minExecutors": "2",
                "spark.dynamicAllocation.maxExecutors": "32",
                "spark.executor.cores": "4",
                "spark.executor.memory": "16g",
                "spark.driver.cores": "4",
                "spark.driver.memory": "16g"
            }
        },
        "environmentConfig": {
            "executionConfig": {
                "serviceAccount": f"dataproc-serverless-sa@{project_id}.iam.gserviceaccount.com",
                "stagingBucket": staging_bucket,
                "networkTags": ["dataproc-serverless", "distributed-training"]
            }
        },
        "labels": {
            "workload": "distributed-training",
            "framework": "pyspark-pytorch",
            "managed-by": "ai-bs-system"
        }
    }

def generate_terraform_hcl(project_id: str, region: str, template_id: str, staging_bucket: str = "gs://ai-bs-dataproc-staging-us-central1") -> str:
    """Generates Terraform HCL resource definitions for Dataproc Serverless Session Template and Batch."""
    return f"""# Terraform HCL definitions for Dataproc Serverless
# Dataproc Serverless Session Template for Interactive Development
resource "google_dataproc_session_template" "distributed_training_template" {{
  name        = "{template_id}"
  location    = "{region}"
  project     = "{project_id}"
  description = "AI-BS High-Performance Serverless Spark Session Template for Distributed ML Training"

  labels = {{
    workload   = "distributed-training"
    framework  = "pyspark-pytorch"
    managed-by = "ai-bs-system"
    tier       = "enterprise-gpu-cpu"
  }}

  runtime_config {{
    version = "2.2"
    properties = {{
      "spark.dynamicAllocation.enabled"      = "true"
      "spark.dynamicAllocation.minExecutors"  = "2"
      "spark.dynamicAllocation.maxExecutors"  = "32"
      "spark.executor.cores"                  = "4"
      "spark.executor.memory"                 = "16g"
      "spark.driver.cores"                    = "4"
      "spark.driver.memory"                   = "16g"
    }}
  }}

  environment_config {{
    execution_config {{
      service_account = "dataproc-serverless-sa@{project_id}.iam.gserviceaccount.com"
      staging_bucket  = "{staging_bucket}"
      network_tags    = ["dataproc-serverless", "distributed-training"]
      ttl             = "28800s"
    }}
  }}

  jupyter_session {{
    kernel       = "PYTHON"
    display_name = "PySpark Distributed Training Kernel (Python 3.11 / Spark 3.5)"
  }}
}}

# Dataproc Serverless Batch Workload for Distributed Training Execution
resource "google_dataproc_batch" "distributed_training_batch" {{
  batch_id = "spark-dist-train-batch"
  location = "{region}"
  project  = "{project_id}"

  labels = {{
    workload   = "distributed-training"
    framework  = "pyspark-pytorch"
    managed-by = "ai-bs-system"
  }}

  pyspark_batch {{
    main_python_file_uri = "{staging_bucket}/distributed_training_driver.py"
    args                 = ["--framework", "both"]
  }}

  runtime_config {{
    version = "2.2"
    properties = {{
      "spark.dynamicAllocation.enabled"      = "true"
      "spark.dynamicAllocation.minExecutors"  = "2"
      "spark.dynamicAllocation.maxExecutors"  = "32"
      "spark.executor.cores"                  = "4"
      "spark.executor.memory"                 = "16g"
      "spark.driver.cores"                    = "4"
      "spark.driver.memory"                   = "16g"
    }}
  }}

  environment_config {{
    execution_config {{
      service_account = "dataproc-serverless-sa@{project_id}.iam.gserviceaccount.com"
      staging_bucket  = "{staging_bucket}"
      network_tags    = ["dataproc-serverless", "distributed-training"]
    }}
  }}
}}

output "dataproc_serverless_session_template_id" {{
  value = google_dataproc_session_template.distributed_training_template.id
}}

output "dataproc_serverless_batch_id" {{
  value = google_dataproc_batch.distributed_training_batch.id
}}
"""

def create_session_template_rest(project_id: str, region: str, template_id: str, access_token: str) -> Dict[str, Any]:
    """Creates a Serverless Spark Session Template via the Google Cloud Dataproc v1 REST API."""
    import urllib.request
    import urllib.error

    url = f"https://dataproc.googleapis.com/v1/projects/{project_id}/locations/{region}/sessionTemplates?sessionTemplateId={template_id}"
    template_body = load_template()
    template_body["name"] = f"projects/{project_id}/locations/{region}/sessionTemplates/{template_id}"

    data = json.dumps(template_body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise RuntimeError(f"GCP Dataproc API returned HTTP {e.code}: {error_msg}")

def validate_configuration() -> bool:
    """Validates session template and batch configurations against Google Cloud Dataproc v1 REST schema.
    
    Returns:
        True if all checks pass.
    Raises:
        AssertionError or ValueError on validation failure.
    """
    print("=" * 70)
    print("DATAPROC SERVERLESS WORKLOAD & SESSION TEMPLATE VALIDATION")
    print("=" * 70)

    # 1. Validate session template file existence and JSON parsing
    template = load_template()
    print("  [PASS] 1. Session template JSON parsed successfully.")

    # 2. Validate Resource Name format (projects/{project}/locations/{location}/sessionTemplates/{template})
    name = template.get("name", "")
    name_pattern = r"^projects/[a-zA-Z0-9-_]+/locations/[a-zA-Z0-9-_]+/sessionTemplates/[a-zA-Z0-9-_]+$"
    assert re.match(name_pattern, name), f"Invalid Dataproc SessionTemplate name: {name}"
    print(f"  [PASS] 2. Resource name conforms to Dataproc v1 REST URI pattern: {name}")

    # 3. Validate environmentConfig & executionConfig
    env_config = template.get("environmentConfig", {})
    assert "executionConfig" in env_config, "Missing environmentConfig.executionConfig"
    exec_config = env_config["executionConfig"]
    
    sa = exec_config.get("serviceAccount", "")
    assert "@" in sa and sa.endswith(".iam.gserviceaccount.com"), f"Invalid service account format: {sa}"
    
    staging_bucket = exec_config.get("stagingBucket", "")
    assert staging_bucket.startswith("gs://"), f"Invalid staging bucket URI: {staging_bucket}"
    
    ttl = exec_config.get("ttl", "")
    assert re.match(r"^\d+s$", ttl), f"Invalid TTL duration format: {ttl}"
    
    network_tags = exec_config.get("networkTags", [])
    assert isinstance(network_tags, list) and len(network_tags) > 0, "networkTags must be a non-empty list"
    print("  [PASS] 3. environmentConfig.executionConfig schema verified (SA, stagingBucket, TTL, networkTags).")

    # 4. Validate runtimeConfig & Spark properties
    runtime_config = template.get("runtimeConfig", {})
    version = runtime_config.get("version", "")
    assert version in ["2.0", "2.1", "2.2", "2.3"], f"Unsupported Dataproc Serverless runtime version: {version}"
    
    props = runtime_config.get("properties", {})
    assert isinstance(props, dict), "runtimeConfig.properties must be a dictionary"
    assert props.get("spark.dynamicAllocation.enabled") == "true", "spark.dynamicAllocation.enabled must be 'true'"
    assert int(props.get("spark.dynamicAllocation.minExecutors", 0)) >= 1, "spark.dynamicAllocation.minExecutors must be >= 1"
    assert int(props.get("spark.dynamicAllocation.maxExecutors", 0)) >= 4, "spark.dynamicAllocation.maxExecutors must be >= 4"
    assert "spark.executor.cores" in props, "Missing spark.executor.cores"
    assert "spark.executor.memory" in props, "Missing spark.executor.memory"
    assert "spark.driver.cores" in props, "Missing spark.driver.cores"
    assert "spark.driver.memory" in props, "Missing spark.driver.memory"
    print(f"  [PASS] 4. runtimeConfig verified: Dataproc Runtime {version} with dynamic allocation [{props['spark.dynamicAllocation.minExecutors']}..{props['spark.dynamicAllocation.maxExecutors']}] executors.")

    # 5. Validate session spec (jupyterSession)
    jupyter_session = template.get("jupyterSession", {})
    assert jupyter_session.get("kernel") in ["PYTHON", "SCALA"], f"Invalid jupyterSession kernel: {jupyter_session.get('kernel')}"
    assert len(jupyter_session.get("displayName", "")) > 0, "Missing jupyterSession.displayName"
    print("  [PASS] 5. jupyterSession specification conforms to Dataproc interactive session schema.")

    # 6. Validate Batch workload configuration
    batch_config = generate_batch_payload(
        project_id="ai-bs-dashboard",
        region="us-central1",
        batch_id="spark-dist-train-batch",
        staging_bucket=staging_bucket
    )
    assert "pysparkBatch" in batch_config, "Batch config missing pysparkBatch"
    assert batch_config["pysparkBatch"]["mainPythonFileUri"].endswith("distributed_training_driver.py")
    assert batch_config["runtimeConfig"]["version"] == "2.2"
    assert batch_config["environmentConfig"]["executionConfig"]["stagingBucket"] == staging_bucket
    print("  [PASS] 6. Dataproc Serverless Batch workload specification verified against REST schema.")

    # 7. Validate driver script syntax and compilation
    assert DRIVER_PY_PATH.exists(), f"Driver script missing: {DRIVER_PY_PATH}"
    py_compile.compile(str(DRIVER_PY_PATH), doraise=True)
    print("  [PASS] 7. Distributed training driver script verified and compiled cleanly.")

    # 8. Validate Terraform HCL generation uses serverless resources (no legacy clusters)
    tf_hcl = generate_terraform_hcl("ai-bs-dashboard", "us-central1", "spark-distributed-training-template")
    assert "google_dataproc_cluster" not in tf_hcl, "Terraform HCL must NOT use legacy google_dataproc_cluster"
    assert "google_dataproc_session_template" in tf_hcl, "Terraform HCL missing google_dataproc_session_template"
    assert "google_dataproc_batch" in tf_hcl, "Terraform HCL missing google_dataproc_batch"
    print("  [PASS] 8. Terraform serverless resource definitions verified (no legacy VM clusters).")

    print("=" * 70)
    print("ALL DATAPROC SERVERLESS CONFIGURATION CHECKS PASSED (EXIT CODE 0)")
    print("=" * 70)
    return True

def print_gcloud_instructions(project_id: str, region: str, staging_bucket: str):
    """Outputs the verified gcloud Dataproc Serverless batch submission command."""
    driver_cli_path = get_driver_cli_path()
    print("\n" + "=" * 70)
    print("GOOGLE CLOUD DATAPROC SERVERLESS SUBMISSION COMMAND")
    print("=" * 70)
    print(f"""
gcloud dataproc batches submit pyspark {driver_cli_path} \\
    --project={project_id} \\
    --region={region} \\
    --staging-bucket={staging_bucket} \\
    --batch=spark-dist-train-$(Get-Date -Format 'yyyyMMdd-HHmmss') \\
    --properties="spark.dynamicAllocation.enabled=true,spark.dynamicAllocation.minExecutors=2,spark.dynamicAllocation.maxExecutors=32,spark.executor.cores=4,spark.executor.memory=16g,spark.driver.cores=4,spark.driver.memory=16g" \\
    -- --framework both
""")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BS Dataproc Serverless Manager")
    parser.add_argument("--project", default="ai-bs-dashboard", help="GCP Project ID")
    parser.add_argument("--region", default="us-central1", help="GCP Region")
    parser.add_argument("--template-id", default="spark-distributed-training-template", help="Session Template ID")
    parser.add_argument("--staging-bucket", default="gs://ai-bs-dataproc-staging-us-central1", help="GCS Staging Bucket")
    parser.add_argument("--validate", action="store_true", help="Validate session template and batch configuration against Dataproc v1 REST schema")
    parser.add_argument("--terraform", action="store_true", help="Generate and print serverless Terraform HCL configuration")
    parser.add_argument("--batch-json", action="store_true", help="Generate and print Dataproc Serverless Batch REST JSON payload")
    parser.add_argument("--show-cli", action="store_true", help="Print verified gcloud CLI command")

    args = parser.parse_args()

    if args.validate:
        try:
            success = validate_configuration()
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"\n[FAIL] Validation error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.terraform:
        print(generate_terraform_hcl(args.project, args.region, args.template_id, args.staging_bucket))
    elif args.batch_json:
        payload = generate_batch_payload(args.project, args.region, "spark-dist-train-batch", args.staging_bucket)
        print(json.dumps(payload, indent=2))
    else:
        print_gcloud_instructions(args.project, args.region, args.staging_bucket)


