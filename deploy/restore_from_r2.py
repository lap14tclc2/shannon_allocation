from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

import boto3


def required(name: str) -> str:
    value = str(os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    endpoint = required("R2_ENDPOINT")
    access_key = required("R2_ACCESS_KEY_ID")
    secret_key = required("R2_SECRET_ACCESS_KEY")
    bucket = required("R2_BUCKET")
    prefix = str(os.environ.get("R2_PREFIX") or "qport").strip("/")
    namespace = Path(os.environ.get("QPORT_AUTH_NAMESPACE") or "/data/qport")
    namespace.mkdir(parents=True, exist_ok=True)

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    dbs: set[str] = set()
    pattern = re.compile(rf"^{re.escape(prefix)}/(.+?\.sqlite3)/")
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/"):
        for item in page.get("Contents") or []:
            match = pattern.match(str(item.get("Key") or ""))
            if match:
                dbs.add(match.group(1))

    if not dbs:
        print("R2 restore: no existing QPort databases found; starting fresh.", flush=True)
        return

    endpoint_host = re.sub(r"^https?://", "", endpoint).rstrip("/")
    env = dict(os.environ)
    env["AWS_ACCESS_KEY_ID"] = access_key
    env["AWS_SECRET_ACCESS_KEY"] = secret_key
    env["LITESTREAM_ACCESS_KEY_ID"] = access_key
    env["LITESTREAM_SECRET_ACCESS_KEY"] = secret_key
    env["LITESTREAM_S3_ENDPOINT"] = endpoint_host

    restored = 0
    for relative in sorted(dbs):
        target = namespace / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        replica_path = "/".join(quote(part, safe="") for part in relative.split("/"))
        replica = f"s3://{bucket}/{prefix}/{replica_path}?endpoint={endpoint_host}"
        print(f"R2 restore: {relative}", flush=True)
        subprocess.run(
            ["litestream", "restore", "-integrity-check", "quick", "-o", str(target), replica],
            check=True,
            env=env,
        )
        restored += 1

    print(f"R2 restore complete: {restored} database(s).", flush=True)


if __name__ == "__main__":
    main()
