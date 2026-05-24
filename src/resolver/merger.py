# build-spec.md Section 8 Step 2: ontology 병합 (공유 + local) — local 우선
"""
ontology 노드는 단일 dict. 충돌 시 local 우선 (Section 8 Step 2).
"""
from __future__ import annotations

from typing import Any


def merge_ontology(
    shared: dict[str, Any] | None,
    local: dict[str, Any] | None,
) -> dict[str, Any]:
    """shared + local 을 얕은 머지. local 의 같은 key 가 shared 를 덮어씀.

    node_types 같은 dict-of-dict 도 한 레벨 deep merge.
    """
    base: dict[str, Any] = dict(shared or {})
    if not local:
        return base
    for key, value in local.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base
