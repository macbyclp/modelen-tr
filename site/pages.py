# -*- coding: utf-8 -*-
"""İç sayfalar (TR/EN), ana sayfadaki yeni dille: kısa cümle, başlık bloğu, çerçeveli bileşenler.
Sayılar `ADAPTASYON.md`, `README.md` ve `*.json` ham çıktılarından alınmıştır."""


def phead(label, h1, lead=""):
    lead_html = f'<p class="lead">{lead}</p>' if lead else ""
    return f'<div class="phead"><p class="label">{label}</p><h1>{h1}</h1>{lead_html}</div>'


def table(head, rows, num_from=1):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = ""
    for r in rows:
        tds = "".join(
            f'<td class="num">{c}</td>' if i >= num_from else f"<td>{c}</td>" for i, c in enumerate(r))
        tr += f"<tr>{tds}</tr>"
    return f'<div class="tscroll"><table class="xt"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def steps(items):
    return '<div class="steps2">' + "".join(
        f"<div><div><h3>{h}</h3><p>{p}</p></div></div>" for h, p in items) + "</div>"


def stages(items):
    out = ""
    for cls, small, b, p in items:
        out += f'<div class="{cls}"><small>{small}</small><b>{b}</b><p>{p}</p></div>'
    return f'<div class="stages">{out}</div>'


def kv(items):
    return '<dl class="kv">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in items) + "</dl>"


def risks(items):
    return '<ul class="risks">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


# ---------------------------------------------------------------- TÜRKÇE
TR = {}

TR["nasil-calisir"] = dict(
    title="Nasıl çalışır · Modelen",
    desc="Modelen'de gönüllü GPU'larla dağıtık eğitim nasıl çalışacak: açık taban, LoRA adaptörü, seyrek senkronizasyon ve doğrulama.",
    body=phead("Nasıl çalışır", "Sıfırdan değil. Açık bir tabandan.",
               "Modeli baştan eğitmek yerine yeni bir dili öğrenen küçük bir parçayı eğitiyoruz (ilk dilimiz Türkçe) ve bu parçayı gönüllü bilgisayarlara bölüyoruz.")
    + """<div class="flow" aria-label="Akış">
<div class="box">Taban model<small>dondurulmuş · ≈ 1,2 GB</small></div><span>+</span>
<div class="box hot">LoRA adaptörü<small>eğitilen · ≈ 40 MB</small></div><span>→</span>
<div class="box">Gönüllüler<small>her biri kendi veri dilimiyle</small></div><span>→</span>
<div class="box hot">Birleştirme<small>25 adımda bir</small></div></div>"""
    + steps([
        ("Açık bir tabandan başlarız",
         "Lisansı uygun bir model alırız; ilk deneyimizde Qwen3-0.6B-Base (Apache-2.0). Sıfırdan eğitim tek ekran kartında aylar sürer ve 8 GB belleğe sığmaz."),
        ("Yalnızca küçük bir adaptörü eğitiriz",
         "LoRA ile taban donuk kalır. Denememizde adaptör ≈ 40 MB, tepe bellek 5,2 GB oldu. Bu, bir dizüstü ekran kartına sığar."),
        ("Güncellemeleri seyrek birleştiririz",
         "Her gönüllü bir süre kendi veri diliminde çalışır; yalnızca adaptör farkları toplanır (DiLoCo). Simülasyonumuzda yaklaşık 25 kat az veri taşındı."),
        ("Katkıyı doğrularız",
         "Hatalı ya da kötü niyetli güncelleme gelebilir. Planımız: aynı işi birden fazla makinede doğrulamak, güncelleme büyüklüğünü ve uyumunu denetlemek, bilinen küçük kontrol görevleri eklemek. Bu mekanizmalar henüz geliştirme aşamasında."),
    ])
    + """<h2>Bilgisayarınıza ne olur</h2>
<ul>
<li>İstemci açık kaynaktır; ne çalıştırdığını okuyabilirsiniz.</li>
<li>İmzalı güncellemeler hedefimizdir; şu an sürümler SHA-256 özetiyle ve kaynak kanıtıyla (attestation) doğrulanabilir.</li>
<li>İstemci yalnızca eğitim işini çalıştırır; dosyalarınıza ve kişisel verilerinize erişmez. Bu bir tasarım ilkesidir; kodu <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub'da</a> okuyup doğrulayabilirsiniz.</li>
<li>İstediğiniz an durdurursunuz.</li>
</ul>
<h2>Bilmediklerimiz</h2>
<p class="note">1 milyar parametre ve üzerinde, gerçek internet koşullarında, farklı veri dilimleriyle, gönüllü kaybı ve kötü niyetli katkı varken sonuçların nasıl değişeceğini ölçmedik. Şimdiye kadarki ölçümler <a href="olcumler.html">Ölçümler</a> sayfasında.</p>""")

TR["yol-haritasi"] = dict(
    title="Yol haritası · Modelen",
    desc="Modelen yol haritası: araştırma, ilk dil uyarlaması, gönüllü istemcisi, pilot ve açık ağ. Tarih taahhüdü yok.",
    body=phead("Yol haritası", "Aşamaları yazıyoruz, tarih vermiyoruz.",
               "Bir aşama bitince ölçtüğümüzü ve bulamadığımızı birlikte yayınlayacağız.")
    + stages([
        ("done", "00 · YAPILDI", "Araştırma", "Küçük modelde seyrek senkronizasyon ve adaptör ölçeğinde DiLoCo simülasyonu."),
        ("done", "01 · İLK DENEY", "İlk dil: Türkçe", "Qwen3-0.6B-Base üzerinde 8 GB'ta LoRA ile kısa sürekli ön eğitim."),
        ("", "02 · SIRADA", "Veri ve ölçüm", "Daha çok Türkçe veri, İngilizce tekrar karışımı, tokenizer, 1,7B taban."),
        ("", "03 · YAYINDA (ALFA)", "Gönüllü istemcisi", "Açık kaynak; Windows ve Ubuntu. Sırada: imzalı güncelleme, katkı doğrulama."),
        ("", "04", "Kapalı pilot", "Küçük bir gönüllü grubuyla gerçek ağda eğitim."),
        ("", "05", "Açık ağ ve ilk yayın", "Ağırlıklar, kod ve veri kaynakları listesi; Apache-2.0 / ilgili lisanslarla."),
    ])
    + "<h2>Bilinen riskler</h2>"
    + risks([
        "Seyrek senkronizasyonla eğitilen ağırlıkların sonradan standart eğitimle uyumsuz kalabileceğine dair araştırma var. Bunu kendimiz sınayacağız.",
        "Eğitim verisinin lisansları (ör. CC BY-SA veriler) yayınlayacağımız ağırlıklar için hukuki inceleme gerektiriyor. Sonucu <a href=\"lisans.html\">Lisans</a> sayfasında duyuracağız.",
        "Birçok dil için açık modeller zaten var. Farkımız ölçülebilir iyileşme ve topluluk sahipliği olmak zorunda.",
    ]))

