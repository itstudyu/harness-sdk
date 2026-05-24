# Harness-gen 참고 자료 (AI Context Reference)

> **이 문서는 AI에게 넘기는 참고 자료(컨텍스트)입니다.**
>
> - 목적: harness-gen 도구를 설계/구축할 때 사상적 기반과 결합 원칙 안내
> - 함께 사용: `harness-gen-build-spec.md` (구체 명세서)
> - 관계: 이 문서 = **왜/무엇**, spec = **어떻게**

---

## 0. 이 문서가 답하는 질문

AI가 도구를 만들면서 다음 질문을 마주칠 때 참조:

- "왜 DB가 아니라 파일이지?"
- "왜 CLAUDE.md는 100줄로 제한?"
- "왜 imports/overrides/local 3개로 분리?"
- "Karpathy 원칙과 Harness 패턴이 충돌하면 어디 따라?"

→ 답이 이 문서에 있음. 명확하지 않으면 Section 8(우선순위)을 참조.

---

## 1. 네 가지 사상의 통합 (큰 그림)

이 도구는 **4가지 검증된 사상을 동시에 구현**하는 컴파일러다.

```
   ┌──────────────────────────────────────┐
   │  사상 1: Karpathy CLAUDE.md         │
   │  → "단순함, 50줄 원칙, 모르면 묻기"  │
   ├──────────────────────────────────────┤
   │  사상 2: LLM Wiki 패턴               │
   │  → "파일 기반 KG, 백링크=엣지"       │
   ├──────────────────────────────────────┤
   │  사상 3: GraphRAG                    │
   │  → "관계 명시, 멀티홉 추론, 결정성"  │
   ├──────────────────────────────────────┤
   │  사상 4: Harness SDKG                │
   │  → "공유+로컬, 3-layer, 검증된 ROI"  │
   └──────────────────────────────────────┘
              ↓ (통합)
       [ harness-gen 도구 ]
              ↓
       [ .harness/ 디렉터리 ]
```

---

## 2. 사상 1: Andrej Karpathy의 CLAUDE.md

### 인물
- OpenAI 공동창립자, 전 Tesla AI 총괄
- 독립 AI 연구자 (Eureka Labs 창업)
- "vibe coding" 용어를 만든 사람
- 2026년 3월 발언: 코딩 작업의 80%를 AI 에이전트에 위임

### 영향력
Forrest Chang이 Karpathy의 LLM 코딩 함정 관찰을 단일 CLAUDE.md 파일로 정리한 GitHub 레포는 **10만+ 스타**를 받으며 업계 표준이 됨.

### 핵심 원칙 (이 도구에 적용 필수)

**원칙 1: 명확한 가정 검증**
> "모델은 사용자 대신 잘못된 가정을 하고 확인 없이 밀어붙인다. 자기 혼란을 관리하지 않고, 명확화를 요청하지 않고, 불일치를 드러내지 않고, 트레이드오프를 제시하지 않고, 필요할 때 밀어붙이지 못한다."

→ **이 도구의 적용**: TBD 항목 미정 시 진행 금지. 사용자에게 물어볼 것.

**원칙 2: 50줄 원칙**
> "200줄을 썼는데 50줄로 가능하면 다시 써라. 시니어 엔지니어가 '과복잡'이라고 할까 자문해라."

→ **이 도구의 적용**: 생성되는 CLAUDE.md ≤ 100줄. 도구 자체 코드도 단순하게.

**원칙 3: 최소 변경**
> "필요한 것만 손대라. 인접 코드를 '개선'하지 마라. 자기가 만든 잘못만 청소해라."

→ **이 도구의 적용**: generate는 .harness/ 만 건드림. 사용자 코드 절대 X.

**원칙 4: 단일 책임**
한 도구는 한 가지만 잘 한다.

→ **이 도구의 적용**: 도구는 **컴파일러**일 뿐. KG 쿼리 / MCP / 모니터링 등 추가 X.

### 출처
- GitHub: https://github.com/forrestchang/andrej-karpathy-skills
- 분석: https://pasqualepillitteri.it/en/news/1872/karpathy-claude-md-trending-github-llm-coding

