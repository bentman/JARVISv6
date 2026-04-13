function invoke(cmd, args) {
  var tauriInvoke =
    (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) ||
    (window.__TAURI_INTERNALS__ && window.__TAURI_INTERNALS__.invoke);

  if (!tauriInvoke) {
    return Promise.reject(new Error("Tauri invoke API unavailable in window context"));
  }

  try {
    return tauriInvoke(cmd, args || {});
  } catch (e) {
    return Promise.reject(e);
  }
}

var statusDot     = document.getElementById("status-dot");
var statusLabel   = document.getElementById("status-label");
var rStt          = document.getElementById("r-stt");
var rTts          = document.getElementById("r-tts");
var rLlm          = document.getElementById("r-llm");
var rProfile      = document.getElementById("r-profile");
var degradedBlock = document.getElementById("degraded-block");
var startBtn      = document.getElementById("start-btn");
var stopBtn       = document.getElementById("stop-btn");
var statusBarText = document.getElementById("status-bar-text");
var emptyState    = document.getElementById("empty-state");
var inputBar      = document.getElementById("input-bar");

var appStatus = "stopped";
var isStarting = false;
var elapsedTimer = null;
var elapsed = 0;
var healthPollTimer = null;
var healthErrorCount = 0;

function applyStatus(status) {
  appStatus = status;
  statusDot.dataset.status = status;
  var labels = {
    stopped: "Stopped", starting: "Starting\u2026",
    healthy: "Ready", degraded: "Degraded"
  };
  statusLabel.textContent = labels[status] || status;
  if (status !== "starting") statusBarText.textContent = labels[status] || status;
  var running = status === "healthy" || status === "degraded";
  startBtn.disabled = running || isStarting;
  stopBtn.disabled = !running && !isStarting;
  if (inputBar) inputBar.style.display = "none"; // 6.2: lifecycle only
}

function setReadinessVal(el, ready) {
  if (!el) return;
  el.textContent = ready ? "\u2713 ready" : "\u2717 unavail";
  el.dataset.ok = ready ? "true" : "false";
}

function clearReadiness() {
  [rStt, rTts, rLlm, rProfile].forEach(function(el) {
    if (el) { el.textContent = "\u2014"; delete el.dataset.ok; }
  });
}

function showError(msg) {
  applyStatus("stopped");
  statusBarText.textContent = "FAILED: " + msg;
  if (emptyState) {
    emptyState.innerHTML =
      "<span class='empty-icon'>\u2717</span>" +
      "<p style='color:#f85149;font-weight:700'>Start failed</p>" +
      "<p class='empty-sub' style='color:#f85149'>" + msg + "</p>";
  }
}

function stopTimers() {
  if (elapsedTimer)    { clearInterval(elapsedTimer);    elapsedTimer = null; }
  if (healthPollTimer) { clearInterval(healthPollTimer); healthPollTimer = null; }
}

function startHealthPolling() {
  // Poll health_check every 500ms until "ok" or error or 180s timeout
  elapsed = 0;
  healthErrorCount = 0;
  elapsedTimer = setInterval(function() {
    elapsed++;
    statusBarText.textContent = "Starting\u2026 (" + elapsed + "s)";
    if (elapsed >= 180) {
      stopTimers();
      isStarting = false;
      showError("timed out after 180s");
    }
  }, 1000);

  healthPollTimer = setInterval(function() {
    invoke("health_check").then(function(raw) {
      var h;
      try { h = JSON.parse(raw); } catch(e) { return; }
      if (h.status === "ok") {
        stopTimers();
        isStarting = false;
        setReadinessVal(rStt, h.stt_ready);
        setReadinessVal(rTts, h.tts_ready);
        setReadinessVal(rLlm, h.llm_ready);
        if (rProfile && h.profile_id) { rProfile.textContent = h.profile_id; rProfile.dataset.ok = "true"; }
        applyStatus("healthy");
      } else if (h.status === "error") {
        healthErrorCount++;
        if (healthErrorCount >= 3) {
          stopTimers();
          isStarting = false;
          showError(h.error || "backend error");
        }
      } else if (h.status === "starting") {
        healthErrorCount = 0;
      }
      // "starting" — keep polling
    }).catch(function() {
      healthErrorCount++;
      if (healthErrorCount >= 3) {
        stopTimers();
        isStarting = false;
        showError("health_check invoke failed");
      }
    });
  }, 500);
}

startBtn.addEventListener("click", function() {
  isStarting = true;
  applyStatus("starting");
   invoke("start_backend").then(function(msg) {
    statusBarText.textContent = String(msg || "start command entered");
    startHealthPolling();
  }).catch(function(err) {
    isStarting = false;
    stopTimers();
    applyStatus("stopped");
    var msg = String(err);
    statusBarText.textContent = "FAILED: " + msg;
    if (emptyState) {
      emptyState.style.display = "flex";
      emptyState.innerHTML =
        "<span class='empty-icon'>\u2717</span>" +
        "<p style='color:#f85149;font-weight:700'>Start failed</p>" +
        "<p class='empty-sub' style='color:#f85149'>" + msg + "</p>";
    }
  });
});

stopBtn.addEventListener("click", function() {
  stopTimers();
  isStarting = false;
  invoke("stop_backend").catch(function() {});
  applyStatus("stopped");
  clearReadiness();
  if (emptyState) {
    emptyState.innerHTML =
      "<span class='empty-icon'>\u25C8</span>" +
      "<p>Start JARVIS to begin a conversation.</p>" +
      "<p class='empty-sub'>Voice and text turns will appear here.</p>";
    emptyState.style.display = "flex";
  }
});

applyStatus("stopped");
