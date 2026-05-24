# reference/shared/ — Bitbucket harness/shared seed

## 이 디렉터리의 정체

이 디렉터리는 사내 Bitbucket `harness/shared` 레포에 들어갈 **default 템플릿의 seed(원본 예시)** 입니다.

- 위치: `harness-sdk/reference/shared/`
- 역할: 아키텍트팀이 Bitbucket에 첫 push 할 default 자료의 1차 자료
- 운용 후엔 Bitbucket이 source of truth, 이 디렉터리는 reference 용도로 유지

## AI 구현자에게

이 도구(harness-gen)를 구축할 때:

1. **PoC 단계** (Bitbucket 셋업 전):
   - `harness-gen generate` 가 fetch할 곳이 없음
   - → 이 디렉터리 (`reference/shared/`)를 직접 사용해도 됨
   - 즉 PoC fetcher는 "Bitbucket URL이 비어있거나 local: prefix면 reference/shared/ 사용" 으로 구현 가능

2. **운용 단계** (Bitbucket 셋업 후):
   - 이 디렉터리 내용을 Bitbucket `harness/shared` 에 푸시
   - `.harness-config.yaml` 의 `registry: bitbucket.company.com/harness.git` 사용
   - 이 디렉터리는 backup / reference로만 유지

## 디렉터리 구조

```
reference/shared/
├── agents/
│   ├── isolation/                    Subagent로 설치되는 agent
│   │   ├── frontend-agent.md
│   │   └── backend-agent.md
│   └── non-isolation/                Skill로 설치되는 agent
│       ├── code-analyst.md
│       └── planner/                  ⭐ 폴더 형식 (templates/ 분리)
│           ├── SKILL.md
│           └── templates/
│               ├── plan-single.md.tmpl
│               ├── plan-multi.md.tmpl
│               ├── role-plan.md.tmpl
│               └── status.yaml.tmpl
└── skills/                           재사용 도구 (검증 등)
    └── lint-checker/
        └── SKILL.md
```

## Install 변환 룰 (도구가 generate 시 수행)

| Source (reference/shared/) | Target (사용자 프로젝트) | Claude Code 메커니즘 |
|---|---|---|
| `agents/isolation/<X>.md` | `.claude/agents/<X>.md` | Subagent |
| `agents/non-isolation/<X>.md` | `.claude/skills/<X>/SKILL.md` | Skill |
| `agents/non-isolation/planner/SKILL.md` | `.claude/skills/planner/SKILL.md` | Skill |
| `agents/non-isolation/planner/templates/*` | `.claude/skills/planner/templates/*` | Skill 부속 자료 |
| `skills/<X>/SKILL.md` | `.claude/skills/<X>/SKILL.md` | Skill |

## 의도적으로 비워둔 것들

다음은 회사가 자기 환경에 맞게 추가:
- 프레임워크 특화 검증 skill (예: angular-code-checker, vertx-pattern-checker)
- 회사 표준 rules (Rule_JWT 등)
- 회사 표준 patterns
- 스택별 presets

default 템플릿은 **tech-agnostic** 만 제공. tech 정보는 `.harness-config.yaml` + CLAUDE.md 경로로 전달.

## 주의 사항

- 이 디렉터리 안의 파일을 직접 편집하지 마세요 (도구 구현 후엔 reference 용도)
- Bitbucket으로 옮긴 후엔 Bitbucket이 source of truth
- 변경 시엔 reference 와 Bitbucket 둘 다 동기화 필요 (운용 정책으로 정함)
