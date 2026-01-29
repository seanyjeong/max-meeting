/**
 * Contacts Store - Contact state management for meeting attendees
 */
import { writable, derived } from 'svelte/store';
import { api } from '$lib/api';

export interface Contact {
	id: number;
	name: string;
	role: string | null;
	organization: string | null;
	phone?: string;
	email?: string;
	created_at: string;
	updated_at: string;
}

export interface ContactCreate {
	name: string;
	role?: string;
	organization?: string;
	phone?: string;
	email?: string;
}

export interface ContactUpdate {
	name?: string;
	role?: string;
	organization?: string;
	phone?: string;
	email?: string;
}

interface ContactsState {
	contacts: Contact[];
	selectedContact: Contact | null;
	isLoading: boolean;
	error: string | null;
	searchQuery: string;
	total: number;
}

function createContactsStore() {
	const { subscribe, set, update } = writable<ContactsState>({
		contacts: [],
		selectedContact: null,
		isLoading: false,
		error: null,
		searchQuery: '',
		total: 0
	});

	return {
		subscribe,

		async fetchContacts(query?: string, limit = 50, offset = 0): Promise<void> {
			update((state) => ({ ...state, isLoading: true, error: null }));

			try {
				const params: Record<string, string | number | undefined> = {
					limit,
					offset
				};
				if (query) {
					params.q = query;
				}

				const response = await api.get<{ data: Contact[]; meta: { total: number } }>(
					'/contacts',
					params
				);

				update((state) => ({
					...state,
					contacts: response.data,
					total: response.meta.total,
					isLoading: false,
					searchQuery: query || ''
				}));
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to fetch contacts';
				update((state) => ({ ...state, isLoading: false, error: message }));
			}
		},

		async fetchContact(id: number): Promise<Contact | null> {
			update((state) => ({ ...state, isLoading: true, error: null }));

			try {
				const response = await api.get<{ data: Contact }>(`/contacts/${id}`);
				update((state) => ({
					...state,
					selectedContact: response.data,
					isLoading: false
				}));
				return response.data;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to fetch contact';
				update((state) => ({ ...state, isLoading: false, error: message }));
				return null;
			}
		},

		async createContact(data: ContactCreate): Promise<Contact | null> {
			update((state) => ({ ...state, isLoading: true, error: null }));

			try {
				const response = await api.post<{ data: Contact }>('/contacts', data);
				update((state) => ({
					...state,
					contacts: [response.data, ...state.contacts],
					total: state.total + 1,
					isLoading: false
				}));
				return response.data;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to create contact';
				update((state) => ({ ...state, isLoading: false, error: message }));
				return null;
			}
		},

		async updateContact(id: number, data: ContactUpdate): Promise<Contact | null> {
			update((state) => ({ ...state, isLoading: true, error: null }));

			try {
				const response = await api.patch<{ data: Contact }>(`/contacts/${id}`, data);
				update((state) => ({
					...state,
					contacts: state.contacts.map((c) => (c.id === id ? response.data : c)),
					selectedContact:
						state.selectedContact?.id === id ? response.data : state.selectedContact,
					isLoading: false
				}));
				return response.data;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to update contact';
				update((state) => ({ ...state, isLoading: false, error: message }));
				return null;
			}
		},

		async deleteContact(id: number): Promise<boolean> {
			update((state) => ({ ...state, isLoading: true, error: null }));

			try {
				await api.delete(`/contacts/${id}`);
				update((state) => ({
					...state,
					contacts: state.contacts.filter((c) => c.id !== id),
					selectedContact: state.selectedContact?.id === id ? null : state.selectedContact,
					total: state.total - 1,
					isLoading: false
				}));
				return true;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to delete contact';
				update((state) => ({ ...state, isLoading: false, error: message }));
				return false;
			}
		},

		setSelectedContact(contact: Contact | null): void {
			update((state) => ({ ...state, selectedContact: contact }));
		},

		clearError(): void {
			update((state) => ({ ...state, error: null }));
		},

		reset(): void {
			set({
				contacts: [],
				selectedContact: null,
				isLoading: false,
				error: null,
				searchQuery: '',
				total: 0
			});
		}
	};
}

export const contactsStore = createContactsStore();

// Derived stores for convenience
export const contacts = derived(contactsStore, ($store) => $store.contacts);
export const selectedContact = derived(contactsStore, ($store) => $store.selectedContact);
export const contactsLoading = derived(contactsStore, ($store) => $store.isLoading);
export const contactsError = derived(contactsStore, ($store) => $store.error);
