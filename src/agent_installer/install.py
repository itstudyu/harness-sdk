# build-spec.md Section 9.6 install — shared/ agent/skill 을 .claude/ 로 변환 설치
"""
변환 룰 (Section 9.6.4):
- agents/isolation/<X>.md            → .claude/agents/<X>.md           (Subagent)
- agents/non-isolation/<X>.md        → .claude/skills/<X>/SKILL.md     (Skill)
- agents/non-isolation/<X>/SKILL.md  → .claude/skills/<X>/SKILL.md     (Skill, 폴더 형식)
- agents/non-isolation/<X>/<dir>/    → .claude/skills/<X>/<dir>/       (Skill 부속, 예: templates)
- skills/<X>/SKILL.md                → .claude/skills/<X>/SKILL.md     (의존 skill 자동)

planner 는 항상 설치 (사용자 선택 불가).

frontmatter 의 `skills:` 의존성 자동 해결 — registry 의 skills/<X>/SKILL.md 로 fetch 시도.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from registry import FetcherError, Registry

PLANNER_NAME = "planner"

# Subagent: agents/isolation/<X>.md, Skill: agents/non-isolation/<X>(.md|/SKILL.md), Dep skill: skills/<X>/SKILL.md
SOURCE_KIND_RE = re.compile(r"^(agents/isolation|agents/non-isolation|skills)/")


@dataclass
class AgentInstallation:
    """설치된 agent 1개의 메타 (manifest.yaml 에 들어갈 entry)."""
    name: str
    install_kind: str        # "subagent" | "skill"
    source: str              # shared/ 내 상대 경로
    location: str            # 프로젝트 내 install 경로 (.claude/...)
    description: str = ""
    tools: list[str] = field(default_factory=list)
    skills_preloaded: list[str] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)
    always_installed: bool = False


def install_agents(
    *,
    project_root: Path,
    registry: Registry,
    subagents: list[str],
    tools: list[str],
    local_agent_paths: list[str],
    agent_overrides: dict[str, dict[str, Any]],
    local_skill_paths: list[str] | None = None,
) -> list[AgentInstallation]:
    """모든 agent 를 변환 + 설치 + 의존 skill 까지. planner 는 항상 포함."""
    claude_dir = project_root / ".claude"
    installations: list[AgentInstallation] = []
    seen_names: set[str] = set()
    installations.append(_install_planner(registry, claude_dir=claude_dir))
    seen_names.add(PLANNER_NAME)
    _install_requested(
        installations, seen_names, registry,
        project_root=project_root, claude_dir=claude_dir,
        subagents=subagents, tools=tools,
        local_agent_paths=local_agent_paths,
        local_skill_paths=local_skill_paths or [],
    )
    _apply_agent_overrides(installations, agent_overrides)
    _resolve_dependent_skills(installations, registry, claude_dir, seen_names)
    return installations


def _install_requested(
    installations: list[AgentInstallation],
    seen_names: set[str],
    registry: Registry,
    *, project_root: Path, claude_dir: Path,
    subagents: list[str], tools: list[str],
    local_agent_paths: list[str], local_skill_paths: list[str],
) -> None:
    """planner 외 명시적으로 요청된 모든 agent/skill 을 설치."""
    for name in subagents:
        installations.append(_resolve_subagent(
            name, registry, project_root=project_root,
            claude_dir=claude_dir, local_agent_paths=local_agent_paths))
        seen_names.add(name)
    for name in tools:
        installations.append(_install_named(
            name, registry, claude_dir=claude_dir, want_isolation=False))
        seen_names.add(name)
    _install_local_artifacts(
        installations, seen_names, project_root=project_root, claude_dir=claude_dir,
        local_agent_paths=local_agent_paths, local_skill_paths=local_skill_paths)


def _install_local_artifacts(
    installations: list[AgentInstallation],
    seen_names: set[str],
    *, project_root: Path, claude_dir: Path,
    local_agent_paths: list[str], local_skill_paths: list[str],
) -> None:
    """agents.local + local.skills 를 순차 설치 (중복 차단)."""
    for local_path in local_agent_paths:
        if _local_already_installed(local_path, installations):
            continue
        installations.append(_install_local(
            local_path, project_root=project_root, claude_dir=claude_dir))
        seen_names.add(Path(local_path).stem)
    for local_skill in local_skill_paths:
        installations.append(_install_local_skill(
            local_skill, project_root=project_root, claude_dir=claude_dir))
        seen_names.add(Path(local_skill).name)


def _resolve_subagent(
    name: str, registry: Registry, *, project_root: Path, claude_dir: Path,
    local_agent_paths: list[str],
) -> AgentInstallation:
    """subagent 이름 → shared isolation 우선, 없으면 agents.local 에서 fallback (HIGH 2)."""
    iso_path = registry.root / "agents" / "isolation" / f"{name}.md"
    if iso_path.exists():
        return _install_named(name, registry, claude_dir=claude_dir, want_isolation=True)
    for lp in local_agent_paths:
        candidate = (project_root / lp).resolve()
        if candidate.exists() and candidate.stem == name:
            return _install_local(lp, project_root=project_root, claude_dir=claude_dir)
    raise FetcherError(
        f"agent '{name}' 정의 없음. shared/agents/isolation/{name}.md 또는 "
        f"agents.local 에 등록된 파일 중 stem={name} 확인."
    )


def _local_already_installed(local_path: str, installations: list[AgentInstallation]) -> bool:
    """동일 source 가 이미 설치됐는지 (subagents fallback 으로 이미 들어왔을 수 있음)."""
    return any(inst.source == local_path for inst in installations)


def _install_local_skill(
    local_path: str, *, project_root: Path, claude_dir: Path
) -> AgentInstallation:
    """프로젝트 내 local/skills/<X>/ → .claude/skills/<X>/ (SKILL.md 포함 폴더 통째 복사)."""
    src_dir = (project_root / local_path).resolve()
    if not src_dir.is_dir():
        raise FetcherError(f"local.skills 디렉터리 없음: {src_dir}")
    skill_md = src_dir / "SKILL.md"
    if not skill_md.exists():
        raise FetcherError(f"local skill 에 SKILL.md 없음: {skill_md}")
    name = src_dir.name
    dest_dir = claude_dir / "skills" / name
    _copy_skill_unit(src_dir, dest_dir)
    front = _read_frontmatter(dest_dir / "SKILL.md")
    return AgentInstallation(
        name=name,
        install_kind="skill",
        source=local_path,
        location=str((dest_dir / "SKILL.md").relative_to(claude_dir.parent)),
        description=front.get("description", ""),
        tools=list(front.get("tools") or []),
    )


def _install_planner(registry: Registry, *, claude_dir: Path) -> AgentInstallation:
    """planner 는 폴더 형식 (SKILL.md + templates/) 통째로 복사."""
    src = registry.root / "agents" / "non-isolation" / "planner"
    if not src.is_dir():
        raise FetcherError(
            f"planner skill 정의 디렉터리 없음: {src} (registry seed 확인)"
        )
    dest = claude_dir / "skills" / PLANNER_NAME
    _copy_skill_folder(src, dest)
    front = _read_frontmatter(dest / "SKILL.md")
    return AgentInstallation(
        name=PLANNER_NAME,
        install_kind="skill",
        source="agents/non-isolation/planner/",
        location=str((dest / "SKILL.md").relative_to(claude_dir.parent)),
        description=front.get("description", ""),
        always_installed=True,
    )


def _install_named(
    name: str, registry: Registry, *, claude_dir: Path, want_isolation: bool
) -> AgentInstallation:
    """isolation/non-isolation 한쪽에서 찾아 설치."""
    src, source_rel, install_kind = _find_agent_source(name, registry, want_isolation=want_isolation)
    if install_kind == "subagent":
        dest = claude_dir / "agents" / f"{name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    else:
        dest_dir = claude_dir / "skills" / name
        _copy_skill_unit(src, dest_dir)
        dest = dest_dir / "SKILL.md"
    front = _read_frontmatter(dest)
    return AgentInstallation(
        name=name,
        install_kind=install_kind,
        source=source_rel,
        location=str(dest.relative_to(claude_dir.parent)),
        description=front.get("description", ""),
        tools=list(front.get("tools") or []),
        skills_preloaded=list(front.get("skills") or []),
    )


def _find_agent_source(
    name: str, registry: Registry, *, want_isolation: bool
) -> tuple[Path, str, str]:
    """isolation/non-isolation 중 하나에서 찾기 — 못 찾으면 다른 쪽 fallback 후 에러."""
    iso_path = registry.root / "agents" / "isolation" / f"{name}.md"
    non_iso_file = registry.root / "agents" / "non-isolation" / f"{name}.md"
    non_iso_dir = registry.root / "agents" / "non-isolation" / name
    if want_isolation and iso_path.exists():
        return iso_path, f"agents/isolation/{name}.md", "subagent"
    if not want_isolation and non_iso_file.exists():
        return non_iso_file, f"agents/non-isolation/{name}.md", "skill"
    if not want_isolation and non_iso_dir.is_dir():
        return non_iso_dir, f"agents/non-isolation/{name}/", "skill"
    raise FetcherError(
        f"agent '{name}' 정의 없음 (want_isolation={want_isolation}). "
        f"registry seed 또는 .harness-config.yaml 의 agents.local 확인."
    )


def _install_local(
    local_path: str, *, project_root: Path, claude_dir: Path
) -> AgentInstallation:
    """프로젝트 내 local/agents/<X>.md → .claude/agents/<X>.md (subagent 만 지원, PoC)."""
    src = project_root / local_path
    if not src.exists():
        raise FetcherError(f"agents.local 파일 없음: {src}")
    name = src.stem
    dest = claude_dir / "agents" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    front = _read_frontmatter(dest)
    return AgentInstallation(
        name=name,
        install_kind="subagent",
        source=local_path,
        location=str(dest.relative_to(claude_dir.parent)),
        description=front.get("description", ""),
        tools=list(front.get("tools") or []),
        skills_preloaded=list(front.get("skills") or []),
    )


def _resolve_dependent_skills(
    installations: list[AgentInstallation],
    registry: Registry,
    claude_dir: Path,
    seen_names: set[str],
) -> None:
    """subagent frontmatter 의 skills: 의존성 → registry/skills/<X>/SKILL.md 설치."""
    pending: list[str] = []
    for inst in list(installations):
        for skill in inst.skills_preloaded:
            if skill in seen_names:
                continue
            pending.append(skill)
            seen_names.add(skill)
    for skill_name in pending:
        installations.append(_install_dep_skill(skill_name, registry, claude_dir))


def _install_dep_skill(
    name: str, registry: Registry, claude_dir: Path
) -> AgentInstallation:
    src = registry.root / "skills" / name / "SKILL.md"
    if not src.exists():
        raise FetcherError(
            f"의존 skill '{name}' 정의 없음: {src} (registry seed 확인)"
        )
    dest_dir = claude_dir / "skills" / name
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / "SKILL.md")
    front = _read_frontmatter(dest_dir / "SKILL.md")
    return AgentInstallation(
        name=name,
        install_kind="skill",
        source=f"skills/{name}/SKILL.md",
        location=str((dest_dir / "SKILL.md").relative_to(claude_dir.parent)),
        description=front.get("description", ""),
    )


def _apply_agent_overrides(
    installations: list[AgentInstallation],
    overrides: dict[str, dict[str, Any]],
) -> None:
    """agents.overrides 의 자유 필드 → installation.custom 에 적재 (meta 키 제외).

    skills: 키는 append (build-spec.md Section 9.6.5).
    """
    if not overrides:
        return
    by_name = {i.name: i for i in installations}
    for name, patch in overrides.items():
        target = by_name.get(name)
        if target is None:
            raise FetcherError(
                f"agents.overrides.{name}: 매칭되는 설치된 agent 없음."
            )
        for k, v in patch.items():
            if k in ("approved_by", "approved_at", "justification"):
                continue
            if k == "skills" and isinstance(v, list):
                for s in v:
                    if s not in target.skills_preloaded:
                        target.skills_preloaded.append(s)
                continue
            target.custom[k] = v


def _copy_skill_folder(src: Path, dest: Path) -> None:
    """폴더 형식 skill (planner) 통째 복사."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _copy_skill_unit(src: Path, dest_dir: Path) -> None:
    """단일 파일 또는 디렉터리 skill 을 .claude/skills/<X>/ 아래로."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dest_dir / "SKILL.md")
        return
    # 디렉터리: 통째 복사 (SKILL.md + templates 등)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(src, dest_dir)


# frontmatter (--- ... ---) 추출용
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _read_frontmatter(path: Path) -> dict[str, Any]:
    """agent/skill 정의 파일의 yaml frontmatter 만 dict 로 반환."""
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    raw = yaml.safe_load(m.group(1)) or {}
    return raw if isinstance(raw, dict) else {}
