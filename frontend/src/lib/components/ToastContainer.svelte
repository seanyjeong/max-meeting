<script lang="ts">
	import { toast } from '$lib/stores/toast';
	import Toast from './Toast.svelte';

	let toasts = $derived($toast);
</script>

<div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
	{#each toasts as toastMessage (toastMessage.id)}
		<Toast
			message={toastMessage.message}
			type={toastMessage.type}
			duration={toastMessage.duration}
			onclose={() => toast.dismiss(toastMessage.id)}
		/>
	{/each}
</div>
