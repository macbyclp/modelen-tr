#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
//! Modelen: gönüllü GPU istemcisi + kodlama yardımcısı, tek masaüstü uygulaması.

mod ayar;
mod dizin;
#[allow(dead_code)] // sağlayıcı katmanı şimdilik kullanılmıyor (Kod sekmesi artık topluluğa soruyor)
mod saglayici;
mod surec;

use eframe::egui::{self, Color32, RichText};
use saglayici::{Saglayici, Tur};
use std::path::PathBuf;
use std::sync::atomic::Ordering;
use std::sync::mpsc::{channel, Receiver};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use surec::{agac, Dugum, Surec};

const KIRMIZI: Color32 = Color32::from_rgb(227, 10, 23);
const KIRMIZI_ACIK: Color32 = Color32::from_rgb(255, 120, 112);

#[derive(PartialEq, Clone, Copy)]
enum Sekme {
    Kod,
    Gonullu,
    Ayarlar,
}

struct Uygulama {
    dizin: Arc<Mutex<(Vec<dizin::Koordinator>, String)>>, // (liste, durum metni)
    /// `--tepside` ile açıldıysa ilk karede sistem tepsisine gizlenir
    tepside_basla: u8,
    _tepsi: Option<tray_icon::TrayIcon>,
    logo: egui::TextureHandle,
    ayar: ayar::Ayarlar,
    sekme: Sekme,
    bildirim: String,
    // topluluğa soru
    soru_girdi: String,
    soru_kod_ekle: bool,
    sorular: Vec<(String, String)>, // (soru, durum)
    soru_alici: Option<Receiver<Result<u64, String>>>,
    // editör
    agac: Vec<Dugum>,
    acik: Option<PathBuf>,
    metin: String,
    kirli: bool,
    secim: (usize, usize), // karakter indeksleri
    // gönüllü / yerel model
    gpu: String,
    isci: Option<Surec>,
    sunucu: Option<Surec>,
    koord_durum: Arc<Mutex<String>>,
    son_durum: Instant,
    koord_surec: Option<Surec>,
    baslat_bekle: Option<Instant>,
    acilis: Option<Instant>,
    // ayarlar
    anahtar_girdi: String,
    koord_anahtar_girdi: String,
}

impl Uygulama {
    fn yeni(cc: &eframe::CreationContext<'_>) -> Self {
        let mut v = egui::Visuals::dark();
        v.selection.bg_fill = KIRMIZI;
        v.hyperlink_color = KIRMIZI_ACIK;
        v.widgets.hovered.bg_stroke.color = KIRMIZI;
        cc.egui_ctx.set_visuals(v);
        let ayar = ayar::yukle();
        let tepsi = tepsi_kur(&cc.egui_ctx);
        let dizin = Arc::new(Mutex::new((dizin::birlestir(&dizin::onbellekten_oku()), "kayıtlı liste".to_string())));
        let mut u = Uygulama {
            dizin,
            tepside_basla: if std::env::args().any(|a| a == "--tepside") { 5 } else { 0 },
            _tepsi: tepsi,
            logo: cc.egui_ctx.load_texture("logo", png_yukle(LOGO_PNG), egui::TextureOptions::LINEAR),
            sekme: if std::env::args().any(|a| a == "--gonullu") { Sekme::Gonullu } else { Sekme::Kod },
            bildirim: String::new(),
            soru_girdi: String::new(),
            soru_kod_ekle: false,
            sorular: vec![],
            soru_alici: None,
            agac: vec![],
            acik: None,
            metin: String::new(),
            kirli: false,
            secim: (0, 0),
            gpu: surec::gpu_bilgi(),
            isci: None,
            sunucu: None,
            koord_durum: Arc::new(Mutex::new("henüz sorgulanmadı".into())),
            son_durum: Instant::now() - Duration::from_secs(60),
            koord_surec: None,
            baslat_bekle: None,
            acilis: None,
            anahtar_girdi: String::new(),
            koord_anahtar_girdi: String::new(),
            ayar,
        };
        u.agaci_yenile();
        u.dizini_yenile(&cc.egui_ctx);
        u
    }

    fn isci_calisiyor(&mut self) -> bool {
        self.isci.as_mut().map(|s| s.calisiyor()).unwrap_or(false)
    }

    /// Katkıyı başlatır. Adres yerel makineyse ve orada koordinatör yoksa önce yerel test koordinatörünü açar.
    fn isci_baslat(&mut self) {
        self.bildirim.clear();
        if let Some(port) = surec::yerel_adres(&self.ayar.koordinator) {
            let calisiyor = self.koord_surec.as_mut().map(|k| k.calisiyor()).unwrap_or(false);
            if !surec::port_acik(port) && !calisiyor {
                let args = vec![
                    "istemci/koordinator.py".to_string(),
                    "--baslangic".into(),
                    "istemci/calisma/tur-0.safetensors".into(),
                    "--en-az".into(),
                    "1".into(),
                    "--port".into(),
                    port.to_string(),
                ];
                match Surec::baslat(&self.ayar.python, &self.ayar.modelen_klasoru, &args) {
                    Ok(k) => {
                        self.koord_surec = Some(k);
                        self.baslat_bekle = Some(Instant::now());
                    }
                    Err(e) => self.bildirim = e,
                }
                return;
            }
        }
        self.isci_dogrudan_baslat();
    }

    /// Kimlik kasasındaki koordinatör anahtarının adı (adrese göre; kapalı gruplar için).
    fn koord_anahtar_adi(&self) -> String {
        format!("koordinator:{}", self.ayar.koordinator.trim().trim_end_matches('/'))
    }

