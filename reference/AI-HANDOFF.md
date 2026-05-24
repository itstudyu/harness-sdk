# AI Handoff — harness-gen 구현 인계서

> **이 문서는 harness-gen CLI 도구를 처음부터 구현할 AI에게 전달하는 인계서입니다.**
> 다른 자료는 모두 이 문서에서 참조하는 보조 자료. 먼저 이 파일을 끝까지 읽으세요.

---

## 0. 한 줄 미션

당신은 **harness-gen** 이라는 multi-agent 오케스트레이션 CLI 도구를 Python 으로 처음부터 구현합니다.

- 구현 위치: `/Users/yu_s/Documents/GitHub/harness-sdk/src/` (Python CLI)
- 도구가 만들 결과물: 사용자 프로젝트의 `CLAUDE.md`, `.claude/`, `.harness/` 디렉터리

---

## 1. 인계 자료 목록 (이 디렉터리에 모든 것이 있음)

```
/Users/yu_s/Documents/GitHub/harness-sdk/reference/
├── AI-HANDOFF.md                    ← 이 파일 (출발점)
├── harness-gen-reference.md         ← 사상적 기반 (왜 이렇게 만드는가)
├── harness-gen-build-spec.md        ← 구체 명세 (무엇/어떻게), v0.7
├── harness-gen-quick-reference.md   ← 빠른 요약, v0.5
└── shared/                          ← default 템플릿 seed
    ├── README.md                    ← shared/ 정체 설명 (반드시 읽기)
    ├── agents/isolation/            ← Subagent로 install 되는 agent 정의
    │   ├── frontend-agent.md
    │   └── backend-agent.md
    └── agents/non-isolation/        ← Skill로 install 되는 agent 정의
        ├── code-analyst.md
        └── planner/
            ├── SKILL.md             ← planner skill (메인 행동 양식)
            └── templates/           ← plan.md, role-plan.md 등 템플릿
    └── skills/lint-checker/SKILL.md ← 재사용 도구 skill
```

---

## 2. 첫 행동 (이 순서 그대로)

### Step 1: 모든 자료 정독

```
1. AI-HANDOFF.md (이 파일) 전체 — 이미 읽고 있음
2. harness-gen-reference.md 전체 — 사상 이해
3. harness-gen-quick-reference.md 전체 — 전체 그림
4. harness-gen-build-spec.md 전체 — 구체 명세
5. shared/README.md 전체 — seed 정체
6. shared/ 디렉터리의 모든 파일 (참고용)
```

**가정 후 진행 금지.** 모르는 게 있으면 사용자에게 물을 것 (Karpathy 원칙).

### Step 2: Pre-flight TBD 2개 확정 (build-spec.md Section 0.1)

다음 2개를 사용자에게 물어보세요 (이게 첫 메시지):

```
명세 잘 받았습니다. 시작하기 전 2가지 확정이 필요합니다:

1. 배포 방식 — pip + git URL (PoC) 로 시작할까요, 사내 PyPI 미러로 갈까요?
   추천: pip + git URL (PoC 단순화)

2. 첫 PoC 도메인 — payment / user / 다른 것 중 어디로?
   추천: payment (이미 build-spec 예시들에 자주 등장)
```

### Step 3: Stage 1 ~ 6 순차 구현

build-spec.md Section 14 "First Actions" 의 Stage 순서 그대로 진행. 각 Stage 완료 후 사용자 확인 받을 것.

```
Stage 1: Schema 검증 (config 파싱)        — Section 5.1, 5.2 참조
Stage 2: Registry fetcher (PoC + 운용)    — Section 11.3 참조
Stage 3: `init` 명령                       — Section 4.1 참조
Stage 4: `generate` 명령 (resolver, 가장 큰 단계)  — Section 4.2, 9.6 참조
Stage 5: `verify` 명령                     — Section 4.3 참조
Stage 6: `update` 명령                     — Section 4.4 참조

(추가) Stage 7: `plan` 명령                 — Section 4.5 참조
(추가) Stage 8: `context` 명령              — Section 4.6 참조
```

---

## 3. 핵심 원칙 (이 도구 만드는 동안 반드시)

build-spec.md Section 10 "MUST / MUST NOT" 전체 준수. 핵심 발췌:

### MUST
- ✅ Karpathy 원칙: 50줄로 가능하면 50줄로
- ✅ 모호하면 가정 후 진행 X — 사용자에게 물어볼 것
- ✅ 각 Stage 완료 후 사용자 확인 (한 번에 다 만들지 마라)
- ✅ Subagent / Skill 명확 분리 (Slash Command 미사용)
- ✅ planner는 Skill로만 (Subagent X)
- ✅ tech-agnostic (특정 프레임워크 단정 X)
- ✅ Bitbucket 단일 레포 + GitHub seed only

### MUST NOT
- ❌ DB / 임베딩 / 벡터 검색 도입
- ❌ 200줄로 가능한 걸 200줄로 짜기
- ❌ `.harness/` 안의 파일을 사용자가 직접 편집하도록 유도
- ❌ Subagent 안에서 Slash Command 호출 시도
- ❌ planner를 Subagent로 구현
- ❌ Subagent에서 다른 Subagent 호출 (nested 불가)
- ❌ agent 정의 파일에 `{{변수}}` 치환 변수 (Claude Code 미지원)
- ❌ 회사가 정해야 할 tech 정보 (framework, version) 를 default seed 에 단정

---

## 4. 자주 헷갈리는 지점 (선제 안내)

