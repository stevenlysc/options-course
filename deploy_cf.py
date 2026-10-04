#!/usr/bin/env python3
"""Deploy options-course to Cloudflare Workers + wire /options routes.

Serves the course index at /options/ and lesson pages at /options/<slug>.
Routes ensured: invest.stevenlysc.com/options and /options/* -> options-course.

Usage: python3 deploy_cf.py [--name options-course]
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import uuid

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import (  # noqa: E402
    add_surrogate_to_request,
    read_json_response,
    read_response_body,
    DynamicCredentialError,
)

API = "https://api.cloudflare.com/client/v4"
CRED = "custom.cloudflare"
HOSTS = ["api.cloudflare.com"]
ACCOUNT = "babba54f52e4076a4aa08e0c59f07229"
ZONE = "6a30e1d5cb1b8eaa6397f2b454c4e868"
PROJ = os.path.dirname(os.path.abspath(__file__))


def _req(method, path, body=None, ctype=None):
    r = urllib.request.Request(API + path, data=body, method=method)
    if ctype:
        r.add_header("Content-Type", ctype)
    add_surrogate_to_request(r, CRED, allowed_hosts=HOSTS)
    return r


def _call(method, path, body=None, ctype=None):
    try:
        with urllib.request.urlopen(_req(method, path, body, ctype),
                                    timeout=120) as resp:
            return read_json_response(resp)
    except urllib.error.HTTPError as e:
        detail = read_response_body(e).decode("utf-8", errors="replace")[:500]
        raise DynamicCredentialError(f"Cloudflare {method} {path} -> "
                                     f"HTTP {e.code}: {detail}")


def _multipart(fields, files):
    boundary = "----cf" + uuid.uuid4().hex
    buf = bytearray()

    def part_headers(name, filename=None, ctype=None):
        disp = f'form-data; name="{name}"'
        if filename:
            disp += f'; filename="{filename}"'
        buf.extend(f"--{boundary}\r\n".encode())
        buf.extend(f"Content-Disposition: {disp}\r\n".encode())
        if ctype:
            buf.extend(f"Content-Type: {ctype}\r\n".encode())
        buf.extend(b"\r\n")

    for name, value in fields.items():
        part_headers(name, ctype="application/json")
        buf.extend(value.encode("utf-8") + b"\r\n")
    for name, (filename, ctype, data) in files.items():
        part_headers(name, filename, ctype)
        buf.extend(data + b"\r\n")
    buf.extend(f"--{boundary}--\r\n".encode())
    return bytes(buf), f"multipart/form-data; boundary={boundary}"


def ensure_routes(script_name):
    existing = _call("GET",
                     f"/zones/{ZONE}/workers/routes?per_page=100")["result"]
    have = {r["pattern"] for r in existing}
    for pattern in ("invest.stevenlysc.com/options",
                    "invest.stevenlysc.com/options/*"):
        if pattern in have:
            print(f"route exists: {pattern}", file=sys.stderr)
            continue
        out = _call("POST", f"/zones/{ZONE}/workers/routes",
                    json.dumps({"pattern": pattern,
                                "script": script_name}).encode(),
                    "application/json")
        if not out.get("success"):
            raise DynamicCredentialError(
                f"route create failed: {out.get('errors')}")
        print(f"route created: {pattern}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="options-course")
    args = ap.parse_args()

    worker_js = open(os.path.join(PROJ, "dist", "worker.js"),
                     encoding="utf-8").read()
    metadata = json.dumps({
        "main_module": "worker.js",
        "compatibility_date": "2026-09-15",
    })
    body, ctype = _multipart(
        {"metadata": metadata},
        {"worker.js": ("worker.js", "application/javascript+module",
                       worker_js.encode("utf-8"))},
    )
    out = _call("PUT",
                f"/accounts/{ACCOUNT}/workers/scripts/{args.name}",
                body, ctype)
    result = out.get("result", {})
    print(json.dumps({
        "ok": out.get("success", False),
        "id": result.get("id"),
        "modified_on": result.get("modified_on"),
        "errors": out.get("errors", []),
    }, ensure_ascii=False))
    if out.get("success"):
        ensure_routes(args.name)


if __name__ == "__main__":
    try:
        main()
    except DynamicCredentialError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
