/**
 * Logger utility for environment-aware logging.
 *
 * In development: All logs are output to console.
 * In production: Only warnings and errors are output.
 */

const isDev = import.meta.env.DEV;

export const logger = {
	/**
	 * Debug level - only in development
	 */
	debug: (...args: unknown[]): void => {
		if (isDev) {
			console.log('[DEBUG]', ...args);
		}
	},

	/**
	 * Info level - only in development
	 */
	info: (...args: unknown[]): void => {
		if (isDev) {
			console.info('[INFO]', ...args);
		}
	},

	/**
	 * Warning level - always output
	 */
	warn: (...args: unknown[]): void => {
		console.warn('[WARN]', ...args);
	},

	/**
	 * Error level - always output
	 */
	error: (...args: unknown[]): void => {
		console.error('[ERROR]', ...args);
	},

	/**
	 * API level - only in development, for API request/response logging
	 */
	api: (...args: unknown[]): void => {
		if (isDev) {
			console.log('[API]', ...args);
		}
	}
};
