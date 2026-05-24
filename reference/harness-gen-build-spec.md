# harness-gen: Project Knowledge Graph Generator

> **AI 빌드 명세서**
> - 대상: 이 도구를 구축할 AI 에이전트 (Claude Code 전용)
> - 원칙: Karpathy 50줄 — 명세는 결정적, 군더더기 없음
> - 가정 후 진행 금지. 모르면 사용자에게 물어볼 것.

---

## 0. 이 도구는 무엇인가

### 한 줄 정의
프로젝트 레포에 **Karpathy LLM Wiki 스타일의 Knowledge Graph 구조**를 자동 생성하는 CLI. 회사 공통 레지스트리에서 룰/패턴을 가져오고, 프로젝트별 커스터마이즈를 지원.

### 이론적 기반 — 3가지 사상의 결합

이 도구는 다음 3가지 산업 패턴을 **동시에 구현**한다:

| 패턴 | 출처 | 이 도구에서의 구현 |
|---|---|---|
| **CLAUDE.md / LLM Wiki** | Andrej Karpathy | 출력물이 순수 Markdown + YAML, DB 없음 |
| **GraphRAG** | Microsoft + 산업 표준 | Rule ↔ Pattern ↔ Example의 명시적 관계 |
| **Reference Architecture** | Harness Inc. SDKG | 공유 레지스트리 + 프로젝트별 import |

### 핵심 통찰

- **생성 결과물 (.harness/) = 프로젝트의 LLM Wiki**
- **공유 레지스트리 + imports = GraphRAG 관계망**
- **모든 게 파일 기반** — DB / 임베딩 / 벡터 검색 X
- **AI는 파일만 읽으면 됨** — 외부 호출 X
- **🎯 타겟 AI: Claude Code 전용** — Cursor/Copilot 호환 고려 X

### 왜 DB가 아닌 파일인가 (Karpathy 사상)

Karpathy 원전 인용 (의역):
> "같은 원시 데이터를 매번 다시 읽는 대신, 모델이 한 번 읽고 구조화한 다음 진화하는 지식 계층을 구축한다."

이 도구는 **컴파일러**다. 사용자의 config를 받아서 AI가 즉시 소비 가능한 구조화된 파일을 생성한다. 임베딩이나 벡터 DB 불필요. AI가 디렉터리 따라가며 직접 읽음. 가벼움 + 디버깅 가능 + Git 추적 가능.

### LLM Wiki와 GraphRAG의 관계

이 도구가 만드는 구조는 본질적으로 같은 사상의 두 표현이다:
- **LLM Wiki 관점**: Markdown 파일 모음 with backlinks
- **GraphRAG 관점**: 노드(파일) + 엣지(YAML ref)로 구성된 그래프

→ 이 도구는 **둘을 하나의 출력물로 통합**한다.

---

## 0.1 Pre-flight TBD (진행 전 확인)

대부분 결정됨. 다음만 확인:

- [x] **구현 언어**: **Python** (확정)
- [x] **공유 레지스트리**: **사내 Bitbucket Server** (확정)
- [x] **타겟 AI**: **Claude Code 전용** (확정)
- [x] **버저닝**: Semantic Versioning + Git tags (기본값)
- [x] **첫 타겟 스택**: Java/Vert.x (확정)
- [ ] **배포 방식**: pip + git URL (PoC) → 추후 사내 PyPI 미러?
- [ ] **첫 PoC 도메인**: payment? user? 다른 것?

→ 미정 항목은 사용자에게 질문 후 진행.

---

## 1. System Overview

### 1.1 3-Tier 아키텍처

```
[Shared Registry]              ← 회사 공통 (Git repo, 버전 태그)
       │ 관리: 아키텍트팀
       │
       │ fetch
       ↓
[harness-gen CLI]              ← 구축할 도구 (이 명세서의 대상)
       │ 관리: 플랫폼팀
       │
       │ generate
       ↓
[Project's .harness/]          ← 각 프로젝트의 KG (Markdown/YAML)
       │ 관리: 각 프로젝트팀
       │
       │ read
       ↓
[Claude Code]                  ← AI 도구 (이 구조를 소비)
```

### 1.2 핵심 워크플로우

```
init     → 템플릿 config 생성 (공유에서 preset 참조)
generate → imports fetch + overrides 적용 + local 병합 → .harness/
verify   → config와 .harness/ 동기화 검증 (CI용)
update   → 버전 갱신
```

### 1.3 Input / Output

| | 무엇 | 누가 |
|---|---|---|
| **Input** | `.harness-config.yaml` (1개 파일) | 개발자가 작성 |
| **Output** | `.harness/` 디렉터리 | 도구가 생성 |
| **External** | Shared Registry | 아키텍트팀이 관리 |

---

## 2. 설계 원칙 (이론적 기반 반영)

### From Karpathy
- 생성되는 CLAUDE.md는 **100줄 이내** (50줄 가능하면 50줄로)
- 생성 파일에 장황한 설명 금지
- 각 파일은 단일 목적
- 도구 자체도 단일 책임 (스캐폴딩 + 머지만)

### From LLM Wiki
- 모든 출력물은 순수 Markdown + YAML
- DB 연결 불필요
- AI가 파일을 직접 읽음
- 파일 간 참조 (YAML ref) = 그래프 엣지

### From GraphRAG
- Rule / Pattern / Example 간 명시적 관계
- 다단계 추론 가능 (Rule → Pattern → Example)
- 벡터 임베딩 불필요
- 구조 우선

### 도구 자체의 메타 원칙

이 도구는 **자신이 구현하는 사상을 스스로 따른다**:
- 도구 코드도 단순할 것 (Karpathy)
- 설정은 YAML로 표현 (Wiki)
- 명령은 명시적, 추측 없음 (GraphRAG의 결정성)

---

## 3. Data Model

### 3.1 Node 타입 (공유 ontology에 정의)

```yaml
# shared/ontology.yaml (공유 레지스트리에 위치)

node_types:
  Rule:
    id: string (format: "Rule_*")
    description: string
    severity: enum [MUST, SHOULD, MAY]
    category: enum [Security, Performance, Style, API_Contract]
    rationale: string
    exceptions: list[string]
    deprecated: bool

  Pattern:
    id: string (format: "Pattern_*")
    language: enum [java, python, typescript]
    implements: ref(Rule.id)  # 정확히 1개
    snippet: string (max 30 lines)
    imports: list[string]

  Example:
    id: string (format: "Example_*")
    filePath: string
    gitCommit: string
    demonstrates: list[ref(Rule.id)]
    quality: enum [draft, reviewed, approved]
```

### 3.2 관계 표현 (파일 기반, DB 없음)

YAML 참조 필드로 엣지 표현:

```yaml
# Rule_JWT.yaml
id: Rule_JWT

# Pattern_JWT_Java.yaml
id: Pattern_JWT_Java
implements: Rule_JWT          # ← 엣지

# Example_ChargeAPI.yaml
id: Example_ChargeAPI
demonstrates: [Rule_JWT]      # ← 엣지
```

→ AI가 `.harness/` 로드 시 이 ref를 따라가며 그래프 탐색.

### 3.3 Hard Constraints

- `Pattern.implements`는 정확히 1개 Rule
- `Example.demonstrates`는 최소 1개 Rule
- 노드 id는 글로벌 unique
- local 노드의 id는 `Local_*` prefix 권장 (충돌 방지)

---

## 4. CLI Commands

### 4.1 `harness-gen init`

**목적**: 새 프로젝트에 템플릿 config 생성

```bash
$ harness-gen init [--stack=java-vertx] [--domain=payment]
                   [--subagents=frontend-agent,backend-agent]
                   [--tools=code-analyst]
                   [--registry=bitbucket.company.com/harness.git]
```

**동작 순서**:
1. Bitbucket harness 레포에서 최신 안정 버전 확인 (Section 9.6.11)
2. `--stack` 기준 preset 가져옴 (목록만, 파일은 아직 fetch 안 함)
3. `--subagents` 옵션으로 사용할 Subagent 선택 (isolation/에서 옴)
4. `--tools` 옵션으로 메인 도구 선택 (non-isolation/에서 옴, planner는 자동 포함)
5. `.harness-config.yaml` 템플릿 생성 (rules + agents 섹션)
6. `.gitignore` 업데이트 (`~/.harness-cache/`, `.harness/plan/` 제외)

