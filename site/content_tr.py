# -*- coding: utf-8 -*-
"""Türkçe içerik. %%ANAHTAR%% biçimli yer tutucular build.py tarafından doldurulur."""

PAGES = {}

PAGES["index"] = dict(
    title="Modelen · Topluluğun birlikte eğittiği açık yapay zekâ",
    desc="Modelen, açık yapay zekâ modellerini gönüllülerin GPU'larıyla birlikte eğitmeyi hedefleyen bir girişimdir. İlk dilimiz Türkçe, hedefimiz herkesin dili. Araştırma aşamasındayız.",
    body="""
<section class="hero prose">
  <p><span class="status">Araştırma aşaması · henüz yayınlanmış model yok</span></p>
  <h1>Topluluğun birlikte eğittiği açık yapay zekâ.</h1>
  <p class="lead">Modelen, dünyanın her yerinden geliştiriciler ve kurumlar için açık lisanslı, yerelde çalışabilen dil modelleri geliştirir. Hedefimiz bu modelleri tek bir kurumun sunucu salonunda değil, gönüllülerin boştaki GPU'larında birlikte eğitmek. İlk dilimiz Türkçe; diğer diller sırada.</p>
  <div class="actions">
    <a class="btn" href="katil.html">Gönüllü olmak istiyorum</a>
    <a class="btn ghost" href="nasil-calisir.html">Nasıl çalışır?</a>
  </div>
</section>

<div class="grid">
  <div class="card"><h3>Açık</h3><p>Kod ve model ağırlıkları Apache-2.0 lisansıyla yayınlanacak. Eğitim verisi kaynakları ve lisansları açıkça listelenecek.</p></div>
  <div class="card"><h3>Dil odaklı</h3><p>Her dilin yapısı genel modellerde hem başarıyı hem maliyeti etkiliyor. Dilleri tek tek ölçerek geliştiriyoruz; pilot dilimiz Türkçe.</p></div>
  <div class="card"><h3>Topluluk sahipliği</h3><p>Katkılar şeffaf bir kayıtta tutulur. Başlangıçta para ya da kripto ödülü yok; katkı kaydı ve söz hakkı var.</p></div>
  <div class="card"><h3>Gizliliğe saygılı</h3><p>Gönüllü istemcisi yalnızca eğitim işini çalıştırır; kişisel dosyalarınıza ya da verilerinize erişmez. Tasarım ilkesi budur ve istemci açık kaynak olacak.</p></div>
</div>

<div class="prose">
<h2>Şu an neredeyiz?</h2>
<p>Dürüst olalım: Modelen erken bir araştırma projesidir. Henüz kamuya açık bir modelimiz ya da gönüllü istemcimiz yok. Şunları yaptık:</p>
<ul>
  <li>Gönüllü ağlarda kullanılan seyrek senkronizasyonlu (DiLoCo türü) eğitimin küçük ölçekte bir simülasyonunu çalıştırdık.</li>
  <li>Açık bir taban modeli (Qwen3-0.6B-Base, Apache-2.0) Türkçe metinle uyarlamayı ve bunu 8 GB'lık tüketici GPU'sunda yapmayı denedik.</li>
  <li>Sonuçlarımız umut verici ama sınırlı: tek koşular, küçük veri, gerçek ağ yok. Ayrıntılar için <a href="yol-haritasi.html">yol haritasına</a> bakın.</li>
</ul>
<p>Bu sayfada ileride yayınlayacağımız şeyler için söz vermiyoruz; yayınladığımız şeyleri gösteriyoruz.</p>

<h2>Kimler için?</h2>
<p>Kendi dilinde açık model arayan geliştiriciler, araştırmacılar ve kurumlar (ilk olarak Türkçe). Hedef ürün biçimi, yerelde çalıştırılabilen modeller ve bir API.</p>
</div>
""")

