import re

file_path = 'src/lib/components/chat/MessageInput/IntegrationsMenu.svelte'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace tab = 'tools' and 'skills' buttons with the actual loops
button_regex = re.compile(r'\{\#if Object\.keys\(tools\)\.length > 0\}.*?\{\/if\}\s*\{\#if skills && Object\.keys\(skills\)\.length > 0\}.*?\{\/if\}', re.DOTALL)

tools_block = """
						{#if Object.keys(tools).length > 0}
							<hr class="border-gray-50 dark:border-gray-800 my-1" />
							<div class="flex flex-col gap-0.5">
								{#each toolIds as toolId}
									<button
										class="relative flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
										aria-pressed={(tools?.[toolId]?.authenticated ?? true)
											? selectedToolIds.includes(toolId)
											: undefined}
										on:click={async (e) => {
											await toggleTool(toolId, e);
										}}
									>
										{#if !(tools?.[toolId]?.authenticated ?? true)}
											<!-- make it slighly darker and not clickable -->
											<div class="absolute inset-0 opacity-50 rounded-xl cursor-pointer z-10"></div>
										{/if}
										<div class="flex-1 truncate">
											<div class="flex flex-1 gap-2 items-center">
												<div class="shrink-0">
													{#if tools?.[toolId]?.meta?.icon}
														<img
															src={tools[toolId].meta.icon}
															alt={tools[toolId].name}
															class="size-4 object-contain rounded-xs"
														/>
													{:else}
														<Wrench />
													{/if}
												</div>
												<div class=" truncate">
													{resolveLocalizedResource(tools?.[toolId], $i18n.language, 'name')}
												</div>
											</div>
										</div>

										{#if tools?.[toolId]?.authenticated === true && toolId.startsWith('server:mcp:')}
											<div class="shrink-0 z-20">
												<Tooltip content={$i18n.t('Disconnect OAuth')}>
													<button
														class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
														type="button"
														on:click={async (e) => {
															e.stopPropagation();
															e.preventDefault();

															const parts = toolId.split(':');
															const serverId = parts.at(-1) ?? toolId;
															const provider = `mcp:${serverId}`;

															try {
																await deleteOAuthSession(localStorage.token, provider);
																toast.success($i18n.t('OAuth session disconnected'));

																// Refresh tools to update authenticated state
																_tools.set(await getTools(localStorage.token));
																selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
																await init();
															} catch (err) {
																toast.error(err ?? $i18n.t('Failed to disconnect'));
															}
														}}
													>
														<LinkSlash className="size-3.5" />
													</button>
												</Tooltip>
											</div>
										{/if}

										{#if tools?.[toolId]?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
											<div class="shrink-0 z-20">
												<Tooltip content={$i18n.t('Valves')}>
													<button
														class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
														type="button"
														on:click={(e) => {
															e.stopPropagation();
															e.preventDefault();
															onShowValves(toolId);
														}}
													>
														<Knobs />
													</button>
												</Tooltip>
											</div>
										{/if}

										<div class=" shrink-0 z-20" inert>
											{#if !(tools?.[toolId]?.authenticated ?? true)}
												<div class="text-xs text-gray-500 font-medium">{$i18n.t('Auth')}</div>
											{:else}
												<Switch state={selectedToolIds.includes(toolId)} />
											{/if}
										</div>
									</button>
								{/each}
							</div>
						{/if}
						
						{#if skills && Object.keys(skills).length > 0}
							<hr class="border-gray-50 dark:border-gray-800 my-1" />
							<div class="flex flex-col gap-0.5">
								{#each skillIds as skillId}
									<button
										class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
										aria-pressed={selectedSkillIds.includes(skillId)}
										on:click={async () => {
											await toggleSkill(skillId);
										}}
									>
										<div class="flex-1 truncate">
											<div class="flex flex-1 gap-2 items-center">
												<Tooltip
													content={resolveLocalizedResource(
														skills?.[skillId],
														$i18n.language,
														'name'
													)}
													placement="top"
												>
													<div class="shrink-0">
														{#if skills?.[skillId]?.meta?.icon}
															<img
																src={skills[skillId].meta.icon}
																alt={skills[skillId].name}
																class="size-4 object-contain rounded-xs"
															/>
														{:else}
															<Cube className="size-4" strokeWidth="1.75" />
														{/if}
													</div>
												</Tooltip>

												<Tooltip
													content={resolveLocalizedResource(
														skills?.[skillId],
														$i18n.language,
														'description'
													)}
													placement="top-start"
												>
													<div class="truncate">
														{resolveLocalizedResource(skills?.[skillId], $i18n.language, 'name')}
													</div>
												</Tooltip>
											</div>
										</div>

										<div class="shrink-0 text-xs text-gray-500">
											{skillSourceLabel(skills?.[skillId])}
										</div>
										{#if skills?.[skillId]?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
											<div class="shrink-0">
												<Tooltip content={$i18n.t('Valves')}>
													<button
														class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
														type="button"
														on:click={(e) => {
															e.stopPropagation();
															e.preventDefault();
															onShowValves(skillId);
														}}
													>
														<Knobs />
													</button>
												</Tooltip>
											</div>
										{/if}

										<div class="shrink-0" inert>
											<Switch state={selectedSkillIds.includes(skillId)} />
										</div>
									</button>
								{/each}
							</div>
						{/if}
"""

content = button_regex.sub(tools_block, content)
content = re.sub(r'\{:else if tab === \'tools\' \&\& tools\}.*?\{\/if\}', '{/if}', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