---

## 3. 사상 2: LLM Wiki 패턴

### 무엇인가
Karpathy가 2026년 초 제안한 개인 지식 베이스 구축 방식.

> "같은 원시 데이터를 매번 다시 읽는 대신, 모델이 한 번 읽고 구조화한 다음 진화하는 지식 계층을 구축한다."

### 핵심 통찰
- **LLM을 컴파일러처럼 사용** → 원시 문서 → 구조화된 위키
- **벡터 DB / 임베딩 사용 안 함**
- **Markdown + Obsidian이면 충분**
- **백링크(`[[link]]`) = 그래프 엣지**

### LLM Wiki ↔ GraphRAG 본질적 동일성

복수 개발자/연구자가 명시적으로 지적:
> "Karpathy의 wiki-with-backlinks 방식은 본질적으로 GraphRAG와 같다. 노드를 Markdown 파일로, 엣지를 백링크로 표현했을 뿐."

따라서 이 도구는:
- 표면: LLM Wiki (Markdown + YAML 파일)
- 본질: GraphRAG (관계 그래프)

### 이 도구의 적용
- `.harness/`는 LLM Wiki 형태로 출력 (파일들)
- YAML 필드(`implements`, `demonstrates`)가 백링크 역할 = 그래프 엣지
- AI는 디렉터리 탐색 + 파일 읽기로 그래프 순회

### 출처
- 분석 (DAIR.AI): https://academy.dair.ai/blog/llm-knowledge-bases-karpathy
- 분석 (agentpedia): https://agentpedia.codes/blog/karpathy-llm-knowledge-bases
- 구현 참고 (Graphify): https://medium.com/data-science-in-your-pocket/andrej-karparthys-llm-wiki-codes-graphify-b73bec5d87ea
- 프레임워크 (obsidian-wiki): https://github.com/Ar9av/obsidian-wiki

---

## 4. 사상 3: GraphRAG

### 정의
지식을 노드(엔티티) + 엣지(관계)의 그래프로 저장하고, AI가 관계를 따라가며 답을 추론하는 방식.

### 일반 RAG와의 결정적 차이

| | 일반 RAG | GraphRAG |
|---|---|---|
| 저장 | 텍스트 청크 + 벡터 | 노드 + 관계 |
| 검색 | 의미 유사도 | 관계 추적 + 의미 |
| 약점 | 관계 추론 불가 | 데이터 구조화 필요 |
| 대표 질문 | "문서 X에 뭐라고 써있어?" | "X 바꾸면 어디 영향?" |

### 핵심 강점: 멀티홉 추론
"Pattern_JWT → 어떤 Rule을 구현? → 어떤 API들이 이 Rule을 따라야 함? → 담당 팀이 누구?" 같은 다단계 질문 가능.

### 이 도구의 적용
- 노드: Rule / Pattern / Example
- 엣지: YAML ref (`implements`, `demonstrates`, `MUST_FOLLOW`)
- 결정성: 같은 입력은 항상 같은 출력 (벡터 검색의 확률적 매칭 X)

### 출처
- Microsoft GraphRAG: https://github.com/microsoft/graphrag
- Anthropic MCP 표준: https://modelcontextprotocol.io
- Neo4j + Claude 가이드: https://neo4j.com/blog/developer/knowledge-graphs-claude-neo4j-mcp/

---

## 5. 사상 4: Harness 공식 구조 (검증된 엔터프라이즈 패턴)

### 무엇인가
Harness Inc.가 2025년 출시한 **Software Delivery Knowledge Graph (SDKG)**. CI/CD 영역에서 검증된 KG + RAG 하이브리드.

### 3-Layer 아키텍처 (공식 발표)

```
┌─────────────────────────────────┐
│ Semantic Layer                   │  ← 의미 정의
│ (Pipeline, Service 등이 무엇인가) │
├─────────────────────────────────┤
│ Knowledge Graph                  │  ← 구조적 관계
├─────────────────────────────────┤
│ RAG                              │  ← 비정형 보강 (선택적)
└─────────────────────────────────┘
```

