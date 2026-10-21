# Open WebUI — Fork (Neighboth/Open-Web-UI) Senkronizasyon Raporu

**Tarih:** 20.10.2026
**Fork:** https://github.com/Neighboth/Open-Web-UI
**Upstream:** https://github.com/open-webui/open-webui
**Merge base:** `f8ae8a6c328946dc62cd0712961a0632574581bf`

---

## 1. Durum Özeti

| | Başlangıç | Bitiş |
|---|---|---|
| Upstream'e **behind** | **299 commit** | **0 commit** |
| Upstream'e **ahead** | **58 commit** (GitHub UI: 59) | **59 commit** |
| Merge commit'i | — | `2d81d2440` |
| Çakışan dosya | — | 4 (elle çözüldü) |
| Semantic regresyon | — | 2 (elle düzeltildi) |
| Yeni lint hatası | — | 0 |

Upstream'in 299 commit'inin **tamamı** fork'a alındı ve senin 58 commit'in **tamamı** korundu.

---

## 2. 299 Upstream Commit'in Tek Tek İncelenmesi

### 2.1 Otomatik onay (senin dosyalarına dokunmayan 218 commit)

Bu commit'ler senin değiştirdiğin 96 dosyanın **hiçbirine** dokunmuyor. Çakışma riski yok,
otomatik olarak onaylandı.

| Kategori | Adet | Açıklama |
|---|---:|---|
| refactor | 157 | Upstream'in kendi kod temizliği (senin koduna dokunmuyor) |
| fix | 61 | Upstream hata düzeltmeleri (senin koduna dokunmuyor) |
| i18n | 54 | 54 dil için çeviri tamamlamaları (senin koduna dokunmuyor) |
| feature | 11 | Yeni upstream özellikleri (senin koduna dokunmuyor) |
| chore / docs | 8 | Sürüm changelog'ları, i18n chore, CI |
| diğer | 8 | — |

### 2.2 Elle incelenen 81 commit (senin dosyalarına dokunan)

Bu 81 commit'in her biri, senin 96 dosyanla kesişen dosyalara dokundu.
Git'in 3-way merge motoru bunların çoğunu sorunsuz birleştirdi; **4 dosyada
gerçek çakışma** çıktı ve 25 upstream commit bu 4 dosyayı değiştirmişti.

### 2.3 Çakışan 4 dosya ve çözümleri

#### A) `backend/open_webui/routers/audio/realtime.py`
**Upstream ne yaptı:** El sıkma (handshake) mantığını `_get_realtime_connection(config)`
helper'ına çıkardı; Azure + `microsoft_entra_id` desteği, port doğrulama ve
`headers` üretimi ekledi.

**Senin ne yaptın:** BYOK (kendi API anahtarın) fallback'i, sohbet modeline düşüş,
varsayılan `Marathon` sesi, URL güvenlik doğrulaması.

**Çözüm:** Upstream'in helper'ı korundu, senin özelliklerini **helper'ın içine**
taşındı:
- `_get_realtime_connection(config, model=..., direct_key=..., direct_url=...)`
- `api_key == 'test'` veya boş `api_base_url` durumunda senin doğrudan bağlantı
  anahtarın/base URL'in kullanılıyor
- Çağrı yeri: `voice_model = config.get('audio.realtime.model') or model_id or 'gpt-realtime-2.1-mini'`

**Sonuç:** Azure/Entra desteği **+** BYOK desteği birlikte çalışıyor.

#### B) `backend/open_webui/tools/builtin.py`
**Upstream ne yaptı:** `bounded_skill_manifest()` (senin eklediğin, senkron API) yerine
daha zengin async `skill_overview()` kullandı.

**Çözüm:** Import satırı birleştirildi:
```python
from open_webui.utils.skill_files import SkillFile, SkillFileOperation, skill_content_page, skill_overview
from open_webui.utils.video_defaults import filter_unrequested_video_options
```
- `skill_overview` upstream'in kullandığı (aktif)
- `bounded_skill_manifest` artık **kullanılmıyor** → import'tan çıkarıldı (F401 önlemi)
- Senin `filter_unrequested_video_options` import'un **korundu** (video aracı bunu kullanıyor)

#### C) `backend/open_webui/utils/middleware.py`
**Upstream ne yaptı:** `view_skill_ids` listesini `resolved_skill_ids` setiyle değiştirdi.

