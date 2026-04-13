// build.rs — forces Cargo to recheck on every build
fn main() {
    println!("cargo:rerun-if-changed=src/lib.rs");
    println!("cargo:rerun-if-changed=src/backend.rs");
    println!("cargo:rerun-if-changed=src/tray.rs");
    println!("cargo:rerun-if-changed=src/main.rs");
    tauri_build::build()
}
