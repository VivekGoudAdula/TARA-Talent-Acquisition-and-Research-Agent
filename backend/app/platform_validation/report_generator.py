"""Report generation for platform validation results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from app.platform_validation.check_result import CategorySummary, ValidationCheck


class ReportGenerator:
    """Writes JSON, Markdown, and HTML validation reports."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or Path.cwd()

    @property
    def json_path(self) -> Path:
        return self._output_dir / "validation_report.json"

    @property
    def md_path(self) -> Path:
        return self._output_dir / "validation_report.md"

    @property
    def html_path(self) -> Path:
        return self._output_dir / "validation_report.html"

    def write_all(
        self,
        generated_at: str,
        overall: str,
        system_health: dict[str, str],
        categories: list[CategorySummary],
        all_checks: list[ValidationCheck],
    ) -> dict[str, str]:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": generated_at,
            "overall_health": overall,
            "system_health": system_health,
            "categories": [
                {
                    "category": cat.category,
                    "status": cat.status,
                    "passed": cat.passed,
                    "failed": cat.failed,
                    "warned": cat.warned,
                    "skipped": cat.skipped,
                    "checks": [
                        {
                            "category": c.category,
                            "name": c.name,
                            "status": c.status,
                            "reason": c.reason,
                            "details": c.details,
                        }
                        for c in cat.checks
                    ],
                }
                for cat in categories
            ],
            "total_checks": len(all_checks),
        }
        self.json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.md_path.write_text(
            self._render_markdown(generated_at, overall, system_health, categories),
            encoding="utf-8",
        )
        self.html_path.write_text(
            self._render_html(generated_at, overall, system_health, categories),
            encoding="utf-8",
        )
        return {
            "json": str(self.json_path),
            "markdown": str(self.md_path),
            "html": str(self.html_path),
        }

    def _render_markdown(
        self,
        generated_at: str,
        overall: str,
        system_health: dict[str, str],
        categories: list[CategorySummary],
    ) -> str:
        lines = [
            "# Tara Platform Validation Report",
            "",
            f"**Generated:** {generated_at}",
            f"**Overall Health:** {overall}",
            "",
            "## System Health",
            "",
            "| Component | Status |",
            "|-----------|--------|",
        ]
        for key, value in system_health.items():
            lines.append(f"| {key.replace('_', ' ').title()} | {value} |")

        lines.extend(["", "## Category Details", ""])
        for cat in categories:
            lines.append(f"### {cat.category} — {cat.status}")
            lines.append(
                f"_Passed: {cat.passed}, Failed: {cat.failed}, "
                f"Warnings: {cat.warned}, Skipped: {cat.skipped}_"
            )
            lines.append("")
            for check in cat.checks:
                lines.append(f"- **[{check.status}]** {check.name}: {check.reason}")
            lines.append("")
        return "\n".join(lines)

    def _render_html(
        self,
        generated_at: str,
        overall: str,
        system_health: dict[str, str],
        categories: list[CategorySummary],
    ) -> str:
        health_rows = "".join(
            f"<tr><td>{escape(k.replace('_', ' ').title())}</td>"
            f"<td class='{escape(v.lower())}'>{escape(v)}</td></tr>"
            for k, v in system_health.items()
        )
        category_blocks = []
        for cat in categories:
            check_rows = "".join(
                f"<tr><td>{escape(c.name)}</td><td class='{c.status.lower()}'>{c.status}</td>"
                f"<td>{escape(c.reason)}</td></tr>"
                for c in cat.checks
            )
            category_blocks.append(
                f"""
                <section>
                  <h2>{escape(cat.category)} <span class="{cat.status.lower()}">{cat.status}</span></h2>
                  <p>Passed: {cat.passed} | Failed: {cat.failed} | Warnings: {cat.warned} | Skipped: {cat.skipped}</p>
                  <table>
                    <thead><tr><th>Check</th><th>Status</th><th>Reason</th></tr></thead>
                    <tbody>{check_rows}</tbody>
                  </table>
                </section>
                """
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Tara Platform Validation Report</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 2rem; color: #1a1a1a; }}
    h1 {{ color: #0b3d6b; }}
    .overall {{ font-size: 1.4rem; font-weight: bold; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 2rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.6rem; text-align: left; }}
    th {{ background: #f4f7fb; }}
    .pass, .PASS {{ color: #0a7a2f; font-weight: bold; }}
    .fail, .FAIL {{ color: #b00020; font-weight: bold; }}
    .warn, .WARN {{ color: #9a6b00; font-weight: bold; }}
    .skip, .SKIP {{ color: #666; }}
    section {{ margin-bottom: 2rem; }}
  </style>
</head>
<body>
  <h1>Tara Platform Validation Report</h1>
  <p>Generated: {escape(generated_at)}</p>
  <p class="overall">Overall Health: {escape(overall)}</p>
  <h2>System Health</h2>
  <table>
    <thead><tr><th>Component</th><th>Status</th></tr></thead>
    <tbody>{health_rows}</tbody>
  </table>
  {''.join(category_blocks)}
</body>
</html>"""
