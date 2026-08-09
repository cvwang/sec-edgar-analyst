"""Re-indexing Utility Script for SEC EDGAR Filing Corpus (RAG-06).

Applies clean Markdown/HTML structural formatting to SEC 10-K filing chunks stored in data/10k_filings/
and GCS (gs://sec-analyst-sec-reports/filings/), then triggers Discovery Engine metadata re-import.
"""

import os
import glob
import logging
from google.cloud import storage
from agent.config import settings
from agent.rag.sec_corpus import clean_sec_document_text

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "10k_filings")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "sec-analyst-sec-reports")


def reindex_gcs_filings() -> int:
    """Reads filing Markdown blobs directly from GCS, cleans formatting into structured Markdown/HTML, and re-uploads."""
    print(f"Connecting to GCS bucket '{GCS_BUCKET_NAME}' on project '{settings.gcp_project_id}'...")
    try:
        storage_client = storage.Client(project=settings.gcp_project_id)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blobs = list(bucket.list_blobs(prefix="filings/"))
        md_blobs = [b for b in blobs if b.name.endswith(".md") and not b.name.endswith("metadata.jsonl")]

        print(f"Found {len(md_blobs)} filing blobs in gs://{GCS_BUCKET_NAME}/filings/ to re-index...")
        reindexed_count = 0

        for blob in md_blobs:
            try:
                raw_text = blob.download_as_text()
                cleaned_text = clean_sec_document_text(raw_text)
                blob.upload_from_string(cleaned_text, content_type="text/markdown")
                reindexed_count += 1
            except Exception as e:
                print(f"Error re-indexing blob {blob.name}: {e}")

        print(f"✅ Successfully re-indexed {reindexed_count} GCS filing blobs with clean Markdown/HTML structural formatting.")
        return reindexed_count
    except Exception as err:
        print(f"GCS re-indexing error: {err}")
        return 0


def upload_and_import_manifest():
    """Triggers generate_and_import_manifest logic to sync GCS bucket and Discovery Engine Datastore."""
    try:
        from scripts.generate_and_import_manifest import main as import_manifest
        import_manifest()
    except Exception as err:
        print(f"Manifest import trigger note: {err}")


def main():
    print("==========================================================================")
    print("🚀 RE-INDEXING SEC CORPUS FILING CHUNKS WITH CLEAN MARKDOWN/HTML FORMAT 🚀")
    print("==========================================================================")
    count = reindex_gcs_filings()
    upload_and_import_manifest()
    print(f"Re-indexing complete for {count} chunks.")


if __name__ == "__main__":
    main()