    fn isci_dogrudan_baslat(&mut self) {
        let args = ["istemci/isci.py".to_string(), "--koordinator".into(), self.ayar.koordinator.clone(), "--isci".into(), self.ayar.takma_ad.clone()];
        let anahtar = ayar::anahtar_oku(&self.koord_anahtar_adi()).unwrap_or_default();
        let ortam: Vec<(&str, &str)> = if anahtar.is_empty() { vec![] } else { vec![("MODELEN_ANAHTAR", anahtar.as_str())] };
        match Surec::baslat_env(&self.ayar.python, &self.ayar.modelen_klasoru, &args, &ortam) {
            Ok(s) => {
                self.isci = Some(s);
                self.acilis = Some(Instant::now());
                self.bildirim.clear();
            }
            Err(e) => self.bildirim = e,
        }
        let _ = ayar::kaydet(&self.ayar);
    }

    fn isci_durdur(&mut self) {
        self.isci = None;
        self.baslat_bekle = None;
        self.acilis = None;
    }

    /// Yerel koordinatörün açılmasını bekler; hazır olunca işçiyi başlatır.
    fn bekleyeni_ilerlet(&mut self) {
        let Some(t) = self.baslat_bekle else { return };
        let port = surec::yerel_adres(&self.ayar.koordinator).unwrap_or(8750);
        if surec::port_acik(port) {
            self.baslat_bekle = None;
            self.isci_dogrudan_baslat();
        } else if !self.koord_surec.as_mut().map(|k| k.calisiyor()).unwrap_or(false) || t.elapsed() > Duration::from_secs(90) {
            self.baslat_bekle = None;
            let son = self.koord_surec.as_ref().and_then(|k| k.son_satirlar(1).pop()).unwrap_or_default();
            self.bildirim = format!("Yerel koordinatör açılamadı. {}", surec::dostca(&son));
        }
    }

    fn durum_sorgula(&mut self, ctx: &egui::Context) {
        if self.son_durum.elapsed() > Duration::from_secs(5) {
            self.son_durum = Instant::now();
            let (adres, hedef, ctx2) = (self.ayar.koordinator.clone(), self.koord_durum.clone(), ctx.clone());
            let anahtar = ayar::anahtar_oku(&self.koord_anahtar_adi()).unwrap_or_default();
            std::thread::spawn(move || {
                let s = surec::koordinator_durumu(&adres, &anahtar).unwrap_or_else(|e| if surec::dostca(&e) != e { "ulaşılamıyor · sunucu kapalı olabilir ya da adres yanlış".to_string() } else { format!("ulaşılamıyor ({e})") });
                *hedef.lock().unwrap() = s;
                ctx2.request_repaint();
            });
        }
    }