PAGES["nasil-calisir"] = dict(
    title="Nasıl çalışır? · Modelen",
    desc="Gönüllü GPU'larla dağıtık model eğitiminin Modelen'de nasıl çalışacağı: seyrek senkronizasyon, LoRA adaptörleri ve doğrulama.",
    body="""
<div class="prose">
<h1>Nasıl çalışır?</h1>
<p class="lead">Kısa anlatım: büyük bir modeli sıfırdan eğitmek yerine, açık bir tabanı bir dile uyarlıyoruz (ilk denememiz Türkçe) ve bu uyarlamayı birçok gönüllü bilgisayara bölüyoruz.</p>

<h2>1. Açık bir tabandan başlıyoruz</h2>
<p>Sıfırdan eğitim, tek bir GPU ile aylar sürer. Bunun yerine lisansı uygun açık bir taban modeli (ilk deneylerimizde Qwen3-0.6B-Base, Apache-2.0) alıp hedef dildeki metinle sürekli ön eğitim uyguluyoruz (ilk koşumuz Türkçe metinle).</p>

<h2>2. Yalnızca küçük bir parçayı eğitiyoruz</h2>
<p>LoRA yöntemiyle taban modeli dondurup yalnızca küçük bir adaptörü eğitiyoruz. Denemelerimizde adaptör yaklaşık 40 MB, taban model ise yaklaşık 1,2 GB. Bu, gönüllü GPU'nun bellek ihtiyacını ve ağ üzerinden taşınan veriyi küçültür.</p>

<h2>3. Seyrek senkronizasyon</h2>
<p>Her gönüllü bilgisayar kendi veri dilimiyle bir süre bağımsız çalışır; sonra yalnızca adaptör güncellemeleri toplanıp birleştirilir. Bu yaklaşımın adı DiLoCo. Bir simülasyonumuzda her adımda senkronize olan eğitime kıyasla yaklaşık 25 kat daha az veri taşıdık ve sonuç çok yakın çıktı. Bu, tek tohumlu, küçük ölçekli, gerçek ağ olmayan bir simülasyondu; gerçek dünyada aynı sonucu alacağımız garanti değil.</p>

<h2>4. Güven ve doğrulama</h2>
<p>Gönüllü bir makine hatalı ya da kötü niyetli güncelleme gönderebilir. Planımız: aynı işi birden fazla makinede doğrulamak, güncelleme büyüklüğü ve uyumunu denetlemek, bilinen küçük kontrol görevleri eklemek. Bu mekanizmalar henüz geliştirme aşamasında.</p>

<h2>5. Sizin bilgisayarınıza ne olur?</h2>
<ul>
  <li>İstemci açık kaynak olacak; ne çalıştırdığını okuyabilirsiniz.</li>
  <li>Güncellemeler imzalanacak.</li>
  <li>İstemci yalnızca eğitim işini çalıştırır; dosyalarınıza ya da kişisel verilerinize erişmez. İstemci yayınlandığında bu ilke tek tek doğrulanabilir olmalı.</li>
  <li>İstediğiniz an durdurabilirsiniz.</li>
</ul>

<h2>Neyi henüz bilmiyoruz?</h2>
<p>1 milyar parametre ve üzeri ölçekte, gerçek internet koşullarında, farklı veri dilimleriyle, gönüllü kaybı ve kötü niyetli katkı varlığında sonuçların nasıl değişeceğini ölçmedik. Bunlar yol haritamızdaki sıradaki işler.</p>
</div>
""")

PAGES["yol-haritasi"] = dict(
    title="Yol haritası · Modelen",
    desc="Modelen yol haritası: araştırma, ilk dil uyarlaması, gönüllü istemcisi, kapalı pilot ve açık ağ. Tarih taahhüdü yok.",
    body="""
<div class="prose">
<h1>Yol haritası</h1>
<p class="lead">Aşamaları sırayla yazıyoruz; tarih taahhüdü vermiyoruz. Bir aşama bitince ölçtüğümüz şeyi, bulamadığımız şeyle birlikte yayınlayacağız.</p>

<ol class="timeline">
  <li class="done"><b>0. Araştırma ve simülasyon · yapıldı (ilk tur)</b>Küçük modelde seyrek senkronizasyon, dış optimizer taraması ve adaptör ölçeğinde DiLoCo simülasyonu. Sınırlar: küçük ölçek, tek tohum, gerçek ağ yok.</li>
  <li class="done"><b>1. İlk dil uyarlaması (Türkçe) · ilk deney yapıldı</b>Qwen3-0.6B-Base üzerinde 8 GB'lık tüketici GPU'sunda LoRA ile kısa sürekli ön eğitim. Türkçe dil modelleme iyileşti; Türkçe kıyas testinde (TurkishMMLU) anlamlı bir iyileşme görmedik ve İngilizcede hafif bir kayıp ölçtük.</li>
  <li><b>2. Daha büyük ve çeşitli veri</b>Daha fazla Türkçe veri, İngilizce tekrar karışımı, tokenizer değerlendirmesi, 1,7B ölçekli taban; ardından diğer dillere genişleme.</li>
  <li><b>3. Gönüllü istemcisi (alfa)</b>Açık kaynak, imzalı güncellemeli istemci; katkı doğrulama; ilk iç testler.</li>
  <li><b>4. Kapalı pilot</b>Küçük bir gönüllü grubuyla gerçek ağ üzerinde eğitim; hata ve güvenlik denemeleri.</li>
  <li><b>5. Açık ağ ve ilk yayın</b>Ağırlıkların, kodun ve veri kaynaklarının listesinin Apache-2.0 / ilgili lisanslarla yayını.</li>
</ol>

<h2>Bilinen riskler</h2>
<ul>
  <li>Seyrek senkronizasyonla eğitilen ağırlıkların sonradan standart eğitimle uyumsuz kalabileceğine dair araştırma var; bunu kendimiz sınayacağız.</li>
  <li>Eğitim verisinin lisansları (ör. CC BY-SA veriler) yayınlayacağımız ağırlıklar için hukuki inceleme gerektiriyor.</li>
  <li>Birçok dil için açık modeller zaten var; farkımız ölçülebilir iyileşme ve topluluk sahipliği olmalı.</li>
</ul>
</div>
""")

