with open(r"S:\open-web-ui-updated\src\lib\components\chat\MessageInput\IntegrationsMenu.svelte", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()
tools_loop = "\n".join(lines[574:709])
skills_loop = "\n".join(lines[733:787])

with open("tools_loop.txt", "w", encoding="utf-8") as f:
    f.write(tools_loop)

with open("skills_loop.txt", "w", encoding="utf-8") as f:
    f.write(skills_loop)

print("Loops written to text files.")
