/**
 * 모달 내부에 포커스를 가두는 유틸리티
 */
export function createFocusTrap(container: HTMLElement) {
	const focusableSelectors = [
		'button:not([disabled])',
		'input:not([disabled])',
		'select:not([disabled])',
		'textarea:not([disabled])',
		'a[href]',
		'[tabindex]:not([tabindex="-1"])'
	].join(', ');

	let previouslyFocused: HTMLElement | null = null;

	function getFocusableElements(): HTMLElement[] {
		return Array.from(container.querySelectorAll(focusableSelectors));
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key !== 'Tab') return;

		const focusable = getFocusableElements();
		if (focusable.length === 0) return;

		const first = focusable[0];
		const last = focusable[focusable.length - 1];

		if (e.shiftKey && document.activeElement === first) {
			e.preventDefault();
			last.focus();
		} else if (!e.shiftKey && document.activeElement === last) {
			e.preventDefault();
			first.focus();
		}
	}

	function activate() {
		previouslyFocused = document.activeElement as HTMLElement;
		container.addEventListener('keydown', handleKeyDown);

		// 첫 번째 포커스 가능 요소에 포커스
		const focusable = getFocusableElements();
		if (focusable.length > 0) {
			focusable[0].focus();
		}
	}

	function deactivate() {
		container.removeEventListener('keydown', handleKeyDown);
		previouslyFocused?.focus();
	}

	return { activate, deactivate };
}
