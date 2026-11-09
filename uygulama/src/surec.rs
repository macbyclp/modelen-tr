//! Gönüllü işçi ve yerel model sunucusu gibi alt süreçlerin yönetimi, GPU bilgisi, koordinatör durumu, dosya ağacı.

use serde_json::Value;
use std::collections::VecDeque;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const SON_SATIR: usize = 400;

pub struct Surec {
    child: Child,
    pub gunluk: Arc<Mutex<VecDeque<String>>>,
    /// İşçi çıktısında tamamlanan tur sayısı ("... adım, ... yük ..." satırları)
    pub tamamlanan: Arc<AtomicUsize>,
}

fn komut(prog: &str) -> Command {
    let c = Command::new(prog);
    #[cfg(windows)]
    {
        let mut c = c;
        c.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        return c;
    }
    #[cfg(not(windows))]
    c
}

fn okuyucu(mut r: impl Read + Send + 'static, gunluk: Arc<Mutex<VecDeque<String>>>, sayac: Arc<AtomicUsize>) {
    std::thread::spawn(move || {
        let (mut satir, mut b) = (Vec::<u8>::new(), [0u8; 1]);
        let it = |satir: &mut Vec<u8>| {
            if !satir.is_empty() {
                let s = String::from_utf8_lossy(satir).to_string();
                if tur_tamam(&s) {
                    sayac.fetch_add(1, Ordering::Relaxed);
                }
                let mut g = gunluk.lock().unwrap();
                if g.len() >= SON_SATIR {
                    g.pop_front();
                }
                g.push_back(s);
                satir.clear();
            }
        };
        // tqdm ilerleme çubukları \r ile biter: hem \r hem \n satır sonu sayılır
        while let Ok(1) = r.read(&mut b) {
            if b[0] == b'\n' || b[0] == b'\r' {
                it(&mut satir);
            } else {
                satir.push(b[0]);
            }
        }
        it(&mut satir);
    });
}

impl Surec {
    pub fn baslat(program: &str, klasor: &str, argumanlar: &[String]) -> Result<Surec, String> {
        Self::baslat_env(program, klasor, argumanlar, &[])
    }

    /// `baslat` + ek ortam değişkenleri (sırlar komut satırında değil, ortamda geçer; `ps`/görev yöneticisinde görünmez).
    pub fn baslat_env(program: &str, klasor: &str, argumanlar: &[String], ortam: &[(&str, &str)]) -> Result<Surec, String> {
        if !Path::new(klasor).join(argumanlar.first().map(String::as_str).unwrap_or("")).exists() {
            return Err(format!("dosya bulunamadı: {}", Path::new(klasor).join(argumanlar.first().map(String::as_str).unwrap_or("")).display()));
        }
        let mut c = komut(program);
        c.args(argumanlar)
            .current_dir(klasor)
            .env("PYTHONIOENCODING", "utf-8")
            .env("PYTHONUNBUFFERED", "1")
            .envs(ortam.iter().copied())
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        let mut child = c.spawn().map_err(|e| format!("başlatılamadı ({program}): {e}"))?;
        let gunluk = Arc::new(Mutex::new(VecDeque::new()));
        let tamamlanan = Arc::new(AtomicUsize::new(0));
        okuyucu(child.stdout.take().unwrap(), gunluk.clone(), tamamlanan.clone());
        okuyucu(child.stderr.take().unwrap(), gunluk.clone(), tamamlanan.clone());
        Ok(Surec { child, gunluk, tamamlanan })
    }

    pub fn calisiyor(&mut self) -> bool {
        matches!(self.child.try_wait(), Ok(None))
    }

    pub fn durdur(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }

    pub fn son_satirlar(&self, n: usize) -> Vec<String> {
        let g = self.gunluk.lock().unwrap();
        g.iter().skip(g.len().saturating_sub(n)).cloned().collect()
    }
}

impl Drop for Surec {
    fn drop(&mut self) {
        self.durdur();
    }
}

/// İşçinin bir turu bitirip yüklediğini gösteren satır (isci.py çıktısı).
pub fn tur_tamam(satir: &str) -> bool {
    satir.contains(" adım, ") && satir.contains("yük ") && !satir.contains("reddedildi")
}

/// Teknik hata satırını sade Türkçeye çevirir; tanınmazsa satırı olduğu gibi verir.
pub fn dostca(satir: &str) -> String {
    let k = satir.to_lowercase();
    if satir.contains("429") {
        "Çok sık soru gönderdiniz, birkaç dakika bekleyin.".into()
    } else if satir.contains("10061") || k.contains("connection refused") || k.contains("urlerror") {
        "Koordinatöre bağlanılamadı. Sunucu kapalı olabilir ya da adres yanlış.".into()
    } else if satir.contains("CUDA GPU bulunamadı") {
        "NVIDIA ekran kartı (CUDA) bulunamadı; katkı için gerekli.".into()
    } else if k.contains("out of memory") {
        "Ekran kartı belleği yetmedi. Başka GPU kullanan uygulamaları kapatın.".into()
    } else {
        satir.to_string()
    }
}