PAGES["sss"] = dict(
    title="Sık sorulan sorular · Modelen",
    desc="Modelen hakkında sık sorulan sorular: gönüllülük, ödeme, güvenlik, lisans ve veri.",
    body="""
<div class="prose">
<h1>Sık sorulan sorular</h1>
<details><summary>Yayınlanmış bir modeliniz var mı?</summary><p>Hayır. Şu an araştırma aşamasındayız. Yayınlayacağımız ilk modelin ne olduğunu, nasıl ölçüldüğünü ve sınırlarını yayın sırasında açıkça yazacağız.</p></details>
<details><summary>Gönüllü olmak için ne gerekiyor?</summary><p>İlk hedef, en az 8 GB belleğe sahip bir NVIDIA ekran kartı. Bu gereksinim değişebilir. Gönüllü istemcisi henüz yayınlanmadı; ilgilenenler <a href="katil.html">Katıl sayfasından</a> bize yazabilir.</p></details>
<details><summary>Para ya da kripto kazanır mıyım?</summary><p>Başlangıçta hayır. Katkınız şeffaf bir kayıtta tutulur ve modelin yönünde söz hakkınız olur. Para ya da token dağıtımı planlamıyoruz.</p></details>
<details><summary>Bilgisayarıma zarar verir mi?</summary><p>Yoğun GPU kullanımı elektrik tüketimini, ısıyı ve fan gürültüsünü artırır; donanım ömrüne etkisi olabilir. İstemci bunu sınırlayacak ayarlar sunacak. Kararı siz verirsiniz ve istediğiniz an durdurabilirsiniz.</p></details>
<details><summary>Kişisel verilerime erişiliyor mu?</summary><p>Tasarım ilkemiz: istemci yalnızca eğitim işini çalıştırır, dosyalarınıza ya da kişisel verilerinize erişmez. Yalnızca teknik bilgiler (ör. GPU modeli, bellek, sürüm) paylaşılır. Ayrıntılar <a href="kvkk.html">Aydınlatma Metninde</a>; istemci yayınlandığında güncellenecek.</p></details>
<details><summary>Hangi veriyle eğitiyorsunuz?</summary><p>İlk deneylerde Türkçe Vikipedi'den bir alt küme kullandık. Daha sonrası için kullanılacak tüm veri kaynaklarını ve lisanslarını yayınlayacağız.</p></details>
<details><summary>Lisans nedir?</summary><p>Kod ve model ağırlıkları için Apache-2.0 hedefliyoruz. Eğitim verisinden kaynaklanan lisans gereklilikleri hukuki incelemeden sonra netleşecek. Ayrıntı: <a href="lisans.html">Lisans</a>.</p></details>
<details><summary>Neden sıfırdan model eğitmiyorsunuz?</summary><p>Tek bir tüketici GPU'sunda 1 milyar parametreli modeli sıfırdan eğitmek aylar sürer ve belleğe sığmaz. Açık bir tabanı uyarlamak çok daha ucuz ve hızlı. İleride sıfırdan eğitim bir seçenek olabilir.</p></details>
<details><summary>Siz kimsiniz?</summary><p>Modelen Alternatif Eğitim Topluluğu. Ayrıntılar <a href="hakkinda.html">Hakkında</a> sayfasında.</p></details>
</div>
""")

PAGES["katil"] = dict(
    title="Katıl · Modelen",
    desc="Modelen'e gönüllü olarak katılmak için bilgi: gönüllü istemcisi henüz yayınlanmadı, ilgilenenler e-posta ile ulaşabilir.",
    body="""
<div class="prose">
<h1>Katıl</h1>
<p class="lead">Gönüllü istemcisi henüz yayınlanmadı. Hazır olduğunda buradan duyuracağız.</p>
<h2>Şimdi ne yapabilirsiniz?</h2>
<ul>
  <li><b>Haberdar olun:</b> <a href="mailto:%%EPOSTA%%?subject=Gönüllü%20ilgisi">%%EPOSTA%%</a> adresine "Gönüllü" konusuyla yazın. E-posta adresiniz yalnızca Modelen duyuruları için kullanılır; ayrıntı için <a href="kvkk.html">Aydınlatma Metni</a>.</li>
  <li><b>Katkı verin:</b> kod, veri değerlendirmesi, dil kıyas testleri (önce Türkçe) ve hukuki/güvenlik incelemesi için de yardıma ihtiyacımız var. <a href="katki-sartlari.html">Katkı şartlarına</a> bakın.</li>
</ul>
<h2>Gönüllü olacaksanız beklentimiz</h2>
<ul>
  <li>Hedef donanım: en az 8 GB belleğe sahip NVIDIA ekran kartı (değişebilir).</li>
  <li>18 yaşından küçükler için veli ya da vasi onayı.</li>
  <li><a href="gonullu-sartlari.html">Gönüllü katılım şartlarını</a> okuyun.</li>
</ul>
<p><b>Para ya da kripto ödülü yoktur.</b> Katkı kaydı ve söz hakkı vardır.</p>
</div>
""")

