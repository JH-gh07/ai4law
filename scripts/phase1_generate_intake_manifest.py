#!/usr/bin/env python3
"""
Phase 1: Generate intake manifest for resources/new/
Records path, MIME, size, SHA-256, source package, and initial asset_class for 219 files.
"""
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any

def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def classify_asset(path: Path) -> str:
    """Initial asset_class based on directory and extension."""
    parts = path.parts
    stem = path.stem.lower()
    
    # Noise files
    if path.name == ".DS_Store" or path.name.startswith("~$"):
        return "noise"
    
    # By directory
    if "知识库补充" in parts:
        if path.suffix.lower() in [".html", ".md"]:
            return "index_catalog"
        return "legal_source_candidate"
    
    if "黄金标准" in parts or "种子案例" in parts:
        if "基准材料" in stem or "论文" in stem:
            return "research_reference"
        if path.suffix.lower() == ".xlsx":
            return "benchmark_scoring_sheet"
        return "benchmark_seed_case"
    
    if "功能路径描述" in parts:
        if "reference" in stem.lower() or "参考" in stem:
            return "legal_source_duplicate"
        if "功能说明" in stem or "测试案例" in stem:
            return "requirement_spec"
        if "流程" in stem:
            return "requirement_workflow"
        return "requirement_support"
    
    # Root files
    if "需求说明书" in stem:
        return "prd"
    if "诊断说明" in stem or "实务" in stem:
        return "product_manual"
    if stem.startswith("gb"):
        return "standard_reference"
    
    return "unknown"

def generate_manifest(base_dir: Path) -> dict[str, Any]:
    """Generate intake manifest."""
    entries = []
    
    for item in sorted(base_dir.rglob("*")):
        if not item.is_file():
            continue
        
        rel_path = item.relative_to(base_dir)
        
        entry = {
            "path": str(rel_path),
            "size_bytes": item.stat().st_size,
            "mime_type": mimetypes.guess_type(item.name)[0] or "application/octet-stream",
            "sha256": compute_sha256(item),
            "asset_class": classify_asset(rel_path),
            "disposition": "pending_review"
        }
        
        entries.append(entry)
    
    manifest = {
        "manifest_version": "1.0.0",
        "phase": "Phase 1 - Resource Intake",
        "base_directory": "resources/new",
        "total_files": len(entries),
        "generated_at": "2026-08-07T10:00:00+0800",
        "entries": entries
    }
    
    return manifest

if __name__ == "__main__":
    base = Path("resources/new")
    if not base.exists():
        print(f"ERROR: {base} does not exist")
        exit(1)
    
    manifest = generate_manifest(base)
    
    output = Path("resources/new/manifest.intake.v1.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Generated manifest: {output}")
    print(f"  Total files: {manifest['total_files']}")
    
    # Summary by asset_class
    from collections import Counter
    classes = Counter(e["asset_class"] for e in manifest["entries"])
    print("\n  By asset_class:")
    for cls, count in classes.most_common():
        print(f"    {cls}: {count}")
