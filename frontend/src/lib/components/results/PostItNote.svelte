<script lang="ts">
	interface Props {
		content: string;
		agendaTitle?: string;
		color?: 'yellow' | 'pink' | 'green' | 'blue';
		small?: boolean;
	}

	let { content, agendaTitle, color = 'yellow', small = false }: Props = $props();

	const colorClasses = {
		yellow: 'bg-amber-100 border-amber-200',
		pink: 'bg-pink-100 border-pink-200',
		green: 'bg-emerald-100 border-emerald-200',
		blue: 'bg-sky-100 border-sky-200'
	};

	const headerColors = {
		yellow: 'bg-amber-200/50',
		pink: 'bg-pink-200/50',
		green: 'bg-emerald-200/50',
		blue: 'bg-sky-200/50'
	};
</script>

<div class="postit {colorClasses[color]}" class:small>
	<div class="postit-tape {headerColors[color]}"></div>
	{#if agendaTitle}
		<div class="postit-header">{agendaTitle}</div>
	{/if}
	<div class="postit-content">
		{content}
	</div>
</div>

<style>
	.postit {
		position: relative;
		padding: 1.25rem 1rem 1rem;
		min-width: 180px;
		max-width: 280px;
		border-radius: 0 0 0.25rem 0.25rem;
		box-shadow:
			2px 3px 8px rgba(0, 0, 0, 0.08),
			0 1px 2px rgba(0, 0, 0, 0.04);
		transform: rotate(-0.5deg);
		border: 1px solid;
		border-top: none;
	}

	.postit.small {
		min-width: 140px;
		max-width: 200px;
		padding: 1rem 0.75rem 0.75rem;
	}

	.postit-tape {
		position: absolute;
		top: -8px;
		left: 50%;
		transform: translateX(-50%);
		width: 60px;
		height: 16px;
		border-radius: 2px;
		opacity: 0.9;
	}

	.postit-header {
		font-size: 0.6875rem;
		color: #6b7280;
		margin-bottom: 0.5rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.025em;
	}

	.postit.small .postit-header {
		font-size: 0.625rem;
		margin-bottom: 0.375rem;
	}

	.postit-content {
		font-size: 0.875rem;
		line-height: 1.5;
		color: #374151;
		white-space: pre-wrap;
		word-break: break-word;
	}

	.postit.small .postit-content {
		font-size: 0.8125rem;
		line-height: 1.4;
	}

	/* Hover effect */
	.postit {
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}

	.postit:hover {
		transform: rotate(0deg) translateY(-2px);
		box-shadow:
			3px 5px 12px rgba(0, 0, 0, 0.1),
			0 2px 4px rgba(0, 0, 0, 0.06);
	}
</style>
