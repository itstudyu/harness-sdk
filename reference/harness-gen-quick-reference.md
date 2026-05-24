# harness-gen 빠른 요약 (Quick Reference)

> **목적**: 구조 흐름과 유저가 정의해야 할 것을 한 번에 파악
> **상세 자료**: `harness-gen-build-spec.md`, `harness-gen-reference.md`

---

## 1. 전체 흐름 한 장 요약

```
[아키텍트팀]                  [플랫폼팀]                  [개발자]
     │                            │                          │
     ↓                            ↓                          ↓
공유 레지스트리                 도구 배포                  프로젝트 작업
(Bitbucket Server)             (pip install)                (각 레포)
     │                            │                          │
     │                            │                  ┌───────┴───────┐
     │                            │                  │               │
     │                            │           1. harness-gen init    │
     │                            │           2. config 편집          │
     │                            │           3. harness-gen generate │
     │                            │                  │               │
     └──────────── fetch ─────────┼──────────────────┘               │
                                  │                                  │
                                  └─→ 생성됨:                          │
                                      • CLAUDE.md (루트)              │
                                      • .claude/settings.json (훅) ⭐  │
                                      • .harness/ (상세 그래프)        │
                                           │                          │
                                           ↓                          │
                                   [Claude Code]                       │
                                   SessionStart 훅으로 강제 로드        │
                                   → 자연어 프롬프트로 코딩             │
```

**🎯 타겟 AI**: Claude Code 전용 (Cursor 등 호환 고려 X)
**🔒 컨텍스트 보장**: `.claude/settings.json` SessionStart 훅으로 무조건 로드

---

## 2. 누가, 무엇을 정의해야 하나

### 👔 A. 아키텍트팀 (공유 레지스트리 관리)

**1회성 셋업** + **지속 관리**:

```
bitbucket.company.com/harness/   # 단일 레포 (cli + shared 통합)
├── ontology.yaml              ⭐ 회사 표준 노드 타입 정의
├── rules/                     ⭐ 회사 표준 룰
│   ├── Rule_JWT.yaml
│   ├── Rule_ErrorFormat.yaml
│   ├── Rule_Logging.yaml
│   └── ...
├── patterns/                  ⭐ 표준 코드 패턴
│   ├── Pattern_JWT_Java.yaml
│   ├── Pattern_ErrorResponse_Java.yaml
│   └── ...
├── presets/                   ⭐ 스택별 추천 번들
│   ├── java-vertx.yaml          ← "Java/Vert.x는 이 룰들 권장"
│   ├── python-fastapi.yaml
│   └── ...
└── Git tags: v1.0.0, v1.1.0...  ⭐ 버저닝
```

**정의 책임**:
- [ ] 회사 표준 룰 목록 (몇 개로 시작?)
- [ ] 룰별 severity (MUST / SHOULD / MAY)
- [ ] 표준 코드 패턴 (스택별)
- [ ] 스택별 권장 preset
- [ ] 버전 릴리즈 정책

---

### 🛠️ B. 플랫폼팀 (도구 배포/운영)

**1회성**:
- [ ] harness-gen 도구 구축 (Python)
- [ ] 사내 PyPI 미러에 배포 (또는 zipapp 단일 파일)
- [ ] Bitbucket Server 인증 가이드 (SSH key / Personal Access Token)
- [ ] 사내 프록시 / SSL 설정 가이드

**지속 관리**:
- [ ] 도구 버전 업그레이드 (분기 1회)
- [ ] 사용자 이슈 대응

---

### 👨‍💻 C. 개발자 (각 프로젝트에서)

**프로젝트당 1회**:

```bash
# 1. 도구로 초기화
$ harness-gen init --stack=java-vertx --domain=payment

# 2. 생성된 .harness-config.yaml 편집 ⬇
```

**`.harness-config.yaml`에서 정의할 것**:

