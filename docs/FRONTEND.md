# Frontend Documentation

## 서버 정보

| 항목 | 값 |
|------|-----|
| **Framework** | SvelteKit 2 + Svelte 5 |
| **Dev Port** | 5173 |
| **Prod Port** | 3000 |
| **Adapter** | adapter-vercel |
| **배포** | Vercel (max-meeting.vercel.app) |
| **Working Dir** | `/home/et/max-ops/max-meeting/frontend` |

## 환경변수

```bash
PUBLIC_API_URL=https://api.meeting.etlab.kr/api/v1
```

## 라우트 (13개)

| 경로 | 파일 | 설명 |
|------|------|------|
| `/` | `+page.svelte` | 대시보드 |
| `/login` | `login/+page.svelte` | 로그인 |
| `/meetings` | `meetings/+page.svelte` | 회의 목록 |
| `/meetings/new` | `meetings/new/+page.svelte` | 회의 생성 + LLM 안건 파싱 |
| `/meetings/deleted` | `meetings/deleted/+page.svelte` | 삭제된 회의 |
| `/meetings/[id]` | `meetings/[id]/+page.svelte` | 회의 상세 |
| `/meetings/[id]/record` | `meetings/[id]/record/+page.svelte` | 녹음 |
| `/meetings/[id]/sketch` | `meetings/[id]/sketch/+page.svelte` | 스케치 |
| `/meetings/[id]/results` | `meetings/[id]/results/+page.svelte` | 결과/회의록 |
| `/meetings/[id]/results/edit` | `meetings/[id]/results/edit/+page.svelte` | 결과 편집 |
| `/contacts` | `contacts/+page.svelte` | 연락처 목록 |
| `/contacts/new` | `contacts/new/+page.svelte` | 연락처 생성 |
| `/contacts/[id]` | `contacts/[id]/+page.svelte` | 연락처 상세 |

## 주요 컴포넌트 (26개)

### 안건 편집
| 컴포넌트 | 설명 |
|----------|------|
| `AgendaEditor.svelte` | 계층형 DnD 안건 편집기 |

### 녹음 (`lib/components/recording/`)
| 컴포넌트 | 설명 |
|----------|------|
| `RecordButton.svelte` | 녹음 버튼 |
| `RecordingGuard.svelte` | 권한/배터리 체크 |
| `Waveform.svelte` | 오디오 파형 |
| `AgendaTracker.svelte` | 안건 진행 |
| `AgendaNotePanel.svelte` | 녹음 중 노트 |
| `NoteSketchArea.svelte` | 녹음 중 스케치 |
| `CompactRecordingBar.svelte` | 미니 녹음 바 |

### 결과 (`lib/components/results/`)
| 컴포넌트 | 설명 |
|----------|------|
| `TranscriptViewer.svelte` | 녹취록 뷰어 |
| `SummaryEditor.svelte` | 요약 편집기 |
| `SpeakerMapper.svelte` | 화자 매핑 |
| `ActionItems.svelte` | 액션아이템 |

### 스케치 (`lib/components/sketch/`)
| 컴포넌트 | 설명 |
|----------|------|
| `SketchPad.svelte` | 스케치 패드 |
| `TldrawWrapper.svelte` | tldraw React 브릿지 |

### 공통
| 컴포넌트 | 설명 |
|----------|------|
| `Card.svelte` | 카드 |
| `Modal.svelte` | 모달 |
| `Button.svelte` | 버튼 |
| `Input.svelte` | 입력 |
| `Badge.svelte` | 배지 |
| `Toast.svelte` | 토스트 |
| `LoadingSpinner.svelte` | 로딩 |
| `Breadcrumb.svelte` | 브레드크럼 |
| `DarkModeToggle.svelte` | 다크모드 |
| `QuickJump.svelte` | 단축키 이동 |
| `PreflightCheck.svelte` | 시스템 체크 |
| `OfflineSyncManager.svelte` | 오프라인 동기화 |

## Stores (8개)

| Store | 파일 | 설명 |
|-------|------|------|
| auth | `auth.ts` | 인증 상태 + refreshToken() |
| meeting | `meeting.ts` | 회의 목록/상세 |
| recording | `recording.ts` | 녹음 상태 + upload |
| results | `results.ts` | 결과 상태 |
| contacts | `contacts.ts` | 연락처 캐시 |
| sketch | `sketch.ts` | 스케치 상태 |
| toast | `toast.ts` | 토스트 큐 |
| sync | `sync.ts` | 오프라인 (IndexedDB) |

## 주요 의존성

```json
{
  "svelte": "^5.0.0",
  "@sveltejs/kit": "^2.0.0",
  "@sveltejs/adapter-vercel": "^6.3.1",
  "tailwindcss": "^3.4.0",
  "dompurify": "^3.3.1",
  "svelte-dnd-action": "^0.9.69",
  "react": "^19.2.4",
  "react-dom": "^19.2.4"
}
```

## 빌드 & 배포

```bash
# 개발
npm run dev

# 빌드
npm run build

# Vercel 배포 (자동)
git push origin main
```
