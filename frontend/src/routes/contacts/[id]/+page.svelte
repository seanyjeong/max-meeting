<script lang="ts">
	/**
	 * Contact Detail/Edit Page
	 *
	 * - View and edit contact details
	 * - Delete option
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		contactsStore,
		selectedContact,
		contactsLoading,
		contactsError
	} from '$lib/stores/contacts';
	import { Button, Input, Card, Modal, Breadcrumb, LoadingSpinner } from '$lib/components';
	import type { ContactUpdate } from '$lib/stores/contacts';

	let contactId = $derived(parseInt($page.params.id || '', 10));

	let formData = $state<ContactUpdate>({
		name: '',
		role: '',
		organization: '',
		phone: '',
		email: ''
	});

	let errors = $state<Record<string, string>>({});
	let isSaving = $state(false);
	let showDeleteModal = $state(false);
	let isDeleting = $state(false);
	let isLoaded = $state(false);

	const breadcrumbItems = $derived([
		{ label: 'Home', href: '/' },
		{ label: '연락처', href: '/contacts' },
		{ label: $selectedContact?.name || '연락처 상세', href: `/contacts/${contactId}` }
	]);

	onMount(async () => {
		const contact = await contactsStore.fetchContact(contactId);
		if (contact) {
			formData = {
				name: contact.name,
				role: contact.role || '',
				organization: contact.organization || '',
				phone: contact.phone || '',
				email: contact.email || ''
			};
			isLoaded = true;
		} else {
			goto('/contacts');
		}
	});

	function validate(): boolean {
		const newErrors: Record<string, string> = {};

		if (!formData.name?.trim()) {
			newErrors.name = '이름은 필수입니다';
		}

		if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
			newErrors.email = '유효한 이메일 주소를 입력하세요';
		}

		if (formData.phone && !/^[\d\-+\s()]+$/.test(formData.phone)) {
			newErrors.phone = '유효한 전화번호를 입력하세요';
		}

		errors = newErrors;
		return Object.keys(newErrors).length === 0;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!validate()) return;

		isSaving = true;
		const updated = await contactsStore.updateContact(contactId, {
			name: formData.name?.trim(),
			role: formData.role?.trim() || undefined,
			organization: formData.organization?.trim() || undefined,
			phone: formData.phone?.trim() || undefined,
			email: formData.email?.trim() || undefined
		});
		isSaving = false;

		if (updated) {
			goto('/contacts');
		}
	}

	function handleCancel() {
		goto('/contacts');
	}

	function handleDeleteClick() {
		showDeleteModal = true;
	}

	async function handleConfirmDelete() {
		isDeleting = true;
		const success = await contactsStore.deleteContact(contactId);
		isDeleting = false;

		if (success) {
			goto('/contacts');
		} else {
			showDeleteModal = false;
		}
	}

	function handleCancelDelete() {
		showDeleteModal = false;
	}
</script>

<svelte:head>
	<title>{$selectedContact?.name || '연락처'} - MAX Meeting</title>
</svelte:head>

<div class="space-y-6">
	<Breadcrumb items={breadcrumbItems} />

	{#if !isLoaded}
		<div class="flex justify-center py-12">
			<LoadingSpinner size="lg" />
		</div>
	{:else}
		<div class="flex items-center justify-between">
			<h1 class="text-2xl font-bold text-gray-900">연락처 수정</h1>
			<Button variant="danger" onclick={handleDeleteClick}>
				<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
					/>
				</svg>
				삭제
			</Button>
		</div>

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

		<Card>
			<form onsubmit={handleSubmit} class="space-y-6">
				<Input
					label="이름"
					name="name"
					required
					bind:value={formData.name}
					error={errors.name}
					placeholder="홍길동"
				/>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<Input
						label="조직/회사"
						name="organization"
						bind:value={formData.organization}
						placeholder="회사명"
					/>

					<Input
						label="직책/역할"
						name="role"
						bind:value={formData.role}
						placeholder="대리"
					/>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<Input
						label="전화번호"
						name="phone"
						type="tel"
						bind:value={formData.phone}
						error={errors.phone}
						placeholder="010-1234-5678"
					/>

					<Input
						label="이메일"
						name="email"
						type="email"
						bind:value={formData.email}
						error={errors.email}
						placeholder="example@email.com"
					/>
				</div>

				<div class="flex justify-end gap-3 pt-4 border-t">
					<Button variant="secondary" type="button" onclick={handleCancel}>취소</Button>
					<Button variant="primary" type="submit" loading={isSaving} disabled={$contactsLoading}>
						저장
					</Button>
				</div>
			</form>
		</Card>
	{/if}
</div>

<!-- Delete Confirmation Modal -->
<Modal bind:open={showDeleteModal} title="연락처 삭제" size="sm">
	<p class="text-gray-600">
		<strong>{$selectedContact?.name}</strong> 연락처를 삭제하시겠습니까?
	</p>
	<p class="text-sm text-gray-500 mt-2">이 작업은 되돌릴 수 없습니다.</p>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={handleCancelDelete} disabled={isDeleting}>취소</Button>
			<Button variant="danger" onclick={handleConfirmDelete} loading={isDeleting}>삭제</Button>
		</div>
	{/snippet}
</Modal>