PAGES["hakkinda"] = dict(
    title="Hakkında · Modelen",
    desc="Modelen Alternatif Eğitim Topluluğu hakkında: misyon, ilkeler ve topluluk bilgileri.",
    body="""
<div class="prose">
<h1>Hakkında</h1>
<p class="lead">Modelen, açık ve topluluk sahipli yapay zekâ modelleri geliştirmeyi amaçlayan uluslararası bir girişimdir. İlk dilimiz Türkçe.</p>
<h2>Misyonumuz</h2>
<p>Geliştiricilerin ve kurumların, verilerini üçüncü taraf servislere göndermek zorunda kalmadan kullanabileceği, şeffaf biçimde eğitilmiş açık modeller sunmak.</p>
<h2>İlkelerimiz</h2>
<ul>
  <li><b>Şeffaflık:</b> Ne ölçtüğümüzü ve ne ölçemediğimizi yayınlarız.</li>
  <li><b>Açıklık:</b> Kod ve ağırlıklar açık lisansla yayınlanır.</li>
  <li><b>Topluluk sahipliği:</b> Katkılar kayıt altındadır, kararlar açık yürütülür.</li>
  <li><b>Gizlilik:</b> Gönüllü cihazlarındaki kişisel verilere erişmeyiz.</li>
  <li><b>Abartmamak:</b> Sonuçlarımızı kanıtladığımız kadar söyleriz.</li>
</ul>
<h2>Topluluk bilgileri</h2>
<table>
  <tr><th>Unvan</th><td>Modelen Alternatif Eğitim Topluluğu</td></tr>
  <tr><th>Alan adı</th><td>modelen.tr</td></tr>
  <tr><th>İletişim</th><td>%%EPOSTA%%</td></tr>
</table>
</div>
""")

PAGES["iletisim"] = dict(
    title="İletişim · Modelen",
    desc="Modelen ile iletişim: genel sorular, gönüllülük, basın ve kişisel veri başvuruları için tek e-posta adresi.",
    body="""
<div class="prose">
<h1>İletişim</h1>
<p class="lead">Tüm konular için tek adres: <a href="mailto:%%EPOSTA%%">%%EPOSTA%%</a></p>
<ul>
  <li><b>Genel, gönüllülük, basın:</b> konu satırına konunuzu yazın.</li>
  <li><b>Kişisel veri başvuruları (KVKK):</b> konu satırına "KVKK Başvurusu" yazın. Ayrıntı: <a href="kvkk.html">Aydınlatma Metni</a>.</li>
  <li><b>Güvenlik bildirimi:</b> konu satırına "Güvenlik" yazın. Sorumlu bildirimlerinize teşekkür ederiz; ayrıntılar <code>/.well-known/security.txt</code> dosyasında.</li>
</ul>
</div>
""")

PAGES["gizlilik"] = dict(
    legal=True,
    title="Gizlilik politikası · Modelen",
    desc="Modelen web sitesinin gizlilik politikası: hangi verilerin işlendiği, çerez kullanımı ve haklarınız.",
    body="""
<div class="prose">
<h1>Gizlilik politikası</h1>
<p><small>Son güncelleme: %%TARIH%%</small></p>
<p>Bu politika modelen.tr web sitesi için geçerlidir. Gönüllü istemcisi yayınlandığında bu politika ve Aydınlatma Metni güncellenecektir.</p>
<h2>Kısaca</h2>
<ul>
  <li>Sitede reklam, takip ya da analiz aracı kullanmıyoruz. Yalnızca hesap açar ya da giriş yaparsanız, oturumunuz için zorunlu çerezler kullanılır.</li>
  <li>Üçüncü taraf betik, yazı tipi ya da gömülü içerik yüklemiyoruz.</li>
  <li>Bize e-posta yazarsanız, yalnızca yanıt vermek için e-postanızı ve mesajınızı işleriz.</li>
</ul>
<h2>İşlediğimiz veriler</h2>
<ul>
  <li><b>Sunucu kayıtları:</b> Siteyi barındıran hizmet sağlayıcı (%%BARINDIRMA%%) güvenlik ve işleyiş amacıyla IP adresi, istek zamanı ve tarayıcı bilgisini kaydedebilir. Kayıt saklama süreleri sağlayıcının politikasına ve yürürlükteki mevzuata tabidir.</li>
  <li><b>E-posta yazışmaları:</b> ad (varsa), e-posta adresi ve mesaj içeriği.</li>
  <li><b>Profil ve topluluk içeriği:</b> profil bilgileri (görünen ad, kullanıcı adı, hakkında metni, fotoğraf, sosyal bağlantılar), gönderiler, takip ve engel kayıtları, şikayetler. Profil varsayılan olarak <b>gizlidir</b>; yalnızca siz "herkese açık" yaparsanız yukarıdaki profil bilgileri ve gönderileriniz herkese açık sayfalarda yayınlanır (e-postanız hiçbir zaman gösterilmez). Fotoğraflardaki konum ve cihaz bilgileri (EXIF) yüklenirken silinir. Profili istediğiniz zaman gizleyebilir ya da hesabınızla birlikte silebilirsiniz.</li>
  <li><b>Hesap ve koordinatör başvurusu:</b> kayıt olursanız ad, e-posta adresi ve parolanız (parola yalnızca geri döndürülemez özet olarak saklanır); koordinatör başvurusu yaparsanız proje adı, açıklamalar, bağlantılar, varsa koordinatör adresi ve iletişim e-postası. Proje adı, açıklamalar, bağlantı ve adres, başvuru onaylanınca herkese açık sayfada yayınlanır; iletişim e-postası ve hesap bilgileriniz yalnızca yöneticilere görünür. Hesap işlemleri için (e-posta doğrulama, şifre sıfırlama, başvuru durumu) info@modelen.tr adresinden işlemsel e-postalar gönderilir; reklam ya da pazarlama e-postası göndermeyiz. Hesabınızı panelden istediğiniz zaman silebilirsiniz; hesap, başvuru ve sayfa kalıcı olarak silinir.</li>
</ul>
<h2>Haklarınız</h2>
<p>6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamındaki haklarınız ve başvuru yöntemi için <a href="kvkk.html">Aydınlatma Metnine</a> bakın.</p>
<h2>Değişiklikler</h2>
<p>Bu politika güncellendiğinde sayfanın başındaki tarih değişir.</p>
</div>
""")