    // ---------- Kolay mod ----------
    fn kolay_sayfa(&mut self, ctx: &egui::Context) {
        self.durum_sorgula(ctx);
        let acik = self.isci_calisiyor();
        self.bekleyeni_ilerlet();
        egui::TopBottomPanel::top("kolay_ust").show_separator_line(false).show(ctx, |ui| {
            if ui.small_button("Gizle").on_hover_text("Sistem tepsisine gönderir; katkı arkada sürer").clicked() {
                tepsiye_gizle(ctx);
            }
        });
        egui::TopBottomPanel::bottom("kolay_alt").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.label(RichText::new(format!("v{}", env!("CARGO_PKG_VERSION"))).small().weak());
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.link("Gelişmiş seçenekler").clicked() {
                        self.ayar.kolay_mod = false;
                        ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(egui::vec2(1100.0, 760.0)));
                        let _ = ayar::kaydet(&self.ayar);
                    }
                });
            });
        });
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.vertical_centered(|ui| {
                ui.add_space((ui.available_height() * 0.03).max(6.0));
                ui.add(egui::Image::new(&self.logo).fit_to_exact_size(egui::vec2(110.0, 110.0)));
                ui.label(RichText::new("modelen").size(30.0).strong().color(KIRMIZI));
                ui.label("GPU'nuzu ortak model eğitimine verin.");
                ui.add_space(16.0);
                let d = 200.0;
                let (rect, yanit) = ui.allocate_exact_size(egui::vec2(d, d), egui::Sense::click());
                let uzerinde = yanit.hovered();
                let (dolgu, yazi) = if acik { (KIRMIZI, "AÇIK") } else { (Color32::from_gray(48), "KAPALI") };
                let yaricap = d / 2.0 - if uzerinde { 0.0 } else { 4.0 };
                if acik {
                    let nabiz = ((ctx.input(|i| i.time) * 2.0).sin() as f32 + 1.0) * 0.5;
                    ui.painter().circle_filled(rect.center(), yaricap + 6.0 + 10.0 * nabiz, KIRMIZI.gamma_multiply(0.30 - 0.15 * nabiz));
                }
                ui.painter().circle_filled(rect.center(), yaricap, dolgu);
                ui.painter().circle_stroke(rect.center(), yaricap, egui::Stroke::new(3.0_f32, if acik { KIRMIZI_ACIK } else { Color32::from_gray(90) }));
                ui.painter().text(rect.center(), egui::Align2::CENTER_CENTER, yazi, egui::FontId::proportional(40.0), Color32::WHITE);
                if yanit.on_hover_cursor(egui::CursorIcon::PointingHand).clicked() {
                    if acik || self.baslat_bekle.is_some() {
                        self.isci_durdur();
                    } else {
                        self.isci_baslat();
                    }
                }
                ui.add_space(20.0);
                let hazirlaniyor = self.baslat_bekle.is_some();
                if hazirlaniyor {
                    ui.colored_label(KIRMIZI_ACIK, "Hazırlanıyor… yerel koordinatör açılıyor.");
                } else if acik {
                    ui.colored_label(Color32::LIGHT_GREEN, "● Katkı veriyorsunuz, teşekkürler!");
                    let sure = self.acilis.map(|t| t.elapsed().as_secs()).unwrap_or(0);
                    let tur = self.isci.as_ref().map(|s| s.tamamlanan.load(Ordering::Relaxed)).unwrap_or(0);
                    ui.label(format!("Süre: {} dk {} sn · Tamamlanan tur: {}", sure / 60, sure % 60, tur));
                } else if let Some(s) = &self.isci {
                    let son = s.son_satirlar(1).pop().unwrap_or_default();
                    ui.colored_label(KIRMIZI_ACIK, format!("Durdu. {}", surec::dostca(&son)));
                } else {
                    ui.label("Açmak için düğmeye basın.");
                }
                if !self.bildirim.is_empty() {
                    ui.colored_label(KIRMIZI_ACIK, &self.bildirim);
                }
                ui.add_space(12.0);
                ui.label(RichText::new(format!("GPU: {}", self.gpu)).small());
                ui.label(RichText::new(format!("Koordinatör: {}", self.koord_durum.lock().unwrap())).small());
            });
            ui.add_space(8.0);
            ui.separator();
            self.koordinator_secici(ui, ctx);
        });
        let hizli = acik || self.baslat_bekle.is_some();
        if !GIZLI.load(Ordering::Relaxed) {
            ctx.request_repaint_after(if hizli { Duration::from_millis(40) } else { Duration::from_secs(2) });
        }
    }

    /// Onaylı koordinatör listesini siteden arka planda çeker; başarısızsa kayıtlı liste kalır.
    fn dizini_yenile(&self, ctx: &egui::Context) {
        let (hedef, ctx, adres) = (self.dizin.clone(), ctx.clone(), self.ayar.dizin_adresi.clone());
        hedef.lock().unwrap().1 = "güncelleniyor…".into();
        std::thread::spawn(move || {
            let sonuc = dizin::getir(&adres);
            let mut g = hedef.lock().unwrap();
            match sonuc {
                Ok(l) => {
                    dizin::onbellege_yaz(&l);
                    g.0 = dizin::birlestir(&l);
                    g.1 = format!("siteden güncellendi ({} onaylı)", l.len());
                }
                Err(_) => g.1 = "siteye ulaşılamadı, kayıtlı liste".into(),
            }
            ctx.request_repaint();
        });
    }

    /// Koordinatör seçimi (Kolay mod ve Gelişmiş'te ortak): seçilen koordinatöre GPU adanır.
    fn koordinator_secici(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.horizontal(|ui| {
            ui.label(RichText::new("Koordinatör seç").strong());
            if ui.small_button("Yenile").clicked() {
                self.dizini_yenile(ctx);
            }
            ui.label(RichText::new(self.dizin.lock().unwrap().1.clone()).small().weak());
        });
        let (liste, secili) = (self.dizin.lock().unwrap().0.clone(), self.ayar.koordinator.trim_end_matches('/').to_string());
        let toplam = ui.available_width();
        let (w_sec, w_ad, w_url) = (22.0, (toplam * 0.22).max(60.0), (toplam * 0.31).max(70.0));
        let w_acik = (toplam - w_sec - w_ad - w_url - 24.0).max(60.0);
        let mut secilen: Option<String> = None;
        egui::ScrollArea::vertical().id_source("koord_liste").max_height(130.0).auto_shrink([false, true]).show(ui, |ui| {
            egui::Grid::new("koord_tablo").striped(true).spacing([6.0, 4.0]).show(ui, |ui| {
                for b in ["", "İsim", "Adres", "Geliştirdiği"] {
                    ui.label(RichText::new(b).small().strong());
                }
                ui.end_row();
                for k in &liste {
                    let bu = k.adres == secili;
                    if ui.add_sized([w_sec, 18.0], egui::RadioButton::new(bu, "")).clicked() {
                        secilen = Some(k.adres.clone());
                    }
                    ui.allocate_ui_with_layout(egui::vec2(w_ad, 18.0), egui::Layout::left_to_right(egui::Align::Center), |ui| { ui.add(egui::Label::new(RichText::new(&k.ad).strong()).truncate(true)).on_hover_text(&k.ad); });
                    ui.allocate_ui_with_layout(egui::vec2(w_url, 18.0), egui::Layout::left_to_right(egui::Align::Center), |ui| { ui.add(egui::Label::new(RichText::new(&k.adres).small().monospace()).truncate(true)).on_hover_text(&k.adres); });
                    ui.allocate_ui_with_layout(egui::vec2(w_acik, 18.0), egui::Layout::left_to_right(egui::Align::Center), |ui| { ui.add(egui::Label::new(RichText::new(&k.aciklama).small()).truncate(true)).on_hover_text(&k.aciklama); });
                    ui.end_row();
                }
            });
        });
        if !liste.iter().any(|k| k.adres == secili) {
            ui.colored_label(KIRMIZI_ACIK, format!("Listede olmayan koordinatör: {secili}"));
        }
        ui.horizontal(|ui| {
            ui.label(RichText::new("Koordinatör olmak mı istiyorsunuz?").small());
            ui.hyperlink_to(RichText::new("modelen.tr/koordinator-ol").small(), "https://modelen.tr/koordinator-ol.html");
            ui.label(RichText::new("·").small());
            ui.hyperlink_to(RichText::new("tüm koordinatörler").small(), "https://modelen.tr/koordinatorler");
        });
        if let Some(adres) = secilen {
            if adres != secili {
                self.isci_durdur();
                self.ayar.koordinator = adres;
                self.koord_durum = Arc::new(Mutex::new("henüz sorgulanmadı".into()));
                self.son_durum = Instant::now() - Duration::from_secs(60);
                let _ = ayar::kaydet(&self.ayar);
            }
        }
    }

    fn agaci_yenile(&mut self) {
        self.agac = if self.ayar.calisma_klasoru.is_empty() { vec![] } else { agac(std::path::Path::new(&self.ayar.calisma_klasoru), 4) };
    }

    fn dosya_ac(&mut self, yol: PathBuf) {
        match std::fs::metadata(&yol) {
            Ok(m) if m.len() > 1_000_000 => return self.bildirim = "Dosya 1 MB'tan büyük, açılmadı.".into(),
            Err(e) => return self.bildirim = format!("Açılamadı: {e}"),
            _ => {}
        }
        match std::fs::read_to_string(&yol) {
            Ok(s) => {
                self.metin = s;
                self.acik = Some(yol);
                self.kirli = false;
                self.secim = (0, 0);
                self.bildirim.clear();
            }
            Err(_) => self.bildirim = "Dosya metin (UTF-8) değil, açılmadı.".into(),
        }
    }

    fn dosya_kaydet(&mut self) {
        if let Some(y) = &self.acik {
            match std::fs::write(y, &self.metin) {
                Ok(_) => {
                    self.kirli = false;
                    self.bildirim = format!("Kaydedildi: {}", y.display());
                }
                Err(e) => self.bildirim = format!("Kaydedilemedi: {e}"),
            }
        }
    }

    fn secim_metni(&self) -> String {
        let (a, b) = self.secim;
        if a == b {
            return String::new();
        }
        self.metin.chars().skip(a).take(b - a).collect()
    }

    /// Sorunun yanına (istenirse) eklenen kod bağlamı: seçim varsa seçim, yoksa açık dosyanın başı.
    fn baglam_metni(&self) -> String {
        if self.acik.is_none() {
            return String::new();
        }
        let dosya = self.acik.as_ref().and_then(|p| p.file_name()).map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
        let sec = self.secim_metni();
        let (etiket, govde) = if sec.is_empty() { ("dosya", self.metin.chars().take(4000).collect::<String>()) } else { ("seçim", sec.chars().take(4000).collect::<String>()) };
        format!("// {dosya} ({etiket})\n{govde}")
    }

    fn soru_gonder(&mut self, ctx: &egui::Context) {
        let soru = self.soru_girdi.trim().to_string();
        if soru.is_empty() || self.soru_alici.is_some() {
            return;
        }
        let baglam = if self.soru_kod_ekle { self.baglam_metni() } else { String::new() };
        let (adres, ad) = (self.ayar.koordinator.clone(), self.ayar.takma_ad.clone());
        let anahtar = ayar::anahtar_oku(&self.koord_anahtar_adi()).unwrap_or_default();
        let (tx, rx) = channel();
        self.soru_alici = Some(rx);
        self.sorular.push((soru.clone(), "gönderiliyor…".into()));
        self.soru_girdi.clear();
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let _ = tx.send(surec::soru_gonder(&adres, &ad, &soru, &baglam, &anahtar));
            ctx.request_repaint();
        });
    }

    fn sorulari_isle(&mut self) {
        let Some(rx) = &self.soru_alici else { return };
        if let Ok(sonuc) = rx.try_recv() {
            let durum = match sonuc {
                Ok(no) => format!("Topluluğa iletildi (#{no})"),
                Err(e) => format!("İletilemedi: {}", surec::dostca(&e)),
            };
            if let Some(son) = self.sorular.last_mut() {
                son.1 = durum;
            }
            self.soru_alici = None;
        }
    }

    // ---------- Kod sekmesi ----------
    fn kod_sekmesi(&mut self, ctx: &egui::Context) {
        egui::SidePanel::left("dosyalar").default_width(220.0).show(ctx, |ui| {
            ui.label(RichText::new("Çalışma klasörü").strong());
            let yanit = ui.add(egui::TextEdit::singleline(&mut self.ayar.calisma_klasoru).hint_text("C:\\proje"));
            if ui.button("Aç / yenile").clicked() || (yanit.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))) {
                self.agaci_yenile();
                let _ = ayar::kaydet(&self.ayar);
            }
            ui.separator();
            let mut ac: Option<PathBuf> = None;
            egui::ScrollArea::both().auto_shrink([false, false]).show(ui, |ui| {
                fn ciz(ui: &mut egui::Ui, d: &[Dugum], ac: &mut Option<PathBuf>) {
                    for n in d {
                        if n.klasor {
                            egui::CollapsingHeader::new(&n.ad).id_source(&n.yol).show(ui, |ui| ciz(ui, &n.cocuklar, ac));
                        } else if ui.selectable_label(false, &n.ad).clicked() {
                            *ac = Some(n.yol.clone());
                        }
                    }
                }
                ciz(ui, &self.agac, &mut ac);
            });
            if let Some(y) = ac {
                self.dosya_ac(y);
            }
        });

        egui::SidePanel::right("sohbet").default_width(420.0).min_width(300.0).show(ctx, |ui| self.sohbet_paneli(ui, ctx));

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.horizontal(|ui| {
                let ad = self.acik.as_ref().map(|p| p.display().to_string()).unwrap_or_else(|| "Dosya seçilmedi".into());
                ui.label(RichText::new(format!("{ad}{}", if self.kirli { " ●" } else { "" })).strong());
                if ui.add_enabled(self.acik.is_some() && self.kirli, egui::Button::new("Kaydet (Ctrl+S)")).clicked() {
                    self.dosya_kaydet();
                }
            });
            ui.separator();
            if self.acik.is_none() {
                ui.label("Soldan bir dosya açın ya da bir klasör girin. Sağdaki panelden, istersek açık dosyayı (seçim varsa seçimi) da ekleyerek topluluğa soru sorabilirsiniz.");
                return;
            }
            egui::ScrollArea::both().auto_shrink([false, false]).show(ui, |ui| {
                let out = egui::TextEdit::multiline(&mut self.metin)
                    .code_editor()
                    .desired_width(f32::INFINITY)
                    .desired_rows(40)
                    .show(ui);
                if out.response.changed() {
                    self.kirli = true;
                }
                if let Some(r) = out.cursor_range {
                    let (a, b) = (r.primary.ccursor.index, r.secondary.ccursor.index);
                    self.secim = (a.min(b), a.max(b));
                }
            });
        });
        if ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::S)) {
            self.dosya_kaydet();
        }
    }

    fn sohbet_paneli(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.heading("Topluluğa sor");
        ui.label("Sorunuz doğrudan Modelen ekibine ulaşır. Cevap vermemiz zaman alabilir.");
        ui.separator();
        ui.with_layout(egui::Layout::bottom_up(egui::Align::Min), |ui| {
            let bekliyor = self.soru_alici.is_some();
            let yazili = !self.soru_girdi.trim().is_empty();
            if ui.add_enabled(!bekliyor && yazili, egui::Button::new(RichText::new("Topluluğa gönder").color(Color32::WHITE)).fill(KIRMIZI)).clicked() {
                self.soru_gonder(ctx);
            }
            let g = ui.add(egui::TextEdit::multiline(&mut self.soru_girdi).desired_rows(5).desired_width(f32::INFINITY).hint_text("Sorunuzu yazın (Ctrl+Enter ile gönder)"));
            if g.has_focus() && ui.input(|i| i.modifiers.command && i.key_pressed(egui::Key::Enter)) {
                self.soru_gonder(ctx);
            }
            ui.add_enabled(self.acik.is_some(), egui::Checkbox::new(&mut self.soru_kod_ekle, "Açık dosyayı (seçim varsa seçimi) de ekle"));
            ui.label(RichText::new("Parola, API anahtarı ya da kişisel veri yazmayın.").small().color(KIRMIZI_ACIK));
            ui.separator();
            egui::ScrollArea::vertical().auto_shrink([false, false]).stick_to_bottom(true).show(ui, |ui| {
                ui.with_layout(egui::Layout::top_down(egui::Align::Min), |ui| {
                    if self.sorular.is_empty() {
                        ui.label("Henüz soru sormadınız.");
                    }
                    for (soru, durum) in &self.sorular {
                        egui::Frame::none().fill(Color32::from_gray(32)).rounding(6.0).inner_margin(8.0).show(ui, |ui| {
                            ui.set_width(ui.available_width());
                            ui.add(egui::Label::new(soru.as_str()).wrap(true));
                            let renk = if durum.starts_with("Topluluğa") { Color32::LIGHT_GREEN } else if durum.starts_with("İletilemedi") { KIRMIZI_ACIK } else { Color32::GRAY };
                            ui.label(RichText::new(durum.as_str()).small().color(renk));
                        });
                        ui.add_space(4.0);
                    }
                });
            });
        });
    }

    // ---------- Gönüllü sekmesi ----------
    fn gonullu_sekmesi(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical().show(ui, |ui| {
                ui.heading("Gönüllü GPU");
                ui.label("GPU'nuzu ortak model eğitimine verin. Yalnızca LoRA adaptörü (~40 MB) ağa çıkar; taban model ve veri yerelde kalır.");
                ui.horizontal(|ui| {
                    ui.label(RichText::new("GPU:").strong());
                    ui.label(&self.gpu);
                    if ui.small_button("Yenile").clicked() {
                        self.gpu = surec::gpu_bilgi();
                    }
                });
                if self.ayar.modelen_klasoru.is_empty() {
                    ui.colored_label(KIRMIZI_ACIK, "Modelen proje klasörü bulunamadı. Ayarlar sekmesinden girin (içinde istemci/isci.py olmalı).");
                }
                ui.separator();
                self.koordinator_secici(ui, ctx);
                ui.add_space(6.0);
                egui::Grid::new("g").num_columns(2).show(ui, |ui| {
                    ui.label("Koordinatör adresi");
                    ui.text_edit_singleline(&mut self.ayar.koordinator);
                    ui.end_row();
                    ui.label("Takma ad");
                    ui.text_edit_singleline(&mut self.ayar.takma_ad);
                    ui.end_row();
                });
                // kapalı grup: koordinatörün verdiği anahtar (Windows kimlik kasasında; dosyaya yazılmaz, komut satırında görünmez)
                let kasa_adi = self.koord_anahtar_adi();
                if ayar::anahtar_oku(&kasa_adi).is_some() {
                    ui.horizontal(|ui| {
                        ui.label("Koordinatör anahtarı: kayıtlı (kimlik kasasında)");
                        if ui.small_button("Sil").clicked() {
                            self.bildirim = match ayar::anahtar_sil(&kasa_adi) {
                                Ok(_) => "Koordinatör anahtarı silindi.".into(),
                                Err(e) => format!("Silinemedi: {e}"),
                            };
                        }
                    });
                } else {
                    ui.horizontal(|ui| {
                        ui.label("Koordinatör anahtarı (kapalı grup)");
                        ui.add(egui::TextEdit::singleline(&mut self.koord_anahtar_girdi).password(true).hint_text("yoksa boş bırakın"));
                        if ui.button("Kasaya kaydet").clicked() && !self.koord_anahtar_girdi.trim().is_empty() {
                            self.bildirim = match ayar::anahtar_yaz(&kasa_adi, self.koord_anahtar_girdi.trim()) {
                                Ok(_) => "Koordinatör anahtarı kasaya kaydedildi.".into(),
                                Err(e) => format!("Kaydedilemedi: {e}"),
                            };
                            self.koord_anahtar_girdi.clear();
                        }
                    });
                }
                ui.label(RichText::new("Takma adı kişisel veri içermeyecek şekilde seçin. Listede olmayan bir adres yazarsanız adaptörünüz o sunucuya gider; yalnızca güvendiğiniz sunuculara bağlanın.").small());
                ui.horizontal(|ui| {
                    let calisiyor = self.isci.as_mut().map(|s| s.calisiyor()).unwrap_or(false);
                    if calisiyor {
                        if ui.button("Katkıyı durdur").clicked() {
                            self.isci_durdur();
                        }
                        ui.colored_label(Color32::LIGHT_GREEN, "● çalışıyor");
                    } else {
                        if ui.add(egui::Button::new(RichText::new("Katkıya başla").color(Color32::WHITE)).fill(KIRMIZI)).clicked() {
                            self.isci_baslat();
                        }
                        if self.isci.is_some() {
                            ui.label("durdu");
                        }
                    }
                });
                self.durum_sorgula(ctx);
                ui.label(format!("Koordinatör: {}", self.koord_durum.lock().unwrap()));
                if let Some(s) = &self.isci {
                    log_goster(ui, "isci_log", s);
                }

                ui.add_space(16.0);
                ui.separator();
                ui.heading("Yerel Modelen modeli");
                ui.label("Kod sekmesindeki \"Modelen (yerel)\" sağlayıcısı bu sunucuya bağlanır (127.0.0.1:8760). Not: 0.6B taban model henüz sohbet asistanı kalitesinde değil.");
                ui.horizontal(|ui| {
                    ui.label("Adaptör");
                    ui.text_edit_singleline(&mut self.ayar.adaptor);
                });
                ui.horizontal(|ui| {
                    let calisiyor = self.sunucu.as_mut().map(|s| s.calisiyor()).unwrap_or(false);
                    if calisiyor {
                        if ui.button("Modeli durdur").clicked() {
                            self.sunucu = None;
                        }
                        ui.colored_label(Color32::LIGHT_GREEN, "● çalışıyor");
                    } else if ui.button("Modeli başlat").clicked() {
                        let mut args = vec!["sunucu/modelen_sunucu.py".to_string()];
                        if !self.ayar.adaptor.is_empty() {
                            args.extend(["--adaptor".into(), self.ayar.adaptor.clone()]);
                        }
                        match Surec::baslat(&self.ayar.python, &self.ayar.modelen_klasoru, &args) {
                            Ok(s) => self.sunucu = Some(s),
                            Err(e) => self.bildirim = e,
                        }
                        let _ = ayar::kaydet(&self.ayar);
                    }
                });
                if let Some(s) = &self.sunucu {
                    log_goster(ui, "sunucu_log", s);
                }
                if !self.bildirim.is_empty() {
                    ui.colored_label(KIRMIZI_ACIK, &self.bildirim);
                }
            });
        });
        if !GIZLI.load(Ordering::Relaxed) {
            ctx.request_repaint_after(Duration::from_secs(2));
        }
    }

    // ---------- Ayarlar sekmesi ----------
    fn ayarlar_sekmesi(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical().show(ui, |ui| {
                ui.heading("Sağlayıcılar");
                let n = self.ayar.saglayicilar.len();
                egui::ComboBox::from_id_source("ayar_sag").selected_text(self.ayar.saglayicilar[self.ayar.secili].ad.clone()).show_ui(ui, |ui| {
                    for i in 0..n {
                        let ad = self.ayar.saglayicilar[i].ad.clone();
                        ui.selectable_value(&mut self.ayar.secili, i, ad);
                    }
                });
                let s = &mut self.ayar.saglayicilar[self.ayar.secili];
                egui::Grid::new("sag_grid").num_columns(2).show(ui, |ui| {
                    ui.label("Ad");
                    ui.text_edit_singleline(&mut s.ad);
                    ui.end_row();
                    ui.label("Tür");
                    egui::ComboBox::from_id_source("tur").selected_text(if s.tur == Tur::Openai { "OpenAI uyumlu" } else { "Anthropic" }).show_ui(ui, |ui| {
                        ui.selectable_value(&mut s.tur, Tur::Openai, "OpenAI uyumlu");
                        ui.selectable_value(&mut s.tur, Tur::Anthropic, "Anthropic");
                    });
                    ui.end_row();
                    ui.label("Adres");
                    ui.text_edit_singleline(&mut s.adres);
                    ui.end_row();
                    ui.label("Model");
                    ui.text_edit_singleline(&mut s.model);
                    ui.end_row();
                    ui.label("Anahtar gerekir");
                    ui.checkbox(&mut s.anahtar_gerekir, "");
                    ui.end_row();
                });
                let ad = s.ad.clone();
                let var = ayar::anahtar_oku(&ad).is_some();
                ui.horizontal(|ui| {
                    ui.label(if var { "Anahtar: kayıtlı (Windows kimlik kasasında)" } else { "Anahtar: yok" });
                    if var && ui.small_button("Sil").clicked() {
                        self.bildirim = match ayar::anahtar_sil(&ad) {
                            Ok(_) => "Anahtar silindi.".into(),
                            Err(e) => format!("Silinemedi: {e}"),
                        };
                    }
                });
                ui.horizontal(|ui| {
                    ui.add(egui::TextEdit::singleline(&mut self.anahtar_girdi).password(true).hint_text("API anahtarını yapıştırın"));
                    if ui.button("Kasaya kaydet").clicked() && !self.anahtar_girdi.is_empty() {
                        self.bildirim = match ayar::anahtar_yaz(&ad, &self.anahtar_girdi) {
                            Ok(_) => "Anahtar kasaya kaydedildi (ayar dosyasına yazılmadı).".into(),
                            Err(e) => format!("Kaydedilemedi: {e}"),
                        };
                        self.anahtar_girdi.clear();
                    }
                });
                if ui.button("Yeni sağlayıcı ekle").clicked() {
                    self.ayar.saglayicilar.push(Saglayici { ad: format!("Yeni {}", n + 1), tur: Tur::Openai, adres: "http://127.0.0.1:8000/v1".into(), model: String::new(), anahtar_gerekir: false });
                    self.ayar.secili = n;
                }
                if n > 1 && ui.button("Bu sağlayıcıyı kaldır").clicked() {
                    self.ayar.saglayicilar.remove(self.ayar.secili);
                    self.ayar.secili = 0;
                }
                ui.separator();
                ui.heading("Genel");
                egui::Grid::new("genel").num_columns(2).show(ui, |ui| {
                    ui.label("Modelen proje klasörü");
                    ui.text_edit_singleline(&mut self.ayar.modelen_klasoru);
                    ui.end_row();
                    ui.label("Python");
                    ui.text_edit_singleline(&mut self.ayar.python);
                    ui.end_row();
                    ui.label("En çok cevap tokeni");
                    ui.add(egui::DragValue::new(&mut self.ayar.max_token).clamp_range(64..=8192));
                    ui.end_row();
                });
                if ui.button("Ayarları kaydet").clicked() {
                    self.bildirim = match ayar::kaydet(&self.ayar) {
                        Ok(_) => "Ayarlar kaydedildi.".into(),
                        Err(e) => format!("Kaydedilemedi: {e}"),
                    };
                }
                if !self.bildirim.is_empty() {
                    ui.colored_label(KIRMIZI_ACIK, &self.bildirim);
                }
            });
        });
    }
}

