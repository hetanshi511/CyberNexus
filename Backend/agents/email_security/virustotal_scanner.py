"""
Email Security Agent — VirusTotal Scanner
Scans URLs and attachment files using the VirusTotal API.
"""
import os
import time
import hashlib
import logging
import requests

logger = logging.getLogger("email_security")

VT_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
VT_BASE = "https://www.virustotal.com/api/v3"
VT_HEADERS = {"x-apikey": VT_API_KEY}

# 10 MB max file size for attachment scanning
MAX_FILE_SIZE = 10 * 1024 * 1024


def scan_url(url: str) -> dict:
    """
    Submits a URL to VirusTotal and returns the scan summary.
    Returns: { url, malicious, suspicious, status }
    """
    if not VT_API_KEY:
        return {"url": url, "malicious": 0, "suspicious": 0, "status": "skipped_no_api_key"}

    try:
        # Submit
        resp = requests.post(
            f"{VT_BASE}/urls",
            headers=VT_HEADERS,
            data={"url": url},
            timeout=15
        )
        resp.raise_for_status()
        analysis_id = resp.json()["data"]["id"]

        # Poll for results (up to 30s)
        for _ in range(6):
            time.sleep(5)
            result = requests.get(
                f"{VT_BASE}/analyses/{analysis_id}",
                headers=VT_HEADERS,
                timeout=15
            ).json()

            status = result.get("data", {}).get("attributes", {}).get("status", "")
            if status == "completed":
                stats = result["data"]["attributes"]["stats"]
                return {
                    "url": url,
                    "malicious": stats.get("malicious", 0),
                    "suspicious": stats.get("suspicious", 0),
                    "status": "completed"
                }

        return {"url": url, "malicious": 0, "suspicious": 0, "status": "timeout"}

    except Exception as e:
        logger.error(f"[VTScanner] URL scan failed for {url}: {e}")
        return {"url": url, "malicious": 0, "suspicious": 0, "status": "error", "error": str(e)}


def scan_attachment(filename: str, data_bytes: bytes, size: int) -> dict:
    """
    Scans an attachment via VirusTotal. Checks hash first, uploads only on miss.
    Returns: { filename, malicious, suspicious, status }
    """
    base = {"filename": filename, "malicious": 0, "suspicious": 0}

    if not VT_API_KEY:
        return {**base, "status": "skipped_no_api_key"}

    if size > MAX_FILE_SIZE:
        logger.info(f"[VTScanner] Skipping {filename} — size {size / 1024 / 1024:.1f} MB exceeds 10 MB limit")
        return {**base, "status": "skipped_too_large"}

    try:
        # Try hash lookup first (free tier friendly — no upload needed)
        sha256 = hashlib.sha256(data_bytes).hexdigest()
        resp = requests.get(
            f"{VT_BASE}/files/{sha256}",
            headers=VT_HEADERS,
            timeout=10
        )

        if resp.status_code == 200:
            stats = resp.json()["data"]["attributes"]["last_analysis_stats"]
            return {
                **base,
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "status": "hash_lookup"
            }

        # Unknown file — upload it
        upload_resp = requests.post(
            f"{VT_BASE}/files",
            headers=VT_HEADERS,
            files={"file": (filename, data_bytes)},
            timeout=30
        )
        upload_resp.raise_for_status()
        analysis_id = upload_resp.json()["data"]["id"]

        # Poll for results
        for _ in range(6):
            time.sleep(5)
            result = requests.get(
                f"{VT_BASE}/analyses/{analysis_id}",
                headers=VT_HEADERS,
                timeout=15
            ).json()
            status = result.get("data", {}).get("attributes", {}).get("status", "")
            if status == "completed":
                stats = result["data"]["attributes"]["stats"]
                return {
                    **base,
                    "malicious": stats.get("malicious", 0),
                    "suspicious": stats.get("suspicious", 0),
                    "status": "uploaded_and_scanned"
                }

        return {**base, "status": "timeout"}

    except Exception as e:
        logger.error(f"[VTScanner] Attachment scan failed for {filename}: {e}")
        return {**base, "status": "error", "error": str(e)}
