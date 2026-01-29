/**
 * Viewport Store - 태블릿 반응형 레이아웃을 위한 viewport 상태 관리
 */
import { readable, derived } from 'svelte/store';
import { browser } from '$app/environment';

export interface ViewportState {
	width: number;
	height: number;
	isLandscape: boolean;
	isPortrait: boolean;
	isTablet: boolean;
	isMobile: boolean;
	isDesktop: boolean;
	size: 'compact' | 'medium' | 'expanded';
}

function getViewportState(): ViewportState {
	if (!browser) {
		// SSR 기본값
		return {
			width: 1024,
			height: 768,
			isLandscape: true,
			isPortrait: false,
			isTablet: true,
			isMobile: false,
			isDesktop: false,
			size: 'expanded'
		};
	}

	const width = window.innerWidth;
	const height = window.innerHeight;
	const isLandscape = width > height;
	const isPortrait = !isLandscape;
	const isMobile = width < 768;
	const isTablet = width >= 768 && width < 1280;
	const isDesktop = width >= 1280;

	let size: 'compact' | 'medium' | 'expanded';
	if (width < 768) {
		size = 'compact';
	} else if (width < 1024) {
		size = 'medium';
	} else {
		size = 'expanded';
	}

	return {
		width,
		height,
		isLandscape,
		isPortrait,
		isTablet,
		isMobile,
		isDesktop,
		size
	};
}

export const viewport = readable<ViewportState>(getViewportState(), (set) => {
	if (!browser) return;

	const handleResize = () => {
		set(getViewportState());
	};

	window.addEventListener('resize', handleResize);
	window.addEventListener('orientationchange', handleResize);

	return () => {
		window.removeEventListener('resize', handleResize);
		window.removeEventListener('orientationchange', handleResize);
	};
});

// 사이드바 표시 여부 (태블릿 가로모드 또는 데스크톱에서만)
export const showSidebar = derived(viewport, ($viewport) => {
	return ($viewport.isTablet && $viewport.isLandscape) || $viewport.isDesktop;
});

// 3-Column 레이아웃 사용 여부
export const useThreeColumn = derived(viewport, ($viewport) => {
	return $viewport.size === 'expanded' && $viewport.isLandscape;
});
