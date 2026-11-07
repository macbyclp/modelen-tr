# Avukat onay listesi

`site/` içindeki yasal metinler ve açık kaynak kararları bir avukat tarafından incelenmeden yayınlanmamalıdır. Bu liste, avukata götürülecek soruları ve metinlerin zayıf noktalarını toplar. Ben hukuki danışman değilim; metinler taslaktır.

## İncelenecek belgeler

| Belge | Yer | Not |
|---|---|---|
| Gizlilik politikası | `site/gizlilik.html` / `en/privacy.html` | Barındırma sağlayıcısı belli değil |
| KVKK aydınlatma metni | `site/kvkk.html` | Yayın zamanlaması |
| Site kullanım şartları | `site/kullanim-sartlari.html` | Sorumluluk sınırı ve yetkili mahkeme boş |
| Çerez politikası | `site/cerez.html` | Çerez yok iddiası barındırmaya bağlı |
| Gönüllü katılım şartları | `site/gonullu-sartlari.html` | İstemci yok; bağlayıcılık ve sorumluluk |
| Katkı şartları | `site/katki-sartlari.html` | DCO + Apache-2.0 yeterli mi |
| Lisans notu | `site/lisans.html`, `LICENSE`, `NOTICE` | Eğitim verisi lisansı |

## Sorulacak ana sorular

1. **Eğitim verisi lisansı ve ağırlıklar.** Türkçe Vikipedi (CC BY-SA / GFDL) ile eğitilen adaptör/ağırlıklar Apache-2.0 altında yayınlanabilir mi, yoksa share-alike şartı ağırlıklara yansır mı? Bu hukuken belirsiz bir alan. FineWeb2 (ODC-By) ve diğer adaylar için de aynı soru.
2. **Taban model.** Qwen3 Apache-2.0; türev ağırlıkların yayını ve NOTICE yükümlülükleri yeterli mi?
3. **Gönüllü ilişkisinin niteliği.** Karşılıksız gönüllü GPU paylaşımı: hizmet ilişkisi/ücretsiz hizmet sayılır mı? 18 yaş altı veli onayı yeterli mi? Elektrik/donanım zararı için sorumluluk sınırlaması geçerli mi (tüketici mevzuatı, genel işlem şartları)?
4. **Bilişim hukuku.** Gönüllü bilgisayarında kod çalıştıran istemci, rıza ve şeffaflık açısından TCK'nın bilişim suçları hükümleri (özellikle 243–244) ve KVKK bakımından nasıl tasarlanmalı? İstemci "yalnızca eğitim işi çalıştırır, kişisel veriye erişmez" iddiasını teknik olarak (sandbox) nasıl güvenceye alır?
5. **Kişisel veri.** Gönüllü teknik verileri (GPU, işletim sistemi, katkı kaydı) kişisel veri sayılır mı; katkı kaydında takma ad; yurt dışı aktarım (barındırma, e-posta).
6. **Katkı kaydı ve söz hakkı.** "Söz hakkı"nı hukuken nasıl yapılandırırız (danışma kurulu, topluluk oylaması, topluluğun hukuki statüsüyle uyum)?
7. **Ticari e-ileti.** Duyuru e-postaları için İYS ve onay gereklilikleri.
8. **Yapay zeka düzenlemesi.** AB Yapay Zekâ Tüzüğü (genel amaçlı model yükümlülükleri) modeller AB'de erişilebilir olursa uygulanır mı? Türkiye'de yürürlükteki veya hazırlanan düzenlemeler.
9. **Kod mülkiyeti.** Topluluk adına yazılmamış kod (ör. `diloco_sim.py`, `adaptor_diloco.py`, `lora_cpt.py`) kimin adına ve hangi lisansla topluluğa katıldığı. Ayrıca yapay zekâ yardımıyla üretilen kodun eser/telif statüsü.
10. **Marka.** "Modelen" için araştırma ve tescil; topluluk adı ile marka çakışması.
11. **Yetkili mahkeme ve hukuk.** Yetkili mahkeme ve icra daireleri belirlenecek.
12. **Teşvik ve hibeler.** Ar-Ge/yazılım teşvikleri ve olası kamu desteklerinin topluluk yapısına uygunluğu (açık kaynak ilkesiyle uyum).

## Metinlerde bilerek yapılan seçimler

- Kişi adı ve kişisel iletişim yok; tek kurumsal e-posta.
- Sitede çerez/takip/üçüncü taraf kaynak yok; aksi halde çerez ve gizlilik metinleri değişmeli.
- Hiçbir yerde "KVKK uyumludur", "güvenlidir", "en iyi" gibi doğrulanmamış iddia yok. Modelin henüz yayınlanmadığı ve sonuçların sınırlı olduğu açıkça yazılı.
- Yer tutucular köşeli parantezle işaretli; `site/build.py` içinde dolduruluyor.
- Yasal sayfalarda `DRAFT` uyarısı var; avukat onayından sonra `DRAFT = False` yapılır.

## Yayın kapısı

Aşağıdakiler tamam olmadan siteyi yayına almayın:
- [ ] Barındırma sağlayıcısı seçildi, gizlilik/aydınlatma metinleri ona göre güncellendi.
- [ ] Avukat tüm yasal metinleri onayladı, `DRAFT = False`.
- [ ] `iletisim@modelen.tr` posta kutusu çalışıyor ve izleniyor.
- [ ] Lisans/eğitim verisi sorusu (madde 1) yanıtlandı; yanıta göre `lisans.html` güncellendi.

## Logo (eklendi 2026-11-07)

13. **Yapay zekâyla üretilen logo.** Seçilen logo (F03 Halay Halkası) gpt-image-2 çıktısından otomatik izlenerek vektörleştirildi. Yapay zekâ üretimi bir eserin telif durumunun ve marka olarak tescil edilebilirliğinin (ayırt edicilik, benzerlik araştırması, TürkPatent) avukatla netleştirilmesi gerekir; ayrıca üretim aracının kullanım koşullarının ticari kullanıma izin verdiği teyit edilmeli. Nihai uygulamada bir tasarımcının logoyu yeniden çizmesi telif belirsizliğini azaltır.
