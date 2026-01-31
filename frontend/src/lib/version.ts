/**
 * App version configuration
 * Update this when deploying new versions
 */
export const APP_VERSION = '1.16.5';
export const BUILD_DATE = '2026-01-31';

// Version history (for reference)
// 1.16.5 - 녹음 파일 자동 정리 (회의록 생성 3일 후 삭제)
// 1.16.4 - STT 타임스탬프 버그 수정 (LLM refine 비활성화로 정확도 보장)
// 1.16.3 - 녹음 페이지 리사이즈 패널, 회의록 메모 통합, UI 컴팩트화
// 1.16.0 - 헤더에 새 로고 적용 (Gemini 나노바나나)
// 1.15.0 - 인쇄용 회의록 개선: 2단 레이아웃, 포스트잇 메모 표시
// 1.14.0 - 새 로고 및 PWA 아이콘 업데이트 (Kimi AI 디자인)
// 1.0.0 - Initial release
// 1.1.0 - SQLAlchemy 성능 개선, 결과 페이지 UX 개선, PWA 지원
// 1.2.0 - STT 파이프라인 안정화, 녹음 없이 회의록 생성 지원, UI 용어 개선
// 1.3.0 - UX 대폭 개선: 회의 마무리 버튼, 녹음 파일 목록, 디버그 패널, 진행률 표시
// 1.4.0 - 계층형 안건 시스템, 3레벨 지원
// 1.5.0 - 세그먼트-안건 매핑 개선, QA 버그 수정
// 1.6.0 - 코드 품질 개선: 보안 수정, 유틸리티 통합, 로깅 개선
// 1.7.0 - STT 에러 처리 개선, 드롭다운 오버플로우 수정, 진행 모달 개선
// 1.8.0 - 질문 수정/삭제 버튼 태블릿 지원
// 1.9.0 - 안건 재매칭 분석 UI 추가
// 1.10.0 - 분석 완료 메시지 추가, 버전 표시 수정
// 1.11.0 - 업무배치 탭 추가, 탭 이름 변경 (메모/필기/업무배치)
// 1.12.0 - 메모 포스트잇 표시 추가
// 1.13.0 - 필기 갤러리 탭 추가, 스케치 백엔드 저장

export function getVersionInfo() {
	return {
		version: APP_VERSION,
		buildDate: BUILD_DATE,
		fullVersion: `v${APP_VERSION} (${BUILD_DATE})`
	};
}
