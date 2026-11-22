import subprocess
import json
import datetime


def sweep_buckets():
    print("Initiating Incremental GCS bucket sweep...")
    state_file = "state.json"

    # Read state
    try:
        with open(state_file, "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {"continuous_heuristic_integration": []}

    last_sync = state.get("last_sync_timestamp", "Never")
    print(f"Last successful sync: {last_sync}")

    try:
        result = subprocess.run(
            "gcloud storage ls",
            capture_output=True,
            text=True,
            check=True,
            shell=True)
        buckets = [b for b in result.stdout.strip().split('\n') if b]
        status = "Success"
        error = None
        print("Command executed successfully.")
    except subprocess.CalledProcessError as e:
        status = "Failed"
        error = e.stderr.strip()
        print("Command failed.")

    current_time = str(datetime.datetime.now())
    entry = {
        "timestamp": current_time,
        "action": "gcs_incremental_sweep",
        "status": status,
    }
    if error:
        entry["error"] = error
    else:
        # Update last sync timestamp only on success
        state["last_sync_timestamp"] = current_time

    state["continuous_heuristic_integration"].append(entry)

    with open(state_file, "w") as f:
        json.dump(state, f, indent=4)

    print(f"\nState saved to {state_file}.")

    if error and "403" in error:
        print(
            f"\n[!] VERIFICATION FAILED: Hit a 403 exception.\nDetails: {error}")
    elif status == "Success":
        print(
            "\n[+] VERIFICATION SUCCESS: Incremental sweep successful! No 403 Billing exceptions.")
    else:
        print(f"\n[!] Sweep failed with a non-403 error:\n{error}")


if __name__ == "__main__":
    sweep_buckets()