### 검증된 효과 (공식 수치)
- 파이프라인 온보딩 **85% 단축**
- 이슈 해결 **7배 가속**
- 디버깅 시간 **50% 감소**

### 신뢰도 (왜 이걸 참고해도 되는가)
- **공식 발표**: Harness Inc. 자사 운영 데이터
- **Anthropic 인정**: Harness MCP Server가 Claude Connectors Directory 등재
- **OpenAI 채택**: OpenAI가 자사 Codex 운영에 Harness 사용
- **Google Cloud 인정**: 2026 Google Cloud Technology Partner of the Year (DevOps 부문)

### 이 도구의 적용
- **3-layer 사상 차용**: Semantic(ontology.yaml) + KG(rules/patterns/examples) + (RAG는 미사용)
- **참조 패턴 차용**: 공유 레지스트리 + 프로젝트별 imports
- **단, 규모는 축소**: Harness는 엔터프라이즈, 이 도구는 프로젝트 단위 스캐폴딩

### 중요: 그대로 복사 X
Harness는 엔터프라이즈용으로 무겁다 (자체 플랫폼, DB, 동기화 엔진 등). 이 도구는 Karpathy 원칙에 따라 **참조만 하고 단순화**.

### 출처
- KG + RAG 블로그 (필독): https://www.harness.io/blog/knowledge-graph-rag
- KG 사용 이유 블로그: https://www.harness.io/blog/why-harness-ai-uses-knowledge-graph
- 공식 제품: https://www.harness.io/products/harness-ai
- Harness Agents 상세: https://www.harness.io/products/harness-ai/agents

---

## 6. 통합 매핑 — 각 사상이 도구의 어디에 반영되나

| 도구 구성요소 | Karpathy | LLM Wiki | GraphRAG | Harness |
|---|---|---|---|---|
| `.harness-config.yaml` | ✓ 단순함 | | | ✓ config 패턴 |
| `.harness/` 디렉터리 | ✓ 50줄 원칙 | ✓ 파일 기반 | ✓ 관계 표현 | ✓ 3-layer |
| Rule/Pattern/Example | | ✓ 백링크 | ✓ 노드/엣지 | ✓ 분류 체계 |
| 공유 레지스트리 | | ✓ 중앙 위키 | | ✓ 참조 패턴 |
| `imports` / `overrides` / `local` | ✓ 명시적 결정 | | ✓ 관계 정의 | ✓ 거버넌스 |
| `.lock.yaml` | ✓ 재현성 | | | |
| CLAUDE.md 합성 (≤100줄) | ✓ 핵심 원칙 | ✓ 시작점 | | |
| `init` 명령 | ✓ 모르면 묻기 | | | ✓ preset 패턴 |
| `generate` 명령 | ✓ 한 가지만 잘 | ✓ 컴파일러 역할 | ✓ 결정성 | |
| MCP 서버 | | | | (미사용 — Karpathy 원칙) |
| 벡터 DB / 임베딩 | (사용 X) | (사용 X) | (사용 X) | (선택사항이지만 채택 X) |

---

## 7. 사용자(Peanut) 상황 — Design Context

### 확정된 결정
| 항목 | 값 | 이유 |
|---|---|---|
| 구현 언어 | **Python** | 가독성, CLI 생태계, YAML 처리 |
| 공유 레지스트리 | **사내 Bitbucket Server** | 회사 표준 Git 호스팅 |
| **타겟 AI** | **Claude Code 전용** | Cursor 등 다른 도구 호환 고려 X |
| 타겟 스택 | **Java/Vert.x** | 회사 표준 백엔드 |
| 버저닝 | **Semantic Versioning + Git tags** | 업계 표준 |
| 배포 | **pip + 사내 PyPI 미러** 또는 zipapp | Python 자연스러운 흐름 |

### 환경적 제약
- **Bitbucket Server (사내)**: HTTP Basic Auth + SSH key 사용. 외부 GitHub 못 씀.
- **SSL/TLS 검사 프록시**: HTTPS 요청 시 사내 CA 인증서 처리 필요
- **EDR 에이전트**: 바이너리 배포 시 검수 필요할 수 있음
- **회사 보안 정책**: 외부 패키지 일부 차단 가능