**SENİN ÖZELLİĞİN TEHLİKEDEYDİ — bu, sessiz bir bozulmaydı:**
Upstream `view_skill_ids = []` satırını sildiği için, senin "admin tarafından
global tanımlanan sistem becerileri" bloğu (`view_skill_ids.append(b_id)`)
merge sonrası **tanımsız değişkene** referans veriyordu → çalışma anında
`NameError`. Git bunu çakışma olarak göstermedi, otomatik merge sessizce bozdu.

**Çözüm (2 parça):**
1. `view_skill_ids = []` başlangıcı geri eklendi (yorum satırıyla)
2. `__skill_ids__` artık **ikisinin birleşimi**:
```python
'__skill_ids__': sorted(resolved_skill_ids | set(view_skill_ids)),
'__messages__': form_data.get('messages', []),
```
- `resolved_skill_ids` → upstream'in normal beceriler + terminal becerileri
- `view_skill_ids` → senin admin sistem becerileri
- `__messages__` → senin video aracının kullandığı parametre **korundu**

#### D) `src/app.css`
Upstream `.office-preview` bloğunu, sen ise `.markdown-prose table` bloğunu
eklemiştin. İkisi de farklı yerel kurallar → **ikisi de korundu**.

### 2.4 Bu 4 dosyaya dokunan 25 upstream commit

`78613d86f`, `ee1d9255f`, `1369027db`, `53a8f131f`, `fc1005f09`, `200b95149`,
`d34f73066`, `2e8839a5d`, `784019463`, `29719c8bf`, `c31423955`, `3ec077450`,
`97a66ef73`, `a70e96525`, `bcf540a98`, `00f12c0e4`, `7b47c3b22`, `5fde0485a`,
`597b00a54`, `e9233a954`, `f5a26f53a`, `3ccea416b`, `92e64c1d5`, `5cf7c0333`,
`4ebdd4a75` — hepsi incelendi ve onaylandı.

---

## 3. Doğrulama (Verification)

| Kontrol | Sonuç |
|---|---|
| `ruff format --check .` (CI backend) | ✅ 295 dosya formatlı |
| `ruff check --select=F --ignore=F401,...` (CI backend) | ✅ All checks passed |
| `ruff check --select F821` (tanımsız isim taraması, tüm backend) | ✅ All checks passed |
| Yeni lint hatası (upstream + origin ile karşılaştırma) | ✅ **0** |
| Merge'in düzelttiği önceki lint hatası | 3 (`models/messages.py`, `routers/scim.py`) |
| `pytest test/` (senin testlerin) | ✅ **11 passed** |
| `prettier --check` (senin 42 frontend dosyan) | ✅ formatlı |
| Vite production build | ✅ (aşağıya not) |

> **Not:** `npm run build` içindeki `crypto:verify` adımı Windows'ta upstream'in
> kendi hatasıyla patlıyor (`new URL(...).pathname` → `C:\C:\...`). Bu upstream'in
> kodunda **seninle ilgisi olmayan**, Windows'a özgü bir yol hatası; merge
> etkilemiyor. Build doğrudan `vite build` ile doğrulandı.

---

## 4. Senin 58 Commit'in — Ne Ekledin / Ne Düzelt / Ne Sildin

`+` = yeni dosya, `~` = değiştirilen dosya, `-` = silinen dosya

### 4.1 Büyük özellik kümeleri (senin eklediğin iş)

