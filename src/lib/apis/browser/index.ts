import { BROWSER_API_BASE_URL } from '$lib/constants';

export interface BrowserOption {
	id: string;
	name: string;
	image: string;
	description?: string;
	default?: boolean;
}

export interface BrowserSessionResponse {
	status: boolean;
	live_url?: string;
	kasm_id?: string;
	cdp_url?: string;
	provider?: string;
	browser_id?: string;
}

export const getAvailableBrowsers = async (token: string = ''): Promise<BrowserOption[]> => {
	let error = null;

	const res = await fetch(`${BROWSER_API_BASE_URL}/browsers`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('Error fetching available browsers:', err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Failed to fetch browsers';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const startBrowserSession = async (
	token: string = '',
	chatId: string,
	browserId: string = 'chrome'
): Promise<BrowserSessionResponse> => {
	let error = null;

	const res = await fetch(`${BROWSER_API_BASE_URL}/session/start`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			chat_id: chatId,
			browser_id: browserId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('Error starting browser session:', err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Failed to start browser session';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const stopBrowserSession = async (token: string = '', chatId: string): Promise<any> => {
	let error = null;

	const res = await fetch(`${BROWSER_API_BASE_URL}/session/stop`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			chat_id: chatId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('Error stopping browser session:', err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Failed to stop browser session';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
