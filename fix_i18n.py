import re

def to_title_case(key_part):
    s = re.sub('([a-z])([A-Z])', r'\1 \2', key_part)
    s = s.replace('Api ', 'API ')
    s = s.replace('Openai', 'OpenAI')
    s = s.replace('Gemini', 'Gemini')
    s = s.replace('Comfyui', 'ComfyUI')
    return s.title().replace('Api', 'API').replace('Openai', 'OpenAI').replace('Comfyui', 'ComfyUI')

with open('src/lib/components/admin/Settings/Video.svelte', 'r', encoding='utf-8') as f:
    text = f.read()

def replacer(match):
    full_key = match.group(1)
    parts = full_key.split('.')
    if 'sections' in parts:
        word = parts[1] # e.g. createVideo
    else:
        word = parts[0] # e.g. videoGenerationEngine
    
    english_text = to_title_case(word)
    if word == 'title' and len(parts) == 1:
        english_text = 'Video Generation Settings'
    return f"'{english_text}'"

new_text = re.sub(r"'settings\.admin\.videos\.([^']+)'", replacer, text)

with open('src/lib/components/admin/Settings/Video.svelte', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Done replacing.')
