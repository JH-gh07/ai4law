#!/usr/bin/env python3
"""Phase D: cross-verification — code evidence + output audit matrix."""

import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ISSUE_FIX_MAP = [
    {"id":"R1","title":"us_14117 DOCX 渲染失败","sev":"P0","task":"A2+B5","checks":{
        "B5_template_9_sections":{"file":"resources/templates/us/4.2_us_14117_compliance_template_v0.md","pat":"## 九、附件与持续监控"},
        "B5_fallback_structured":{"file":"backend/domains/us/eo14117/service.py","pat":"## 五、风险详情与分析"},
        "A2_normalize_import":{"file":"backend/domains/us/eo14117/service.py","pat":"normalize_legal_markdown_structure"},
    }},
    {"id":"R2","title":"assessment footnotes 回写失败","sev":"P0","task":"A2","checks":{
        "A2_numeric_footnotes":{"file":"backend/common/llm/postprocess.py","pat":"def _resolve_numeric_footnotes"},
        "A2_pipeline_fallback":{"file":"backend/common/llm/postprocess.py","pat":"numeric_footnotes"},
    }},
    {"id":"R3","title":"pipia CIT截断标记","sev":"P0","task":"A2","checks":{
        "A2_truncated_marker_re":{"file":"backend/common/llm/postprocess.py","pat":"_TRUNCATED_CIT_MARKER_RE"},
    }},
    {"id":"R4","title":"dpia 占位文本","sev":"P0","task":"A1+C4","checks":{
        "C4_dpia_quality_gate":{"file":"backend/domains/eu/dpia/service.py","pat":"def _check_chapter_quality"},
    }},
    {"id":"R5","title":"cpra 占位文本","sev":"P0","task":"A1+C4","checks":{
        "A1_strict_constraint_no_halluc":{"file":"backend/common/llm/module_generator.py","pat":"不得新增行业"},
    }},
    {"id":"R6","title":"cn_flow 占位文本","sev":"P0","task":"A1+C4","checks":{
        "A1_system_prompt_exists":{"file":"backend/common/llm/module_generator.py","pat":"你是一名资深数据合规律师"},
    }},
    {"id":"R7","title":"eu_scc Clause截断","sev":"HIGH","task":"B3","checks":{
        "B3_enrich_finding_texts":{"file":"backend/domains/eu/scc_review/scc_rule_engine.py","pat":"def _enrich_finding_texts"},
        "B3_suggested_text_defaults":{"file":"backend/domains/eu/scc_review/scc_rule_engine.py","pat":"_SUGGESTED_TEXT_DEFAULTS"},
    }},
    {"id":"R8","title":"us_14117 markdown崩坏","sev":"HIGH","task":"B5","checks":{
        "B5_template_60_lines":{"file":"resources/templates/us/4.2_us_14117_compliance_template_v0.md","pat":"风险匹配矩阵"},
    }},
    {"id":"R9","title":"pipia 表格截断","sev":"MEDIUM","task":"A1+B2","checks":{
        "B2_fact_refs_linked":{"file":"backend/domains/cn/pipia/service.py","pat":"fact_refs=matching_fact_ids"},
        "A1_rule_based_chapter":{"file":"backend/domains/cn/pipia/service.py","pat":"def _render_rule_based_chapter"},
    }},
    {"id":"C1","title":"LLM静默失败","sev":"P0","task":"A1+C4","checks":{
        "C4_assessment_state":{"file":"backend/domains/cn/security_assessment/service.py","pat":"def _check_chapter_quality"},
        "C4_dpia_state":{"file":"backend/domains/eu/dpia/service.py","pat":"def _check_chapter_quality"},
        "A1_pipia_rule_based":{"file":"backend/domains/cn/pipia/service.py","pat":"_render_rule_based_chapter"},
    }},
    {"id":"C2","title":"CIT标记崩溃","sev":"P0","task":"A2","checks":{
        "A2_resolve_numeric":{"file":"backend/common/llm/postprocess.py","pat":"def _resolve_numeric_footnotes"},
        "A2_strict_cit_format":{"file":"backend/common/llm/module_generator.py","pat":"严禁使用"},
    }},
    {"id":"C3","title":"evidence_chain空值","sev":"HIGH","task":"A3","checks":{
        "A3_pipia_legal_basis":{"file":"backend/domains/cn/pipia/service.py","pat":"legal_basis="},
        "A3_assessment_doc_refs":{"file":"backend/domains/cn/security_assessment/evidence_builder.py","pat":"document_refs=_extract_document_refs"},
        "A3_euscc_doc_refs":{"file":"backend/domains/eu/dpia/evidence_builder.py","pat":"document_refs=_extract_document_refs"},
        "A3_us14117_doc_refs":{"file":"backend/domains/us/eo14117/evidence_builder.py","pat":"document_refs=_extract_document_refs"},
        "A3_assessment_rag":{"file":"backend/domains/cn/security_assessment/evidence_builder.py","pat":"rag_query_used="},
    }},
    {"id":"C4","title":"tia推测措辞","sev":"MEDIUM","task":"C2","checks":{
        "C2_no_speculation":{"file":"backend/common/llm/module_generator.py","pat":"不得使用推测"},
    }},
    {"id":"C5","title":"pipia测试泄漏","sev":"MEDIUM","task":"C1","checks":{
        "C1_disclaimer_re":{"file":"backend/domains/cn/pipia/service.py","pat":"_TEST_DISCLAIMER_RE"},
    }},
    {"id":"C6","title":"PATH_MISMATCH","sev":"HIGH","task":"B1","checks":{
        "B1_state_enum":{"file":"backend/domains/cn/security_assessment/task_state.py","pat":"PATH_MISMATCH"},
        "B1_error_class":{"file":"backend/domains/cn/security_assessment/task_state.py","pat":"class PathMismatchError"},
        "B1_handler":{"file":"backend/domains/cn/security_assessment/service.py","pat":"except PathMismatchError"},
    }},
    {"id":"C7","title":"pipia单条Issue","sev":"HIGH","task":"B2","checks":{
        "B2_8_issue_appends":{"file":"backend/domains/cn/pipia/service.py","pat":"告知同意机制存在缺陷"},
    }},
    {"id":"C8","title":"euscc original_text","sev":"HIGH","task":"B3","checks":{
        "B3_extract_text":{"file":"backend/domains/eu/scc_review/scc_rule_engine.py","pat":"def _extract_text_by_location"},
    }},
    {"id":"C9","title":"material_checklist","sev":"MEDIUM","task":"C3","checks":{
        "C3_20_checklist":{"file":"backend/domains/cn/security_assessment/report_renderer.py","pat":"_SECURITY_ASSESSMENT_CHECKLIST"},
    }},
    {"id":"C10","title":"硬编码COMPLETED","sev":"MEDIUM","task":"C4","checks":{
        "C4_assessment_dynamic":{"file":"backend/domains/cn/security_assessment/service.py","pat":"_check_chapter_quality"},
        "C4_dpia_dynamic":{"file":"backend/domains/eu/dpia/service.py","pat":"_check_chapter_quality"},
    }},
]