**대화형 모드** (옵션 미지정 시):
```
? Registry URL: bitbucket.company.com/harness.git
? Domain: payment
? Stack: java-vertx
? Subagents (격리됨, Task로 호출):
  ☑ frontend-agent
  ☐ backend-agent
? Tools (메인에서 실행, planner는 자동):
  ☑ code-analyst
```

**핵심**: init은 공유 룰/agent를 **"참조 명시"만** 한다. 실제 파일 fetch/생성은 generate에서.

**Preset 동작**:
- `--stack` 값에 해당하는 `<registry>/reference/shared/presets/<stack>.yaml` 가 있으면 그 내용을 config 템플릿의 imports/subagents/tools 기본값으로 사용
- 없으면 (PoC seed 처럼 presets 폴더가 없는 경우) → warning 1회 출력 + 빈 imports/subagents/tools 로 config 생성 (사용자가 수동으로 채워야 함, 에러 X)
- presets 파일 형식:
  ```yaml
  # shared/presets/java-vertx.yaml
  recommended_imports:
    - rules/Rule_JWT
    - rules/Rule_ErrorFormat
    - patterns/Pattern_JWT_Java
  recommended_subagents: [frontend-agent, backend-agent]
  recommended_tools: [code-analyst]
  ```

### 4.2 `harness-gen generate`

**목적**: config를 컴파일해서 `.harness/` 생성

```bash
$ harness-gen generate [--cache-dir=~/.harness-cache]
```

**Phase 단계**:
```
Phase 1: Config 파싱 + 검증
        - .harness-config.yaml 의 모든 필드 검증 (Section 5 schema)
        - tools 에 planner 명시 시 → warning + 무시 (planner는 자동)
        - subagents/tools 에 shared 와 local 둘 다 없는 agent → 에러
Phase 2: Imports 해결 (Bitbucket harness fetch or 캐시 — Section 11.3)
Phase 3: Ontology 병합 (공유 + local)
Phase 4: Overrides 적용 (rules + agents 모두, approved_by 검증)
Phase 5: Local 데이터 통합 (rules/patterns/skills 의 데이터만)
        - agent install 은 Phase 6 에서 (책임 분리)
Phase 6: Agent 인스턴스 결정 + 설치 (install 레이어)
        - 인스턴스 목록 = subagents + tools + local.agents + planner (항상)
        - install_kind 결정 (Section 9.6.4 path → kind 매핑)
        - subagents (isolation/) → .claude/agents/<X>.md
        - tools/planner (non-isolation/) → .claude/skills/<X>/SKILL.md
        - planner 의 templates/ 통째로 복사 → .claude/skills/planner/templates/
        - subagent frontmatter 의 skills: 의존성 해결 → .claude/skills/
        - .harness/agents/manifest.yaml 생성 (Section 9.6.6 schema)
Phase 7: CLAUDE.md 합성 (rules + installed agents 목록 + custom 필드 요약)
Phase 8: .gitignore 갱신 (.harness/plan/ 추가)
Phase 9: .lock.yaml 갱신 (agent/skill/rule 모두 commit hash 포함)
```

### 4.3 `harness-gen verify`

**목적**: CI에서 동기화 확인

```bash
$ harness-gen verify
# Exit 0: OK
# Exit 1: config와 .harness/가 불일치
# Exit 2: override 미승인
# Exit 3: deprecated 룰 사용 중
```

### 4.4 `harness-gen update`

**목적**: import 버전 일괄 갱신

```bash
$ harness-gen update [--to=v1.3.0] [--minor] [--major]
# config의 imports 버전만 갱신. 실제 fetch는 generate에서.
```

### 4.5 `harness-gen plan` ⭐ (작업 plan 관리)

**목적**: `.harness/plan/{yyyymmdd-작업명}/` 디렉터리 관리

```bash
$ harness-gen plan list                                # 모든 plan (날짜순 정렬)
$ harness-gen plan show 20260524-payment-page          # 특정 plan 상세 보기
$ harness-gen plan clean --older-than=30d              # 30일 이상 된 plan 삭제
$ harness-gen plan clean --status=abandoned            # 중단된 plan만 삭제
$ harness-gen plan clean --status=done --older-than=7d # 완료된 1주 이상된 plan 삭제
```

**동작**:
- `list`: status.yaml 기반으로 plan 상태별 색상 표시
- `show`: plan.md + 모든 *-plan.md + status.yaml 출력
- `clean`: 조건 매치 디렉터리 삭제 (확인 프롬프트, --yes로 skip 가능)

**핵심**: 자동 삭제 X. 사용자가 원할 때만 정리. 자동 보관/이동 정책 X (Karpathy 단순함).

### 4.6 `harness-gen context` ⭐ (Claude Code 훅용)

**목적**: 현재 프로젝트의 harness 컨텍스트를 stdout으로 출력. **Claude Code SessionStart 훅에서 호출**.

```bash
$ harness-gen context
# stdout으로 컨텍스트 출력 (Claude Code가 자동 캡처)
```

**동작**:
1. 프로젝트 루트의 `CLAUDE.md` 읽기
2. `.harness/.lock.yaml`에서 stale 여부 확인 (1시간 초과 시 경고)
3. stdout으로 통합 컨텍스트 출력
4. Exit 0 (성공) → Claude Code 컨텍스트에 추가됨

**Stale 경고 예시**:
```
⚠ 이 프로젝트의 harness 컨텍스트가 2일 전에 생성됨.
  최신 룰 적용 위해 `harness-gen generate` 권장.
[기존 CLAUDE.md 내용 출력]
```

---

## 5. `.harness-config.yaml` Schema

사용자가 작성하는 **유일한 파일**:

```yaml
# 메타
version: "1.0"                    # config 스키마 버전
domain: "payment"                 # 도메인
stack: "java-vertx"               # 스택

# 공유 레지스트리에서 가져올 것들
imports:
  - shared@v1.2.0/rules/Rule_JWT
  - shared@v1.2.0/rules/Rule_ErrorFormat
  - shared@v1.2.0/patterns/Pattern_JWT_Java
  - shared@v1.2.0/ontology.yaml

# 가져온 것들의 부분 수정
overrides:
  Rule_JWT:
    exceptions: ["/payment/webhook"]
    approved_by: "@architect-kim"
    approved_at: "2026-05-20"
    justification: "외부 webhook 자체 서명 검증"

# 프로젝트 전용 (local 파일 경로)
local:
  rules:
    - rules/Rule_RefundTimeLimit.yaml
  patterns:
    - patterns/Pattern_RefundFlow.yaml

# 🆕 Agent 섹션 (Section 9.6, rules 패턴과 일관)
agents:
  # planner는 항상 설치 (명시 불필요, 자동)

  # Subagent 선택 (shared/agents/isolation/에서 옴)
  subagents:
    - frontend-agent
    # - backend-agent      # 미선택 시 설치 X

  # 메인 도구 선택 (shared/agents/non-isolation/에서 옴)
  tools:
    - code-analyst
    # - compliance-agent

  # 회사 표준 agent의 부분 수정 (rules의 overrides와 동일 패턴)
  overrides:
    frontend-agent:
      framework: "angular@16"
      skills:                            # append (preload skill 추가)
        - angular16-migration-helper
      approved_by: "@kim"
      approved_at: "2026-05-24"
      justification: "팀이 Angular 16 사용 중"

  # 프로젝트 전용 agent (rules의 local과 동일 패턴)
  local:
    - local/agents/mobile-agent.md       # 회사 표준에 없는 신규
```

### 5.1 정식 Schema (도구 구현 시 검증 룰)

