# Hata Düzeltme Raporu — 21.10.2026

Repo: `Neighboth/Open-Web-UI` (fork) · Branch: `main` · Upstream: `open-webui/open-webui`

Tüm hatalar **gerçek sağlayıcılara (sağlayıcı / Kasm Workspaces) canlı isteklerle**
tespit edildi ve düzeltildi. Testler: `test/live_provider_check.py` (10/10),
`test/live_realtime_check.py`, `test/test_video_generation_params.py`,
`test/test_browser_session_url.py` → **20/20 pytest geçti**.

---

## 1. Video 400 — "mode is required"

### Kök neden (empirik)
`video_generation.openai.params = {"mode": "text"}` DB'de kayıtlıydı ama
backend **hiç okumuyordu**: `VIDEO_CONFIG_KEYS` içinde `VIDEOS_OPENAI_API_PARAMS`
yoktu. Admin arayüzü alanı gösteriyor ve kaydediyordu, router ise `DEFAULT_CONFIG`
boş değerini kullanıyordu → payload'da `mode` hiç gitmiyordu.

Canlı doğrulama (sağlayıcı):
```
mode YOK  -> HTTP 400 {"code":"invalid_request","message":"mode is required"}
mode=text -> HTTP 503 {"code":"video_queue_full"}   ← istek KABUL EDİLDİ
```

### Düzeltmeler
| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/routers/videos.py` | `VIDEO_CONFIG_KEYS`'e `VIDEOS_OPENAI_API_PARAMS` → `video_generation.openai.params` ve `VIDEO_GENERATION_MODE` → `video_generation.mode` eklendi |
| `backend/open_webui/routers/videos.py` | `params` string olarak saklanmışsa (`'{"mode": "text"}'`) JSON parse ediliyor |
| `backend/open_webui/routers/videos.py` | **Zararlı retry düzeltmesi:** "X is required" hatasında parametre artık **silinmiyor** (önce siliyordu → aynı hata 4 kez tekrarlanıyordu). Sadece "unsupported / not an allowed request field" gibi "desteklenmiyor" hatalarında siliniyor |
| `backend/open_webui/routers/videos.py` | Eksik parametre hatasında admin ayarına yönlendiren mesaj |
| `src/lib/components/admin/Settings/Video.svelte` | "Video Generation Mode" alanı eklendi |
| `src/lib/components/admin/Settings/Video.svelte` | Bozuk JSON'da kaydetmenin sessizce başarısız olması yerine hata gösteriliyor |

**Canlı sonuç:** payload artık `{"model","prompt","size","aspect_ratio","mode":"text"}` →
sağlayıcı **503 video_queue_full** döndürüyor (yani istek kabul edildi, kuyruk dolu).

> Not: sağlayıcı bu modelde `duration` alanını kabul etmiyor
> ("duration is not an allowed request field"). Yeni retry mantığı bu alanı
> otomatik düşürüp tekrar deniyor → istek başarılı oluyor.

---

## 2. Resim 400 — "Model agnes-image-2.5-flash is an image model"

### Kök neden (empirik — 25+ payload varyasyonu denendi)
Sağlayıcının `GET /v1/models` kataloğu modelin hangi endpoint'lerde
sunulduğunu **kendisi** söylüyor:

| Model | `supported_endpoint_types` | Sonuç |
|---|---|---|
| `agnes/agnes-image-2.5-flash` | `["openai"]` → **sadece chat** | 400 |
| `openai/gpt-image-1` | `["image-generation", "openai"]` | 200 ✅ |

Denenen payload'lar (hepsi aynı 400'ü verdi):
`{model,prompt}` · `{model,prompt,n}` · `size` 1K/2K/3K/4K/1024x1024/4096x4096 ·
`ratio` · `extra_body.response_format` · `return_base64` · `mode=text2img` ·
`response_format` b64_json · **sağlayıcının kendi OpenAPI şemasındaki tam şekil**
(`ImageGenRequest`: model/prompt/n/size) · `/chat/completions` + `modalities` ·
`/chat/completions` + `response_format:image` · model adı varyasyonları
(`agnes-image-2.5-flash`, `AgnesAI/...`, `agnesai/...`, `agnes/Agnes-...`)

**Sonuç:** Sağlayıcının Agnes kanalı görsel endpoint'i **sunmuyor**; istek
chat yoluna düşüyor ve Agnes "görsel endpoint'i kullan" diye cevap veriyor.
Bu sağlayıcı tarafındaki kanal yapılandırmasıdır, gönderim biçimi değil.

Çalışan modeller (canlı doğrulandı): `openai/gpt-image-1`, `openai/gpt-image-1.5`,
`openai/gpt-image-2.5`, `openai/gpt-image-2.5-sunburst`, `openai/dall-e-2/3`,
`black-forest-labs/flux-*`

Ayrıca `size=4096x4096` gpt-image-1'de **502** veriyor (geçerli: 1024x1024 / 1536x1024 / 1024x1536).

### Düzeltmeler
| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/routers/images.py` | Sağlayıcının JSON hata mesajı artık `HTTPException.detail` içinde görünüyor (önce `raise_for_status()` → opak 500) |
| `backend/open_webui/routers/images.py` | "Bu model image endpoint'inde sunulmuyor" ipucu eklendi → hangi model seçilmeli yazıyor |
| `backend/open_webui/routers/images.py` | **Provider-agnostic retry:** sağlayıcı "bu alan kabul edilmiyor" derse alan düşürülüp tekrar deniyor (`response_format` / `size` / `n`), boyut reddedilirse `1024x1024` ile tekrar |
| `backend/open_webui/routers/images.py` | `except HTTPException: raise` — sağlayıcı hatası "Something went wrong" ile sarılmıyor |

