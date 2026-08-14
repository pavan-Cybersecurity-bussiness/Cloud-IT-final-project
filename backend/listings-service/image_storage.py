"""
image_storage.py — stores listing photos in Azure Blob Storage when
AZURE_STORAGE_CONNECTION_STRING is set. Otherwise falls back to the local
filesystem, so the service is fully runnable (docker-compose, unit testing,
Minikube without cloud credentials wired up yet) without any cloud account.

Switching from local disk to Azure Blob Storage is a one-line change: set
AZURE_STORAGE_CONNECTION_STRING in the environment. No code changes needed.
"""
import os
import uuid

AZURE_CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER = os.environ.get("AZURE_BLOB_CONTAINER", "listing-images")
LOCAL_UPLOAD_DIR = os.environ.get("LOCAL_UPLOAD_DIR", "/data/uploads")
PUBLIC_GATEWAY_URL = os.environ.get("PUBLIC_GATEWAY_URL", "http://localhost:8080")

_blob_service_client = None
if AZURE_CONN_STR:
    from azure.storage.blob import BlobServiceClient

    _blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
    try:
        _blob_service_client.create_container(AZURE_CONTAINER)
    except Exception:
        pass  # container already exists — fine


def using_azure_blob():
    return _blob_service_client is not None


def save_image(file_storage):
    """Takes a Werkzeug FileStorage (or None) and returns a public URL, or None."""
    if file_storage is None or file_storage.filename == "":
        return None

    ext = os.path.splitext(file_storage.filename)[1] or ".jpg"
    blob_name = f"{uuid.uuid4().hex}{ext}"

    if _blob_service_client:
        blob_client = _blob_service_client.get_blob_client(AZURE_CONTAINER, blob_name)
        blob_client.upload_blob(file_storage.stream, overwrite=True)
        return blob_client.url

    os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)
    file_storage.save(os.path.join(LOCAL_UPLOAD_DIR, blob_name))
    # Served back out through the gateway's generic proxy at
    # /api/listings/uploads/<name> -> this service's /uploads/<name> route.
    return f"{PUBLIC_GATEWAY_URL}/api/listings/uploads/{blob_name}"
