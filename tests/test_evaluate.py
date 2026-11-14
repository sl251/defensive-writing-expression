"""Deterministic v3.3 evaluator regression checks (no model calls)."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import evaluate


ROOT = Path(__file__).resolve().parent.parent


class CatalogTests(unittest.TestCase):
    def test_catalog_has_64_cases_with_expected_scene_coverage(self):
        report = evaluate.catalog_summary(ROOT / "tests" / "cases.json")
        self.assertEqual(report["catalog_cases"], 64)
        self.assertEqual(report["scenario_counts"]["legacy-short-rewrite"], 22)
        self.assertEqual(report["scenario_counts"]["real-answer"], 12)
        self.assertEqual(report["scenario_counts"]["persona-continuity"], 12)
        self.assertEqual(report["scenario_counts"]["multi-turn"], 8)
        self.assertEqual(report["scenario_counts"]["edge-boundary"], 10)
        self.assertGreaterEqual(report["conversation_turns_defined"], 24)
        self.assertFalse(report["semantic_scores_computed"])

    def test_role_samples_are_diverse_and_original_regressions_are_limited(self):
        data = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        original_role_cases = [
            item for item in cases
            if "猫娘" in json.dumps(item, ensure_ascii=False)
            or "cat-" in item["id"]
        ]
        self.assertEqual(
            {x["id"] for x in original_role_cases},
            {"persona-cat-script", "multi-cat-follow"},
        )
        personas = [c for c in cases if c.get("scene") == "persona-continuity"]
        from collections import Counter
        voice_counts = Counter(c["voice"] for c in personas)
        self.assertGreaterEqual(len(voice_counts), 8)
        self.assertLessEqual(max(voice_counts.values()), 2)
        for case in personas:
            self.assertGreaterEqual(len(case.get("voice_traits", [])), 2)
        for case in [c for c in cases if c.get("scene") == "multi-turn"]:
            self.assertGreaterEqual(len(case.get("voice_traits", [])), 2)

    def test_core_guidance_has_no_single_character_dependency(self):
        for rel in (
            "SKILL.md",
            "references/patterns.md",
            "references/examples.md",
            "references/judge-rubric.md",
            "README.md",
        ):
            source = (ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(source=rel):
                self.assertNotIn("猫娘", source)
                self.assertNotIn("喵", source)

    def test_catalog_rejects_duplicate_id(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dups.json"
            p.write_text(json.dumps({"cases": [
                {"id": "duplicate", "input": "A"},
                {"id": "duplicate", "input": "B"},
            ]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                evaluate.catalog_summary(p)


class ConversationTests(unittest.TestCase):
    def test_unfilled_turns_are_not_treated_as_passed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "multi.json"
            p.write_text(json.dumps({"cases": [{
                "id": "demo", "mode": "Respond", "scene": "multi-turn",
                "voice": "温和图书管理员", "level": 5,
                "turns": [
                    {"user": "解释借书规则", "response": "这类规则需要以具体馆方公示为准。"},
                    {"user": "那有什么局限？"},
                    {"user": "不要防御性", "level": 0, "response": "好的，正常解释。"},
                ],
            }]}), encoding="utf-8")
            items = evaluate.load_outputs(p)
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]["id"], "demo#turn1")
            self.assertEqual(items[1]["id"], "demo#turn3")
            self.assertEqual(items[1]["level"], 0)
            self.assertEqual(items[0]["conversation_id"], "demo")
            self.assertEqual(items[0]["voice"], "温和图书管理员")

    def test_literal_scene_checks_do_not_claim_semantic_quality(self):
        ok = evaluate.check_scene_constraints("先说清楚适用范围。", {"checks": {
            "must_contain_all": ["范围"],
            "must_contain_any": ["先说清楚", "具体来说"],
            "must_not_contain": ["测试全部通过"],
        }})
        self.assertTrue(ok["passed"])
        self.assertEqual(ok["scope"], "literal assertions only")
        bad = evaluate.check_scene_constraints("测试全部通过", {"checks": {
            "must_not_contain": ["测试全部通过"]
        }})
        self.assertFalse(bad["passed"])


class JudgeTests(unittest.TestCase):
    def test_legacy_judge_remains_compatible(self):
        review = {"scores": {k: 5 for k in evaluate.JUDGE_WEIGHTS}}
        result = evaluate.evaluate_external_judge(review)
        self.assertEqual(result["rubric"], "legacy-rewrite")
        self.assertTrue(result["accepted"])

    def test_context_judge_requires_task_and_persona(self):
        review = {"rubric": "context-v3.3",
                  "scores": {k: 5 for k in evaluate.CONTEXT_JUDGE_WEIGHTS}}
        self.assertTrue(evaluate.evaluate_external_judge(review)["accepted"])
        review["scores"]["persona_continuity"] = 2
        self.assertFalse(evaluate.evaluate_external_judge(review)["accepted"])
        review["scores"]["persona_continuity"] = 5
        review["scores"]["task_completion"] = 1
        self.assertFalse(evaluate.evaluate_external_judge(review)["accepted"])

    def test_invalid_judge_rubric_fails(self):
        with self.assertRaises(ValueError):
            evaluate.evaluate_external_judge({
                "rubric": "unknown", "scores": {k: 5 for k in evaluate.JUDGE_WEIGHTS}
            })


if __name__ == "__main__":
    unittest.main()
