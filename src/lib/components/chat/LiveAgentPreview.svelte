<script>
	import { agentLiveUrl, chatId } from '$lib/stores';
	import XMark from '$lib/components/icons/XMark.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import { getContext } from 'svelte';
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
</script>

{#if $agentLiveUrl}
	<div
		class="h-full w-full max-w-[50vw] bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 flex flex-col relative transition-all duration-300 z-50"
	>
		<div
			class="h-12 flex items-center justify-between px-3 border-b border-gray-200 dark:border-gray-800 shrink-0 bg-white dark:bg-gray-950"
		>
			<div class="font-medium text-sm flex gap-2 items-center text-gray-800 dark:text-gray-200">
				<GlobeAlt className="size-4 text-blue-500" />
				{$i18n.t('Live Agent Preview')}
			</div>
			<div class="flex gap-1">
				<a
					href={$agentLiveUrl}
					target="_blank"
					class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500"
					title="Open in new tab"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-4"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
						/></svg
					>
				</a>
				<button
					on:click={handleClose}
					class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500"
				>
					<XMark className="size-4" />
				</button>
			</div>
		</div>
		<iframe
			src={$agentLiveUrl}
			class="w-full h-full border-none bg-white dark:bg-gray-900 flex-1"
			title="Agent Preview"
		></iframe>
	</div>
{/if}