fn log_goster(ui: &mut egui::Ui, id: &str, s: &Surec) {
    egui::ScrollArea::vertical().id_source(id).max_height(160.0).stick_to_bottom(true).auto_shrink([false, true]).show(ui, |ui| {
        for l in s.son_satirlar(60) {
            ui.label(RichText::new(l).monospace().small());
        }
    });
}

impl eframe::App for Uygulama {
    fn update(&mut self, ctx: &egui::Context, _f: &mut eframe::Frame) {
        self.sorulari_isle();
        // eframe pencereyi ilk karelerden sonra gösterir; gizleme birkaç kare sonra yapılır
        if self.tepside_basla > 0 {
            self.tepside_basla -= 1;
            if self.tepside_basla == 0 {
                tepsiye_gizle(ctx);
            } else {
                ctx.request_repaint();
            }
        }
        if self.ayar.kolay_mod {
            return self.kolay_sayfa(ctx);
        }
        self.bekleyeni_ilerlet();
        egui::TopBottomPanel::top("ust").show(ctx, |ui| {
            ui.horizontal(|ui| {
                if ui.small_button("Gizle").on_hover_text("Sistem tepsisine gönderir; katkı arkada sürer").clicked() {
                    tepsiye_gizle(ctx);
                }
                ui.label(RichText::new("modelen").heading().color(KIRMIZI));
                ui.add_space(12.0);
                for (s, ad) in [(Sekme::Kod, "Kod"), (Sekme::Gonullu, "Gönüllü"), (Sekme::Ayarlar, "Ayarlar")] {
                    if ui.selectable_label(self.sekme == s, ad).clicked() {
                        self.sekme = s;
                        self.bildirim.clear();
                    }
                }
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.link("Kolay mod").clicked() {
                        self.ayar.kolay_mod = true;
                        ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(egui::vec2(455.0, 863.0)));
                        let _ = ayar::kaydet(&self.ayar);
                    }
                });
            });
        });
        match self.sekme {
            Sekme::Kod => self.kod_sekmesi(ctx),
            Sekme::Gonullu => self.gonullu_sekmesi(ctx),
            Sekme::Ayarlar => self.ayarlar_sekmesi(ctx),
        }
    }

    fn on_exit(&mut self) {
        let _ = ayar::kaydet(&self.ayar);
        // alt süreçler (işçi, sunucu, koordinatör) uygulamayla birlikte kapansın
        self.isci = None;
        self.sunucu = None;
        self.koord_surec = None;
    }
}