### Admin panelinde yapılacak
**Ayarlar → Images**:
- `Image Generation Model` → `openai/gpt-image-1` (çalıştığı doğrulandı)
- `Image Size` → `1024x1024` (`4096x4096` 502 veriyor; kod otomatik düşürüyor ama doğrusu budur)

---

## 3. Sesli arama (voice call) — "bağlantı kurulamadı"

### Kök neden (empirik)
Ayarlanan model: `google/gemini-3.1-flash-live-preview`, sağlayıcı: sağlayıcı.

```
wss://<provider-host>/v1/realtime?model=google/gemini-3.1-flash-live-preview
  -> handshake OK, sonra sunucu socket'i ANINDA kapatiyor (ConnectionClosedError)
wss://.../v1/realtime?model=google/gemini-3.8-live
  -> ayni sekil (dene 3 farkli header kombinasyonu + ilk mesaj bicimleri)
wss://.../v1/realtime?model=openai/gpt-realtime        -> HTTP 503 (kanal yok)
wss://.../v1/realtime?model=mistralai/voxtral-mini-realtime-latest
  -> session.created ✅ AMA sadece transkripsiyon (session.type='realtime' reddediliyor)
```

**Sağlayıcının kendi hatası ne diyor?** `/v1/responses` üzerinden Gemini live
modeli denendiğinde upstream şunu döndürüyor:
```
"models/gemini-3.8-live only supports real-time bidirectional streaming via
 WebSocket (bidiGenerateContent). Please use the Gemini Live API
 (bidiGenerateContent via WebSocket) instead of generateContent."
```
Yani Gemini live modelleri **Gemini Live `bidiGenerateContent` WebSocket
protokolü** ile konuşuyor; OpenAI-Realtime köprüsüne çevrilmiyor.

**Sonuç:** sağlayıcı'ın kataloğunda **tam çift yönlü OpenAI-Realtime modeli yok**.
Open WebUI'ın realtime köprüsü OpenAI Realtime protokolü konuşuyor; Gemini Live
modelleri sağlayıcı'da bu protokole çevrilmiyor. Bu **sağlayıcı tarafı bir
kısıttır**, kodla aşılamaz — ama artık teşhisi net.

> Gemini Live desteği istenirse backend köprüsüne ikinci bir protokol adaptörü
> (setup mesajı, farklı olay adları, farklı ses çerçeveleme ve araç çağrısı
> çevirisi) eklenmesi gerekir. Bu ayrı bir özellik işidir.

