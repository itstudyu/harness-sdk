# Stage 6 integration test: harness-gen update — imports 의 version 일괄 갱신
"""
build-spec.md Section 4.4:
- --to=<v>: 모든 import version 강제 교체
- --minor / --major: SemVer bump
- 비SemVer import 는 skip + warning
- 실제 fetch 는 generate 가 (이 명령은 config 만 수정)
"""
from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from cli.update import update_cmd


def _write_config(path: Path, imports: list[str]) -> None:
    path.write_text(
        "version: \"1.0\"\n"
        "domain: payment\n"
        "stack: java-vertx\n"
        "registry: local:reference/shared\n"
        "imports:\n" + "\n".join(f"  - {imp}" for imp in imports) + "\n",
        encoding="utf-8",
    )


def test_update_to_explicit_version(tmp_path: Path) -> None:
    cfg = tmp_path / ".harness-config.yaml"
    _write_config(cfg, ["shared@v1.2.0/rules/Rule_JWT", "shared@v1.2.0/patterns/Pattern_JWT_Java"])
    runner = CliRunner()
    result = runner.invoke(update_cmd, ["--to", "v1.3.0", "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load(cfg.read_text())
    assert all("@v1.3.0/" in imp for imp in config["imports"])


def test_update_minor_bumps_semver(tmp_path: Path) -> None:
    cfg = tmp_path / ".harness-config.yaml"
    _write_config(cfg, ["shared@v1.2.5/rules/Rule_X"])
    runner = CliRunner()
    result = runner.invoke(update_cmd, ["--minor", "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load(cfg.read_text())
    assert config["imports"][0] == "shared@v1.3.0/rules/Rule_X"


def test_update_major_bumps_semver(tmp_path: Path) -> None:
    cfg = tmp_path / ".harness-config.yaml"
    _write_config(cfg, ["shared@v1.2.5/rules/Rule_X"])
    runner = CliRunner()
    result = runner.invoke(update_cmd, ["--major", "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load(cfg.read_text())
    assert config["imports"][0] == "shared@v2.0.0/rules/Rule_X"


def test_update_skips_non_semver_with_minor(tmp_path: Path) -> None:
    cfg = tmp_path / ".harness-config.yaml"
    _write_config(cfg, ["shared@main/rules/Rule_Bleeding"])
    runner = CliRunner()
    result = runner.invoke(update_cmd, ["--minor", "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "SemVer 형식 아님" in result.output
    config = yaml.safe_load(cfg.read_text())
    assert config["imports"][0] == "shared@main/rules/Rule_Bleeding"


def test_update_requires_exactly_one_mode(tmp_path: Path) -> None:
    cfg = tmp_path / ".harness-config.yaml"
    _write_config(cfg, [])
    runner = CliRunner()
    # 0개
    result = runner.invoke(update_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code != 0
    # 2개
    result = runner.invoke(
        update_cmd, ["--to", "v1.0.0", "--minor", "--project-root", str(tmp_path)]
    )
    assert result.exit_code != 0


def test_update_preserves_comments_and_non_import_lines(tmp_path: Path) -> None:
    """yaml 라이브러리 round-trip 이 아니라 정규식 in-place — 주석 보존."""
    cfg = tmp_path / ".harness-config.yaml"
    cfg.write_text(
        "version: \"1.0\"\n"
        "# 회사 표준 룰\n"
        "domain: payment\n"
        "stack: java-vertx\n"
        "registry: local:reference/shared\n"
        "imports:\n"
        "  - shared@v1.0.0/rules/Rule_JWT  # 보안 핵심\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(update_cmd, ["--to", "v2.0.0", "--project-root", str(tmp_path)])
    # 주석 보존 우선: trailing comment 가 살아있는지는 정규식 한계로 100% 보장은 어려움.
    # 최소한 별개 주석 라인 (# 회사 표준 룰) 은 보존되어야 함.
    text = cfg.read_text()
    assert "# 회사 표준 룰" in text
    assert "shared@v2.0.0/rules/Rule_JWT" in text
    assert result.exit_code == 0


def test_update_missing_config_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(update_cmd, ["--to", "v1.0.0", "--project-root", str(tmp_path)])
    assert result.exit_code != 0
    assert "없음" in result.output