### 사용자 학습 단계
- IT 3년 경험, 비개발자 출신
- 코드 읽기 가능 (변수, 함수 수준)
- 직접 코드 작성 X
- **함의**: 도구는 명확한 에러 메시지 + 친절한 문서 필요

### Bitbucket Server 통합 시 주의
- `git clone https://bitbucket.company.com/...` 형태
- Authentication: `~/.netrc` 또는 SSH key 활용
- API 호출 필요 시: Bitbucket REST API v2 (`/rest/api/1.0/...`)
- **PoC 단계는 로컬 디렉터리로 검증 후 Bitbucket 통합**

### Claude Code 전용 활용 포인트
- **루트 `CLAUDE.md` 자동 로드**: 매 세션 시작 시 인식
- **Nested CLAUDE.md 지원**: 하위 디렉터리 작업 시 해당 CLAUDE.md도 컨텍스트로 로드
- **`.cursorrules` 등 다른 도구 파일 생성 X** — 깔끔하게 유지
- **MCP 서버 통합 가능** (향후): 그래프를 MCP로 노출하면 더 깊은 컨텍스트 활용

---

## 8. 사상 충돌 시 우선순위

도구를 만들다 보면 사상들이 충돌할 수 있다. 이때 우선순위:

```
1순위: Karpathy 단순함
       → "이거 정말 필요한가? 50줄로 가능한가?"

2순위: GraphRAG 결정성
       → "같은 입력 = 같은 출력 보장하는가?"

3순위: LLM Wiki 가독성
       → "AI가 파일 직접 읽어도 이해 가능한가?"

4순위: Harness 실용성 (참고용)
       → "엔터프라이즈 기능 흉내내지 말 것"
```

### 충돌 예시와 판단

**예시 1**: "성능 위해 그래프 DB 도입?"
- Karpathy: 너무 무거움 (1순위 위반) → **NO**
- LLM Wiki: 파일 기반 원칙 위반 (3순위 위반) → **NO**
- Harness: 엔터프라이즈 흉내 (4순위 위반) → **NO**
- → **결론**: 도입하지 않음

**예시 2**: "임포트 fetch 시 캐싱?"
- Karpathy: 단순함 — 캐시는 합리적
- GraphRAG: 결정성 — 캐시 키만 잘 설계하면 OK
- Harness: 참고 — 동기화 패턴
- → **결론**: 도입함 (단, 캐시 키는 import 경로 + 버전 hash)

**예시 3**: "AI가 알아서 추측해서 진행?"
- Karpathy 원칙 1: **명확히 금지** (모르면 묻기)
- → **결론**: 절대 금지

---

## 9. AI에게 주는 결합 원칙

### MUST (반드시 지킬 것)
- ✅ 모호 시 사용자에게 질문, 가정 후 진행 금지
- ✅ 생성되는 CLAUDE.md ≤ 100줄
- ✅ 모든 출력물은 파일 (Markdown / YAML)
- ✅ Rule/Pattern/Example 간 관계는 YAML ref로 표현
- ✅ Bitbucket Server 환경 고려 (auth, 프록시 등)
- ✅ 한국어 주석 작성 (Peanut 가독성)

### MUST NOT (절대 금지)
- ❌ 벡터 DB / 임베딩 / 벡터 검색 도입
- ❌ 200줄로 가능한 걸 200줄로 작성
- ❌ Harness 엔터프라이즈 기능 그대로 복사
- ❌ Example의 본문을 그래프에 복사 (경로만)
- ❌ Override 자동 생성 (사람의 명시적 결정)
- ❌ "imports를 최신으로 자동 추적" 같은 마법

### 모호한 경우 대처
1. Section 8 우선순위 표 확인
2. 그래도 모호하면 사용자에게 질문
3. 가정 후 진행 금지
4. 진행 시 가정한 부분 명시

---

## 10. 검증된 출처 (모두 1차 자료, 신뢰도 ⭐ 표시)