### Düzeltmeler
| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/routers/audio/realtime.py` | Sağlayıcı handshake sonrası kapatırsa hata mesajı modeli adıyla söylüyor: *"The model X is most likely not served as an OpenAI Realtime model by this endpoint."* |
| `backend/open_webui/routers/audio/realtime.py` | `session.update` reddedilirse sağlayıcının mesajı eklendi (modelin sadece transkripsiyon olduğu ancak böyle anlaşılıyor) |
| `backend/open_webui/routers/audio/realtime.py` | **YENİ:** `POST /api/v1/audio/realtime/verify` — admin için bağlantı doğrulama endpoint'i |
| `src/lib/apis/audio/index.ts` | `verifyRealtimeConnection()` eklendi |
| `src/lib/components/admin/Settings/Audio.svelte` | "Voice Model" yanına kilit ikonlu **doğrula** düğmesi eklendi |

**Canlı doğrulama:**
```
model = google/gemini-3.1-flash-live-preview
  status = False
  error  = The Realtime provider closed the connection before the session started.
           The model "google/gemini-3.1-flash-live-preview" is most likely not
           served as an OpenAI Realtime model by this endpoint.
model = mistralai/voxtral-mini-realtime-latest
  status = True
```

### Admin panelinde yapılacak
- **Ayarlar → Audio → Voice Model**: sağlayıcı üzerinden çalışan tam-duplex
  realtime modeli yok. Seçenekler:
  1. `audio.realtime.openai.api_base_url` = `https://api.openai.com/v1` + kendi
     OpenAI anahtarın, model = `gpt-realtime-2.1-mini` (veya `gpt-realtime-mini`)
  2. sağlayıcı'da kalırsan sesli arama çalışmaz — yeni **doğrula** düğmesiyle
     hangi modelin gerçekten realtime olduğunu anında görürsün.

---

## 4. Kasm iframe — "iframe geliyor, sonra Kasm admin açılıp toast hata veriyor"

### Kök neden (empirik, 2 ayrı hata)

**(a) `is_safe_kasm_connection_url` gerçek Kasm URL'ini reddediyordu.**
Kasm'in döndürdüğü kanonik connect URL'i 5 parçalı:
```
<kasm-host>:8443/#/connect/kasm/{kasm_id}/{user_id}/{session_token}
```
Fonksiyon sadece 4 parçalıyı kabul ediyordu → **aktif oturum "tehlikeli" sayılıp
siliniyor ve konteyner YOK EDİLİYORDU** → iframe'deki Kasm oturumu ölüyor,
Kasm dashboard'a düşüp toast hata veriyordu. "Yeni sekmede aç" ise yeni URL ile
çalıştığı için sorun görünmüyordu.

**(b) Kasm API hatası sessizce yutuluyordu.**
`get_images` çözümlemesi başarısız olunca kod `image_id` yerine **docker image
adı** gönderiyordu (`kasmweb/chrome:1.16.0`) → Kasm "No Default Image Found"
diyordu → kod hata yerine `live_url` = `<kasm-host>:8443/?password=...`
yani **Kasm dashboard'unu** döndürüyordu (`status: True`!). Dashboard iframe'da
toast hatası veriyordu; üstelik Kasm çerezi `SameSite=Lax` olduğu için iframe
içinde gönderilmiyor → login başarısız.

Bu sessiz fallback **iki ayrı yerde** vardı: `request_kasm` hata döndüğünde ve
ağ hatası (`except Exception`) yakalandığında. İkisi de kapatıldı — canlı test
sırasında ikincisi yakalandı.

Doğrulama:
```
image_id = kasmweb/chrome:1.16.0        -> HTTP 500
image_id = kasmweb/chrome:1.19.0        -> HTTP 500
image    = kasmweb/chrome:1.19.0        -> "No Default Image Found"
image_id = d9ef421727814e6bbebe91a023bcc608  -> OK  (gerçek image_id)
```