TR["sss"] = dict(
    title="Sık sorulan sorular · Modelen",
    desc="Modelen hakkında sık sorulan sorular: gönüllülük, ödeme, güvenlik, lisans ve veri.",
    body=phead("SSS", "Sık sorulan sorular.") + """
<details><summary>Yayınlanmış bir modeliniz var mı?</summary><p>Hayır. Araştırma aşamasındayız. İlk modeli yayınlarken ne olduğunu, nasıl ölçüldüğünü ve sınırlarını açıkça yazacağız.</p></details>
<details><summary>Gönüllü olmak için ne gerekiyor?</summary><p>İlk hedef, en az 8 GB belleğe sahip bir NVIDIA ekran kartı. Bu değişebilir. Windows kurulum programı yayında; <a href="katil.html">Katıl sayfasından</a> indirebilirsiniz.</p></details>
<details><summary>Para ya da kripto kazanır mıyım?</summary><p>Başlangıçta hayır. Katkınız şeffaf bir kayıtta tutulur ve modelin yönünde söz hakkınız olur. Para ya da token dağıtmayı planlamıyoruz.</p></details>
<details><summary>Bilgisayarıma zarar verir mi?</summary><p>Yoğun ekran kartı kullanımı elektrik tüketimini, ısıyı ve fan gürültüsünü artırır; donanım ömrüne etkisi olabilir. İstemci bunu sınırlayan ayarlar sunacak. Karar sizde; istediğiniz an durdurabilirsiniz.</p></details>
<details><summary>Kişisel verilerime erişiliyor mu?</summary><p>Tasarım ilkemiz: istemci yalnızca eğitim işini çalıştırır, dosyalarınıza ve kişisel verilerinize erişmez. Yalnızca teknik bilgiler (ör. ekran kartı modeli, bellek, sürüm) paylaşılır. Ayrıntı: <a href="kvkk.html">Aydınlatma Metni</a>.</p></details>
<details><summary>Hangi veriyle eğitiyorsunuz?</summary><p>İlk deneylerde Türkçe Vikipedi'den bir alt küme kullandık. Sonrası için kullanacağımız tüm kaynakları ve lisanslarını yayınlayacağız.</p></details>
<details><summary>Lisans nedir?</summary><p>Kod ve model ağırlıkları için Apache-2.0 hedefliyoruz. Eğitim verisinden doğan lisans gereklilikleri hukuki incelemeden sonra netleşecek. Ayrıntı: <a href="lisans.html">Lisans</a>.</p></details>
<details><summary>Neden sıfırdan model eğitmiyorsunuz?</summary><p>Tek bir tüketici ekran kartında 1 milyar parametreli modeli sıfırdan eğitmek aylar sürer ve belleğe sığmaz. Açık bir tabanı uyarlamak çok daha ucuz ve hızlı. İleride sıfırdan eğitim bir seçenek olabilir.</p></details>
<details><summary>Siz kimsiniz?</summary><p>Modelen Alternatif Eğitim Topluluğu. Ayrıntı: <a href="hakkinda.html">Hakkında</a>.</p></details>
""")


TR["koordinator-ol"] = dict(
    title="Koordinatör ol · Modelen",
    desc="Modelen koordinatörü olmak için sitede kayıt ol ve başvur: onaylanan koordinatörler Koordinatörler sayfasında yayınlanır.",
    legal=True,
    body=phead("Koordinatör ol", "Gönüllülerin GPU'larını kendi projen için kullan.",
               "Sitede kayıt ol, başvur; yöneticiler onaylarsa sayfan Koordinatörler listesinde yayınlanır.")
    + "<h2>Nasıl işliyor?</h2>"
    + steps([("Kayıt ol", "Siteden hesap aç; e-posta ve parola yeterli."),
             ("Başvuruyu doldur", "Proje adını, ne yaptığını anlat. Koordinatör adresi <b>zorunlu değil</b>; sonradan eklenebilir."),
             ("İnceleme", "Yöneticiler başvuruyu kendi panelinde görür; onaylar, reddeder ya da not düşer. Sonucu panelinde görürsün."),
             ("Yayın", "Onaylanınca sayfan <a href=\"/koordinatorler\">Koordinatörler</a> listesinde yayınlanır. Adresin varsa gönüllüler uygulamadan GPU'sunu sana adayabilir.")])
    + """<p class="actions"><a class="btn accent" href="/kayit">Kayıt ol</a> <a class="btn" href="/giris">Giriş yap</a> <a class="btn ghost" href="/koordinatorler">Koordinatörleri gör</a></p>"""
    + """<h2>Koşullar</h2>
<ul>
<li>Gönüllünün bilgisayarında yalnızca Modelen'in yayımladığı eğitim betiği çalışır; koordinatör gönüllüye keyfi kod gönderemez.</li>
<li>Koordinatör adresin varsa HTTPS ile erişilebilir olmalı; ağırlıklar ve sonuçlar güvenli aktarılmalı. Adres zorunlu değildir; adresi olmayan projeler yalnızca sitede görünür.</li>
<li>Neyin, hangi veriyle ve hangi lisansla eğitildiğini açıkça yazmalısın; çıktıların nasıl kullanılacağını önceden belirtmelisin.</li>
<li>Gönüllülerin kişisel verisini toplamazsın; takma ad dışında bilgi istemezsin.</li>
<li>Koşullara aykırılıkta yöneticiler seni listeden çıkarabilir.</li>
</ul>
<p class="note">Dürüst durum: koordinatör yazılımı henüz bir prototip; kimlik doğrulama ve zehirlenme koruması eksik. Bu yüzden liste yalnızca yöneticilerin elle onayladığı kişilerden oluşur. Hesap ve başvuru bilgilerin yalnızca değerlendirme için kullanılır; iletişim e-postan herkese açık değildir. <a href="kvkk.html">Aydınlatma Metni</a></p>""")

