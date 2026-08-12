# DEPRECATED — Phase 0 completed 2026-08-12. See status/manifest/resources_new_v2_phase0.json
# Original source: scripts/phase1_analyze_manifest.py.bak
#!/usr/bin/env python3
"""Phase 1: Analyze intake manifest for duplicates, anomalies, and security concerns."""
import json
from collections import defaultdict
from pathlib import Path

def analyze_manifest(manifest_path: Path):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    
    entries = manifest["entries"]
    
    # Group by SHA-256 (duplicates)
    by_hash = defaultdict(list)
    for e in entries:
        by_hash[e["sha256"]].append(e["path"])
    
    duplicates = {h: paths for h, paths in by_hash.items() if len(paths) > 1}
    
    # Same name, different hash
    by_name = defaultdict(list)
    for e in entries:
        name = Path(e["path"]).name
        by_name[name].append((e["path"], e["sha256"]))
    
    name_conflicts = {name: items for name, items in by_name.items() if len(set(h for _, h in items)) > 1}
    
    # MIME mismatches
    mime_mismatches = []
    for e in entries:
        path = Path(e["path"])
        ext = path.suffix.lower()
        mime = e["mime_type"]
        
        expected = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        
        if ext in expected and mime != expected[ext]:
            mime_mismatches.append(e["path"])
    
    # Large files
    large_files = [(e["path"], e["size_bytes"]) for e in entries if e["size_bytes"] > 10_000_000]
    
    # Noise files
    noise = [e["path"] for e in entries if e["asset_class"] == "noise"]
    
    # Unknown classification
    unknown = [e["path"] for e in entries if e["asset_class"] == "unknown"]
    
    # Generate report
    report = {
        "total_files": len(entries),
        "duplicates": {
            "count": len(duplicates),
            "groups": [{"hash": h[:16], "paths": p} for h, p in list(duplicates.items())[:5]]
        },
        "name_conflicts": {
            "count": len(name_conflicts),
            "examples": list(name_conflicts.keys())[:5]
        },
        "mime_mismatches": {
            "count": len(mime_mismatches),
            "paths": mime_mismatches[:5]
        },
        "large_files": {
            "count": len(large_files),
            "files": [{"path": p, "mb": round(s/1_000_000, 2)} for p, s in large_files[:5]]
        },
        "noise_files": {
            "count": len(noise),
            "paths": noise
        },
        "unknown_classification": {
            "count": len(unknown),
            "note": "These require manual asset_class assignment"
        }
    }
    
    output = Path("resources/new/analysis.phase1.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Analysis complete: {output}")
    print(f"\n  Duplicates (same hash): {report['duplicates']['count']}")
    print(f"  Name conflicts (same name, diff hash): {report['name_conflicts']['count']}")
    print(f"  MIME mismatches: {report['mime_mismatches']['count']}")
    print(f"  Large files (>10MB): {report['large_files']['count']}")
    print(f"  Noise files: {report['noise_files']['count']}")
    print(f"  Unknown classification: {report['unknown_classification']['count']}")
    
    return report

if __name__ == "__main__":
    manifest_path = Path("resources/new/manifest.intake.v1.json")
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found")
        exit(1)
    
    analyze_manifest(manifest_path)
