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
		{ value: null, label: 'Off' },
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
			class="bg-transparent hover:bg-gray-100 {currentReasoning
				? 'text-amber-500 dark:text-amber-400'
				: 'text-gray-700 dark:text-white'} dark:hover:bg-gray-800 rounded-full size-[1.875rem] flex justify-center items-center outline-hidden focus:outline-hidden shrink-0 transition"
			aria-label={$i18n.t('Reasoning')}
			type="button"
		>
			<LightBulb className="size-4.5" strokeWidth={currentReasoning ? '2' : '1.5'} />
		</button>
	</Tooltip>
	<div slot="content">
		<DropdownMenu className="min-w-44 max-w-48 max-h-72 overflow-hidden p-1.5">
			<div class="px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400">
				{$i18n.t('Thinking Level')}
			</div>
			<div class="flex flex-col gap-0.5">
				{#each options as option}
					<button
						class="relative flex w-full gap-2 items-center px-2 py-1.5 text-xs font-normal cursor-pointer rounded-xl hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition"
						on:click={() => setReasoning(option.value)}
					>
						<div class="flex-1 text-left truncate">
							{option.value === null
								? $i18n.language === 'tr-TR'
									? 'Kapalı'
									: $i18n.t('Off')
								: $i18n.t(option.label)}
						</div>
						{#if currentReasoning === option.value}
							<div class="shrink-0 text-amber-500 dark:text-amber-400">
								<Check className="size-3.5" strokeWidth="2.5" />
							</div>
						{/if}
					</button>
				{/each}
			</div>
		</DropdownMenu>
	</div>
</Dropdown>
