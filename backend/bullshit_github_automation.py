import subprocess
import os


def commit_and_push_build(
    repo_path: str,
    commit_message: str = "AI-BS Auto Updater: Successful Build Integration",
    branch: str = "main",
) -> dict:
    """
    Automates GitHub version control by adding, committing, and pushing code.

    Args:
        repo_path: The absolute path to the local git repository.
        commit_message: The message for the commit.
        branch: The branch to push to.
    """
    print(f"[GitHub Automation] Securing build at {repo_path}")

    if not os.path.exists(os.path.join(repo_path, ".git")):
        return {"status": "error", "error": "Not a valid git repository."}

    try:
        # Add all files
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, check=True, capture_output=True
        )

        # Commit
        commit_res = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if "nothing to commit" in commit_res.stdout:
            return {"status": "success", "data": "No new changes to commit."}

        # Push
        push_res = subprocess.run(
            ["git", "push", "origin", branch],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        return {
            "status": "success",
            "data": f"Successfully committed and pushed to {branch}.",
        }

    except subprocess.CalledProcessError as e:
        return {"status": "error", "error": f"Git command failed: {e.stderr}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Test execution
    print("GitHub Automation Module Initialized.")
