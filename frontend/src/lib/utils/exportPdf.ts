/**
 * PDF Export Utility
 *
 * Generates PDF from meeting results using browser print functionality.
 * No external PDF library needed - uses CSS print styles.
 */

interface MeetingData {
	title: string;
	date?: string;
	location?: string;
	attendees?: { name: string; role?: string }[];
	summary?: string;
	actionItems?: {
		content: string;
		assignee?: string;
		dueDate?: string;
		priority?: string;
		status?: string;
	}[];
	transcriptSegments?: {
		speaker?: string;
		text: string;
		timestamp?: number;
	}[];
}

/**
 * Format timestamp to HH:MM:SS
 */
function formatTimestamp(seconds: number): string {
	const h = Math.floor(seconds / 3600);
	const m = Math.floor((seconds % 3600) / 60);
	const s = Math.floor(seconds % 60);
	return h > 0
		? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
		: `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Generate HTML content for PDF
 */
function generatePdfHtml(meeting: MeetingData): string {
	const priorityLabels: Record<string, string> = {
		high: '높음',
		medium: '보통',
		low: '낮음'
	};

	const statusLabels: Record<string, string> = {
		pending: '대기',
		in_progress: '진행 중',
		completed: '완료'
	};

	return `
<!DOCTYPE html>
<html lang="ko">
<head>
	<meta charset="UTF-8">
	<title>${meeting.title} - 회의 결과</title>
	<style>
		* {
			margin: 0;
			padding: 0;
			box-sizing: border-box;
		}
		body {
			font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
			line-height: 1.6;
			color: #1f2937;
			padding: 40px;
			max-width: 800px;
			margin: 0 auto;
		}
		h1 {
			font-size: 24px;
			margin-bottom: 8px;
			color: #111827;
		}
		h2 {
			font-size: 18px;
			margin: 24px 0 12px;
			color: #374151;
			border-bottom: 2px solid #e5e7eb;
			padding-bottom: 8px;
		}
		.meta {
			color: #6b7280;
			font-size: 14px;
			margin-bottom: 24px;
		}
		.meta span {
			margin-right: 16px;
		}
		.attendees {
			display: flex;
			flex-wrap: wrap;
			gap: 8px;
			margin-bottom: 16px;
		}
		.attendee {
			background: #f3f4f6;
			padding: 4px 12px;
			border-radius: 16px;
			font-size: 14px;
		}
		.summary {
			background: #f9fafb;
			padding: 16px;
			border-radius: 8px;
			border-left: 4px solid #3b82f6;
		}
		.summary p {
			margin-bottom: 8px;
		}
		.action-items {
			list-style: none;
		}
		.action-item {
			padding: 12px;
			border: 1px solid #e5e7eb;
			border-radius: 8px;
			margin-bottom: 8px;
		}
		.action-item-content {
			font-weight: 500;
			margin-bottom: 4px;
		}
		.action-item-meta {
			display: flex;
			gap: 12px;
			font-size: 12px;
			color: #6b7280;
		}
		.priority-high { color: #dc2626; }
		.priority-medium { color: #d97706; }
		.priority-low { color: #059669; }
		.transcript {
			font-size: 14px;
		}
		.transcript-segment {
			margin-bottom: 12px;
			padding-bottom: 12px;
			border-bottom: 1px solid #f3f4f6;
		}
		.transcript-segment:last-child {
			border-bottom: none;
		}
		.speaker {
			font-weight: 600;
			color: #3b82f6;
		}
		.timestamp {
			color: #9ca3af;
			font-size: 12px;
			margin-left: 8px;
		}
		@media print {
			body {
				padding: 20px;
			}
			.page-break {
				page-break-before: always;
			}
		}
	</style>
</head>
<body>
	<h1>${meeting.title}</h1>
	<div class="meta">
		${meeting.date ? `<span>일시: ${meeting.date}</span>` : ''}
		${meeting.location ? `<span>장소: ${meeting.location}</span>` : ''}
	</div>

	${meeting.attendees && meeting.attendees.length > 0 ? `
	<h2>참석자</h2>
	<div class="attendees">
		${meeting.attendees.map(a => `
			<span class="attendee">${a.name}${a.role ? ` (${a.role})` : ''}</span>
		`).join('')}
	</div>
	` : ''}

	${meeting.summary ? `
	<h2>회의 요약</h2>
	<div class="summary">
		${meeting.summary.split('\n').map(p => `<p>${p}</p>`).join('')}
	</div>
	` : ''}

	${meeting.actionItems && meeting.actionItems.length > 0 ? `
	<h2>실행 항목 (${meeting.actionItems.length})</h2>
	<ul class="action-items">
		${meeting.actionItems.map(item => `
			<li class="action-item">
				<div class="action-item-content">${item.content}</div>
				<div class="action-item-meta">
					${item.assignee ? `<span>담당: ${item.assignee}</span>` : ''}
					${item.dueDate ? `<span>기한: ${item.dueDate}</span>` : ''}
					${item.priority ? `<span class="priority-${item.priority}">우선순위: ${priorityLabels[item.priority] || item.priority}</span>` : ''}
					${item.status ? `<span>상태: ${statusLabels[item.status] || item.status}</span>` : ''}
				</div>
			</li>
		`).join('')}
	</ul>
	` : ''}

	${meeting.transcriptSegments && meeting.transcriptSegments.length > 0 ? `
	<div class="page-break"></div>
	<h2>전사록</h2>
	<div class="transcript">
		${meeting.transcriptSegments.map(seg => `
			<div class="transcript-segment">
				${seg.speaker ? `<span class="speaker">${seg.speaker}</span>` : ''}
				${seg.timestamp !== undefined ? `<span class="timestamp">${formatTimestamp(seg.timestamp)}</span>` : ''}
				<p>${seg.text}</p>
			</div>
		`).join('')}
	</div>
	` : ''}

	<div style="margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #9ca3af; text-align: center;">
		MAX Meeting에서 생성됨 - ${new Date().toLocaleDateString('ko-KR')}
	</div>
</body>
</html>
	`;
}

/**
 * Export meeting results to PDF using print dialog
 */
export function exportToPdf(meeting: MeetingData): void {
	const html = generatePdfHtml(meeting);

	// Open new window with PDF content
	const printWindow = window.open('', '_blank');
	if (!printWindow) {
		alert('팝업이 차단되었습니다. 팝업을 허용해주세요.');
		return;
	}

	printWindow.document.write(html);
	printWindow.document.close();

	// Wait for content to load, then print
	printWindow.onload = () => {
		printWindow.focus();
		printWindow.print();
	};
}

/**
 * Download meeting results as HTML file (alternative to PDF)
 */
export function exportToHtml(meeting: MeetingData): void {
	const html = generatePdfHtml(meeting);
	const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
	const url = URL.createObjectURL(blob);

	const a = document.createElement('a');
	a.href = url;
	a.download = `${meeting.title.replace(/[^a-zA-Z0-9가-힣]/g, '_')}_회의결과.html`;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}

/**
 * Copy meeting summary to clipboard as plain text
 */
export async function copyToClipboard(meeting: MeetingData): Promise<boolean> {
	const text = `
${meeting.title}
${'='.repeat(meeting.title.length)}

${meeting.date ? `일시: ${meeting.date}` : ''}
${meeting.location ? `장소: ${meeting.location}` : ''}

${meeting.attendees && meeting.attendees.length > 0 ? `
참석자: ${meeting.attendees.map(a => a.name).join(', ')}
` : ''}

${meeting.summary ? `
요약
----
${meeting.summary}
` : ''}

${meeting.actionItems && meeting.actionItems.length > 0 ? `
실행 항목
--------
${meeting.actionItems.map((item, i) => `${i + 1}. ${item.content}${item.assignee ? ` (담당: ${item.assignee})` : ''}`).join('\n')}
` : ''}

---
MAX Meeting에서 생성
	`.trim();

	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch {
		return false;
	}
}
