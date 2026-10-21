<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { getAvailableBrowsers, type BrowserOption } from '$lib/apis/browser';
	import { updateUserSettings } from '$lib/apis/users';
	import { settings } from '$lib/stores';
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
			logo: '/assets/browsers/chrome.png',
			description: 'Google Chrome with isolated profile & DevTools CDP',
			default: true
		},
		{
			id: 'vivaldi',
			name: 'Vivaldi Browser',
			image: 'kasmweb/vivaldi:1.16.0',
			logo: '/assets/browsers/vivaldi.png',
			description: 'Vivaldi customizable feature-rich browser',
			default: false
		},
		{
			id: 'firefox',
			name: 'Mozilla Firefox',
			image: 'kasmweb/firefox:1.16.0',
			logo: '/assets/browsers/firefox.png',
			description: 'Mozilla Firefox with privacy protections',
			default: false
		}
	];

	let loading = false;

	// The user's own Kasm account.  With it the browser container runs as that
	// account, so the session belongs to the user alone and nobody inherits
	// the sessions of the shared instance account.
	let kasmUser = '';
	let kasmPassword = '';
	let savingKasm = false;

	const loadKasmCredentials = () => {
		const own = ($settings as any)?.browserSandboxKasm ?? ($settings as any)?.ui?.browserSandboxKasm;
		kasmUser = own?.user ?? '';
		kasmPassword = own?.password ?? '';
	};

	const saveKasmCredentials = async () => {
		savingKasm = true;
		const value = kasmUser.trim() && kasmPassword.trim() ? { user: kasmUser.trim(), password: kasmPassword.trim() } : {};
		const res = await updateUserSettings(localStorage.token, { browserSandboxKasm: value }).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		savingKasm = false;
		if (res) {
			settings.set({ ...$settings, browserSandboxKasm: value } as any);
			toast.success($i18n.t('Browser account saved'));
		}
	};

	const loadBrowsers = async () => {
		loading = true;
		try {
			const res = await getAvailableBrowsers(localStorage.token);
			if (res && Array.isArray(res) && res.length > 0) {
				browsers = res;
			}
		} catch (e) {
			console.debug('Using default browser list:', e);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		loadBrowsers();
	});

	$: if (show) {
		selectedBrowser = localStorage.getItem('selected_browser') || 'chrome';
		loadBrowsers();
		loadKasmCredentials();
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
								class="size-8 rounded-lg flex items-center justify-center shrink-0 bg-gray-100/70 dark:bg-gray-800/70 p-1"
							>
								{#if browser.logo || ['chrome', 'chromium', 'firefox', 'brave', 'tor', 'vivaldi', 'edge'].includes(browser.id)}
									<img
										src={browser.logo || `/assets/browsers/${browser.id}.png`}
										alt={browser.name}
										class="size-6 object-contain pointer-events-none"
										on:error={(e) => {
											// Fallback if image fails to load
											e.currentTarget.style.display = 'none';
										}}
									/>
								{:else}
									<GlobeAlt className="size-5 text-gray-500" />
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

			<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
				<div class="text-xs font-semibold mb-1 text-gray-700 dark:text-gray-300">
					{$i18n.t('My Browser Account')}
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
					{$i18n.t(
						'Optional. With your own sandbox account the browser container runs as you, so your session is not shared with anybody else.'
					)}
				</div>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
					<input
						class="w-full h-8 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 placeholder:text-gray-300 focus:border-blue-400 outline-hidden"
						placeholder={$i18n.t('Username')}
						bind:value={kasmUser}
					/>
					<SensitiveInput bind:value={kasmPassword} placeholder={$i18n.t('Password')} />
				</div>
				<div class="flex justify-end mt-3">
					<button
						class="px-3 py-1.5 text-xs font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 transition rounded-lg"
						type="button"
						disabled={savingKasm}
						on:click={saveKasmCredentials}
					>
						{savingKasm ? $i18n.t('Saving...') : $i18n.t('Save Account')}
					</button>
				</div>
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