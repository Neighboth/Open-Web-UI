<script lang="ts">
	import { getContext } from 'svelte';
	import { settings } from '$lib/stores';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n = getContext('i18n') as any;

	export let closeOnOutsideClick = true;
	let show = false;

	const options = [
		{ value: null, label: 'Default' },
		{ value: 'low', label: 'Low' },
		{ value: 'medium', label: 'Medium' },
		{ value: 'high', label: 'High' }
	];

	$: currentReasoning = $settings?.params?.reasoning_effort ?? null;

	const setReasoning = (val: string | null) => {
		settings.set({
			...($settings ?? {}),
			params: {
				...($settings?.params ?? {}),
				reasoning_effort: val
			}
		});
		show = false;
	};
</script>

<Dropdown bind:show {closeOnOutsideClick}>
	<Tooltip content={$i18n.t('Reasoning Effort')} placement="top">
		<button
			class="bg-transparent hover:bg-gray-100 text-gray-700 dark:text-white dark:hover:bg-gray-800 rounded-full size-[1.875rem] flex justify-center items-center outline-hidden focus:outline-hidden shrink-0"
			aria-label={$i18n.t('Reasoning')}
			type="button"
		>
			<LightBulb className="size-4.5" strokeWidth="1.5" />
		</button>
	</Tooltip>
	<div slot="content">
		<DropdownMenu className="min-w-40 max-w-40 max-h-72 overflow-hidden">
			<div class="p-1 flex flex-col gap-0.5">
				{#each options as option}
					<button
						class="relative flex w-full gap-2 items-center px-2 py-1.5 text-sm font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => setReasoning(option.value)}
					>
						<div class="flex-1 text-left truncate">
							{$i18n.t(option.label)}
						</div>
						{#if currentReasoning === option.value}
							<div class="shrink-0 text-gray-600 dark:text-gray-300">
								<Check className="size-3.5" strokeWidth="2.5" />
							</div>
						{/if}
					</button>
				{/each}
			</div>
		</DropdownMenu>
	</div>
</Dropdown>
