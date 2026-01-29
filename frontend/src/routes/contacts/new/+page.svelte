<script lang="ts">
	/**
	 * Create New Contact Page
	 *
	 * - Form for contact details
	 * - Validation
	 * - Save and redirect
	 */
	import { goto } from '$app/navigation';
	import { contactsStore, contactsLoading, contactsError } from '$lib/stores/contacts';
	import { Button, Input, Card, Breadcrumb } from '$lib/components';
	import type { ContactCreate } from '$lib/stores/contacts';

	let formData = $state<ContactCreate>({
		name: '',
		role: '',
		organization: '',
		phone: '',
		email: ''
	});

	let errors = $state<Record<string, string>>({});
	let isSaving = $state(false);

	const breadcrumbItems = [
		{ label: 'Home', href: '/' },
		{ label: '연락처', href: '/contacts' },
		{ label: '새 연락처', href: '/contacts/new' }
	];

	function validate(): boolean {
		const newErrors: Record<string, string> = {};

		if (!formData.name.trim()) {
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
		const contact = await contactsStore.createContact({
			name: formData.name.trim(),
			role: formData.role?.trim() || undefined,
			organization: formData.organization?.trim() || undefined,
			phone: formData.phone?.trim() || undefined,
			email: formData.email?.trim() || undefined
		});
		isSaving = false;

		if (contact) {
			goto('/contacts');
		}
	}

	function handleCancel() {
		goto('/contacts');
	}
</script>

<svelte:head>
	<title>새 연락처 - MAX Meeting</title>
</svelte:head>

<div class="space-y-6">
	<Breadcrumb items={breadcrumbItems} />

	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold text-gray-900">새 연락처</h1>
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
</div>
