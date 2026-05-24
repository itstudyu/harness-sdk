# build-spec.md Section 8 Step 1: imports 수집 — registry 에서 각 path 를 read 후 dict 로
"""
입력: .harness-config.yaml 의 imports (list[str], 형식 'shared@<version>/<path>')
출력: ImportedNode list (raw + parsed dict + source path)

ontology.yaml 같이 path 가 ontology 면 dict 전체, rules/patterns 면 노드 1개.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from registry import ImportRef, Registry, parse_import


@dataclass
class ImportedNode:
    """resolve 된 import 하나. raw import 문자열 + 실제 파일 + 파싱된 dict."""
    ref: ImportRef
    source_path: Path
    data: dict[str, Any]
    kind: str   # "ontology" | "rule" | "pattern" | "unknown"


def resolve_imports(import_strs: list[str], registry: Registry) -> list[ImportedNode]:
    """import 문자열 각각을 fetch + parse. 실패 시 즉시 raise."""
    return [_resolve_one(s, registry) for s in import_strs]


def _resolve_one(import_str: str, registry: Registry) -> ImportedNode:
    ref = parse_import(import_str)
    path = registry.resolve(ref)
    if path.is_dir():
        # 디렉터리 형식 import 는 ontology.yaml 같은 케이스가 아니라 잘못된 사용
        raise ValueError(
            f"imports 에 디렉터리 경로 금지 ({import_str}). 단일 파일만 허용."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: yaml 최상위는 map 이어야 함 (실제: {type(raw).__name__})")
    return ImportedNode(ref=ref, source_path=path, data=raw, kind=_infer_kind(ref.path))


def _infer_kind(path: str) -> str:
    """import path 의 첫 segment 로 노드 종류 추론. 명세 Section 3.1 의 Rule/Pattern + ontology."""
    head = path.split("/", 1)[0]
    if head == "ontology" or path.endswith("ontology.yaml") or path == "ontology":
        return "ontology"
    if head == "rules":
        return "rule"
    if head == "patterns":
        return "pattern"
    return "unknown"
