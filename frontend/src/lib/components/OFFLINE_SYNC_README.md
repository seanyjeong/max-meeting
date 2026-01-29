# Offline Sync & Conflict Resolution

오프라인 작업 및 동기화 충돌 해결을 위한 컴포넌트와 스토어입니다.

## 구성 요소

### 1. `SyncConflictDialog.svelte`
동기화 충돌을 해결하기 위한 다이얼로그 컴포넌트입니다.

**Props:**
- `conflict: ConflictData` - 충돌 데이터
- `onResolve: (choice: 'local' | 'server' | 'merge') => void` - 해결 선택 핸들러
- `onCancel: () => void` - 취소 핸들러

**사용 예시:**
```svelte
<script>
  import SyncConflictDialog from '$lib/components/SyncConflictDialog.svelte';

  let conflict = {
    resourceType: 'meeting',
    resourceId: 1,
    localData: { title: '로컬 제목' },
    serverData: { title: '서버 제목' },
    localUpdatedAt: new Date('2024-01-10T10:00:00'),
    serverUpdatedAt: new Date('2024-01-10T11:00:00')
  };

  function handleResolve(choice) {
    console.log('Selected:', choice);
  }
</script>

<SyncConflictDialog {conflict} onResolve={handleResolve} onCancel={() => {}} />
```

### 2. `offline.ts` Store
오프라인 동기화 및 충돌 관리를 위한 스토어입니다.

**State:**
```typescript
interface OfflineState {
  isOnline: boolean;           // 온라인 상태
  isSyncing: boolean;           // 동기화 진행 중
  pendingConflicts: ConflictData[];  // 대기 중인 충돌
  syncQueue: OfflineQueueItem[];     // 동기화 대기열
  lastSyncAt: Date | null;      // 마지막 동기화 시간
  syncError: string | null;     // 동기화 에러
}
```

**주요 메서드:**

#### `addToQueue(item)`
오프라인 작업을 동기화 큐에 추가합니다.

```typescript
offlineStore.addToQueue({
  type: 'update',
  resourceType: 'meeting',
  resourceId: 1,
  data: { title: '수정된 제목' }
});
```

#### `checkAndAddConflict(resourceType, resourceId, localData, localUpdatedAt)`
서버와 비교하여 충돌을 감지하고 추가합니다.

```typescript
const hasConflict = await offlineStore.checkAndAddConflict(
  'meeting',
  1,
  localMeetingData,
  new Date(localMeetingData.updated_at)
);

if (hasConflict) {
  console.log('충돌이 감지되었습니다.');
}
```

#### `resolveConflict(index, choice)`
충돌을 해결합니다.

```typescript
// 로컬 버전 선택
offlineStore.resolveConflict(0, 'local');

// 서버 버전 선택
offlineStore.resolveConflict(0, 'server');
```

#### `syncQueue()`
큐의 모든 작업을 동기화합니다.

```typescript
await offlineStore.syncQueue();
```

### 3. `OfflineSyncManager.svelte`
자동으로 충돌을 감지하고 UI를 표시하는 매니저 컴포넌트입니다.

**사용 예시:**
```svelte
<!-- +layout.svelte -->
<script>
  import OfflineSyncManager from '$lib/components/OfflineSyncManager.svelte';
</script>

<OfflineSyncManager />

<slot />
```

이 컴포넌트는:
- 충돌 발생 시 자동으로 다이얼로그 표시
- 오프라인 상태 표시
- 동기화 진행 상태 표시
- 온라인 복귀 시 자동 동기화

## 통합 가이드

### 1. Layout에 OfflineSyncManager 추가

```svelte
<!-- src/routes/+layout.svelte -->
<script>
  import OfflineSyncManager from '$lib/components/OfflineSyncManager.svelte';
</script>

<OfflineSyncManager />

<!-- 나머지 레이아웃 코드 -->
```

### 2. 리소스 업데이트 시 오프라인 지원

