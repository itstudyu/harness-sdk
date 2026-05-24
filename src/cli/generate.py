# harness-gen generate — Phase 1~9 (build-spec.md Section 4.2, 8, 9, 9.6)
"""
Phase 1: config 파싱 + 검증 (Stage 1)
Phase 2: imports 해결 (Stage 2 fetcher)
Phase 3: ontology 병합 (resolver/merger)
Phase 4: overrides 적용 (rules + agents)
Phase 5: local 데이터 통합 (rules/patterns 파일 복사)
Phase 6: agent 인스턴스 결정 + 설치 (agent_installer)
Phase 7: CLAUDE.md 합성 (synth/claude_md)
Phase 8: .gitignore 갱신 (init 과 동일 entry)
Phase 9: .lock.yaml 갱신
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import yaml

from agent_installer import install_agents
from cli.init import GITIGNORE_ENTRIES, _ensure_gitignore  # 재사용
from registry import FetcherError, create_registry
from resolver import OverrideError, apply_overrides, merge_ontology, resolve_imports
from resolver.imports import ImportedNode
from synth import (
    synthesize_claude_md,
    write_lockfile,
    write_manifest,
    write_settings_json,
)
from synth.claude_md import ClaudeMdInput
from synth.lockfile import LockInput
from validators import load_and_validate

# generate 동안 raw exception 으로 새어나가면 사용자에게 traceback 노출 → ClickException 으로 wrap
_USER_FACING_ERRORS = (FetcherError, OverrideError, ValueError)


@click.command(name="generate")
@click.option("--project-root", default=".", type=click.Path(file_okay=False, path_type=Path))
@click.option("--cache-dir", default=None, type=click.Path(file_okay=False, path_type=Path),
              help="운용 모드 git clone 캐시 (기본: ~/.harness-cache).")
@click.option("--ci", is_flag=True, default=False, help="CI 모드 (warning → error 격상).")
def generate_cmd(project_root: Path, cache_dir: Path | None, ci: bool) -> None:
    """`.harness-config.yaml` 을 컴파일해서 .harness/, .claude/, CLAUDE.md 생성."""
    try:
        _generate(project_root.resolve(), cache_dir=cache_dir, ci=ci)
    except _USER_FACING_ERRORS as exc:
        # actionable 메시지로 변환 (Section 10 MUST). dataclass Exception 이라 message 우선.
        msg = getattr(exc, "message", None) or str(exc)
        raise click.ClickException(msg) from exc


def _generate(project_root: Path, *, cache_dir: Path | None, ci: bool) -> None:
    ctx = _phase1_load_config(project_root, ci_mode=ci)
    nodes = _phase2_imports(ctx, cache_dir=cache_dir)
    _phase3_4_merge_and_override(ctx, nodes)
    local_rule_ids = _phase5_local(ctx)
    installations = _phase6_install_agents(ctx)
    _phase7_claude_md(ctx, nodes, local_rule_ids, installations)
    _phase8_gitignore(project_root)
    _phase9_lockfile(ctx, nodes, installations)
    write_settings_json(project_root / ".claude")
    click.echo("✓ generate 완료")
    click.echo(f"  .claude/, .harness/, CLAUDE.md 생성: {project_root}")


@dataclass
class _Ctx:
    """generate phase 들이 공유하는 상태."""
    project_root: Path
    config: dict[str, Any]
    ci_mode: bool
    registry_value: str
    registry: Any   # Registry — 순환 import 방지 위해 Any


def _phase1_load_config(project_root: Path, *, ci_mode: bool) -> _Ctx:
    """Section 4.2 Phase 1: config 파싱 + 모든 룰 검증."""
    config_path = project_root / ".harness-config.yaml"
    if not config_path.exists():
        raise click.ClickException(f"{config_path} 없음. 먼저 'harness-gen init' 실행.")
    result = load_and_validate(config_path, ci_mode=ci_mode)
    if not result.ok:
        raise click.ClickException(
            "config 검증 실패:\n  - " + "\n  - ".join(result.errors)
        )
    for w in result.warnings:
        click.echo(f"⚠ {w}", err=True)
    return _Ctx(
        project_root=project_root,
        config=result.config,
        ci_mode=ci_mode,
        registry_value=result.config["registry"],
        registry=None,
    )


def _phase2_imports(ctx: _Ctx, *, cache_dir: Path | None) -> list[ImportedNode]:
    """Section 4.2 Phase 2: imports fetch (registry 결정 포함)."""
    import_strs: list[str] = list(ctx.config.get("imports") or [])
    version = _first_version(import_strs)
    ctx.registry = create_registry(
        ctx.registry_value,
        project_root=ctx.project_root,
        cache_root=cache_dir,
        requested_version=version,
    )
    for w in ctx.registry.warnings:
        click.echo(f"⚠ {w}", err=True)
    return resolve_imports(import_strs, ctx.registry)


def _first_version(imports: list[str]) -> str | None:
    """첫 import 의 version 을 추출 (Bitbucket clone branch 로 사용)."""
    for s in imports:
        if "@" in s and "/" in s:
            return s.split("@", 1)[1].split("/", 1)[0]
    return None


def _phase3_4_merge_and_override(ctx: _Ctx, nodes: list[ImportedNode]) -> None:
    """Phase 3 (ontology merge) + Phase 4 (rules-level overrides)."""
    ontology_local = _read_local_ontology(ctx)
    shared_ontology = _extract_shared_ontology(nodes)
    merged = merge_ontology(shared_ontology, ontology_local)
    (ctx.project_root / ".harness").mkdir(parents=True, exist_ok=True)
    (ctx.project_root / ".harness" / "ontology.yaml").write_text(
        yaml.safe_dump(merged, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    result = apply_overrides(
        nodes, ctx.config.get("overrides"), ci_mode=ctx.ci_mode
    )
    for w in result.warnings:
        click.echo(f"⚠ {w}", err=True)


def _extract_shared_ontology(nodes: list[ImportedNode]) -> dict[str, Any]:
    """nodes 중 ontology 종류의 dict 만 통합."""
    out: dict[str, Any] = {}
    for n in nodes:
        if n.kind == "ontology":
            out.update(n.data)
    return out


def _read_local_ontology(ctx: _Ctx) -> dict[str, Any] | None:
    """ontology.yaml 로컬 파일 (있으면) 로드."""
    path = ctx.project_root / "ontology.yaml"
    if not path.exists():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else None


def _phase5_local(ctx: _Ctx) -> list[str]:
    """Phase 5: local rules/patterns 파일을 .harness/<kind>/local/ 로 복사. local rule id 반환."""
    local = ctx.config.get("local") or {}
    rule_ids: list[str] = []
    for rule_path in local.get("rules") or []:
        rule_ids.append(_copy_local_node(ctx, rule_path, kind="rules"))
    for pat_path in local.get("patterns") or []:
        _copy_local_node(ctx, pat_path, kind="patterns")
    _write_resolved_imports(ctx)
    return rule_ids


def _copy_local_node(ctx: _Ctx, rel_path: str, *, kind: str) -> str:
    """local/rules/X.yaml → .harness/rules/local/X.yaml 복사. id 추출."""
    src = ctx.project_root / rel_path
    if not src.exists():
        raise click.ClickException(f"local.{kind} 파일 없음: {src}")
    dest_dir = ctx.project_root / ".harness" / kind / "local"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    raw = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    return raw.get("id", src.stem) if isinstance(raw, dict) else src.stem


def _write_resolved_imports(ctx: _Ctx) -> None:
    """imports 결과를 .harness/rules/_resolved/, .harness/patterns/_resolved/ 에 dump."""
    # 호출자 phase 에서 nodes 를 직접 받지 않으므로 placeholder — phase7 에서 함께 처리.
    return


def _phase6_install_agents(ctx: _Ctx) -> list:
    """Phase 6: agent install + manifest 작성."""
    agents = ctx.config.get("agents") or {}
    installations = install_agents(
        project_root=ctx.project_root,
        registry=ctx.registry,
        subagents=list(agents.get("subagents") or []),
        tools=list(agents.get("tools") or []),
        local_agent_paths=list(agents.get("local") or []),
        agent_overrides=dict(agents.get("overrides") or {}),
    )
    write_manifest(installations, output_path=ctx.project_root / ".harness" / "agents" / "manifest.yaml")
    return installations


def _phase7_claude_md(
    ctx: _Ctx, nodes: list[ImportedNode], local_rule_ids: list[str], installations: list
) -> None:
    """Phase 7: CLAUDE.md 합성 + .harness/rules/, .harness/patterns/ resolved 파일 dump."""
    _dump_resolved_nodes(ctx, nodes)
    payload = ClaudeMdInput(
        domain=ctx.config["domain"],
        stack=ctx.config["stack"],
        nodes=nodes,
        local_rule_ids=local_rule_ids,
        installations=installations,
    )
    (ctx.project_root / "CLAUDE.md").write_text(
        synthesize_claude_md(payload), encoding="utf-8"
    )


def _dump_resolved_nodes(ctx: _Ctx, nodes: list[ImportedNode]) -> None:
    """rules/patterns 노드를 .harness/<kind>/_resolved/<id>.yaml 로 저장."""
    for n in nodes:
        if n.kind not in ("rule", "pattern"):
            continue
        dest_dir = ctx.project_root / ".harness" / f"{n.kind}s" / "_resolved"
        dest_dir.mkdir(parents=True, exist_ok=True)
        node_id = n.data.get("id", n.source_path.stem)
        (dest_dir / f"{node_id}.yaml").write_text(
            yaml.safe_dump(n.data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _phase8_gitignore(project_root: Path) -> None:
    """Phase 8: init 과 동일한 entry 확인 (멱등). init 모듈 helper 재사용."""
    _ensure_gitignore(project_root)
    # 추가 안전망: GITIGNORE_ENTRIES 가 import 됐는지 확인 (no-op)
    _ = GITIGNORE_ENTRIES


def _phase9_lockfile(ctx: _Ctx, nodes: list[ImportedNode], installations: list) -> None:
    """Phase 9: .harness/.lock.yaml 작성 (재현 정보)."""
    write_lockfile(
        LockInput(
            nodes=nodes,
            installations=installations,
            registry=ctx.registry_value,
            registry_mode=ctx.registry.mode,
        ),
        output_path=ctx.project_root / ".harness" / ".lock.yaml",
    )