TR["topluluk-kurallari"] = dict(
    title="Topluluk kuralları · Modelen",
    desc="Modelen topluluğunda profil, gönderi ve takip için temel kurallar; bildirim ve moderasyon süreci.",
    legal=True,
    body=phead("Topluluk", "Topluluk kuralları", "Burası açık yapay zekâ üzerine birlikte çalışanların alanı. Kısa tutuyoruz.")
    + "<h2>Temel kurallar</h2>"
    + risks(["Birbirimize saygılı davranırız; taciz, nefret söylemi, tehdit ve aşağılama yasaktır.",
             "Spam, toplu reklam ve aldatıcı bağlantılar yasaktır.",
             "Başkasının kişisel verisini (telefon, adres, kimlik, özel yazışma) izinsiz paylaşmayız.",
             "Yasa dışı içerik, telif hakkını ihlal eden içerik ve zararlı yazılım bağlantıları paylaşmayız.",
             "Yanıltıcı bilgiyi bilerek yaymayız; model sonuçlarını olduğundan iyi göstermeyiz.",
             "Profilinizde ve gönderilerinizde yalnızca paylaşma hakkınız olan görselleri kullanırsınız."])
    + "<h2>Gizlilik</h2><p>Profiliniz varsayılan olarak gizlidir; siz açana kadar kimse göremez. E-posta adresiniz hiçbir sayfada gösterilmez. Bir kullanıcıyı engelleyebilirsiniz; engellenen kişi sizi göremez ve takip edemez.</p>"
    + "<h2>Bildirim ve moderasyon</h2><p>Kurallara aykırı bir gönderi ya da profili \"Bildir\" düğmesiyle bildirebilirsiniz. Yöneticiler bildirimi inceler; gönderiyi gizleyebilir, profili gizleyebilir ya da paylaşımı kısıtlayabilir. Kararlara itiraz için %%EPOSTA%% adresine yazabilirsiniz. Yasal bildirimler (ör. hak ihlali) aynı adrese yapılır; makul sürede incelenir.</p>"
    + '<p class="note"><a href="/akis">Akışa dön</a></p>')

TR["katil"] = dict(
    title="Katıl · Modelen",
    desc="Modelen'e gönüllü ya da katkıcı olarak katılmak için bilgi: Windows kurulum programını indirin; gereksinimler, kurulum ve dürüst durum.",
    body=phead("Katıl", "GPU'nuzu açık modellere adayın.",
               "Kurulum programı yayında. Gerisini o halleder.")
    + """<div class="indir">
<div class="indir-os">
<div class="indir-ana">
<span class="indir-et">Windows 10/11 · 64 bit</span>
<h2>Windows</h2>
<p>Tek dosya, çift tıklayın. Python, PyTorch ve taban modeli kurulum programı sizin yerinize kurar; yönetici yetkisi gerekmez.</p>
<a class="btn accent big" href="https://github.com/macbyclp/modelen-tr/releases/latest/download/Modelen-Kurulum.exe"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" focusable="false"><path d="M3 5.5l7.6-1.1v7H3zM11.6 4.3L21 3v8.4h-9.4zM3 12.6h7.6v7L3 18.5zM11.6 12.6H21V21l-9.4-1.3z"/></svg> İndir</a>
<p class="indir-alt">Modelen-Kurulum.exe · kendisi küçüktür; kurulum sırasında birkaç GB indirir<br><a href="https://github.com/macbyclp/modelen-tr/releases/latest" rel="noopener">SHA-256 ile doğrula</a> · <a href="https://docs.modelen.tr/gonullu-kurulumu/" rel="noopener">Kurulum rehberi</a></p>
</div>
<div class="indir-ana">
<span class="indir-et">Ubuntu / Linux · x86_64</span>
<h2>Linux</h2>
<p>Tek betik. Python, PyTorch ve taban modeli kurar; sudo gerekmez. Grafik arayüz yoktur, işçi komut satırından çalışır.</p>
<a class="btn accent big" href="https://github.com/macbyclp/modelen-tr/releases/latest/download/kur.sh"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" focusable="false"><path d="M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm2.6 4.2L5.5 9.3 8.2 12l-2.7 2.7 1.1 1.1L10.4 12zM11.5 15h6v-1.6h-6z"/></svg> kur.sh</a>
<p class="indir-alt"><code>bash kur.sh</code> ile çalıştırın · <code>--dene</code> hiçbir şey kurmaz<br><a href="https://github.com/macbyclp/modelen-tr/releases/latest" rel="noopener">SHA-256 ile doğrula</a> · <a href="https://docs.modelen.tr/gonullu-kurulumu/#ubuntu-linux" rel="noopener">Kurulum rehberi</a></p>
</div>
</div>
<ol class="indir-adim">
<li><b>İndirin ve çalıştırın.</b> Windows: çift tıklayın; SmartScreen uyarırsa "Daha fazla bilgi", sonra "Yine de çalıştır" deyin (program henüz imzalı değil). Linux: <code>bash kur.sh</code>.</li>
<li><b>Kurulumu bekleyin.</b> Süre, internet hızınıza bağlıdır.</li>
<li><b>Başlatın.</b> Windows: Modelen'i açıp bir koordinatör seçin ve AÇIK'a basın. Linux: <code>modelen-isci --koordinator &lt;adres&gt; --isci &lt;takma ad&gt;</code>.</li>
</ol>
</div>
<p class="indir-mac"><b>macOS:</b> şimdilik desteklenmiyor (Mac'lerde NVIDIA ekran kartı yok).</p>
<p class="note"><b>Dürüst durum:</b> Modelen araştırma aşamasındadır. Şu an dizinde onaylı bir koordinatör yok; ilk koordinatörler katıldığında <a href="koordinatorler.html">Koordinatörler</a> sayfasında listelenecek ve uygulamadan seçilebilecek. Kurulumu şimdi yapabilir, hazır olduğunda katkı verebilirsiniz.</p>
<div class="cards2">
<div><h3>Gereksinimler</h3><ul>
<li>NVIDIA ekran kartı (en az 6 GB bellek; 8 GB ile denendi) ve güncel sürücü.</li>
<li>Yaklaşık 8 GB boş disk ve internet.</li>
<li>18 yaşından küçükler için veli ya da vasi onayı.</li>
<li>Para ya da kripto ödülü yok; katkı kaydı ve söz hakkı var.</li></ul></div>
<div><h3>Kurulum hakkında</h3><ul>
<li>Her şey tek klasöre kurulur (<code>%LOCALAPPDATA%\\Modelen</code>); silerek kaldırılır.</li>
<li>Eğitim sizin kartınızda yapılır; ağdan yalnızca küçük bir adaptör (~40 MB) geçer.</li>
<li>Kaynak kod <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub'da</a> açıktır.</li></ul></div>
<div><h3>Başka nasıl katılırım?</h3><ul>
<li><a href="koordinator-ol.html">Koordinatör olun</a>: kendi topluluğunuzla, seçtiğiniz veriyle eğitim çalıştırın.</li>
<li>Kod, dil kıyas testleri (önce Türkçe), veri değerlendirmesi, hukuki ve güvenlik incelemesi: <a href="katki-sartlari.html">Katkı şartları</a>.</li></ul></div></div>
<p class="note">Haber almak için <a href="mailto:%%EPOSTA%%?subject=Gönüllü%20ilgisi">%%EPOSTA%%</a> adresine yazın; e-postanızı yalnızca Modelen duyuruları için kullanırız. <a href="kvkk.html">Aydınlatma Metni</a> · <a href="gonullu-sartlari.html">Gönüllü şartları</a></p>""")

