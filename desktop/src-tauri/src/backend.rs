use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

// Prevent console window popup and allow GUI-spawned Python to initialize I/O.
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

use reqwest::blocking::Client;

pub const DEFAULT_BACKEND_PORT: u16 = 8765;
const SPAWN_LOG_FILE: &str = "backend_spawn_stderr.log";
const STARTUP_LOG_FILE: &str = "backend_startup.log";

#[derive(Debug)]
pub struct BackendProcessManager {
    child: Option<Child>,
    port: u16,
}

impl Default for BackendProcessManager {
    fn default() -> Self {
        Self {
            child: None,
            port: DEFAULT_BACKEND_PORT,
        }
    }
}

impl BackendProcessManager {
    pub fn spawn_backend(&mut self, port: u16) -> Result<(), String> {
        if self.is_running() {
            self.port = port;
            return Ok(());
        }

        let repo_root = resolve_repo_root()?;
        let python_path = repo_root.join("backend").join(".venv").join("Scripts").join("python.exe");
        let backend_entry = repo_root.join("scripts").join("run_backend.py");

        if !python_path.exists() {
            return Err(format!("missing backend python path: {}", python_path.display()));
        }
        if !backend_entry.exists() {
            return Err(format!("missing backend entrypoint: {}", backend_entry.display()));
        }

        let stderr_log = repo_root.join("reports").join("backend_spawn_stderr.log");
        std::fs::create_dir_all(repo_root.join("reports"))
            .map_err(|e| format!("failed to create reports dir: {e}"))?;
        let stderr_file = std::fs::File::create(&stderr_log)
            .map_err(|e| format!("failed to create stderr log: {e}"))?;
        let stdout_file = stderr_file.try_clone()
            .map_err(|e| format!("failed to clone stderr log: {e}"))?;

        let mut cmd = Command::new(&python_path);
        cmd.arg(backend_entry)
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg(port.to_string())
            .env("PYTHONUTF8", "1")
            .env("PYTHONIOENCODING", "utf-8")
            .current_dir(&repo_root)
            .stdout(std::process::Stdio::from(stdout_file))
            .stderr(std::process::Stdio::from(stderr_file));

        #[cfg(target_os = "windows")]
        cmd.creation_flags(CREATE_NO_WINDOW);

        let mut child = cmd
            .spawn()
            .map_err(|err| format!("failed to spawn backend: {err}"))?;

        // Detect immediate startup failures and surface concrete cause.
        thread::sleep(Duration::from_millis(350));
        if let Some(status) = child
            .try_wait()
            .map_err(|err| format!("failed backend status check after spawn: {err}"))?
        {
            let log_excerpt = read_spawn_log_tail(40);
            return Err(format!(
                "backend exited immediately after spawn (status: {status}). spawn log tail:\n{log_excerpt}"
            ));
        }

        self.port = port;
        self.child = Some(child);
        Ok(())
    }

    pub fn wait_healthy(&mut self, url: &str, timeout_ms: u64) -> Result<(), String> {
        let client = Client::builder()
            .timeout(Duration::from_millis(700))
            .build()
            .map_err(|err| format!("failed to build health client: {err}"))?;

        let deadline = Instant::now() + Duration::from_millis(timeout_ms);
        while Instant::now() < deadline {
            if let Some(child) = self.child.as_mut() {
                if let Some(status) = child
                    .try_wait()
                    .map_err(|err| format!("failed backend status check during health wait: {err}"))?
                {
                    self.child = None;
                    return Err(format!(
                        "backend exited before becoming healthy (status: {status}). spawn log tail:\n{}\nstartup log tail:\n{}",
                        read_spawn_log_tail(40),
                        read_startup_log_tail(40)
                    ));
                }
            } else {
                return Err("backend process handle missing during health wait".to_string());
            }

            if let Ok(resp) = client.get(url).send() {
                if resp.status().is_success() {
                    return Ok(());
                }
            }
            thread::sleep(Duration::from_millis(250));
        }

        Err(format!(
            "backend health check timed out after {timeout_ms}ms for {url}. spawn log tail:\n{}\nstartup log tail:\n{}",
            read_spawn_log_tail(40),
            read_startup_log_tail(40)
        ))
    }

    pub fn kill_backend(&mut self) -> Result<(), String> {
        let Some(child) = self.child.as_mut() else {
            return Ok(());
        };

        if child
            .try_wait()
            .map_err(|err| format!("failed backend status check: {err}"))?
            .is_some()
        {
            self.child = None;
            return Ok(());
        }

        child
            .kill()
            .map_err(|err| format!("failed to terminate backend process: {err}"))?;
        child
            .wait()
            .map_err(|err| format!("failed waiting for backend process exit: {err}"))?;

        self.child = None;
        Ok(())
    }

    pub fn is_running(&mut self) -> bool {
        let Some(child) = self.child.as_mut() else {
            return false;
        };

        match child.try_wait() {
            Ok(Some(_)) => {
                self.child = None;
                false
            }
            Ok(None) => true,
            Err(_) => {
                self.child = None;
                false
            }
        }
    }

    pub fn port(&self) -> u16 {
        self.port
    }
}

pub struct DesktopState {
    pub backend: Arc<Mutex<BackendProcessManager>>,
}

impl Default for DesktopState {
    fn default() -> Self {
        Self {
            backend: Arc::new(Mutex::new(BackendProcessManager::default())),
        }
    }
}

pub fn health_url(port: u16) -> String {
    format!("http://127.0.0.1:{port}/health")
}

pub fn read_spawn_log_tail(max_lines: usize) -> String {
    let repo_root = match resolve_repo_root() {
        Ok(root) => root,
        Err(err) => return format!("<unable to resolve repo root: {err}>"),
    };
    let log_path = repo_root.join("reports").join(SPAWN_LOG_FILE);
    let content = match std::fs::read_to_string(&log_path) {
        Ok(content) => content,
        Err(err) => return format!("<unable to read {}: {err}>", log_path.display()),
    };

    let tail: Vec<&str> = content.lines().rev().take(max_lines).collect();
    if tail.is_empty() {
        return format!("<{} is empty>", log_path.display());
    }

    tail.into_iter().rev().collect::<Vec<&str>>().join("\n")
}

pub fn read_startup_log_tail(max_lines: usize) -> String {
    let repo_root = match resolve_repo_root() {
        Ok(root) => root,
        Err(err) => return format!("<unable to resolve repo root: {err}>"),
    };
    let log_path = repo_root.join("reports").join(STARTUP_LOG_FILE);
    let content = match std::fs::read_to_string(&log_path) {
        Ok(content) => content,
        Err(err) => return format!("<unable to read {}: {err}>", log_path.display()),
    };

    let tail: Vec<&str> = content.lines().rev().take(max_lines).collect();
    if tail.is_empty() {
        return format!("<{} is empty>", log_path.display());
    }

    tail.into_iter().rev().collect::<Vec<&str>>().join("\n")
}

fn resolve_repo_root() -> Result<PathBuf, String> {
    // Use the compile-time manifest dir directly without canonicalize().
    // canonicalize() adds \\?\ prefix on Windows which breaks Python imports.
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..");
    // Normalize without canonicalize by using components
    Ok(p)
}