PAGES["kvkk"] = dict(
    legal=True,
    title="KVKK Aydınlatma Metni · Modelen",
    desc="6698 sayılı KVKK kapsamında Modelen aydınlatma metni: veri sorumlusu, işleme amaçları, hukuki sebepler ve haklarınız.",
    body="""
<div class="prose">
<h1>Kişisel Verilerin İşlenmesine İlişkin Aydınlatma Metni</h1>
<p><small>6698 sayılı Kanun m.10 · Son güncelleme: %%TARIH%%</small></p>
<h2>1. Veri sorumlusu</h2>
<p>Modelen Alternatif Eğitim Topluluğu · E-posta: %%EPOSTA%%</p>
<h2>2. İşlenen kişisel veriler, amaçlar ve hukuki sebepler</h2>
<table>
  <tr><th>Veri</th><th>Amaç</th><th>Hukuki sebep</th></tr>
  <tr><td>İşlem güvenliği verileri (IP adresi, istek zamanı, tarayıcı bilgisi; barındırma sağlayıcısı üzerinden)</td><td>Sitenin güvenli ve kesintisiz çalışması, mevzuat gereği kayıt tutulması</td><td>Hukuki yükümlülük; meşru menfaat (m.5/2-f)</td></tr>
  <tr><td>İletişim verileri (ad, e-posta, mesaj içeriği)</td><td>Taleplerinize yanıt vermek, gönüllü ve duyuru iletişimi</td><td>Meşru menfaat; sözleşmenin kurulması için gerekli olduğu hallerde m.5/2-c</td></tr>
  <tr><td>Profil ve topluluk içeriği (görünen ad, kullanıcı adı, hakkında, fotoğraf, sosyal bağlantılar, gönderiler, takip/engel/şikayet kayıtları)</td><td>Topluluk özelliklerinin sunulması, kötüye kullanımın önlenmesi ve moderasyon</td><td>Açık rıza (herkese açık yapılan bilgiler); meşru menfaat (güvenlik ve moderasyon)</td></tr>
  <tr><td>Hesap ve başvuru verileri (ad, e-posta, parola özeti, proje bilgileri, iletişim e-postası, oturum kaydı)</td><td>Hesabın yürütülmesi, koordinatör başvurusunun değerlendirilmesi, onaylanan koordinatörlerin yayınlanması ve işlemsel e-posta bildirimleri (doğrulama, şifre sıfırlama, başvuru durumu)</td><td>Sözleşmenin kurulması ve ifası (m.5/2-c); açık rıza (yayınlanan proje bilgileri için)</td></tr>
</table>
<p>Gönüllü istemcisi yayınlandığında işlenecek teknik veriler (ör. GPU modeli, bellek, işletim sistemi, istemci sürümü, çalışma süresi, katkı kayıtları) bu metne eklenecektir. İlkemiz, istemcinin kimlik bilgisi, dosya içeriği ya da kişisel içerik toplamamasıdır.</p>
<h2>3. Verilerin aktarılması</h2>
<p>Verileriniz, hizmetin sunulması için barındırma ve e-posta hizmeti aldığımız sağlayıcılara (%%BARINDIRMA%%) ve yasal yükümlülükler gereği yetkili kurumlara aktarılabilir. Yurt dışına aktarım söz konusu olduğunda Kanun'un 9. maddesindeki şartlara uygun hareket edilir.</p>
<h2>4. Toplama yöntemi</h2>
<p>Veriler, web sitesi ziyaretiniz sırasında otomatik yollarla, bize gönderdiğiniz elektronik postalarla ve kayıt ile koordinatör başvuru formlarına kendi girdiğiniz bilgilerle toplanır.</p>
<h2>5. Haklarınız (m.11)</h2>
<ul>
  <li>Kişisel verinizin işlenip işlenmediğini öğrenme,</li>
  <li>İşlenmişse buna ilişkin bilgi talep etme,</li>
  <li>İşlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme,</li>
  <li>Yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme,</li>
  <li>Eksik veya yanlış işlenmişse düzeltilmesini isteme,</li>
  <li>Kanun'da öngörülen şartlar çerçevesinde silinmesini veya yok edilmesini isteme ve bunun aktarılan üçüncü kişilere bildirilmesini isteme,</li>
  <li>İşlenen verilerin otomatik sistemlerle analiz edilmesi sonucu aleyhinize bir sonuç çıkmasına itiraz etme,</li>
  <li>Kanuna aykırı işleme nedeniyle zarara uğramanız halinde zararın giderilmesini talep etme.</li>
</ul>
<h2>6. Başvuru yöntemi</h2>
<p>Başvurularınızı, Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ'de belirtilen yöntemlerle, kimliğinizi tespit edecek bilgilerle birlikte %%EPOSTA%% adresine (konu satırı: "KVKK Başvurusu") iletebilirsiniz. Başvurular, talebin niteliğine göre en kısa sürede ve en geç otuz gün içinde sonuçlandırılır. Başvurunun reddedilmesi, cevabın yetersiz bulunması veya süresinde cevap verilmemesi halinde, yanıtı öğrendiğiniz tarihten itibaren otuz gün ve her halde başvuru tarihinden itibaren altmış gün içinde Kişisel Verileri Koruma Kurulu'na şikâyette bulunabilirsiniz.</p>
</div>
""")

