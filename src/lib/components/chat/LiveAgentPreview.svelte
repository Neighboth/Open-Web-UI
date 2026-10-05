<script>
	import { agentLiveUrl, chatId } from '$lib/stores';
	import XMark from '$lib/components/icons/XMark.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import { getContext, onDestroy } from 'svelte';
	import { stopBrowserSession } from '$lib/apis/browser';

	const i18n = getContext('i18n');

	const handleClose = async () => {
		agentLiveUrl.set(null);
		if ($chatId) {
			try {
				await stopBrowserSession(localStorage.token, $chatId);
			} catch (e) {
				console.debug('Failed to stop browser session:', e);
			}
		}
	};

	onDestroy(() => {
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
					class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 transition"
					title="Kapat"
				>
					<XMark className="size-4" />
				</button>
			</div>
		</div>
		<iframe
			src={$agentLiveUrl}
			class="w-full h-full border-none bg-white dark:bg-gray-900 flex-1"
			title="Agent Preview"
			allow="autoplay; microphone; camera; clipboard-read; clipboard-write; window-management; fullscreen; display-capture"
			referrerpolicy="no-referrer"
		></iframe>
	</div>
{/if}
