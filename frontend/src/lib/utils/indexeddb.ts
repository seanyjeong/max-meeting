/**
 * IndexedDB utilities for recording crash recovery
 *
 * Stores recording chunks locally to recover from browser crashes.
 */

const DB_NAME = 'max-meeting-recordings';
const DB_VERSION = 1;
const STORE_NAME = 'recording-chunks';

interface RecordingChunk {
	id?: number;
	meetingId: number;
	blob: Blob;
	timestamp: Date;
}

let dbInstance: IDBDatabase | null = null;

async function openDB(): Promise<IDBDatabase> {
	if (dbInstance) return dbInstance;

	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);

		request.onerror = () => {
			reject(new Error('Failed to open IndexedDB'));
		};

		request.onsuccess = () => {
			dbInstance = request.result;
			resolve(dbInstance);
		};

		request.onupgradeneeded = (event) => {
			const db = (event.target as IDBOpenDBRequest).result;

			if (!db.objectStoreNames.contains(STORE_NAME)) {
				const store = db.createObjectStore(STORE_NAME, {
					keyPath: 'id',
					autoIncrement: true
				});
				store.createIndex('meetingId', 'meetingId', { unique: false });
				store.createIndex('timestamp', 'timestamp', { unique: false });
			}
		};
	});
}

/**
 * Save a recording chunk to IndexedDB
 */
export async function saveRecordingChunk(meetingId: number, blob: Blob): Promise<void> {
	const db = await openDB();

	return new Promise((resolve, reject) => {
		const transaction = db.transaction(STORE_NAME, 'readwrite');
		const store = transaction.objectStore(STORE_NAME);

		const chunk: RecordingChunk = {
			meetingId,
			blob,
			timestamp: new Date()
		};

		const request = store.add(chunk);

		request.onerror = () => {
			reject(new Error('Failed to save recording chunk'));
		};

		request.onsuccess = () => {
			resolve();
		};
	});
}

/**
 * Get all recording chunks for a meeting
 */
export async function getRecordingChunks(meetingId: number): Promise<Blob[]> {
	const db = await openDB();

	return new Promise((resolve, reject) => {
		const transaction = db.transaction(STORE_NAME, 'readonly');
		const store = transaction.objectStore(STORE_NAME);
		const index = store.index('meetingId');

		const request = index.getAll(meetingId);

		request.onerror = () => {
			reject(new Error('Failed to get recording chunks'));
		};

		request.onsuccess = () => {
			const chunks = request.result as RecordingChunk[];
			// Sort by timestamp and return blobs
			chunks.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
			resolve(chunks.map((chunk) => chunk.blob));
		};
	});
}

/**
 * Clear all recording chunks for a meeting
 */
export async function clearRecordingChunks(meetingId: number): Promise<void> {
	const db = await openDB();

	return new Promise((resolve, reject) => {
		const transaction = db.transaction(STORE_NAME, 'readwrite');
		const store = transaction.objectStore(STORE_NAME);
		const index = store.index('meetingId');

		const request = index.getAllKeys(meetingId);

		request.onerror = () => {
			reject(new Error('Failed to clear recording chunks'));
		};

		request.onsuccess = () => {
			const keys = request.result;
			let remaining = keys.length;

			if (remaining === 0) {
				resolve();
				return;
			}

			keys.forEach((key) => {
				const deleteRequest = store.delete(key);
				deleteRequest.onsuccess = () => {
					remaining--;
					if (remaining === 0) resolve();
				};
				deleteRequest.onerror = () => {
					reject(new Error('Failed to delete recording chunk'));
				};
			});
		};
	});
}

/**
 * Check if there are unsaved recordings for a meeting
 */
export async function hasUnsavedRecordings(meetingId: number): Promise<boolean> {
	const chunks = await getRecordingChunks(meetingId);
	return chunks.length > 0;
}

/**
 * Get all meetings with unsaved recordings
 */
export async function getMeetingsWithUnsavedRecordings(): Promise<number[]> {
	const db = await openDB();

	return new Promise((resolve, reject) => {
		const transaction = db.transaction(STORE_NAME, 'readonly');
		const store = transaction.objectStore(STORE_NAME);
		const index = store.index('meetingId');

		const request = index.openCursor(null, 'nextunique');
		const meetingIds: number[] = [];

		request.onerror = () => {
			reject(new Error('Failed to get meetings with unsaved recordings'));
		};

		request.onsuccess = (event) => {
			const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result;
			if (cursor) {
				meetingIds.push(cursor.key as number);
				cursor.continue();
			} else {
				resolve(meetingIds);
			}
		};
	});
}

/**
 * Combine all chunks into a single blob
 */
export async function combineRecordingChunks(meetingId: number): Promise<Blob | null> {
	const chunks = await getRecordingChunks(meetingId);
	if (chunks.length === 0) return null;
	return new Blob(chunks, { type: 'audio/webm' });
}

/**
 * Get storage estimate
 */
export async function getStorageEstimate(): Promise<{
	usage: number;
	quota: number;
	percentUsed: number;
} | null> {
	if (!navigator.storage || !navigator.storage.estimate) {
		return null;
	}

	try {
		const estimate = await navigator.storage.estimate();
		const usage = estimate.usage || 0;
		const quota = estimate.quota || 0;
		const percentUsed = quota > 0 ? (usage / quota) * 100 : 0;

		return { usage, quota, percentUsed };
	} catch {
		return null;
	}
}