PAGES["kullanim-sartlari"] = dict(
    legal=True,
    title="Site kullanım şartları · Modelen",
    desc="Modelen web sitesinin kullanım şartları: içerik, fikri mülkiyet, sorumluluk ve uygulanacak hukuk.",
    body="""
<div class="prose">
<h1>Site kullanım şartları</h1>
<p><small>Son güncelleme: %%TARIH%%</small></p>
<h2>1. Kapsam</h2>
<p>Bu şartlar modelen.tr web sitesinin kullanımını düzenler. Siteyi kullanarak bu şartları kabul etmiş olursunuz. Gönüllü olarak bilgisayar gücü paylaşımı ve kod/veri katkıları için ayrı şartlar geçerlidir: <a href="gonullu-sartlari.html">Gönüllü Şartları</a>, <a href="katki-sartlari.html">Katkı Şartları</a>.</p>
<h2>2. Bilgilendirme amacı</h2>
<p>Site içeriği genel bilgilendirme amaçlıdır. Modelen araştırma aşamasındadır; sitede yer alan sonuçlar, planlar ve ölçümler değişebilir ve bir garanti ya da taahhüt oluşturmaz.</p>
<h2>3. Fikri mülkiyet</h2>
<p>Site metinleri, görselleri ve "Modelen" adı ile logosu aksi belirtilmedikçe %%UNVAN%%'ye aittir. Modelen yazılımı ve modelleri, yayınlandıklarında ilgili lisanslar (Apache-2.0) altında kullanılabilir; bu lisans ad ve logo kullanım hakkı vermez.</p>
<h2>4. Sorumluluğun sınırı</h2>
<p>Site "olduğu gibi" sunulur. Yürürlükteki mevzuatın izin verdiği ölçüde, sitenin kullanımından doğan dolaylı zararlardan sorumlu değiliz. Bu madde, mevzuatın sınırlamaya izin vermediği sorumlulukları etkilemez.</p>
<h2>5. Dış bağlantılar</h2>
<p>Üçüncü taraf sitelere verilen bağlantıların içeriğinden sorumlu değiliz.</p>
<h2>6. Uygulanacak hukuk ve yetki</h2>
<p>Bu şartlara Türk hukuku uygulanır. Uyuşmazlıklarda %%MAHKEME%% yetkilidir; tüketici mevzuatından doğan haklarınız saklıdır.</p>
<h2>7. Değişiklik</h2>
<p>Şartları güncelleyebiliriz; güncel sürüm bu sayfada yayınlanır.</p>
</div>
""")

