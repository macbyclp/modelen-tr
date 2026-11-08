//! Modelen kurulum programı: `kur.ps1` derleme sırasında içine gömülür; çalışınca geçici klasöre yazılıp
//! Windows PowerShell ile çalıştırılır. Komut satırı bağımsız değişkenleri betiğe aktarılır
//! (örn. `Modelen-Kurulum.exe -Dene`, `-Hedef D:\Modelen`, `-CudaSurumu cu121`).
//! Betik yönetici yetkisi istemez ve her şeyi tek klasöre kurar.

use std::io::{self, Write};
use std::path::PathBuf;
use std::process::{exit, Command};

/// kur.ps1 (UTF-8 BOM'lu; Windows PowerShell 5.1 Türkçe karakterleri böyle doğru okur).
const BETIK: &str = include_str!("../../kur.ps1");

fn bekle() {
    print!("\nKapatmak için Enter'a basın...");
    let _ = io::stdout().flush();
    let mut s = String::new();
    let _ = io::stdin().read_line(&mut s);
}

fn temizle(dizin: &PathBuf) {
    let _ = std::fs::remove_dir_all(dizin);
}

fn main() {
    let ek: Vec<String> = std::env::args().skip(1).collect();
    println!("Modelen kurulumu (sürüm {})", env!("CARGO_PKG_VERSION"));
    println!("Bu program yönetici yetkisi istemez; her şeyi tek bir klasöre kurar.\n");

    let dizin = std::env::temp_dir().join(format!("modelen-kurulum-{}", std::process::id()));
    if let Err(e) = std::fs::create_dir_all(&dizin) {
        eprintln!("Geçici klasör oluşturulamadı: {e}");
        bekle();
        exit(2);
    }
    let yol = dizin.join("kur.ps1");
    if let Err(e) = std::fs::write(&yol, BETIK.as_bytes()) {
        eprintln!("Kurulum betiği yazılamadı: {e}");
        temizle(&dizin);
        bekle();
        exit(2);
    }

    let durum = Command::new("powershell")
        .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"])
        .arg(&yol)
        .args(&ek)
        .status();
    temizle(&dizin);

    let kod = match durum {
        Ok(d) => d.code().unwrap_or(1),
        Err(e) => {
            eprintln!("PowerShell başlatılamadı: {e}");
            2
        }
    };
    if kod != 0 {
        eprintln!("\nKurulum tamamlanamadı (çıkış kodu {kod}). Yukarıdaki HATA satırını GitHub'da bildirebilirsiniz:\nhttps://github.com/macbyclp/modelen-tr/issues");
    }
    bekle();
    exit(kod);
}
