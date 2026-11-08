"""Portal API v1 şeması (OpenAPI 3.0). Hem `/api/v1/openapi.json` olarak sunulur hem de dokümantasyon sitesi bu veriden başvuru sayfasını üretir.
Yalnızca veri; hiçbir bağımlılığı yok. Açıklamalar Türkçe, `x-en` alanları İngilizce karşılıktır."""

HATA = {"type": "object", "properties": {"hata": {"type": "string"}, "kod": {"type": "string"}}, "required": ["hata", "kod"]}

KOORD_ALANLARI = {
    "ad": {"type": "string", "minLength": 2, "maxLength": 60, "description": "Proje / koordinatör adı"},
    "kisa": {"type": "string", "minLength": 10, "maxLength": 200, "description": "Listelerde görünen kısa açıklama"},
    "ayrinti": {"type": "string", "maxLength": 5000, "description": "Herkese açık ayrıntılı açıklama (düz metin)"},
    "baglanti": {"type": "string", "format": "uri", "maxLength": 200, "description": "Web sitesi ya da depo (http/https)"},
    "adres": {"type": "string", "format": "uri", "maxLength": 200, "description": "Koordinatör adresi (https); boş olabilir"},
    "hf": {"type": "string", "format": "uri", "maxLength": 200, "description": "Hugging Face bağlantısı (huggingface.co / hf.co)"},
    "iletisim": {"type": "string", "format": "email", "maxLength": 120, "description": "Yalnızca yöneticilere görünen iletişim e-postası"},
}

SEMALAR = {
    "Hata": HATA,
    "Koordinatorum": {"type": "object", "properties": {
        "slug": {"type": "string"}, **KOORD_ALANLARI,
        "durum": {"type": "string", "enum": ["beklemede", "onaylandi", "reddedildi", "askida"]},
        "yonetici_notu": {"type": "string"}, "taslak_var": {"type": "boolean", "description": "Onaylı profilde onay bekleyen düzenleme var"},
        "adres_dogrulandi": {"type": "boolean"}, "gorsel_sayisi": {"type": "integer"},
        "sayfa": {"type": "string", "format": "uri", "nullable": True, "description": "Onaylıysa herkese açık sayfa"},
        "nabiz": {"$ref": "#/components/schemas/NabizDurumu"}}},
    "KoordinatorGirdisi": {"type": "object", "properties": KOORD_ALANLARI, "additionalProperties": False},
    "Nabiz": {"type": "object", "required": ["durum"], "additionalProperties": False, "properties": {
        "durum": {"type": "string", "enum": ["calisiyor", "bekliyor", "bakimda", "durdu"]},
        "tur": {"type": "integer", "minimum": 0}, "toplam_tur": {"type": "integer", "minimum": 0},
        "aktif_isci": {"type": "integer", "minimum": 0}, "protokol": {"type": "string", "maxLength": 10, "example": "1"},
        "surum": {"type": "string", "maxLength": 30}, "mesaj": {"type": "string", "maxLength": 120}}},
    "NabizDurumu": {"type": "object", "nullable": True, "properties": {
        "durum": {"type": "string", "enum": ["cevrimici", "gecikmeli", "bakimda", "durdu", "bilinmiyor"]},
        "son_gorulme": {"type": "integer", "nullable": True, "description": "Unix zamanı (sn)"},
        "tur": {"type": "integer", "nullable": True}, "toplam_tur": {"type": "integer", "nullable": True}, "aktif_isci": {"type": "integer", "nullable": True}}},
    "KoordinatorOzet": {"type": "object", "properties": {
        "slug": {"type": "string"}, "ad": {"type": "string"}, "aciklama": {"type": "string"},
        "adres": {"type": "string", "nullable": True}, "adres_dogrulandi": {"type": "boolean"},
        "hf": {"type": "string", "nullable": True}, "baglanti": {"type": "string", "nullable": True},
        "nabiz": {"$ref": "#/components/schemas/NabizDurumu"}, "sayfa": {"type": "string", "format": "uri"}}},
    "AdresDogrulama": {"type": "object", "properties": {
        "adres": {"type": "string"}, "dosya": {"type": "string", "format": "uri", "description": "Bu adreste yayınlanmalı"},
        "icerik": {"type": "string", "description": "Dosyanın tek satırlık içeriği"}}},
}