### 4.1 "agent" 라는 단어
- 사용자/팀 입장: `agent` (isolation 여부로 구분)
- Claude Code 입장: `Subagent` (분리 context) vs `Skill` (공유 context)
- harness-gen 도구가 path 보고 자동 변환:
  - `shared/agents/isolation/X.md` → Subagent (`.claude/agents/X.md`)
  - `shared/agents/non-isolation/X.md` 또는 `X/SKILL.md` → Skill (`.claude/skills/X/SKILL.md`)

### 4.2 planner 의 특수성
- 항상 설치 (사용자 선택 불가)
- 메인 Claude 의 행동 양식 (Subagent X, Skill 로 구현)
- `agents/non-isolation/planner/` 폴더 구조 (SKILL.md + templates/ 포함)
- 도구가 install 시 `templates/` 도 함께 복사 필수

### 4.3 fetcher 동작 (PoC vs 운용)
- `registry: "local:reference/shared"` → PoC, 같은 레포 내 직접 사용
- `registry: "bitbucket..."` → clone to `~/.harness-cache/`
- 자세한 룰: build-spec.md Section 11.3

### 4.4 `framework` 같은 사용자 정의 필드
- agent 정의 파일 frontmatter 엔 **금지** (Claude Code 공식 사양만)
- `.harness-config.yaml` 의 `agents.overrides.<agent>` 안에서는 **자유**
- 도구는 그 값을 `manifest.yaml` 의 `custom:` 키 아래로 옮김
- agent 본문은 이 값을 모름 → CLAUDE.md 통해 LLM 이 알게 됨

### 4.5 manifest.yaml 정확한 schema
- build-spec.md Section 9.6.6 의 "manifest.yaml 정식 schema" 표
- `install_kind`, `source`, `location` 은 도구가 자동 채움
- `description`, `tools`, `skills_preloaded` 는 frontmatter 에서 복사
- `custom` 은 사용자 overrides 에서

---

## 5. 구현 진행 룰

### 5.1 단계별 진행

각 Stage 완료 시:
1. 사용자에게 "Stage N 완료. 확인해주세요." 보고
2. 사용자 OK 받기 전 다음 Stage 진행 X
3. 진행 중 모호한 점 발견 → 즉시 stop + 사용자에게 질문

### 5.2 코드 작성 시

- Python 3.11+ 가정
- 타입 힌트 사용
- 한 함수 50줄 이내 권장 (Karpathy)
- 한 파일 단일 책임
- 외부 의존성 최소화 (PyYAML, click 정도)

### 5.3 테스트

- 각 명령마다 integration test 1개 이상 필수
- PoC 모드 (`local:reference/shared`) 로 테스트 가능
- 테스트 위치: `tests/integration/test_<command>.py`

### 5.4 디렉터리 구조

```
harness-sdk/
├── reference/           ← 이미 존재 (수정 X)
├── src/                 ← 당신이 만들 곳
│   ├── cli/
│   ├── resolver/
│   ├── synth/
│   ├── registry/
│   ├── agent_installer/
│   └── validators/
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml       ← 당신이 만듦
└── README.md            ← 당신이 만듦
```

---

## 6. 진행 보고 형식

각 Stage 완료 후:

```markdown
## Stage N 완료 보고

### 구현 내용
- <어떤 파일을 만들었는지>
- <주요 결정 사항>

### 가정한 부분 (있다면)
- <명세에 없어서 추측한 부분>

### 테스트
- <어떤 테스트를 만들었고 통과했는지>

### 다음 Stage 시작 OK?
```

---

## 7. 문제 발생 시 우선순위

1. **명세에서 답을 찾을 수 있는가?** → 명세 다시 읽기
2. **shared/ seed 의 실제 파일에서 답을 찾을 수 있는가?** → seed 정독
3. **둘 다 모호한가?** → 사용자에게 질문 (가정 후 진행 금지)
4. **사상이 충돌하는가?** → reference.md Section 8 우선순위 표 적용
   - 1순위: Karpathy 단순함
   - 2순위: GraphRAG 결정성
   - 3순위: LLM Wiki 가독성
   - 4순위: Harness 실용성

---

## 8. 첫 메시지 템플릿

이 인계서 정독이 끝나면 사용자에게 다음 메시지부터 시작:

```
명세 잘 받았습니다.

확인한 자료:
- AI-HANDOFF.md ✓
- harness-gen-reference.md ✓
- harness-gen-build-spec.md (v0.7) ✓
- harness-gen-quick-reference.md (v0.5) ✓
- shared/ 전체 ✓

시작하기 전 Pre-flight TBD 2개 확정 부탁드립니다:

1. 배포 방식 — pip + git URL (PoC) / 사내 PyPI 미러 / 다른 방식?
   추천: pip + git URL (PoC 단순화)

2. 첫 PoC 도메인 — payment / user / 다른 도메인?
   추천: payment (예시 다수 등장)

답변 주시면 Stage 1 (Schema 검증) 부터 시작하겠습니다.
```

---

## 9. 기억해야 할 핵심 한 줄

> **"이 도구는 Karpathy의 LLM Wiki 사상을 GraphRAG 구조로 컴파일하는 컴파일러다.
> 도구 자체도 그 사상 (단순함, 명시성, 결정성, 가독성) 을 따른다."**

복잡함이 정당화될 때만 복잡하게. 의심스러우면 단순하게. 모르면 묻기.

---

**Document Version**: v0.1 (첫 인계 버전)
**Companion Documents**:
- `harness-gen-reference.md` (사상)
- `harness-gen-build-spec.md` v0.7 (구현 명세)
- `harness-gen-quick-reference.md` v0.5 (빠른 요약)
- `shared/README.md` (seed 정체)
