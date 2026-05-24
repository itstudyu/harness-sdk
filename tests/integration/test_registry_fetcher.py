# Stage 2 integration test: PoC local 모드 fetcher (Bitbucket 모드는 mocked git clone 으로 검증)
"""
build-spec.md Section 11.3 의 fetcher 룰:

- local: prefix → 같은 레포 안 path 직접
- import 형식 파싱 (shared@<version>/<path>)
- 확장자 자동 (.yaml 우선)
- version 무시 warning 1회
- bitbucket 모드 git clone 호출 검증 (실제 네트워크 X, monkeypatch)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from registry import (
    FetcherError,
    create_registry,
    parse_import,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_parse_import_valid() -> None:
    ref = parse_import("shared@v1.2.0/rules/Rule_JWT")
    assert ref.version == "v1.2.0"
    assert ref.path == "rules/Rule_JWT"
    assert ref.raw == "shared@v1.2.0/rules/Rule_JWT"


def test_parse_import_invalid_raises() -> None:
    with pytest.raises(FetcherError) as exc:
        parse_import("not-a-shared-import")
    assert "잘못된 import 형식" in exc.value.message


def test_local_registry_resolves_existing_seed_file() -> None:
    """reference/shared/agents/non-isolation/code-analyst.md 는 실제로 존재."""
    reg = create_registry(
        "local:reference/shared",
        project_root=PROJECT_ROOT,
    )
    assert reg.mode == "local"
    ref = parse_import("shared@v0.0.0/agents/non-isolation/code-analyst")
    path = reg.resolve(ref)
    assert path.exists()
    assert path.name == "code-analyst.md"
    # version 무시 warning 1회
    assert any("무시" in w for w in reg.warnings)
    # 같은 registry 로 두 번째 resolve 시 warning 중복 X
    reg.resolve(parse_import("shared@v0.0.0/agents/non-isolation/code-analyst"))
    assert len([w for w in reg.warnings if "무시" in w]) == 1


def test_local_registry_resolves_directory_kind(tmp_path: Path) -> None:
    """planner 처럼 디렉터리 형식 (templates/ 포함) 도 path 로 받을 수 있어야 함."""
    reg = create_registry(
        "local:reference/shared",
        project_root=PROJECT_ROOT,
    )
    ref = parse_import("shared@v0.0.0/agents/non-isolation/planner")
    path = reg.resolve(ref)
    assert path.is_dir()
    assert (path / "SKILL.md").exists()


def test_local_registry_missing_path_errors(tmp_path: Path) -> None:
    reg = create_registry(
        "local:reference/shared",
        project_root=PROJECT_ROOT,
    )
    with pytest.raises(FetcherError) as exc:
        reg.resolve(parse_import("shared@v1.0.0/rules/Rule_DoesNotExist"))
    assert "찾을 수 없음" in exc.value.message


def test_local_registry_nonexistent_root_errors(tmp_path: Path) -> None:
    with pytest.raises(FetcherError) as exc:
        create_registry("local:no/such/dir", project_root=tmp_path)
    assert "없음" in exc.value.message


def test_local_registry_empty_path_errors(tmp_path: Path) -> None:
    with pytest.raises(FetcherError) as exc:
        create_registry("local:", project_root=tmp_path)
    assert "비어있음" in exc.value.message


def test_bitbucket_registry_requires_version(tmp_path: Path) -> None:
    with pytest.raises(FetcherError) as exc:
        create_registry(
            "bitbucket.company.com/harness.git",
            project_root=tmp_path,
            cache_root=tmp_path / "cache",
        )
    assert "version" in exc.value.message


def test_bitbucket_registry_clones_and_uses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """git clone 을 monkeypatch 로 가짜화: 호출 인자 검증 + cache 디렉터리 생성 모사."""
    cache_root = tmp_path / "cache"
    captured: dict = {}

    def fake_run(cmd, check, capture_output, text):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        # 가짜 clone: shared 디렉터리 만들고 sentinel 파일 하나 둠
        dest = Path(cmd[-1])
        shared = dest / "reference" / "shared" / "rules"
        shared.mkdir(parents=True, exist_ok=True)
        (shared / "Rule_Demo.yaml").write_text("id: Rule_Demo\n", encoding="utf-8")

        class _Done:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Done()

    monkeypatch.setattr(subprocess, "run", fake_run)

    reg = create_registry(
        "https://bitbucket.company.com/harness.git",
        project_root=tmp_path,
        cache_root=cache_root,
        requested_version="v1.2.0",
    )
    assert reg.mode == "bitbucket"
    assert "v1.2.0" in str(reg.root)
    # clone 명령 검증
    assert captured["cmd"][:5] == ["git", "clone", "--depth", "1", "--branch"]
    assert captured["cmd"][5] == "v1.2.0"
    # 실제 resolve 동작
    path = reg.resolve(parse_import("shared@v1.2.0/rules/Rule_Demo"))
    assert path.name == "Rule_Demo.yaml"


def test_bitbucket_registry_clone_failure_surfaces_helpful_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd, check, capture_output, text):  # type: ignore[no-untyped-def]
        raise subprocess.CalledProcessError(
            returncode=128, cmd=cmd, stderr="fatal: Authentication failed"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FetcherError) as exc:
        create_registry(
            "https://bitbucket.company.com/harness.git",
            project_root=tmp_path,
            cache_root=tmp_path / "cache",
            requested_version="v1.2.0",
        )
    msg = exc.value.message
    assert "git clone 실패" in msg
    assert "Authentication failed" in msg
    assert "~/.netrc" in msg
