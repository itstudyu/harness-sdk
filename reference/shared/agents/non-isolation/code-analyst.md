---
name: code-analyst
description: 코드베이스 분석, 의존성 추적, 영향 범위 분석 (read-only). Use when planner가 영향 범위 파악 필요, 사용자가 "이 함수 어디서 쓰여", "이 모듈 의존성 분석" 같은 요청.
---

# Code Analyst Skill

메인 Claude가 직접 수행하는 코드베이스 분석 도구.
Subagent 호출 전 사전 분석이 필요하거나, planner가 영향 범위를 파악해야 할 때 사용.

---

## 사용 시점

- planner의 사전 분석:
  - "이 변경의 영향 범위는?"
  - "이 코드는 어디서 호출되나?"
  - "이 모듈의 의존성은?"
- frontend/backend agent 부르기 전 사전 정찰
- 사용자가 명시적으로 요청

---

## 분석 절차

### 1. 프로젝트 구조 파악

```bash
# 디렉터리 구조 (빌드/캐시 제외)
find . -type d \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/dist/*' \
  -not -path '*/target/*' \
  -not -path '*/.harness-cache/*'

# 프로젝트 타입 판단
ls package.json pom.xml build.gradle Cargo.toml go.mod pyproject.toml 2>/dev/null
```

### 2. 주요 파일 인벤토리

```bash
Glob "src/**/*"
```

### 3. 의존성 / 호출 추적

```bash
# Import 분석 (프로젝트 언어에 맞게)
Grep "import" src/

# 특정 함수의 사용처
Grep "functionName" src/
```

### 4. 영향 범위 분석

특정 파일/함수가 변경됐을 때 영향받는 곳:
1. 직접 import하는 파일들 grep
2. 그 파일들이 export하는 심볼들 추출
3. 그 심볼들을 import하는 파일들 grep (transitive)
4. 깊이 2~3 까지만 (그 이상은 noise)

---

## 보고 형식

```markdown
# Code Analysis: <분석 대상>

## Overview
- Project type: <자동 감지된 것>
- Source files: <count>
- Entry points: <file paths>

## Dependency Graph (대상 모듈)
- <ModuleA> → <ModuleB, ModuleC>

## Impact Analysis (특정 변경 시)
변경 대상: <file>
직접 영향: <files>
간접 영향: <files>

## Conventions Detected
- Naming: <observed pattern>
- Folder structure: <observed pattern>
- Test location: <observed pattern>

## Risks / Notes
- <잠재적 문제, 충돌 가능 지점>
```

---

## 금지 사항

- 코드 수정 (이 skill은 read-only)
- Subagent 호출 (이 skill은 메인이 직접 사용)
- 장황한 출력 (raw grep 결과 그대로 X, 핵심만 요약)
- 추측 (코드에 명시 안 된 것을 단정하지 마라)
