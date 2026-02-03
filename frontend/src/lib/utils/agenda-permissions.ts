/**
 * Agenda Permission Utilities
 *
 * 회의 중 아젠다 CRUD 권한을 관리합니다.
 * 녹음 상태와 time_segments를 기반으로 편집 가능 여부를 결정합니다.
 */

import type { Agenda } from '$lib/stores/meeting';

export interface AgendaPermissions {
	canEditTitle: boolean;
	canEditDescription: boolean;
	canDelete: boolean;
	canAddChild: boolean;
	reason?: string;
}

/**
 * 아젠다의 편집 권한을 계산합니다.
 *
 * 권한 규칙:
 * 1. activeAgendaId와 일치하거나 열린 segment가 있으면 → 모든 편집 금지
 * 2. 녹음 중이고 time_segments가 있으면 → 삭제만 금지
 * 3. 녹음 중이면 → 자식 추가 금지
 * 4. 녹음 중이 아니면 → time_segments 없는 경우만 삭제 허용
 *
 * @param agenda - 대상 아젠다
 * @param activeAgendaId - 현재 녹음 중인 아젠다 ID (null = 녹음 중 아님)
 * @param isRecording - 녹음 진행 중 여부
 * @returns 권한 객체
 */
export function getAgendaPermissions(
	agenda: Agenda,
	activeAgendaId: number | null,
	isRecording: boolean
): AgendaPermissions {
	// 열린 세그먼트 체크 (end: null = 현재 녹음 중)
	const hasOpenSegment = agenda.time_segments?.some((s) => s.end === null) ?? false;
	// 녹음된 구간 존재 여부
	const hasAnySegment = (agenda.time_segments?.length ?? 0) > 0;

	// Case 1: 현재 녹음 중인 아젠다 또는 열린 세그먼트 존재
	if (activeAgendaId === agenda.id || hasOpenSegment) {
		return {
			canEditTitle: false,
			canEditDescription: false,
			canDelete: false,
			canAddChild: false,
			reason: '현재 녹음 중인 안건입니다'
		};
	}

	// Case 2: 녹음 중이고, 이미 녹음된 구간이 있음
	if (isRecording && hasAnySegment) {
		return {
			canEditTitle: true,
			canEditDescription: true,
			canDelete: false,
			canAddChild: false,
			reason: '녹음된 구간이 있어 삭제할 수 없습니다'
		};
	}

	// Case 3: 녹음 중이지만 녹음된 구간 없음
	if (isRecording) {
		return {
			canEditTitle: true,
			canEditDescription: true,
			canDelete: true,
			canAddChild: false // 녹음 중에는 자식 추가 비허용
		};
	}

	// Case 4: 녹음 중 아님 - time_segments 유무에 따라
	return {
		canEditTitle: true,
		canEditDescription: true,
		canDelete: !hasAnySegment,
		canAddChild: true
	};
}

/**
 * 새 아젠다 추가 가능 여부를 반환합니다.
 *
 * @param isRecording - 녹음 진행 중 여부
 * @param isPaused - 일시정지 상태 여부
 * @returns 추가 가능 여부
 */
export function canAddAgenda(isRecording: boolean, isPaused: boolean): boolean {
	// 녹음 중이 아니거나, 일시정지 상태면 추가 가능
	return !isRecording || isPaused;
}

/**
 * 자식 아젠다를 포함하여 권한을 재귀적으로 체크합니다.
 *
 * @param agenda - 대상 아젠다 (children 포함)
 * @param activeAgendaId - 현재 녹음 중인 아젠다 ID
 * @param isRecording - 녹음 진행 중 여부
 * @returns 아젠다 ID를 키로 하는 권한 맵
 */
export function getAgendaPermissionsMap(
	agendas: Agenda[],
	activeAgendaId: number | null,
	isRecording: boolean
): Map<number, AgendaPermissions> {
	const permMap = new Map<number, AgendaPermissions>();

	function processAgenda(agenda: Agenda) {
		permMap.set(agenda.id, getAgendaPermissions(agenda, activeAgendaId, isRecording));

		// 자식 아젠다 처리
		if (agenda.children) {
			for (const child of agenda.children) {
				processAgenda(child);
			}
		}
	}

	for (const agenda of agendas) {
		processAgenda(agenda);
	}

	return permMap;
}
