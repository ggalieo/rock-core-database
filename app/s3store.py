# -*- coding: utf-8 -*-
"""Serve /assets/core/* from MinIO/S3 when configured; otherwise local static."""
import mimetypes
import os
from pathlib import Path

_client = None


def s3_enabled():
    return bool(os.environ.get("S3_BUCKET", "").strip() and os.environ.get("S3_ENDPOINT", "").strip())


def client():
    global _client
    if _client is not None:
        return _client
    try:
        import boto3
        from botocore.config import Config
    except ImportError as e:
        raise RuntimeError("S3 is enabled but boto3 is not installed. Run: pip install -r requirements-pg.txt") from e
    _client = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    return _client


def serve_core_object(handler, url_path):
    """Return True if the object was served from S3; False means use local file."""
    if not s3_enabled() or not url_path.startswith("/assets/core/"):
        return False
    filename = Path(url_path).name
    if not filename or "/" in filename or "\\" in filename:
        return False
    key = "core/" + filename
    bucket = os.environ["S3_BUCKET"]
    try:
        obj = client().get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
    except Exception:
        return False
    ctype = obj.get("ContentType") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "public, max-age=3600")
    handler.end_headers()
    handler.wfile.write(body)
    return True
