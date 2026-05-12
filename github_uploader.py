"""
github_uploader.py — Auto-push diagrams to GitHub
====================================================
Uploads generated diagram files to a GitHub repository.
Triggered automatically by generate_diagram.py or scheduler.py.

Usage:
    from github_uploader import upload_diagrams
    upload_diagrams(["output_diagrams/diagram_20260314.drawio"])
"""

import os
import sys
from datetime import datetime

try:
    from github import Github, GithubException
except ImportError:
    print("Install PyGithub:  pip install PyGithub")
    sys.exit(1)

from config import (
    GITHUB_TOKEN,
    GITHUB_REPO,
    GITHUB_BRANCH,
    GITHUB_UPLOAD_DIR,
    timestamp,
)

# File types to upload as binary vs text
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".vsdx"}


def _read_file(path: str):
    """Read file as binary or text depending on extension."""
    ext = os.path.splitext(path)[1].lower()
    mode = "rb" if ext in BINARY_EXTENSIONS else "r"
    with open(path, mode) as f:
        return f.read()


def upload_diagrams(file_paths: list) -> list:
    """
    Upload a list of diagram files to GitHub.

    Args:
        file_paths: List of local file paths to upload.

    Returns:
        List of GitHub raw URLs for successfully uploaded files.
    """
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set — skipping GitHub upload.")
        print("Set it with:  export GITHUB_TOKEN=ghp_your_token")
        return []

    if not GITHUB_REPO:
        print("GITHUB_REPO not set — skipping GitHub upload.")
        return []

    try:
        gh   = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)
    except GithubException as e:
        print(f"GitHub connection failed: {e}")
        return []

    uploaded_urls = []
    ts = timestamp()

    for local_path in file_paths:
        if not os.path.exists(local_path):
            print(f"  SKIP: {local_path} not found")
            continue

        filename    = os.path.basename(local_path)
        github_path = f"{GITHUB_UPLOAD_DIR}/{filename}"
        commit_msg  = f"Auto-update: {filename} [{ts}]"

        try:
            content = _read_file(local_path)

            # Check if file already exists (update) or is new (create)
            try:
                existing = repo.get_contents(github_path, ref=GITHUB_BRANCH)
                repo.update_file(
                    path=github_path,
                    message=commit_msg,
                    content=content,
                    sha=existing.sha,
                    branch=GITHUB_BRANCH,
                )
                action = "Updated"
            except GithubException:
                repo.create_file(
                    path=github_path,
                    message=commit_msg,
                    content=content,
                    branch=GITHUB_BRANCH,
                )
                action = "Created"

            raw_url = (
                f"https://raw.githubusercontent.com/"
                f"{GITHUB_REPO}/{GITHUB_BRANCH}/{github_path}"
            )
            uploaded_urls.append(raw_url)
            print(f"  {action}: {filename} → {raw_url}")

        except GithubException as e:
            print(f"  FAIL: {filename} — {e}")
        except Exception as e:
            print(f"  FAIL: {filename} — {e}")

    return uploaded_urls


# ── CLI usage ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import glob

    print("GitHub Uploader")
    print("-" * 40)

    # Upload all files in output_diagrams/
    files = glob.glob("output_diagrams/*")
    if not files:
        print("No files in output_diagrams/ to upload.")
        sys.exit(0)

    print(f"Uploading {len(files)} files to {GITHUB_REPO}...")
    urls = upload_diagrams(files)
    print(f"\nDone. {len(urls)}/{len(files)} files uploaded.")