const LOGO_PNG: &[u8] = include_bytes!("../assets/logo-512.png");
const SIMGE_PNG: &[u8] = include_bytes!("../assets/simge-256.png");

fn png_coz(b: &[u8]) -> (Vec<u8>, usize, usize) {
    let r = image::load_from_memory_with_format(b, image::ImageFormat::Png).expect("gömülü PNG bozuk").to_rgba8();
    let (w, h) = (r.width() as usize, r.height() as usize);
    (r.into_raw(), w, h)
}

fn png_yukle(b: &[u8]) -> egui::ColorImage {
    let (rgba, w, h) = png_coz(b);
    egui::ColorImage::from_rgba_unmultiplied([w, h], &rgba)
}

/// Pencere simgesi: Halay Halkası logosu.
fn simge() -> egui::IconData {
    let (rgba, w, h) = png_coz(SIMGE_PNG);
    egui::IconData { rgba, width: w as u32, height: h as u32 }
}

/// Pencere tepsiye gizliyken true: egui'ye yeni çizim istenmez (gizli pencerede istek boşa döner, işlemciyi yer).
static GIZLI: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

fn tepsiye_gizle(ctx: &egui::Context) {
    GIZLI.store(true, Ordering::Relaxed);
    #[cfg(windows)]
    if win::gizle() {
        return;
    }
    ctx.send_viewport_cmd(egui::ViewportCommand::Visible(false));
}

