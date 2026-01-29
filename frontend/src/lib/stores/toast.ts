import { writable } from 'svelte/store';

export interface ToastMessage {
	id: string;
	message: string;
	type: 'success' | 'error' | 'warning' | 'info';
	duration?: number;
}

function createToastStore() {
	const { subscribe, update } = writable<ToastMessage[]>([]);

	return {
		subscribe,

		show(message: string, type: ToastMessage['type'] = 'info', duration = 5000) {
			const id = crypto.randomUUID();
			update(toasts => [...toasts, { id, message, type, duration }]);

			if (duration > 0) {
				setTimeout(() => this.dismiss(id), duration);
			}

			return id;
		},

		success(message: string, duration?: number) {
			return this.show(message, 'success', duration);
		},

		error(message: string, duration?: number) {
			return this.show(message, 'error', duration);
		},

		warning(message: string, duration?: number) {
			return this.show(message, 'warning', duration);
		},

		info(message: string, duration?: number) {
			return this.show(message, 'info', duration);
		},

		dismiss(id: string) {
			update(toasts => toasts.filter(t => t.id !== id));
		},

		clear() {
			update(() => []);
		}
	};
}

export const toast = createToastStore();
