# -*- coding: utf-8 -*-
"""Upload app/static/assets/core/*.jpg to MinIO/S3 under core/<filename>."""
import argparse
import mimetypes
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CORE = BASE / "app" / "static" / "assets" / "core"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:9000")
    ap.add_argument("--bucket", default="rock-core")
    ap.add_argument("--access-key", default="minioadmin")
    ap.add_argument("--secret-key", default="minioadmin")
    ap.add_argument("--region", default="us-east-1")
    args = ap.parse_args()

    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3", endpoint_url=args.endpoint,
        aws_access_key_id=args.access_key,
        aws_secret_access_key=args.secret_key,
        region_name=args.region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    try:
        s3.create_bucket(Bucket=args.bucket)
    except Exception:
        pass

    files = sorted(p for p in CORE.iterdir() if p.is_file())
    total = 0
    for p in files:
        key = "core/" + p.name
        s3.upload_file(
            str(p), args.bucket, key,
            ExtraArgs={"ContentType": mimetypes.guess_type(p.name)[0] or "image/jpeg"},
        )
        total += p.stat().st_size
        print("uploaded", key)
    print(f"done: {len(files)} files, {total/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