/// Windows'ta "gizli" (SW_HIDE) pencerede eframe yeniden çizim iletisi alamaz ve ana döngü işlemciyi
/// boşuna %100 yer. Bu yüzden tepsiye gizleme şöyle yapılır: pencere ekran dışına taşınır, görev çubuğu
/// düğmesi kalksın diye araç penceresi stiline alınır; pencere teknik olarak "görünür" kalır, döngü uyur.
#[cfg(windows)]
mod win {
    use std::sync::atomic::{AtomicI32, Ordering::Relaxed};

    #[repr(C)]
    #[derive(Default)]
    struct Dik {
        sol: i32,
        ust: i32,
        sag: i32,
        alt: i32,
    }

    #[link(name = "user32")]
    extern "system" {
        fn FindWindowW(sinif: *const u16, baslik: *const u16) -> isize;
        fn ShowWindow(h: isize, komut: i32) -> i32;
        fn SetForegroundWindow(h: isize) -> i32;
        fn PostMessageW(h: isize, ileti: u32, w: usize, l: isize) -> i32;
        fn GetWindowRect(h: isize, r: *mut Dik) -> i32;
        fn SetWindowPos(h: isize, ara: isize, x: i32, y: i32, cx: i32, cy: i32, bayrak: u32) -> i32;
        fn GetWindowLongPtrW(h: isize, indeks: i32) -> isize;
        fn SetWindowLongPtrW(h: isize, indeks: i32, deger: isize) -> isize;
    }

