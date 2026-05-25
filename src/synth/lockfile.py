# build-spec.md Section 8 Step 6: .harness/.lock.yaml — imports + agents commit hash 기록 (재현용)
"""
PoC (local: 모드) 에선 git 정보 없으므로 imports 의 raw 문자열만 기록.
운용 모드: 추후 fetcher 가 노출하는 commit hash 를 받아 기록 (Stage 2 에서 캐시 commit hash 노출은 미구현 — 향후 보강).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agent_installer import AgentInstallation
from resolver.imports import ImportedNode

LOCK_VERSION = "1.0"
GENERATED_BY = "harness-gen v0.1.0"


@dataclass
class LockInput:
    nodes: list[ImportedNode]
    installations: list[AgentInstallation]
    registry: str
    registry_mode: str   # "local" | "bitbucket"
    registry_commit: str | None = None  # bitbucket clone 후 HEAD hash (재현성, Section 11.3)


def write_lockfile(
    payload: LockInput, *, output_path: Path, now: datetime | None = None
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(_build(payload, now or datetime.now(timezone.utc)),
                       sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _build(payload: LockInput, now: datetime) -> dict[str, Any]:
    return {
        "version": LOCK_VERSION,
        "generated_at": now.isoformat(),
        "generated_by": GENERATED_BY,
        "registry": payload.registry,
        "registry_mode": payload.registry_mode,
        "registry_commit": payload.registry_commit,
        "imports": [_import_entry(n, payload.registry_commit) for n in payload.nodes],
        "agents": [_agent_entry(i) for i in payload.installations],
    }


def _import_entry(n: ImportedNode, commit: str | None) -> dict[str, Any]:
    return {
        "raw": n.ref.raw,
        "version": n.ref.version,
        "path": n.ref.path,
        "kind": n.kind,
        "id": n.data.get("id") if isinstance(n.data, dict) else None,
        "commit": commit,
    }


def _agent_entry(i: AgentInstallation) -> dict[str, Any]:
    return {
        "name": i.name,
        "install_kind": i.install_kind,
        "source": i.source,
    }
