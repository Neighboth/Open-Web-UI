<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	const i18n = getContext<any>('i18n');

	export let show = false;
	export let tool: any = null;
	export let onSave: Function = () => {};

	let key = '';

	$: if (show && tool) {
		const existing = ($settings as any)?.tools?.[tool.id];
		key = typeof existing === 'string' ? existing : (existing?.key ?? '');
	}

	const submitHandler = async () => {
		if (!tool?.id) return;

		const currentTools = ($settings as any)?.tools ?? {};
		const updatedTools = {
			...currentTools,
			[tool.id]: key.trim()
		};

		const res = await updateUserSettings(localStorage.token, {
			tools: updatedTools
		}).catch((err) => {
			toast.error(`${err}`);
			return null;
		});

		if (res) {
			settings.set({
				...$settings,
				tools: updatedTools
			} as any);
			toast.success($i18n.t('Tool credentials saved'));
			onSave();
			show = false;
		}
	};
</script>

<Modal bind:show size="sm">
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class="flex items-center gap-2 text-base font-medium">
				{#if tool?.meta?.icon}
					<img src={tool.meta.icon} alt={tool.name} class="size-5 object-contain rounded-sm" />
				{/if}
				<span>{tool?.name ?? $i18n.t('Tool Configuration')}</span>
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
				type="button"
			>
				<XMark className="size-5" />
			</button>
		</div>

		<form
			class="flex flex-col w-full px-5 pb-5 dark:text-gray-200"
			on:submit|preventDefault={submitHandler}
		>
			{#if tool?.meta?.user_provided_description}
				<div class="text-xs text-gray-600 dark:text-gray-400 mb-3 whitespace-pre-wrap">
					{tool.meta.user_provided_description}
				</div>
			{:else}
				<div class="text-xs text-gray-600 dark:text-gray-400 mb-3">
					{$i18n.t(
						'This tool requires personal credentials. Please enter your API key or token below.'
					)}
				</div>
			{/if}

			<div class="mb-4">
				<div class="text-xs font-semibold mb-1">
					{$i18n.t('API Key / Token')}
				</div>
				<SensitiveInput
					bind:value={key}
					placeholder={$i18n.t('Enter your credentials')}
					required={false}
				/>
			</div>

			<div class="flex justify-end gap-2 pt-2">
				<button
					class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 transition rounded-full"
					type="button"
					on:click={() => {
						show = false;
					}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
					type="submit"
				>
					{$i18n.t('Save')}
				</button>
			</div>
		</form>
	</div>
</Modal>
