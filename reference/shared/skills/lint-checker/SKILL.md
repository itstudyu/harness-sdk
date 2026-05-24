---
name: lint-checker
description: 프로젝트의 lint 도구를 자동 감지하고 실행. Use when 코드 작성 후 lint 검증이 필요할 때.
---

# Lint Checker Skill

프로젝트 타입을 감지하고 적절한 lint 도구를 실행합니다.
메인 Claude와 Subagent 모두 호출 가능 (preload 시).

---

## 실행 절차

### 1. 프로젝트 타입 감지

```bash
ls package.json pom.xml build.gradle pyproject.toml go.mod 2>/dev/null
```

### 2. Lint 명령 실행

프로젝트 타입에 맞는 명령 실행. 다음은 일반적인 예시 (실제 명령은 프로젝트의 package.json scripts 등에서 확인):

- `npm run lint`
- `mvn checkstyle:check`
- `./gradlew checkstyleMain`
- `ruff check .`
- `golangci-lint run`

### 3. 결과 파싱

- errors: 0 → PASS
- errors: >0 → FAIL
- warnings: 보고만 (PASS 차단 X)

---

## 보고 형식

```
lint-checker: PASS (0 errors, N warnings)

또는

lint-checker: FAIL (N errors)
- <파일:라인> — <에러 메시지>
- ...
```

---

## 금지 사항

- 코드 자동 수정 (`--fix` 사용 X)
- 설정 파일 변경 (`.eslintrc` 등)
- 결과를 장황하게 출력 (요약 + 핵심 에러만)
