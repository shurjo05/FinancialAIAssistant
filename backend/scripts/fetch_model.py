"""Fetch the pinned trained model from its GitHub Release, instead of retraining.

Reads `app/ml/model_metadata.json` for the release tag, artifact name, and
expected SHA-256, downloads the asset into `app/ml/artifacts/`, and verifies its
checksum. Idempotent: if the artifact already exists and matches, it does
nothing. Used by the Dockerfile at build time and by developers who don't want
to retrain locally.

Uses only the standard library so it runs before app dependencies are present.

    python -m scripts.fetch_model            # from backend/
    MODEL_REPO=owner/repo python -m scripts.fetch_model

Exit codes: 0 = artifact present and verified; 1 = download or checksum failure.
"""

import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
METADATA_PATH = BACKEND_DIR / "app" / "ml" / "model_metadata.json"
ARTIFACTS_DIR = BACKEND_DIR / "app" / "ml" / "artifacts"
DEFAULT_REPO = "shurjo05/FinancialAIAssistant"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    tag = meta["release_tag"]
    artifact = meta["artifact"]
    expected_sha = meta["sha256"]
    repo = os.getenv("MODEL_REPO", DEFAULT_REPO)

    dest = ARTIFACTS_DIR / artifact
    if dest.exists() and _sha256(dest) == expected_sha:
        print(f"Model already present and verified: {dest} ({tag})")
        return 0

    url = f"https://github.com/{repo}/releases/download/{tag}/{artifact}"
    print(f"Fetching {artifact} from {url}")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_name = tempfile.mkstemp(dir=ARTIFACTS_DIR, suffix=".part")
    os.close(tmp_fd)
    tmp = Path(tmp_name)
    try:
        try:
            with urllib.request.urlopen(url) as resp, tmp.open("wb") as out:
                while chunk := resp.read(1 << 20):
                    out.write(chunk)
        except urllib.error.HTTPError as e:
            print(f"ERROR: download failed ({e.code} {e.reason}). "
                  f"Is release '{tag}' published with asset '{artifact}'?", file=sys.stderr)
            return 1
        except urllib.error.URLError as e:
            print(f"ERROR: network failure: {e.reason}", file=sys.stderr)
            return 1

        actual_sha = _sha256(tmp)
        if actual_sha != expected_sha:
            print(f"ERROR: checksum mismatch.\n  expected {expected_sha}\n  got      {actual_sha}",
                  file=sys.stderr)
            return 1

        tmp.replace(dest)
        print(f"Downloaded and verified: {dest} ({tag}, {dest.stat().st_size} bytes)")
        return 0
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
