#!/usr/bin/env python3
"""Evaluate surface features, case assertions, and cross-sample diversity of
deliberately defensive Chinese writing (stdlib only).

This script does NOT generate text, access an LLM, or verify deep semantic fidelity.
A separately obtained human/LLM judge report can be validated and combined via
--judge-json. The resulting semantic score is from THAT reviewer, not this script.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

NEGATION = re.compile(
    r"并不意味着|不意味着|并不代表|不代表|不等于|并不是说|不是说|"
    r"不能据此|不应理解为|不能简单|并不当然|不当然|不构成|更不是|"
    r"也不是|无意否认|不宜|不能因此|不能直接|不必然|无法据此|未必|≠"
)
BOUNDARIES = [
    "在特定条件下", "在当前", "从目前", "从现有", "一般经验", "具体情况", "个体差异",
    "不同场景", "不同情况", "不同的人", "实际情况", "适用范围", "适用条件", "前提条件",
    "覆盖范围", "因人而异", "仅供参考", "仍应", "局限", "边界", "目前掌握", "在一定程度上",
    "既定条件", "明示前提", "特定情境", "具体情境", "参照基准", "前置条件",
]
META = [
    "校验过程", "验证过程", "验证机制", "验证方法", "复核机制", "证据链", "测试覆盖",
    "判断标准", "确认过程", "用于验证", "验证的验证", "对校验", "元验证", "校验机制",
    "澄清这一点", "指出这些限制", "强调验证", "强调这些边界", "强调边界", "不是在否定",
    "否认修复价值", "否认校验价值", "取消个人偏好", "否定本次", "否定这次",
]
MISREAD_AXES = {
    "generalization": ["所有人", "全部", "任何人", "每个人", "所有情况", "普遍", "绝对", "全面领先", "所有接口"],
    "moralization": ["道德", "人格", "缺乏品味", "贬低", "否定", "价值", "指责", "标签化"],
    "obligation": ["必须", "统一标准", "统一要求", "强制", "照着选"],
    "causality": ["因果", "归因", "因果关系"],
    "evidence": ["证明", "测试", "校验", "验证", "依据", "保证", "可靠", "参照基准"],
    "time": ["未来所有", "长期稳定", "始终", "永久", "后续使用", "后续表现", "后续版本", "全天候"],
    "alternative": ["其他方案", "其他店", "其他选择", "不同观点", "另一方", "各方", "反对"],
}
CONNECTORS = ["当然", "与此同时", "需要强调", "值得注意", "有必要", "此外", "不过", "进一步", "即便", "即使"]
JUDGE_WEIGHTS = {
    "claim_preservation": 25,
    "factual_integrity": 20,
    "misread_diversity": 15,
    "recursive_logic": 15,
    "naturalness": 15,
    "target_fit": 10,
}
TARGETS = {0: (0, 0), 1: (0, 2), 2: (1, 4), 3: (2, 6), 4: (4, 10), 5: (5, 16)}

PRESERVE_STOPWORDS = {
    "建议", "应该", "最好", "认为", "觉得", "说话", "一般", "意义", "方面",
    "个人", "本次", "相关", "已知", "主观", "声称", "进行", "保持", "必须",
    "启用", "仅", "的", "了", "在", "是", "和", "与", "且", "并", "对",
    "把", "被", "不", "没", "有", "为", "以", "上", "中", "下",
}
EMPATHY_CLICHES = ["理解你的感受", "理解大家的感受", "理解各方", "感同身受", "完全理解你"]
INTERLOCUTOR_CLICHES = ["有人可能认为", "部分人可能会说", "外界或许会质疑", "批评者可能", "有人会指责"]
CARRIER_TERMS = ["测试", "哈希", "校验", "监控", "采样", "日志", "压测", "合同", "审计"]


def extract_preserve_keywords(preserve: str, raw_input: str = "") -> list[str]:
    """Extract 2-char Chinese content bigrams from preserve (and input fallback) for recall check."""
    combined = f"{preserve} {raw_input}".strip()
    chunks = re.findall(r"[一-鿿]+", combined)
    tokens: list[str] = []
    for chunk in chunks:
        if len(chunk) < 2:
            continue
        for i in range(len(chunk) - 1):
            bg = chunk[i : i + 2]
            if bg not in PRESERVE_STOPWORDS and not any(ch in "的了在是和与且并对把被为以上" for ch in bg):
                if bg not in tokens:
                    tokens.append(bg)
    return tokens


def check_preserve_retention(text: str, preserve: str, raw_input: str = "", level: int = 3) -> dict[str, Any]:
    if level == 0 or "不启用" in preserve:
        return {"applicable": False, "passed": True, "recall": 1.0, "matched": [], "missing": []}
    keywords = extract_preserve_keywords(preserve, raw_input)
    if not keywords:
        return {"applicable": False, "passed": True, "recall": 1.0, "matched": [], "missing": []}
    matched = [kw for kw in keywords if kw in text]
    missing = [kw for kw in keywords if kw not in text]
    recall = round(len(matched) / len(keywords), 2)
    return {
        "applicable": True,
        "passed": recall >= 0.4,
        "recall": recall,
        "matched": matched,
        "missing": missing,
    }


def check_case_constraints(
    text: str,
    level: int,
    raw_input: str = "",
    overrides: dict[str, Any] | None = None,
    guardrail: str = "",
) -> dict[str, Any]:
    """Verify deterministic surface constraints from overrides and guardrails."""
    overrides = overrides or {}
    violations: list[str] = []

    if overrides.get("empathy") == 0 or "不得使用理解你的感受" in guardrail:
        hits = [p for p in EMPATHY_CLICHES if p in text]
        if hits:
            violations.append(f"empathy=0 violated by: {', '.join(hits)}")

    if overrides.get("recursive_depth") == 0 or "不得出现二阶免责声明" in guardrail:
        meta_hits = [x for x in META if x in text]
        if meta_hits:
            violations.append(f"recursive_depth=0 violated by meta cues: {', '.join(meta_hits)}")

    if overrides.get("misreads") == 0 or "不能虚构任何人的反驳" in guardrail:
        interlocutor_hits = [p for p in INTERLOCUTOR_CLICHES if p in text]
        if interlocutor_hits:
            violations.append(f"misreads=0 violated by hypothetical interlocutor: {', '.join(interlocutor_hits)}")

    if "首句不以需要强调的是开头" in guardrail:
        first_sent = re.split(r"[。！？!?]", text.strip())[0].strip()
        if first_sent.startswith("需要强调的是"):
            violations.append("first sentence starts with forbidden '需要强调的是'")

    max_chars = overrides.get("max_chars")
    if isinstance(max_chars, int) and max_chars > 0:
        actual_chars = len(re.sub(r"\s+", "", text))
        if actual_chars > max_chars:
            violations.append(f"max_chars={max_chars} exceeded ({actual_chars} chars)")

    if "零新增载体" in guardrail or "不得凭空脑补" in guardrail:
        source_carriers = {c for c in CARRIER_TERMS if c in raw_input}
        invented = [c for c in CARRIER_TERMS if c in text and c not in source_carriers]
        if invented:
            violations.append(f"unmentioned carriers invented: {', '.join(invented)}")

    if level == 1 and ("紧急行动指令" in guardrail or "行动建议直接" in guardrail):
        neg_count = len(NEGATION.findall(text))
        if neg_count > 1:
            violations.append(f"emergency safety diluted by {neg_count} defensive negations")

    return {"passed": len(violations) == 0, "violations": violations}


def analyze(text: str, level: int = 3) -> dict[str, Any]:
    if level not in TARGETS:
        raise ValueError("level must be an integer from 0 to 5")
    body = re.sub(r"\s+", "", text)
    chars = len(body)
    negations = NEGATION.findall(body)
    boundaries = sorted(x for x in BOUNDARIES if x in body)
    meta = sorted(x for x in META if x in body)
    axes = sorted(k for k, cues in MISREAD_AXES.items() if any(x in body for x in cues))
    connectors = sorted(x for x in CONNECTORS if x in body)
    marker_density = len(negations) * 100 / max(1, chars)
    lead_phrases = ["需要强调的是", "这里有必要", "与此同时", "不过", "当然"]
    repetition = {p: body.count(p) for p in lead_phrases if body.count(p) > 1}
    lo, hi = TARGETS[level]
    dev = lo - len(negations) if len(negations) < lo else max(0, len(negations) - hi)

    aux_score = (
        min(20, 4 * len(axes))
        + min(15, 3 * len(boundaries))
        + min(20, 5 * len(meta))
        + min(15, 3 * len(connectors))
    )
    if len(negations) == 0:
        aux_score = aux_score // 3

    surface = (
        min(30, 4 * len(negations))
        + aux_score
        - min(15, 5 * sum(n - 1 for n in repetition.values()))
    )
    fit_penalty = 25 * dev if level == 0 else 10 * dev
    return {
        "characters": chars,
        "target_level": level,
        "defensive_marker_occurrences": len(negations),
        "markers_per_100_chars": round(marker_density, 2),
        "misread_axis_hints": axes,
        "boundary_hints": boundaries,
        "meta_validation_hints": meta,
        "connector_hints": connectors,
        "repeated_lead_phrases": repetition,
        "surface_style_score_0_100": max(0, min(100, surface)),
        "level_fit_surface_score_0_100": max(0, 100 - fit_penalty),
        "count_within_level_band": lo <= len(negations) <= hi,
        "caveat": "仅衡量表面特征与断言规则；不能替代深层语义保真与事实审查。",
    }


def analyze_cross_sample_diversity(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect template collisions in opening prefixes and closing suffixes across a batch."""
    defensive_items = [x for x in items if x.get("level", 3) >= 1]
    if len(defensive_items) < 2:
        return {
            "evaluated_count": len(defensive_items),
            "opening_diversity_ratio": 1.0,
            "closing_diversity_ratio": 1.0,
            "opening_collisions": {},
            "closing_collisions": {},
            "warnings": [],
        }

    opening_groups: dict[str, list[str]] = {}
    closing_groups: dict[str, list[str]] = {}
    for idx, item in enumerate(defensive_items):
        item_id = str(item.get("id", idx))
        compact = re.sub(r"\s+", "", item["text"])
        sentences = [s for s in re.split(r"[。！？!?；;]", compact) if s]
        first = sentences[0] if sentences else compact
        last = sentences[-1] if sentences else compact
        open_key = first[:8]
        close_key = last[-10:]
        opening_groups.setdefault(open_key, []).append(item_id)
        closing_groups.setdefault(close_key, []).append(item_id)

    open_collisions = {k: v for k, v in opening_groups.items() if len(v) > 1}
    close_collisions = {k: v for k, v in closing_groups.items() if len(v) > 1}
    warnings: list[str] = []
    for prefix, ids in open_collisions.items():
        warnings.append(f"开头模板撞车 '{prefix}...' 出现在 {len(ids)} 条样本中: {', '.join(ids)}")
    for suffix, ids in close_collisions.items():
        warnings.append(f"结尾模板撞车 '...{suffix}' 出现在 {len(ids)} 条样本中: {', '.join(ids)}")

    n = len(defensive_items)
    return {
        "evaluated_count": n,
        "opening_diversity_ratio": round(len(opening_groups) / n, 2),
        "closing_diversity_ratio": round(len(closing_groups) / n, 2),
        "opening_collisions": open_collisions,
        "closing_collisions": close_collisions,
        "warnings": warnings,
    }


