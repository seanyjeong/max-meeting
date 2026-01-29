<script lang="ts">
	/**
	 * Contacts List Page
	 *
	 * - Search with pg_trgm backend
	 * - List view with edit/delete actions
	 * - Link to create new contact
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { contactsStore, contacts, contactsLoading, contactsError } from '$lib/stores/contacts';
	import { Button, Input, Card, Modal, LoadingSpinner } from '$lib/components';
	import type { Contact } from '$lib/stores/contacts';

	let searchQuery = $state('');
	let searchTimeout: ReturnType<typeof setTimeout>;

	let showDeleteModal = $state(false);
	let contactToDelete = $state<Contact | null>(null);
	let isDeleting = $state(false);

	onMount(() => {
		contactsStore.fetchContacts();
	});

	function handleSearch() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			contactsStore.fetchContacts(searchQuery);
		}, 300);
	}

	function handleCreateNew() {
		goto('/contacts/new');
	}

	function handleEdit(contact: Contact) {
		goto(`/contacts/${contact.id}`);
	}

	function handleDeleteClick(contact: Contact) {
		contactToDelete = contact;
		showDeleteModal = true;
	}

	async function handleConfirmDelete() {
		if (!contactToDelete) return;

		isDeleting = true;
		const success = await contactsStore.deleteContact(contactToDelete.id);
		isDeleting = false;

		if (success) {
			showDeleteModal = false;
			contactToDelete = null;
		}
	}

	function handleCancelDelete() {
		showDeleteModal = false;
		contactToDelete = null;
	}
</script>

<svelte:head>
	<title>연락처 - MAX Meeting</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
		<h1 class="text-2xl font-bold text-gray-900">연락처</h1>
		<Button variant="primary" onclick={handleCreateNew}>
			<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 4v16m8-8H4"
				/>
			</svg>
			새 연락처
		</Button>
	</div>

	<!-- Search -->
	<Card>
		<div class="flex gap-4">
			<div class="flex-1">
				<Input
					type="search"
					placeholder="이름, 조직, 직책으로 검색..."
					bind:value={searchQuery}
					oninput={handleSearch}
				/>
			</div>
		</div>
	</Card>

	<!-- Error -->
	{#if $contactsError}
		<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700" role="alert">
			<p>{$contactsError}</p>
			<button
				type="button"
				class="text-sm underline mt-2"
				onclick={() => contactsStore.clearError()}
			>
				닫기
			</button>
		</div>
	{/if}

	<!-- Loading -->
	{#if $contactsLoading && $contacts.length === 0}
		<div class="flex justify-center py-12">
			<LoadingSpinner size="lg" />
		</div>
	{/if}

	<!-- Empty State -->
	{#if !$contactsLoading && $contacts.length === 0}
		<Card>
			<div class="text-center py-12">
				<svg
					class="w-16 h-16 mx-auto text-gray-400 mb-4"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.5"
						d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
					/>
				</svg>
				<h3 class="text-lg font-medium text-gray-900 mb-2">연락처가 없습니다</h3>
				<p class="text-gray-500 mb-6">첫 번째 연락처를 추가해보세요.</p>
				<Button variant="primary" onclick={handleCreateNew}>새 연락처 추가</Button>
			</div>
		</Card>
	{/if}

	<!-- Contacts List -->
	{#if $contacts.length > 0}
		<div class="bg-white shadow-sm rounded-lg overflow-hidden">
			<ul class="divide-y divide-gray-200" role="list">
				{#each $contacts as contact (contact.id)}
					<li class="hover:bg-gray-50 transition-colors">
						<div class="px-4 py-4 sm:px-6 flex items-center justify-between">
							<div class="flex-1 min-w-0">
								<button
									type="button"
									class="text-left w-full"
									onclick={() => handleEdit(contact)}
								>
									<p class="text-sm font-medium text-primary-600 truncate">
										{contact.name}
									</p>
									<div class="mt-1 flex items-center gap-4 text-sm text-gray-500">
										{#if contact.organization}
											<span>{contact.organization}</span>
										{/if}
										{#if contact.role}
											<span class="text-gray-400">|</span>
											<span>{contact.role}</span>
										{/if}
									</div>
								</button>
							</div>
							<div class="flex items-center gap-2 ml-4">
								<button
									type="button"
									class="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors min-w-touch min-h-touch flex items-center justify-center"
									onclick={() => handleEdit(contact)}
									aria-label="수정"
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
										/>
									</svg>
								</button>
								<button
									type="button"
									class="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors min-w-touch min-h-touch flex items-center justify-center"
									onclick={() => handleDeleteClick(contact)}
									aria-label="삭제"
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
										/>
									</svg>
								</button>
							</div>
						</div>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>

<!-- Delete Confirmation Modal -->
<Modal bind:open={showDeleteModal} title="연락처 삭제" size="sm">
	<p class="text-gray-600">
		<strong>{contactToDelete?.name}</strong> 연락처를 삭제하시겠습니까?
	</p>
	<p class="text-sm text-gray-500 mt-2">이 작업은 되돌릴 수 없습니다.</p>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={handleCancelDelete} disabled={isDeleting}>취소</Button>
			<Button variant="danger" onclick={handleConfirmDelete} loading={isDeleting}>삭제</Button>
		</div>
	{/snippet}
</Modal>
