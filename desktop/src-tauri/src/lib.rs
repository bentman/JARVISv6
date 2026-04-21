mod backend;
mod tray;

use std::sync::{Arc, Mutex};

use backend::{BackendProcessManager, DesktopState};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut};

pub const BACKEND_PORT: u16 = 8765;
const DEFAULT_POST_TIMEOUT_SECS: u64 = 3;
const SESSION_START_TIMEOUT_SECS: u64 = 8;
fn health_url() -> String { format!("http://127.0.0.1:{BACKEND_PORT}/health") }
fn session_start_url() -> String { format!("http://127.0.0.1:{BACKEND_PORT}/session/start") }
fn session_state_url() -> String { format!("http://127.0.0.1:{BACKEND_PORT}/session/state") }
fn session_ptt_url() -> String { format!("http://127.0.0.1:{BACKEND_PORT}/session/ptt") }
fn session_text_url() -> String { format!("http://127.0.0.1:{BACKEND_PORT}/session/text") }

fn post_json_empty(url: &str) -> Result<String, String> {
    post_json_empty_with_timeout(url, DEFAULT_POST_TIMEOUT_SECS)
}

fn post_json_empty_with_timeout(url: &str, timeout_secs: u64) -> Result<String, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(timeout_secs))
        .build()
        .map_err(|e| format!("failed to build http client: {e}"))?;
    let resp = client
        .post(url)
        .send()
        .map_err(|e| format!("POST {url} failed: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("POST {url} non-success status {}", resp.status().as_u16()));
    }
    resp.text().map_err(|e| format!("POST {url} response read failed: {e}"))
}

fn post_json_body(url: &str, body: &str) -> Result<String, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
        .map_err(|e| format!("failed to build http client: {e}"))?;
    let resp = client
        .post(url)
        .header("Content-Type", "application/json")
        .body(body.to_string())
        .send()
        .map_err(|e| format!("POST {url} failed: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("POST {url} non-success status {}", resp.status().as_u16()));
    }
    resp.text().map_err(|e| format!("POST {url} response read failed: {e}"))
}

fn register_ptt_hotkey(app: &tauri::AppHandle) -> Result<(), String> {
    let shortcut = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::KeyJ);
    let ptt_url = session_ptt_url();
    app.global_shortcut()
        .on_shortcut(shortcut, move |_app, _shortcut, _event| {
            let _ = post_json_empty(&ptt_url);
        })
        .map_err(|e| format!("failed to register global hotkey Ctrl+Alt+J: {e}"))
}

fn start_backend_lifecycle(
    backend_arc: &Arc<Mutex<BackendProcessManager>>,
    port: u16,
) -> Result<(), String> {
    {
        let mut mgr = backend_arc
            .lock()
            .map_err(|_| "backend manager lock poisoned".to_string())?;
        mgr.kill_backend()?;
        mgr.spawn_backend(port)?;
    }

    let url = backend::health_url(port);
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_millis(700))
        .build()
        .map_err(|err| format!("failed to build startup health client: {err}"))?;
    let deadline = std::time::Instant::now() + std::time::Duration::from_millis(30_000);

    while std::time::Instant::now() < deadline {
        let backend_running = {
            let mut mgr = backend_arc
                .lock()
                .map_err(|_| "backend manager lock poisoned".to_string())?;
            mgr.is_running()
        };

        if !backend_running {
            let mut mgr = backend_arc
                .lock()
                .map_err(|_| "backend manager lock poisoned".to_string())?;
            let _ = mgr.kill_backend();
            return Err(format!(
                "backend failed startup health gate: backend exited before becoming healthy. spawn log tail:\n{}\nstartup log tail:\n{}",
                backend::read_spawn_log_tail(40),
                backend::read_startup_log_tail(40)
            ));
        }

        if let Ok(resp) = client.get(&url).send() {
            if resp.status().is_success() {
                break;
            }
        }

        std::thread::sleep(std::time::Duration::from_millis(250));
    }

    if std::time::Instant::now() >= deadline {
        let mut mgr = backend_arc
            .lock()
            .map_err(|_| "backend manager lock poisoned".to_string())?;
        let _ = mgr.kill_backend();
        return Err(format!(
            "backend failed startup health gate: backend health check timed out after 30000ms for {url}. spawn log tail:\n{}\nstartup log tail:\n{}",
            backend::read_spawn_log_tail(40),
            backend::read_startup_log_tail(40)
        ));
    }

    let _ = post_json_empty_with_timeout(&session_start_url(), SESSION_START_TIMEOUT_SECS)
        .map_err(|err| format!("backend healthy but /session/start failed: {err}"))?;

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
fn session_state() -> Result<String, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;

    let resp = client
        .get(session_state_url())
        .send()
        .map_err(|e| format!("session_state request failed: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("session_state returned non-success status {}", resp.status().as_u16()));
    }

    resp.text().map_err(|e| format!("session_state read failed: {e}"))
}

#[tauri::command]
fn push_to_talk() -> Result<String, String> {
    post_json_empty(&session_ptt_url())
}

#[tauri::command]
fn submit_text(text: String) -> Result<String, String> {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return Err("text must not be empty".to_string());
    }

    let escaped = trimmed.replace('\\', "\\\\").replace('"', "\\\"");
    let body = format!("{{\"text\":\"{escaped}\"}}");
    post_json_body(&session_text_url(), &body)
}

#[tauri::command]
fn stop_backend(state: tauri::State<'_, DesktopState>) -> Result<(), String> {
    stop_backend_shared_path(&state.backend)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .manage(DesktopState::default())
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            health_check,
            session_state,
            push_to_talk,
            submit_text,
        ])
        .setup(|app| {
            tray::setup_tray(app.handle())?;
            register_ptt_hotkey(app.handle())
                .map_err(|err| tauri::Error::from(std::io::Error::new(std::io::ErrorKind::Other, err)))?;
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
