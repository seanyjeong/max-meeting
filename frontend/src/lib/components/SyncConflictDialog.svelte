<script lang="ts">
	import Button from './Button.svelte';
	import { formatDateTime } from '$lib/utils/format';

	interface ConflictData {
		resourceType: 'meeting' | 'note' | 'sketch';
		resourceId: number;
		localData: unknown;
		serverData: unknown;
		localUpdatedAt: Date;
		serverUpdatedAt: Date;
	}

	interface Props {
		conflict: ConflictData;
		onResolve: (choice: 'local' | 'server' | 'merge') => void;
		onCancel: () => void;
	}

	let { conflict, onResolve, onCancel }: Props = $props();

	// 데이터 차이 하이라이트를 위한 포맷팅
	function formatData(data: unknown): string {
		return JSON.stringify(data, null, 2);
	}
</script>

<!-- 모달 다이얼로그 -->
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true">
	<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
		<!-- 헤더 -->
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h2 class="text-xl font-bold text-gray-900 dark:text-white">
				동기화 충돌 발생
			</h2>
			<p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
				오프라인에서 수정한 내용과 서버 데이터가 충돌합니다. 어떤 버전을 유지할지 선택해주세요.
			</p>
		</div>

		<!-- 본문 -->
		<div class="flex-1 overflow-y-auto px-6 py-4">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<!-- 로컬 버전 -->
				<div class="border-2 border-blue-500 rounded-lg p-4">
					<div class="flex items-center justify-between mb-3">
						<h3 class="font-semibold text-blue-600 dark:text-blue-400 text-lg">
							내 변경사항 (로컬)
						</h3>
						<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
							로컬
						</span>
					</div>
					<p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
						수정 시간: {formatDateTime(conflict.localUpdatedAt)}
					</p>
					<div class="bg-gray-100 dark:bg-gray-900 rounded p-3 text-sm overflow-auto max-h-96 font-mono">
						<pre class="text-gray-800 dark:text-gray-200">{formatData(conflict.localData)}</pre>
					</div>
				</div>

				<!-- 서버 버전 -->
				<div class="border-2 border-green-500 rounded-lg p-4">
					<div class="flex items-center justify-between mb-3">
						<h3 class="font-semibold text-green-600 dark:text-green-400 text-lg">
							서버 버전
						</h3>
						<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
							서버
						</span>
					</div>
					<p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
						수정 시간: {formatDateTime(conflict.serverUpdatedAt)}
					</p>
					<div class="bg-gray-100 dark:bg-gray-900 rounded p-3 text-sm overflow-auto max-h-96 font-mono">
						<pre class="text-gray-800 dark:text-gray-200">{formatData(conflict.serverData)}</pre>
					</div>
				</div>
			</div>

			<!-- 안내 메시지 -->
			<div class="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
				<div class="flex">
					<svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
					</svg>
					<div class="ml-3">
						<p class="text-sm text-yellow-700 dark:text-yellow-300">
							선택한 버전으로 데이터가 덮어씌워집니다. 신중하게 선택해주세요.
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- 버튼들 -->
		<div class="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
			<Button variant="secondary" onclick={onCancel}>
				나중에 결정
			</Button>
			<Button variant="primary" onclick={() => onResolve('local')}>
				<svg class="w-4 h-4 mr-1.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				내 버전 유지
			</Button>
			<Button variant="primary" onclick={() => onResolve('server')}>
				<svg class="w-4 h-4 mr-1.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
				</svg>
				서버 버전 사용
			</Button>
		</div>
	</div>
</div>
