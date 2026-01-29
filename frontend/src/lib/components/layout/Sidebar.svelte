<script lang="ts">
	import { page } from '$app/stores';
	import { Home, Calendar, Users, Settings, ChevronLeft, Menu } from 'lucide-svelte';

	interface Props {
		collapsed?: boolean;
		onToggle?: () => void;
	}

	let { collapsed = false, onToggle }: Props = $props();

	const navItems = [
		{ href: '/', icon: Home, label: '대시보드' },
		{ href: '/meetings', icon: Calendar, label: '회의' },
		{ href: '/contacts', icon: Users, label: '연락처' }
	];

	function isActive(href: string): boolean {
		if (href === '/') {
			return $page.url.pathname === '/';
		}
		return $page.url.pathname.startsWith(href);
	}
</script>

<aside
	class="flex flex-col h-full bg-white dark:bg-base-dark border-r border-gray-200 dark:border-surface transition-all duration-normal
		{collapsed ? 'w-16' : 'w-sidebar'}"
>
	<!-- Header -->
	<div class="flex items-center justify-between h-header px-4 border-b border-gray-200 dark:border-surface">
		{#if !collapsed}
			<a href="/" class="text-lg font-bold text-primary-600 dark:text-primary-400">
				MAX Meeting
			</a>
		{/if}
		<button
			type="button"
			onclick={onToggle}
			class="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-text-muted dark:hover:text-text dark:hover:bg-surface transition-colors touch-target"
			aria-label={collapsed ? '사이드바 펼치기' : '사이드바 접기'}
		>
			{#if collapsed}
				<Menu class="w-5 h-5" />
			{:else}
				<ChevronLeft class="w-5 h-5" />
			{/if}
		</button>
	</div>

	<!-- Navigation -->
	<nav class="flex-1 p-3 space-y-1">
		{#each navItems as item}
			<a
				href={item.href}
				class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-fast touch-target
					{isActive(item.href)
						? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300'
						: 'text-gray-700 hover:bg-gray-100 dark:text-text-muted dark:hover:bg-surface'}
					{collapsed ? 'justify-center' : ''}"
				title={collapsed ? item.label : undefined}
			>
				<svelte:component this={item.icon} class="w-5 h-5 flex-shrink-0" />
				{#if !collapsed}
					<span class="font-medium">{item.label}</span>
				{/if}
			</a>
		{/each}
	</nav>

	<!-- Footer -->
	<div class="p-3 border-t border-gray-200 dark:border-surface">
		<a
			href="/settings"
			class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-gray-100 dark:text-text-muted dark:hover:bg-surface transition-colors touch-target
				{collapsed ? 'justify-center' : ''}"
			title={collapsed ? '설정' : undefined}
		>
			<Settings class="w-5 h-5 flex-shrink-0" />
			{#if !collapsed}
				<span class="font-medium">설정</span>
			{/if}
		</a>
	</div>
</aside>
