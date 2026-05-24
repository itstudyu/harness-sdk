# build-spec.md Section 9.5: .claude/settings.json — SessionStart 훅으로 컨텍스트 강제 주입
"""
훅이 'harness-gen context' 를 실행하면 stdout 이 Claude Code 컨텍스트에 자동 추가됨.
"""
from __future__ import annotations

import json
from pathlib import Path

SETTINGS = {
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "harness-gen context",
                    }
                ]
            }
        ]
    }
}


def write_settings_json(claude_dir: Path) -> Path:
    """`.claude/settings.json` 생성. 이미 존재하면 덮어씀 (도구가 생성한 파일이라 OK)."""
    claude_dir.mkdir(parents=True, exist_ok=True)
    target = claude_dir / "settings.json"
    target.write_text(
        json.dumps(SETTINGS, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target
