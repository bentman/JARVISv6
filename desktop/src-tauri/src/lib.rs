mod backend;
mod tray;

use std::sync::{Arc, Mutex};

use backend::{BackendProcessManager, DesktopState};

pub const BACKEND_PORT: u16 = 8765;
fn health_url() -> String { format!("http://127.0.0.1:{BACKEND_PORT}/health") }

fn start_backend_lifecycle(
    backend_arc: &Arc<Mutex<BackendProcessManager>>,
    port: u16,
) -> Result<(), String> {
    let mut mgr = backend_arc
        .lock()
        .map_err(|_| "backend manager lock poisoned".to_string())?;

    mgr.kill_backend()?;
    mgr.spawn_backend(port)?;
    let url = backend::health_url(port);
    if let Err(err) = mgr.wait_healthy(&url, 30_000) {
        let _ = mgr.kill_backend();
        return Err(format!("backend failed startup health gate: {err}"));
    }

    Ok(())
}

fn stop_backend_lifecycle(backend_arc: &Arc<Mutex<BackendProcessManager>>) -> Result<(), String> {
    let mut mgr = backend_arc
        .lock()
        .map_err(|_| "backend manager lock poisoned".to_string())?;
    mgr.kill_backend()
}

pub(crate) fn start_backend_shared_path(backend_arc: &Arc<Mutex<BackendProcessManager>>) -> Result<(), String> {
    start_backend_lifecycle(backend_arc, BACKEND_PORT)
}

pub(crate) fn stop_backend_shared_path(backend_arc: &Arc<Mutex<BackendProcessManager>>) -> Result<(), String> {
    stop_backend_lifecycle(backend_arc)
}

pub(crate) fn tray_start_backend(backend_arc: &Arc<Mutex<BackendProcessManager>>) -> Result<(), String> {
    start_backend_shared_path(backend_arc)
}

pub(crate) fn tray_stop_backend(backend_arc: &Arc<Mutex<BackendProcessManager>>) -> Result<(), String> {
    stop_backend_shared_path(backend_arc)
}

#[tauri::command]
fn start_backend(state: tauri::State<'_, DesktopState>) -> Result<String, String> {
    start_backend_shared_path(&state.backend)
        .map_err(|err| format!("start_backend command entered; spawn failed: {err}"))?;
    Ok(format!("backend healthy on port {BACKEND_PORT}"))
}

#[tauri::command]
fn health_check(state: tauri::State<'_, DesktopState>) -> Result<String, String> {
    // Non-blocking single health probe. JS polls this until "ok".
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;

    let backend_running = {
        let mut mgr = state
            .backend
            .lock()
            .map_err(|_| "backend manager lock poisoned".to_string())?;
        mgr.is_running()
    };

    match client.get(health_url()).send() {
        Ok(resp) if resp.status().is_success() => {
            let text = resp.text().map_err(|e| e.to_string())?;
            Ok(text)
        }
        Ok(resp) => Ok(format!(
            "{{\"status\":\"error\",\"error\":\"health returned non-success status {}\"}}",
            resp.status().as_u16()
        )),
        Err(_) if backend_running => Ok("{\"status\":\"starting\"}".to_string()),
        Err(_) => Ok(
            "{\"status\":\"error\",\"error\":\"backend process is not running\"}".to_string(),
        ),
    }
}

#[tauri::command]
fn stop_backend(state: tauri::State<'_, DesktopState>) -> Result<(), String> {
    stop_backend_shared_path(&state.backend)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(DesktopState::default())
        .invoke_handler(tauri::generate_handler![start_backend, stop_backend, health_check])
        .setup(|app| {
            tray::setup_tray(app.handle())?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                use tauri::Manager;
                if let Err(err) = stop_backend_lifecycle(&window.app_handle().state::<DesktopState>().backend) {
                    eprintln!("window close stop_backend failed: {err}");
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