```yaml
# .harness-config.yaml schema (JSON Schema 풍 의사 표현)
version: string                  # required, "1.0" (현재)
domain: string                   # required, 자유 텍스트
stack: string                    # required, preset 식별용
registry: string                 # required, "bitbucket.../harness.git" 또는 "local:reference/shared"

imports: list[string]            # optional, default []
                                 # 형식: "shared@<version>/<path>"

overrides: map                   # optional, default {}
                                 # key: rule_id 또는 agent_name
                                 # value: map (수정할 필드 + approved_by + approved_at)

local:                           # optional, default {}
  rules: list[string]            # 파일 경로 (config 기준 상대)
  patterns: list[string]
  skills: list[string]           # 스킬 디렉터리 경로
  # agents.local 은 agents 섹션 안에 (아래 참조)

agents:                          # optional (rules 만 쓰면 생략 가능), default {}
  subagents: list[string]        # default []
                                 # agent name 만 (출처는 자동 — shared 우선, local fallback)
  tools: list[string]            # default []
                                 # planner 는 자동, 명시 시 warning
  overrides: map                 # default {}
                                 # key: agent_name
                                 # value: map (자유 필드 + approved_by 필수 + approved_at 필수)
  local: list[string]            # default []
                                 # 파일 경로
```

### 5.2 검증 룰 (Phase 1)

- 모든 required 필드 누락 → 에러
- `version` 이 알려진 schema 버전 아님 → 에러
- `imports` 형식 위반 → 에러 (정규식: `^shared@[^/]+/.+$`)
- `agents.tools` 에 `planner` 명시 → warning + 제거
- `agents.overrides.<X>` 의 `approved_by` 누락 → 에러 (CI 모드) / warning (개발 모드)
- `agents.subagents`/`tools` 의 agent 가 shared 와 local 어디에도 없음 → Phase 2 후 에러

**핵심**: `CLAUDE.md`는 **프로젝트 루트**에 위치. `.claude/settings.json`이 **SessionStart 훅**을 자동 설정하여 무조건 컨텍스트에 로드되도록 보장.

```
project-root/
├── CLAUDE.md                     ← 🤖 Claude Code 자동 로드 (≤100줄, 요약 + agent 목록)
├── .harness-config.yaml          ← 👤 사용자 작성 (rules + agents 선택)
├── .gitignore                    ← ✏️ ~/.harness-cache/ + .harness/plan/ 추가됨
├── .claude/                      ← 🤖 도구 생성, Claude Code 통합 ⭐
│   ├── settings.json             ← SessionStart 훅 — 컨텍스트 강제 주입
│   ├── agents/                   ← 🆕 Subagent 정의 (isolation/에서 옴)
│   │   ├── frontend-agent.md     ← 사용자가 subagents 에 선택한 것만
│   │   └── backend-agent.md
│   └── skills/                   ← 🆕 Skill (planner + tools + 검증 도구)
│       ├── planner/              ← 항상 설치 (shared/agents/non-isolation/planner/에서 옴)
│       │   ├── SKILL.md
│       │   └── templates/        ← planner가 plan.md 작성 시 사용
│       │       ├── plan-single.md.tmpl
│       │       ├── plan-multi.md.tmpl
│       │       ├── role-plan.md.tmpl
│       │       └── status.yaml.tmpl
│       ├── code-analyst/SKILL.md ← tools 에서 선택한 것 (non-isolation/에서 옴)
│       └── lint-checker/SKILL.md ← agent 의존 skill (자동 설치)
├── local/                        ← 👤 사용자 작성 (선택, Section 9.6.5)
│   ├── agents/                   ← 프로젝트 전용 agent 정의
│   │   └── mobile-agent.md
│   └── skills/                   ← 프로젝트 전용 skill (의존 skill 작성용)
│       └── react-native-linter/SKILL.md
├── .harness/                     ← 🤖 도구 생성, 상세 그래프 + plan
│   ├── ontology.yaml             ← 병합된 의미 정의
│   ├── rules/
│   │   ├── _resolved/            ← imports 결과 (override 적용됨)
│   │   ├── local/                ← 프로젝트 전용
│   │   └── CLAUDE.md             ← (선택) rules 디렉터리 작업 시 참고용
│   ├── patterns/
│   │   ├── _resolved/
│   │   └── local/
│   ├── agents/
│   │   └── manifest.yaml         ← 🆕 설치된 agent 메타 (planner가 참조)
│   ├── plan/                     ← 🆕 작업별 plan (.gitignore 처리, 로컬만)
│   │   ├── 20260524-payment-page/   ← {yyyymmdd-작업명} 형식
│   │   │   ├── plan.md
│   │   │   ├── frontend-plan.md
│   │   │   └── status.yaml       ← pending|in_progress|done|failed|abandoned
│   │   ├── 20260523-user-login-fix/
│   │   └── 20260520-refund-flow/
│   └── .lock.yaml                ← 버전/커밋 기록 (재현용)
└── ... 기존 프로젝트 파일들
```

### 3가지 컨텍스트 보장 메커니즘

| 메커니즘 | 보장 수준 | 위치 |
|---|---|---|
| 1. **`.claude/settings.json` 훅** ⭐ | **무조건** (강제) | `.claude/settings.json` |
| 2. **루트 CLAUDE.md 자동 로드** | 기본 동작 | `/CLAUDE.md` |
| 3. **Nested CLAUDE.md** | 디렉터리 작업 시 | `.harness/rules/CLAUDE.md` |

→ **3중 보호**. 1번이 메인, 2번이 백업, 3번은 깊은 작업 시 보강.

### 두 종류 CLAUDE.md의 역할

| 위치 | 용도 | 분량 | 로드 시점 |
|---|---|---|---|
| **`/CLAUDE.md`** (루트) | 프로젝트 전체 요약 + `.harness/` 포인터 | ≤100줄 | 매 세션 자동 + 훅 강제 |
| **`/.harness/rules/CLAUDE.md`** (선택) | rules 작업 시 deep context | ≤50줄 | Claude가 rules/ 작업 시 |

### 왜 이 구조인가
- Claude Code는 **루트 CLAUDE.md를 자동 인식** + **하위 디렉터리 CLAUDE.md도 컨텍스트로 로드**
- `.claude/settings.json`의 **SessionStart 훅**은 stdout이 Claude 컨텍스트로 추가됨 (공식 동작)
- 루트 CLAUDE.md = "전체 요약" (Karpathy 100줄 원칙)
- `.harness/` 안의 파일들 = 상세 그래프 (필요 시 참조)
- 훅으로 **누락 위험 0** 보장

---

## 7. 공유 레지스트리 구조

```
github.com/company/harness/    # 단일 레포 (cli + shared 통합)
├── rules/                        ← 회사 표준 룰
├── patterns/                     ← 표준 코드 패턴
├── presets/                      ← init이 참조 (스택별 추천 번들)
│   ├── java-vertx.yaml
│   ├── python-fastapi.yaml
│   └── frontend-angular.yaml
├── ontology.yaml                 ← 공통 의미 정의
└── version.yaml                  ← 메타데이터
```

**버저닝**: Git 태그 (`v1.2.0`, `v1.3.0` …)

---

## 8. Resolution Logic (해석 로직) — 가장 중요

`harness-gen generate` 실행 시 정확한 순서:

```
Step 1: imports 수집
   각 import 경로 → 캐시 확인 → 없으면 fetch
   결과: 원본 YAML 파일 목록

Step 2: ontology 병합
   공유 ontology + local ontology (있다면) merge
   충돌 시 local 우선

Step 3: overrides 적용
   각 override 항목:
     a. 대상 노드가 imports에 있는지 확인
     b. 없으면 에러
     c. approved_by 검증 (CI 모드면)
     d. 노드의 해당 필드만 교체

Step 4: local 통합
   local 파일 그대로 .harness/local/ 복사
   id 충돌 시 에러

Step 5: CLAUDE.md 합성 (Section 9 참고)
   - 위치: **프로젝트 루트** (`/CLAUDE.md`), Claude Code 자동 로드용
   - .harness/ 안의 상세 파일을 가리키는 포인터 역할 포함

Step 6: .lock.yaml 생성
   - 각 import의 실제 Git commit hash
   - 생성 시각
   - 도구 버전
```

---

## 9. CLAUDE.md 생성 규격 (Karpathy 준수, Claude Code 호환)

**위치**: 프로젝트 루트 (`/CLAUDE.md`) — Claude Code 자동 로드 위치

**MUST 따를 형식**:

```markdown
# Project Context

**Domain**: payment
**Stack**: Java/Vert.x
**Generated**: 2026-05-24 (by harness-gen v0.1.0)

## Applied Rules

- **Rule_JWT** (MUST): 외부 API는 JWT 검증. 예외: /payment/webhook
- **Rule_ErrorFormat** (MUST): 에러는 {code, message, timestamp}
- **Rule_RefundTimeLimit** (MUST, local): 환불은 24시간 이내만

## Available Patterns

- `Pattern_JWT_Java` → JWT 검증
- `Pattern_ErrorResponse_Java` → 표준 에러 응답
- `Pattern_RefundFlow` (local) → 환불 로직 표준

## Installed Agents

- **planner** (always, skill): 메인 행동 양식 — 작업 계획 수립
- **frontend-agent** (subagent): frontend 구현 전담 (frontmatter description 그대로)
- **code-analyst** (skill): 코드베이스 분석 및 의존성 추적

→ planner가 작업 요청 시 `.harness/plan/{yyyymmdd-작업명}/`에 plan 작성

## Project Notes

- 외부 webhook 처리는 별도 인증 로직 사용
- 환불 관련 코드는 RefundHandler 참조

## 상세 컨텍스트 (필요 시 참조)

- 룰 전체 정의: `.harness/rules/`
- 패턴 코드 조각: `.harness/patterns/`
- 의미 정의: `.harness/ontology.yaml`
- agent 상세 메타: `.harness/agents/manifest.yaml`
- 작업 plan 히스토리: `.harness/plan/` (로컬만)
- 정확한 버전 정보: `.harness/.lock.yaml`
```

**제약**:
- 최대 100줄
- 초과 시 룰을 더 작은 그룹으로 split
- 마크다운 헤더 깊이 ≤ 3
- 코드 블록 없음 (참조만)

---

## 9.5 Claude Code Hook Integration ⭐ (컨텍스트 강제 보장)

### 왜 훅이 필요한가
`CLAUDE.md` 자동 로드만으로도 동작하지만, **훅을 추가하면 누락 위험 0**.

- 자동 로드: Claude Code 기본 동작 (대부분 작동)
- 훅 강제: **무조건 보장** (Anthropic 공식 메커니즘)

### 생성할 `.claude/settings.json`

`harness-gen generate` 시 자동으로 다음 파일 생성:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "harness-gen context"
          }
        ]
      }
    ]
  }
}
```

### 동작 흐름

```
[사용자가 claude code 실행]
       │
       ▼
[Claude Code: SessionStart 이벤트 발생]
       │
       ▼
[.claude/settings.json 읽음 → 훅 발견]
       │
       ▼
[$ harness-gen context 실행]
       │
       ▼
[stdout으로 CLAUDE.md 내용 + 메타데이터 출력]
       │
       ▼
[Claude Code: 출력을 컨텍스트에 자동 추가]
       │
       ▼