```yaml
version: "1.0"

# 필수 4개
domain: "payment"              ⭐ 도메인 (자유 텍스트)
stack: "java-vertx"            ⭐ 스택 (preset 식별용)
registry: "bitbucket.company.com/harness.git"   ⭐ 레지스트리 위치

# imports: 공유에서 가져올 룰/패턴 (preset이 기본값 채워줌)
imports:
  - shared@v1.2.0/rules/Rule_JWT
  - shared@v1.2.0/rules/Rule_ErrorFormat
  - shared@v1.2.0/patterns/Pattern_JWT_Java
  - shared@v1.2.0/ontology.yaml

# overrides: 공유 룰의 부분 수정 (필요할 때만)
overrides:
  Rule_JWT:
    exceptions: ["/payment/webhook"]      # ⭐ 예외 추가
    approved_by: "@architect-kim"         # ⭐ 승인자 명시 (필수)
    approved_at: "2026-05-21"

# local: 이 프로젝트 전용 룰/패턴 (필요할 때만)
local:
  rules:
    - rules/Rule_RefundTimeLimit.yaml     # ⭐ 프로젝트 고유 룰
  patterns:
    - patterns/Pattern_RefundFlow.yaml

# 🆕 agents: 사용할 agent 선택 (Section 7 참고, rules 패턴 일관)
agents:
  # planner는 항상 자동 설치 (명시 불필요)

  subagents:                # ⭐ isolation/에서 옴 (Subagent로 설치)
    - frontend-agent
    # - backend-agent       # 미선택 시 설치 X

  tools:                    # ⭐ non-isolation/에서 옴 (Skill로 설치)
    - code-analyst

  overrides:                # rules의 overrides와 동일 패턴
    frontend-agent:
      framework: "angular@16"
      approved_by: "@kim"
      approved_at: "2026-05-24"

  local:                    # rules의 local과 동일 패턴
    - local/agents/mobile-agent.md
```

**정의해야 할 핵심 4가지**:

| 항목 | 무엇 | 빈도 |
|---|---|---|
| `domain` | 어떤 도메인 (payment, user, order...) | 1회 |
| `stack` | 어떤 기술 스택 (java-vertx 등) | 1회 |
| `imports` | 어떤 공유 룰 적용 | 1회 + 버전 업데이트 시 |
| `local` | 프로젝트 고유 룰 (필요시) | 발생 시 추가 |

**선택 항목**:
- `overrides`: 공유 룰의 예외 케이스 (승인 필수)

---

## 3. 빠른 시작 체크리스트

### Phase 0: 사전 준비 (회사 차원, 1회)
- [ ] 아키텍트팀: 공유 레지스트리 초기 룰 5~10개 정의
- [ ] 플랫폼팀: harness-gen 도구 배포
- [ ] Bitbucket Server 접근 권한 정리 (읽기/쓰기)

### Phase 1: 개발자 첫 사용 (프로젝트당 1회)
- [ ] 도구 설치: `pip install harness-gen`
- [ ] 프로젝트 디렉터리에서: `harness-gen init`
- [ ] `.harness-config.yaml` 편집 (domain, stack, imports 확인)
- [ ] `harness-gen generate` 실행
- [ ] `.harness/` 디렉터리 생성 확인
- [ ] Claude Code 실행하면 자동 인식

### Phase 2: 일상 사용 (개발 중)
- [ ] 새 룰 추가 필요? → `local`에 추가 후 `generate`
- [ ] 회사 룰 업그레이드 알림? → `imports`의 버전 수정 후 `generate`
- [ ] PR 올릴 때: CI에서 `harness-gen verify` 자동 실행

---

## 4. 가장 자주 묻는 질문

### Q. `.harness/` 안의 파일을 직접 편집해도 되나?
**A. NO.** 항상 `generate`로만 갱신. 직접 편집은 `.harness-config.yaml`에서만.

### Q. 공유 룰을 안 가져오고 싶으면?
**A.** `.harness-config.yaml`의 `imports`를 비우면 됨. 단, 회사 표준 미적용 = 비추.