### Düzeltmeler
| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/utils/browser_session.py` | `is_safe_kasm_connection_url` artık Kasm'in gerçek 5 parçalı connect URL'ini (`kasm_id/user_id/token`) ve eski 4 parçalıyı kabul ediyor |
| `backend/open_webui/routers/browser.py` | `_is_kasm_dashboard_url()` — Kasm dashboard'unu oturum görüntüsü olarak kullanma. Fragment'ı olan bir URL (`/#/connect/...`) dashboard **değildir** |
| `backend/open_webui/routers/browser.py` | Kasm API hatasında **sessiz dashboard fallback'i kaldırıldı** (3 yerde: API hatası, ağ hatası, standalone mod); gerçek hata mesajı döndürülüyor |
| `backend/open_webui/routers/browser.py` | Image çözümlemesi: `friendly_name` tam eşleşme → sonra `friendly_name`/`name`/`docker_image` içinde alt-küme; `get_images` timeout'u 8s → 15s |
| `backend/open_webui/routers/browser.py` | Image çözülemezse `image_id` uydurmak yerine net hata ("No Kasm workspace image matches the browser ...") |

**Canlı doğrulama (gerçek Kasm sunucusu):**
```
kasm: konteyner baslatildi ve connect URL guvenli     -> PASS
      status=True provider=kasm
      url=<kasm-host>:8443/#/connect/kasm/{id}/{uid}/{token}  guvenli=True
kasm: ikinci istek konteyneri yok etmiyor, ayni URL-i donduruyor  -> PASS
      ilk  = ...5LSq5njxV-9yTmNQtd_LipgjPck2x5b2bIhOlW3w
      ikinci = ...5LSq5njxV-9yTmNQtd_LipgjPck2x5b2bIhOlW3w     (önce: konteyner yok edilirdi)
```

---

## 5. Kasm hesap izolasyonu — "bir kullanıcı benim admin hesabıma erişiyor"

### Kök neden (empirik)
`browser_sandbox.kasm.user` + `password` **instance genelinde** tanımlıydı.
Canlı test: **admin olmayan** bir Open WebUI kullanıcısı (`role=user`) tarayıcı
oturumu açtığında konteyner **admin'in Kasm hesabıyla** açılıyordu:

```
status=True
live_url = <kasm-host>:8443/#/connect/kasm/{kasm_id}/<admin-kasm-user-id>/{token}
                                     ^^^ admin'in Kasm user_id'si
Kasm tarafı: kasm_id=... user_id=<admin-kasm-user-id>
             username=<admin-kasm-account>   share_id=3b97126e  (herkese açık join linki)
```

Yani kullanıcı, **admin'in Kasm oturum token'ını** alıyordu. Üstelik
`enable_sharing: True` olduğu için her oturum için herkese açık bir
`#/join/<share_id>` linki de üretiliyordu.

### Düzeltmeler
| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/utils/browser_session.py` | **YENİ** `get_user_kasm_credentials(user)` — kullanıcı kendi Kasm hesabını kendi ayarlarından girer (`settings.browserSandboxKasm` / `settings.ui.browserSandboxKasm`) |
| `backend/open_webui/routers/browser.py` | Kendi Kasm hesabı olan kullanıcı **her zaman** erişebilir ve konteyner **kendi hesabında** açılır |
| `backend/open_webui/routers/browser.py` | **YENİ** `browser_sandbox.allowed_roles` (varsayılan `["admin"]`) — paylaşılan hesabı sadece bu roller kullanabilir |
| `backend/open_webui/routers/browser.py` | `enable_sharing` artık `browser_sandbox.kasm.enable_sharing` ayarından geliyor (varsayılan **kapalı**) → herkese açık join linki üretilmiyor |
| `backend/open_webui/routers/configs.py` | Yeni ayarlar eklendi (`BROWSER_SANDBOX_ALLOWED_ROLES`, `KASM_ENABLE_SHARING`) |
| `src/lib/components/admin/Settings/CodeExecution.svelte` | "Roles allowed to use the shared Kasm account" alanı + "Allow shared session links" anahtarı |
| `src/lib/components/chat/MessageInput/BrowserSelectModal.svelte` | Kullanıcı kendi Kasm kullanıcı adı/şifresini girebiliyor ("My Browser Account") |

**Canlı doğrulama (gerçek Kasm sunucusu, 5/5):**
```
kasm: konteyner gercekten calisiyor (get_kasm_status)      -> PASS  HTTP 200
kasm: konteyner listede ve paylasim linki kapali             -> PASS  share_id=None
kasm: SPA sayfasi iframe icin yukleniyor (X-Frame-Options yok) -> PASS  HTTP 200
kasm: siradan kullanici paylasilan hesabi kullanamaz         -> PASS  status=False
      "The browser sandbox uses a shared Kasm account and is limited to: admin.
       Configure your own Kasm account in your user settings or ask an
       administrator to allow your role."