/// Soruyu topluluğa (koordinatör /soru) gönderir; başarıda soru numarasını döndürür.
pub fn soru_gonder(adres: &str, isci: &str, soru: &str, baglam: &str, anahtar: &str) -> Result<u64, String> {
    let ajan = ureq::AgentBuilder::new().timeout(Duration::from_secs(10)).build();
    let govde = serde_json::json!({"soru": soru, "baglam": baglam, "isci": isci, "surum": env!("CARGO_PKG_VERSION")});
    let mut istek = ajan.post(&format!("{}/soru", adres.trim_end_matches('/')));
    if !anahtar.is_empty() {
        istek = istek.set("X-Anahtar", anahtar);
    }
    let v: Value = istek
        .send_json(govde)
        .map_err(|e| e.to_string())?
        .into_json()
        .map_err(|e| e.to_string())?;
    Ok(v["no"].as_u64().unwrap_or(0))
}

/// Adres yerel makineyi gösteriyor mu (127.0.0.1 / localhost)?
pub fn yerel_adres(adres: &str) -> Option<u16> {
    let a = adres.trim().trim_start_matches("http://").trim_start_matches("https://");
    let (host, port) = a.trim_end_matches('/').split_once(':')?;
    if host == "127.0.0.1" || host == "localhost" {
        port.parse().ok()
    } else {
        None
    }
}

/// Yerel portta dinleyen var mı?
pub fn port_acik(port: u16) -> bool {
    use std::net::{SocketAddr, TcpStream};
    TcpStream::connect_timeout(&SocketAddr::from(([127, 0, 0, 1], port)), Duration::from_millis(300)).is_ok()
}

/// nvidia-smi ile GPU adı, VRAM ve kullanım. GPU yoksa açıklayıcı metin.
pub fn gpu_bilgi() -> String {
    let c = komut("nvidia-smi")
        .args(["--query-gpu=name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"])
        .output();
    match c {
        Ok(o) if o.status.success() => {
            let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
            if s.is_empty() { "GPU bulunamadı".into() } else { s }
        }
        _ => "NVIDIA GPU/nvidia-smi bulunamadı (eğitim şu an yalnızca CUDA ile çalışır)".into(),
    }
}

/// Koordinatör /durum özeti (okunur metin).
pub fn koordinator_durumu(adres: &str, anahtar: &str) -> Result<String, String> {
    let ajan = ureq::AgentBuilder::new().timeout(Duration::from_secs(5)).build();
    let mut i = ajan.get(&format!("{}/durum", adres.trim_end_matches('/')));
    if !anahtar.is_empty() {
        i = i.set("X-Anahtar", anahtar);
    }
    let v: Value = i.call().map_err(|e| e.to_string())?.into_json().map_err(|e| e.to_string())?;
    Ok(durum_ozeti(&v))
}

pub fn durum_ozeti(v: &Value) -> String {
    let tur = v["tur"].as_u64().unwrap_or(0);
    let top = v["toplam_tur"].as_u64().unwrap_or(0);
    let bek = v["bekleyen_sonuc"].as_array().map(|a| a.len()).unwrap_or(0);
    let isci = v["isciler"].as_object().map(|o| o.len()).unwrap_or(0);
    let yuk = v["trafik"]["yuklenen_bayt"].as_f64().unwrap_or(0.0) / 1e6;
    let ind = v["trafik"]["indirilen_bayt"].as_f64().unwrap_or(0.0) / 1e6;
    format!("tur {tur}/{top} · bu turda {bek} sonuç bekliyor · {isci} işçi görüldü · indirilen {ind:.0} MB · yüklenen {yuk:.0} MB")
}

pub struct Dugum {
    pub ad: String,
    pub yol: PathBuf,
    pub cocuklar: Vec<Dugum>,
    pub klasor: bool,
}

const ATLA: &[&str] = &[".git", "node_modules", "target", ".venv", "__pycache__", ".idea", "dist", "build"];

pub fn agac(yol: &Path, derinlik: u32) -> Vec<Dugum> {
    let Ok(rd) = std::fs::read_dir(yol) else { return vec![] };
    let mut v: Vec<Dugum> = rd
        .flatten()
        .filter_map(|e| {
            let ad = e.file_name().to_string_lossy().into_owned();
            let klasor = e.file_type().ok()?.is_dir();
            if klasor && (ATLA.contains(&ad.as_str()) || derinlik == 0) {
                return None;
            }
            let yol = e.path();
            let cocuklar = if klasor { agac(&yol, derinlik - 1) } else { vec![] };
            Some(Dugum { ad, yol, cocuklar, klasor })
        })
        .collect();
    v.sort_by(|a, b| b.klasor.cmp(&a.klasor).then(a.ad.to_lowercase().cmp(&b.ad.to_lowercase())));
    v
}

#[cfg(test)]
mod testler {
    use super::*;

