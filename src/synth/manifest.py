# build-spec.md Section 9.6.6: .harness/agents/manifest.yaml — 설치된 agent 의 상세 메타
"""
planner skill 이 참조 (어떤 agent 가 있는지, frontmatter 정보, custom 필드 등).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agent_installer import AgentInstallation

MANIFEST_VERSION = "1.0"
GENERATED_BY = "harness-gen v0.1.0"


def write_manifest(
    installations: list[AgentInstallation],
    *,
    output_path: Path,
    now: datetime | None = None,
) -> None:
    """manifest.yaml 작성. now 인자로 테스트에서 시각 fix 가능."""
    payload = _build_payload(installations, now=now or datetime.now(timezone.utc))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _build_payload(
    installations: list[AgentInstallation], *, now: datetime
) -> dict[str, Any]:
    return {
        "version": MANIFEST_VERSION,
        "generated_at": now.isoformat(),
        "generated_by": GENERATED_BY,
        "agents": {i.name: _entry(i) for i in installations},
    }


def _entry(i: AgentInstallation) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "install_kind": i.install_kind,
        "source": i.source,
        "location": i.location,
        "description": i.description,
    }
    if i.always_installed:
        entry["always_installed"] = True
    if i.tools:
        entry["tools"] = i.tools
    if i.skills_preloaded:
        entry["skills_preloaded"] = i.skills_preloaded
    if i.custom:
        entry["custom"] = i.custom
    return entry
