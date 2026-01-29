<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import AgendaEditor, { type AgendaItem } from '$lib/components/AgendaEditor.svelte';
	import { Sparkles, ArrowLeft } from 'lucide-svelte';

	interface MeetingType {
		id: number;
		name: string;
	}

	interface Contact {
		id: number;
		name: string;
		role: string | null;
		organization: string | null;
	}

	let meetingTypes: MeetingType[] = [];
	let contacts: Contact[] = [];
	let isLoading = false;
	let isSaving = false;
	let error = '';
	let showNewTypeModal = false;
	let newTypeName = '';
	let isCreatingType = false;

	// Attendee autocomplete state
	let searchQuery = '';
	let contactSuggestions: Contact[] = [];
	let isSearching = false;
	let showSuggestions = false;
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;
	let selectedContacts: Contact[] = [];

	// Form fields
	let title = '';
	let typeId: number | null = null;
	let scheduledAt = '';
	let location = '';
	let selectedAttendees: number[] = [];

	// Agenda fields
	interface QuestionInput {
		question: string;
		is_generated: boolean;
		answered: boolean;
	}

	interface AgendaInput {
		id: string;
		title: string;
		description: string;
		questions: QuestionInput[];
		children?: AgendaInput[];
	}
	let agendas: AgendaInput[] = [{ id: crypto.randomUUID(), title: '', description: '', questions: [], children: [] }];
	let agendaTextInput = '';
	let isParsing = false;
	let generatingQuestionsFor: string | null = null;
	let parseDebounceTimer: ReturnType<typeof setTimeout> | null = null;
	let isAutoPreviewEnabled = true;
	let showAgendaEditor = false;

	// Helper functions for AgendaEditor integration
	function agendaToEditorItem(a: AgendaInput): AgendaItem {
		return {
			id: a.id,
			title: a.title || '',
			description: a.description || '',
			children: (a.children || []).map(agendaToEditorItem)
		};
	}

	function editorItemToAgenda(item: AgendaItem, existingMap: Map<string, AgendaInput>): AgendaInput {
		const existing = existingMap.get(item.id);
		return {
			id: item.id,
			title: item.title || '',
			description: item.description || '',
			questions: existing?.questions || [],
			children: (item.children || []).map((c: AgendaItem) => editorItemToAgenda(c, existingMap))
		};
	}

	function flattenAgendas(list: AgendaInput[]): Map<string, AgendaInput> {
		const map = new Map<string, AgendaInput>();
		for (const a of list) {
			map.set(a.id, a);
			if (a.children && a.children.length > 0) {
				const childMap = flattenAgendas(a.children);
				childMap.forEach((v, k) => map.set(k, v));
			}
		}
		return map;
	}

	function handleEditorItemsChange(items: AgendaItem[]) {
		console.log('[+page] handleEditorItemsChange called with', items.length, 'items');
		const existingMap = flattenAgendas(agendas);
		agendas = items.map((item) => editorItemToAgenda(item, existingMap));
		console.log('[+page] agendas updated:', agendas);
	}

	onMount(async () => {
		// 로그인 상태 확인 (브라우저에서만)
		if (typeof window !== 'undefined') {
			const token = localStorage.getItem('accessToken');
			if (import.meta.env.DEV) console.log('[NEW_MEETING] Token check:', token ? 'EXISTS' : 'MISSING');
			if (!token) {
				if (import.meta.env.DEV) console.warn('[NEW_MEETING] No access token - redirecting to login');
				goto('/login');
				return;
			}
		}

		isLoading = true;

		// 회의 유형 로드 (개별 try-catch)
		try {
			if (import.meta.env.DEV) console.log('[NEW_MEETING] Loading meeting types...');
			const typesResponse = await api.get<{ data: MeetingType[] }>('/meeting-types');
			if (import.meta.env.DEV) console.log('[NEW_MEETING] Meeting types loaded:', typesResponse);
			meetingTypes = typesResponse.data || [];
			if (import.meta.env.DEV) console.log('[NEW_MEETING] meetingTypes set to:', meetingTypes);
		} catch (err: any) {
			if (import.meta.env.DEV) console.error('[NEW_MEETING] Failed to load meeting types:', err);
			if (err.status === 401 || err.status === 403) {
				localStorage.removeItem('accessToken');
				localStorage.removeItem('refreshToken');
				goto('/login');
				return;
			}
		}

		// 연락처 로드 (개별 try-catch)
		try {
			if (import.meta.env.DEV) console.log('[NEW_MEETING] Loading contacts...');
			const contactsResponse = await api.get<{ data: Contact[] }>('/contacts', { limit: 100 });
			if (import.meta.env.DEV) console.log('[NEW_MEETING] Contacts loaded:', contactsResponse);
			contacts = contactsResponse.data || [];
		} catch (err: any) {
			if (import.meta.env.DEV) console.error('[NEW_MEETING] Failed to load contacts:', err);
			// 연락처 로드 실패는 무시 (필수 아님)
		}

		isLoading = false;
	});

	function addAgenda() {
		agendas = [...agendas, { id: crypto.randomUUID(), title: '', description: '', questions: [], children: [] }];
	}

	function removeAgenda(id: string) {
		if (agendas.length <= 1) return;
		agendas = agendas.filter((a) => a.id !== id);
	}

	function moveAgenda(index: number, direction: 'up' | 'down') {
		const newIndex = direction === 'up' ? index - 1 : index + 1;
		if (newIndex < 0 || newIndex >= agendas.length) return;

		const newAgendas = [...agendas];
		[newAgendas[index], newAgendas[newIndex]] = [newAgendas[newIndex], newAgendas[index]];
		agendas = newAgendas;
	}

	async function parseAgendas() {
		if (!agendaTextInput.trim()) {
			error = '안건 텍스트를 입력해주세요';
			return;
		}

		isParsing = true;
		error = '';

		try {
			// Use backend AI parsing API for intelligent hierarchical structure detection
			interface ParsedItem {
				title: string;
				description?: string | null;
				children?: ParsedItem[];
			}
			const response = await api.post<{ items: ParsedItem[] }>(
				'/agendas/parse-preview',
				{ text: agendaTextInput }
			);

			// Recursively convert parsed items with children
			function convertItem(item: ParsedItem): AgendaInput {
				return {
					id: crypto.randomUUID(),
					title: item.title,
					description: item.description || '',
					questions: [],
					children: (item.children || []).map(convertItem)
				};
			}

			const parsedAgendas: AgendaInput[] = (response.items || []).map(convertItem);

			if (parsedAgendas.length > 0) {
				// Replace existing agendas with parsed ones
				agendas = parsedAgendas;
				agendaTextInput = '';
				showAgendaEditor = true;
			} else {
				error = '유효한 안건을 찾을 수 없습니다';
			}
		} catch (err: any) {
			if (import.meta.env.DEV) console.error('Failed to parse agendas:', err);
			// Fallback to local parsing if API fails
			const fallbackAgendas = parseAgendasLocal(agendaTextInput);
			if (fallbackAgendas.length > 0) {
				agendas = fallbackAgendas;
				agendaTextInput = '';
				showAgendaEditor = true;
			} else {
				error = '안건 파싱에 실패했습니다. 다시 시도하세요.';
			}
		} finally {
			isParsing = false;
		}
	}

	// Local fallback parser with hierarchical structure support
	function parseAgendasLocal(text: string): AgendaInput[] {
		const lines = text.split('\n');
		const result: AgendaInput[] = [];
		let currentAgenda: AgendaInput | null = null;
		let subItems: string[] = [];

		for (const line of lines) {
			const trimmedLine = line.trimEnd();
			if (!trimmedLine) continue;

			// Check if this is a main agenda item (numbered: "1.", "2.", etc.)
			const mainMatch = trimmedLine.match(/^(\d+)[\.\)]\s*(.+)$/);
			// Check if this is a sub-item (indented or starts with dash/bullet)
			const isSubItem = /^(\s{2,}|\t)/.test(line) || /^\s*[-\*\•]\s/.test(trimmedLine);

			if (mainMatch && !isSubItem) {
				// Save previous agenda with collected sub-items
				if (currentAgenda) {
					currentAgenda.description = subItems.join('\n');
					result.push(currentAgenda);
				}

				// Start new main agenda
				currentAgenda = {
					id: crypto.randomUUID(),
					title: mainMatch[2].trim(),
					description: '',
					questions: [],
					children: []
				};
				subItems = [];
			} else if (currentAgenda && isSubItem) {
				// This is a sub-item, add to description
				// Clean up the sub-item formatting
				const cleanedSubItem = trimmedLine.replace(/^\s+/, '').replace(/^[-\*\•]\s*/, '- ');
				subItems.push(cleanedSubItem);
			} else if (!currentAgenda && trimmedLine) {
				// First item without number, treat as main agenda
				currentAgenda = {
					id: crypto.randomUUID(),
					title: trimmedLine.replace(/^[-\*\•]\s*/, '').trim(),
					description: '',
					questions: [],
					children: []
				};
				subItems = [];
			} else if (currentAgenda && !isSubItem) {
				// Continuation text without proper numbering - treat as new item
				if (currentAgenda) {
					currentAgenda.description = subItems.join('\n');
					result.push(currentAgenda);
				}
				currentAgenda = {
					id: crypto.randomUUID(),
					title: trimmedLine.replace(/^[-\*\•]\s*/, '').trim(),
					description: '',
					questions: [],
					children: []
				};
				subItems = [];
			}
		}

		// Don't forget the last agenda
		if (currentAgenda) {
			currentAgenda.description = subItems.join('\n');
			result.push(currentAgenda);
		}

		return result;
	}

	function debouncedParse(text: string) {
		if (parseDebounceTimer) clearTimeout(parseDebounceTimer);

		if (!text.trim() || text.trim().length < 10) {
			return;
		}

		parseDebounceTimer = setTimeout(async () => {
			if (!isAutoPreviewEnabled) return;
			await parseAgendas();
		}, 500);
	}

	async function handleSubmit() {
		error = '';

		if (!title.trim()) {
			error = '제목은 필수입니다';
			return;
		}

		if (!typeId) {
			error = '회의 유형은 필수입니다';
			return;
		}

		const validAgendas = agendas.filter((a) => a.title.trim());
		if (validAgendas.length === 0) {
			error = '최소 하나의 안건이 필요합니다';
			return;
		}

		isSaving = true;

		try {
			// Create meeting - API returns MeetingDetailResponse directly (not wrapped in data)
			const meetingResponse = await api.post<{ id: number }>('/meetings', {
				title: title.trim(),
				type_id: typeId,
				scheduled_at: scheduledAt || null,
				location: location.trim() || null,
				attendee_ids: selectedAttendees
			});

			const meetingId = meetingResponse.id;

			// Add agendas
			for (let i = 0; i < validAgendas.length; i++) {
				await api.post(`/meetings/${meetingId}/agendas`, {
					title: validAgendas[i].title.trim(),
					description: validAgendas[i].description.trim() || null,
					order_num: i + 1
				});
			}

			goto(`/meetings/${meetingId}`);
		} catch (err) {
			if (import.meta.env.DEV) console.error('Failed to create meeting:', err);
			error = '회의 생성에 실패했습니다. 다시 시도하세요.';
		} finally {
			isSaving = false;
		}
	}

	function toggleAttendee(contactId: number) {
		const contact = getContactById(contactId);
		if (!contact) return;

		if (selectedAttendees.includes(contactId)) {
			selectedAttendees = selectedAttendees.filter((id) => id !== contactId);
			selectedContacts = selectedContacts.filter((c) => c.id !== contactId);
		} else {
			selectedAttendees = [...selectedAttendees, contactId];
			selectedContacts = [...selectedContacts, contact];
		}
	}

	async function createNewMeetingType() {
		if (!newTypeName.trim()) {
			error = '회의 유형 이름을 입력해주세요';
			return;
		}

		isCreatingType = true;
		error = '';

		try {
			const response = await api.post<MeetingType>('/meeting-types', {
				name: newTypeName.trim()
			});

			// 응답이 직접 객체로 옴 (data로 감싸지지 않음)
			const newType = response as MeetingType;
			meetingTypes = [...meetingTypes, newType].sort((a, b) => a.name.localeCompare(b.name));
			typeId = newType.id;
			showNewTypeModal = false;
			newTypeName = '';
		} catch (err: any) {
			if (import.meta.env.DEV) console.error('Failed to create meeting type:', err);
			if (err.response?.status === 409) {
				error = `'${newTypeName}' 유형이 이미 존재합니다`;
			} else {
				error = '회의 유형 생성에 실패했습니다';
			}
		} finally {
			isCreatingType = false;
		}
	}

	function closeNewTypeModal() {
		showNewTypeModal = false;
		newTypeName = '';
		error = '';
	}

	// Attendee autocomplete functions
	async function searchContacts(event: Event) {
		const input = event.target as HTMLInputElement;
		searchQuery = input.value;

		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}

		if (!searchQuery.trim()) {
			contactSuggestions = [];
			showSuggestions = false;
			return;
		}

		searchTimeout = setTimeout(async () => {
			isSearching = true;
			try {
				const response = await api.get<{ data: Contact[] }>('/contacts', {
					q: searchQuery,
					limit: 10
				});
				contactSuggestions = response.data.filter(
					(c) => !selectedAttendees.includes(c.id)
				);
				showSuggestions = true;
			} catch (err) {
				if (import.meta.env.DEV) console.error('Failed to search contacts:', err);
			} finally {
				isSearching = false;
			}
		}, 300);
	}

	function addAttendee(contact: Contact) {
		if (!selectedAttendees.includes(contact.id)) {
			selectedAttendees = [...selectedAttendees, contact.id];
			selectedContacts = [...selectedContacts, contact];
		}
		searchQuery = '';
		contactSuggestions = [];
		showSuggestions = false;
	}

	function removeAttendee(contactId: number) {
		selectedAttendees = selectedAttendees.filter((id) => id !== contactId);
		selectedContacts = selectedContacts.filter((c) => c.id !== contactId);
	}

	function getContactById(id: number): Contact | undefined {
		return contacts.find((c) => c.id === id) || selectedContacts.find((c) => c.id === id);
	}

	function addQuestion(agendaId: string) {
		agendas = agendas.map((a) =>
			a.id === agendaId
				? {
						...a,
						questions: [...a.questions, { question: '', is_generated: false, answered: false }]
				  }
				: a
		);
	}

	function removeQuestion(agendaId: string, questionIndex: number) {
		agendas = agendas.map((a) =>
			a.id === agendaId
				? {
						...a,
						questions: a.questions.filter((_, i) => i !== questionIndex)
				  }
				: a
		);
	}

	async function regenerateQuestions(agendaId: string) {
		const agenda = agendas.find((a) => a.id === agendaId);
		if (!agenda || !agenda.title.trim()) {
			return;
		}

		generatingQuestionsFor = agendaId;
		error = '';

		try {
			// Backend auto-generates questions on agenda creation
			// Show placeholder message instead of mock data
			agendas = agendas.map((a) =>
				a.id === agendaId
					? {
							...a,
							questions: [
								{ question: '회의 생성 후 AI가 자동으로 질문을 생성합니다', is_generated: true, answered: false }
							]
					  }
					: a
			);
		} catch (err) {
			if (import.meta.env.DEV) console.error('Failed to generate questions:', err);
			error = '질문 생성에 실패했습니다';
		} finally {
			generatingQuestionsFor = null;
		}
	}