def evaluate_external_judge(review: dict[str, Any]) -> dict[str, Any]:
    """Validate a review supplied by a DIFFERENT reviewer; never create it."""
    if not isinstance(review, dict) or not isinstance(review.get("scores"), dict):
        raise ValueError("judge JSON requires an object with a scores object")
    scores = review["scores"]
    absent = set(JUDGE_WEIGHTS) - set(scores)
    if absent:
        raise ValueError("judge JSON missing scores: " + ", ".join(sorted(absent)))
    for name in JUDGE_WEIGHTS:
        score = scores[name]
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 5:
            raise ValueError(f"judge score {name!r} must be a number from 0 to 5")
    veto = review.get("veto", False)
    if not isinstance(veto, bool):
        raise ValueError("judge.veto must be boolean")
    for name in ("issues", "suggestions"):
        if name in review and (
            not isinstance(review[name], list)
            or not all(isinstance(x, str) for x in review[name])
        ):
            raise ValueError(f"judge.{name} must be an array of strings")
    total = sum(scores[k] * w / 5 for k, w in JUDGE_WEIGHTS.items())
    return {
        "source": "external reviewer, not script-inferred",
        "weighted_score_0_100": round(total, 1),
        "accepted": not veto
        and total >= 80
        and scores["claim_preservation"] >= 4
        and scores["factual_integrity"] >= 4,
        "veto": veto,
        "scores": {k: scores[k] for k in JUDGE_WEIGHTS},
        "issues": review.get("issues", []),
        "suggestions": review.get("suggestions", []),
        "caveat": "外部评分不等于事实已验证；其可信度取决于实际评审者和证据。",
    }


