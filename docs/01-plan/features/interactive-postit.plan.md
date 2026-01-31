# Plan: 인터랙티브 포스트잇

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | interactive-postit |
| 작성일 | 2026-01-31 |
| 우선순위 | Medium |
| 예상 범위 | Frontend + Backend |

## 2. 현재 문제점

### 2.1 기능 제한
- **고정된 위치**: 메모가 안건 옆에 고정 배치됨
- **삭제 불가**: 결과 페이지에서 메모를 뗄 수 없음
- **이동 불가**: 드래그로 위치 변경 불가
- **단조로운 UI**: 실제 포스트잇 느낌 부족

### 2.2 사용자 니즈
- 진짜 포스트잇처럼 자유롭게 붙이고 떼고 싶음
- 안건별로 메모 위치를 시각적으로 배치하고 싶음
- 결과 페이지에서 불필요한 메모 정리하고 싶음

## 3. 개선 목표

### 3.1 핵심 기능
| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 드래그 이동 | 포스트잇을 드래그해서 위치 변경 | High |
| 삭제 기능 | 결과 페이지에서 메모 떼기(삭제) | High |
| 위치 저장 | x, y 좌표를 DB에 저장 | High |
| 회전 효과 | 랜덤 회전으로 자연스러운 배치 | Medium |
| 그림자 효과 | 붙어있는 느낌의 그림자 | Medium |

### 3.2 목표 UX
```
┌─────────────────────────────────────────────┐
│  안건 1: 프로젝트 일정 논의                    │
│  ┌────────┐                                 │
│  │ 📌     │  ← 드래그로 이동 가능              │
│  │ 메모1  │     클릭 시 삭제 버튼 표시         │
│  │        │                                 │
│  └────────┘     ┌────────┐                  │
│                 │ 📌     │ ← 약간 회전       │
│                 │ 메모2  │                   │
│                 └────────┘                  │
└─────────────────────────────────────────────┘
```

## 4. 기술 요구사항

### 4.1 Backend 변경
```
테이블: manual_notes
추가 필드:
  - position_x: float (nullable, 0~100 %)
  - position_y: float (nullable, 0~100 %)
  - rotation: float (nullable, -5 ~ 5 deg)
  - is_visible: boolean (default: true)

API 변경:
  - PATCH /notes/{id}/position - 위치 업데이트
  - PATCH /notes/{id}/visibility - 표시/숨김 토글
```

### 4.2 Frontend 변경
```
컴포넌트:
  - DraggablePostIt.svelte (새로 생성)
  - PostItCanvas.svelte (컨테이너, 드래그 영역)

라이브러리:
  - @neodrag/svelte (드래그앤드롭) 또는 네이티브 구현

페이지:
  - /results/+page.svelte - 드래그 기능 추가
  - /results/report/+page.svelte - 읽기 전용
```

## 5. 구현 범위

### Phase 1: 기본 드래그 (MVP)
- [ ] Backend: position_x, position_y 필드 추가
- [ ] Backend: 위치 업데이트 API
- [ ] Frontend: DraggablePostIt 컴포넌트
- [ ] Frontend: 결과 페이지에 드래그 적용

### Phase 2: 삭제 & 시각 효과
- [ ] Backend: is_visible 필드 추가
- [ ] Frontend: 삭제(숨김) 버튼
- [ ] Frontend: 회전 효과 (rotation)
- [ ] Frontend: 그림자 효과

### Phase 3: 고급 기능 (선택)
- [ ] 포스트잇 크기 조절
- [ ] 색상 변경
- [ ] 애니메이션 효과

## 6. 영향 범위

| 파일/테이블 | 변경 유형 |
|-------------|----------|
| `manual_notes` 테이블 | 컬럼 추가 |
| `backend/app/models/note.py` | 필드 추가 |
| `backend/app/schemas/note.py` | 스키마 추가 |
| `backend/app/routers/notes.py` | API 추가 |
| `frontend/.../PostItNote.svelte` | 드래그 기능 추가 |
| `frontend/.../results/+page.svelte` | 드래그 컨테이너 |

## 7. 리스크 & 고려사항

| 리스크 | 완화 방안 |
|--------|----------|
| 모바일 터치 드래그 | touch event 지원 필요 |
| 성능 (많은 메모) | 위치 업데이트 디바운스 |
| 충돌 (겹침) | z-index 자동 조절 |
| DB 마이그레이션 | nullable 필드로 안전하게 |

## 8. 일정

| 단계 | 설명 |
|------|------|
| Plan | ✅ 완료 |
| Design | 다음 단계 |
| Do (Phase 1) | MVP 구현 |
| Check | Gap 분석 |
| Do (Phase 2) | 시각 효과 |

## 9. 참고

- 기존 PostItNote.svelte 컴포넌트 재활용
- Svelte 5 runes 사용
- 인쇄용 회의록에서는 고정 위치로 출력
