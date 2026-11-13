"""Download the two public Zenodo PDF snapshots referenced by the manifest.

The PDFs stay local because the text license does not cover every image in them.
The manifest and this reproducible fetch recipe are the submission artifacts.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifest.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for document in manifest["documents"]:
        relative = Path(document["source_path_or_url"])
        if relative.is_absolute() or relative.parts[:2] != ("data", "corpus") or len(relative.parts) != 3:
            raise ValueError(f"Unexpected corpus path: {relative}")
        target = ROOT / relative
        if target.is_file():
            if _sha256(target.read_bytes()) != document["sha256"]:
                raise ValueError(f"Local PDF differs from manifest: {target}")
            print(f"Already verified: {relative}")
            continue

        record_url = document["source_url"]
        parsed = urllib.parse.urlparse(record_url)
        if parsed.scheme != "https" or parsed.netloc != "zenodo.org" or not parsed.path.startswith("/records/"):
            raise ValueError(f"Unexpected Zenodo record URL: {record_url}")
        record_id = parsed.path.rstrip("/").split("/")[-1]
        if not record_id.isdecimal():
            raise ValueError(f"Invalid Zenodo record ID: {record_url}")
        with urllib.request.urlopen(f"https://zenodo.org/api/records/{record_id}", timeout=45) as response:
            record = json.load(response)
        matches = [item for item in record.get("files", []) if item.get("key") == relative.name]
        if len(matches) != 1 or matches[0].get("checksum") != f"md5:{document['zenodo_md5']}":
            raise ValueError(f"Zenodo file/checksum differs from manifest: {record_id}")
        download_url = matches[0].get("links", {}).get("self", "")
        download_parts = urllib.parse.urlparse(download_url)
        if download_parts.scheme != "https" or download_parts.netloc != "zenodo.org":
            raise ValueError(f"Unexpected file download URL: {download_url}")
        with urllib.request.urlopen(download_url, timeout=120) as response:
            data = response.read()
        if hashlib.md5(data).hexdigest() != document["zenodo_md5"] or _sha256(data) != document["sha256"]:
            raise ValueError(f"Downloaded PDF differs from manifest: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"Downloaded and verified: {relative}")


if __name__ == "__main__":
    main()
