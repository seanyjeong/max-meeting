<script lang="ts">
	interface Props {
		href?: string;
		label?: string;
	}

	let { href = '#main-content', label = '본문으로 바로가기' }: Props = $props();
</script>

<a
	{href}
	class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50
           focus:px-4 focus:py-2 focus:bg-primary-600 focus:text-white focus:rounded-lg
           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
>
	{label}
</a>