def load_outputs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    is_cases = False
    if isinstance(data, dict):
        if "outputs" in data:
            data = data["outputs"]
        elif "cases" in data:
            data = data["cases"]
            is_cases = True
    if not isinstance(data, list):
        raise ValueError("batch JSON must be a list, {outputs:[...]}, or {cases:[...]}")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"batch item {index} must be an object")
        text = row.get("text") if isinstance(row.get("text"), str) else row.get("response")
        if not isinstance(text, str) or not text.strip():
            if is_cases:
                continue
            raise ValueError(f"batch item {index} requires text or response string")
        level = row.get("level", 3)
        if level not in TARGETS:
            raise ValueError(f"batch item {index} has invalid level {level!r}")
        normalized.append({**row, "text": text, "level": level})
    if is_cases and not normalized:
        raise ValueError("cases JSON contains no populated 'response' or 'text' fields to evaluate")
    return normalized


def self_test() -> None:
    samples = [
        "这个方案不错。",
        "这个方案不错，但这并不意味着适合所有人，也不是说其他方案没有价值。具体情况仍应结合实际情况判断。",
        "这次校验通过不等于全链路已验证；即使复核验证过程，也不意味着验证机制本身绝对可靠。指出这些边界并不是在否定校验价值，更不代表已经发现实际错误。",
    ]
    values = [analyze(x)["surface_style_score_0_100"] for x in samples]
    assert values[0] < values[1] < values[2], values
    assert analyze(samples[2])["meta_validation_hints"]

    # Level 0 opt-out verification
    off_clean = analyze("直接说结论：这个方案可以推进。", level=0)
    assert off_clean["count_within_level_band"] and off_clean["level_fit_surface_score_0_100"] == 100
    off_leaky = analyze("这个方案可以推进，但这并不意味着没有风险。", level=0)
    assert not off_leaky["count_within_level_band"] and off_leaky["level_fit_surface_score_0_100"] < 100

    # Preserve retention verification
    keep_ok = check_preserve_retention("下雨天最好带伞，但这不意味着晴天也要带着。", "建议在下雨天携带雨伞", "下雨天最好带伞。", 3)
    assert keep_ok["passed"] and keep_ok["recall"] >= 0.5, keep_ok
    keep_lost = check_preserve_retention("我们需要综合考虑天气变化和个人出行习惯。", "建议在下雨天携带雨伞", "下雨天最好带伞。", 3)
    assert not keep_lost["passed"], keep_lost

    # Constraint & zero-carrier verification
    c_fail = check_case_constraints(
        "新版本接口快了不少，虽然监控采样维度有限，但局部提速不等于全链路稳定。",
        level=5,
        raw_input="接口响应快了不少。",
        overrides={"max_chars": 20},
        guardrail="零新增载体",
    )
    assert not c_fail["passed"] and len(c_fail["violations"]) == 2, c_fail

    # Cross-sample template collision verification
    dup_batch = [
        {"id": "a", "level": 3, "text": "需要强调的是，这个方案不错，但仍需结合实际情况判断。"},
        {"id": "b", "level": 3, "text": "需要强调的是，这家店很好吃，但仍需结合实际情况判断。"},
    ]
    div = analyze_cross_sample_diversity(dup_batch)
    assert div["opening_collisions"] and div["closing_collisions"], div

    review = {"scores": {k: 5 for k in JUDGE_WEIGHTS}, "veto": False}
    assert evaluate_external_judge(review)["weighted_score_0_100"] == 100
    review["scores"]["factual_integrity"] = 2
    assert not evaluate_external_judge(review)["accepted"]
    review["scores"]["factual_integrity"] = 5
    review["veto"] = True
    assert not evaluate_external_judge(review)["accepted"]

    fixtures = Path(__file__).resolve().parent.parent / "tests" / "sample_responses.json"
    assert len(load_outputs(fixtures)) >= 6
    print("PASS self-test | surface_scores:", values, "| fixture_count:", len(load_outputs(fixtures)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="Response text")
    source.add_argument("--file", type=Path, help="UTF-8 response file")
    source.add_argument("--batch", type=Path, help="Batch responses as JSON array, {outputs:[...]}, or {cases:[...]}")
    parser.add_argument("--level", type=int, choices=range(0, 6), default=3)
    parser.add_argument("--judge-json", type=Path, help="EXTERNALLY generated semantic reviewer JSON")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if sum(x is not None for x in (args.text, args.file, args.batch)) != 1:
        parser.error("Provide exactly one of --text, --file, or --batch")
    try:
        judge = json.loads(args.judge_json.read_text(encoding="utf-8")) if args.judge_json else None
        if args.batch:
            outputs = load_outputs(args.batch)
            results = []
            for i, item in enumerate(outputs):
                lvl = item.get("level", args.level)
                result: dict[str, Any] = {"id": item.get("id", str(i)), **analyze(item["text"], lvl)}
                if "preserve" in item or "input" in item:
                    result["preserve_check"] = check_preserve_retention(
                        item["text"],
                        str(item.get("preserve", "")),
                        str(item.get("input", "")),
                        lvl,
                    )
                if "overrides" in item or "guardrail" in item:
                    result["constraint_check"] = check_case_constraints(
                        item["text"],
                        lvl,
                        str(item.get("input", "")),
                        item.get("overrides"),
                        str(item.get("guardrail", "")),
                    )
                if judge is not None:
                    if not isinstance(judge, dict) or result["id"] not in judge:
                        raise ValueError(f"missing external judge report for batch id {result['id']}")
                    result["external_judge"] = evaluate_external_judge(judge[result["id"]])
                results.append(result)
            out: Any = {
                "count": len(results),
                "cross_sample_diversity": analyze_cross_sample_diversity(outputs),
                "results": results,
            }
        else:
            content = args.text if args.text is not None else args.file.read_text(encoding="utf-8")
            out = analyze(content, args.level)
            if judge is not None:
                out["external_judge"] = evaluate_external_judge(judge)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        parser.error(str(e))
    if args.json or args.batch:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"表面风格分：{out['surface_style_score_0_100']}/100；级别表面标记适配：{out['level_fit_surface_score_0_100']}/100")
        print(f"否定推断标记：{out['defensive_marker_occurrences']}；每百字 {out['markers_per_100_chars']}")
        print("误读维度线索：" + (", ".join(out["misread_axis_hints"]) or "无"))
        print("元防御线索：" + (", ".join(out["meta_validation_hints"]) or "无"))
        if "external_judge" in out:
            print("外部评审加权分：", out["external_judge"]["weighted_score_0_100"])
            print("外部评审建议接受：", out["external_judge"]["accepted"])
        print(out["caveat"])


if __name__ == "__main__":
    main()
