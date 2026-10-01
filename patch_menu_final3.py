with open(r"S:\open-web-ui-updated\src\lib\components\chat\MessageInput\IntegrationsMenu.svelte", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

tools_loop = lines[574:709] # 575 to 709 (inclusive of {/if} at index 708)
skills_loop = lines[733:786] # 734 to 786 (inclusive of {/if} at index 785)

tools_loop = ["\t\t\t\t\t\t" + line.strip() for line in tools_loop]
skills_loop = ["\t\t\t\t\t\t" + line.strip() for line in skills_loop]

new_block = [
    "\t\t\t\t\t{#if tools}",
    "\t\t\t\t\t\t<hr class=\"my-1 border-gray-200 dark:border-gray-800\" />",
    "\t\t\t\t\t\t<div class=\"px-2 py-1 text-xs text-gray-500 font-semibold\">{$i18n.t('Tools')}</div>"
] + tools_loop + [
    "\t\t\t\t\t\t<hr class=\"my-1 border-gray-200 dark:border-gray-800\" />",
    "\t\t\t\t\t\t<div class=\"px-2 py-1 text-xs text-gray-500 font-semibold\">{$i18n.t('Skills')}</div>"
] + skills_loop + [
    "\t\t\t\t\t{:else}",
    "\t\t\t\t\t\t<div class=\"py-4\">",
    "\t\t\t\t\t\t\t<Spinner />",
    "\t\t\t\t\t\t</div>",
    "\t\t\t\t\t{/if}"
]

new_lines = lines[:343] + new_block + lines[392:552] + lines[789:]

with open(r"S:\open-web-ui-updated\src\lib\components\chat\MessageInput\IntegrationsMenu.svelte", "w", encoding="utf-8") as f:
    f.write("\n".join(new_lines) + "\n")
print("Done!")
