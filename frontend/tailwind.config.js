/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				// Primary colors (Blue)
				primary: {
					50: '#eff6ff',
					100: '#dbeafe',
					200: '#bfdbfe',
					300: '#93c5fd',
					400: '#60a5fa',
					500: '#3b82f6',
					600: '#2563eb',
					700: '#1d4ed8',
					800: '#1e40af',
					900: '#1e3a8a',
					950: '#172554'
				},
				// Catppuccin Mocha inspired dark theme
				base: {
					DEFAULT: '#1e1e2e',
					light: '#313244',
					dark: '#181825'
				},
				surface: {
					DEFAULT: '#313244',
					light: '#45475a',
					dark: '#1e1e2e'
				},
				text: {
					DEFAULT: '#cdd6f4',
					muted: '#a6adc8',
					subtle: '#6c7086'
				},
				accent: {
					mauve: '#cba6f7',
					blue: '#89b4fa',
					red: '#f38ba8',
					green: '#a6e3a1',
					yellow: '#f9e2af',
					peach: '#fab387'
				}
			},
			// Tablet-friendly touch targets (48px minimum for fingers)
			minHeight: {
				touch: '44px',
				'touch-lg': '48px',
				'touch-xl': '56px'
			},
			minWidth: {
				touch: '44px',
				'touch-lg': '48px',
				'touch-xl': '56px'
			},
			// Layout dimensions
			width: {
				sidebar: '280px',
				'detail-panel': '400px',
				recording: '80px',
				'recording-btn': '48px'
			},
			height: {
				recording: '80px',
				'recording-bar': '56px',
				header: '64px'
			},
			// Spacing for touch-friendly interfaces
			spacing: {
				'touch': '12px',
				'touch-lg': '16px',
				'touch-xl': '24px'
			},
			// Animation for recording indicator and micro-interactions
			animation: {
				pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
				'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
				'fade-in': 'fadeIn 0.15s ease-out',
				'slide-up': 'slideUp 0.2s ease-out',
				'slide-right': 'slideRight 0.2s ease-out'
			},
			keyframes: {
				fadeIn: {
					'0%': { opacity: '0' },
					'100%': { opacity: '1' }
				},
				slideUp: {
					'0%': { opacity: '0', transform: 'translateY(10px)' },
					'100%': { opacity: '1', transform: 'translateY(0)' }
				},
				slideRight: {
					'0%': { opacity: '0', transform: 'translateX(-10px)' },
					'100%': { opacity: '1', transform: 'translateX(0)' }
				}
			},
			// Typography
			fontFamily: {
				sans: ['Pretendard', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Noto Sans KR', 'sans-serif'],
				mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace']
			},
			// Border radius for modern look
			borderRadius: {
				'2xl': '1rem',
				'3xl': '1.5rem'
			},
			// Box shadow for depth
			boxShadow: {
				'soft': '0 2px 8px rgba(0, 0, 0, 0.08)',
				'medium': '0 4px 16px rgba(0, 0, 0, 0.12)',
				'strong': '0 8px 32px rgba(0, 0, 0, 0.16)'
			},
			// Transition for smooth interactions
			transitionDuration: {
				'fast': '100ms',
				'normal': '200ms',
				'slow': '300ms'
			}
		},
		// Responsive breakpoints for tablet
		screens: {
			sm: '640px',
			md: '768px',      // Tablet portrait
			lg: '1024px',     // Tablet landscape
			xl: '1280px',     // Desktop
			'2xl': '1536px'
		}
	},
	plugins: []
};
