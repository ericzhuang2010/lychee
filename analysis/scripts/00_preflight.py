#!/usr/bin/env python3
"""Outcome-free filesystem, resource, checksum, and URL preflight."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--archive")
    parser.add_argument("--required", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--stage", type=int, default=0)
    parser.add_argument("--no-url-check", action="store_true")
    return parser.parse_args()


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def file_type_ok(path: Path, expected: str) -> tuple[bool, str]:
    with path.open("rb") as handle:
        prefix = handle.read(8)
    if expected == "pdf":
        return prefix.startswith(b"%PDF-"), repr(prefix)
    if expected == "zip":
        return prefix.startswith(b"PK"), repr(prefix)
    if expected == "gzip":
        return prefix.startswith(b"\x1f\x8b"), repr(prefix)
    if expected == "text":
        try:
            path.read_text(encoding="utf-8")
            return True, "utf-8"
        except UnicodeDecodeError as exc:
            return False, str(exc)
    return True, "not checked"


def memory_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def url_status(url: str) -> tuple[bool, str]:
    headers = {"User-Agent": "lychee-discovery-preflight/1.0"}
    request = urllib.request.Request(url, headers=headers, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code not in {403, 405}:
            return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, str(exc)
    request = urllib.request.Request(
        url, headers={**headers, "Range": "bytes=0-0"}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status in {200, 206}, f"HTTP {response.status}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, str(exc)


def row(
    category: str,
    item_id: str,
    target: str,
    status: str,
    required: bool,
    observed: Any,
    expected: Any,
    detail: str = "",
) -> dict[str, str]:
    return {
        "category": category,
        "id": item_id,
        "target": target,
        "status": status,
        "required": str(required).lower(),
        "observed": str(observed),
        "expected": str(expected),
        "detail": detail,
    }


def main() -> int:
    args = parse_args()
    project = Path(args.project).resolve()
    required_path = Path(args.required)
    if not required_path.is_absolute():
        required_path = project / required_path
    config = json.loads(required_path.read_text())
    rows: list[dict[str, str]] = []

    disk = shutil.disk_usage(project)
    minimum_disk = int(config["resources"]["minimum_free_bytes"])
    rows.append(
        row(
            "resource",
            "free_disk_bytes",
            str(project),
            "PASS" if disk.free >= minimum_disk else "FAIL",
            True,
            disk.free,
            f">={minimum_disk}",
        )
    )
    cpus = os.cpu_count() or 0
    minimum_cpus = int(config["resources"]["minimum_cpus"])
    rows.append(
        row(
            "resource",
            "cpu_count",
            str(project),
            "PASS" if cpus >= minimum_cpus else "FAIL",
            True,
            cpus,
            f">={minimum_cpus}",
        )
    )
    ram = memory_bytes()
    preferred_ram = int(config["resources"]["preferred_ram_bytes"])
    rows.append(
        row(
            "resource",
            "ram_bytes",
            "/proc/meminfo",
            "PASS" if ram is not None and ram >= preferred_ram else "WARN",
            False,
            ram if ram is not None else "unknown",
            f"preferred>={preferred_ram}",
            "Low RAM is nonblocking only with one alignment and capped STAR sorting.",
        )
    )
    if args.archive:
        archive = Path(args.archive).expanduser().resolve()
        rows.append(
            row(
                "directory",
                "legacy_archive",
                str(archive),
                "PASS" if archive.is_dir() else "WARN",
                False,
                archive.exists(),
                "directory if available",
                "Missing archive is nonblocking because S2 is recovered and S3 is reconstructable.",
            )
        )

    for item in config["files"]:
        if int(item.get("stage", 0)) > args.stage:
            continue
        required = bool(item.get("required", False))
        path = project / item["path"]
        if not path.exists():
            rows.append(
                row(
                    "file",
                    item["id"],
                    str(path),
                    "FAIL" if required else "ROUTE",
                    required,
                    "missing",
                    item.get("type", "file"),
                    item.get("reconstruction_route", ""),
                )
            )
            continue
        size = path.stat().st_size
        minimum = int(item.get("minimum_bytes", 0))
        type_ok, type_detail = file_type_ok(path, item.get("type", ""))
        checks: list[tuple[str, str, str]] = []
        for algorithm in ("md5", "sha256"):
            if algorithm in item:
                observed_digest = digest(path, algorithm)
                checks.append((algorithm, observed_digest, item[algorithm]))
        checksum_ok = all(observed == expected for _, observed, expected in checks)
        passed = size >= minimum and type_ok and checksum_ok
        checksum_detail = "; ".join(
            f"{algorithm}={observed}" for algorithm, observed, _ in checks
        )
        rows.append(
            row(
                "file",
                item["id"],
                str(path),
                "PASS" if passed else "FAIL",
                required,
                size,
                f"type={item.get('type', 'any')}; bytes>={minimum}",
                "; ".join(part for part in (type_detail, checksum_detail) if part),
            )
        )

    for item in config.get("urls", []):
        if int(item.get("stage", 0)) > args.stage:
            continue
        required = bool(item.get("required", False))
        if args.no_url_check:
            ok, detail = True, "skipped by --no-url-check"
            status = "SKIP"
        else:
            ok, detail = url_status(item["url"])
            status = "PASS" if ok else ("FAIL" if required else "WARN")
        rows.append(
            row(
                "url",
                item["id"],
                item["url"],
                status,
                required,
                detail,
                "HTTP 2xx/3xx",
            )
        )

    report = Path(args.report)
    if not report.is_absolute():
        report = project / report
    report.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "category",
        "id",
        "target",
        "status",
        "required",
        "observed",
        "expected",
        "detail",
    ]
    with report.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    failures = [entry for entry in rows if entry["required"] == "true" and entry["status"] == "FAIL"]
    print(f"Wrote {len(rows)} checks to {report}")
    if failures:
        print("Required preflight failures: " + ", ".join(entry["id"] for entry in failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

