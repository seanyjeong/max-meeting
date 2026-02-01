/**
 * Meeting Store - Meeting state management
 */
import { writable } from 'svelte/store';

export interface MeetingType {
	id: number;
	name: string;
	description?: string | null;
	question_perspective?: string | null;
}

export interface Meeting {
	id: number;
	type_id: number | null;
	meeting_type?: MeetingType | null;
	title: string;
	scheduled_at: string | null;
	location: string | null;
	status: 'draft' | 'in_progress' | 'completed';
	created_at: string;
	updated_at: string;
}

export interface MeetingDetail extends Meeting {
	agendas: Agenda[];
	attendees: Attendee[];
}

export interface TimeSegment {
	start: number;
	end: number | null;
}

export interface Agenda {
	id: number;
	meeting_id: number;
	parent_id: number | null;
	level: number;
	order_num: number;
	title: string;
	description: string | null;
	status: 'pending' | 'in_progress' | 'completed';
	started_at_seconds: number | null;
	time_segments: TimeSegment[] | null;
	questions: AgendaQuestion[];
	children: Agenda[];
}

export interface AgendaQuestion {
	id: number;
	agenda_id: number;
	question: string;
	order_num: number;
	is_generated: boolean;
	answered: boolean;
}

export interface ContactBrief {
	id: number;
	name: string;
	organization: string | null;
	role: string | null;
}

export interface Attendee {
	id: number;
	meeting_id: number;
	contact_id: number | null;
	name: string | null;  // For ad-hoc attendees without contact
	attended: boolean | null;
	speaker_label: string | null;
	contact: ContactBrief | null;
}

export const meetings = writable<Meeting[]>([]);
export const currentMeeting = writable<MeetingDetail | null>(null);
export const isLoading = writable<boolean>(false);

export function resetMeetingStore(): void {
	meetings.set([]);
	currentMeeting.set(null);
	isLoading.set(false);
}
