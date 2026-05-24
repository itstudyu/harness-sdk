---
name: planner
description: 사용자 작업 요청을 받으면 먼저 요청을 명확화(애매하면 한 번에 하나씩 질문), 그 다음 작업명 추출, 실행 모드 결정, plan 디렉터리 생성, Subagent 위임을 수행. Use when 사용자가 새 작업/기능/버그 수정을 요청할 때, "계획 세워줘", "작업 시작" 같은 표현을 쓸 때.
---

# Planner Skill

요청이 애매하면 가정 후 진행 X. 한 번에 하나씩 물어볼 것.
직접 구현 X — plan 만들고 적절한 Subagent에 위임.

## Step 0: 명확화 (가장 중요)

다음이 명확한지 자문:
- 무엇을 만들/수정?
- 어디에 위치? (신규/기존, URL, 폴더)
- 누가 사용? (유저/관리자/내부)
- 기존 코드와 어떻게 연계?
- 성공/실패 기준?
- 어떤 agent 필요?

애매하면 한 번에 하나씩 질문. 추천 답변 제시. 코드에서 답 찾을 수 있으면 `Read`/`Grep`/`Glob`으로 직접 찾기.
모두 명확해질 때까지 Step 1로 진행 금지.

## Step 1: 작업명 confirm

- 핵심 키워드 + 오늘 날짜(YYYYMMDD) → 슬러그 생성
- 예: "결제 페이지 만들어줘" → `20260524-payment-page`
- 사용자에게 `y/n/custom` 확인
- 중복 디렉터리 존재 시 → `-2`, `-3` suffix 자동

## Step 2: enabled agent 파악

```
Read .harness/agents/manifest.yaml
```

## Step 3: 실행 모드 결정

- agent 1개 → 단일 모드
- agent 2개 이상:
  - 각 agent frontmatter의 메타 확인 (의존성, 인터페이스 공유)
  - 의존성 있음 → 순차
  - 인터페이스 공유 → 병렬 + Shared Contract
  - 완전 독립 → 자유 병렬
  - 메타로 결정 불가 → LLM 판단 + 근거를 plan.md에 명시

## Step 4: plan 디렉터리 생성

작업 디렉터리: `.harness/plan/{yyyymmdd-작업명}/`

다음 템플릿을 Read해서 변수 치환 후 Write:

| 파일 | 템플릿 (이 skill 디렉터리 기준) |
|---|---|
| `plan.md` (단일 agent) | `templates/plan-single.md.tmpl` |
| `plan.md` (다중 agent) | `templates/plan-multi.md.tmpl` |
| `{role}-plan.md` | `templates/role-plan.md.tmpl` |
| `status.yaml` | `templates/status.yaml.tmpl` |

템플릿 변수는 `{{var_name}}` 형식. 본인이 치환 후 Write.

### 변수 매핑 표

| 변수 | 값 출처 | 예시 |
|---|---|---|
| `{{task_slug}}` | Step 1 에서 확정된 슬러그 | `20260524-payment-page` |
| `{{agent_name}}` | 단일 모드: 그 agent 이름 | `frontend-agent` |
| `{{agent_list}}` | 다중 모드: comma list | `frontend-agent, backend-agent` |
| `{{role}}` | role-plan 의 짧은 이름 | `frontend`, `backend` |
| `{{role_title}}` | role 의 Title Case | `Frontend`, `Backend` |
| `{{mode}}` | Step 3 결정 모드 | `단일` / `순차` / `병렬` / `병렬+contract-first` |
| `{{reason}}` | Step 3 판단 근거 (LLM 작성) | `frontend/backend 가 동일 API 공유` |
| `{{started_at_iso}}` | 현재 시각 ISO 8601 | `2026-05-24T14:32:00+09:00` |
| `{{preloaded_skills_list}}` | manifest 의 `skills_preloaded` (markdown list) | `- lint-checker` |
| `{{tasks_checklist}}` | 사용자 요청 기반 LLM 작성 | `- [ ] PaymentForm 컴포넌트` |
| `{{verification_steps}}` | preloaded skill 목록을 verification 형태로 | `- lint-checker → PASS 필요` |
| `{{subagent_plan_list}}` | 호출할 *-plan.md 파일 목록 | `- frontend-plan.md` |
| `{{agents_yaml_list}}` | status.yaml용 yaml list | `  - frontend-agent` |
| `{{shared_contract_or_empty}}` | 다중+공유 시 작성, 아니면 빈 문자열 | (template 주석 참조) |
| `{{shared_contract_ref_or_empty}}` | role-plan용 reference 문구, 아니면 빈 문자열 | (template 주석 참조) |
| `{{dependencies_or_empty}}` | 의존성 설명, 없으면 빈 문자열 | `frontend ↔ backend: 독립` |
| `{{notes_or_empty}}` | 추가 메모, 없으면 빈 문자열 | (자유) |

## Step 5: Dispatch

- 병렬 가능 → 한 메시지에 여러 `Task(subagent_type=..., prompt="...")` 호출
- 순차 → 한 번에 하나씩
- prompt에는 해당 `*-plan.md` 경로 명시

## Step 6: 결과 통합 + 실패 처리

- 각 subagent 결과 = 요약만 (디테일 X)
- 다중 agent 시 통합 검증: Shared Contract 위반, 파일 충돌 확인
- 실패 시 → 해당 agent만 재호출 (최대 3회) → 그래도 실패 → status: abandoned
- status.yaml 갱신 (done | failed | abandoned)

## Step 7: 사용자 보고

요약만. 디테일은 `.harness/plan/{slug}/` 가리킴.

## 금지 사항

- 애매한 요청을 가정으로 메우고 진행
- 한 번에 여러 질문하기
- 메인이 직접 구현 시도 (반드시 Subagent에 위임)
- 단일 agent에 Shared Contract 강제
- enabled 아닌 agent 호출
- Subagent의 중간 로그를 사용자에게 노출