### Q. `imports` / `overrides` / `local` 차이?
- **imports**: 공유에서 그대로 가져옴
- **overrides**: 가져온 것의 일부 수정 (예외 추가 등)
- **local**: 이 프로젝트만의 룰 (공유에 없음)

### Q. `.harness/` 디렉터리는 Git에 커밋?
**A. YES.** `.harness/`와 `.lock.yaml`은 항상 커밋. 캐시(`~/.harness-cache/`)만 gitignore.

---

## 5. 정의 우선순위 (어디부터?)

만약 모든 걸 한 번에 못 한다면:

```
1순위: 공유 레지스트리에 룰 3~5개 (가장 중요한 보안/표준)
   예: Rule_JWT, Rule_ErrorFormat, Rule_Logging

2순위: 그 룰들의 Pattern (Java/Vert.x용)
   예: Pattern_JWT_Java, Pattern_ErrorResponse_Java

3순위: java-vertx preset 만들기
   → init이 자동으로 이 룰들 추천하게 됨

4순위: 1개 프로젝트에 PoC 적용
   → 효과 검증 후 확대
```

→ **최소한의 5개 룰 + 1개 preset**으로 시작 가능. 한 달 안에 PoC 검증.

---

## 6. 핵심 요약 (한 줄씩)

- **흐름**: 아키텍트가 룰 정의 → 도구가 fetch → 개발자가 generate → AI가 활용
- **개발자가 정의**: domain, stack, imports, (overrides), (local), **agents**
- **아키텍트가 정의**: 회사 표준 룰/패턴/preset/ontology
- **플랫폼팀이 정의**: 도구 배포 방식, Bitbucket 인증
- **시작점**: 공유 룰 5개 + java-vertx preset 1개 = PoC 가능

---

## 7. 🆕 Multi-Agent 요약 (자세한 내용: build-spec.md Section 9.6)

### 7.1 2가지 호출 메커니즘 (Slash Command 미사용, Skill로 통일)

| 종류 | Context | 호출 주체 | 용도 |
|---|---|---|---|
| **Subagent** (`.claude/agents/*.md`) | **분리** | 메인이 `Task()` 호출 | 큰 작업 위임 (frontend 구현 전체) |
| **Skill** (`.claude/skills/*/SKILL.md`) | **공유** | 메인이 자동/명시적 호출, Subagent는 frontmatter `skills:` preload 시 가능 | planner, tools, 검증 도구 모두 |

⚠️ **기술적 제약**:
- Slash Command는 Subagent 내부 호출 불가 → 모두 Skill로 통일
- Subagent가 다른 Subagent 호출 불가 (nested 금지)
- Subagent에서 Skill 호출하려면 frontmatter `skills:` 에 명시 필요

### 7.2 shared 안의 agent 분류 (사용자 멘탈 모델)

```
shared/agents/                   (Bitbucket harness/shared 또는 reference/shared/)
├── isolation/                   → Subagent로 설치됨 (.claude/agents/)
│   ├── frontend-agent.md
│   └── backend-agent.md
└── non-isolation/               → Skill로 설치됨 (.claude/skills/)
    ├── code-analyst.md
    └── planner/                 ⭐ 항상 설치 (폴더 형식, templates/ 포함)
        ├── SKILL.md
        └── templates/
            ├── plan-single.md.tmpl
            ├── plan-multi.md.tmpl
            ├── role-plan.md.tmpl
            └── status.yaml.tmpl

shared/skills/                   → 재사용 도구
└── lint-checker/                (default seed. 회사가 angular-code-checker 등 추가 가능)
    └── SKILL.md
```

→ 사용자는 "agent"라는 단일 개념으로 생각, 도구가 적절한 메커니즘으로 자동 변환.
→ default seed 는 tech-agnostic. 프레임워크 특화 skill 은 회사가 추가.

### 7.3 Conductor Pattern (planner = 메인)

