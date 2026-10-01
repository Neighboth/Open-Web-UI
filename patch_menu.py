import re

with open(r"S:\open-web-ui-updated\src\lib\components\chat\MessageInput\IntegrationsMenu.svelte", "r", encoding="utf-8") as f:
    content = f.read()

# I want to extract the tools loop logic from tab == 'tools' and skills loop logic from tab == 'skills'
tools_loop_match = re.search(r'\{#if toolIds\.length === 0\}(.*?)\{/if\}[\s\n]*</div>[\s\n]*</div>', content.split("{:else if tab === 'tools'")[1], re.DOTALL)
if tools_loop_match:
    tools_loop = "{#if toolIds.length === 0}" + tools_loop_match.group(1) + "{/if}"
else:
    print("Failed to find tools loop")
    exit(1)

skills_loop_match = re.search(r'\{#if skillIds\.length === 0\}(.*?)\{/if\}[\s\n]*</div>[\s\n]*</div>', content.split("{:else if tab === 'skills'")[1], re.DOTALL)
if skills_loop_match:
    skills_loop = "{#if skillIds.length === 0}" + skills_loop_match.group(1) + "{/if}"
else:
    print("Failed to find skills loop")
    exit(1)

# Now find the tab == '' block and replace the buttons with the loops
tab_main_match = re.search(r'\{#if tab === \'\'\}(.*?)\{:else if tab === \'tools\'', content, re.DOTALL)
if tab_main_match:
    tab_main = tab_main_match.group(1)
    
    # In tab_main, replace the whole `{#if tools}` block
    tab_main = re.sub(r'\{#if tools\}.*?\{/if\}', '{#if tools}\n<hr class="my-1 border-gray-200 dark:border-gray-800" />\n<div class="px-2 py-1 text-xs text-gray-500 font-semibold">' + "{$i18n.t('Tools')}" + '</div>\n' + tools_loop + '\n{/if}', tab_main, flags=re.DOTALL)
    
    # In tab_main, replace the whole `{#if skills}` block
    tab_main = re.sub(r'\{#if skills\}.*?\{/if\}', '{#if skills}\n<hr class="my-1 border-gray-200 dark:border-gray-800" />\n<div class="px-2 py-1 text-xs text-gray-500 font-semibold">' + "{$i18n.t('Skills')}" + '</div>\n' + skills_loop + '\n{/if}', tab_main, flags=re.DOTALL)
    
    # We replace the whole tab matching
    content = re.sub(r'\{#if tab === \'\'\}.*?\{:else if tab === \'tools\'', '{#if tab === \'\'}' + tab_main + '{:else if tab === \'tools\'', content, flags=re.DOTALL)
else:
    print("Failed to find tab == ''")
    exit(1)

with open(r"S:\open-web-ui-updated\src\lib\components\chat\MessageInput\IntegrationsMenu.svelte", "w", encoding="utf-8") as f:
    f.write(content)
print("Successfully replaced loops!")