TR["hakkinda"] = dict(
    title="Hakkında · Modelen",
    desc="Modelen Alternatif Eğitim Topluluğu hakkında: misyon, ilkeler ve topluluk bilgileri.",
    body=phead("Hakkında", "Açık, topluluk sahipli yapay zekâ.",
               "Verinizi üçüncü taraf servislere göndermek zorunda kalmadan kullanabileceğiniz, şeffaf biçimde eğitilmiş açık modeller.")
    + "<h2>İlkelerimiz</h2>"
    + kv([("Şeffaflık", "Ne ölçtüğümüzü ve ne ölçemediğimizi yayınlarız."),
          ("Açıklık", "Kod ve ağırlıklar açık lisansla yayınlanır."),
          ("Topluluk sahipliği", "Katkılar kayıt altındadır, kararlar açık yürütülür."),
          ("Gizlilik", "Gönüllü cihazlarındaki kişisel verilere erişmeyiz."),
          ("Abartmamak", "Sonuçlarımızı kanıtladığımız kadar söyleriz.")])
    + """<h2>Topluluk bilgileri</h2>
<table>
<tr><th>Unvan</th><td>Modelen Alternatif Eğitim Topluluğu</td></tr>
<tr><th>Alan adı</th><td>modelen.tr</td></tr>
<tr><th>İletişim</th><td>%%EPOSTA%%</td></tr>
</table>
""")

TR["iletisim"] = dict(
    title="İletişim · Modelen",
    desc="Modelen ile iletişim: genel sorular, gönüllülük, basın ve kişisel veri başvuruları için tek e-posta adresi.",
    body=phead("İletişim", "Tek adres.")
    + '<a class="bigmail" href="mailto:%%EPOSTA%%">%%EPOSTA%%</a>'
    + kv([("Genel, gönüllülük, basın", "Konu satırına konunuzu yazın."),
          ("KVKK başvurusu", 'Konu satırına "KVKK Başvurusu" yazın. Ayrıntı: <a href="kvkk.html">Aydınlatma Metni</a>.'),
          ("Güvenlik bildirimi", 'Konu satırına "Güvenlik" yazın. Sorumlu bildirimlere teşekkür ederiz; ayrıntı <code>/.well-known/security.txt</code> dosyasında.')]))

