# Registry fetcher (build-spec.md Section 11.3): PoC local 모드 + 운용 Bitbucket clone 모드
"""
.harness-config.yaml 의 registry 값에 따라 두 모드로 동작:

- "local:<path>" (PoC)  → 같은 레포 안 path 직접 사용, version 무시 (warning 1회)
- git URL (운용)         → ~/.harness-cache/<repo>@<version>/ 에 shallow clone

import 항목 형식: shared@<version>/<path>
파일 확장자는 자동 추가 (.yaml 우선, 없으면 .md).

캐시 무효화는 명시적 (sync 메서드)만. auto TTL 없음 — Karpathy 단순함.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# import 형식: shared@<version>/<path>
IMPORT_RE = re.compile(r"^shared@(?P<version>[^/]+)/(?P<path>.+)$")

# 확장자 fallback 순서
EXTENSION_CANDIDATES: tuple[str, ...] = (".yaml", ".yml", ".md")

# PoC 모드 prefix
LOCAL_PREFIX = "local:"

# 운용 모드 캐시 root (사용자 home 의 ~/.harness-cache)
DEFAULT_CACHE_ROOT = Path.home() / ".harness-cache"


@dataclass
class FetcherError(Exception):
    """fetch 실패: 원인 메시지 + 시도한 경로/명령."""
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


@dataclass(frozen=True)
class ImportRef:
    """파싱된 import 항목. raw 원본 + version + 경로 (확장자 미포함 가능)."""
    raw: str
    version: str
    path: str


def parse_import(raw: str) -> ImportRef:
    """`shared@v1.2.0/rules/Rule_JWT` → ImportRef. 형식 위반 시 FetcherError."""
    m = IMPORT_RE.match(raw)
    if not m:
        raise FetcherError(
            f"잘못된 import 형식: '{raw}' (기대: 'shared@<version>/<path>')"
        )
    return ImportRef(raw=raw, version=m.group("version"), path=m.group("path"))


@dataclass
class Registry:
    """fetch 한 import 의 절대 경로 + version 정보 반환자."""
    root: Path                       # shared/ 가 위치하는 실제 디렉터리
    mode: str                        # "local" or "bitbucket"
    version_warned: bool = False     # local 모드 version 무시 warning 1회용
    warnings: list[str] = None       # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []

    def resolve(self, ref: ImportRef) -> Path:
        """import 경로를 실제 파일로 매핑.

        - local 모드: version 무시 (warning 1회), root/path.<ext>
        - bitbucket 모드: root 는 캐시 디렉터리 안의 reference/shared/, root/path.<ext>
        """
        if self.mode == "local" and not self.version_warned:
            self.warnings.append(
                f"local registry 모드: import version '{ref.version}' 은 무시됨"
            )
            self.version_warned = True

        base = self.root / ref.path
        if base.exists() and base.is_file():
            return base
        for ext in EXTENSION_CANDIDATES:
            candidate = base.with_suffix(base.suffix + ext) if base.suffix else base.with_suffix(ext)
            if candidate.exists():
                return candidate
        # 마지막으로 디렉터리 (planner/ 같은 폴더 형식) 도 허용
        if base.exists() and base.is_dir():
            return base
        raise FetcherError(
            f"import 를 찾을 수 없음: {ref.raw} (탐색: {base} + 확장자 {EXTENSION_CANDIDATES})"
        )


def create_registry(
    registry_value: str,
    *,
    project_root: Path,
    cache_root: Path | None = None,
    requested_version: str | None = None,
) -> Registry:
    """`.harness-config.yaml` 의 registry 값을 받아 적합한 Registry 생성.

    - "local:reference/shared" → project_root/reference/shared
    - "bitbucket.company.com/harness.git" → cache 안의 shared/ (Section 11.3 운용 모드)
    """
    if registry_value.startswith(LOCAL_PREFIX):
        return _local_registry(registry_value, project_root=project_root)
    return _bitbucket_registry(
        registry_value,
        cache_root=cache_root or DEFAULT_CACHE_ROOT,
        requested_version=requested_version,
    )


def _local_registry(registry_value: str, *, project_root: Path) -> Registry:
    local_path = registry_value[len(LOCAL_PREFIX):].strip()
    if not local_path:
        raise FetcherError("local registry 경로가 비어있음 (예: 'local:reference/shared')")
    root = (project_root / local_path).resolve()
    if not root.exists():
        raise FetcherError(f"local registry 디렉터리 없음: {root}")
    if not root.is_dir():
        raise FetcherError(f"local registry 가 디렉터리가 아님: {root}")
    return Registry(root=root, mode="local")


def _bitbucket_registry(
    registry_value: str,
    *,
    cache_root: Path,
    requested_version: str | None,
) -> Registry:
    """운용 모드: cache 에 clone (없으면) 후 안의 reference/shared/ 를 root 로."""
    if not requested_version:
        raise FetcherError(
            "Bitbucket registry 사용 시 version 필요 (imports 의 shared@<version> 에서 추출)"
        )
    repo_name = _repo_name(registry_value)
    cache_dir = cache_root / f"{repo_name}@{requested_version}"
    shared_root = cache_dir / "reference" / "shared"

    if not shared_root.exists():
        cache_root.mkdir(parents=True, exist_ok=True)
        if cache_dir.exists():
            # 부분 clone 잔존 → 깨끗이 시작
            shutil.rmtree(cache_dir)
        _git_clone(registry_value, requested_version, cache_dir)
        if not shared_root.exists():
            raise FetcherError(
                f"clone 후에도 shared/ 없음: {shared_root} "
                f"(registry 의 reference/shared/ 디렉터리 확인 필요)"
            )
    return Registry(root=shared_root.resolve(), mode="bitbucket")


def _repo_name(registry_value: str) -> str:
    """git URL 에서 repo 이름만 추출 (캐시 디렉터리명에 사용)."""
    name = registry_value.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or "registry"


def _git_clone(url: str, version: str, dest: Path) -> None:
    """shallow clone — 인증은 OS 기본 (~/.netrc, SSH key) 사용. 실패 시 친절한 메시지."""
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--branch", version,
        url,
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise FetcherError(f"git 실행파일을 찾을 수 없음: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise FetcherError(
            f"git clone 실패 (exit {exc.returncode}):\n"
            f"  명령: {' '.join(cmd)}\n"
            f"  stderr: {stderr}\n"
            f"  도움말: ~/.netrc 인증 또는 SSH key 설정 확인."
        ) from exc
