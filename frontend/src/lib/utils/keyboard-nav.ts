/**
 * 화살표 키로 목록 항목 탐색
 */
export function createListNavigation(
	getItems: () => HTMLElement[],
	options: {
		wrap?: boolean;
		orientation?: 'vertical' | 'horizontal';
	} = {}
) {
	const { wrap = true, orientation = 'vertical' } = options;

	const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft';
	const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight';

	function handleKeyDown(e: KeyboardEvent) {
		const items = getItems();
		const currentIndex = items.findIndex((item) => item === document.activeElement);

		if (e.key === nextKey) {
			e.preventDefault();
			const nextIndex = wrap
				? (currentIndex + 1) % items.length
				: Math.min(currentIndex + 1, items.length - 1);
			items[nextIndex]?.focus();
		} else if (e.key === prevKey) {
			e.preventDefault();
			const prevIndex = wrap
				? (currentIndex - 1 + items.length) % items.length
				: Math.max(currentIndex - 1, 0);
			items[prevIndex]?.focus();
		} else if (e.key === 'Home') {
			e.preventDefault();
			items[0]?.focus();
		} else if (e.key === 'End') {
			e.preventDefault();
			items[items.length - 1]?.focus();
		}
	}

	return { handleKeyDown };
}