```typescript
// 예: 미팅 업데이트
import { offlineStore } from '$lib/stores/offline';
import { api } from '$lib/api';

async function updateMeeting(meetingId: number, data: MeetingData) {
  if (!navigator.onLine) {
    // 오프라인: 큐에 추가
    offlineStore.addToQueue({
      type: 'update',
      resourceType: 'meeting',
      resourceId: meetingId,
      data
    });

    // 로컬스토리지에 임시 저장
    localStorage.setItem(`meeting-${meetingId}`, JSON.stringify(data));

    return;
  }

  try {
    // 온라인: 직접 서버에 저장
    await api.patch(`/meetings/${meetingId}`, data);
  } catch (error) {
    // 실패 시 큐에 추가
    offlineStore.addToQueue({
      type: 'update',
      resourceType: 'meeting',
      resourceId: meetingId,
      data
    });
  }
}
```

### 3. 온라인 복귀 시 충돌 체크

```typescript
import { offlineStore } from '$lib/stores/offline';

// 앱 초기화 시 또는 온라인 복귀 시
window.addEventListener('online', async () => {
  // 로컬에 저장된 데이터 확인
  const localData = JSON.parse(localStorage.getItem('meeting-1') || '{}');
  const localUpdatedAt = new Date(localData.updated_at);

  // 충돌 체크
  const hasConflict = await offlineStore.checkAndAddConflict(
    'meeting',
    1,
    localData,
    localUpdatedAt
  );

  if (!hasConflict) {
    // 충돌 없음: 자동 동기화
    await offlineStore.syncQueue();
  }
  // 충돌 있음: OfflineSyncManager가 자동으로 다이얼로그 표시
});
```

## 로컬스토리지 저장 형식

```typescript
// 동기화 큐
localStorage.setItem('offline-sync-queue', JSON.stringify([
  {
    id: 'uuid-1',
    type: 'update',
    resourceType: 'meeting',
    resourceId: 1,
    data: { ... },
    timestamp: '2024-01-10T10:00:00Z',
    retryCount: 0
  }
]));

// 대기 중인 충돌
localStorage.setItem('offline-pending-conflicts', JSON.stringify([
  {
    resourceType: 'meeting',
    resourceId: 1,
    localData: { ... },
    serverData: { ... },
    localUpdatedAt: '2024-01-10T10:00:00Z',
    serverUpdatedAt: '2024-01-10T11:00:00Z'
  }
]));
```

## 테스트 가이드

### 1. 오프라인 상태 테스트

Chrome DevTools에서:
1. F12 → Network 탭
2. "Offline" 선택
3. 앱에서 데이터 수정
4. 오프라인 인디케이터 확인
5. "Online" 선택
6. 자동 동기화 확인

### 2. 충돌 시뮬레이션

```typescript
// 수동으로 충돌 추가 (테스트용)
import { offlineStore } from '$lib/stores/offline';

offlineStore.addToQueue({
  type: 'update',
  resourceType: 'meeting',
  resourceId: 1,
  data: { title: '로컬 제목' }
});

// 서버에 다른 버전이 있다고 가정
await offlineStore.checkAndAddConflict(
  'meeting',
  1,
  { title: '로컬 제목', updated_at: '2024-01-10T10:00:00Z' },
  new Date('2024-01-10T10:00:00Z')
);
```

## 주의사항

1. **대용량 데이터**: 로컬스토리지는 용량 제한(~5MB)이 있으므로 대용량 데이터는 IndexedDB 사용 권장
2. **보안**: 민감한 데이터는 암호화하여 저장
3. **충돌 해결**: 병합(merge) 전략은 리소스 타입에 따라 커스터마이징 필요
4. **재시도 정책**: 현재는 무한 재시도이므로 실패 횟수 제한 추가 권장

## 향후 개선 사항

- [ ] IndexedDB 지원 (대용량 데이터)
- [ ] 스마트 병합 알고리즘
- [ ] 재시도 정책 (exponential backoff)
- [ ] 충돌 히스토리 로깅
- [ ] 배치 동기화 최적화
