# STT 타임스탬프 버그 수정 완료 보고서

> 버전: v1.16.6 | 날짜: 2026-01-31

## 📋 작업 개요

| 항목 | 내용 |
|------|------|
| **문제** | 긴 녹음(20분+)에서 마지막 부분 대화 누락 및 안건별 내용 불일치 |
| **근본 원인** | LLM refine_transcript 함수의 1:1 인덱스 매핑 버그 |
| **해결책** | LLM refine 비활성화, 원본 Whisper 세그먼트 직접 사용 |
| **부가 작업** | 녹음 파일 자동 정리, 프론트엔드 디버그 코드 제거 |

---

## 🐛 문제 분석

### 증상
- 1221초 녹음이 1009초에서 끝남 (212초 누락)
- 안건 2번에 안건 1번 내용이 표시됨
- 긴 회의일수록 누락 비율 증가

### 원인 추적
```
Whisper STT: 263개 세그먼트 (0~1220초)
     ↓
LLM refine: 218줄로 압축 (정제)
     ↓
1:1 인덱스 매핑: segment[i] ← refined[i]
     ↓
결과: 세그먼트 219~263번 (마지막 45개) 타임스탬프 손실
```

### 핵심 버그 코드 (수정 전)
```python
# backend/app/services/llm.py - refine_transcript()
for i, line in enumerate(lines):
    if i < len(segments):
        segments[i]["text"] = line  # 1:1 매핑 - 개수 불일치 시 누락
```

---

## ✅ 해결 방안

### 1. LLM refine 비활성화 (핵심 수정)

**파일**: `backend/workers/tasks/stt.py`

```python
# 변경 전
refined_segments = await refine_transcript(combined_result, meeting_result.meeting, agendas)
final_segments = refined_segments["segments"]

# 변경 후
final_segments = combined_result["segments"]  # Whisper 원본 사용
logger.info(f"Saving {len(final_segments)} Whisper segments")
```

**이유**:
- Whisper 자체 정확도가 충분히 높음
- 타임스탬프 정확성이 텍스트 정제보다 중요
- LLM 처리 시간 절약 (약 30초)

### 2. Dead Code 제거

```python
# 제거된 코드 (stt.py)
- from app.services.llm import refine_transcript
- meeting_result = await session.execute(...)  # 미사용 쿼리
- agendas_result = await session.execute(...)  # 미사용 쿼리
```

### 3. STT 에러 시 상태 업데이트

```python
# log_stt_error_sync() 함수에 추가
recording.status = RecordingStatus.FAILED
await session.commit()
```

---

## 🗑️ 녹음 파일 자동 정리 (신규 기능)

### 요구사항
- 회의록 생성 후 녹음 파일은 불필요
- 재처리 대비 3일 유예 후 삭제
- 매일 새벽 3시 자동 실행

### 구현

**파일**: `backend/workers/tasks/cleanup.py` (신규)

```python
@shared_task(name="workers.tasks.cleanup.cleanup_old_recordings")
def cleanup_old_recordings(retention_days: int = 3) -> dict:
    """회의록 생성 후 retention_days일 지난 녹음 파일 삭제"""
    # 삭제 조건:
    # 1. meeting_result 존재 (LLM 분석 완료)
    # 2. result.created_at + retention_days < now
    # 3. recording.file_path 파일 존재
```

**Celery Beat 스케줄**:
```python
beat_schedule = {
    "cleanup-old-recordings": {
        "task": "workers.tasks.cleanup.cleanup_old_recordings",
        "schedule": crontab(hour=3, minute=0),  # 매일 새벽 3시
        "args": (3,),  # 3일 유예
    },
}
```

**systemd 서비스**: `/etc/systemd/system/maxmeeting-beat.service`

---

## 🧹 프론트엔드 디버그 코드 정리

### 삭제된 항목

| 파일 | 제거 내용 |
|------|----------|
| `DebugPanel.svelte` | 컴포넌트 전체 삭제 |
| `record/+page.svelte` | console.log 23개 |
| `results.ts` | console.log/error 11개 |
| `recording.ts` | console.log/error 5개 |
| `notes.ts` | console.log 5개 |
| `AgendaNotePanel.svelte` | console.log 7개 |
| `AgendaEditor.svelte` | console.log 5개 |
| `meetings/new/+page.svelte` | debug log 함수 및 호출 전체 |
| 기타 10개 파일 | console.error 각 1-3개 |

### 유지된 항목 (적절한 사용)
- `logger.ts` - DEV 체크가 있는 로깅 유틸리티
- `import.meta.env.DEV` 로 감싼 로그들
- `hooks.server.ts` - 서버 프록시 에러 로깅
- `service-worker.ts` - SW 동기화 로깅

---

## 📊 검증 결과

### STT 타임스탬프 검증
```sql
-- 수정 전
SELECT MIN(start_time), MAX(end_time) FROM transcript_segments WHERE recording_id = 12;
-- 결과: 0.62 ~ 1009.24 (누락)

-- 수정 후 (재처리)
SELECT MIN(start_time), MAX(end_time) FROM transcript_segments WHERE recording_id = 12;
-- 결과: 0.62 ~ 1220.4 (전체 커버)
```

### 안건 내용 검증
- 안건 1 (학원 인사말): ✅ 인사말 관련 대화
- 안건 2 (1억원 장학금): ✅ 장학금 이벤트 관련 대화
- 안건 3 (체대입시 설명): ✅ 체대입시 관련 대화

---

## 📁 변경 파일 목록

### Backend
| 파일 | 변경 내용 |
|------|----------|
| `workers/tasks/stt.py` | LLM refine 비활성화, dead code 제거, FAILED 상태 업데이트 |
| `workers/tasks/cleanup.py` | 신규 - 녹음 파일 자동 정리 |
| `workers/tasks/__init__.py` | cleanup 태스크 export |
| `workers/celery_app.py` | cleanup 라우팅, beat_schedule 추가 |

### Frontend
| 파일 | 변경 내용 |
|------|----------|
| `lib/version.ts` | 1.16.5 → 1.16.6 |
| `lib/components/ui/DebugPanel.svelte` | 삭제 |
| 15개 파일 | console.log/error/warn 제거 |

### Infrastructure
| 파일 | 변경 내용 |
|------|----------|
| `/etc/systemd/system/maxmeeting-beat.service` | Celery Beat 서비스 신규 |

---

## 🚀 배포 체크리스트

- [x] STT 타임스탬프 버그 수정
- [x] LLM refine dead code 제거
- [x] STT 에러 시 FAILED 상태 업데이트
- [x] 녹음 파일 자동 정리 기능
- [x] Celery Beat 서비스 설정
- [x] 프론트엔드 디버그 코드 정리
- [x] 버전 업데이트 (1.16.6)
- [ ] Git 커밋
- [ ] 백엔드 배포 (systemctl restart)
- [ ] 프론트엔드 배포 (Vercel 자동)

---

## 📈 기대 효과

| 항목 | 개선 |
|------|------|
| **STT 정확도** | 긴 녹음에서도 100% 대화 캡처 |
| **안건 매칭** | 타임스탬프 기반 정확한 매칭 |
| **디스크 공간** | 3일 후 녹음 파일 자동 삭제 |
| **프론트 성능** | 불필요한 로깅 제거로 약간의 성능 향상 |
| **디버깅** | logger.ts 통한 일관된 로깅 체계 |

---

*Generated: 2026-01-31*
