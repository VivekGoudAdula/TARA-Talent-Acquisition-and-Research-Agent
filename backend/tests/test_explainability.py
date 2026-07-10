"""Unit tests for Explainable AI layer."""

import json
import unittest

from app.explainability.prompt_builder import PromptBuilder
from app.explainability.reason_engine import ReasonCodeEngine, ReasonCodeInput
from app.explainability.response_parser import ResponseParser


class ReasonCodeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ReasonCodeEngine()

    def test_generates_multiple_reason_codes(self) -> None:
        codes = self.engine.generate(
            ReasonCodeInput(
                monthly_income=85000,
                emi_burden=18,
                credit_score=760,
                financial_health_score=91,
                digital_engagement_score=95,
                savings_ratio=36,
                repayment_capacity="High",
                repayment_confidence=0.94,
                consent=True,
            )
        )
        self.assertIn("Stable Salary", codes)
        self.assertIn("Low EMI Burden", codes)
        self.assertIn("Excellent Credit Score", codes)
        self.assertIn("Strong Financial Health", codes)
        self.assertIn("High Digital Engagement", codes)
        self.assertIn("High Savings Ratio", codes)

    def test_low_credit_adds_review_code(self) -> None:
        codes = self.engine.generate(
            ReasonCodeInput(
                monthly_income=30000,
                emi_burden=40,
                credit_score=580,
                financial_health_score=55,
                digital_engagement_score=50,
                savings_ratio=5,
                repayment_capacity="Low",
                repayment_confidence=0.4,
                consent=False,
            )
        )
        self.assertIn("Credit Score Needs Review", codes)
        self.assertIn("Consent Not Provided", codes)


class ResponseParserTests(unittest.TestCase):
    def test_parses_valid_json(self) -> None:
        payload = {
            "summary": "Strong profile.",
            "repayment_explanation": "High capacity.",
            "product_explanation": "Personal Loan fits.",
            "conversion_explanation": "High conversion.",
            "confidence_summary": "High confidence.",
            "reason_codes": ["Stable Salary"],
        }
        result = ResponseParser().parse(json.dumps(payload), ["Stable Salary"])
        self.assertEqual(result["summary"], "Strong profile.")
        self.assertEqual(result["reason_codes"], ["Stable Salary"])

    def test_extracts_json_from_markdown_block(self) -> None:
        raw = 'Here is the result:\n{"summary":"OK","repayment_explanation":"R","product_explanation":"P","conversion_explanation":"C","confidence_summary":"H","reason_codes":["A"]}'
        result = ResponseParser().parse(raw, ["A"])
        self.assertEqual(result["summary"], "OK")


class PromptBuilderTests(unittest.TestCase):
    def test_fallback_explanation_structure(self) -> None:
        summary = {
            "customer_name": "Rahul",
            "repayment_capacity": "High",
            "repayment_confidence": 94,
            "recommended_product": "Personal Loan",
            "conversion_probability": 91,
            "top_reason_codes": ["Stable Salary", "Low EMI Burden"],
        }
        result = PromptBuilder().build_fallback(summary)
        self.assertIn("summary", result)
        self.assertIn("repayment_explanation", result)
        self.assertIn("product_explanation", result)
        self.assertIn("conversion_explanation", result)
        self.assertEqual(result["reason_codes"], summary["top_reason_codes"])


if __name__ == "__main__":
    unittest.main()