    #[test]
    fn durum_ozeti_okunur() {
        let v: Value = serde_json::from_str(
            r#"{"tur":2,"toplam_tur":6,"bekleyen_sonuc":["a"],"isciler":{"a":1.0,"b":2.0},"trafik":{"indirilen_bayt":80800000,"yuklenen_bayt":40400000}}"#,
        )
        .unwrap();
        let s = durum_ozeti(&v);
        assert!(s.contains("tur 2/6") && s.contains("1 sonuç") && s.contains("2 işçi") && s.contains("81 MB") && s.contains("40 MB"), "{s}");
    }

    #[test]
    fn dostca_ve_sayac() {
        assert!(dostca("urllib.error.URLError: <urlopen error [WinError 10061] x>").starts_with("Koordinatöre bağlanılamadı"));
        assert!(dostca("CUDA GPU bulunamadı; prototip işçi GPU gerektirir.").contains("NVIDIA"));
        assert_eq!(dostca("başka bir şey"), "başka bir şey");
        assert!(tur_tamam("[işçi a] tur 2 20 adım, 31 sn, yük 40.4 MB -> {}"));
        assert!(!tur_tamam("[işçi a] tur 2 reddedildi: 409 x"));
        assert_eq!(yerel_adres("http://127.0.0.1:8750"), Some(8750));
        assert_eq!(yerel_adres("https://ornek.org:8750"), None);
    }

    #[test]
    fn soru_sahte_sunucuya_gider() {
        use std::io::{Read, Write};
        let dinle = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = dinle.local_addr().unwrap().port();
        let sunucu = std::thread::spawn(move || {
            let (mut c, _) = dinle.accept().unwrap();
            c.set_read_timeout(Some(Duration::from_millis(400))).unwrap();
            let mut alinan = Vec::new();
            let mut tampon = [0u8; 4096];
            while let Ok(n) = c.read(&mut tampon) {
                if n == 0 {
                    break;
                }
                alinan.extend_from_slice(&tampon[..n]);
            }
            let g = r#"{"tamam":true,"no":7}"#;
            let _ = write!(c, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}", g.len(), g);
            String::from_utf8_lossy(&alinan).to_string()
        });
        let no = soru_gonder(&format!("http://127.0.0.1:{port}"), "ali", "Merhaba, nasılsınız?", "", "").unwrap();
        assert_eq!(no, 7);
        let istek = sunucu.join().unwrap();
        assert!(istek.starts_with("POST /soru"), "{istek}");
        assert!(istek.contains("Merhaba") && istek.contains("\"isci\":\"ali\""), "{istek}");
        assert!(dostca("status code 429").contains("Çok sık"));
    }

    #[test]
    fn agac_gereksizleri_atlar() {
        let d = std::env::temp_dir().join(format!("modelen-agac-{}", std::process::id()));
        std::fs::create_dir_all(d.join("src")).unwrap();
        std::fs::create_dir_all(d.join("target")).unwrap();
        std::fs::write(d.join("src").join("a.rs"), "x").unwrap();
        std::fs::write(d.join("b.py"), "y").unwrap();
        let a = agac(&d, 3);
        let adlar: Vec<&str> = a.iter().map(|n| n.ad.as_str()).collect();
        assert_eq!(adlar, ["src", "b.py"]);
        assert_eq!(a[0].cocuklar.len(), 1);
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn surec_calisir_ve_durdurulur() {
        let d = std::env::temp_dir();
        let f = d.join(format!("modelen-surec-{}.py", std::process::id()));
        std::fs::write(&f, "import time\nprint('merhaba', flush=True)\ntime.sleep(30)\n").unwrap();
        let py = if cfg!(windows) { "python" } else { "python3" };
        let Ok(mut s) = Surec::baslat(py, d.to_str().unwrap(), &[f.file_name().unwrap().to_string_lossy().into_owned()]) else {
            return; // python yoksa atla
        };
        for _ in 0..50 {
            if s.son_satirlar(5).iter().any(|l| l == "merhaba") {
                break;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        assert!(s.son_satirlar(5).iter().any(|l| l == "merhaba"));
        assert!(s.calisiyor());
        s.durdur();
        assert!(!s.calisiyor());
        let _ = std::fs::remove_file(f);
    }

    #[test]
    fn ortam_degiskeni_surece_gecer_komut_satirina_degil() {
        let d = std::env::temp_dir();
        let f = d.join(format!("modelen-ortam-{}.py", std::process::id()));
        std::fs::write(&f, "import os
print('anahtar=' + os.environ.get('MODELEN_ANAHTAR', 'YOK'), flush=True)
").unwrap();
        let py = if cfg!(windows) { "python" } else { "python3" };
        let ad = f.file_name().unwrap().to_string_lossy().into_owned();
        let Ok(mut s) = Surec::baslat_env(py, d.to_str().unwrap(), &[ad.clone()], &[("MODELEN_ANAHTAR", "gizli-123")]) else {
            return; // python yoksa atla
        };
        for _ in 0..50 {
            if s.son_satirlar(5).iter().any(|l| l.starts_with("anahtar=")) {
                break;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        assert!(s.son_satirlar(5).iter().any(|l| l == "anahtar=gizli-123"));
        assert!(!ad.contains("gizli"), "anahtar komut satırında olmamalı");
        s.durdur();
        let _ = std::fs::remove_file(f);
    }
}