TR["olcumler"] = dict(
    title="Ölçümler · Modelen",
    desc="Modelen'in şimdiye kadarki tüm deneyleri: seyrek senkronizasyon, Türkçe uyarlama ve adaptör ölçeğinde DiLoCo. Tablolar ve sınırlar.",
    body=phead("Ölçümler", "Ne ölçtük, ne ölçemedik.",
               "Hepsi küçük, tek donanımlı denemeler. Her tablonun altında sınırını yazıyoruz.")
    + table(["Deney", "Sorumuz", "Sonuç", "Durum"], [
        ["1 · Seyrek senkronizasyon (oyuncak model)", "Seyrek senkron kaybı ne kadar artırır?", "+0,07 ile +0,23 nat (veriye ve H'ye göre)", "tamamlandı · küçük ölçek"],
        ["2 · Qwen3-0.6B Türkçe uyarlama", "20 dakikalık LoRA Türkçeyi iyileştirir mi?", "Dil modelleme −%4,3; kıyas testi değişmedi", "tamamlandı · tek koşu"],
        ["3 · Adaptör-DiLoCo", "Adaptörde seyrek senkronizasyonun bedeli?", "Fark %0,09; ~25× az veri", "tamamlandı · simülasyon"],
    ], num_from=9)
    + '<p class="cap2">Ham çıktılar ve betikler <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub deposunda</a> (Apache-2.0).</p>'
    + """<h2>1 · Seyrek senkronizasyon, oyuncak model <span class="tag">DiLoCo</span></h2>
<p>3,3M parametreli bayt düzeyinde bir GPT, 4 sanal işçi, işçi başına 500 adım, 3 tohum, dış optimizer lr 1,0 / momentum 0,5. İki veriyle denedik: küçük bir yerel Türkçe metin (256 KB) ve Türkçe Vikipedi'nin ilk 3280 makalesi (30 MB). Değerler, referans eğitime (her adımda senkron) göre doğrulama kaybı farkıdır (nat; düşük iyi).</p>"""
    + table(["H (iki senkron arası adım)", "Senkron sayısı", "Yerel metin: fark", "Vikipedi: fark"], [
        ["10", "50", "+0,067", "+0,126"], ["25", "20", "+0,107", "+0,112"],
        ["50", "10", "+0,161", "+0,168"], ["100", "5", "+0,226", "+0,156"],
    ])
    + '<p class="cap2">Referans kayıp: yerel metinde 1,532, Vikipedi\'de 1,919.</p>'
    + '<p class="note">Sınır: küçük model, dış optimizer yalnızca H=25\'te ayarlandı. Vikipedi\'de H\'nin etkisi tohum gürültüsüyle aynı büyüklükte; "H büyüdükçe düzenli kötüleşir" demiyoruz. 12 ayarlık dış optimizer taraması daha iyi bir nokta bulmadı.</p>'
    + """<h2>2 · Qwen3-0.6B Türkçe uyarlama <span class="tag">LoRA</span></h2>
<p>Qwen3-0.6B-Base, LoRA r=16 (tüm doğrusal katmanlar), 215 adım ≈ 1,76M token, RTX 4060 Laptop (8 GB), adım başına ≈ 5,6 sn, tepe bellek 5,23 GB, adaptör 40,4 MB. Türkçe değerlendirme, eğitimde kullanılmayan bir Vikipedi parçasından.</p>"""
    + table(["Ölçüt", "Taban", "LoRA sonrası"], [
        ["Türkçe bayt başına bit", "1,297", "1,241"], ["Türkçe perplexity", "15,22", "13,52"],
        ["İngilizce bayt başına bit (WikiText-2)", "0,9468", "0,9597"],
        ["TurkishMMLU 5-shot", "%35,6 (320/900)", "%34,7 (312/900)"], ["Kelime başına token", "2,78", "2,78"],
    ])
    + '<p class="note">Okuma: Türkçe dil modelleme iyileşti, İngilizcede hafif kayıp var, TurkishMMLU\'da fark 8 soru ve 900 soruluk testin standart hatası (≈ 1,6 puan) içinde. "Model iyileşti" diyemiyoruz. Sınır: tek koşu; değerlendirme metni eğitimle aynı alandan.</p>'
    + """<h2>3 · Adaptör-DiLoCo <span class="tag">simülasyon</span></h2>
<p>Qwen3-0.6B + LoRA, 4 sanal işçi (taban paylaşılan ve dondurulmuş), 8 tur × 25 yerel adım. Baseline: aynı toplam işlem, her adımda senkron. Ölçü: Türkçe bayt başına bit, 60 bin tokenlik ayrılmış parça.</p>"""
    + table(["Tur", "Baseline", "Adaptör-DiLoCo"], [
        ["0", "1,2714", "1,2714"], ["2", "1,2390", "1,2395"], ["4", "1,2238", "1,2275"],
        ["6", "1,2184", "1,2201"], ["8", "1,2155", "1,2166"],
    ])
    + '<p class="cap2">Son fark 0,0011 (%0,09); baseline kazancının ≈ %98\'i. İletişim (hesap): baseline 200 adım × 4 işçi × 40,4 MB ≈ 32 GB, DiLoCo 8 tur ≈ 1,3 GB. Tepe bellek 5,64 GB.</p>'
    + '<p class="note">Sınır: tek tohum, küçük ölçüm parçası, veri dilimleri aynı akıştan (gerçek gönüllülerde farklı olur), ağ gecikmesi, işçi kaybı ve kötü niyetli katkı yok, dış optimizer bu model için ayarlanmadı, DiLoCo sonrası standart eğitimle uyum sınanmadı.</p>')

# ---------------------------------------------------------------- ENGLISH
EN = {}

EN["nasil-calisir"] = dict(
    title="How it works · Modelen",
    desc="How distributed training on volunteer GPUs will work at Modelen: open base, LoRA adapter, sparse synchronisation and verification.",
    body=phead("How it works", "Not from scratch. From an open base.",
               "Instead of training a model from the ground up, we train a small part that learns a new language (Turkish first) and split that part across volunteer computers.")
    + """<div class="flow" aria-label="Flow">
<div class="box">Base model<small>frozen · ≈ 1.2 GB</small></div><span>+</span>
<div class="box hot">LoRA adapter<small>trained · ≈ 40 MB</small></div><span>→</span>
<div class="box">Volunteers<small>each on its own data slice</small></div><span>→</span>
<div class="box hot">Merge<small>every 25 steps</small></div></div>"""
    + steps([
        ("We start from an open base",
         "We take a suitably licensed model; in our first experiment Qwen3-0.6B-Base (Apache-2.0). Training from scratch takes months on one graphics card and does not fit in 8 GB of memory."),
        ("We train only a small adapter",
         "With LoRA the base stays frozen. In our experiment the adapter was ≈ 40 MB and peak memory 5.2 GB. That fits on a laptop graphics card."),
        ("We merge updates sparsely",
         "Each volunteer works on its own data slice for a while; only adapter differences are collected (DiLoCo). In our simulation about 25 times less data moved."),
        ("We verify contributions",
         "Faulty or malicious updates can arrive. Our plan: verify the same work on several machines, check update size and consistency, and add small known test tasks. These mechanisms are still under development."),
    ])
    + """<h2>What happens on your computer</h2>
<ul>
<li>The client is open source; you can read what it runs.</li>
<li>Signed updates are our goal; for now releases can be verified with a SHA-256 digest and build-provenance attestation.</li>
<li>The client runs only the training job and does not access your files or personal data. This is a design principle; you can verify it by reading the code on <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub</a>.</li>
<li>You can stop at any time.</li>
</ul>
<h2>What we don't know</h2>
<p class="note">We have not measured how results change at 1 billion parameters and above, over real internet conditions, with different data slices, and with volunteer dropout and malicious contributions. Our measurements so far are on the <a href="measurements.html">Measurements</a> page.</p>""")

