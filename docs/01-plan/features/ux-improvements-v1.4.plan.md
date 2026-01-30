# UX 개선 및 버그 수정 v1.4

> 작성일: 2026-01-30
> 버전: v1.4.0 (예정)

## 1. 개요

회의 시스템 테스트 피드백 기반 UX 개선 및 버그 수정

## 2. 이슈 목록

### 🔴 Critical (기능 문제)

| # | 이슈 | 현상 | 예상 원인 |
|---|------|------|----------|
| C1 | 자식안건 생성 안됨 | 회의 생성 시 자식안건 파싱/생성 실패 | LLM 파싱 로직 또는 프론트엔드 전송 문제 |
| C2 | 자식안건 숫자 표기 | 숫자 없이 표시됨 (1.1, 1.2 필요) | UI 렌더링 누락 |
| C3 | 안건별 토론 불일치 | 토론내용과 아젠다 매칭 오류 | LLM 요약 생성 시 매핑 오류 |
| C4 | PDF 자식안건 없음 | 회의록 PDF에 자식안건 미표시 | report 페이지 데이터 누락 |

### 🟡 UX 개선

| # | 이슈 | 현상 | 해결방안 |
|---|------|------|---------|
| U1 | 진행 게이지 없음 | STT/회의록 생성 시 멈춤 느낌 | 실시간 진행률 표시 (polling/SSE) |
| U2 | 대화내용 탭 UI | 선택된 안건 색상 구분 어려움 | 선택 상태 색상 대비 강화 |
| U3 | 질문 수정/삭제 | UI에서 접근 방법 불명확 | 질문 옆 수정/삭제 버튼 추가 |
| U4 | 회의 시작 통합 | "녹음"/"텍스트만" 분리됨 | 단일 "회의 시작" 버튼으로 통합 |
| U5 | 타이핑 Shift 고정 | 메모 입력 시 대문자 고정 | 입력 필드 이벤트 핸들링 수정 |
| U6 | 빠른이동 제거 | 상단 빠른이동 UI 불필요 | 제거 |

### 🟢 레이아웃/디자인

| # | 이슈 | 현상 | 해결방안 |
|---|------|------|---------|
| L1 | 녹음 버튼 위치 | 떠있는 느낌 | 회의 영역 안으로 통합 |
| L2 | 태블릿 화면 크기 | 2000x1200 대응 부족 | 반응형 레이아웃 개선 |

## 3. 우선순위 및 구현 순서

```
Phase 1: Critical 버그 (C1-C4)
  ├── C1: 자식안건 생성 로직 수정
  ├── C2: 자식안건 숫자 표기
  ├── C3: 안건별 토론 매칭 수정
  └── C4: PDF 자식안건 표시

Phase 2: UX 개선 (U1-U6)
  ├── U1: 진행 게이지 추가
  ├── U2: 대화내용 탭 색상 개선
  ├── U3: 질문 수정/삭제 UI
  ├── U4: 회의 시작 통합
  ├── U5: Shift 키 버그 수정
  └── U6: 빠른이동 제거

Phase 3: 레이아웃 (L1-L2)
  ├── L1: 녹음 버튼 통합
  └── L2: 태블릿 반응형 개선
```

## 4. 예상 변경 파일

### Phase 1 (Critical)
- `backend/app/services/llm.py` - parse_agenda_text 수정
- `frontend/src/routes/meetings/new/+page.svelte` - 안건 전송 로직
- `frontend/src/routes/meetings/[id]/+page.svelte` - 자식안건 숫자 표기
- `backend/app/services/result.py` - 토론 매칭 로직
- `frontend/src/routes/meetings/[id]/results/report/+page.svelte` - PDF 자식안건

### Phase 2 (UX)
- `frontend/src/routes/meetings/[id]/results/+page.svelte` - 게이지, 탭 UI
- `frontend/src/lib/components/recording/AgendaNotePanel.svelte` - 질문 UI
- `frontend/src/routes/meetings/[id]/+page.svelte` - 회의 시작 통합
- `frontend/src/routes/meetings/[id]/record/+page.svelte` - Shift 버그, 빠른이동

### Phase 3 (레이아웃)
- `frontend/src/routes/meetings/[id]/record/+page.svelte` - 녹음 버튼
- `frontend/src/app.css` 또는 컴포넌트 CSS - 태블릿 반응형

## 5. 검증 체크리스트

### Phase 1
- [ ] 회의 생성 시 자식안건 정상 생성
- [ ] 자식안건 1.1, 1.2 형식 표기
- [ ] 안건별 토론 내용 정확히 매칭
- [ ] PDF에 자식안건 표시

### Phase 2
- [ ] STT 진행률 게이지 표시
- [ ] 회의록 생성 진행률 표시
- [ ] 대화내용 탭 선택 상태 명확
- [ ] 질문 수정/삭제 가능
- [ ] 회의 시작 버튼 통합
- [ ] 타이핑 정상 작동
- [ ] 빠른이동 제거됨

### Phase 3
- [ ] 녹음 버튼 회의 영역 내
- [ ] 2000x1200 태블릿에서 정상 표시

## 6. 다음 단계

`/pdca design ux-improvements-v1.4` 로 설계 진행
