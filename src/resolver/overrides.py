# build-spec.md Section 8 Step 3 + Section 9.6.5: overrides 적용 (rules + agents 양쪽)
"""
rules-level overrides: imports 한 rule 노드의 필드 부분 교체 (approved_by 필수).
agents-level overrides: agent 정의의 custom 필드 + skills append 처리 (.harness/agents/manifest.yaml 에 들어감).

approved_by 누락 정책: ci_mode=True → 에러, False → warning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from resolver.imports import ImportedNode

# overrides 메타 필드 (실제 노드/agent 에 들어가면 안 됨)
META_KEYS: frozenset[str] = frozenset(
    {"approved_by", "approved_at", "justification"}
)


@dataclass
class OverrideError(Exception):
    """overrides 적용 실패."""
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


@dataclass
class OverrideResult:
    nodes: list[ImportedNode]
    warnings: list[str] = field(default_factory=list)


def apply_overrides(
    nodes: list[ImportedNode],
    overrides: dict[str, dict[str, Any]] | None,
    *,
    ci_mode: bool = False,
) -> OverrideResult:
    """rules-level overrides 만 처리 (key 가 imports 노드의 id 와 매칭).

    agents-level overrides 는 agent_installer 에서 별도 처리.
    """
    if not overrides:
        return OverrideResult(nodes=nodes)
    by_id = _index_by_id(nodes)
    warnings: list[str] = []
    for key, patch in overrides.items():
        if key not in by_id:
            raise OverrideError(
                f"overrides.{key}: 매칭되는 import 노드 없음 (imports 에 추가 후 재시도)"
            )
        _check_approval(key, patch, ci_mode=ci_mode, warnings=warnings)
        _apply_patch(by_id[key].data, patch)
    return OverrideResult(nodes=nodes, warnings=warnings)


def _index_by_id(nodes: list[ImportedNode]) -> dict[str, ImportedNode]:
    """노드의 'id' 필드로 lookup table. id 누락 노드는 매칭 대상에서 제외 (ontology 등)."""
    out: dict[str, ImportedNode] = {}
    for n in nodes:
        node_id = n.data.get("id") if isinstance(n.data, dict) else None
        if isinstance(node_id, str):
            out[node_id] = n
    return out


def _check_approval(
    key: str, patch: dict[str, Any], *, ci_mode: bool, warnings: list[str]
) -> None:
    approved_by = patch.get("approved_by")
    if approved_by and isinstance(approved_by, str):
        return
    msg = f"overrides.{key}.approved_by 누락 (사람의 명시적 승인 필요)"
    if ci_mode:
        raise OverrideError(msg)
    warnings.append(msg)


def _apply_patch(target: dict[str, Any], patch: dict[str, Any]) -> None:
    """patch 의 메타 필드 제외하고 target 에 키 단위로 덮어쓰기."""
    for k, v in patch.items():
        if k in META_KEYS:
            continue
        target[k] = v