EN["yol-haritasi"] = dict(
    title="Roadmap · Modelen",
    desc="Modelen roadmap: research, first-language adaptation, volunteer client, pilot and open network. No date commitments.",
    body=phead("Roadmap", "We write the stages, not the dates.",
               "When a stage ends we will publish what we measured together with what we could not find.")
    + stages([
        ("done", "00 · DONE", "Research", "Sparse synchronisation on a small model and an adapter-scale DiLoCo simulation."),
        ("done", "01 · FIRST EXPERIMENT", "First language: Turkish", "Short continued pre-training with LoRA on Qwen3-0.6B-Base on 8 GB."),
        ("", "02 · NEXT", "Data and evaluation", "More Turkish data, English replay mix, tokenizer, a 1.7B base."),
        ("", "03 · LIVE (ALPHA)", "Volunteer client", "Open source; Windows and Ubuntu. Next: signed updates, contribution verification."),
        ("", "04", "Closed pilot", "Training over a real network with a small group of volunteers."),
        ("", "05", "Open network and first release", "Weights, code and list of data sources under Apache-2.0 / applicable licences."),
    ])
    + "<h2>Known risks</h2>"
    + risks([
        "Research suggests weights trained with sparse synchronisation may not combine well with later standard training. We will test this ourselves.",
        "Training-data licences (e.g. CC BY-SA data) need legal review for the weights we release. We will announce the outcome on the <a href=\"license.html\">Licence</a> page.",
        "Open models already exist for many languages. Our difference has to be measurable improvement and community ownership.",
    ]))

EN["sss"] = dict(
    title="FAQ · Modelen",
    desc="Frequently asked questions about Modelen: volunteering, payment, security, licence and data.",
    body=phead("FAQ", "Frequently asked questions.") + """
<details><summary>Do you have a released model?</summary><p>No. We are at the research stage. When we release a first model we will state clearly what it is, how it was measured and its limits.</p></details>
<details><summary>What do I need to volunteer?</summary><p>The initial target is an NVIDIA graphics card with at least 8 GB of memory. This may change. The Windows installer is available; download it from the <a href="join.html">Join page</a>.</p></details>
<details><summary>Will I earn money or crypto?</summary><p>Not to begin with. Your contribution is kept in a transparent record and you get a say in the model's direction. We do not plan to distribute money or tokens.</p></details>
<details><summary>Can it harm my computer?</summary><p>Heavy graphics-card use increases power draw, heat and fan noise and may affect hardware lifespan. The client will offer settings to limit this. The decision is yours and you can stop at any time.</p></details>
<details><summary>Does it access my personal data?</summary><p>Our design principle: the client runs only the training job and does not access your files or personal data. Only technical information (e.g. graphics card model, memory, version) is shared. Details: <a href="kvkk-notice.html">Data Notice</a>.</p></details>
<details><summary>What data do you train on?</summary><p>In early experiments we used a subset of Turkish Wikipedia. For later work we will publish all sources and their licences.</p></details>
<details><summary>What is the licence?</summary><p>We aim for Apache-2.0 for code and model weights. Licence requirements arising from training data will be settled after legal review. See <a href="license.html">Licence</a>.</p></details>
<details><summary>Why don't you train from scratch?</summary><p>Training a 1-billion-parameter model from scratch on one consumer graphics card takes months and does not fit in memory. Adapting an open base is much cheaper and faster. Training from scratch may become an option later.</p></details>
<details><summary>Who are you?</summary><p>Modelen Alternatif Eğitim Topluluğu. See <a href="about.html">About</a>.</p></details>
""")


EN["koordinator-ol"] = dict(
    title="Become a coordinator · Modelen",
    desc="Apply to become a Modelen coordinator: register on the site and apply; approved coordinators are published on the Coordinators page.",
    legal=True,
    body=phead("Become a coordinator", "Use volunteers' GPUs for your own project.",
               "Register on the site and apply; if the admins approve, your page is published in the Coordinators list.")
    + "<h2>How it works</h2>"
    + steps([("Register", "Create an account on the site; email and password are enough."),
             ("Fill in the application", "Describe your project and what you do. A coordinator address is <b>not required</b>; it can be added later."),
             ("Review", "Admins see the application in their own panel and approve, reject or leave a note. You see the result in your panel."),
             ("Published", "Once approved, your page appears in the <a href=\"/koordinatorler\">Coordinators</a> list. If you have an address, volunteers can dedicate their GPUs to you from the app.")])
    + """<p class="actions"><a class="btn accent" href="/kayit">Register</a> <a class="btn" href="/giris">Sign in</a> <a class="btn ghost" href="/koordinatorler">See coordinators</a></p><p class="note">The portal interface is currently in Turkish only.</p>"""
    + """<h2>Terms</h2>
<ul>
<li>Only the training script published by Modelen runs on a volunteer's computer; a coordinator cannot send arbitrary code to volunteers.</li>
<li>If you have a coordinator address it must be reachable over HTTPS; weights and results must be transferred securely. The address is optional; projects without one appear on the site only.</li>
<li>You must state clearly what is trained, on which data and under which licence, and how the outputs will be used.</li>
<li>You do not collect volunteers' personal data; you ask for nothing beyond a nickname.</li>
<li>On breach of the terms, admins may remove you from the list.</li>
</ul>
<p class="note">Honest status: the coordinator software is still a prototype; authentication and poisoning protection are missing. That is why the list consists only of people the admins approve by hand. Your account and application details are used only for review; your contact email is not public. <a href="kvkk-notice.html">Data Notice</a></p>""")

