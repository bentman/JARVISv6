use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager};

use crate::backend::DesktopState;
use crate::{tray_start_backend, tray_stop_backend};

const MENU_START: &str = "start_jarvis";
const MENU_STOP:  &str = "stop_jarvis";
const MENU_QUIT:  &str = "quit_jarvis";

pub fn setup_tray(app: &AppHandle) -> Result<(), tauri::Error> {
    let start = MenuItem::with_id(app, MENU_START, "Start JARVIS", true, None::<&str>)?;
    let stop  = MenuItem::with_id(app, MENU_STOP,  "Stop JARVIS",  true, None::<&str>)?;
    let quit  = MenuItem::with_id(app, MENU_QUIT,  "Quit",          true, None::<&str>)?;
    let menu  = Menu::with_items(app, &[&start, &stop, &quit])?;

    // Clone the Arc<Mutex<BackendProcessManager>> out of managed state now,
    // before the closure captures it. This avoids the lifetime issue with
    // tauri::State<'_> inside the 'static closure.
    let backend_arc = app.state::<DesktopState>().backend.clone();
    let backend_arc_quit = backend_arc.clone();

    let tray_icon = app.default_window_icon().cloned().ok_or_else(|| {
        tauri::Error::from(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "default window icon missing for tray",
        ))
    })?;

    TrayIconBuilder::new()
        .icon(tray_icon)
        .menu(&menu)
        .on_menu_event(move |app, event| {
            match event.id().as_ref() {
                MENU_START => {
                    if let Err(err) = tray_start_backend(&backend_arc) {
                        eprintln!("tray start_backend failed: {err}");
                    }
                }
                MENU_STOP => {
                    if let Err(err) = tray_stop_backend(&backend_arc) {
                        eprintln!("tray stop_backend failed: {err}");
                    }
                }
                MENU_QUIT => {
                    if let Err(err) = tray_stop_backend(&backend_arc_quit) {
                        eprintln!("tray quit stop_backend failed: {err}");
                    }
                    app.exit(0);
                }
                _ => {}
            }
        })
        .build(app)?;

    Ok(())
}
