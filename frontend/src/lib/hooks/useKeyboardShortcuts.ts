/**
 * useKeyboardShortcuts - Keyboard shortcut hook for Svelte 5
 *
 * Usage:
 * ```ts
 * import { useKeyboardShortcuts } from '$lib/hooks/useKeyboardShortcuts';
 *
 * const { registerShortcut, unregisterShortcut, showHelp } = useKeyboardShortcuts();
 *
 * registerShortcut({
 *   key: 's',
 *   modifiers: ['ctrl'],
 *   description: 'Save',
 *   action: () => save()
 * });
 * ```
 */
import { onMount, onDestroy } from 'svelte';

export interface KeyboardShortcut {
	key: string;
	modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[];
	description: string;
	action: () => void;
	category?: string;
	enabled?: boolean;
}

interface UseKeyboardShortcutsOptions {
	disableInInputs?: boolean;
	globalHelp?: boolean;
}

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}) {
	const { disableInInputs = true, globalHelp = true } = options;

	let shortcuts: KeyboardShortcut[] = [];
	let showHelp = $state(false);

	function handleKeyDown(e: KeyboardEvent) {
		// Don't capture shortcuts when typing in inputs
		if (disableInInputs) {
			const target = e.target as HTMLElement;
			if (
				target.tagName === 'INPUT' ||
				target.tagName === 'TEXTAREA' ||
				target.isContentEditable
			) {
				// Allow Escape in inputs
				if (e.key !== 'Escape') return;
			}
		}

		// Check for ? to show help
		if (globalHelp && e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey) {
			e.preventDefault();
			showHelp = !showHelp;
			return;
		}

		// Escape closes help
		if (e.key === 'Escape' && showHelp) {
			e.preventDefault();
			showHelp = false;
			return;
		}

		// Check registered shortcuts
		for (const shortcut of shortcuts) {
			if (shortcut.enabled === false) continue;

			const keyMatches = e.key.toLowerCase() === shortcut.key.toLowerCase();

			const modifiersMatch =
				(!shortcut.modifiers || shortcut.modifiers.length === 0)
					? !e.ctrlKey && !e.altKey && !e.metaKey && !e.shiftKey
					: shortcut.modifiers.every(mod => {
							switch (mod) {
								case 'ctrl': return e.ctrlKey;
								case 'alt': return e.altKey;
								case 'shift': return e.shiftKey;
								case 'meta': return e.metaKey;
								default: return false;
							}
						}) &&
						(!shortcut.modifiers.includes('ctrl') ? !e.ctrlKey : true) &&
						(!shortcut.modifiers.includes('alt') ? !e.altKey : true) &&
						(!shortcut.modifiers.includes('shift') ? !e.shiftKey : true) &&
						(!shortcut.modifiers.includes('meta') ? !e.metaKey : true);

			if (keyMatches && modifiersMatch) {
				e.preventDefault();
				shortcut.action();
				return;
			}
		}
	}

	function registerShortcut(shortcut: KeyboardShortcut) {
		// Remove existing shortcut with same key combination
		unregisterShortcut(shortcut.key, shortcut.modifiers);
		shortcuts.push(shortcut);
	}

	function unregisterShortcut(key: string, modifiers?: string[]) {
		shortcuts = shortcuts.filter(s => {
			if (s.key !== key) return true;
			if (!modifiers && !s.modifiers) return false;
			if (!modifiers || !s.modifiers) return true;
			return JSON.stringify(s.modifiers.sort()) !== JSON.stringify(modifiers.sort());
		});
	}

	function getShortcuts(): KeyboardShortcut[] {
		return [...shortcuts];
	}

	function getShortcutsByCategory(): Record<string, KeyboardShortcut[]> {
		const groups: Record<string, KeyboardShortcut[]> = {};
		for (const shortcut of shortcuts) {
			const category = shortcut.category || '기타';
			if (!groups[category]) groups[category] = [];
			groups[category].push(shortcut);
		}
		return groups;
	}

	// Setup event listener
	onMount(() => {
		window.addEventListener('keydown', handleKeyDown);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeyDown);
		shortcuts = [];
	});

	return {
		registerShortcut,
		unregisterShortcut,
		getShortcuts,
		getShortcutsByCategory,
		get showHelp() { return showHelp; },
		set showHelp(value: boolean) { showHelp = value; }
	};
}

/**
 * Format shortcut key for display
 */
export function formatShortcutKey(shortcut: KeyboardShortcut): string {
	const parts: string[] = [];

	if (shortcut.modifiers) {
		// Mac uses ⌘, Windows uses Ctrl
		const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;

		if (shortcut.modifiers.includes('meta')) parts.push(isMac ? '⌘' : 'Win');
		if (shortcut.modifiers.includes('ctrl')) parts.push(isMac ? '⌃' : 'Ctrl');
		if (shortcut.modifiers.includes('alt')) parts.push(isMac ? '⌥' : 'Alt');
		if (shortcut.modifiers.includes('shift')) parts.push(isMac ? '⇧' : 'Shift');
	}

	// Format special keys
	const keyNames: Record<string, string> = {
		' ': 'Space',
		ArrowUp: '↑',
		ArrowDown: '↓',
		ArrowLeft: '←',
		ArrowRight: '→',
		Enter: '⏎',
		Escape: 'Esc',
		Backspace: '⌫',
		Delete: '⌦',
		Tab: '⇥'
	};

	const displayKey = keyNames[shortcut.key] || shortcut.key.toUpperCase();
	parts.push(displayKey);

	return parts.join('+');
}