EN["topluluk-kurallari"] = dict(
    title="Community rules · Modelen",
    desc="Basic rules for profiles, posts and follows in the Modelen community; reporting and moderation.",
    legal=True,
    body=phead("Community", "Community rules", "This is a place for people working together on open AI. We keep it short.")
    + "<h2>Basic rules</h2>"
    + risks(["We treat each other respectfully; harassment, hate speech, threats and belittling are not allowed.",
             "Spam, bulk advertising and deceptive links are not allowed.",
             "We do not share anyone else's personal data (phone, address, ID, private messages) without permission.",
             "We do not share illegal content, copyright-infringing content or links to malware.",
             "We do not knowingly spread misleading information or present model results as better than they are.",
             "In your profile and posts you use only images you have the right to share."])
    + "<h2>Privacy</h2><p>Your profile is private by default; nobody can see it until you open it. Your email address is never shown. You can block a user; a blocked person cannot see or follow you.</p>"
    + "<h2>Reporting and moderation</h2><p>You can report a post or profile that breaks the rules with the \"Report\" button. Admins review reports and may hide a post, hide a profile or restrict posting. To appeal a decision, write to %%EPOSTA%%. Legal notices (e.g. rights infringement) go to the same address and are reviewed within a reasonable time.</p>"
    + '<p class="note"><a href="/akis">Back to the feed</a></p>')

EN["katil"] = dict(
    title="Join · Modelen",
    desc="How to join Modelen as a volunteer or contributor: download the Windows installer; requirements, setup and honest status.",
    body=phead("Join", "Lend your GPU to open models.",
               "The installer is available. It takes care of the rest.")
    + """<div class="indir">
<div class="indir-os">
<div class="indir-ana">
<span class="indir-et">Windows 10/11 · 64-bit</span>
<h2>Windows</h2>
<p>One file, double-click. It installs Python, PyTorch and the base model for you; no administrator rights needed.</p>
<a class="btn accent big" href="https://github.com/macbyclp/modelen-tr/releases/latest/download/Modelen-Kurulum.exe"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" focusable="false"><path d="M3 5.5l7.6-1.1v7H3zM11.6 4.3L21 3v8.4h-9.4zM3 12.6h7.6v7L3 18.5zM11.6 12.6H21V21l-9.4-1.3z"/></svg> Download</a>
<p class="indir-alt">Modelen-Kurulum.exe · the file itself is small; setup downloads a few GB<br><a href="https://github.com/macbyclp/modelen-tr/releases/latest" rel="noopener">Verify with SHA-256</a> · <a href="https://docs.modelen.tr/en/gonullu-kurulumu/" rel="noopener">Setup guide</a></p>
</div>
<div class="indir-ana">
<span class="indir-et">Ubuntu / Linux · x86_64</span>
<h2>Linux</h2>
<p>One script. It installs Python, PyTorch and the base model; no sudo needed. There is no graphical app; the worker runs from the command line.</p>
<a class="btn accent big" href="https://github.com/macbyclp/modelen-tr/releases/latest/download/kur.sh"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" focusable="false"><path d="M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm2.6 4.2L5.5 9.3 8.2 12l-2.7 2.7 1.1 1.1L10.4 12zM11.5 15h6v-1.6h-6z"/></svg> kur.sh</a>
<p class="indir-alt">Run with <code>bash kur.sh</code> · <code>--dene</code> installs nothing<br><a href="https://github.com/macbyclp/modelen-tr/releases/latest" rel="noopener">Verify with SHA-256</a> · <a href="https://docs.modelen.tr/en/gonullu-kurulumu/#ubuntu-linux" rel="noopener">Setup guide</a></p>
</div>
</div>
<ol class="indir-adim">
<li><b>Download and run it.</b> Windows: double-click; if SmartScreen warns, choose "More info", then "Run anyway" (the program is not signed yet). Linux: <code>bash kur.sh</code>.</li>
<li><b>Wait for setup.</b> The time depends on your internet speed.</li>
<li><b>Start.</b> Windows: open Modelen, pick a coordinator and press ON. Linux: <code>modelen-isci --koordinator &lt;address&gt; --isci &lt;pseudonym&gt;</code>.</li>
</ol>
</div>
<p class="indir-mac"><b>macOS:</b> not supported yet (Macs have no NVIDIA graphics cards).</p>
<p class="note"><b>Honest status:</b> Modelen is at the research stage. There is no approved coordinator in the directory yet; once the first coordinators join they will be listed on the <a href="koordinatorler.html">Coordinators</a> page and selectable from the app. You can install now and contribute when one is ready.</p>
<div class="cards2">
<div><h3>Requirements</h3><ul>
<li>An NVIDIA graphics card (at least 6&nbsp;GB of memory; tested with 8&nbsp;GB) and a current driver.</li>
<li>About 8&nbsp;GB of free disk and internet.</li>
<li>For under-18s, parental or guardian consent.</li>
<li>No money or crypto reward; there is a contribution record and a say in direction.</li></ul></div>
<div><h3>About the installer</h3><ul>
<li>Everything is installed in one folder (<code>%LOCALAPPDATA%\\Modelen</code>) and removed by deleting it.</li>
<li>Training happens on your card; only a small adapter (~40&nbsp;MB) crosses the network.</li>
<li>The source is open on <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub</a>.</li></ul></div>
<div><h3>Other ways to join</h3><ul>
<li><a href="become-coordinator.html">Become a coordinator</a>: run training with your own community and the data you choose.</li>
<li>Code, language benchmarks (Turkish first), data evaluation, legal and security review: <a href="contributing.html">Contribution terms</a>.</li></ul></div></div>
<p class="note">To stay informed, write to <a href="mailto:%%EPOSTA%%?subject=Volunteer%20interest">%%EPOSTA%%</a>; we use your email only for Modelen announcements. <a href="kvkk-notice.html">KVKK notice</a> · <a href="volunteer-terms.html">Volunteer terms</a></p>""")