def check_pattern(rel: str, pat: str) -> bool:
    p = ROOT / rel
    if not p.exists(): return False
    return pat in p.read_text(encoding="utf-8")

def verify_fixes():
    results = []; passed = failed = 0
    for issue in ISSUE_FIX_MAP:
        checks = {}
        for name, spec in issue["checks"].items():
            checks[name] = check_pattern(spec["file"], spec["pat"])
        ok = all(checks.values())
        (passed if ok else failed) and None or (passed := passed + 1) if ok else (failed := failed + 1)
        results.append({"id":issue["id"],"title":issue["title"],"severity":issue["sev"],
                        "task":issue["task"],"status":"VERIFIED" if ok else "NOT_APPLIED","checks":checks})
    return {"total":len(results),"passed":passed,"failed":failed,"issues":results}

def check_markdown(mod: str):
    p = ROOT / "tmp" / mod / "markdown.md"
    if not p.exists(): return {"module":mod,"exists":False}
    t = p.read_text(encoding="utf-8")
    lines = t.split("\n")
    headings = [l.strip()[:80] for l in lines if l.strip().startswith("#")]
    return {"module":mod,"exists":True,"lines":len(lines),"chars":len(t),
            "headings":len(headings),"heading_list":headings[:10],
            "has_placeholder":"占位" in t or "LLM未配置" in t,
            "has_cit_truncated":"{{CIT-" in t}

def main(output_path=None):
    print("=" * 70)
    print("Phase D: Cross-Verification")
    print("=" * 70)

    print("\n[1] Code Fix Verification")
    r = verify_fixes()
    print(f"    {r['passed']}/{r['total']} VERIFIED, {r['failed']} NOT_APPLIED")
    for it in r["issues"]:
        if it["status"]!="VERIFIED":
            bad = [k for k,v in it["checks"].items() if not v]
            print(f"    ✗ {it['id']}: {it['title']} — {bad}")

    print("\n[2] Output Markdown Analysis")
    mods = ["assessment","pipia","dpia","eu_scc","bcr","us_14117","cn_flow","cpra","tia","review","diagnosis"]
    md = {}
    for m in mods:
        a = check_markdown(m); md[m] = a
        flags = ""
        if a.get("has_placeholder"): flags += " ⚠PLACEHOLDER"
        if a.get("has_cit_truncated"): flags += " ⚠CIT"
        if a["exists"]:
            print(f"    {m:15s} {a['lines']:>4d}L {a['chars']:>5d}c {a['headings']:>2d}H{flags}")
        else:
            print(f"    {m:15s} NO OUTPUT")

    s = {"code":r,"markdown":md,"verdict":{
        "all_fixes_ok":r["failed"]==0,
        "placeholder_modules":[m for m,v in md.items() if v.get("has_placeholder")],
        "cit_truncated":[m for m,v in md.items() if v.get("has_cit_truncated")],
    }}

    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")
    print(f"  Code fixes: {r['passed']}/{r['total']} VERIFIED")
    ph = s["verdict"]["placeholder_modules"]
    print(f"  Placeholder remaining: {ph if ph else 'NONE ✅'}")
    print(f"  CIT truncated: {s['verdict']['cit_truncated'] or 'NONE ✅'}")

    if output_path:
        out = Path(output_path); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  Report → {out}")
    return s

if __name__=="__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output",default=None)
    a = p.parse_args()
    main(output_path=a.output)
