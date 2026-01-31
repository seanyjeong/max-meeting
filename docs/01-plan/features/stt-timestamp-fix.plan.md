# STT 타임스탬프 버그 수정 계획

## 문제 정의

### 현상
- 긴 녹음(20분+)에서 안건별 대화 내용이 다른 안건에 잘못 매핑됨
- 뒤로 갈수록 오차가 심해짐
- 예: 안건2(564-664초)에 안건1.2.3 내용이 표시됨

### 근본 원인
LLM `refine_transcript` 함수에서:
1. 원본 세그먼트 263개 → LLM 출력 218개로 줄어듦
2. 비율 기반 타임스탬프 매핑 시도 → **텍스트-시간 연결 완전히 깨짐**
3. 각 정제된 라인이 원본과 1:1 대응되지 않아 시간 정보 손실

### 영향 범위
- STT 전사록 타임스탬프 전체
- 안건별 대화 내용 매핑
- 회의록 생성 품질

---

## 해결 방안

### Option A: LLM Refine 비활성화 (권장 - 빠른 수정)
- 원본 Whisper 전사록 그대로 사용
- 타임스탬프 정확도 100% 보장
- 단점: 오타, 동음이의어 오류 그대로 남음

### Option B: 타임스탬프 보존형 Refine
- LLM에 타임스탬프를 함께 전달
- "텍스트만 수정, 시간은 유지" 지시
- 복잡하고 LLM 오류 가능성 있음

### Option C: 세그먼트 단위 개별 Refine
- 각 세그먼트를 개별적으로 LLM 정제
- 타임스탬프 완벽 보존
- 단점: API 호출 많음, 비용 증가

### 결정: Option A (LLM Refine 비활성화)
- 이유: 가장 확실하고 빠른 수정
- Whisper 자체가 충분히 정확함
- 향후 필요시 Option C로 업그레이드 가능

---

## 수정 계획

### 1단계: 코드 수정
**파일**: `backend/workers/tasks/stt.py`

```python
# 수정 전 (676-686행)
try:
    logger.info(f"Refining transcript with LLM for recording {recording_id}")
    refined_segments = await refine_transcript(...)
    final_segments = refined_segments
except Exception as e:
    final_segments = combined_result["segments"]

# 수정 후
# LLM refine 비활성화 - 타임스탬프 정확도 우선
final_segments = combined_result["segments"]
logger.info(f"Using original segments without LLM refinement: {len(final_segments)} segments")
```

### 2단계: 기존 전사록 재처리
```bash
# 워커 재시작
sudo systemctl restart maxmeeting-worker

# recording 21 재처리
python -c "from workers.tasks.stt import reprocess_recording; reprocess_recording.delay(21)"

# LLM 결과 재생성
python -c "from workers.tasks.llm import generate_meeting_result; generate_meeting_result.delay(14)"
```

### 3단계: 검증
- [ ] 전사록 타임스탬프 연속성 확인
- [ ] 안건2(564-664초) 내용이 실제 "장학금 이벤트" 인지 확인
- [ ] 마지막 안건(북부회장, 유튜브) 내용 확인

---

## 2시간+ 녹음 고려사항

### 현재 설정
- `STT_CHUNK_MINUTES = 5` (5분 청크)
- 2시간 = 24청크

### 잠재적 문제
1. **메모리**: 24청크 결합 시 메모리 사용량
2. **처리 시간**: 약 24분 소요 예상
3. **청크 경계**: 문장이 청크 경계에서 잘릴 수 있음

### 향후 개선 (별도 Plan)
- 청크 오버랩 추가 (10초씩)
- 청크 경계 문장 병합 로직
- 진행 상황 더 상세한 피드백

---

## 체크리스트

- [x] `workers/tasks/stt.py` LLM refine 비활성화
- [x] 워커 재시작
- [x] recording 21 재처리 (transcript_id: 19, 263 segments)
- [x] meeting 14 LLM 결과 재생성 (result_id: 33, version: 5)
- [x] 안건별 내용 검증 (안건2 "1억원 장학금" 내용 일치 확인)
- [x] version.ts 업데이트 (1.16.4)
- [ ] 커밋 및 배포

---

## 담당 및 일정
- 담당: Claude
- 예상 소요: 30분
- 우선순위: **긴급**
