fn main() {
    #[cfg(windows)]
    {
        let mut r = winresource::WindowsResource::new();
        r.set_icon("assets/simge.ico");
        r.set("ProductName", "Modelen");
        r.set("FileDescription", "Modelen");
        if let Err(e) = r.compile() {
            println!("cargo:warning=exe simgesi gömülemedi: {e}");
        }
    }
}