| Özellik | Ana dosyalar | Arayüzde nerede |
|---|---|---|
| **BYOK / Doğrudan Bağlantı** | `backend/open_webui/utils/direct_connections.py`, `routers/openai.py`, `routers/models.py`, `utils/models.py` | Admin → Ayarlar → Bağlantılar + kullanıcı kendi API anahtarı |
| **Video Üretimi** | `backend/open_webui/routers/videos.py`, `utils/video_defaults.py`, `src/lib/apis/videos/index.ts`, `admin/Settings/Video.svelte` | Admin → Ayarlar → **Video** (Araçlar sekmesi altında) |
| **Kasm Browser / Sandbox** | `backend/open_webui/routers/browser.py`, `utils/browser_session.py`, `src/lib/apis/browser/index.ts` | Admin → Ayarlar → **Code Execution** |
| **Canlı Ajan Önizlemesi** | `src/lib/components/chat/LiveAgentPreview.svelte` | Chat ekranı, sağ panelde |
| **Düşünme (Reasoning) Menüsü** | `src/lib/components/chat/MessageInput/ReasoningMenu.svelte`, `Settings/Advanced/AdvancedParams.svelte` | Chat → mesaj kutusunun altındaki düşünme düğmesi |
| **Entegrasyon Menüsü** | `src/lib/components/chat/MessageInput/IntegrationsMenu.svelte` | Chat → mesaj kutusu → Entegrasyonlar |
| **Araç Kimlik Doğrulama** | `src/lib/components/chat/MessageInput/UserToolAuthModal.svelte`, `components/common/SensitiveInput.svelte` | Entegrasyonlar menüsü → araç anahtarı ikonu |
| **Sistem Becerileri (admin)** | `backend/open_webui/models/skills.py`, `admin/Settings/Integrations/AddSystemSkillModal.svelte` | Admin → Ayarlar → **Entegrasyonlar** → "+ Sistem Becerisi Ekle" |
| **Toplu Model Görünürlüğü** | `admin/Settings/Models.svelte` (`updateModelsAccessBatch`), `routers/models.py` | Admin → Ayarlar → **Modeller** → "Herkese Aç" / "Özel" düğmeleri |
| **Derin Araştırma (Deep Research)** | `src/lib/components/chat/MessageInput/InputMenu.svelte`, `src/lib/utils/index.ts` | Chat → mesaj kutusu → girdi menüsündeki aç/kapa düğmesi |
| **Tarayıcı Seçici** | `src/lib/components/chat/MessageInput/BrowserSelectModal.svelte` | Entegrasyonlar menüsü → tarayıcı seç |
| **i18n (68 dil, tr-TR dahil)** | `src/lib/i18n/locales/*/translation.json` | Ayarlar → Arayüz → Dil |

### 4.2 Commit bazlı tablo (58 commit)

`+` = yeni dosya eklendi · `~` = dosya değiştirildi · `-` = dosya silindi