[Claude가 모든 룰을 이해한 상태로 세션 시작] ✅
```

### MUST 충족 사항

- ✅ Exit 0 (성공) — 그래야 stdout이 컨텍스트로 추가됨
- ✅ stdout만 사용 (stderr는 디버그용)
- ✅ 빠른 실행 (≤500ms 권장 — 세션 시작 지연 최소화)
- ✅ Stale 체크 포함 (1시간 초과 시 stdout에 경고)

### 추가 옵션 (선택적, 고급)

**UserPromptSubmit 훅** 추가하면 매 프롬프트마다 컨텍스트 보강 가능:

```json
{
  "hooks": {
    "SessionStart": [...],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "harness-gen context --light"
          }
        ]
      }
    ]
  }
}
```

→ PoC에선 SessionStart만으로 충분. 필요시 추가.

### Generate가 만들어야 할 것 (요약)

| 파일 | 내용 |
|---|---|
| `/CLAUDE.md` | 프로젝트 컨텍스트 요약 + 설치된 agent 목록 (Section 9 형식) |
| `/.claude/settings.json` | SessionStart 훅 설정 |
| `/.claude/agents/*.md` | 선택된 Subagent 정의 (isolation/에서, Section 9.6.4) |
| `/.claude/skills/planner/SKILL.md` | 항상 설치, 메인 행동 양식 |
| `/.claude/skills/{tools, deps}/SKILL.md` | tools + agent 의존 skill 자동 설치 |
| `/.harness/...` | 상세 그래프 (rules, patterns, ontology) |
| `/.harness/agents/manifest.yaml` | 설치된 agent 메타 (정식 schema 는 Section 9.6.6) |
| `/.harness/plan/` | 작업별 plan (.gitignore 처리, Section 9.6.8) |
| `/.harness/.lock.yaml` | 재현성 보장 정보 (agent 출처 commit hash 포함) |
| `/.gitignore` | `~/.harness-cache/`, `.harness/plan/` 추가 |

→ `harness-gen generate` 한 명령으로 위 전부 자동 생성.

---

## 9.6 Multi-Agent Orchestration ⭐ (Planner-Driven Workflow)

### 9.6.1 핵심 사상 — 3가지 호출 메커니즘의 분리

Claude Code는 3가지 서로 다른 메커니즘을 제공한다. harness-gen은 이를 **명확히 분리**해서 사용한다:

| 종류 | 위치 | Context | 호출 주체 | 용도 |
|---|---|---|---|---|
| **Subagent** | `.claude/agents/*.md` | **분리됨** (별도 window) | 메인이 `Task`로 호출 | 큰 작업 위임 (frontend 전체 구현 등) |
| **Skill** | `.claude/skills/*/SKILL.md` | **공유** (메인 context) | 메인이 자동/명시적 호출, Subagent도 preload 시 가능 | planner, 검증, 도구 모두 |
| **Slash Command** | `.claude/commands/*.md` | **공유** (메인 context) | 메인이 `/명령어`로 호출 | (현 디자인에선 미사용 — 모두 Skill로 통일) |

**⚠️ 기술적 제약 (Claude Code 공식 동작)**:
- **Slash Command는 Subagent 내부에서 호출 불가능** (메인 세션 전용)
- **Skill은 Subagent에서 호출 가능** (단, agent frontmatter의 `skills:` 필드로 preload 필요)
- **Subagent가 다른 Subagent 호출 불가능** (공식 금지, nested subagent X)
- → **검증/도구는 Skill로 통일** (메인도, Subagent도 호출 가능)

### 9.6.2 Planner = 메인 자체 (Subagent X)

`planner`는 **별도 Subagent가 아니라 메인 Claude의 행동 양식**이다:

- **구현 방식**: **Skill** (`.claude/skills/planner/SKILL.md`)로만 구현
- 메인은 자기 자신을 Subagent로 호출 불가능 → Skill이 유일한 메커니즘
- 항상 설치됨 (사용자 선택 불가)
- 메인이 계획 + 위임 + 검증 + 재시도 결정을 모두 수행
- `.harness/plan/{yyyymmdd-작업명}/plan.md` 와 `*-plan.md` 파일을 직접 작성

### 9.6.3 아키텍처: Conductor Pattern

```
사용자
  ↓
메인 Claude (= planner skill로 동작)
  │  - plan.md 작성
  │  - frontend-plan.md, backend-plan.md 등 작성
  │  - 의존성/병렬 가능성 판단 (Section 9.6.10)
  │
  ├─→ Task(frontend-agent) ── 별도 context ──→ 구현 + 자기 검증 (preloaded skills)
  ├─→ Task(backend-agent)  ── 별도 context ──→ 구현 + 자기 검증
  │   (병렬 가능 시 동시 dispatch)
  │
  └─ 결과 요약만 메인에 반환 ← Anthropic 공식 권장 패턴
     ↓
     통합 검증 실패 시 → 해당 Subagent 재호출하여 수정
```

**역할 분담**:
- **Subagent (frontend-agent 등)**: 구현 + 자기 검증 (preloaded skill로). 최종 요약만 메인에 반환
- **메인 (planner)**: 계획 + 위임 + 통합 검증 + 흐름 통제

### 9.6.4 Agent 분류 (shared 안의 폴더 구조)

`shared/` (Bitbucket harness/shared 또는 PoC 시 `reference/shared/`) 안에서 agent를 **isolation 여부**로 분류:

```
shared/                                (Bitbucket harness/shared 또는 reference/shared/)
├── agents/
│   ├── isolation/                     ← Subagent로 설치됨 (context 분리)
│   │   ├── frontend-agent.md
│   │   └── backend-agent.md
│   └── non-isolation/                 ← Skill로 설치됨 (context 공유)
│       ├── code-analyst.md
│       └── planner/                   ⭐ 항상 설치 (메인 행동 양식)
│           ├── SKILL.md               ← Claude Code 표준 (skills 폴더 형식)
│           └── templates/             ← plan/role-plan/status.yaml 템플릿
│               ├── plan-single.md.tmpl
│               ├── plan-multi.md.tmpl
│               ├── role-plan.md.tmpl
│               └── status.yaml.tmpl
└── skills/                            ← 재사용 가능한 검증/도구
    └── lint-checker/
        └── SKILL.md
```

**설치 변환 룰** (도구가 generate 시 수행):

| Source (shared/) | Target (사용자 프로젝트) | Claude Code 메커니즘 |
|---|---|---|
| `agents/isolation/<X>.md` | `.claude/agents/<X>.md` | Subagent |
| `agents/non-isolation/<X>.md` (단일 파일) | `.claude/skills/<X>/SKILL.md` | Skill |
| `agents/non-isolation/<X>/SKILL.md` (폴더) | `.claude/skills/<X>/SKILL.md` | Skill |
| `agents/non-isolation/<X>/<subdir>/` | `.claude/skills/<X>/<subdir>/` | Skill 부속 자료 |
| `skills/<X>/SKILL.md` | `.claude/skills/<X>/SKILL.md` | Skill (도구) |

**개념 vs 구현 분리**:
- 사용자/팀 입장: 둘 다 "agent" (isolation 여부로 구분)
- Claude Code 입장: Subagent vs Skill로 변환되어 설치
- → 사용자는 추상 개념(agent)으로 생각, 도구가 적절한 메커니즘으로 자동 변환

**Default agent seed**:
- `reference/shared/` 디렉터리에 default 템플릿 작성 완료 (frontend-agent, backend-agent, code-analyst, planner/, lint-checker)
- 이 디렉터리는 Bitbucket harness/shared 의 1차 자료
- PoC 단계에선 도구가 이 디렉터리를 직접 fetch 대체로 사용 가능 (Bitbucket 셋업 전)
- 자세한 내용: `reference/shared/README.md`

### 9.6.5 Agent 선택 (사용자 커스텀, rules 패턴과 일관)

`.harness-config.yaml` 에 agent 섹션 추가:

```yaml
# 기존 섹션들 (rules)
imports: [...]
overrides: [...]
local: [...]

# 🆕 Agent 섹션 (rules 패턴 그대로 적용)
agents:
  # planner는 항상 설치 (명시 불필요, 자동)

  subagents:                           # isolation/에서 옴
    - frontend-agent
    # - backend-agent                  # 미선택 → 설치 X

  tools:                               # non-isolation/에서 옴 (planner 제외)
    - code-analyst
    # - compliance-agent

  # 회사 표준 agent의 부분 수정 (rules의 overrides와 동일 패턴)
  overrides:
    frontend-agent:
      framework: "angular@16"
      skills:                          # append (preload skill 추가)
        - angular16-migration-helper
      approved_by: "@kim"
      approved_at: "2026-05-24"
      justification: "팀이 Angular 16 사용 중"

  # 프로젝트 전용 agent (rules의 local과 동일 패턴)
  local:
    - local/agents/mobile-agent.md     # 회사 표준에 없는 신규
```

**Generate 동작**:
1. `subagents` + `tools` 의 agent를 해당 출처에서 fetch (Bitbucket harness 레포의 `reference/shared/`)
2. agent frontmatter의 `skills:` 의존성 자동 해결 → `.claude/skills/`에 설치
3. `overrides` 적용 (rules overrides와 동일 로직, approved_by 필수)
4. `local` agent + 그 의존 skill 통합
5. `planner` skill 항상 설치 (`.claude/skills/planner/SKILL.md`)
6. `.harness/agents/manifest.yaml` 생성
7. CLAUDE.md에 설치된 agent 목록 요약 추가

### 9.6.6 설치된 Agent 인지 메커니즘 (Dual-Layer)

planner가 "지금 어떤 agent들이 있는지" 알아야 plan을 적절히 짠다. **두 곳에 기록**:

#### Layer 1: CLAUDE.md (요약, 사람 + 메인 즉시 인지)
```markdown
## Installed Agents
- planner (skill, always installed)
- frontend-agent (subagent)
- code-analyst (skill)
```

#### Layer 2: `.harness/agents/manifest.yaml` (상세, planner skill이 참조)

agent 정의 파일의 frontmatter 를 그대로 옮긴 형태 + harness-gen 이 추가하는 install 메타:

```yaml
agents:
  planner:
    install_kind: skill                  # subagent | skill (도구가 자동 채움)
    source: agents/non-isolation/planner/   # 도구가 자동 채움
    location: .claude/skills/planner/SKILL.md
    always_installed: true               # planner는 항상

  frontend-agent:
    install_kind: subagent
    source: agents/isolation/frontend-agent.md
    location: .claude/agents/frontend-agent.md
    skills_preloaded:                    # subagent frontmatter의 skills: 그대로
      - lint-checker
    description: "Frontend 구현 전담 Subagent"

  code-analyst:
    install_kind: skill
    source: agents/non-isolation/code-analyst.md
    location: .claude/skills/code-analyst/SKILL.md
```

**핵심**:
- `install_kind`, `source`, `location` 은 **도구가 install 시 자동 채움** (agent 작성자가 적지 않음)
- `skills_preloaded`, `description` 등은 agent frontmatter에서 복사
- 추가 메타가 필요해지면 (예: 병렬 호환성) **agent 작성자가 frontmatter에 적고**, 도구는 manifest로 옮기기만 함 (도구가 발명 X)

#### manifest.yaml 정식 schema

```yaml
# .harness/agents/manifest.yaml schema
version: "1.0"           # required, manifest schema 버전
generated_at: <ISO 8601> # required, 생성 시각
generated_by: <string>   # required, "harness-gen v0.1.0" 같은 도구 버전
agents:                  # required, map: <agent-name> → entry
  <agent-name>:
    # 도구가 자동 채움
    install_kind: <enum: subagent | skill>  # required
    source: <string>                        # required, shared/ 내 상대경로
    location: <string>                      # required, 프로젝트 내 install 경로
    always_installed: <bool>                # optional, default false (planner만 true)

    # frontmatter에서 복사
    description: <string>                   # required, frontmatter description 그대로
    tools: <list[string]>                   # optional, frontmatter tools (subagent만)
    skills_preloaded: <list[string]>        # optional, frontmatter skills (subagent만)

    # 사용자 overrides에서 받은 자유 필드
    custom: <map>                           # optional, .harness-config.yaml의 agents.overrides.<agent> 내용 (approved_by 제외)

    # 향후 확장 (PoC 에서 미사용)
    parallel_compatible_with: <list[string]>  # optional
    requires_after: <list[string]>            # optional
```

**install_kind 결정 알고리즘 (도구 구현 룰)**:
```
source path 가:
  - agents/isolation/<X>.md            → install_kind: subagent
  - agents/non-isolation/<X>.md        → install_kind: skill
  - agents/non-isolation/<X>/SKILL.md  → install_kind: skill
  - skills/<X>/SKILL.md                → install_kind: skill (의존성으로 자동 설치)
```

**예시 (frontend-agent 만 enabled)**:
```yaml
version: "1.0"
generated_at: "2026-05-24T14:32:00+09:00"
generated_by: "harness-gen v0.1.0"
agents:
  planner:
    install_kind: skill
    source: agents/non-isolation/planner/
    location: .claude/skills/planner/SKILL.md
    always_installed: true
    description: "사용자 작업 요청을 받으면 ... Use when ..."

  frontend-agent:
    install_kind: subagent
    source: agents/isolation/frontend-agent.md
    location: .claude/agents/frontend-agent.md
    description: "Frontend 구현 전담 Subagent (격리된 context)"
    tools: [Read, Write, Edit, Bash, Glob, Grep]
    skills_preloaded: [lint-checker]
    custom:
      framework: "angular@16"

  lint-checker:                            # frontend-agent 의존으로 자동 install
    install_kind: skill
    source: skills/lint-checker/SKILL.md
    location: .claude/skills/lint-checker/SKILL.md
    description: "..."
```

### 9.6.7 Agent 정의 파일 frontmatter 규격 ⭐

각 agent 템플릿 파일의 frontmatter는 **Claude Code 공식 사양만** 사용:

```markdown
---
name: frontend-agent
description: Frontend 구현 전담 Subagent (격리된 context)
tools: [Read, Write, Edit, Bash, Glob, Grep]
skills:                                  # Subagent 내부에서 호출 가능 (자동 preload)
  - lint-checker
---

# 본문 (LLM이 따를 행동 양식)
...
```

**MUST**:
- ✅ Claude Code 공식 frontmatter 필드만 사용: `name`, `description`, `tools`, `skills` 등
- ✅ `description` 은 "What. Use when ..." 패턴 권장 (트리거 키워드 포함)
- ✅ tech-agnostic 작성 (프레임워크/버전 단정 X — 그건 사용자 `.harness-config.yaml`에서)

**MUST NOT** (agent 정의 파일의 frontmatter에서):
- ❌ Claude Code 공식 사양 외 필드 추가 (예: `type`, `version`, `always_installed`)
  - 이런 메타는 harness-gen 의 manifest.yaml 이 담당 (도구가 install 시 채움)
- ❌ `{{변수}}` 치환 변수 사용 (Claude Code 미지원)
- ❌ "Angular 17+", "Vert.x 4.4" 등 버전/프레임워크 단정 (사용자 config가 결정)

**`.harness-config.yaml` 의 `agents.overrides.<agent>` 안 필드는 자유 허용**:
- 사용자가 `framework: "angular@16"` 같은 임의 필드 자유 추가 가능
- 이 값은 `.harness/agents/manifest.yaml` 의 해당 agent entry 에 `custom:` 키 아래로 들어감
  ```yaml
  agents:
    frontend-agent:
      install_kind: subagent
      ...
      custom:           # overrides 에서 받은 사용자 정의 필드
        framework: "angular@16"
  ```
- 실제로 agent 가 이 값을 어떻게 사용할지는 **CLAUDE.md 에 반영되어 LLM 이 인지** (즉 도구는 단순 전달만, frontmatter에 주입 X)

**병렬 판단 메타데이터 (옵션)**:
- 향후 필요해지면 agent 작성자가 frontmatter에 임의 필드 추가 가능 (예: `parallel_compatible_with`)
- 단, 그 필드의 의미와 planner 가 어떻게 사용할지는 **추가 시점에 명세** 필수
- 현 단계 PoC 에선 적지 않음 (단순 dispatch 부터 시작)

### 9.6.8 Plan 파일 구조 — `.harness/plan/{yyyymmdd-작업명}/`

```
.harness/plan/                           ← .gitignore 처리 (전체)
├── 20260524-payment-page/               ← {yyyymmdd-작업명}, 시간순 정렬
│   ├── plan.md                          ← 전체 워크플로우 (planner 작성)
│   ├── frontend-plan.md                 ← frontend-agent용 (planner 작성)
│   ├── backend-plan.md                  ← backend-agent용 (해당 시)
│   └── status.yaml                      ← pending | in_progress | done | failed | abandoned
├── 20260523-user-login-fix/
└── 20260520-refund-flow/
```

**라이프사이클 정책**:
- `.gitignore`에 `.harness/plan/` 추가 (전체 gitignore)
- 로컬엔 유지 (디버깅/재참조용)
- 팀 공유 X (각자 다름)
- 청소 명령: `harness-gen plan clean --older-than=30d --status=done` (수동, 자동 X)

**디렉터리 명명 규칙**:
- `yyyymmdd-{kebab-case-작업명}` (예: `20260524-payment-page`)
- 같은 날 같은 작업명 충돌 시: `20260524-payment-page-2`, `-3` ... suffix
- **작업명 추출 방식**: planner가 제안 → 사용자가 confirm/수정 (예: "20260524-payment-page 로 시작할게요. OK? (y/n/custom)")

#### `plan.md` 형식 (전체 워크플로우, 다중 agent 시)

```markdown
# 20260524-payment-system

## Workflow
1. [Implementation] frontend + backend 병렬 실행
2. [Verification] 통합 테스트
3. [Failure handling] 실패 시 해당 agent 재호출

## Shared Contract (다중 agent 시만 작성 — 단일 agent면 생략)
### API: POST /api/payment
- Request:  { amount: number, currency: "KRW" | "USD" }
- Response: { transactionId: string, status: "ok" | "failed" }

### Types
- `Payment` interface 정의 위치: shared/types/payment.ts

## Subagents to Execute (병렬 가능 여부는 9.6.10 planner 판단)
- frontend-plan.md
- backend-plan.md

## Execution Strategy (planner가 9.6.10 절차로 결정)
- Mode: parallel + contract-first
- Reason: frontend / backend 가 동일 API 인터페이스 공유 + 의존성 없음
```

#### `{role}-plan.md` 형식 (개별 agent용)

```markdown
# Frontend Plan

## Subagent
frontend-agent

## Preloaded Skills (이 subagent 내부에서 호출 가능)
- lint-checker
- angular-code-checker
- frontend-verify

## Shared Contract (READ ONLY — 다중 agent 시)
→ 반드시 ../plan.md의 "Shared Contract" 섹션 먼저 읽을 것

## Implementation Tasks
- [ ] PaymentForm 컴포넌트 (Shared Contract의 Request 타입 따름)
- [ ] POST /api/payment 호출 로직 (Shared Contract의 Response 타입 따름)

## Self-Verification (subagent 내부 수행)
- lint-checker 실행 → PASS 필요
- angular-code-checker 실행 → PASS 필요
- frontend-verify 실행 → PASS 필요

## Report to Main (요약만 메인에 반환)
- 구현 파일 목록
- 검증 결과 (PASS/FAIL 카운트)
- 발견한 이슈와 해결 방법 (1~2줄)
```

### 9.6.9 단일 vs 다중 Agent 시나리오

planner는 **설치된 agent 수에 따라 plan 구조를 동적으로 조정**한다:

| 시나리오 | plan.md 구조 | 병렬 실행 | Shared Contract 섹션 |
|---|---|---|---|
| **단일 agent** (frontend만 등) | 단순 | 불필요 | 생략 |
| **다중 agent + 독립** | 기본 | 가능 | 생략 또는 최소 |
| **다중 agent + 계약 공유** | Shared Contract 포함 | 가능 (병렬) | 필수 |
| **다중 agent + 의존성** | 순차 단계 명시 | 부분 가능 (DAG) | 필요 시 |

→ planner skill이 Section 9.6.10 알고리즘으로 동적 판단 (Karpathy 단순함 원칙).

### 9.6.10 Planner의 실행 모드 결정 (LLM 판단 우선, 메타 보강 가능)

PoC 단계에선 planner skill의 LLM 판단에 위임. 메타데이터 기반 결정은 **필요해지면 추후 추가** (Karpathy "필요해질 때 추가" 원칙).

```
[STEP 1] manifest.yaml 에서 enabled agent 목록 확인
   - 1개 → 단일 실행 모드 (Shared Contract 섹션 생략)
   - 2개 이상 → STEP 2로

[STEP 2] LLM 판단 (planner skill의 본문에 명시된 절차)
   - 의존성 있나? (선행 agent 필요한가)
     - 예: code-analyst 결과를 frontend가 사용 → 순차
   - 같은 인터페이스 공유하나? (API 계약 등)
     - 예: frontend ↔ backend API → 병렬 + Shared Contract
   - 완전 독립?
     - 자유 병렬
   - 판단 근거를 plan.md "Execution Strategy" 섹션에 명시

[STEP 3] 결정된 모드로 plan.md / *-plan.md 작성 후 dispatch
```

**판단 예시** (LLM 가이드용, 강제 룰 X):
| enabled | 일반적 결정 |
|---|---|
| `[frontend]` | 단일 실행 |
| `[frontend, backend]` (API 공유) | 병렬 + Contract-first |
| `[code-analyst, frontend]` | 순차 (분석 → 구현) |
| `[frontend, mobile]` (독립) | 자유 병렬 |

**향후 확장 (필요해지면)**:
- agent frontmatter에 `parallel_compatible_with`, `requires_after` 같은 메타 추가 가능
- 단, 추가 시점에 **planner skill 본문에 이 필드를 어떻게 사용하는지 명시 필수**
- 현 PoC 에선 미사용 (LLM 판단만으로 충분)

### 9.6.11 출처 (Bitbucket Single Source)

모든 agent / skill 템플릿은 **사내 Bitbucket harness 레포 하나**에서 옴:

```
bitbucket.company.com/harness/         ← 한 레포에 도구 + 자료 통합
├── cli/                                ← harness-gen Python CLI 코드
├── shared/                             ← 모든 template (rules + agents + skills)
│   ├── rules/
│   ├── patterns/
│   ├── ontology.yaml
│   ├── agents/
│   │   ├── isolation/
│   │   └── non-isolation/
│   ├── skills/
│   └── presets/
├── version.yaml                        ← 통합 버저닝 (cli + shared 동일 commit)
└── README.md
```

**운용 흐름**:
```
[GitHub 원본]                                      [Bitbucket 사내]
github.com/anthropics/.../harness                  bitbucket.company.com/harness
   │                                                       │
   │  1회 fork (seed)                                     │
   ├──────────────────────────────────────────────────────→│
   │                                                       │
   │  이후 수동 sync (검증 후)                              │
   └──────────────────────────────────────────────────────→│
                                                           │
                                                           │  generate
                                                           ├──→ 각 프로젝트
```

**핵심 특성**:
- ✅ GitHub 의존성 0 (초기 1회만)
- ✅ 사내 거버넌스 100% (외부 변경 자동 반영 X)
- ✅ 도구 ↔ 자료 버전 lock (한 commit)
- ✅ 사용자는 출처 적을 일 X (`.harness-config.yaml`에 이름만)

`.harness-config.yaml` 예시:
```yaml
registry: "bitbucket.company.com/harness.git"
imports:
  - shared@v1.2.0/rules/Rule_JWT
agents:
  subagents:
    - frontend-agent          # bitbucket harness 레포에서 자동 해결
```

---

## 10. AI 빌드 규칙 (이 도구 만들 AI에게)

### MUST
- ✅ Karpathy 원칙: 50줄로 가능하면 50줄로
- ✅ Pre-flight TBD 미정 시 사용자에게 질문
- ✅ `.harness/`는 항상 generate로 재생성 가능해야 함
- ✅ `.lock.yaml`은 재현성 보장 (generate 시 항상 갱신)
- ✅ Overrides 적용 시 approved_by 검증 (rules + agents 모두)
- ✅ 에러 메시지는 명확하고 actionable
- ✅ **Subagent / Skill 명확 분리** (Section 9.6) — Slash Command는 미사용
- ✅ **planner는 Skill로만 구현** (Subagent X, 항상 설치)
- ✅ **검증/도구는 모두 Skill** (메인 + Subagent 양쪽 호출 가능)
- ✅ **agent 인지는 Dual-Layer**: CLAUDE.md 요약 + `.harness/agents/manifest.yaml` 상세
- ✅ **Subagent는 구현 + 자기 검증, 최종 요약만 반환** (Anthropic 공식 권장)
- ✅ **plan 디렉터리는 `{yyyymmdd-작업명}` 형식**, .gitignore 처리
- ✅ **agent 커스텀은 overrides + local 둘 다 지원** (rules 패턴 일관)
- ✅ **모든 template은 Bitbucket harness 단일 레포에서** (GitHub은 seed only)
- ✅ **병렬 판단은 planner skill의 LLM 판단** (PoC). 메타데이터는 필요해질 때 추가 (Section 9.6.10)

### MUST NOT
- ❌ DB / 임베딩 / 벡터 검색 도입 (도구의 핵심 철학 위반)
- ❌ Example의 본문을 그래프에 복사 (경로만)
- ❌ Override를 자동 생성 (사람의 명시적 결정만)
- ❌ Imports를 "최신 자동 추적" 모드로 (버전 명시 강제)
- ❌ 200줄로 가능한 걸 200줄로 짜기
- ❌ `.harness/` 안의 파일을 사용자가 직접 편집하도록 유도
- ❌ **Subagent 안에서 Slash Command 호출 시도** (불가능, Claude Code 제약)
- ❌ **planner를 Subagent로 구현** (메인 자신은 Subagent 호출 X)
- ❌ **Subagent에서 다른 Subagent 호출** (Claude Code 공식 금지, nested 불가)
- ❌ **단일 agent 시나리오에 Shared Contract 강제** (불필요한 오버헤드)
- ❌ **GitHub에서 generate 시점에 자동 fetch** (사내 거버넌스 위반)
- ❌ **`.harness/plan/`을 자동 삭제** (디버깅 가치 손실)
- ❌ **agent 출처를 사용자가 매번 명시하도록 강요** (Bitbucket 단일 출처라 불필요)

### 모호한 경우
1. 기존 패턴 검색
2. 사용자에게 명확화 요청
3. 가정 후 진행 금지
4. 진행 보고 시 가정 명시

---

## 11. 도구 자체의 파일 구조

### 11.1 GitHub 개발 레포 (이 레포: `harness-sdk`)

도구 코드와 자료 seed가 한 레포에 같이 있음 (Q8 결정: 단일 레포):

```
harness-sdk/                          (GitHub 개발 레포, 또는 Bitbucket fork)
├── README.md
├── reference/                        ← 명세 + default seed (사람이 작성)
│   ├── harness-gen-build-spec.md
│   ├── harness-gen-quick-reference.md
│   ├── harness-gen-reference.md
│   └── shared/                       ← Bitbucket harness/shared 의 seed (Section 9.6.4)
│       ├── README.md
│       ├── agents/
│       │   ├── isolation/
│       │   └── non-isolation/
│       └── skills/
├── src/                              ← ⭐ 도구 코드 (Python CLI)
│   ├── cli/
│   │   ├── init.py
│   │   ├── generate.py
│   │   ├── verify.py
│   │   ├── update.py
│   │   ├── plan.py                   ← Section 4.5
│   │   └── context.py                ← Section 4.6
│   ├── resolver/
│   │   ├── imports.py
│   │   ├── overrides.py
│   │   └── merger.py
│   ├── synth/
│   │   ├── claude_md.py              ← CLAUDE.md 합성
│   │   └── manifest.py               ← .harness/agents/manifest.yaml 생성
│   ├── registry/
│   │   ├── fetcher.py                ← Bitbucket clone or PoC 시 reference/shared/ 사용
│   │   └── cache.py
│   ├── agent_installer/              ← Section 9.6 install 변환 룰
│   │   └── install.py
│   └── validators/
├── tests/
│   ├── unit/
│   └── integration/
├── templates/                        ← 도구 자체가 사용하는 템플릿 (config 등)
│   ├── config.yaml.tmpl
│   └── claude.md.tmpl
└── pyproject.toml
```

### 11.2 Bitbucket 운용 레포 (회사 사내, Q8 B-2)

GitHub `harness-sdk` 를 Bitbucket 으로 fork 한 후의 구조. 디렉터리는 GitHub과 동일하되 회사가 자료를 추가/수정:

```
bitbucket.company.com/harness/        (사내 단일 레포: cli + shared 통합)
├── reference/
│   └── shared/                       ← 회사가 추가/덮어쓰기 (이게 실제 source of truth)
├── src/                              ← 도구 코드 (회사가 수정 가능)
└── ...
```

**핵심 분리**:
- `src/` = 도구 코드 (플랫폼팀 관리)
- `reference/shared/` = 자료 (아키텍트팀 관리)
- 한 레포지만 책임 분리

### 11.3 fetcher 동작 (PoC vs 운용)

`src/registry/fetcher.py` 가 처리.

#### registry 설정별 동작

| 환경 | registry 설정 | 동작 |
|---|---|---|
| **PoC** (Bitbucket 셋업 전) | `registry: "local:reference/shared"` 또는 미설정 | 같은 레포의 `reference/shared/` 직접 사용 |
| **운용** | `registry: "bitbucket.company.com/harness.git"` | Bitbucket clone (`~/.harness-cache/`) → 안의 `reference/shared/` 디렉터리 fetch |

→ PoC에서 운용으로 전환 시 사용자 변경 사항은 `.harness-config.yaml` 의 `registry` 필드 한 줄뿐.

#### import syntax 파싱

`.harness-config.yaml` 의 `imports:` 항목 형식:
```
shared@<version>/<path>
```

파싱 룰:
- `shared@v1.2.0/rules/Rule_JWT` → `version=v1.2.0`, `path=rules/Rule_JWT`
- 정규식: `^shared@(?P<version>[^/]+)/(?P<path>.+)$`
- 파일 확장자는 자동 추가 (`.yaml` 우선, 없으면 `.md`)

#### PoC 모드 (`local:reference/shared`) 디테일

```
1. .harness-config.yaml 의 registry 가 "local:" prefix 로 시작 → PoC 모드
2. local: 뒤의 경로 (예: "reference/shared") 가 fetch source
3. shared@v1.2.0/rules/Rule_JWT 같은 import 의 version 부분은 무시 (warning 1회 출력)
4. path 부분을 source 디렉터리에서 직접 찾음
   → reference/shared/rules/Rule_JWT.yaml
5. 캐시 사용 안 함 (이미 local 이라 의미 없음)
```

#### 운용 모드 (Bitbucket) 디테일

```
1. .harness-config.yaml 의 registry 가 "bitbucket..." 또는 git URL
2. 캐시 경로: ~/.harness-cache/<repo-name>@<version>/
3. 캐시 미존재 시:
   - git clone --depth 1 --branch <version> <registry> ~/.harness-cache/<repo>@<version>/
   - 인증: ~/.netrc 또는 SSH key (사용자 OS 기본 설정 따름)
4. 캐시 존재 시:
   - .lock.yaml 의 commit hash 와 캐시의 HEAD 비교
   - 일치 → 캐시 사용
   - 불일치 → 캐시 삭제 후 재 clone
5. import path 해석: ~/.harness-cache/<repo>@<version>/reference/shared/<path>
6. 사내 프록시/SSL: 환경변수 HTTPS_PROXY, CURL_CA_BUNDLE 자연스럽게 사용 (도구가 별도 설정 X)
```

#### 캐시 무효화

| 트리거 | 동작 |
|---|---|
| `.lock.yaml` 의 commit hash 와 캐시 HEAD 불일치 | 캐시 삭제 → 재 clone |
| `harness-gen update --to=<버전>` 실행 | 새 버전 fetch (구버전 캐시는 유지) |
| 사용자가 수동으로 `~/.harness-cache/` 삭제 | 다음 generate 시 재 fetch |

자동 TTL 무효화는 **하지 않음** (Karpathy 단순함: 명시적 갱신만).

#### 인증 실패 시

- 친절한 에러 메시지 + 다음 안내:
  - `~/.netrc` 형식 예시
  - SSH key 등록 가이드 URL (사내 문서 링크는 init 시 받음)
- 절대 자동으로 비밀번호 묻지 X (CLI 환경)

---

## 12. 운용 흐름 (Operational Flow)

```
[Day -∞] 공유 레포 준비 (아키텍트팀)
   ↓
[Day -1] 도구 배포 (플랫폼팀)
   ↓
[Day 0]  $ harness-gen init        ← 공유 룰 참조 등록
   ↓
         config 편집
   ↓
         $ harness-gen generate    ← 공유 룰 실제 fetch
   ↓
         git commit
   ↓
[Day 1~] AI 코딩 일상 (Claude Code가 .harness/ 자동 로드)
   ↓
[Week N] 공유 룰 v1.3.0 출시
   ↓
         config의 version 갱신 + generate
   ↓
         git commit
```

**핵심**:
- 사용자는 `.harness-config.yaml` 하나만 작성
- 도구가 나머지 자동 처리
- `.harness/` 와 `.lock.yaml`은 항상 Git 커밋 (재현성)

---

## 13. 외부 참조

### 이 도구가 구현하는 사상의 원전
- **Karpathy CLAUDE.md (Forrest Chang 정리)**:
  https://github.com/forrestchang/andrej-karpathy-skills
- **Karpathy LLM Wiki 패턴 분석 (DAIR.AI)**:
  https://academy.dair.ai/blog/llm-knowledge-bases-karpathy
- **LLM Wiki ↔ GraphRAG 연결 (agentpedia)**:
  https://agentpedia.codes/blog/karpathy-llm-knowledge-bases
- **Graphify 참고 구현 (Tree-sitter 기반 KG)**:
  https://medium.com/data-science-in-your-pocket/andrej-karparthys-llm-wiki-codes-graphify-b73bec5d87ea
- **obsidian-wiki 프레임워크**:
  https://github.com/Ar9av/obsidian-wiki

### 대규모 참고 (영감)
- **Harness SDKG (엔터프라이즈 버전)**:
  https://www.harness.io/blog/knowledge-graph-rag
- **Harness AI 공식 페이지**:
  https://www.harness.io/products/harness-ai
- **Microsoft GraphRAG**:
  https://github.com/microsoft/graphrag
- **Anthropic MCP 공식**:
  https://modelcontextprotocol.io

### 비슷한 도구 (디자인 참고)
- **npm/yarn**: imports + lock 패턴 (package.json + package-lock.json)
- **Tailwind CSS**: config + override 패턴
- **Kustomize (Kubernetes)**: base + overlay 패턴
- **Maven**: dependency + parent POM 패턴

---

## 14. 빌드 순서 (AI를 위한 First Actions)

1. **Section 0.1의 미확정 TBD 2개**를 사용자에게 확인 (배포 방식, PoC 도메인)
2. 답변 받으면 Section 11의 디렉터리 구조 생성
3. 다음 순서로 구현 (각 단계 ≤ 100줄 변경):
   ```
   Stage 1: Schema 검증 (config 파싱)         — Section 5.1, 5.2
   Stage 2: Registry fetcher (PoC + 운용)     — Section 11.3
   Stage 3: `init` 명령                        — Section 4.1
   Stage 4: `generate` 명령 (resolver 구현)    — Section 4.2, 9.6
   Stage 5: `verify` 명령                      — Section 4.3
   Stage 6: `update` 명령                      — Section 4.4
   Stage 7: `plan` 명령 (plan list/show/clean) — Section 4.5
   Stage 8: `context` 명령 (SessionStart 훅용) — Section 4.6
   ```
4. 각 Stage 완료 후 사용자 확인
5. 테스트 작성 필수 (각 명령당 최소 1개 integration test)

---

## 15. 사상의 한 줄 요약

> **"이 도구는 Karpathy의 LLM Wiki 사상을 GraphRAG 구조로 컴파일하는 컴파일러다.
> Harness Inc.의 엔터프라이즈 아키텍처를 프로젝트 단위 스캐폴딩으로 축소한 형태."**

→ **Karpathy의 단순함 + GraphRAG의 정확성 + Harness의 실용성**

---

**Document Version**: v0.7 (재검수 HIGH 5건 추가 수정: harness-shared 잔재, Cursor 언급 제거, Stage 7/8 추가, Section 참조 정정, 버전 메타 동기화)
**Next Action**:
  1. Section 0.1 Pre-flight TBD 확정 (배포 방식, PoC 도메인)
  2. Section 14 First Actions 시작 (Stage 1~6 순차 구현)
**Decision Log** (grill-me 세션 결과):
  - Q1: Subagent / Skill 명확 분리 (Slash Command 미사용)
  - Q2: planner = 메인 자체, Skill로만 구현 (Subagent X)
  - Q3: Conductor Pattern — Subagent는 구현 + 자기 검증, 메인은 통합 흐름 통제
  - Q4: agent 선택 = subagents + tools 리스트, Dual-Layer (CLAUDE.md + manifest.yaml)
  - Q5: shared/agents/isolation/ + non-isolation/ + skills/ 분리 유지
  - Q6: 커스텀 = overrides + local 둘 다 (rules 패턴 일관)
  - Q7: plan = `{yyyymmdd-작업명}` + .gitignore + planner 제안/사용자 confirm
  - Q8: Bitbucket 단일 레포 (cli + shared 통합, GitHub은 seed only)
  - Q9: 병렬 판단 = planner skill의 LLM 판단 (PoC). 메타데이터 보강은 필요해질 때 (Section 9.6.10)
**Maintained by**: 첫 구축 후 운용 중 갱신
