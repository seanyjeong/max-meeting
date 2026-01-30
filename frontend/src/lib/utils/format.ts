/**
 * Date/Time formatting utilities
 *
 * Centralized formatting functions to avoid duplication across components.
 */

/**
 * Format a date string to Korean locale date format.
 * @param dateString - ISO date string or Date object
 * @returns Formatted date string (e.g., "2026. 01. 30.")
 */
export function formatDate(dateString: string | Date | null | undefined): string {
	if (!dateString) return '-';
	const date = new Date(dateString);
	if (isNaN(date.getTime())) return '-';
	return date.toLocaleDateString('ko-KR', {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit'
	});
}

/**
 * Format a date string to Korean locale datetime format.
 * @param dateString - ISO date string or Date object
 * @returns Formatted datetime string (e.g., "2026. 01. 30. 14:30")
 */
export function formatDateTime(dateString: string | Date | null | undefined): string {
	if (!dateString) return '-';
	const date = new Date(dateString);
	if (isNaN(date.getTime())) return '-';
	return date.toLocaleString('ko-KR', {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit'
	});
}

/**
 * Format seconds to time string (MM:SS or HH:MM:SS).
 * @param seconds - Number of seconds
 * @returns Formatted time string
 */
export function formatTime(seconds: number): string {
	if (!seconds || seconds < 0) return '0:00';

	const hours = Math.floor(seconds / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	const secs = Math.floor(seconds % 60);

	if (hours > 0) {
		return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}
	return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format milliseconds to time string.
 * @param ms - Number of milliseconds
 * @returns Formatted time string
 */
export function formatDuration(ms: number): string {
	const seconds = Math.floor(ms / 1000);
	return formatTime(seconds);
}

/**
 * Truncate a string to a maximum length with ellipsis.
 * @param str - String to truncate
 * @param maxLength - Maximum length (default: 50)
 * @returns Truncated string
 */
export function truncate(str: string | null | undefined, maxLength: number = 50): string {
	if (!str) return '';
	if (str.length <= maxLength) return str;
	return str.slice(0, maxLength - 3) + '...';
}

/**
 * Format a relative time string (e.g., "3분 전", "1시간 전").
 * @param dateString - ISO date string or Date object
 * @returns Relative time string
 */
export function formatRelativeTime(dateString: string | Date): string {
	const date = new Date(dateString);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffSec = Math.floor(diffMs / 1000);
	const diffMin = Math.floor(diffSec / 60);
	const diffHour = Math.floor(diffMin / 60);
	const diffDay = Math.floor(diffHour / 24);

	if (diffSec < 60) return '방금 전';
	if (diffMin < 60) return `${diffMin}분 전`;
	if (diffHour < 24) return `${diffHour}시간 전`;
	if (diffDay < 7) return `${diffDay}일 전`;

	return formatDate(date);
}