</script>

<svelte:head>
	<title>새 회의 - MAX Meeting</title>
</svelte:head>

<div class="max-w-3xl mx-auto">
	<div class="mb-6">
		<a href="/meetings" class="text-sm text-gray-500 hover:text-gray-700">
			&larr; 회의 목록으로
		</a>
	</div>

	<h1 class="text-2xl font-bold text-gray-900 mb-8">새 회의</h1>

	{#if isLoading}
		<div class="flex justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
		</div>
	{:else}
		<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-8">
			{#if error}
				<div class="rounded-md bg-red-50 p-4" role="alert">
					<p class="text-sm font-medium text-red-800">{error}</p>
				</div>
			{/if}

			<!-- Basic Info -->
			<section class="card">
				<h2 class="text-lg font-medium text-gray-900 mb-4">기본 정보</h2>

				<div class="space-y-4">
					<div>
						<label for="title" class="block text-sm font-medium text-gray-700 mb-1">
							제목 <span class="text-red-500">*</span>
						</label>
						<input
							id="title"
							type="text"
							bind:value={title}
							required
							class="input"
							placeholder="회의 제목"
						/>
					</div>

					<div>
						<label for="type" class="block text-sm font-medium text-gray-700 mb-1">
							회의 유형 <span class="text-red-500">*</span>
						</label>
						<div class="flex gap-2">
							<select id="type" bind:value={typeId} required class="input flex-1">
								<option value={null}>유형 선택...</option>
								{#each meetingTypes as type (type.id)}
									<option value={type.id}>{type.name}</option>
								{/each}
							</select>
							<button
								type="button"
								onclick={() => { showNewTypeModal = true; }}
								class="btn btn-secondary whitespace-nowrap"
								title="새 유형 추가"
							>
								+ 새 유형
							</button>
						</div>
					</div>

					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						<div>
							<label for="scheduled" class="block text-sm font-medium text-gray-700 mb-1">
								일시
							</label>
							<input
								id="scheduled"
								type="datetime-local"
								bind:value={scheduledAt}
								class="input"
							/>
						</div>

						<div>
							<label for="location" class="block text-sm font-medium text-gray-700 mb-1">
								장소
							</label>
							<input
								id="location"
								type="text"
								bind:value={location}
								class="input"
								placeholder="회의 장소"
							/>
						</div>
					</div>
				</div>
			</section>

			<!-- Attendees -->
			<section class="card">
				<h2 class="text-lg font-medium text-gray-900 mb-4">참석자</h2>

				<!-- Search Input with Autocomplete -->
				<div class="mb-4 relative">
					<label for="attendee-search" class="block text-sm font-medium text-gray-700 mb-1">
						참석자 검색
					</label>
					<input
						id="attendee-search"
						type="text"
						value={searchQuery}
						oninput={searchContacts}
						placeholder="이름으로 검색..."
						class="input"
						autocomplete="off"
					/>

					<!-- Suggestions Dropdown -->
					{#if showSuggestions && contactSuggestions.length > 0}
						<ul class="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
							{#each contactSuggestions as contact (contact.id)}
								<li>
									<button
										type="button"
										onclick={() => addAttendee(contact)}
										class="w-full text-left px-4 py-2 hover:bg-primary-50 focus:bg-primary-50 focus:outline-none"
									>
										<div class="flex flex-col">
											<span class="font-medium text-gray-900">{contact.name}</span>
											{#if contact.organization || contact.role}
												<span class="text-sm text-gray-500">
													{contact.organization || ''}{contact.organization && contact.role ? ' - ' : ''}{contact.role || ''}
												</span>
											{/if}
										</div>
									</button>
								</li>
							{/each}
						</ul>
					{:else if showSuggestions && searchQuery && !isSearching}
						<div class="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg p-3">
							<p class="text-sm text-gray-500">검색 결과가 없습니다</p>
						</div>
					{/if}
				</div>

				<!-- Selected Attendees -->
				{#if selectedAttendees.length > 0}
					<div class="mb-4">
						<div class="block text-sm font-medium text-gray-700 mb-2">
							선택된 참석자 ({selectedAttendees.length}명)
						</div>
						<div class="flex flex-wrap gap-2">
							{#each selectedAttendees as attendeeId (attendeeId)}
								{@const contact = getContactById(attendeeId)}
								{#if contact}
									<span class="inline-flex items-center gap-1 px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm">
										{contact.name}
										<button
											type="button"
											onclick={() => removeAttendee(attendeeId)}
											class="ml-1 hover:text-primary-900 focus:outline-none"
											title="제거"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
											</svg>
										</button>
									</span>
								{/if}
							{/each}
						</div>
					</div>
				{/if}

				<!-- Quick Select from All Contacts (Optional) -->
				{#if contacts.length > 0}
					<details class="mt-4">
						<summary class="text-sm text-gray-600 cursor-pointer hover:text-gray-800">
							전체 연락처 목록에서 선택 ({contacts.length}명)
						</summary>
						<div class="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto border border-gray-200 rounded p-2">
							{#each contacts as contact (contact.id)}
								<label
									class="flex items-center p-2 rounded hover:bg-gray-50 cursor-pointer {selectedAttendees.includes(
										contact.id
									)
										? 'bg-primary-50'
										: ''}"
								>
									<input
										type="checkbox"
										checked={selectedAttendees.includes(contact.id)}
										onchange={() => toggleAttendee(contact.id)}
										class="h-4 w-4 text-primary-600 rounded border-gray-300"
									/>
									<span class="ml-2 text-sm text-gray-700">{contact.name}</span>
								</label>
							{/each}
						</div>
					</details>
				{:else}
					<p class="text-sm text-gray-500">사용 가능한 연락처가 없습니다. 먼저 연락처를 추가하세요.</p>
				{/if}
			</section>

			<!-- Agendas -->
			<section class="card">
				<div class="flex justify-between items-center mb-4">
					<h2 class="text-lg font-medium text-gray-900">안건</h2>
					<button type="button" onclick={addAgenda} class="btn btn-secondary text-sm">
						+ 안건 추가
					</button>
				</div>

				<!-- Text Input Mode -->
				<div class="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
					<label for="agendaText" class="block text-sm font-medium text-gray-700 mb-2">
						안건 텍스트 입력
					</label>
					<textarea
						id="agendaText"
						bind:value={agendaTextInput}
						oninput={() => isAutoPreviewEnabled && debouncedParse(agendaTextInput)}
						placeholder="안건을 입력하세요. 예:
1. 예산안 심의
2. 신규 사업 검토
3. 인사 발령 승인"
						rows="5"
						class="input mb-3"
					></textarea>
					<div class="flex items-center gap-4">
						<button
							type="button"
							onclick={parseAgendas}
							disabled={isParsing || !agendaTextInput.trim()}
							class="btn btn-primary text-sm disabled:opacity-50"
						>
							{#if isParsing}
								파싱 중...
							{:else}
								AI로 파싱
							{/if}
						</button>
						<label class="inline-flex items-center">
							<input type="checkbox" bind:checked={isAutoPreviewEnabled} class="rounded text-primary-600" />
							<span class="ml-2 text-sm text-gray-600">자동 미리보기</span>
						</label>
					</div>
					<p class="mt-2 text-xs text-gray-500">
						번호가 있는 목록이나 항목별로 줄바꿈하여 입력하면 자동으로 안건 목록으로 변환됩니다.
					</p>
				</div>

				{#if showAgendaEditor && agendas.length > 0 && !agendaTextInput}
					<div class="mb-4">
						<button
							type="button"
							onclick={() => { showAgendaEditor = false; }}
							class="btn btn-secondary text-sm"
						>
							<ArrowLeft class="w-4 h-4 inline mr-1" />
							텍스트 입력으로 돌아가기
						</button>
					</div>
					<AgendaEditor
						items={agendas.map(agendaToEditorItem)}
						onItemsChange={handleEditorItemsChange}
					/>
				{:else}
					<div class="space-y-4">
						{#each agendas as agenda, index (agenda.id)}
							<div class="border border-gray-200 rounded-lg p-4">
								<div class="flex items-start justify-between mb-3">
									<span class="text-sm font-medium text-gray-500">안건 {index + 1}</span>
									<div class="flex items-center space-x-1">
										<button
											type="button"
											onclick={() => moveAgenda(index, 'up')}
											disabled={index === 0}
											class="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
											title="위로 이동"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
											</svg>
										</button>
										<button
											type="button"
											onclick={() => moveAgenda(index, 'down')}
											disabled={index === agendas.length - 1}
											class="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
											title="아래로 이동"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
											</svg>
										</button>
										<button
											type="button"
											onclick={() => removeAgenda(agenda.id)}
											disabled={agendas.length <= 1}
											class="p-1 text-red-400 hover:text-red-600 disabled:opacity-30"
											title="제거"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
											</svg>
										</button>
									</div>
								</div>

								<div class="space-y-3">
									<input
										type="text"
										bind:value={agenda.title}
										placeholder="안건 제목"
										class="input"
									/>
									<textarea
										bind:value={agenda.description}
										placeholder="설명 (선택사항)"
										rows="2"
										class="input"
									></textarea>

									<!-- Questions Section -->
									<div class="mt-4 pl-4 border-l-2 border-gray-200">
										<div class="flex items-center justify-between mb-2">
											<h5 class="text-sm font-medium text-gray-700">토의 질문</h5>
											<div class="flex gap-2">
												<button
													type="button"
													onclick={() => addQuestion(agenda.id)}
													class="text-xs px-2 py-1 text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded"
													title="질문 추가"
												>
													+ 질문 추가
												</button>
												<button
													type="button"
													onclick={() => regenerateQuestions(agenda.id)}
													disabled={!agenda.title.trim() || generatingQuestionsFor === agenda.id}
													class="text-xs px-2 py-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
													title="AI 질문 생성"
												>
													{#if generatingQuestionsFor === agenda.id}
														생성 중...
													{:else}
														<Sparkles class="w-4 h-4 inline mr-1" />
														AI 질문 생성
													{/if}
												</button>
											</div>
										</div>

										{#if agenda.questions.length === 0}
											<p class="text-xs text-gray-400 italic">질문이 없습니다</p>
										{:else}
											<div class="space-y-2">
												{#each agenda.questions as question, qi}
													<div class="flex items-center gap-2 group">
														<input
															type="text"
															bind:value={question.question}
															placeholder="질문 내용"
															class="input text-sm flex-1"
														/>
														{#if question.is_generated}
															<span
																class="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded whitespace-nowrap flex items-center gap-1"
																title="AI 생성"
															>
																<Sparkles class="w-3 h-3" />
																AI
															</span>
														{/if}
														<button
															type="button"
															onclick={() => removeQuestion(agenda.id, qi)}
															class="p-1 text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
															title="질문 삭제"
														>
															<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
															</svg>
														</button>
													</div>
												{/each}
											</div>
										{/if}
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Submit -->
			<div class="flex justify-end space-x-4">
				<a href="/meetings" class="btn btn-secondary">
					취소
				</a>
				<button
					type="submit"
					disabled={isSaving}
					class="btn btn-primary disabled:opacity-50"
				>
					{#if isSaving}
						생성 중...
					{:else}
						회의 생성
					{/if}
				</button>
			</div>
		</form>
	{/if}
</div>

<!-- New Meeting Type Modal -->
{#if showNewTypeModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
			<h3 class="text-lg font-semibold text-gray-900 mb-4">새 회의 유형 추가</h3>

			<div class="mb-4">
				<label for="newTypeName" class="block text-sm font-medium text-gray-700 mb-1">
					유형 이름 <span class="text-red-500">*</span>
				</label>
				<input
					id="newTypeName"
					type="text"
					bind:value={newTypeName}
					placeholder="예: 북부, 전국, 일산"
					class="input"
					maxlength="50"
					autofocus
					onkeydown={(e) => {
						if (e.key === 'Enter' && !isCreatingType) {
							e.preventDefault();
							createNewMeetingType();
						} else if (e.key === 'Escape') {
							e.preventDefault();
							closeNewTypeModal();
						}
					}}
				/>
			</div>

			{#if error}
				<div class="rounded-md bg-red-50 p-3 mb-4">
					<p class="text-sm text-red-800">{error}</p>
				</div>
			{/if}

			<div class="flex justify-end space-x-3">
				<button
					type="button"
					onclick={closeNewTypeModal}
					disabled={isCreatingType}
					class="btn btn-secondary disabled:opacity-50"
				>
					취소
				</button>
				<button
					type="button"
					onclick={createNewMeetingType}
					disabled={isCreatingType || !newTypeName.trim()}
					class="btn btn-primary disabled:opacity-50"
				>
					{#if isCreatingType}
						생성 중...
					{:else}
						추가
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
