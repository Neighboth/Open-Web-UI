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
		if (config?.BROWSER_SANDBOX_ENABLE && config?.BROWSER_SANDBOX_PROVIDER === 'kasm') {
			if (config.KASM_WORKSPACES_URL && !config.BROWSER_SANDBOX_LIVE_URL) {
				const baseUrl = config.KASM_WORKSPACES_URL.replace(/\/+$/, '');
				const pw = config.KASM_WORKSPACES_PASSWORD
					? `?password=${encodeURIComponent(config.KASM_WORKSPACES_PASSWORD)}&username=${encodeURIComponent(config.KASM_WORKSPACES_USER || 'kasm_user')}`
					: '';
				config.BROWSER_SANDBOX_LIVE_URL = `${baseUrl}/${pw}`;
			}
			if (config.KASM_CDP_URL && !config.BROWSER_SANDBOX_URL) {
				config.BROWSER_SANDBOX_URL = config.KASM_CDP_URL;
			}
		}
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

					{#if config.CODE_EXECUTION_ENGINE === 'e2b'}
						<AdminSettingField
							label={$i18n.t('E2B API Key')}
							description={$i18n.t(
								'API Key from your e2b.dev account for sandboxed microVM execution.'
							)}
						>
							<SensitiveInput
								variant="settings"
								type="text"
								placeholder={$i18n.t('Enter E2B API Key (e2b_...)')}
								bind:value={config.CODE_EXECUTION_E2B_API_KEY}
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
								bind:value={config.CODE_EXECUTION_E2B_TEMPLATE}
								autocomplete="off"
							/>
						</AdminSettingField>

						<div
							class="rounded-xl bg-blue-500/10 border border-blue-500/20 p-3.5 text-xs text-blue-900 dark:text-blue-200 mt-2 mb-2 space-y-1.5"
						>
							<div class="font-semibold flex items-center gap-1.5">
								<span>🚀</span>
								{$i18n.t('E2B Sandboxed Execution Setup Guide')}
							</div>
							<p class="leading-relaxed">
								{$i18n.t(
									'E2B runs code and commands inside secure cloud microVMs with full OS capabilities, package management, and internet access.'
								)}
							</p>
							<ol class="list-decimal pl-4 space-y-1">
								<li>
									{$i18n.t('Create an account at')}
									<a
										href="https://e2b.dev"
										target="_blank"
										rel="noreferrer"
										class="underline font-medium hover:text-blue-600">e2b.dev</a
									>.
								</li>
								<li>
									{$i18n.t(
										'Copy your API Key from the dashboard and paste it into the field above.'
									)}
								</li>
								<li>
									{$i18n.t(
										'Save settings. The model will now run Python and shell tools securely in dedicated E2B sandboxes.'
									)}
								</li>
							</ol>
						</div>
					{/if}

					{#if config.CODE_EXECUTION_ENGINE === 'self_hosted'}
						<AdminSettingField
							label={$i18n.t('Sandbox Runner URL')}
							description={$i18n.t('HTTP endpoint of your self-hosted Docker sandbox runner.')}
						>
							<input
								class={inputClass}
								type="text"
								placeholder="http://localhost:8080"
								bind:value={config.CODE_EXECUTION_SANDBOX_URL}
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
								bind:value={config.CODE_EXECUTION_SANDBOX_AUTH_TOKEN}
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
								bind:value={config.CODE_EXECUTION_SANDBOX_TIMEOUT}
								placeholder="60"
								autocomplete="off"
							/>
						</AdminSettingField>

						<div
							class="rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-3.5 text-xs text-emerald-900 dark:text-emerald-200 mt-2 mb-2 space-y-1.5"
						>
							<div class="font-semibold flex items-center gap-1.5">
								<span>🐳</span>
								{$i18n.t('Self-Hosted Docker Sandbox Setup Guide')}
							</div>
							<p class="leading-relaxed">
								{$i18n.t(
									'Run your own isolated code runner container for private, on-premise execution.'
								)}
							</p>
							<ol class="list-decimal pl-4 space-y-1">
								<li>
									{$i18n.t('Start the runner container:')}
									<code class="px-1 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 font-mono"
										>docker run -d -p 8080:8080 --name sandbox-runner
										openwebui/sandbox-runner:latest</code
									>
								</li>
								<li>
									{$i18n.t(
										'Provide the container endpoint (e.g. http://localhost:8080 or docker network DNS).'
									)}
								</li>
								<li>
									{$i18n.t(
										'Save settings to enable on-premise execution for code and terminal commands.'
									)}
								</li>
							</ol>
						</div>
					{/if}
				{/if}
			</AdminSettingSection>

			<hr class="my-10 border-t-2 border-gray-200 dark:border-gray-800" />

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
							description={$i18n.t(
								'API Key from your e2b.dev account for sandboxed microVM execution.'
							)}
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

						<div
							class="rounded-xl bg-blue-500/10 border border-blue-500/20 p-3.5 text-xs text-blue-900 dark:text-blue-200 mt-2 mb-2 space-y-1.5"
						>
							<div class="font-semibold flex items-center gap-1.5">
								<span>🚀</span>
								{$i18n.t('E2B Sandboxed Execution Setup Guide')}
							</div>
							<p class="leading-relaxed">
								{$i18n.t(
									'E2B runs code and commands inside secure cloud microVMs with full OS capabilities, package management, and internet access.'
								)}
							</p>
							<ol class="list-decimal pl-4 space-y-1">
								<li>
									{$i18n.t('Create an account at')}
									<a
										href="https://e2b.dev"
										target="_blank"
										rel="noreferrer"
										class="underline font-medium hover:text-blue-600">e2b.dev</a
									>.
								</li>
								<li>
									{$i18n.t(
										'Copy your API Key from the dashboard and paste it into the field above.'
									)}
								</li>
								<li>
									{$i18n.t(
										'Save settings. The model will now run Python and shell tools securely in dedicated E2B sandboxes.'
									)}
								</li>
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

						<div
							class="rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-3.5 text-xs text-emerald-900 dark:text-emerald-200 mt-2 mb-2 space-y-1.5"
						>
							<div class="font-semibold flex items-center gap-1.5">
								<span>🐳</span>
								{$i18n.t('Self-Hosted Docker Sandbox Setup Guide')}
							</div>
							<p class="leading-relaxed">
								{$i18n.t(
									'Run your own isolated code runner container for private, on-premise execution.'
								)}
							</p>
							<ol class="list-decimal pl-4 space-y-1">
								<li>
									{$i18n.t('Start the runner container:')}
									<code class="px-1 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 font-mono"
										>docker run -d -p 8080:8080 --name sandbox-runner
										openwebui/sandbox-runner:latest</code
									>
								</li>
								<li>
									{$i18n.t(
										'Provide the container endpoint (e.g. http://localhost:8080 or docker network DNS).'
									)}
								</li>
								<li>
									{$i18n.t(
										'Save settings to enable on-premise execution for code and terminal commands.'
									)}
								</li>
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

			<hr class="my-10 border-t-2 border-gray-200 dark:border-gray-800" />

			<AdminSettingSection
				title={$i18n.t('Computer Use / Live Agent Preview (Browser & OS Sandbox)')}
			>
				<AdminSettingRow
					label={$i18n.t('Enable Browser / Computer Use Sandbox')}
					description={$i18n.t(
						'Allow models to control a headless or graphical browser and operating system session.'
					)}
					let:labelId
				>
					<Switch bind:state={config.BROWSER_SANDBOX_ENABLE} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if config.BROWSER_SANDBOX_ENABLE}
					<AdminSettingRow
						label={$i18n.t('Sandbox Provider')}
						description={$i18n.t('Select browser or virtual workspace environment')}
					>
						<SettingsSelect
							bind:value={config.BROWSER_SANDBOX_PROVIDER}
							placeholder={$i18n.t('Select Provider')}
						>
							<option value="browserless">{$i18n.t('Browserless (Chromium / Playwright)')}</option>
							<option value="kasm">{$i18n.t('Kasm Workspaces (KasmVNC / Isolated Desktop)')}</option>
							<option value="vnc">{$i18n.t('Generic noVNC / Linux Desktop')}</option>
						</SettingsSelect>
					</AdminSettingRow>

					{#if (config.BROWSER_SANDBOX_PROVIDER ?? 'browserless') === 'kasm'}
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2 mt-2">
							<AdminSettingField
								label={$i18n.t('Kasm Web / Stream URL')}
								description={$i18n.t('Kasm Workspaces or KasmVNC web endpoint (e.g. https://localhost:6901)')}
							>
								<input
									class={inputClass}
									type="text"
									placeholder="https://localhost:6901"
									bind:value={config.KASM_WORKSPACES_URL}
									autocomplete="off"
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('Kasm VNC Password / Auth Token')}
								description={$i18n.t('VNC_PW password or API token for auto-login')}
							>
								<SensitiveInput
									variant="settings"
									type="text"
									placeholder={$i18n.t('Enter VNC Password or Token')}
									bind:value={config.KASM_WORKSPACES_PASSWORD}
									autocomplete="off"
								/>
							</AdminSettingField>
						</div>

						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('Kasm Username')}
								description={$i18n.t('Default: kasm_user')}
							>
								<input
									class={inputClass}
									type="text"
									placeholder="kasm_user"
									bind:value={config.KASM_WORKSPACES_USER}
									autocomplete="off"
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('Remote Debugging / CDP Endpoint')}
								description={$i18n.t('Chromium CDP port for automation (e.g. http://localhost:9222)')}
							>
								<input
									class={inputClass}
									type="text"
									placeholder="http://localhost:9222"
									bind:value={config.KASM_CDP_URL}
									autocomplete="off"
								/>
							</AdminSettingField>
						</div>

						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('Kasm API Key (On-Demand Mode)')}
								description={$i18n.t('Optional API Key for auto-spawning containers via /request_kasm')}
							>
								<SensitiveInput
									variant="settings"
									type="text"
									placeholder={$i18n.t('Enter Kasm API Key')}
									bind:value={config.KASM_WORKSPACES_API_KEY}
									autocomplete="off"
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('Kasm API Secret (On-Demand Mode)')}
								description={$i18n.t('API Secret to authorize container requests & destruction')}
							>
								<SensitiveInput
									variant="settings"
									type="text"
									placeholder={$i18n.t('Enter Kasm API Secret')}
									bind:value={config.KASM_WORKSPACES_API_SECRET}
									autocomplete="off"
								/>
							</AdminSettingField>
						</div>

						<AdminSettingField
							label={$i18n.t('Live Screen / Web Preview URL')}
							description={$i18n.t('Live streaming URL rendered in chat side-panel (auto-login supported).')}
						>
							<input
								class={inputClass}
								type="text"
								placeholder="https://localhost:6901/?password=..."
								bind:value={config.BROWSER_SANDBOX_LIVE_URL}
								autocomplete="off"
							/>
						</AdminSettingField>

					{:else if config.BROWSER_SANDBOX_PROVIDER === 'vnc'}
						<AdminSettingField
							label={$i18n.t('Live Screen / Web VNC Stream URL')}
							description={$i18n.t(
								'URL to render inside the live agent preview pane so users can watch and interact in real-time (e.g. http://localhost:6080/vnc.html).'
							)}
						>
							<input
								class={inputClass}
								type="text"
								placeholder="http://localhost:6080/vnc.html"
								bind:value={config.BROWSER_SANDBOX_LIVE_URL}
								autocomplete="off"
							/>
						</AdminSettingField>

					{:else}
						<AdminSettingField
							label={$i18n.t('Browser Sandbox URL / Endpoint')}
							description={$i18n.t(
								'Self-hosted Browserless / Chromium / Playwright container or cloud service (e.g. http://localhost:3000 or wss://chrome.browserless.io).'
							)}
						>
							<input
								class={inputClass}
								type="text"
								placeholder="http://localhost:3000"
								bind:value={config.BROWSER_SANDBOX_URL}
								autocomplete="off"
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Browser Sandbox Auth Token')}
							description={$i18n.t('API token for browser service authentication (optional).')}
						>
							<SensitiveInput
								variant="settings"
								type="text"
								placeholder={$i18n.t('Enter Auth Token')}
								bind:value={config.BROWSER_SANDBOX_AUTH_TOKEN}
								autocomplete="off"
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Live Screen / Web VNC Stream URL')}
							description={$i18n.t(
								'URL to render inside the live agent preview pane so users can watch and interact in real-time (e.g. http://localhost:6080/vnc.html).'
							)}
						>
							<input
								class={inputClass}
								type="text"
								placeholder="http://localhost:6080/vnc.html"
								bind:value={config.BROWSER_SANDBOX_LIVE_URL}
								autocomplete="off"
							/>
						</AdminSettingField>
					{/if}

					<div class="px-1 text-sm text-gray-500 my-3 space-y-2">
						<p>
							{$i18n.t(
								'Open WebUI supports live UI preview for agents (like Gemini Spark or ChatGPT Agent). This allows models to open a browser or operating system interface on the right side of the chat screen, where you can watch the agent work live and take over manually if needed.'
							)}
						</p>

						<p class="font-medium text-gray-700 dark:text-gray-300 mt-2">
							{$i18n.t('Per-User & Per-Chat Zero-Idle Sandbox Isolation:')}
						</p>
						<p class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t(
								'Every chat runs in an isolated context directory (/data/browser_sessions/${userId}_${chatId}). Browser and container instances automatically freeze / spin-down after 5 minutes of inactivity (consuming 0 CPU and 0 RAM) and instantly resume when returning to the conversation, preserving cookies, logins, and session data permanently.'
							)}
						</p>

						<p class="font-medium text-gray-700 dark:text-gray-300 mt-2">
							{$i18n.t('Self-Hosted Browser Quickstart Guide:')}
						</p>
						<ol
							class="list-decimal list-inside ml-2 space-y-2 text-xs text-gray-600 dark:text-gray-400"
						>
							<li>
								<strong>{$i18n.t('Kasm Workspaces / KasmVNC (Isolated Chrome with CDP Automation):')}</strong>
								<code class="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded font-mono text-[11px] block mt-0.5"
									>docker run --rm -d --shm-size=512m -p 6901:6901 -p 9222:9222 -e VNC_PW=password -e APP_ARGS="--remote-debugging-port=9222 --remote-debugging-address=0.0.0.0" kasmweb/chrome:1.16.0</code
								>
							</li>
							<li>
								<strong>{$i18n.t('Run Browserless / Chrome via Docker:')}</strong>
								<code class="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded font-mono text-[11px] block mt-0.5"
									>docker run -d -p 3000:3000 -e "CONCURRENT=10" ghcr.io/browserless/chromium</code
								>
							</li>
							<li>
								<strong>{$i18n.t('For full Linux OS & GUI with VNC preview (noVNC):')}</strong>
								<code class="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded font-mono text-[11px] block mt-0.5"
									>docker run -d -p 6080:80 -v /dev/shm:/dev/shm dorowu/ubuntu-desktop-lxde-vnc</code
								>
							</li>
							<li>
								{$i18n.t(
									'Enter the endpoint and live VNC/Kasm URL above. When the model invokes the browser or OS agent, the screen will slide open on the right.'
								)}
							</li>
						</ol>
					</div>
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