    const GWL_EXSTYLE: i32 = -20;
    const WS_EX_TOOLWINDOW: isize = 0x80;
    const WS_EX_APPWINDOW: isize = 0x4_0000;
    const SWP_NOSIZE_NOZORDER_NOACTIVATE: u32 = 0x0001 | 0x0004 | 0x0010;

    static X: AtomicI32 = AtomicI32::new(100);
    static Y: AtomicI32 = AtomicI32::new(100);

    fn pencere() -> Option<isize> {
        let ad: Vec<u16> = "Modelen".encode_utf16().chain(std::iter::once(0)).collect();
        let h = unsafe { FindWindowW(std::ptr::null(), ad.as_ptr()) };
        (h != 0).then_some(h)
    }

    pub fn gizle() -> bool {
        let Some(h) = pencere() else { return false };
        unsafe {
            let mut r = Dik::default();
            if GetWindowRect(h, &mut r) != 0 && r.sol > -20000 {
                X.store(r.sol, Relaxed);
                Y.store(r.ust, Relaxed);
            }
            ShowWindow(h, 0);
            let st = GetWindowLongPtrW(h, GWL_EXSTYLE);
            SetWindowLongPtrW(h, GWL_EXSTYLE, (st | WS_EX_TOOLWINDOW) & !WS_EX_APPWINDOW);
            SetWindowPos(h, 0, -32000, -32000, 0, 0, SWP_NOSIZE_NOZORDER_NOACTIVATE);
            ShowWindow(h, 8); // SW_SHOWNA
        }
        true
    }

