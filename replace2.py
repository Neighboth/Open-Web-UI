import re

file_path = 'src/lib/components/chat/Chat.svelte'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add LiveAgentPreview import
content = content.replace("import Messages from './Messages.svelte';", "import Messages from './Messages.svelte';\n\timport LiveAgentPreview from './LiveAgentPreview.svelte';")

# Add agentLiveUrl import
content = content.replace("import {\n\tchatId,", "import {\n\tagentLiveUrl,\n\tchatId,")

# Event parsing
content = content.replace("} else if (type === 'context_compaction') {", "} else if (type === 'live_agent_preview') {\n\t\t\t\t\t\tagentLiveUrl.set(data?.url ?? null);\n\t\t\t\t\t} else if (type === 'context_compaction') {")

# UI Placement: 
# Find the end of ChatControls which looks like this:
# 						{codeInterpreterEnabled}
# 					/>
# 				{/if}
# 			</div>
# 		</div>
# 	{:else if loading}

replacement = """						{codeInterpreterEnabled}
					/>
				{/if}
			</div>
			<LiveAgentPreview />
		</div>
	{:else if loading}"""

content = content.replace("""						{codeInterpreterEnabled}
					/>
				{/if}
			</div>
		</div>
	{:else if loading}""", replacement)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
