<script>
	import { agentLiveUrl, agentLiveNotice, chatId } from '$lib/stores';
	import XMark from '$lib/components/icons/XMark.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import { getContext, onDestroy } from 'svelte';
	import { stopBrowserSession } from '$lib/apis/browser';

	const i18n = getContext('i18n');

	const handleClose = async () => {
		agentLiveUrl.set(null);
		agentLiveNotice.set(null);
		if ($chatId) {
			try {
				await stopBrowserSession(localStorage.token, $chatId);
			} catch (e) {
				console.debug('Failed to stop browser session:', e);
			}
		}
	};

	const openInWindow = () => {
		if (!$agentLiveUrl) return;
		const w = Math.min(1440, Math.floor(window.screen.availWidth * 0.9));
		const h = Math.min(900, Math.floor(window.screen.availHeight * 0.9));
		const left = Math.floor((window.screen.availWidth - w) / 2);
		const top = Math.floor((window.screen.availHeight - h) / 2);
		const win = window.open(
			$agentLiveUrl,
			'kasm_agent_preview',
			`popup=yes,width=${w},height=${h},top=${top},left=${left},menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes`
		);
		if (win) {
			win.focus();
		}
	};

	onDestroy(() => {
		agentLiveNotice.set(null);
		if ($agentLiveUrl && $chatId) {
			try {
				stopBrowserSession(localStorage.token, $chatId);
			} catch (e) {
				console.debug('Failed to stop browser session on destroy:', e);
			}
		}
	});
</script>

{#if $agentLiveUrl}
	<div
		class="h-full w-full md:max-w-[50vw] fixed md:relative inset-0 md:inset-auto z-50 md:z-auto bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 flex flex-col transition-all duration-300 shrink-0 shadow-2xl md:shadow-none"
	>
		<div
			class="h-12 flex items-center justify-between px-3 border-b border-gray-200 dark:border-gray-800 shrink-0 bg-white dark:bg-gray-950"
		>
			<div class="font-medium text-sm flex gap-2 items-center text-gray-800 dark:text-gray-200 truncate">
				<GlobeAlt className="size-4 text-blue-500 shrink-0" />
				<span class="truncate">{$i18n.t('Live Agent Preview')}</span>
			</div>
			<div class="flex gap-1.5 items-center shrink-0">
				<button
					type="button"
					on:click={openInWindow}
					class="px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:hover:bg-emerald-900/60 dark:text-emerald-300 text-xs font-medium flex items-center gap-1.5 transition border border-emerald-200/50 dark:border-emerald-800/50 cursor-pointer"
					title="Düz Tarayıcıda Aç (Pop-out Pencere)"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="size-3.5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0H3"
						/>
					</svg>
					<span>{$i18n.t('Düz Tarayıcıda Aç')}</span>
				</button>
				<a
					href={$agentLiveUrl}
					target="_blank"
					rel="noreferrer"
					class="px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 dark:bg-blue-950/60 dark:hover:bg-blue-900/60 dark:text-blue-300 text-xs font-medium flex items-center gap-1.5 transition border border-blue-200/50 dark:border-blue-800/50"
					title="Yeni Sekmede Aç"
				>
					<span>{$i18n.t('Yeni Sekmede Aç')}</span>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="size-3.5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
						/>
					</svg>
				</a>
				<button
					on:click={handleClose}
					class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 transition cursor-pointer"
					title="Kapat"
				>
					<XMark className="size-4" />
				</button>
			</div>
		</div>
		{#if $agentLiveNotice}
			<div class="px-4 py-3 bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-900/60 text-xs text-amber-900 dark:text-amber-200">
				<p class="font-semibold mb-1">{$i18n.t('The live preview cannot be embedded')}</p>
				<p class="mb-3">{$agentLiveNotice}</p>
				<button
					type="button"
					on:click={openInWindow}
					class="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-medium transition"
				>
					{$i18n.t('Open in a new tab')}
				</button>
			</div>
		{/if}
		<div class="px-3 py-1.5 bg-blue-50/80 dark:bg-blue-950/40 border-b border-blue-100 dark:border-blue-900/50 flex items-center justify-between text-xs text-blue-700 dark:text-blue-300">
			<span class="truncate">Masaüstü açılmazsa veya iframe/SSL engeli olursa:</span>
			<button
				type="button"
				on:click={openInWindow}
				class="underline font-semibold shrink-0 ml-2 hover:text-blue-900 dark:hover:text-blue-100 cursor-pointer flex items-center gap-1"
			>
				Düz Tarayıcıda Aç &rarr;
			</button>
		</div>
		{#if $agentLiveNotice}
			<div class="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900">
				<GlobeAlt className="size-8 text-gray-400" strokeWidth="1.5" />
				<p>{$i18n.t('The session is running. Open it in a new tab to use it.')}</p>
			</div>
		{:else}
			<iframe
				src={$agentLiveUrl}
				class="w-full h-full border-none bg-white dark:bg-gray-900 flex-1"
				title="Agent Preview"
				allow="autoplay; microphone; camera; clipboard-read; clipboard-write; window-management; fullscreen; display-capture; web-share"
				referrerpolicy="no-referrer"
				loading="eager"
			></iframe>
		{/if}
	</div>
{/if}
