#!/usr/bin/env python3
"""Rewrite `image:` fields in HA add-on config files.

Reads UPSTREAM_URL, UPSTREAM_BRANCH, MIRROR_IMAGE_PREFIX from environment
(populated from .mirror/config.env by the workflow).

For every addon (dir containing config.yaml/.yml/.json), if config has
`image: <upstream>`, rewrites it to `image: {PREFIX}{sanitized-upstream}`
and records the mapping in .mirror/image-map.json for the image-mirror
workflow to consume.

Sanitization: lowercase, then translate '/' and '.' to '-'.
Example: ghcr.io/hassio-addons/ssh -> ghcr-io-hassio-addons-ssh
Result:  ghcr.io/woowtech/ha-mirror-ghcr-io-hassio-addons-ssh
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PREFIX = os.environ.get("MIRROR_IMAGE_PREFIX", "ghcr.io/woowtech/ha-mirror-")
UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "")
UPSTREAM_BRANCH = os.environ.get("UPSTREAM_BRANCH", "")

SKIP_DIRS = {".git", ".github", ".mirror", "node_modules"}


def sanitize(image: str) -> str:
    return image.lower().translate(str.maketrans({"/": "-", ".": "-"}))


def load_config(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json":
        try:
            return "json", json.loads(text), text
        except Exception:
            return None, None, text
    return "yaml", None, text


# Horizontal whitespace only. Plain `\s*` after the colon swallows the newline,
# so a block-style field (`arch:` on its own line) captures the first list item
# instead of failing to match — which silently reduced `arches` to one entry.
H = r"[^\S\n]*"


def extract_field_yaml(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}{H}:{H}(.+?){H}$", text, re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip().strip('"').strip("'")
    return val or None


def extract_arches(addon_dir: Path, cfg_kind: str, cfg_data, cfg_text) -> list[str]:
    build = addon_dir / "build.yaml"
    if not build.exists():
        build = addon_dir / "build.json"
    if build.exists():
        try:
            btext = build.read_text(encoding="utf-8", errors="replace")
            if build.suffix == ".json":
                data = json.loads(btext)
                bf = data.get("build_from") or {}
            else:
                bf = {}
                in_bf = False
                for line in btext.splitlines():
                    if re.match(r"^build_from\s*:\s*$", line):
                        in_bf = True
                        continue
                    if in_bf:
                        m = re.match(r"^\s+([a-z0-9_]+)\s*:", line)
                        if m:
                            bf[m.group(1)] = True
                        elif re.match(r"^\S", line):
                            in_bf = False
            if bf:
                return sorted(bf.keys())
        except Exception:
            pass
    if cfg_kind == "json" and isinstance(cfg_data, dict):
        arches = cfg_data.get("arch") or []
    else:
        arches_line = extract_field_yaml(cfg_text, "arch")
        arches = []
        if arches_line:
            arches = [a.strip().strip('"').strip("'") for a in re.findall(r"[a-z0-9_]+", arches_line)]
        if not arches:
            arches = []
            in_arch = False
            for line in cfg_text.splitlines():
                if re.match(r"^arch\s*:\s*$", line):
                    in_arch = True
                    continue
                if in_arch:
                    m = re.match(r"^\s*-\s*(\S+)", line)
                    if m:
                        arches.append(m.group(1).strip('"').strip("'"))
                    elif re.match(r"^\S", line):
                        in_arch = False
    return sorted(arches) if arches else ["amd64", "aarch64", "armv7", "armhf", "i386"]


def process(cfg_path: Path):
    kind, data, text = load_config(cfg_path)
    if kind is None:
        return None
    if kind == "json":
        image = (data or {}).get("image") if isinstance(data, dict) else None
        version = (data or {}).get("version") if isinstance(data, dict) else None
        slug = (data or {}).get("slug") if isinstance(data, dict) else None
        name = (data or {}).get("name") if isinstance(data, dict) else None
    else:
        image = extract_field_yaml(text, "image")
        version = extract_field_yaml(text, "version")
        slug = extract_field_yaml(text, "slug")
        name = extract_field_yaml(text, "name")
    if not image:
        return None
    if image.startswith(PREFIX):
        return {
            "dir": str(cfg_path.parent),
            "slug": slug,
            "name": name,
            "upstream_image": None,
            "new_image": image,
            "version": version,
            "arches": extract_arches(cfg_path.parent, kind, data, text),
            "already_patched": True,
        }
    new_image = f"{PREFIX}{sanitize(image)}"
    if kind == "json":
        data["image"] = new_image
        cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        new_text = re.sub(
            rf"^(image{H}:{H}).+?{H}$",
            lambda m: f"{m.group(1)}{new_image}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        cfg_path.write_text(new_text, encoding="utf-8")
    return {
        "dir": str(cfg_path.parent),
        "slug": slug,
        "name": name,
        "upstream_image": image,
        "new_image": new_image,
        "version": version,
        "arches": extract_arches(cfg_path.parent, kind, data, text),
        "already_patched": False,
    }


def main() -> int:
    root = Path(".")
    results = []
    for cfg in sorted(root.rglob("config.*")):
        if cfg.name not in {"config.yaml", "config.yml", "config.json"}:
            continue
        if any(p in SKIP_DIRS for p in cfg.parts):
            continue
        r = process(cfg)
        if r:
            results.append(r)
            marker = "✓" if not r["already_patched"] else "="
            print(f"  {marker} {r['dir']}: {r.get('upstream_image') or r['new_image']} → {r['new_image']}")
    image_map = {
        "upstream_url": UPSTREAM_URL,
        "upstream_branch": UPSTREAM_BRANCH,
        "mirror_image_prefix": PREFIX,
        "addons": [r for r in results if r.get("upstream_image")],
    }
    Path(".mirror").mkdir(exist_ok=True)
    Path(".mirror/image-map.json").write_text(
        json.dumps(image_map, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nPatched {sum(1 for r in results if not r['already_patched'])} configs, "
          f"total tracked {len(results)}. Map: .mirror/image-map.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
