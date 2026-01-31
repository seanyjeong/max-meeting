# Plan: STT/LLM 로깅 시스템

## 개요

| 항목 | 내용 |
|------|------|
| **Feature ID** | stt-llm-logging |
| **우선순위** | P2 |
| **생성일** | 2025-01-31 |
| **상태** | Plan |

## 문제 정의

### 현재 상태

1. **STT 파이프라인**
   - `workers/tasks/stt.py`에서 기본 `logger.info/warning` 사용
   - Redis Pub/Sub로 진행률 전송 (`publish_progress`)
   - **문제**: 음성 처리 실패 시 원인 진단 어려움 (Whisper API 응답, 처리 시간 등 미기록)

2. **LLM 파이프라인**
   - `workers/tasks/llm.py`에서 기본 `logger.info/warning` 사용
   - `app/services/llm.py`에서 API 호출하지만 트레이싱 없음
   - **문제**: API 비용 추적 불가, 실패 원인 진단 어려움

3. **기존 Audit 시스템**
   - `app/middleware/audit_log.py`에 AuditLogger 존재
   - 보안 이벤트 로깅용 (login, resource access 등)
   - STT/LLM 처리 로깅에는 부적합

## 요구사항

### 필수 (Must Have)

| ID | 요구사항 | 이유 |
|----|----------|------|
| R1 | STT 처리 시작/완료/실패 로깅 | 음성 처리 파이프라인 모니터링 |
| R2 | STT 처리 시간 기록 (청크별, 전체) | 성능 병목 파악 |
| R3 | LLM API 호출 로깅 (provider, model, prompt 길이) | API 사용량 추적 |
| R4 | LLM 응답 시간 및 토큰 수 기록 | 비용 추정 |
| R5 | 에러 발생 시 상세 컨텍스트 로깅 | 디버깅 용이성 |

### 선택 (Nice to Have)

| ID | 요구사항 | 이유 |
|----|----------|------|
| R6 | 일별/월별 사용량 대시보드 쿼리 | 운영 리포트 |
| R7 | 비용 알림 (threshold 초과 시) | 예산 관리 |

## 제약사항

1. **기존 코드 최소 변경**: 현재 워커 로직 변경 최소화
2. **성능 영향 없음**: 로깅이 STT/LLM 처리 속도에 영향 X
3. **저장소**: PostgreSQL 활용 (새 테이블 추가)

## 성공 기준

| 기준 | 측정 방법 |
|------|----------|
| STT 처리 로그 조회 가능 | `SELECT * FROM stt_logs WHERE recording_id = ?` |
| LLM 호출 로그 조회 가능 | `SELECT * FROM llm_logs WHERE meeting_id = ?` |
| 에러 발생 시 원인 파악 가능 | 로그에 error_type, error_message, context 포함 |
| 일별 사용량 조회 가능 | 집계 쿼리로 토큰 수, 처리 건수 확인 |

## 관련 파일

```
backend/
├── workers/tasks/
│   ├── stt.py          # STT 처리 태스크
│   └── llm.py          # LLM 처리 태스크
├── app/services/
│   ├── llm.py          # LLM 서비스 (Gemini/OpenAI)
│   └── gemini.py       # Gemini provider
├── app/middleware/
│   └── audit_log.py    # 기존 감사 로그 (참고용)
└── app/models/
    └── (새 모델 추가 예정)
```

## 다음 단계

1. Design: 로깅 테이블 스키마 설계, 로깅 위치 결정
2. Do: 모델/마이그레이션 생성, 로깅 코드 삽입
3. Check: Gap 분석 + 전체 QA