### Karpathy ⭐⭐⭐
- CLAUDE.md (Forrest Chang 정리): https://github.com/forrestchang/andrej-karpathy-skills
- 분석 (Pasquale Pillitteri): https://pasqualepillitteri.it/en/news/1872/karpathy-claude-md-trending-github-llm-coding

### LLM Wiki ⭐⭐⭐
- DAIR.AI 분석: https://academy.dair.ai/blog/llm-knowledge-bases-karpathy
- agentpedia 분석: https://agentpedia.codes/blog/karpathy-llm-knowledge-bases
- Graphify (AST 기반 구현): https://medium.com/data-science-in-your-pocket/andrej-karparthys-llm-wiki-codes-graphify-b73bec5d87ea
- obsidian-wiki: https://github.com/Ar9av/obsidian-wiki

### Harness 공식 ⭐⭐⭐
- KG + RAG 블로그 (필독): https://www.harness.io/blog/knowledge-graph-rag
- KG 사용 이유: https://www.harness.io/blog/why-harness-ai-uses-knowledge-graph
- 제품 페이지: https://www.harness.io/products/harness-ai
- Harness Agents: https://www.harness.io/products/harness-ai/agents

### GraphRAG ⭐⭐
- Microsoft GraphRAG: https://github.com/microsoft/graphrag
- Neo4j + Claude + MCP: https://neo4j.com/blog/developer/knowledge-graphs-claude-neo4j-mcp/

### Anthropic / MCP ⭐⭐⭐
- MCP 공식 사이트: https://modelcontextprotocol.io
- Anthropic Claude Connectors: (Harness MCP Server 등재 확인)

### 디자인 참고 (Reference Architectures) ⭐⭐
- npm/yarn (imports + lock 패턴): https://docs.npmjs.com
- Tailwind CSS (config + override): https://tailwindcss.com/docs/configuration
- Kustomize (base + overlay): https://kustomize.io

---

## 11. AI를 위한 실행 가이드

이 문서를 받았을 때 권장 흐름:

```
1단계: Section 1~5 정독
       → 4가지 사상 이해

2단계: Section 6 매핑 표
       → 도구의 각 부분이 어느 사상 반영인지 파악

3단계: Section 7 사용자 상황
       → Peanut의 환경/제약 인지

4단계: Section 8 우선순위
       → 설계 결정 시 충돌 해결 기준

5단계: 의문 발생 시 Section 10 출처 참조
       또는 사용자에게 질문

6단계: 함께 받은 harness-gen-build-spec.md 와 결합
       → 이 문서: "왜", spec: "무엇/어떻게"
```

---

## 12. 한 줄 통합 정의

> **"이 도구는 Karpathy의 단순함을 토대로, LLM Wiki의 파일 구조를 따르고, GraphRAG의 관계를 명시하고, Harness의 검증된 패턴을 참고하여 만든, Bitbucket Server 기반 사내 환경에 맞는 프로젝트별 Knowledge Graph 생성기다."**

---

## 13. 결합의 본질 (왜 이 4개가 같이 가는가)

| 사상 | 기여하는 것 | 없으면 무슨 일? |
|---|---|---|
| **Karpathy** | 단순함, 명확성 | 도구가 비대해짐 |
| **LLM Wiki** | 파일 기반 구조 | DB 종속, 무거움 |
| **GraphRAG** | 관계의 명시성 | AI가 추측해야 함 |
| **Harness** | 실용 패턴 (imports/overrides) | 바퀴 재발명 |

**4개가 합쳐져야 비로소**:
- 가볍고 (Karpathy)
- 이식 가능하고 (LLM Wiki — 파일이라 어디든 작동)
- 정확하고 (GraphRAG — 관계 추적 가능)
- 검증된 (Harness — 엔터프라이즈에서 7배 가속 증명)

→ **하나라도 빠지면 이 도구의 가치 약화**.

---

**Document Version**: v0.1 (AI Context Reference)
**Companion Documents**:
- `harness-gen-build-spec.md` (구체 구현 명세)

**Usage**: Spec과 함께 AI에게 전달. 이 문서는 "왜/사상", spec은 "무엇/구현".
