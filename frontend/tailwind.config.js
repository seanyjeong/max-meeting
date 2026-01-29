/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
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
				}
			},
			// Tablet-friendly touch targets
			minHeight: {
				touch: '44px'
			},
			minWidth: {
				touch: '44px'
			},
			// Recording button size
			width: {
				recording: '80px',
				'recording-btn': '48px'
			},
			height: {
				recording: '80px',
				'recording-bar': '56px'
			},
			// Animation for recording indicator
			animation: {
				pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
				'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite'
			}
		},
		// Responsive breakpoints for tablet
		screens: {
			sm: '640px',
			md: '768px',
			lg: '1024px',
			xl: '1280px',
			'2xl': '1536px'
		}
	},
	plugins: []
};