PAGES["cerez"] = dict(
    legal=True,
    title="Çerez politikası · Modelen",
    desc="Modelen web sitesi çerez kullanmaz. Bu sayfa çerez politikamızı açıklar.",
    body="""
<div class="prose">
<h1>Çerez politikası</h1>
<p><small>Son güncelleme: %%TARIH%%</small></p>
<p>modelen.tr reklam, takip ya da analiz amaçlı hiçbir çerez ya da benzeri teknoloji yerleştirmez ve tarayıcınızın yerel depolama alanına veri yazmaz.</p>
<p>Siteyi yalnızca okuyorsanız çerez kullanılmaz. Hesap açar ya da giriş yaparsanız, hizmetin çalışması için <b>zorunlu</b> iki çerez yerleştirilir: oturum çerezi (<code>ms</code>, giriş durumunuzu tutar, en çok 14 gün) ve form güvenliği çerezi (<code>mc</code>, sahte istekleri engeller). İkisi de yalnızca bu siteye gönderilir, betiklerce okunamaz (HttpOnly) ve çıkış yapınca ya da hesabınızı silince oturum çerezi geçersiz olur. Zorunlu çerezler için ayrıca onay istenmez.</p>
<p>Barındırma sağlayıcısı, sunucu kayıtlarında IP adresi gibi teknik bilgileri tutabilir; ayrıntı için <a href="gizlilik.html">Gizlilik politikasına</a> bakın.</p>
<p>İleride başka çerez ya da analiz aracı eklersek, kullanmadan önce bu politikayı güncelleyeceğiz ve gerekli olan yerde açık rızanızı isteyeceğiz.</p>
</div>
""")

PAGES["gonullu-sartlari"] = dict(
    legal=True,
    title="Gönüllü katılım şartları · Modelen",
    desc="Modelen gönüllü katılım şartları taslağı: gönüllü GPU paylaşımının koşulları, güvenlik ilkeleri, sorumluluklar.",
    body="""
<div class="prose">
<h1>Gönüllü katılım şartları</h1>
<p><small>Son güncelleme: %%TARIH%% · İstemci yayınlanana kadar bağlayıcı değildir.</small></p>
<p>Bu şartlar, Modelen'in gönüllü eğitim ağına bilgisayar gücü sağlayacak kişiler (“Gönüllü”) içindir. Gönüllü istemcisi henüz yayınlanmamıştır; bu metin planlanan koşulları gösterir.</p>
<h2>1. Gönüllülük ve karşılıksızlık</h2>
<p>Katılım isteğe bağlıdır ve karşılıksızdır. Para, kripto varlık ya da başka bir ödeme yapılmaz. Katkılarınız şeffaf bir katkı kaydında (isterseniz takma adla) görünür.</p>
<h2>2. Yaş</h2>
<p>18 yaşından küçükler yalnızca veli ya da vasi onayıyla katılabilir.</p>
<h2>3. İstemci ve güvenlik ilkeleri</h2>
<ul>
  <li>İstemci açık kaynak olarak yayınlanır; güncellemeler imzalıdır.</li>
  <li>İstemci yalnızca eğitim işini çalıştırır; dosyalarınıza, tarayıcı verilerinize, ekranınıza ya da kimlik bilgilerinize erişmez.</li>
  <li>Paylaşılan teknik bilgiler: GPU modeli ve belleği, işletim sistemi, istemci sürümü, çalışma süresi ve katkı sonuçları.</li>
  <li>İstediğiniz zaman durdurabilir ve kaldırabilirsiniz; kaldırma sonrası istemciden veri toplanmaz.</li>
</ul>
<h2>4. Gönüllünün yükümlülükleri</h2>
<ul>
  <li>İstemciyi değiştirerek sahte, hatalı ya da zararlı katkı göndermemek.</li>
  <li>Başkasına ait ya da izniniz olmayan bir bilgisayarda izinsiz çalıştırmamak.</li>
  <li>Hesap/katkı kaydı bilgilerinizin doğruluğunu korumak.</li>
</ul>
<h2>5. Donanım ve enerji</h2>
<p>Yoğun GPU kullanımı elektrik tüketimini, ısıyı ve gürültüyü artırır ve donanım ömrünü etkileyebilir. Kullanım süresi ve güç sınırını siz belirlersiniz. Modelen'in sorumluluğu, mevzuatın izin verdiği ölçüde sınırlıdır; bu sınırlama zorunlu hükümleri etkilemez.</p>
<h2>6. Katılımın sonlandırılması</h2>
<p>Siz her zaman çıkabilirsiniz. Güvenliği tehdit eden ya da bu şartları ihlal eden katkıları ağdan çıkarma hakkımız saklıdır.</p>
<h2>7. Kişisel veriler</h2>
<p>Kişisel verilerin işlenmesi <a href="kvkk.html">Aydınlatma Metni</a> kapsamındadır.</p>
<h2>8. Uygulanacak hukuk</h2>
<p>Türk hukuku; yetkili mahkeme: %%MAHKEME%%.</p>
</div>
""")

