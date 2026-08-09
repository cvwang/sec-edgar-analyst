"""Re-indexing Utility Script for SEC EDGAR Filing Corpus (RAG-06).

Uploads clean Markdown filing disclosures from data/10k_filings/ to GCS (gs://sec-analyst-sec-reports/filings/)
and triggers Discovery Engine manifest re-import for Vertex AI Search.
"""

import os
import glob
import logging
from google.cloud import storage
from agent.config import settings

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "10k_filings")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "sec-analyst-sec-reports")


def upload_local_filings_to_gcs() -> int:
    """Uploads clean Markdown filing disclosures from data/10k_filings/ directly to GCS filings/ prefix."""
    if not os.path.exists(DATA_DIR):
        print(f"Data directory '{DATA_DIR}' does not exist locally.")
        return 0

    md_files = glob.glob(os.path.join(DATA_DIR, "*.md"))
    print(f"Connecting to GCS bucket '{GCS_BUCKET_NAME}' on project '{settings.gcp_project_id}'...")
    print(f"Found {len(md_files)} local Markdown filing files in {DATA_DIR} to upload to GCS...")

    storage_client = storage.Client(project=settings.gcp_project_id)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    uploaded_count = 0
    for file_path in md_files:
        filename = os.path.basename(file_path)
        gcs_path = f"filings/{filename}"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            blob = bucket.blob(gcs_path)
            blob.upload_from_string(content, content_type="text/markdown")
            uploaded_count += 1
        except Exception as e:
            print(f"Error uploading {filename} to GCS: {e}")

    print(f"✅ Successfully uploaded {uploaded_count} clean Markdown filing files to gs://{GCS_BUCKET_NAME}/filings/")
    return uploaded_count


def upload_and_import_manifest():
    """Triggers generate_and_import_manifest logic to sync GCS bucket and Discovery Engine Datastore."""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "scripts/generate_and_import_manifest.py"],
            capture_output=True,
            text=True,
            env=dict(os.environ, PYTHONPATH=".")
        )
        print(result.stdout)
        if result.stderr:
            print("Import manifest stderr:", result.stderr)
    except Exception as err:
        print(f"Manifest import trigger note: {err}")


def main():
    print("==========================================================================")
    print("🚀 UPLOADING CLEAN MARKDOWN FILINGS TO GCS & LAUNCHING VERTEX RE-IMPORT 🚀")
    print("==========================================================================")
    count = upload_local_filings_to_gcs()
    upload_and_import_manifest()
    print(f"Re-indexing complete for {count} chunks.")


if __name__ == "__main__":
    main()
