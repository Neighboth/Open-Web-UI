<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import { getAvailableBrowsers, type BrowserOption } from '$lib/apis/browser';
	import { toast } from 'svelte-sonner';

	const i18n = getContext<any>('i18n');

	export let show = false;
	export let selectedBrowser = 'chrome';
	export let onSelect: (browserId: string) => void = () => {};

	let browsers: BrowserOption[] = [
		{
			id: 'chrome',
			name: 'Google Chrome',
			image: 'kasmweb/chrome:1.16.0',
			description: 'Google Chrome with isolated profile & DevTools CDP',
			default: true
		},
		{
			id: 'chromium',
			name: 'Chromium',
			image: 'kasmweb/chromium:1.16.0',
			description: 'Fast open-source Chromium Browser',
			default: false
		},
		{
			id: 'firefox',
			name: 'Mozilla Firefox',
			image: 'kasmweb/firefox:1.16.0',
			description: 'Mozilla Firefox with privacy protections',
			default: false
		},
		{
			id: 'brave',
			name: 'Brave',
			image: 'kasmweb/brave:1.16.0',
			description: 'Brave Privacy Browser with ad-blocking',
			default: false
		},
		{
			id: 'tor',
			name: 'Tor Browser',
			image: 'kasmweb/tor-browser:1.16.0',
			description: 'Tor Anonymous & Onion Routing Browser',
			default: false
		},
		{
			id: 'edge',
			name: 'Microsoft Edge',
			image: 'kasmweb/edge:1.16.0',
			description: 'Microsoft Edge Browser',
			default: false
		}
	];

	let loading = false;

	const loadBrowsers = async () => {
		loading = true;
		try {
			const res = await getAvailableBrowsers(localStorage.token);
			if (res && res.length > 0) {
				browsers = res;
			}
		} catch (e) {
			console.debug('Using default browser list:', e);
		} finally {
			loading = false;
		}
	};

	$: if (show) {
		selectedBrowser = localStorage.getItem('selected_browser') || 'chrome';
		loadBrowsers();
	}

	const selectBrowser = (id: string) => {
		selectedBrowser = id;
		localStorage.setItem('selected_browser', id);
		onSelect(id);
		toast.success($i18n.t(`Browser selected: ${browsers.find((b) => b.id === id)?.name || id}`));
		show = false;
	};
</script>

<Modal bind:show size="sm">
	<div>
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<div class="flex items-center gap-2 text-base font-medium">
				<GlobeAlt className="size-5 text-blue-500" />
				<span>{$i18n.t('Select Sandbox Browser')}</span>
			</div>
			<button
				class="self-center p-1 rounded-lg text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={() => {
					show = false;
				}}
				type="button"
			>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="px-5 pb-5">
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				{$i18n.t(
					'Choose the isolated browser container for live previews, web automation, and agent tasks. Profiles and cookies are saved automatically.'
				)}
			</div>

			<div class="space-y-2 max-h-72 overflow-y-auto pr-1">
				{#each browsers as browser (browser.id)}
					<button
						type="button"
						class="w-full flex items-center justify-between p-2.5 rounded-xl border transition text-left {selectedBrowser ===
						browser.id
							? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/30 dark:border-blue-500'
							: 'border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
						on:click={() => selectBrowser(browser.id)}
					>
						<div class="flex items-center gap-3 min-w-0">
							<div
								class="size-8 rounded-lg flex items-center justify-center shrink-0 {selectedBrowser ===
								browser.id
									? 'bg-blue-500 text-white'
									: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'}"
							>
								{#if browser.id === 'chrome'}
									<svg class="size-5" viewBox="0 0 24 24" fill="currentColor">
										<path
											d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8 0-.55.06-1.08.17-1.6L8 14.23V16c0 1.1.9 2 2 2h4v1.93c-.63.05-1.3.07-2 .07zm6.93-5.27C18.61 13.9 17.41 13 16 13h-1v-3c0-.55-.45-1-1-1h-4V7h2c.55 0 1-.45 1-1V4.26c3.48 1.48 6 4.93 6 8.95 0 .53-.05 1.05-.07 1.52z"
										/>
									</svg>
								{:else if browser.id === 'firefox'}
									<svg class="size-5" viewBox="0 0 24 24" fill="currentColor">
										<path
											d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm3.7 4.9a6.8 6.8 0 0 1 1.7 4.7 6.9 6.9 0 0 1-1.6 4.6 5.2 5.2 0 0 1-4.1 1.8 5.6 5.6 0 0 1-5.3-4.1 4.8 4.8 0 0 1 .6-3.8 6.5 6.5 0 0 1 3.5-2.7c.3 1 .9 1.8 1.8 2.2a2.6 2.6 0 0 0 1.2-3.2 4.9 4.9 0 0 1 2.2.5z"
										/>
									</svg>
								{:else if browser.id === 'brave'}
									<svg class="size-5" viewBox="0 0 24 24" fill="currentColor">
										<path
											d="M12 2L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-3zm0 4.18A4.82 4.82 0 0 1 16.82 11c0 3.1-2.28 5.9-4.82 6.72A7.32 7.32 0 0 1 7.18 11 4.82 4.82 0 0 1 12 6.18z"
										/>
									</svg>
								{:else if browser.id === 'tor'}
									<svg class="size-5" viewBox="0 0 24 24" fill="currentColor">
										<path
											d="M12 2A10 10 0 0 0 2 12a10 10 0 0 0 10 10 10 10 0 0 0 10-10A10 10 0 0 0 12 2zm0 2a8 8 0 0 1 8 8c0 3.3-2 6.1-4.9 7.3A7.95 7.95 0 0 1 12 4zm0 3a5 5 0 0 1 5 5 5 5 0 0 1-3.2 4.6A4.98 4.98 0 0 1 12 7z"
										/>
									</svg>
								{:else}
									<GlobeAlt className="size-5" />
								{/if}
							</div>
							<div class="truncate">
								<div class="flex items-center gap-1.5 font-medium text-sm text-gray-900 dark:text-gray-100">
									<span>{browser.name}</span>
									{#if browser.default || browser.id === 'chrome'}
										<span
											class="text-[10px] font-semibold uppercase px-1.5 py-0.2 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300"
										>
											{$i18n.t('Default')}
										</span>
									{/if}
								</div>
								{#if browser.description}
									<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
										{browser.description}
									</div>
								{/if}
							</div>
						</div>

						<div class="shrink-0 ml-2">
							{#if selectedBrowser === browser.id}
								<div
									class="size-5 rounded-full bg-blue-500 text-white flex items-center justify-center"
								>
									<Check className="size-3.5" strokeWidth="2.5" />
								</div>
							{:else}
								<div class="size-5 rounded-full border border-gray-300 dark:border-gray-700"></div>
							{/if}
						</div>
					</button>
				{/each}
			</div>

			<div class="flex justify-end gap-2 pt-4">
				<button
					class="px-4 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 transition rounded-xl"
					on:click={() => {
						show = false;
					}}
					type="button"
				>
					{$i18n.t('Close')}
				</button>
			</div>
		</div>
	</div>
</Modal>