kasm: kendi hesabi olan kullanici erisebiliyor                -> PASS  status=True
```

### Admin panelinde yapılacak
**Ayarlar → Code Execution → Kasm**:
- `Roles allowed to use the shared Kasm account` → `admin` (varsayılan).
  Tüm kullanıcılara açmak istersen `admin, user` yaz.
- `Allow shared session links` → kapalı bırakılmalı (herkese açık join linki üretir).

Kullanıcıların tarayıcı kullanabilmesi için iki yol var:
1. Roller listesine `user` ekle (paylaşılan hesap — oturumlar herkese açık olur)
2. Her kullanıcı **kendi Kasm hesabını** girsin (tam izolasyon) →
   Chat → Entegrasyonlar → Web Browser ⚙️ → "My Browser Account"

---

## 6. Sağlayıcı adı koddan çıkarıldı

`pixrouter` stringi 3 yerde hardcoded'dı (senin önceki commit'lerin). Repo
public olduğu için ve başka siteler de kullanacağı için **kaldırıldı**.

| Eski | Yeni |
|---|---|
| `if not api_base_url or 'pixrouter' in (api_base_url or '') or api_base_url == 'test':` | `api_base_url = resolve_provider_base_url(api_base_url, u_url)` |

`resolve_provider_base_url()` (`backend/open_webui/utils/direct_connections.py`)
marka adına bakmaz, **host'a** bakar: kullanıcının kendi anahtarı, **kendi
host'una** gönderilir; admin'in URL'i sadece kullanıcının kendi bağlantısıyla
**aynı host'u** gösteriyorsa korunur. Bu kural her sağlayıcı için doğru çalışır
ve marka adına bağımlı değildir.

---

## 7. Eklenen testler

| Dosya | Kapsam |
|---|---|
| `test/test_video_generation_params.py` | admin params/mode payload'a gidiyor mu, string-JSON parse, desteklenmeyen alan düşürülüyor, "required" hatasında alan **silinmiyor** |
| `test/test_browser_session_url.py` | 5 parçalı + 4 parçalı Kasm connect URL, boş segment reddi |
| `test/test_kasm_dashboard_fallback.py` | dashboard tespiti, fragment'lı session URL'ı dashboard sayılmıyor, ağ hatasında dashboard **dönülmüyor** |
| `test/test_kasm_isolation.py` | paylaşılan hesap rol kısıtı, kendi hesabı olan kullanıcı, admin erişimi |
| `test/live_provider_check.py` | **canlı** sağlayıcı + Kasm doğrulaması (10 kontrol) — tüm host/anahtar/model **environment'tan** okunur |
| `test/live_realtime_check.py` | **canlı** realtime model doğrulaması — environment'tan okunur |
| `test/live_kasm_check.py` | **canlı** Kasm: konteyner çalışıyor mu, share linki kapalı mı, hesap izolasyonu — environment'tan okunur |

## 8. Doğrulama özeti

| Kontrol | Sonuç |
|---|---|
| `pytest test/` | ✅ **28 passed** |
| `ruff format --check` (CI backend) | ✅ 295 dosya formatlı |
| `ruff check --select=F` (CI backend) | ✅ All checks passed |
| Canlı video isteği (mode gönderilerek) | ✅ 400 "mode is required" → 503 (kabul edildi) |
| Canlı image hatası | ✅ artık model/endpoint ipucuyla görünüyor |
| Canlı Kasm konteyner + 2. istek | ✅ konteyner artık yok edilmiyor |
| Canlı Kasm: konteyner çalışıyor, share kapalı, hesap izolasyonu | ✅ 5/5 |
| Canlı realtime model doğrulama | ✅ doğru modeli doğru raporluyor |
| `pixrouter` stringi kodda | ✅ **0** (yerine host bazlı genel kural) |
| Vite production build | ✅ |

> **Gizlilik:** Raporlarda ve test dosyalarında sunucu IP'si, port, hesap adı ve
> anahtar **bulunmaz** — tüm canlı test değerleri environment değişkenlerinden
> okunur (`KASM_URL`, `PIX_URL`, `KASM_API_KEY`, …).