EN["hakkinda"] = dict(
    title="About · Modelen",
    desc="About Modelen Alternatif Eğitim Topluluğu: mission, principles and community information.",
    body=phead("About", "Open, community-owned AI.",
               "Openly and transparently trained models you can use without sending your data to third-party services.")
    + "<h2>Our principles</h2>"
    + kv([("Transparency", "We publish what we measured and what we could not measure."),
          ("Openness", "Code and weights are released under open licences."),
          ("Community ownership", "Contributions are on record and decisions are made in the open."),
          ("Privacy", "We do not access personal data on volunteers' devices."),
          ("No overclaiming", "We say only as much as we have proven.")])
    + """<h2>Community information</h2>
<table>
<tr><th>Name</th><td>Modelen Alternatif Eğitim Topluluğu</td></tr>
<tr><th>Domain</th><td>modelen.tr</td></tr>
<tr><th>Contact</th><td>%%EPOSTA%%</td></tr>
</table>
""")

EN["iletisim"] = dict(
    title="Contact · Modelen",
    desc="Contact Modelen: general questions, volunteering, press and personal-data requests via one email address.",
    body=phead("Contact", "One address.")
    + '<a class="bigmail" href="mailto:%%EPOSTA%%">%%EPOSTA%%</a>'
    + kv([("General, volunteering, press", "Put your topic in the subject line."),
          ("KVKK request", 'Use "KVKK Request" as the subject. See the <a href="kvkk-notice.html">Data Notice</a>.'),
          ("Security report", 'Use "Security" as the subject. We thank you for responsible disclosure; details are in <code>/.well-known/security.txt</code>.')]))

EN["olcumler"] = dict(
    title="Measurements · Modelen",
    desc="Every Modelen experiment so far: sparse synchronisation, Turkish adaptation and adapter-scale DiLoCo. Tables and limits.",
    body=phead("Measurements", "What we measured, what we could not.",
               "All small, single-hardware experiments. Under every table we write its limit.")
    + table(["Experiment", "Our question", "Result", "Status"], [
        ["1 · Sparse synchronisation (toy model)", "How much does sparse sync raise the loss?", "+0.07 to +0.23 nat (by data and H)", "done · small scale"],
        ["2 · Qwen3-0.6B Turkish adaptation", "Does 20 minutes of LoRA improve Turkish?", "Language modelling −4.3%; benchmark unchanged", "done · single run"],
        ["3 · Adapter DiLoCo", "What does sparse sync cost on an adapter?", "0.09% gap; ~25× less data", "done · simulation"],
    ], num_from=9)
    + '<p class="cap2">Raw outputs and scripts are in the <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub repository</a> (Apache-2.0).</p>'
    + """<h2>1 · Sparse synchronisation, toy model <span class="tag">DiLoCo</span></h2>
<p>A byte-level GPT with 3.3M parameters, 4 simulated workers, 500 steps per worker, 3 seeds, outer optimiser lr 1.0 / momentum 0.5. We tried two datasets: a small local Turkish text (256 KB) and the first 3,280 articles of Turkish Wikipedia (30 MB). Values are the validation-loss gap to the reference run (synchronised every step), in nats; lower is better.</p>"""
    + table(["H (steps between syncs)", "Number of syncs", "Local text: gap", "Wikipedia: gap"], [
        ["10", "50", "+0.067", "+0.126"], ["25", "20", "+0.107", "+0.112"],
        ["50", "10", "+0.161", "+0.168"], ["100", "5", "+0.226", "+0.156"],
    ])
    + '<p class="cap2">Reference loss: 1.532 on the local text, 1.919 on Wikipedia.</p>'
    + '<p class="note">Limit: small model; the outer optimiser was tuned only at H=25. On Wikipedia the effect of H is the same size as seed noise, so we do not claim "it gets steadily worse as H grows". A 12-setting outer-optimiser sweep found no better point.</p>'
    + """<h2>2 · Qwen3-0.6B Turkish adaptation <span class="tag">LoRA</span></h2>
<p>Qwen3-0.6B-Base, LoRA r=16 (all linear layers), 215 steps ≈ 1.76M tokens, RTX 4060 Laptop (8 GB), ≈ 5.6 s per step, peak memory 5.23 GB, adapter 40.4 MB. Turkish evaluation is on a Wikipedia slice not used in training.</p>"""
    + table(["Metric", "Base", "After LoRA"], [
        ["Turkish bits per byte", "1.297", "1.241"], ["Turkish perplexity", "15.22", "13.52"],
        ["English bits per byte (WikiText-2)", "0.9468", "0.9597"],
        ["TurkishMMLU 5-shot", "35.6% (320/900)", "34.7% (312/900)"], ["Tokens per word", "2.78", "2.78"],
    ])
    + '<p class="note">Reading: Turkish language modelling improved, English shows a slight loss, and the TurkishMMLU difference is 8 questions, within the standard error (≈ 1.6 points) of a 900-question test. We cannot say "the model improved". Limit: single run; the evaluation text is from the same domain as training.</p>'
    + """<h2>3 · Adapter DiLoCo <span class="tag">simulation</span></h2>
<p>Qwen3-0.6B + LoRA, 4 simulated workers (base shared and frozen), 8 rounds × 25 local steps. Baseline: same total compute, synchronised every step. Metric: Turkish bits per byte on a 60k-token held-out slice.</p>"""
    + table(["Round", "Baseline", "Adapter DiLoCo"], [
        ["0", "1.2714", "1.2714"], ["2", "1.2390", "1.2395"], ["4", "1.2238", "1.2275"],
        ["6", "1.2184", "1.2201"], ["8", "1.2155", "1.2166"],
    ])
    + '<p class="cap2">Final gap 0.0011 (0.09%); ≈ 98% of the baseline gain. Communication (computed): baseline 200 steps × 4 workers × 40.4 MB ≈ 32 GB, DiLoCo 8 rounds ≈ 1.3 GB. Peak memory 5.64 GB.</p>'
    + '<p class="note">Limit: single seed, small held-out slice, data slices from the same stream (real volunteers will differ), no network latency, worker loss or malicious contributions, outer optimiser not tuned for this model, compatibility with later standard training not tested.</p>')
