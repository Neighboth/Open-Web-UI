with open(r"S:\open-web-ui-updated\src\lib\components\chat\MessageInput\IntegrationsMenu.svelte", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

# find index of </DropdownMenu>
idx = 0
for i, line in enumerate(lines):
    if "</DropdownMenu>" in line:
        idx = i
        break

# insert {/if} before </DropdownMenu>
lines.insert(idx, "\t\t\t{/if}")

with open(r"S:\open-web-ui-updated\src\lib\components\chat\MessageInput\IntegrationsMenu.svelte", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("Done!")
