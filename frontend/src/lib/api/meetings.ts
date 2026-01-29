/**
 * Meetings API - Functions for interacting with meeting endpoints
 */

import { api } from '../api';
import type { Meeting } from '../stores/meeting';

export interface PaginationParams {
	limit?: number;
	offset?: number;
	status?: string;
	type_id?: number;
	from?: string;
	to?: string;
	deleted_only?: boolean;
}

export interface PaginatedResponse<T> {
	data: T[];
	meta: {
		total: number;
		limit: number;
		offset: number;
	};
}

export interface MeetingResponse {
	data: Meeting;
}

/**
 * Get list of meetings
 */
export async function getMeetings(params?: PaginationParams): Promise<PaginatedResponse<Meeting>> {
	const queryParams: Record<string, string | number | undefined> = {};

	if (params) {
		if (params.limit !== undefined) queryParams.limit = params.limit;
		if (params.offset !== undefined) queryParams.offset = params.offset;
		if (params.status) queryParams.status = params.status;
		if (params.type_id) queryParams.type_id = params.type_id;
		if (params.from) queryParams.from = params.from;
		if (params.to) queryParams.to = params.to;
		if (params.deleted_only !== undefined) queryParams.deleted_only = params.deleted_only ? 'true' : 'false';
	}

	return api.get<PaginatedResponse<Meeting>>('/meetings', queryParams);
}

/**
 * Get deleted meetings only
 */
export async function getDeletedMeetings(params?: PaginationParams): Promise<PaginatedResponse<Meeting>> {
	return getMeetings({ ...params, deleted_only: true });
}

/**
 * Restore a deleted meeting
 */
export async function restoreMeeting(meetingId: number): Promise<Meeting> {
	const response = await api.post<MeetingResponse>(`/meetings/${meetingId}/restore`);
	return response.data;
}

/**
 * Delete a meeting (soft delete)
 */
export async function deleteMeeting(meetingId: number): Promise<void> {
	await api.delete(`/meetings/${meetingId}`);
}
