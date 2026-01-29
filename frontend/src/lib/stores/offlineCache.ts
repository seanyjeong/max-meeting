/**
 * Offline Cache - IndexedDB 기반 오프라인 캐싱
 * 회의 전에 안건/질문지를 사전 다운로드하여 오프라인에서도 사용 가능하도록 함
 */
import { browser } from '$app/environment';
import type { MeetingDetail, Agenda } from './meeting';
import type { Contact } from './contacts';
import { get } from 'svelte/store';
import { auth } from './auth';

const DB_NAME = 'max-meeting-cache';
const DB_VERSION = 1;
const STORES = {
	meetings: 'meetings',
	agendas: 'agendas',
	contacts: 'contacts',
};

let db: IDBDatabase | null = null;

// DB 초기화
export async function initDB(): Promise<IDBDatabase> {
	if (db) return db;
	if (!browser) throw new Error('IndexedDB는 브라우저에서만 사용할 수 있습니다');

	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			db = request.result;
			if (import.meta.env.DEV) console.log('IndexedDB 연결 완료');
			resolve(db);
		};

		request.onupgradeneeded = (event) => {
			const database = (event.target as IDBOpenDBRequest).result;

			// 회의 저장소
			if (!database.objectStoreNames.contains(STORES.meetings)) {
				database.createObjectStore(STORES.meetings, { keyPath: 'id' });
				if (import.meta.env.DEV) console.log('회의 저장소 생성');
			}

			// 안건 저장소 (meeting_id로 인덱싱)
			if (!database.objectStoreNames.contains(STORES.agendas)) {
				const agendaStore = database.createObjectStore(STORES.agendas, { keyPath: 'id' });
				agendaStore.createIndex('meeting_id', 'meeting_id', { unique: false });
				if (import.meta.env.DEV) console.log('안건 저장소 생성');
			}

			// 연락처 저장소
			if (!database.objectStoreNames.contains(STORES.contacts)) {
				database.createObjectStore(STORES.contacts, { keyPath: 'id' });
				if (import.meta.env.DEV) console.log('연락처 저장소 생성');
			}
		};
	});
}

// 데이터 저장
export async function cacheData<T extends { id: number }>(storeName: string, data: T[]): Promise<void> {
	const database = await initDB();
	const tx = database.transaction(storeName, 'readwrite');
	const store = tx.objectStore(storeName);

	for (const item of data) {
		store.put(item);
	}

	return new Promise((resolve, reject) => {
		tx.oncomplete = () => {
			if (import.meta.env.DEV) console.log(`${data.length}개 항목을 ${storeName}에 캐싱 완료`);
			resolve();
		};
		tx.onerror = () => reject(tx.error);
	});
}

// 데이터 조회
export async function getCachedData<T>(storeName: string): Promise<T[]> {
	const database = await initDB();
	const tx = database.transaction(storeName, 'readonly');
	const store = tx.objectStore(storeName);

	return new Promise((resolve, reject) => {
		const request = store.getAll();
		request.onsuccess = () => {
			if (import.meta.env.DEV) console.log(`${storeName}에서 ${request.result.length}개 항목 조회`);
			resolve(request.result);
		};
		request.onerror = () => reject(request.error);
	});
}

// 특정 회의의 안건 조회
export async function getCachedAgendas(meetingId: number): Promise<Agenda[]> {
	const database = await initDB();
	const tx = database.transaction(STORES.agendas, 'readonly');
	const store = tx.objectStore(STORES.agendas);
	const index = store.index('meeting_id');

	return new Promise((resolve, reject) => {
		const request = index.getAll(meetingId);
		request.onsuccess = () => {
			if (import.meta.env.DEV) console.log(`회의 ${meetingId}의 안건 ${request.result.length}개 조회`);
			resolve(request.result);
		};
		request.onerror = () => reject(request.error);
	});
}

// 특정 회의 데이터 조회
export async function getCachedMeeting(meetingId: number): Promise<MeetingDetail | null> {
	const database = await initDB();
	const tx = database.transaction(STORES.meetings, 'readonly');
	const store = tx.objectStore(STORES.meetings);

	return new Promise((resolve, reject) => {
		const request = store.get(meetingId);
		request.onsuccess = () => {
			if (request.result) {
				if (import.meta.env.DEV) console.log(`캐시에서 회의 ${meetingId} 조회 성공`);
			} else {
				if (import.meta.env.DEV) console.log(`캐시에 회의 ${meetingId} 없음`);
			}
			resolve(request.result || null);
		};
		request.onerror = () => reject(request.error);
	});
}

// 회의 데이터 사전 다운로드
export async function prefetchMeetingData(meetingId: number): Promise<void> {
	try {
		if (import.meta.env.DEV) console.log(`회의 ${meetingId} 데이터 사전 다운로드 시작`);

		// 토큰 가져오기
		const authState = get(auth);
		const headers: Record<string, string> = { 'Content-Type': 'application/json' };
		if (authState.accessToken) {
			headers['Authorization'] = `Bearer ${authState.accessToken}`;
		}

		// 회의 상세 조회
		const meetingRes = await fetch(`/api/v1/meetings/${meetingId}`, { headers });

		if (meetingRes.ok) {
			const meeting = await meetingRes.json();

			// 회의 전체 데이터 캐싱 (안건 포함)
			await cacheData(STORES.meetings, [meeting]);

			// 안건을 별도로도 캐싱 (인덱싱된 조회를 위해)
			if (meeting.agendas && meeting.agendas.length > 0) {
				await cacheData(STORES.agendas, meeting.agendas);
			}

			if (import.meta.env.DEV) console.log(`회의 ${meetingId} 캐싱 완료 (안건 ${meeting.agendas?.length || 0}개)`);
		} else {
			if (import.meta.env.DEV) console.error(`회의 ${meetingId} 조회 실패: ${meetingRes.status}`);
		}
	} catch (error) {
		if (import.meta.env.DEV) console.error('회의 데이터 사전 다운로드 실패:', error);
	}
}

// 연락처 캐싱
export async function cacheContacts(): Promise<void> {
	try {
		if (import.meta.env.DEV) console.log('연락처 데이터 캐싱 시작');

		// 토큰 가져오기
		const authState = get(auth);
		const headers: Record<string, string> = { 'Content-Type': 'application/json' };
		if (authState.accessToken) {
			headers['Authorization'] = `Bearer ${authState.accessToken}`;
		}

		const res = await fetch('/api/v1/contacts?limit=100', { headers });

		if (res.ok) {
			const contactsData = await res.json();
			const contacts = contactsData.data || [];
			await cacheData(STORES.contacts, contacts);
			if (import.meta.env.DEV) console.log(`연락처 ${contacts.length}개 캐싱 완료`);
		} else {
			if (import.meta.env.DEV) console.error(`연락처 조회 실패: ${res.status}`);
		}
	} catch (error) {
		if (import.meta.env.DEV) console.error('연락처 캐싱 실패:', error);
	}
}

// 오프라인 여부 확인
export function isOffline(): boolean {
	return browser && !navigator.onLine;
}

// 캐시 클리어
export async function clearCache(): Promise<void> {
	if (!browser) return;

	return new Promise((resolve, reject) => {
		const request = indexedDB.deleteDatabase(DB_NAME);
		request.onsuccess = () => {
			if (import.meta.env.DEV) console.log('캐시 삭제 완료');
			db = null;
			resolve();
		};
		request.onerror = () => reject(request.error);
	});
}
