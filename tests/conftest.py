# pytest 공용 fixture / sys.path 설정 (src/ 를 root 로 잡기)
"""
src/ 를 import path 에 추가 (pytest 전역).

build-spec.md Section 11.1 의 src/ 레이아웃은 namespace package 가 아니라
flat src layout 이므로 pyproject 의 packages.find 가 src/ 를 root 로 잡음.
테스트도 같은 방식으로 import.
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
