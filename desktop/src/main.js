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
var conversationFeed = document.getElementById("conversation-feed");
var turnCount = document.getElementById("turn-count");
var wakeIndicator = document.getElementById("wake-indicator");
var degradedList = document.getElementById("degraded-list");
var textInput = document.getElementById("text-input");
var sendBtn = document.getElementById("send-btn");
var pttBtn = document.getElementById("ptt-btn");

var appStatus = "stopped";
var isStarting = false;
var elapsedTimer = null;
var elapsed = 0;
var healthPollTimer = null;
var sessionPollTimer = null;
var healthErrorCount = 0;
var renderedTurnsSignature = "";
var renderedSessionId = null;
var pttInFlight = false;

function setPttVisual(active) {
  pttInFlight = !!active;
  if (!pttBtn) return;
  pttBtn.disabled = pttInFlight || textInput && textInput.disabled;
  pttBtn.dataset.active = pttInFlight ? "true" : "false";
  pttBtn.setAttribute("aria-pressed", pttInFlight ? "true" : "false");
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setInputAvailability(available) {
  if (!inputBar) return;
  inputBar.style.display = available ? "flex" : "none";
  if (textInput) textInput.disabled = !available;
  if (sendBtn) sendBtn.disabled = !available;
  if (pttBtn) pttBtn.disabled = !available || pttInFlight;
}

function clearConversationFeed() {
  renderedTurnsSignature = "";
  renderedSessionId = null;
  if (!conversationFeed) return;
  conversationFeed.innerHTML = "";
  if (emptyState) {
    emptyState.style.display = "flex";
    conversationFeed.appendChild(emptyState);
  }
}

function setWakeIndicator(active) {
  if (!wakeIndicator) return;
  var isActive = !!active;
  wakeIndicator.dataset.active = isActive ? "true" : "false";
  wakeIndicator.textContent = isActive ? "wake active" : "wake inactive";
}

function renderTurnsFromBackend(sessionId, turns) {
  if (!conversationFeed) return;
  var normalized = Array.isArray(turns) ? turns : [];
  var sid = sessionId ? String(sessionId) : "";
  var signature = sid + "::" + normalized.map(function(t) {
    return [
      String(t.turn_id || ""),
      String(t.turn_index || ""),
      String(t.transcript || ""),
      String(t.response_text || "")
    ].join("~");
  }).join("|");

  if (renderedSessionId !== sid) {
    conversationFeed.innerHTML = "";
    renderedTurnsSignature = "";
    renderedSessionId = sid;
  }

  if (signature === renderedTurnsSignature) {
    return;
  }

  conversationFeed.innerHTML = "";
  if (!normalized.length) {
    if (emptyState) {
      emptyState.style.display = "flex";
      conversationFeed.appendChild(emptyState);
    }
    renderedTurnsSignature = signature;
    renderedSessionId = sid;
    return;
  }

  normalized.forEach(function(turn) {
    var transcript = turn && turn.transcript ? String(turn.transcript) : "(no transcript)";
    var response = turn && turn.response_text ? String(turn.response_text) : "(no response)";
    appendTurn("user", transcript);
    appendTurn("assistant", response);
  });

  renderedTurnsSignature = signature;
  renderedSessionId = sid;
}

function appendTurn(role, text) {
  if (!conversationFeed) return;
  if (emptyState && emptyState.parentElement === conversationFeed) {
    emptyState.remove();
  }
  var turn = document.createElement("div");
  turn.className = "turn";

  var label = document.createElement("div");
  label.className = "turn-label " + (role === "user" ? "user-label" : "assistant-label");
  label.textContent = role === "user" ? "You" : "JARVIS";

  var bubble = document.createElement("div");
  bubble.className = role === "user" ? "turn-user" : "turn-assistant";
  bubble.innerHTML = escapeHtml(text);

  turn.appendChild(label);
  turn.appendChild(bubble);
  conversationFeed.appendChild(turn);
  conversationFeed.scrollTop = conversationFeed.scrollHeight;
}

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
  setInputAvailability(running);
}

function applyResidentStatusLabel(residentStatus) {
  if (!residentStatus) return;
  var normalized = String(residentStatus);
  var labels = {
    listening: "Ready (PTT/Hotkey)",
    transcribing: "Transcribing",
    thinking: "Thinking",
    speaking: "Speaking",
    degraded: "Degraded",
    stopped: "Stopped",
    idle: "Idle",
    interrupted: "Interrupted"
  };
  var pretty = labels[normalized] || (normalized.charAt(0).toUpperCase() + normalized.slice(1));
  statusLabel.textContent = pretty;
  statusBarText.textContent = pretty;
  statusDot.dataset.status = residentStatus;
}

