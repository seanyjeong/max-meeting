/**
 * tldraw 캔버스를 이미지로 내보내기
 */

export async function exportToPng(
	svgElement: SVGElement,
	width: number = 1920,
	height: number = 1080
): Promise<Blob> {
	// SVG를 문자열로 변환
	const serializer = new XMLSerializer();
	const svgString = serializer.serializeToString(svgElement);
	const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
	const url = URL.createObjectURL(svgBlob);

	// 캔버스에 그리기
	const canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;
	const ctx = canvas.getContext('2d')!;

	// 배경 흰색
	ctx.fillStyle = 'white';
	ctx.fillRect(0, 0, width, height);

	// 이미지 로드 및 그리기
	return new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => {
			ctx.drawImage(img, 0, 0, width, height);
			URL.revokeObjectURL(url);

			canvas.toBlob((blob) => {
				if (blob) resolve(blob);
				else reject(new Error('Failed to create PNG blob'));
			}, 'image/png');
		};
		img.onerror = reject;
		img.src = url;
	});
}

export async function exportToPdf(
	svgElement: SVGElement,
	filename: string = 'sketch.pdf'
): Promise<void> {
	// 브라우저 환경에서만 동작
	if (typeof window === 'undefined') {
		throw new Error('PDF export is only available in browser environment');
	}

	// jsPDF 동적 import (번들 크기 최적화)
	const jsPDFModule = await import('jspdf');
	const jsPDF = jsPDFModule.default;

	const png = await exportToPng(svgElement);
	const imgData = await blobToBase64(png);

	const pdf = new jsPDF({
		orientation: 'landscape',
		unit: 'px',
		format: [1920, 1080]
	});

	pdf.addImage(imgData, 'PNG', 0, 0, 1920, 1080);
	pdf.save(filename);
}

function blobToBase64(blob: Blob): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onloadend = () => resolve(reader.result as string);
		reader.onerror = reject;
		reader.readAsDataURL(blob);
	});
}

export function downloadBlob(blob: Blob, filename: string) {
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	a.click();
	URL.revokeObjectURL(url);
}