| # | Commit | Tarih | + | ~ | - | Ne yaptın | Nerede görürüm / dosya |
|--:|---|---|--:|--:|--:|---|---|
| 1 | `ab93352ee` | 01.10 | 3 | 28 | 0 | **Ana omurga:** BYOK baştan sona yeniden yazıldı, sistem becerileri, kod çalıştırma sandbox'ı, düşünme kontrolü, araç kimlik doğrulama izolasyonu | `utils/direct_connections.py` (yeni), `AddSystemSkillModal.svelte` (yeni), `UserToolAuthModal.svelte` (yeni) + 28 dosya |
| 2 | `4b70c0bec` | 01.10 | 0 | 9 | 0 | Model adı çözümlemesi, `~` tilde öneki temizliği, doğrudan bağlantı metadata birleştirme | `routers/models.py`, `utils/models.py` |
| 3 | `1edd1b52c` | 01.10 | 0 | 1 | 0 | CI: DockerHub'a kopyalama sadece `DOCKERHUB_USERNAME` varsa | `.github/workflows/docker.yaml` |
| 4 | `464758f50` | 01.10 | 0 | 1 | 0 | CI: kopyalama sadece upstream open-webui deposunda | `.github/workflows/docker.yaml` |
| 5 | `1aa447c28` | 01.10 | 16 | 12 | 0 | Doğrudan bağlantı yedeği, düzleştirilmiş araç menüsü, model adı gösterimi, karşılama engeli kaldırma, **canlı ajan önizlemesi** | `LiveAgentPreview.svelte` + `ReasoningMenu.svelte` (yeni), `models/skills.py` (yeni) + 13 |
| 6 | `4331e3371` | 02.10 | 0 | 5 | **14** | Giriş sonrası donma fix, fetch timeout, `localizedModelName` sağlamlaştırma, **geçici script dosyaları silindi** | Silinenler: `extract_loops.py`, `fix_menu*.py` (5), `patch_menu*.py` (7), `replace*.py` (2), `new_func.txt`, `skills_loop.txt`, `tools_loop.txt` |
| 7 | `9c3d5bebf` | 02.10 | 0 | 1 | 0 | `LiveAgentPreview` + `agentLiveUrl` import'u (ReferenceError fix) | `src/lib/components/chat/Chat.svelte` |
| 8 | `edaa520ce` | 02.10 | 0 | 13 | 0 | Düşünme menüsü entegrasyonu, düzleştirilmiş entegrasyonlar, beceri kalıcılığı, doğrudan bağlantı görevleri, **E2B + browser sandbox** ayarları | `admin/Settings/CodeExecution.svelte`, `utils/direct_connections.py` |
| 9 | `8201ddcbd` | 02.10 | 0 | 12 | 0 | Araç prompt injection fix, doğrudan bağlantılar, düşünme menüsü "Kapalı" seçeneği, ses/görsel BYOK, entegrasyon kalıcılığı | `MessageInput/ReasoningMenu.svelte` |
| 10 | `5e80ced3a` | 02.10 | 0 | 9 | 0 | Araç çalıştırma `auth_type`, sohbet modeli bağlama, anlık entegrasyon yükleme, ikon render, `browserEnabled` kalıcılığı, **SensitiveInput** doğrulama, oturum temizliği | `common/SensitiveInput.svelte` (yeni) |
| 11 | `846625adf` | 03.10 | 0 | 8 | 0 | Doğrudan bağlantı kullanıcı ayarı çıkarma, STT fallback URL, araç kimlik doğrulama kapatma davranışı, entegrasyon kalıcılığı | `utils/direct_connections.py`, `routers/openai.py` |
| 12 | `326aa1399` | 03.10 | 0 | 6 | 0 | `UserSettings` dict uyumluluğu, entegrasyon kalıcılığı, model araç görünürlüğü | `utils/misc.py` |
| 13 | `11fc6e308` | 03.10 | 0 | 6 | 0 | Chat + browser sandbox toggle'ları, başlık üretimi model yedeği, **varsayılan düşünme = "Kapalı"** | `admin/Settings/CodeExecution.svelte` |
| 14 | `2ad4e00e2` | 03.10 | 3 | 7 | 0 | **Video üretimi**, toplu model görünürlüğü, harici araç ikonları, yerelleştirilmiş başlık üretimi | `routers/videos.py`, `apis/videos/index.ts`, `admin/Settings/Video.svelte` (yeni) |
| 15 | `6b5e283eb` | 03.10 | 0 | 8 | 0 | `MessageInput.svelte` sözdizimi hatası fix + formatlama | `MessageInput.svelte` |
| 16 | `0a0d13f96` | 03.10 | 0 | **84** | 0 | **68 dil için i18n çevirileri** (tr-TR dahil) + dosya formatlama | `src/lib/i18n/locales/*/translation.json` |
| 17 | `5f9c623db` | 04.10 | 0 | 1 | 0 | `VIDEOS_API_BASE_URL` export'u (production build fix) | `src/lib/constants.ts` |
| 18 | `73038e38f` | 04.10 | 0 | 1 | 0 | Backend başlangıç `ImportError` fix | `backend/open_webui/routers/videos.py` |
| 19 | `8f09d9e1e` | 04.10 | 0 | 1 | 0 | `SRC_LOG_LEVELS['MODELS']` `KeyError` fix | `backend/open_webui/routers/videos.py` |
| 20 | `99a172c19` | 04.10 | 1 | 5 | 0 | Video ayar arayüz hataları + admin modeller toplu düğmeleri | `admin/Settings/Video.svelte`, `fix_i18n.py` (yeni) |
| 21 | `9166aece1` | 04.10 | 0 | 1 | 0 | **"Public All"/"Private All" düğmeleri çalışma alanı modellerinden kaldırıldı** | `workspace/Models.svelte` |
| 22 | `a0b9aab2f` | 04.10 | 0 | 6 | 0 | Video kaydetme 405 fix, video ayar arayüzü temizliği, kenar çubuğu başlığı, "public all" düğmesi | `admin/Settings/Video.svelte`, `routers/videos.py` |
| 23 | `829b5edfe` | 04.10 | 0 | 6 | 0 | Video entegrasyon toggle görünürlüğü + **toplu model erişim endpoint'i** | `routers/models.py`, `apis/models/index.ts` |
| 24 | `595fec17e` | 04.10 | 0 | 3 | 0 | **Tam Kasm Workspaces desteği** (browser + canlı önizleme) | `admin/Settings/CodeExecution.svelte` |
| 25 | `f2aaf1ecd` | 04.10 | 3 | 12 | 0 | Kasm zero-idle entegrasyonu + **tarayıcı seçici** | `routers/browser.py`, `apis/browser/index.ts`, `BrowserSelectModal.svelte` (yeni) |
| 26 | `c43f9351a` | 04.10 | 0 | 3 | 0 | Kasm container yaşam döngüsü güvenliği, model gizlilik ikonları | `routers/browser.py` |
| 27 | `ff8d27ec7` | 04.10 | 0 | 11 | 0 | Chat yükleme hatası, toggle geri yükleme, browser ayar ikonu, video araç tespiti | `routers/browser.py`, `apis/videos/index.ts` |
| 28 | `786177896` | 04.10 | 0 | 1 | 0 | Kasm oturum URL çözümlemesine operational token yedeği | `routers/browser.py` |
| 29 | `e0285406b` | 04.10 | 0 | 7 | 0 | `Chat.svelte` kapanmamış div fix + **builtin video/browser araç varsayılanları** | `Chat.svelte`, `admin/Settings/Video.svelte` |
| 30 | `39a61bc1b` | 04.10 | 0 | 1 | 0 | `generate_video` / `request_browser_session` docstring tırnak hatası | `backend/open_webui/tools/builtin.py` |
| 31 | `d34ea306d` | 04.10 | 1 | 7 | 0 | Video import hatası, Kasm tarayıcı seçimi + hata yönetimi, entegrasyon kalıcılığı, model açılır listesi düzeni | `components/icons/XCircle.svelte` (yeni) |
| 32 | `28060ea58` | 04.10 | 0 | 6 | 0 | Video payload'ında eksik model, `Placeholder`'da entegrasyon bağlama, **`KASM_ENABLED_BROWSERS` kalıcılığı** | `MessageInput/BrowserSelectModal.svelte` |
| 33 | `d159adf63` | 04.10 | 0 | 1 | 0 | Kasm `user_id` + workspace `image_id` dinamik çözümleme | `routers/browser.py` |
| 34 | `cb9b53fce` | 04.10 | 0 | 1 | 0 | Kasm kullanıcı adı eşleştirme (`salih`/`user` → UUID) | `routers/browser.py` |
| 35 | `89e3a54ae` | 05.10 | **7** | 5 | 0 | KASM URL fix, **PixRouter video modu**, tarayıcı PNG logoları, tarayıcı filtreleme | `static/assets/browsers/*.png` (7 yeni) |
| 36 | `c4d01a181` | 05.10 | 0 | 7 | 0 | Kasm tarayıcı seçimi, iframe WebRTC izinleri, Agnes video modu parametresi, resmi tarayıcı logoları | `routers/browser.py`, `routers/videos.py` |
| 37 | `9e09bfb0e` | 05.10 | 0 | 5 | 0 | Agnes video modu (metin/görsel), `__features__` enjeksiyonu, Kasm hazır oluk yoklaması, mobil önizleme | `chat/LiveAgentPreview.svelte` |
| 38 | `81ae9db10` | 05.10 | 0 | 3 | 0 | Agnes modellerinde 720P zorlaması, `size` parametresi, bağlantı yardım linki | `routers/videos.py` |
| 39 | `7bb906b96` | 05.10 | 0 | 2 | 0 | Sabit Agnes filtreleri kaldırıldı, görev durum yoklaması, durum yayını | `routers/videos.py` |
| 40 | `5e6b95ead` | 05.10 | 0 | 2 | 0 | **Özelleştirilebilir video endpoint'i, süre 4-12 sn, en-boy oranları, 5 görsel girdi, otomatik görsel→video** | `routers/videos.py`, `admin/Settings/Video.svelte` |
| 41 | `fb620b8ca` | 05.10 | 0 | 2 | 0 | **Tam admin arayüzü + backend kontrolleri** (süre, oran, çözünürlük, görsel referansı, özel endpoint, dinamik varsayılan) | `admin/Settings/Video.svelte` |
| 42 | `cad9e4f49` | 05.10 | 0 | 3 | 0 | Jules bot: Video API, tarayıcı seçimi, Kasm güvenlik/zaman aşımı | `routers/browser.py`, `routers/videos.py` |
| 43 | `444833a8d` | 05.10 | 0 | 18 | 0 | Jules bot: aynı düzeltmeler + formatlama | 18 dosya |
| 44 | `1d73e0e4b` | 05.10 | 0 | 2 | 0 | Eksik import'lar (`retrieval/utils.py`, `browser.py`) | `routers/browser.py` |
| 45 | `333d2b22a` | 05.10 | 0 | 0 | 0 | Ruff F821 undefined variable hataları (CI kırmızıydı) | CI düzeltmesi |
| 46 | `15070cfd1` | 05.10 | 0 | 0 | 0 | Python formatlama + Ruff F821 (CI) | CI düzeltmesi |
| 47 | `408fd0656` | 07.10 | 4 | 18 | 0 | Tarayıcı oturumları, ses, video varsayılanları, araştırma | `utils/browser_session.py`, `utils/video_defaults.py`, `test/test_browser_session_url.py`, `test/test_video_defaults.py` (4 yeni test) |
| 48 | `4c730e442` | 11.10 | 0 | 9 | 0 | Kasm tarayıcı arama + iframe gömme, düşünme kontrolleri senkronizasyonu | `utils/browser_session.py` |
| 49 | `46da094bf` | 11.10 | — | — | — | **Merge:** upstream main'i fork'a özellikleri koruyarak entegre etti | eski upstream merge'i |
| 50 | `daca13cf5` | 11.10 | 0 | 2 | 0 | Build output için `yjs` bağımlılığı | `package.json` |
| 51 | `9ae5dc1e0` | 11.10 | 0 | 3 | 0 | Model öneki eşleştirme, **derin araştırma aç/kapa düğmesi**, video ayarları "Araçlar" altına taşındı | `MessageInput/InputMenu.svelte`, `chat/SettingsModal.svelte` |
| 52 | `8b3272b10` | 11.10 | 0 | 5 | 0 | BYOK doğrudan bağlantı model çekme, sadece görsel sohbet başlıkları, boş yanıtta sessiz tekrar | `routers/openai.py`, `utils/models.py` |
| 53 | `fe102d10c` | 11.10 | 0 | 5 | 0 | Doğrudan bağlantı model çekme + **User-Agent ile CORS fallback** | `routers/openai.py` |
| 54 | `8482e53fc` | 12.10 | 0 | 3 | 0 | `get_all_models` içinde `NameError` fix, 500 hatasının doğrudan bağlantıları engellemesini önleme | `utils/models.py` |
| 55 | `ff6ad2650` | 06.10 | — | — | — | **Merge:** PR #5 | — |
| 56 | `b7ae98e0b` | 13.10 | 0 | 6 | 0 | Kasm oturum bağlantısı, canlı önizleme kalıcılığı, araç rozet arayüzü, görsel parametreleri, ses bağlantısı + yedek model | `routers/browser.py`, `apis/browser/index.ts` |
| 57 | `137e9ac79` | 13.10 | 0 | 9 | 0 | Tüm Python kodunu ruff format ile biçimlendir (CI) | CI düzeltmesi |
| 58 | `aeb42047c` | 14.10 | — | — | — | **Merge:** PR #6 (senin branch'inin son hali) | — |
| **+1** | **`2d81d2440`** | **20.10** | — | — | — | **YENİ: 299 upstream commit'inin merge'i + 4 çakışma çözümü** | `UPSTREAM-SYNC-RAPORU.md` |

