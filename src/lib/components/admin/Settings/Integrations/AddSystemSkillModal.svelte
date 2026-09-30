<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext<any>('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let show = false;
	export let edit = false;
	export let skill: any = null;

	export let onSubmit: Function = () => {};
	export let onDelete: () => void = () => {};

	let id = '';
	let name = '';
	let description = '';
	let content = '';
	let showDeleteConfirmDialog = false;

	const init = () => {
		if (skill) {
			id = skill.id ?? '';
			name = skill.name ?? '';
			description = skill.description ?? '';
			content = skill.content ?? '';
		} else {
			id = '';
			name = '';
			description = '';
			content = '';
		}
	};

	$: if (show) {
		init();
	}

	const submitHandler = () => {
		if (!id.trim()) {
			toast.error($i18n.t('Please enter a skill ID'));
			return;
		}
		if (!name.trim()) {
			toast.error($i18n.t('Please enter a skill name'));
			return;
		}

		onSubmit({
			id: id.trim().toLowerCase().replace(/\s+/g, '-'),
			name: name.trim(),
			description: description.trim(),
			content: content.trim()
		});

		show = false;
	};
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	title={$i18n.t('Delete System Skill')}
	message={$i18n.t('Are you sure you want to delete this system skill? This cannot be undone.')}
	on:confirm={() => {
		onDelete();
		show = false;
	}}
/>

<Modal bind:show size="md">
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{#if edit}
					{$i18n.t('Edit System Skill')}
				{:else}
					{$i18n.t('Add System Skill')}
				{/if}
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
			class="flex flex-col md:flex-row w-full px-5 pb-5 md:space-x-4 dark:text-gray-200"
			on:submit|preventDefault={submitHandler}
		>
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<div class="flex flex-col w-full gap-3">
					<div>
						<div class="text-xs font-semibold mb-1">
							{$i18n.t('Skill ID')}
						</div>
						<input
							class="w-full text-sm bg-transparent rounded-lg border border-gray-300 dark:border-gray-700 px-3 py-2 outline-hidden"
							placeholder="e.g. python-expert"
							bind:value={id}
							disabled={edit}
							required
						/>
					</div>

					<div>
						<div class="text-xs font-semibold mb-1">
							{$i18n.t('Skill Name')}
						</div>
						<input
							class="w-full text-sm bg-transparent rounded-lg border border-gray-300 dark:border-gray-700 px-3 py-2 outline-hidden"
							placeholder="e.g. Python Clean Code Expert"
							bind:value={name}
							required
						/>
					</div>

					<div>
						<div class="text-xs font-semibold mb-1">
							{$i18n.t('Description')}
						</div>
						<input
							class="w-full text-sm bg-transparent rounded-lg border border-gray-300 dark:border-gray-700 px-3 py-2 outline-hidden"
							placeholder={$i18n.t('Brief description for model tool/skill selection')}
							bind:value={description}
						/>
					</div>

					<div>
						<div class="text-xs font-semibold mb-1">
							{$i18n.t('Instructions / Prompt Content')}
						</div>
						<Textarea
							className="w-full text-sm bg-transparent rounded-lg border border-gray-300 dark:border-gray-700 px-3 py-2 outline-hidden min-h-[120px]"
							placeholder={$i18n.t('Instructions, guidelines or system prompt provided by this skill...')}
							bind:value={content}
						/>
					</div>

					<div class="flex justify-between items-center pt-2">
						{#if edit}
							<button
								class="text-xs text-red-500 hover:text-red-700 font-medium"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{:else}
							<div></div>
						{/if}

						<div class="flex gap-2">
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
					</div>
				</div>
			</div>
		</form>
	</div>
</Modal>
