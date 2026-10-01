<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { getCodeExecutionConfig, setCodeExecutionConfig } from '$lib/apis/configs';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';

	const i18n: any = getContext('i18n');

	export let saveHandler: Function;

	let config: any = null;

	let engines = ['pyodide', 'jupyter', 'e2b', 'self_hosted'];
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const submitHandler = async () => {
		const res = await setCodeExecutionConfig(localStorage.token, config);
	};

	onMount(async () => {
		const res = await getCodeExecutionConfig(localStorage.token);

		if (res) {
			config = res;
		}
	});
</script>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('settings.admin.codeExecution.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if config}
			<AdminSettingSection
				title={$i18n.t('settings.admin.codeExecution.sections.codeExecution.title')}
				first
			>
				<AdminSettingRow
					label={$i18n.t('settings.admin.codeExecution.enableCodeExecution.label')}
					description={$i18n.t('settings.admin.codeExecution.enableCodeExecution.description')}
					let:labelId
				>
					<Switch bind:state={config.ENABLE_CODE_EXECUTION} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if config.ENABLE_CODE_EXECUTION}
					<AdminSettingRow
						label={$i18n.t('settings.admin.codeExecution.codeExecutionEngine.label')}
						description={config.CODE_EXECUTION_ENGINE === 'jupyter'
							? $i18n.t(
									'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks\u2014proceed with extreme caution.'
								)
							: $i18n.t('settings.admin.codeExecution.codeExecutionEngine.description')}
					>
						<SettingsSelect
							bind:value={config.CODE_EXECUTION_ENGINE}
							placeholder={$i18n.t('Select a engine')}
							required
						>
							<option disabled selected value="">{$i18n.t('Select a engine')}</option>
							{#each engines as engine}
								<option value={engine}>{engine}{engine === 'jupyter' ? ' (Legacy)' : ''}</option>
							{/each}
						</SettingsSelect>
					</AdminSettingRow>

					{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
						<AdminSettingField
							label={$i18n.t('settings.admin.codeExecution.codeExecutionJupyterUrl.label')}
							description={$i18n.t(
								'settings.admin.codeExecution.codeExecutionJupyterUrl.description'
							)}
						>
							<input
								class={inputClass}
								type="text"
								placeholder={$i18n.t('Enter Jupyter URL')}
								bind:value={config.CODE_EXECUTION_JUPYTER_URL}
								autocomplete="off"
							/>
						</AdminSettingField>

						<!-- LICENSE covers this Open WebUI wordmark.
							Do not alter, remove, obscure, or replace it except as LICENSE permits:
							https://docs.openwebui.com/license. -->
						<AdminSettingRow
							label={$i18n.t('settings.admin.codeExecution.codeExecutionJupyterAuth.label')}
							description={$i18n.t(
								'settings.admin.codeExecution.codeExecutionJupyterAuth.description'
							)}
						>
							<SettingsSelect
								bind:value={config.CODE_EXECUTION_JUPYTER_AUTH}
								placeholder={$i18n.t('Select an auth method')}
							>
								<option selected value="">{$i18n.t('None')}</option>
								<option value="token">{$i18n.t('Token')}</option>
								<option value="password">{$i18n.t('Password')}</option>
							</SettingsSelect>
						</AdminSettingRow>

						{#if config.CODE_EXECUTION_JUPYTER_AUTH}
							<AdminSettingField
								label={config.CODE_EXECUTION_JUPYTER_AUTH === 'password'
									? $i18n.t('settings.admin.codeExecution.codeExecutionJupyterAuthPassword.label')
									: $i18n.t('settings.admin.codeExecution.codeExecutionJupyterAuthToken.label')}
								description={$i18n.t(
									'settings.admin.codeExecution.codeExecutionJupyterAuthPassword.description'
								)}
							>
								{#if config.CODE_EXECUTION_JUPYTER_AUTH === 'password'}
									<SensitiveInput
										variant="settings"
										type="text"
										placeholder={$i18n.t('Enter Jupyter Password')}
										bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD}
										autocomplete="off"
									/>
								{:else}
									<SensitiveInput
										variant="settings"
										type="text"
										placeholder={$i18n.t('Enter Jupyter Token')}
										bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN}
										autocomplete="off"
									/>
								{/if}
							</AdminSettingField>
						{/if}

						<AdminSettingField
							label={$i18n.t('settings.admin.codeExecution.codeExecutionJupyterTimeout.label')}
							description={$i18n.t(
								'settings.admin.codeExecution.codeExecutionJupyterTimeout.description'
							)}
						>
							<input
								class={inputClass}
								type="number"
								bind:value={config.CODE_EXECUTION_JUPYTER_TIMEOUT}
								placeholder={$i18n.t('e.g. 60')}
								autocomplete="off"
							/>
						</AdminSettingField>
					{/if}
				{/if}
			</AdminSettingSection>

			<AdminSettingSection
				title={$i18n.t('settings.admin.codeExecution.sections.codeInterpreter.title')}
			>
				<AdminSettingRow
					label={$i18n.t('settings.admin.codeExecution.enableCodeInterpreter.label')}
					description={$i18n.t('settings.admin.codeExecution.enableCodeInterpreter.description')}
					let:labelId
				>
					<Switch bind:state={config.ENABLE_CODE_INTERPRETER} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if config.ENABLE_CODE_INTERPRETER}
					<AdminSettingRow
						label={$i18n.t('settings.admin.codeExecution.codeInterpreterEngine.label')}
						description={config.CODE_INTERPRETER_ENGINE === 'jupyter'
							? $i18n.t(
									'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks\u2014proceed with extreme caution.'
								)
							: $i18n.t('settings.admin.codeExecution.codeInterpreterEngine.description')}
					>
						<SettingsSelect
							bind:value={config.CODE_INTERPRETER_ENGINE}
							placeholder={$i18n.t('Select a engine')}
							required
						>
							<option disabled selected value="">{$i18n.t('Select a engine')}</option>
							{#each engines as engine}
								<option value={engine}>{engine}{engine === 'jupyter' ? ' (Legacy)' : ''}</option>
							{/each}
						</SettingsSelect>
					</AdminSettingRow>

					{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
						<AdminSettingField
							label={$i18n.t('settings.admin.codeExecution.codeInterpreterJupyterUrl.label')}
							description={$i18n.t(
								'settings.admin.codeExecution.codeInterpreterJupyterUrl.description'
							)}
						>
							<input
								class={inputClass}
								type="text"
								placeholder={$i18n.t('Enter Jupyter URL')}
								bind:value={config.CODE_INTERPRETER_JUPYTER_URL}
								autocomplete="off"
							/>
						</AdminSettingField>

						<!-- LICENSE covers this Open WebUI wordmark.
							Do not alter, remove, obscure, or replace it except as LICENSE permits:
							https://docs.openwebui.com/license. -->
						<AdminSettingRow
							label={$i18n.t('settings.admin.codeExecution.codeInterpreterJupyterAuth.label')}
							description={$i18n.t(
								'settings.admin.codeExecution.codeInterpreterJupyterAuth.description'
							)}
						>
							<SettingsSelect
								bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH}
								placeholder={$i18n.t('Select an auth method')}
							>
								<option selected value="">{$i18n.t('None')}</option>
								<option value="token">{$i18n.t('Token')}</option>
								<option value="password">{$i18n.t('Password')}</option>
							</SettingsSelect>
						</AdminSettingRow>

						{#if config.CODE_INTERPRETER_JUPYTER_AUTH}
							<AdminSettingField
								label={config.CODE_INTERPRETER_JUPYTER_AUTH === 'password'
									? $i18n.t('settings.admin.codeExecution.codeInterpreterJupyterAuthPassword.label')
									: $i18n.t('settings.admin.codeExecution.codeInterpreterJupyterAuthToken.label')}
								description={$i18n.t(
									'settings.admin.codeExecution.codeInterpreterJupyterAuthPassword.description'
								)}
							>
								{#if config.CODE_INTERPRETER_JUPYTER_AUTH === 'password'}
									<SensitiveInput
										variant="settings"
										type="text"
										placeholder={$i18n.t('Enter Jupyter Password')}
										bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD}
										autocomplete="off"
									/>
								{:else}
									<SensitiveInput
										variant="settings"
										type="text"
										placeholder={$i18n.t('Enter Jupyter Token')}
										bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN}
										autocomplete="off"
									/>
								{/if}
							</AdminSettingField>
						{/if}

						<AdminSettingField
							label={$i18n.t('settings.admin.codeExecution.codeInterpreterJupyterTimeout.label')}
							description={$i18n.t(
								'settings.admin.codeExecution.codeInterpreterJupyterTimeout.description'
							)}
						>
							<input
								class={inputClass}
								type="number"
								bind:value={config.CODE_INTERPRETER_JUPYTER_TIMEOUT}
								placeholder={$i18n.t('e.g. 60')}
								autocomplete="off"
							/>
						</AdminSettingField>
					{/if}

					{#if config.CODE_INTERPRETER_ENGINE === 'e2b'}
						<AdminSettingField
							label={$i18n.t('E2B API Key')}
							description={$i18n.t('API Key from your e2b.dev account for sandboxed microVM execution.')}
						>
							<SensitiveInput
								variant="settings"
								type="text"
								placeholder={$i18n.t('Enter E2B API Key (e2b_...)')}
								bind:value={config.CODE_INTERPRETER_E2B_API_KEY}
								autocomplete="off"
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('E2B Template ID')}
							description={$i18n.t('Custom E2B sandbox template ID (default: base).')}
						>
							<input
								class={inputClass}
								type="text"
								placeholder="base"
								bind:value={config.CODE_INTERPRETER_E2B_TEMPLATE}
								autocomplete="off"
							/>
						</AdminSettingField>

						<div class="rounded-xl bg-blue-500/10 border border-blue-500/20 p-3.5 text-xs text-blue-900 dark:text-blue-200 mt-2 mb-2 space-y-1.5">
							<div class="font-semibold flex items-center gap-1.5">
								<span>🚀</span> {$i18n.t('E2B Sandboxed Execution Setup Guide')}
							</div>
							<p class="leading-relaxed">
								{$i18n.t('E2B runs code and commands inside secure cloud microVMs with full OS capabilities, package management, and internet access.')}
							</p>
							<ol class="list-decimal pl-4 space-y-1">
								<li>{$i18n.t('Create an account at')} <a href="https://e2b.dev" target="_blank" rel="noreferrer" class="underline font-medium hover:text-blue-600">e2b.dev</a>.</li>
								<li>{$i18n.t('Copy your API Key from the dashboard and paste it into the field above.')}</li>
								<li>{$i18n.t('Save settings. The model will now run Python and shell tools securely in dedicated E2B sandboxes.')}</li>
							</ol>
						</div>
					{/if}

					{#if config.CODE_INTERPRETER_ENGINE === 'self_hosted'}
						<AdminSettingField
							label={$i18n.t('Sandbox Runner URL')}
							description={$i18n.t('HTTP endpoint of your self-hosted Docker sandbox runner.')}
						>
							<input
								class={inputClass}
								type="text"
								placeholder="http://localhost:8080"
								bind:value={config.CODE_INTERPRETER_SANDBOX_URL}
								autocomplete="off"
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Sandbox Runner Auth Token')}
							description={$i18n.t('Bearer authentication token (optional).')}
						>
							<SensitiveInput
								variant="settings"
								type="text"
								placeholder={$i18n.t('Enter Auth Token')}
								bind:value={config.CODE_INTERPRETER_SANDBOX_AUTH_TOKEN}
								autocomplete="off"
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Timeout (seconds)')}
							description={$i18n.t('Execution timeout in seconds.')}
						>
							<input
								class={inputClass}
								type="number"
								bind:value={config.CODE_INTERPRETER_SANDBOX_TIMEOUT}
								placeholder="60"
								autocomplete="off"
							/>
						</AdminSettingField>

						<div class="rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-3.5 text-xs text-emerald-900 dark:text-emerald-200 mt-2 mb-2 space-y-1.5">
							<div class="font-semibold flex items-center gap-1.5">
								<span>🐳</span> {$i18n.t('Self-Hosted Docker Sandbox Setup Guide')}
							</div>
							<p class="leading-relaxed">
								{$i18n.t('Run your own isolated code runner container for private, on-premise execution.')}
							</p>
							<ol class="list-decimal pl-4 space-y-1">
								<li>{$i18n.t('Start the runner container:')} <code class="px-1 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 font-mono">docker run -d -p 8080:8080 --name sandbox-runner openwebui/sandbox-runner:latest</code></li>
								<li>{$i18n.t('Provide the container endpoint (e.g. http://localhost:8080 or docker network DNS).')}</li>
								<li>{$i18n.t('Save settings to enable on-premise execution for code and terminal commands.')}</li>
							</ol>
						</div>
					{/if}

					<AdminSettingField
						label={$i18n.t('settings.admin.codeExecution.codeInterpreterPromptTemplate.label')}
						description={$i18n.t(
							'settings.admin.codeExecution.codeInterpreterPromptTemplate.description'
						)}
					>
						<Textarea
							className={textareaClass}
							bind:value={config.CODE_INTERPRETER_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</AdminSettingField>
				{/if}
			</AdminSettingSection>
		{/if}
	</div>
	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