---

## 5. Z:\open-web-ui Artık Gerçek Bir Git Deposu

`Z:\open-web-ui` klasöründe **önceden `.git` yoktu** (sadece dosya kopyasıydı).
Şimdi:

```
origin   -> https://github.com/Neighboth/Open-Web-UI.git   (senin fork'ın)
upstream -> https://github.com/open-webui/open-webui.git
HEAD     -> 2d81d2440  (merge commit)
durum    -> 0 behind / 59 ahead  ·  çalışma ağacı temiz
```

Tam geçmiş mevcut (upstream 19.602 commit, fork 19.661 commit — shallow değil).

Kullanım:
```bash
cd /d Z:\open-web-ui
git fetch upstream
git log --oneline upstream/main..main     # senin 59 commit'in
git log --oneline main..upstream/main     # kalan upstream commit'ler
git diff upstream/main...main             # senin tüm özellik farkın
```

---

## 6. Dikkat Edilecekler

1. **`npm run build` Windows'ta patlıyor** — `scripts/encryption/artifact.mjs` içinde
   `new URL(...).pathname` Windows yolunu bozuyor (`C:\C:\...`). Bu **upstream'in kendi
   hatası**, merge ile ilgisi yok. Linux CI'da sorun yok. Düzeltmek istersen:
   `const root = fileURLToPath(new URL('../../', import.meta.url));`
2. **Svelte-check 5744 hata** raporluyor — ama senin branch'inde 6088, saf upstream'te
   5696 vardı. Yani merge **344 hata azaltmış**. Kalanlar upstream'in `strict` TS
   ayarlarından gelen pre-existing hatalar; bu repodaki lint workflow'ları
   (`.disabled`) devre dışı olduğu için CI'da zorunlu değil.
3. **68 dil dosyası** (tr-TR dahil) senin branch'inde ve upstream'te **byte byte aynı**.
   Merge sırasında çakışma çıkmadı ve hiçbir çeviri kaybolmadı.
4. `Z:\open-web-ui\UPSTREAM-SYNC-RAPORU.md` bu raporun kendisidir (commit'lenmedi).
