# build-spec.md Section 9: CLAUDE.md 합성 (≤100줄, Karpathy 원칙)
"""
프로젝트 루트에 생성. Claude Code 가 자동 로드 + SessionStart 훅이 보강.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agent_installer import AgentInstallation
from resolver.imports import ImportedNode

MAX_LINES = 100
TOOL_VERSION = "0.1.0"


@dataclass
class ClaudeMdInput:
    domain: str
    stack: str
    nodes: list[ImportedNode]
    local_rule_ids: list[str]
    installations: list[AgentInstallation]
    notes: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []


def synthesize_claude_md(payload: ClaudeMdInput) -> str:
    """프로젝트 루트 CLAUDE.md 한 문자열 생성. 100줄 초과 시 ValueError."""
    sections = [
        _header(payload),
        _rules_section(payload),
        _patterns_section(payload),
        _agents_section(payload),
        _notes_section(payload),
        _detail_pointer_section(),
    ]
    text = "\n".join(s for s in sections if s).rstrip() + "\n"
    line_count = text.count("\n")
    if line_count > MAX_LINES:
        raise ValueError(
            f"CLAUDE.md {line_count}줄 — {MAX_LINES} 초과. rules/patterns/agents 그룹 분할 필요."
        )
    return text


def _header(p: ClaudeMdInput) -> str:
    return (
        "# Project Context\n\n"
        f"**Domain**: {p.domain}\n"
        f"**Stack**: {p.stack}\n"
        f"**Generated**: {_today()} (by harness-gen v{TOOL_VERSION})\n"
    )


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _rules_section(p: ClaudeMdInput) -> str:
    rules = [n for n in p.nodes if n.kind == "rule"]
    if not rules and not p.local_rule_ids:
        return ""
    lines = ["## Applied Rules", ""]
    for n in rules:
        lines.append(_rule_line(n.data))
    for lid in p.local_rule_ids:
        lines.append(f"- **{lid}** (local)")
    lines.append("")
    return "\n".join(lines)


def _rule_line(data: dict[str, Any]) -> str:
    rid = data.get("id", "<unknown>")
    sev = data.get("severity", "")
    desc = data.get("description", "")
    sev_part = f" ({sev})" if sev else ""
    return f"- **{rid}**{sev_part}: {desc}"


def _patterns_section(p: ClaudeMdInput) -> str:
    pats = [n for n in p.nodes if n.kind == "pattern"]
    if not pats:
        return ""
    lines = ["## Available Patterns", ""]
    for n in pats:
        pid = n.data.get("id", "<unknown>")
        impl = n.data.get("implements", "")
        lines.append(f"- `{pid}` → {impl}")
    lines.append("")
    return "\n".join(lines)


def _agents_section(p: ClaudeMdInput) -> str:
    if not p.installations:
        return ""
    lines = ["## Installed Agents", ""]
    for inst in p.installations:
        marker = "always" if inst.always_installed else inst.install_kind
        desc = inst.description.split(".")[0].strip()
        lines.append(f"- **{inst.name}** ({marker}): {desc}")
    lines.append("")
    lines.append("→ planner 가 작업 요청 시 `.harness/plan/{yyyymmdd-작업명}/` 에 plan 작성")
    lines.append("")
    return "\n".join(lines)


def _notes_section(p: ClaudeMdInput) -> str:
    if not p.notes:
        return ""
    lines = ["## Project Notes", ""]
    for note in p.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def _detail_pointer_section() -> str:
    return (
        "## 상세 컨텍스트 (필요 시 참조)\n\n"
        "- 룰 전체 정의: `.harness/rules/`\n"
        "- 패턴 코드 조각: `.harness/patterns/`\n"
        "- 의미 정의: `.harness/ontology.yaml`\n"
        "- agent 상세 메타: `.harness/agents/manifest.yaml`\n"
        "- 작업 plan 히스토리: `.harness/plan/` (로컬만)\n"
        "- 정확한 버전 정보: `.harness/.lock.yaml`\n"
    )
