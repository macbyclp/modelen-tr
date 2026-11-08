fn main() {
    println!("cargo:rerun-if-changed=../kur.ps1");
    println!("cargo:rerun-if-changed=../uygulama/assets/simge.ico");
    #[cfg(windows)]
    {
        let mut res = winresource::WindowsResource::new();
        res.set_icon("../uygulama/assets/simge.ico");
        res.set("ProductName", "Modelen Kurulum");
        res.set("FileDescription", "Modelen gönüllü kurulum programı");
        res.set("LegalCopyright", "Apache-2.0");
        if let Err(e) = res.compile() {
            println!("cargo:warning=simge gömülemedi: {e}");
        }
    }
}