GUVENLIK = [{"anahtar": []}]


def _yanit(kod, aciklama, sema=None):
    d = {"description": aciklama}
    if sema:
        d["content"] = {"application/json": {"schema": sema}}
    return {str(kod): d}


def _ref(ad):
    return {"$ref": f"#/components/schemas/{ad}"}


STANDART_HATALAR = {**_yanit(401, "Anahtar yok ya da geçersiz", _ref("Hata")), **_yanit(429, "Hız sınırı aşıldı", _ref("Hata"))}


def sema(site="https://modelen.tr"):
    yollar = {
        "/saglik": {"get": {"summary": "Sağlık denetimi", "x-en": "Health check", "tags": ["Genel"], "security": [],
                            "responses": _yanit(200, "Servis ayakta", {"type": "object", "properties": {"durum": {"type": "string", "example": "tamam"}, "zaman": {"type": "integer"}}})}},
        "/koordinatorler": {"get": {"summary": "Onaylı koordinatörleri listele", "x-en": "List approved coordinators", "tags": ["Herkese açık"], "security": [],
                                    "description": "Yalnızca yöneticilerin onayladığı koordinatörler. 60 sn önbelleğe alınabilir. CORS açık.",
                                    "responses": _yanit(200, "Liste", {"type": "object", "properties": {"surum": {"type": "integer"}, "guncelleme": {"type": "string"},
                                                                                                         "koordinatorler": {"type": "array", "items": _ref("KoordinatorOzet")}}})}},
        "/koordinatorler/{slug}": {"get": {"summary": "Bir koordinatörün herkese açık ayrıntısı", "x-en": "Public details of a coordinator", "tags": ["Herkese açık"], "security": [],
                                           "parameters": [{"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}}],
                                           "responses": {**_yanit(200, "Koordinatör", _ref("KoordinatorOzet")), **_yanit(404, "Yok ya da onaylı değil", _ref("Hata"))}}},
        "/ben": {"get": {"summary": "Anahtar sahibi hesap", "x-en": "Account of the key owner", "tags": ["Hesap"], "security": GUVENLIK,
                         "responses": {**_yanit(200, "Hesap", {"type": "object", "properties": {"id": {"type": "integer"}, "ad": {"type": "string"}, "eposta": {"type": "string"},
                                                                                              "eposta_dogrulandi": {"type": "boolean"}, "rol": {"type": "string"},
                                                                                              "koordinator": {"type": "object", "nullable": True, "properties": {"slug": {"type": "string"}, "ad": {"type": "string"}, "durum": {"type": "string"}}}}}), **STANDART_HATALAR}}},
        "/koordinator": {
            "get": {"summary": "Kendi koordinatör kaydım", "x-en": "My coordinator record", "tags": ["Koordinatör"], "security": GUVENLIK,
                    "responses": {**_yanit(200, "Kayıt", _ref("Koordinatorum")), **_yanit(404, "Başvuru yok", _ref("Hata")), **STANDART_HATALAR}},
            "post": {"summary": "Koordinatör başvurusu oluştur", "x-en": "Create a coordinator application", "tags": ["Koordinatör"], "security": GUVENLIK,
                     "description": "E-posta doğrulanmış olmalı. `ad` ve `kisa` zorunlu. Başvuru yönetici onayına düşer.",
                     "requestBody": {"required": True, "content": {"application/json": {"schema": _ref("KoordinatorGirdisi")}}},
                     "responses": {**_yanit(201, "Oluşturuldu", _ref("Koordinatorum")), **_yanit(400, "Doğrulama hatası", _ref("Hata")), **_yanit(403, "E-posta doğrulanmamış", _ref("Hata")),
                                   **_yanit(409, "Zaten başvuru var", _ref("Hata")), **STANDART_HATALAR}},
            "patch": {"summary": "Koordinatör bilgilerini güncelle", "x-en": "Update coordinator details", "tags": ["Koordinatör"], "security": GUVENLIK,
                      "description": "Yalnızca gönderilen alanlar değişir. İncelemedeki/reddedilmiş başvuruda doğrudan, **onaylı** profilde taslak olarak kaydedilir ve yönetici onayından sonra yayına girer (202). Adres değişirse doğrulama sıfırlanır.",
                      "requestBody": {"required": True, "content": {"application/json": {"schema": _ref("KoordinatorGirdisi")}}},
                      "responses": {**_yanit(200, "Güncellendi", _ref("Koordinatorum")), **_yanit(202, "Taslak olarak kaydedildi (onay bekliyor)", _ref("Koordinatorum")),
                                    **_yanit(400, "Doğrulama hatası", _ref("Hata")), **_yanit(404, "Başvuru yok", _ref("Hata")), **_yanit(409, "Askıda", _ref("Hata")), **STANDART_HATALAR}}},
        "/koordinator/nabiz": {"post": {"summary": "Nabız (çalışıyorum) bildirimi", "x-en": "Heartbeat", "tags": ["Koordinatör"], "security": GUVENLIK,
                                        "description": "Onaylı koordinatörler en geç 15 dakikada bir göndermelidir; herkese açık sayfada \"çevrimiçi\" görünürsünüz. En çok dakikada 6 istek.",
                                        "requestBody": {"required": True, "content": {"application/json": {"schema": _ref("Nabiz")}}},
                                        "responses": {**_yanit(200, "Kaydedildi"), **_yanit(400, "Geçersiz gövde", _ref("Hata")), **_yanit(403, "Onaylı koordinatör değil", _ref("Hata")), **STANDART_HATALAR}}},
        "/koordinator/adres-dogrula": {"post": {"summary": "Adres doğrulamasını başlat", "x-en": "Start address verification", "tags": ["Koordinatör"], "security": GUVENLIK,
                                                "description": "Adresinizi kontrol ettiğinizi kanıtlamak için döndürülen içeriği `/.well-known/modelen-dogrulama.txt` yoluyla yayınlayın, sonra `/kontrol` uç noktasını çağırın.",
                                                "responses": {**_yanit(200, "Talimat", _ref("AdresDogrulama")), **_yanit(400, "Adres yok ya da https değil", _ref("Hata")), **_yanit(404, "Başvuru yok", _ref("Hata")), **STANDART_HATALAR}}},
        "/koordinator/adres-dogrula/kontrol": {"post": {"summary": "Adres doğrulamasını kontrol et", "x-en": "Check address verification", "tags": ["Koordinatör"], "security": GUVENLIK,
                                                        "description": "Portal adresinizi (yalnızca genel internetteki https adreslerini) okur ve içeriği karşılaştırır. 10 dakikada en çok 10 deneme.",
                                                        "responses": {**_yanit(200, "Doğrulandı", {"type": "object", "properties": {"adres_dogrulandi": {"type": "boolean"}}}), **_yanit(422, "Dosya yok ya da içerik uyuşmuyor", _ref("Hata")),
                                                                      **_yanit(400, "Önce doğrulamayı başlatın", _ref("Hata")), **STANDART_HATALAR}}},
    }
    return {
        "openapi": "3.0.3",
        "info": {"title": "Modelen Portal API", "version": "1.0.0", "x-en": "Modelen Portal API",
                 "description": "Koordinatörlerin Modelen portalına programatik erişimi: başvuru ve profil yönetimi, nabız ve adres doğrulama, herkese açık koordinatör dizini."},
        "servers": [{"url": f"{site}/api/v1"}],
        "components": {"securitySchemes": {"anahtar": {"type": "http", "scheme": "bearer", "description": "Panel > API anahtarları sayfasından oluşturulan `mdl_...` anahtarı"}},
                       "schemas": SEMALAR},
        "paths": yollar,
    }
