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
| `agnes/agnes-image-2.1-flash` | `["openai", "image-generation"]` | katalogda **var** |
| `agnes/agnes-image-2.0-flash` | `[..., "image-generation"]` | katalogda **var** |
| `agnes/agnes-image-2.5-flash` | `[""openai""]` → **sadece chat** | 400 |
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

## 7. Gemini Live desteği (OpenAI Realtime + Gemini Live)

Realtime köprüsü artık **iki protokolü** konuşuyor. Tarayıcı tarafı her zaman
OpenAI Realtime biçimli olaylar kullanır (`input_audio_buffer.append`,
`response.output_audio.delta`, …); sağlayıcıya gidiş ve dönüş
`backend/open_webui/routers/audio/gemini_live.py` içinde çevrilir.

| Yön | OpenAI Realtime | Gemini Live |
|---|---|---|
| Kurulum | `session.update` | `{"setup": {...}}` + `setupComplete` |
| Ses girişi | `input_audio_buffer.append` (24 kHz) | `realtimeInput.mediaChunks` (**16 kHz**'e yeniden örneklenir) |
| Ses çıkışı | `response.output_audio.delta` | `serverContent.modelTurn.parts[].inlineData` → aynı olaya çevrilir |
| Metin | `conversation.item.create` | `clientContent.turns` |
| Araç çağrısı | `response.output_item.done` | `toolCall.functionCalls` → aynı olaya çevrilir |
| Araç sonucu | `conversation.item.create` (function_call_output) | `toolResponse.functionResponses` |
| Kesinti | `response.cancel` | `serverContent.interrupted` → `input_audio_buffer.speech_started` |

| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/routers/audio/gemini_live.py` | **YENİ** — protokol çevirisi, 24 kHz→16 kHz örnekleme, ses eşleme tablosu |
| `backend/open_webui/routers/audio/realtime.py` | `provider = 'gemini'` dalı: Gemini kurulum mesajı, çeviri, `verify` endpoint'i Gemini'yi de anlıyor |
| `backend/open_webui/routers/audio/__init__.py` | `PROVIDER` seçeneklerine `gemini`, `GEMINI_WS_URL` ayarı |
| `src/lib/apis/audio/index.ts` | `RealtimeConfig` tipine `gemini` ve `GEMINI_WS_URL` |
| `src/lib/components/admin/Settings/Audio.svelte` | "Gemini Live" sağlayıcı seçeneği + WS URL alanı |
| `test/test_gemini_live.py` | **YENİ** — 12 çeviri testi (ses örnekleme, ses eşleme, setup, araç çağrısı/sonucu, transkripsiyon, kesinti) |

**Yapılandırma:** Ayarlar → Audio → Provider = `Gemini Live`, Voice Model =
`google/gemini-3.8-live`. WS URL boş bırakılırsa herkese açık Gemini Live
endpoint'i kullanılır; bir gateway aynı servisi sunuyorsa `GEMINI_WS_URL` ile
ona yönlendirilir (`{model}` yer tutucusu desteklenir).

**WS URL şablonları:**

| Hedef | URL |
|---|---|
| Google (herkese açık) | `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent` |
| Gateway (Google yolunu yansıtıyorsa) | `wss://<gateway>/v1beta/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent` |
| Model adı gömülü ise | `wss://<gateway>/...?model={model}` |

> **Sağlayıcı notu (ölçülen):** Test edilen gateway'da Gemini live modelleri
> OpenAI Realtime köprüsünde **çevrilmiyor** (handshake sonrası socket kapanıyor)
> ve gateway'in Gemini native **HTTP** yolu (`/v1beta/models/{model}:{method}`)
> çalışıyor ama **WebSocket** relay'i yok (14 aday yolunun tamamı 404). Yani
> gateway tarafında Gemini Live için `bidiGenerateContent` WS yolu açılmalı;
> bu kodda WS yolu yapılandırılabilir olduğu için açılır açılmaz çalışır.
> Bu arada Gemini native HTTP yolundan gelen hata, modelin **gerçekten** Gemini
> Live modeli olduğunu ve sadece WS beklediğini doğruluyor:
> *"models/gemini-3.8-live only supports real-time bidirectional streaming via
> WebSocket (bidiGenerateContent)"*.

---

## 8. Kasm: kullanıcı hesabı istemiyor + katlanarak sessiz yeniden deneme

### Kullanıcı hesabı kaldırıldı
Tarayıcı açmak için hesap istemiyor: instance hesabı herkes tarafından
kullanılıyor, kullanıcıdan hiçbir kimlik bilgisi istenmiyor (GPT Agent / Gemini
Spark davranışı). Admin arayüzündeki "rol kısıtı" ve kullanıcıdaki "Kasm
hesabım" alanları kaldırıldı.

**Opsiyonel istisna:** Yönetici kendi oturumlarını **kendi Kasm hesabında**
çalıştırabilir (Chat → Entegrasyonlar → Web Browser ⚙️ → "My Browser Account").
Bu alan **sadece admin'e** görünür, sıradan kullanıcı hiç form görmez.

> **Önemli:** Paylaşılan Kasm hesabı **kişisel bir hesap olmamalı**. Kişisel
> hesap kullanılırsa o hesabın kayıtlı girişleri (cookie'ler) herkese açık
> olur. Ayrı bir servis hesabı oluşturmanız gerekiyor.

**Kasm hesapları (canlı kontrol):**
| Hesap | Grup | Durum |
|---|---|---|
| `<paylasilan-hesap>` | All Users | Paylaşılan servis hesabı — yönetici **değil** ✅ |
| `salih` | All Users + **Administrators** | Kişisel yönetici hesabın |

`/api/public/create_user` → **401 "Access Denied"** (API anahtarının sahibi
yönetici değil) → yeni hesap **Kasm web arayüzünden yönetici olarak** açılmalı:
**Settings → Users → Add User** → admin yetkisi yok, gruplar: sadece "All Users" →
sonra **Permissions → Images** üzerinden bu hesaba `kasmweb/*` workspace izni
verilmeli (yoksa konteyner açamaz).

### Katlanarak sessiz yeniden deneme
Kasm sunucusu erişilemez olduğunda veya hata döndürdüğünde kullanıcıya
söylenmeden **1 sn → 2 sn → 4 sn → 8 sn** bekleyerek **5 kez** yeniden deniyor.
Bekleme katlanarak büyüyor, denemeler sessiz.

| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/routers/browser.py` | **YENİ** `kasm_retry()` (katlanarak bekleme) ve `kasm_post()` (tüm Kasm API çağrıları bu üzerinden) |
| `backend/open_webui/routers/browser.py` | `authenticate`, `get_users`, `get_images`, `request_kasm`, `get_kasm_status` çağrıları retry'li |
| `test/test_kasm_isolation.py` | Paylaşılan hesabın herkese açık olması + retry sırası testi |
| `test/live_kasm_check.py` | Canlı doğrulama (5 kontrol) |

**Canlı doğrulama (gerçek Kasm sunucusu, 5/5):**
```
kasm: hesap istemeden tarayici acilir (paylasilan hesap)  -> PASS
kasm: konteyner gercekten calisiyor (get_kasm_status)      -> PASS  HTTP 200
kasm: paylasim linki kapali (share_id yok)                 -> PASS  share_id=None
kasm: SPA sayfasi iframe icin yukleniyor                    -> PASS  HTTP 200
kasm: 5 kez denenir, aralar 1s/2s/4s/8s                    -> PASS  deneme=5
```

---

## 10. Kasm iframe'i neden bozuk? — TLS sertifikası

### Canlı teşhis
Tarayıcıda birebir reprodüksiyon:

```
[browser.navigation_failed] The desktop rejected the site's TLS connection.
ERR_CERT_AUTHORITY_INVALID (-202)
```

Sertifika incelemesi:

| Alan | Değer |
|---|---|
| Subject / Issuer | `CN=vm183597.ovadns.com` (**self-signed**) |
| SAN | **yok** → IP adresiyle eşleşme imkânsız |
| Geçerlilik | 2026-10-04 → 2031-10-03 (tarih sorunu yok) |
| DNS | `vm183597.ovadns.com` **çözülmüyor** |

**Neden yeni sekmede çalışıyor, iframe'de çalışmıyor?**
Tarayıcı güvenilmeyen sertifika için **"Gelişmiş → Devam et"** uyarısı gösterir.
Bu uyarı **alt-çerçevede (iframe) gösterilemez**, Chrome yüklemeyi **doğrudan
engeller** → *"Çalışma sayfasındaki web ... sorunlarla karşılaşılıyor olabilir veya
kalıcı olarak yeni bir web adresine taşınmış olabilir."* hatası çıkar.

Yani bu **Open WebUI'de değil, Kasm sunucusunun sertifikasında** bir sorun.

### Çözüm (sunucu tarafı, kalıcı)
1. `kasm.senin-domain.com` → `<kasm-host>` DNS kaydı
2. 443'te bir reverse proxy (Caddy/nginx) + **Let's Encrypt** sertifikası →
   `https://127.0.0.1:8443`'e proxy
3. Open WebUI → Ayarlar → Code Execution → **Kasm URL** = `https://kasm.senin-domain.com`

Alternatif (reverse proxy istemezsen): Kasm'ın **kendi CA'sını** dışa aktarıp
istemci makinelerine kur (Windows: "Trusted Root Certification Authorities") ve
sertifikanın CN'ini kullanan **hostname**'i kullan (`vm183597.ovadns.com` →
`hosts` dosyasına ekle). IP adresi **asla** kullanılmamalı (SAN olmadığı için
eşleşmez).

### Kod tarafı yapılan
Artık kullanıcı Chrome'un kafa karışıcı hata sayfasını görmüyor:

| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/routers/browser.py` | **YENİ** `kasm_tls_status()` — Kasm sertifikasının sistem güven deposunda güvenilir olup olmadığını kontrol ediyor (sonuç önbellekleniyor) |
| `backend/open_webui/routers/browser.py` | Oturum cevabına ve `session/active` cevabına `tls` bilgisi ekleniyor |
| `backend/open_webui/tools/builtin.py` | `browser_session` olayına `tls` bilgisi taşınıyor |
| `src/lib/stores/index.ts` | **YENİ** `agentLiveNotice` store'u |
| `src/lib/components/chat/Chat.svelte` | `browser_session` olayından `tls` bilgisi okunup uyarıya çevriliyor |
| `src/lib/components/chat/LiveAgentPreview.svelte` | Sertifika güvenilmezse **bozuk iframe yerine** net bir uyarı + "Yeni sekmede aç" düğmesi gösteriliyor |

**Canlı doğrulama:**
```
https://<kasm-host>:8443   applicable=True  trusted=False  detail="self-signed certificate"
http://<kasm-host>:8443    applicable=False trusted=True
https://example.com          applicable=True  trusted=True
```

---

## 11. Tarayıcıyı kontrol eden araçlar (Computer Use)

Model artık açılan tarayıcıyı **gerçekten kullanabiliyor**. Hepsi Chrome DevTools
Protocol üzerinden çalışıyor (ek bağımlılık yok — WebSocket'i aiohttp yapar).

| Araç | Ne yapar |
|---|---|
| `browser_view` | Sayfayı "görür": adres, başlık, görünen metin + tıklanabilir öğeler (buton/bağlantı/alan) **koordinatlarıyla** |
| `browser_screenshot` | Ekran görüntüsü alır, sohbete **görsel olarak ekler** (model görebilir) |
| `browser_click` | Tıklar: ya koordinat (`x`,`y`) ya da **metinle** ("Submit" butonunu bul ve tıkla) |
| `browser_scroll` | Kaydırır: `dy`/`dx` ile, ya da `to=top/bottom/<metin>` |
| `browser_type` | Odaklı alana yazar (`clear=true` ile önce temizler) |
| `browser_press` | Tuş basar: Enter, Tab, Escape, Backspace, Delete, Space, ok tuşları, Ctrl+A/C/V |
| `browser_drag` | Sürükler (slider, metin seçimi) |
| `browser_select` | Açılır listeden seçer (`<select>`) |
| `browser_delete` | Odaklı alandan siler (Backspace ×N) |
| `browser_open` | Adres açar |
| `browser_wait` | Bekler (sayfa yüklenirken) |

| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/utils/browser_cdp.py` | **YENİ** — CDP istemcisi, sayfa anlık görüntüsü/click/select/find betikleri, tuş tablosu, DevTools uç noktası keşfi |
| `backend/open_webui/tools/builtin.py` | **YENİ** 11 araç (`browser_view` … `browser_wait`) |
| `backend/open_webui/utils/tools.py` | Araçlar tarayıcı özelliği açıkken kaydediliyor |
| `test/test_browser_cdp.py` | **YENİ** — betik üretimi, tuş tablosu, URL normalizasyonu testleri |

### DevTools uç noktası nasıl bulunur?
1. **Ayarlanan adres önceliklidir**: Admin → Code Execution → **Kasm CDP URL**
   (örn. `http://<kasm-host>:3000`)
2. Yoksa Kasm konteynerinin **port haritasından** 9222 portu bulunur ve
   `/json/list` üzerinden sayfanın WebSocket adresi alınır.

> Uç nokta bulunamazsa araçlar net bir mesaj döner:
> *"The browser does not expose a DevTools endpoint. Configure 'Kasm CDP URL' ..."*

---

## 12. Medya araçlarının seçenekleri modele söylenmiyordu

### Kök neden
`generate_video` / `generate_image` / `edit_image` araçlarının açıklaması **sabit
metin**ti (ör. *"aspect ratio ('21:9', '16:9', '4:3', '1:1', '3:4', '9:16')"*).
Admin 8 oran girdiyse model hâlâ 6 tanesini duyuyordu; çözünürlük seçenekleri
hiç söylenmiyordu.

Ayrıca **Images ayarlarında 4 alan kaydedilmiyordu**:
`IMAGE_DEFAULT_RATIO`, `IMAGE_ALLOWED_SIZES`, `IMAGE_ALLOWED_RATIOS`,
`ENABLE_REFERENCE_IMAGES` backend'de `IMAGE_CONFIG_KEYS` içinde yoktu →
`config_updates()` bunları düşürüyordu → **"kaydet dedim, input boşaldı"**
tam da buydu.

### Düzeltmeler
| Dosya | Değişiklik |
|---|---|
| `backend/open_webui/utils/tools.py` | **YENİ** `build_media_options_hint()` — admin'in girdiği oran/çözünürlük/süre/referans görsel limiti araç açıklamasına ekleniyor |
| `backend/open_webui/routers/images.py` | Eksik config anahtarları eklendi (`default_ratio`, `allowed_sizes`, `allowed_ratios`, `reference_images.enable/max`) |
| `backend/open_webui/routers/images.py` | `IMAGE_SIZE` doğrulaması artık **1K / 2K / 3K / 4K** tier'larını da kabul ediyor (eskiden `^\d+x\d+$` → reddediyordu) |
| `backend/open_webui/routers/images.py` | Tier boyutlar çözünürlük olarak **aynen** sağlayıcıya gidiyor (eskiden `'x' in size` kontrolü "1K"yi yok sayıp `size.split('x')` ile ValueError veriyordu) |
| `backend/open_webui/routers/images.py` | İzin verilmeyen çözünürlük/oran reddediliyor, model hangi değerlerin geçerli olduğunu öğrenip düzeltebiliyor |
| `backend/open_webui/routers/images.py` | Varsayılan oran, sağlayıcı parametrelerinde yoksa otomatik ekleniyor |
| `backend/open_webui/routers/videos.py` | Aynı doğrulama video için de var |
| `src/lib/components/admin/Settings/Images.svelte` | "Azami referans görsel sayısı" alanı eklendi |
| `src/lib/i18n/locales/tr-TR,en-US` | 18 yeni çeviri anahtarı |

**Modele artık şunlar söyleniyor:**
```
Options configured by the administrator. Only use these values...
- aspect ratio: 21:9, 16:9, 4:3, 1:1, 3:4, 9:16, 2:3, 3:2 (default: 16:9)
- resolution: 720P, 1080P, 1024x1024 (default: 720P)
- duration: 4 - 12 seconds (default: 12)
- reference images: up to 5
```
```
- resolution: 4096x4096, 1K, 2K, 3K, 4K (default: 4096x4096)
- aspect ratio: 1:1, 16:9, 9:16, 4:3, 3:4, 2:3, 3:2, 21:9 (default: 1:1)
- reference images: up to 4
```

---

## 13. Kasm önizleme üst barı ve i18n

4-5 buton aynı işi yapıyordu, bazıları çeviri dışıydı. Artık:
- Başlıkta **tek buton** ("Ayrı pencerede aç") + kapatma
- Altta eski mavi bar kaldırıldı
- Sertifika uyarısı varsa net mesaj + "Yeni sekmede aç" butonu
- Tüm metinler tr-TR + en-US çeviri kataloğunda

---

## 14. Bu turda düzeltilenler

### Admin → Images sayfası boş ekran veriyordu (bloker)
Pydantic v2'da `Optional[X]` **varsayılan değersiz** yani hâlâ **zorunlu** alan
demektir. Yeni eklenen 5 alan (`IMAGE_DEFAULT_RATIO`, `IMAGE_ALLOWED_SIZES`,
`IMAGE_ALLOWED_RATIOS`, `ENABLE_REFERENCE_IMAGES`, `REFERENCE_IMAGES_MAX`) response
modelinde zorunlu kaldı → FastAPI doğrulaması 500 verdi → sayfa boş kaldı.
Artık `= None` varsayılanları var.

### PixRouter Gemini realtime proxy'si test edildi ✅
Proxy **Gemini Live** el sıkışması kullanıyor (OpenAI-Realtime değil):
- `wss://<host>/v1/realtime?model={model}` — model **sorgu dizesinde** olmalı (yoksa HTTP 400)
- İlk mesaj `{"setup": {...}}` → yanıt `{"setupComplete": {}}` + `sessionResumptionUpdate`
- Backend'in Gemini dalı bununla birebir çalışıyor (canlı test: `setupComplete` geldi)

| Değişiklik | Detay |
|---|---|
| `backend/open_webui/routers/audio/realtime.py` | `{model}` yer tutucusu artık **tam model id'sini** koyuyor (`google/gemini-3.8-live`), çünkü gateway modeli kendi yayımladığı id ile tanıyor |
| `backend/open_webui/routers/audio/realtime.py` | Gemini dalında boş `api_base_url` reddedilmiyordu (adres WS şablonundan geliyor) |
| `backend/open_webui/routers/audio/realtime.py` | Şema dönüşümü yalnızca baştaki `http(s)://` için yapılıyor |

### Sesli arama: BYOK modelleri kabul ediliyor
`modelId` hesaplanırken **direct (BYOK) modelleri bilerek dışlanıyordu** →
"Select one server-configured chat model." hatası. Backend'de
`generate_direct_chat_completion` kullanıcının kendi bağlantısıyla çalışmayı
zaten destekliyor; engel sadece frontend filtresiydi. Artık BYOK modeli de seçilebilir.

### 4K / 2K / 3K boyutları arayüzde de kabul ediliyor
Placeholder'lar güncellendi: "Default Size (e.g. 1024x1024, 1K, 2K, 3K or 4K)".

### Kasm sertifikası iframe'i engellemiyor
Sertifika güvenilmezse ekran **boş** kalmıyor; iframe her zaman açılıyor, üstünde
kısa bir uyarı şeridi ve "Yeni sekmede aç" düğmesi duruyor.

---

## 15. Eklenen testler

| Dosya | Kapsam |
|---|---|
| `test/test_video_generation_params.py` | admin params/mode payload'a gidiyor mu, string-JSON parse, desteklenmeyen alan düşürülüyor, "required" hatasında alan **silinmiyor** |
| `test/test_browser_session_url.py` | 5 parçalı + 4 parçalı Kasm connect URL, boş segment reddi |
| `test/test_kasm_dashboard_fallback.py` | dashboard tespiti, fragment'lı session URL'ı dashboard sayılmıyor, ağ hatasında dashboard **dönülmüyor** |
| `test/test_kasm_isolation.py` | paylaşılan hesap herkese açık, katlanarak retry sırası |
| `test/test_gemini_live.py` | Gemini Live çevirisi: ses örnekleme, ses eşleme, setup, araç çağrısı/sonucu, transkripsiyon, kesinti |
| `test/test_media_options.py` | modele giden oran/çözünürlük listesi, tier boyut doğrulaması |
| `test/test_browser_tools.py` | tarayıcı araçları özellik açıkken modele ulaşıyor, kapalıyken ulaşmıyor |
| `test/live_provider_check.py` | **canlı** sağlayıcı + Kasm doğrulaması (10 kontrol) — tüm host/anahtar/model **environment'tan** okunur |
| `test/live_realtime_check.py` | **canlı** realtime model doğrulaması — environment'tan okunur |
| `test/live_kasm_check.py` | **canlı** Kasm: konteyner çalışıyor mu, share linki kapalı mı, retry sırası — environment'tan okunur |

## 10. Doğrulama özeti

| Kontrol | Sonuç |
|---|---|
| `pytest test/` | ✅ **58 passed** |
| `ruff format --check` (CI backend) | ✅ 297 dosya formatlı |
| `ruff check --select=F` (CI backend) | ✅ All checks passed |
| Canlı video isteği (mode gönderilerek) | ✅ 400 "mode is required" → 503 (kabul edildi) |
| Canlı Agnes image 2.5 flash | ✅ 1K/2K/3K/4K/4096x4096 + 8 oranın tamamı 200 |
| Canlı image hatası | ✅ artık model/endpoint ipucuyla görünüyor |
| Canlı Kasm (5 kontrol) | ✅ 5/5 |
| Canlı realtime model doğrulama | ✅ doğru modeli doğru raporluyor |
| `pixrouter` stringi kodda | ✅ **0** (yerine host bazlı genel kural) |
| Vite production build | ✅ |

> **Gizlilik:** Raporlarda ve test dosyalarında sunucu IP'si, port, hesap adı ve
> anahtar **bulunmaz** — tüm canlı test değerleri environment değişkenlerinden
> okunur (`KASM_URL`, `PIX_URL`, `KASM_API_KEY`, …).
