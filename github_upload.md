# Prompt: Push Diagrams to GitHub Repository
> Attach `.github/INSTRUCTIONS.md` to Copilot Chat before using this prompt.

---

## Use this prompt when:
You want to auto-upload generated diagram files to a GitHub repository
so the client can access them via browser or SharePoint integration.

---

## Setup

```bash
# Set credentials as environment variables (never hardcode)
export GITHUB_TOKEN=ghp_your_personal_access_token
export GITHUB_REPO=your-org/network-diagrams

# Install library
pip install PyGithub
```

Create a GitHub Personal Access Token:
GitHub → Settings → Developer settings → Personal access tokens → Fine-grained
Permissions needed: Contents (read + write)

---

## Prompt (copy → paste into Copilot Chat)

```
Using INSTRUCTIONS.md rules and config.py settings, write a Python
module called github_uploader.py with a function upload_diagrams(file_paths).

The function should:
1. Read GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH, GITHUB_UPLOAD_DIR from config.py
2. Connect using PyGithub: Github(token).get_repo(repo_name)
3. For each file path in file_paths:
   a. Read the file content (binary for PNG/PDF, text for drawio/svg)
   b. Build the GitHub path: GITHUB_UPLOAD_DIR/filename
   c. Check if the file already exists in the repo (for update vs create)
   d. If exists: repo.update_file(path, commit_msg, content, sha)
   e. If new:    repo.create_file(path, commit_msg, content, branch)
   f. Commit message: "Auto-update: {filename} [{timestamp}]"
   g. Log success URL for each uploaded file
4. Return list of GitHub raw URLs for uploaded files

Handle Github.GithubException gracefully — log and continue on failure.
If GITHUB_TOKEN is empty, print a warning and skip upload silently.
```

---

## Verify upload worked

After running, check:
```
https://github.com/YOUR-ORG/network-diagrams/tree/main/diagrams
```

---

## Variation — SharePoint integration

```
Write a Python function upload_to_sharepoint(file_paths) that
uploads diagram files to a SharePoint document library using
the Office365-REST-Python-Client library.

Read SHAREPOINT_URL, SHAREPOINT_USERNAME, SHAREPOINT_PASSWORD
from environment variables. Target folder: "Network Diagrams/Auto-Generated"

This is the SharePoint Integration component shown in the project architecture.
```