```
사용자
  ↓
메인 Claude (= planner skill로 동작, 항상 설치)
  │  - .harness/plan/{yyyymmdd-작업명}/plan.md 작성
  │  - 의존성/병렬 가능성 판단 (frontmatter 메타데이터 + LLM)
  │
  ├─→ Task(frontend-agent) ── 분리 context ──→ 구현 + 자기 검증 (preload skill)
  ├─→ Task(backend-agent)  ── 분리 context ──→ 구현 + 자기 검증
  │   (병렬 가능 시 동시 dispatch)
  │
  └─ 최종 요약만 메인에 반환 (Anthropic 공식 권장)
     ↓
     통합 검증 실패 시 → 해당 Subagent 재호출하여 수정
```

### 7.4 사용자 선택 (rules 패턴과 일관)

```yaml
agents:
  # planner는 항상 자동 설치 (명시 불필요)

  subagents:                       # isolation/에서 옴
    - frontend-agent

  tools:                           # non-isolation/에서 옴
    - code-analyst

  overrides:                       # rules의 overrides와 동일 패턴
    frontend-agent:
      framework: "angular@16"
      approved_by: "@kim"
      approved_at: "2026-05-24"

  local:                           # rules의 local과 동일 패턴
    - local/agents/mobile-agent.md
```

### 7.5 Plan 디렉터리 (`{yyyymmdd-작업명}` + .gitignore)

```
.harness/plan/                    ← .gitignore (전체)
├── 20260524-payment-page/        ← {yyyymmdd-작업명} = 시간순 자동 정렬
│   ├── plan.md                   ← 전체 워크플로우
│   ├── frontend-plan.md          ← frontend-agent용
│   └── status.yaml               ← pending|in_progress|done|failed|abandoned
└── 20260523-user-login-fix/
```

- 작업명: planner가 제안 → 사용자가 confirm/수정
- 라이프사이클: gitignore + 로컬 유지 (디버깅용)
- 청소: `harness-gen plan clean --older-than=30d` (수동)

### 7.6 단일 vs 다중 Agent (planner 동적 판단)

| 시나리오 | plan.md 구조 | 병렬 | Shared Contract |
|---|---|---|---|
| **단일** (frontend만 등) | 단순 | 불필요 | 생략 |
| **다중 + 독립** | 기본 | 가능 | 생략 또는 최소 |
| **다중 + 계약 공유** | Shared Contract 포함 | 가능 | 필수 |
| **다중 + 의존성** | 순차 단계 명시 | 부분 (DAG) | 필요 시 |

**판단 절차** (PoC):
1. enabled agent 수 확인 (1개 → 단일 모드 종료)
2. agent 2개 이상 → planner skill 의 LLM 판단:
   - 의존성 있나? (선행 agent 필요)
   - 같은 인터페이스 공유?
   - 완전 독립?
3. 결정 근거를 plan.md "Execution Strategy" 섹션에 명시
4. 향후 필요해지면 agent frontmatter에 메타 추가 가능 (예: `parallel_compatible_with`) — 단, 추가 시 planner 본문에 사용법 명세 필수

### 7.7 출처 (Bitbucket Single Source)

```
[GitHub 원본] ──── 1회 fork ────→ [Bitbucket 사내] ──── generate ────→ [각 프로젝트]
                  + 수동 sync
```

- 도구(`src/`) + 자료(`reference/shared/`)가 **한 레포에 통합** (GitHub harness-sdk → Bitbucket harness)
- GitHub 의존성 0 (초기 seed만)
- 사내 거버넌스 100% (외부 변경 자동 반영 X)
- 사용자는 출처 명시 X (`.harness-config.yaml`에 이름만)
- **PoC 단계**: `registry: "local:reference/shared"` 로 Bitbucket 없이 곧바로 사용 가능

---

**Document Version**: v0.5 (Cursor 잔재 제거, harness-shared 명칭 통일, build-spec 버전 동기화)
**Companion**:
- `AI-HANDOFF.md` v0.1 (AI 첫 인계서 — 가장 먼저 읽을 것)
- `harness-gen-build-spec.md` v0.7 (상세 구현 명세)
- `harness-gen-reference.md` (사상적 기반, 변경 없음)
- `reference/shared/` (default 템플릿 seed, README 참조)