PAGES["katki-sartlari"] = dict(
    legal=True,
    title="Katkı şartları · Modelen",
    desc="Modelen'e kod, veri ve dokümantasyon katkısı için şartlar: Apache-2.0 lisansı ve Developer Certificate of Origin.",
    body="""
<div class="prose">
<h1>Katkı şartları</h1>
<p><small>Son güncelleme: %%TARIH%%</small></p>
<p>Modelen'e kod, dokümantasyon, kıyas testi ya da veri katkısı vermeniz bizim için değerlidir. Katkınızın uygun biçimde kullanılabilmesi için aşağıdaki şartlar geçerlidir.</p>
<h2>1. Lisans</h2>
<p>Katkınız, katkı yaptığınız projenin lisansı (kod ve modeller için Apache-2.0) altında lisanslanır. Bu, Apache-2.0'ın 5. maddesindeki “Katkıların Gönderilmesi” hükmüyle uyumludur. Yazarlık bilginiz korunur.</p>
<h2>2. Developer Certificate of Origin (DCO)</h2>
<p>Her commit mesajına <code>Signed-off-by: Adınız &lt;eposta&gt;</code> satırını ekleyerek Developer Certificate of Origin 1.1 sürümünü kabul etmiş olursunuz (metin: developercertificate.org). Özetle: katkıyı yapmaya hakkınız vardır ve katkınızın proje lisansıyla paylaşılmasını kabul edersiniz.</p>
<h2>3. Veri katkıları</h2>
<p>Veri katkılarında kaynağı, lisansı ve kişisel veri içerip içermediğini belirtmeniz gerekir. Kişisel veri içeren, telif hakkı izni olmayan ya da lisansı belirsiz veriler kabul edilmez.</p>
<h2>4. İnceleme</h2>
<p>Katkıları kalite, güvenlik ve lisans uyumu açısından inceleriz ve reddetme hakkımız saklıdır.</p>
<h2>5. Davranış</h2>
<p>Saygılı ve yapıcı bir iletişim bekliyoruz. Topluluk davranış kuralları için <a href="topluluk-kurallari.html">Topluluk kuralları</a> sayfasına, kod için <a href="https://github.com/macbyclp/modelen-tr" rel="noopener">GitHub deposuna</a> bakın.</p>
</div>
""")

PAGES["lisans"] = dict(
    title="Lisans · Modelen",
    desc="Modelen kod ve model lisansı: Apache License 2.0. Eğitim verisi lisansları ve marka kullanımı hakkında not.",
    body="""
<div class="prose">
<h1>Lisans</h1>
<p>Modelen kodu ve model ağırlıkları, yayınlandıklarında <b>Apache License 2.0</b> altında sunulacaktır. Tam metin: <a href="https://www.apache.org/licenses/LICENSE-2.0">apache.org/licenses/LICENSE-2.0</a> ve depodaki <code>LICENSE</code> dosyası.</p>
<h2>Önemli notlar</h2>
<ul>
  <li><b>Taban model:</b> İlk deneylerimizde kullanılan Qwen3-0.6B-Base (Alibaba Cloud) Apache-2.0 lisanslıdır. Kullandığımız her taban modelin lisansını ayrıca belirtiriz.</li>
  <li><b>Eğitim verisi:</b> İlk deneylerde kullanılan Türkçe Vikipedi metni CC BY-SA / GFDL gibi lisanslarla yayınlanmıştır. Bu tür verilerle eğitilen ağırlıkların hangi koşullarla yayınlanabileceği hukuki incelemeye tabidir; sonucu burada duyuracağız.</li>
  <li><b>Marka:</b> Apache-2.0, “Modelen” adı ve logosunun kullanımı hakkında izin vermez.</li>
  <li><b>Garanti:</b> Yazılım ve modeller “olduğu gibi” sunulur; garanti verilmez.</li>
</ul>
</div>
""")

NAV = [("index", "Ana sayfa"), ("nasil-calisir", "Nasıl çalışır"), ("yol-haritasi", "Yol haritası"),
       ("sss", "SSS"), ("katil", "Katıl"), ("koordinatorler", "Koordinatörler"), ("akis", "Akış"), ("koordinator-ol", "Koordinatör ol"), ("hakkinda", "Hakkında"), ("iletisim", "İletişim")]
FOOT = [("gizlilik", "Gizlilik"), ("kvkk", "KVKK Aydınlatma"), ("kullanim-sartlari", "Kullanım şartları"),
        ("cerez", "Çerez"), ("topluluk-kurallari", "Topluluk kuralları"), ("gonullu-sartlari", "Gönüllü şartları"), ("katki-sartlari", "Katkı şartları"),
        ("lisans", "Lisans")]
UI = dict(
    lang="tr", skip="İçeriğe geç", switch="English", draft=("<b>Taslak:</b> Bu metin yayınlanmadan önce bir avukat tarafından "
    "incelenmelidir."),
    footer_tag="Açık, topluluk sahipli yapay zekâ.",
    copyright="© 2026 Modelen Alternatif Eğitim Topluluğu",
    sitename="Modelen", nav_label="Ana gezinme", legal_label="Yasal bağlantılar",
)
