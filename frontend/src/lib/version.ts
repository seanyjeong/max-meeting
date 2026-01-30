/**
 * App version configuration
 * Update this when deploying new versions
 */
export const APP_VERSION = '1.1.0';
export const BUILD_DATE = '2026-01-30';

// Version history (for reference)
// 1.0.0 - Initial release
// 1.1.0 - SQLAlchemy 성능 개선, 결과 페이지 UX 개선, PWA 지원

export function getVersionInfo() {
	return {
		version: APP_VERSION,
		buildDate: BUILD_DATE,
		fullVersion: `v${APP_VERSION} (${BUILD_DATE})`
	};
}