function renderResidentState(state) {
  if (!state) return;

  applyResidentStatusLabel(state.status || "unknown");
  if (statusBarText && !String(statusBarText.textContent || "").trim()) {
    statusBarText.textContent = "Ready";
  }
  setWakeIndicator(state.wake_active === true);

  if (turnCount) {
    turnCount.textContent = "Turns: " + String(state.turn_count || 0);
  }

  if (degradedBlock) {
    var degraded = Array.isArray(state.degraded_conditions) ? state.degraded_conditions : [];
    degradedBlock.style.display = degraded.length ? "block" : "none";
    if (degraded.length) {
      appStatus = "degraded";
    }
    if (degradedList) {
      degradedList.innerHTML = degraded.map(function(item) {
        return "<li>" + escapeHtml(item) + "</li>";
      }).join("");
    }
  }

  if (!conversationFeed) return;
  if (Array.isArray(state.turns)) {
    renderTurnsFromBackend(state.session_id, state.turns);
    return;
  }

  // Backward-compatibility fallback (non-authoritative) for older payloads.
  var fallbackTurns = [];
  if (state.last_turn_id || state.last_transcript || state.last_response) {
    fallbackTurns.push({
      turn_id: state.last_turn_id || "fallback",
      transcript: state.last_transcript,
      response_text: state.last_response
    });
  }
  renderTurnsFromBackend(state.session_id, fallbackTurns);
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
  setInputAvailability(false);
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
  if (sessionPollTimer) { clearInterval(sessionPollTimer); sessionPollTimer = null; }
}

function startSessionPolling() {
  if (sessionPollTimer) clearInterval(sessionPollTimer);
  sessionPollTimer = setInterval(function() {
    invoke("session_state").then(function(raw) {
      var state;
      try { state = JSON.parse(raw); } catch(e) { return; }
      renderResidentState(state);
    }).catch(function() {
      if (appStatus === "healthy" || appStatus === "degraded") {
        statusBarText.textContent = "Session state unavailable; retrying…";
      }
    });
  }, 500);
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
        var degradedReady = !(h.stt_ready && h.tts_ready && h.llm_ready);
        applyStatus(degradedReady ? "degraded" : "healthy");
        clearConversationFeed();
        startSessionPolling();
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
  setInputAvailability(false);
  clearReadiness();
  if (turnCount) turnCount.textContent = "";
  if (degradedBlock) degradedBlock.style.display = "none";
  if (degradedList) degradedList.innerHTML = "";
  if (emptyState) {
    emptyState.innerHTML =
      "<span class='empty-icon'>\u25C8</span>" +
      "<p>Start JARVIS to begin a conversation.</p>" +
      "<p class='empty-sub'>Voice and text turns will appear here.</p>";
    emptyState.style.display = "flex";
  }
  clearConversationFeed();
  setWakeIndicator(false);
});

function submitTextFromInput() {
  if (!textInput) return;
  var text = textInput.value.trim();
  if (!text) return;
  sendBtn.disabled = true;
  invoke("submit_text", { text: text }).then(function() {
    textInput.value = "";
  }).catch(function(err) {
    statusBarText.textContent = "Text send failed: " + String(err);
  }).finally(function() {
    sendBtn.disabled = false;
    textInput.focus();
  });
}

if (sendBtn) {
  sendBtn.addEventListener("click", submitTextFromInput);
}

if (textInput) {
  textInput.addEventListener("keydown", function(evt) {
    if (evt.key === "Enter") {
      evt.preventDefault();
      submitTextFromInput();
    }
  });
}

if (pttBtn) {
  pttBtn.addEventListener("click", function() {
    if (pttInFlight) return;
    setPttVisual(true);
    statusBarText.textContent = "PTT trigger sent…";
    invoke("push_to_talk").then(function() {
      statusBarText.textContent = "PTT trigger queued";
    }).catch(function(err) {
      statusBarText.textContent = "PTT failed: " + String(err);
    }).finally(function() {
      setTimeout(function() {
        setPttVisual(false);
      }, 200);
    });
  });
}

applyStatus("stopped");
setPttVisual(false);
setWakeIndicator(false);
clearConversationFeed();