    pub fn goster() -> bool {
        let Some(h) = pencere() else { return false };
        unsafe {
            ShowWindow(h, 0);
            let st = GetWindowLongPtrW(h, GWL_EXSTYLE);
            SetWindowLongPtrW(h, GWL_EXSTYLE, (st & !WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW);
            SetWindowPos(h, 0, X.load(Relaxed), Y.load(Relaxed), 0, 0, SWP_NOSIZE_NOZORDER_NOACTIVATE);
            ShowWindow(h, 9); // SW_RESTORE
            SetForegroundWindow(h);
        }
        true
    }

    pub fn kapat() -> bool {
        let Some(h) = pencere() else { return false };
        unsafe { PostMessageW(h, 0x0010, 0, 0) }; // WM_CLOSE
        true
    }
}

fn pencereyi_goster(ctx: &egui::Context) {
    GIZLI.store(false, Ordering::Relaxed);
    #[cfg(windows)]
    if win::goster() {
        ctx.request_repaint();
        return;
    }
    ctx.send_viewport_cmd(egui::ViewportCommand::Visible(true));
    ctx.send_viewport_cmd(egui::ViewportCommand::Focus);
}

fn uygulamayi_kapat(ctx: &egui::Context) {
    #[cfg(windows)]
    if win::kapat() {
        return;
    }
    ctx.send_viewport_cmd(egui::ViewportCommand::Close);
}

/// Sistem tepsisi simgesi: sol tık pencereyi gösterir, sağ tık menüsü Göster / Çık. Kurulamazsa uygulama tepsisiz çalışır.
fn tepsi_kur(ctx: &egui::Context) -> Option<tray_icon::TrayIcon> {
    use tray_icon::menu::{Menu, MenuEvent, MenuItem};
    use tray_icon::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
    let menu = Menu::new();
    menu.append_items(&[&MenuItem::with_id("goster", "Göster", true, None), &MenuItem::with_id("cik", "Çık", true, None)]).ok()?;
    let (rgba, w, h) = png_coz(SIMGE_PNG);
    let simge = tray_icon::Icon::from_rgba(rgba, w as u32, h as u32).ok()?;
    let t = TrayIconBuilder::new().with_menu(Box::new(menu)).with_menu_on_left_click(false).with_tooltip("Modelen").with_icon(simge).build().ok()?;
    let ctx = ctx.clone();
    std::thread::spawn(move || loop {
        while let Ok(e) = TrayIconEvent::receiver().try_recv() {
            if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = e {
                pencereyi_goster(&ctx);
            }
        }
        while let Ok(e) = MenuEvent::receiver().try_recv() {
            match e.id.0.as_str() {
                "goster" => pencereyi_goster(&ctx),
                "cik" => uygulamayi_kapat(&ctx),
                _ => {}
            }
        }
        std::thread::sleep(Duration::from_millis(100));
    });
    Some(t)
}

fn main() -> eframe::Result<()> {
    let secenekler = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size(if ayar::yukle().kolay_mod { [455.0, 863.0] } else { [1100.0, 760.0] })
            .with_min_inner_size([360.0, 520.0])
            .with_icon(simge())
            .with_title("Modelen"),
        ..Default::default()
    };
    eframe::run_native("Modelen", secenekler, Box::new(|cc| Box::new(Uygulama::yeni(cc))))
}
