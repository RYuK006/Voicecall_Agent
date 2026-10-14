// Indic Voice Agent Frontend Controller

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements - Call Controls
  const btnStartCall = document.getElementById("btn-start-call");
  const btnSimCall = document.getElementById("btn-sim-call");
  const btnToggleMic = document.getElementById("btn-toggle-mic");
  const btnEndCall = document.getElementById("btn-end-call");
  const micLabel = document.getElementById("mic-label");
  const guestSelect = document.getElementById("guest-select");
  const langSelect = document.getElementById("lang-select");
  const genderSelect = document.getElementById("gender-select");
  const callStatusDot = document.getElementById("call-status-dot");
  const callStatusLabel = document.getElementById("call-status-label");
  const callTimerEl = document.getElementById("call-timer");
  const avatarRing = document.getElementById("avatar-ring");
  const waveContainer = document.getElementById("wave-container");
  const liveCue = document.getElementById("live-cue");
  const transcriptStream = document.getElementById("transcript-stream");
  const btnClearTranscript = document.getElementById("btn-clear-transcript");
  const manualTextInput = document.getElementById("manual-text-input");
  const btnSendManual = document.getElementById("btn-send-manual");

  // DOM Elements - Dashboard
  const statTotal = document.getElementById("stat-total");
  const statConfirmed = document.getElementById("stat-confirmed");
  const statDeclined = document.getElementById("stat-declined");
  const statHeadcount = document.getElementById("stat-headcount");
  const guestTableBody = document.getElementById("guest-table-body");
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  // DOM Elements - Modal & Forms
  const modal = document.getElementById("add-guest-modal");
  const btnAddGuestModal = document.getElementById("btn-add-guest-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const addGuestForm = document.getElementById("add-guest-form");
  const eventForm = document.getElementById("event-form");

  // State Variables
  let ws = null;
  let callTimerInterval = null;
  let callSeconds = 0;
  let isCallActive = false;
  let isMicMuted = false;
  let recognition = null;
  let currentAudio = null;
  let currentGuest = null;
  let shouldEndCallAfterSpeech = false;
  let silenceTimer = null;
  let simMonitorInterval = null;
  let isWaitingSimAnswer = false;

  function resetSilenceTimer() {
    clearTimeout(silenceTimer);
    if (!isCallActive) return;
    silenceTimer = setTimeout(() => {
      if (isCallActive) {
        appendTranscript("system", "⏱️ 25 seconds of silence detected. Concluding call...");
        endCall();
      }
    }, 25000);
  }

  function clearSilenceTimer() {
    clearTimeout(silenceTimer);
  }

  function startSimMonitor() {
    stopSimMonitor();
    let hadSimActive = false;
    let pollCount = 0;

    simMonitorInterval = setInterval(async () => {
      try {
        const res = await fetch("/api/sim-call-status");
        const data = await res.json();
        pollCount++;

        // 1. If currently dialing and waiting for recipient to pick up (AI MUST NOT SPEAK YET)
        if (isWaitingSimAnswer) {
          if (data.state === "dialing" || data.state === "ringing") {
            liveCue.textContent = data.state === "ringing" ?
              "🔔 Recipient phone ringing... Waiting for user to pick up." :
              "📞 Dialing outgoing call... Connecting cellular line.";
          }
          else if (data.state === "active" || data.answered === true) {
            // RECIPIENT ANSWERED!
            isWaitingSimAnswer = false;
            hadSimActive = true;
            appendTranscript("system", "🟢 Call answered by recipient! Connecting AI voice stream now...");
            // NOW we initialize the AI call!
            startCall();
          }
          else if (data.state === "idle" && pollCount > 3) {
            // Call was rejected, busy, or canceled before pickup
            isWaitingSimAnswer = false;
            stopSimMonitor();
            appendTranscript("system", "❌ Recipient did not answer or declined the call.");
            updateCallState("idle");
          }
          else if (data.state === "unknown" && pollCount > 3) {
            // Simulated/fallback mode if no telemetry available
            appendTranscript("system", "ℹ️ Simulated SIM mode: Starting AI voice stream.");
            isWaitingSimAnswer = false;
            hadSimActive = true;
            startCall();
          }
        }
        // 2. If call is active and conversation is running
        else if (isCallActive) {
          if (data.state === "active") {
            hadSimActive = true;
          } else if (data.state === "idle" && hadSimActive) {
            appendTranscript("system", "📞 Cellular call disconnected on phone.");
            endCall();
            stopSimMonitor();
          }
        }
      } catch (e) {
        console.warn("SIM status polling error:", e);
      }
    }, 1000);
  }

  function stopSimMonitor() {
    if (simMonitorInterval) {
      clearInterval(simMonitorInterval);
      simMonitorInterval = null;
    }
  }

  // Language mapping to Web Speech API locale
  const langLocales = {
    "hi": "hi-IN",
    "ml": "ml-IN",
    "en": "en-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "bn": "bn-IN",
    "mr": "mr-IN"
  };

  // --- Initial Data Load ---
  loadEventConfig();
  loadGuests();
  loadStats();
  loadKeysStatus();

  // --- Tab Navigation ---
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add("active");
    });
  });

  // --- Modal Handling ---
  btnAddGuestModal.addEventListener("click", () => modal.classList.add("open"));
  btnCloseModal.addEventListener("click", () => modal.classList.remove("open"));

  addGuestForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("new-name").value.trim();
    const phone = document.getElementById("new-phone").value.trim();
    const preferred_language = document.getElementById("new-lang").value;

    try {
      const res = await fetch("/api/guests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, phone, preferred_language, status: "Pending", attendees_count: 0, dietary_preference: "None" })
      });
      if (res.ok) {
        modal.classList.remove("open");
        addGuestForm.reset();
        await loadGuests();
        await loadStats();
      }
    } catch (err) {
      console.error("Failed to add guest:", err);
    }
  });

  // --- Event Config Form Handling ---
  eventForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      event_name: document.getElementById("ev-name").value,
      organizer: document.getElementById("ev-organizer").value,
      date: document.getElementById("ev-date").value,
      time: document.getElementById("ev-time").value,
      venue: document.getElementById("ev-venue").value,
      description: document.getElementById("ev-desc").value
    };

    try {
      const res = await fetch("/api/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        alert("Event settings updated successfully!");
      }
    } catch (err) {
      console.error("Failed to save event:", err);
    }
  });

  // --- API Fetch Helpers ---
  async function loadEventConfig() {
    try {
      const res = await fetch("/api/event");
      const data = await res.json();
      document.getElementById("ev-name").value = data.event_name || "";
      document.getElementById("ev-organizer").value = data.organizer || "";
      document.getElementById("ev-date").value = data.date || "";
      document.getElementById("ev-time").value = data.time || "";
      document.getElementById("ev-venue").value = data.venue || "";
      document.getElementById("ev-desc").value = data.description || "";
    } catch (e) {
      console.error("Error loading event:", e);
    }
  }

  // --- AI Brain & API Keys Management ---
  const keysForm = document.getElementById("keys-form");
  const currentEngineName = document.getElementById("current-engine-name");

  async function loadKeysStatus() {
    try {
      const res = await fetch("/api/keys");
      const d = await res.json();
      if (currentEngineName) {
        currentEngineName.textContent = d.active_engine;
        if (d.has_grok || d.has_groq) {
          currentEngineName.style.color = "var(--accent-green)";
        }
      }
    } catch(e) {
      console.error("Error loading keys status:", e);
    }
  }

  if (keysForm) {
    keysForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const grok_key = document.getElementById("input-grok-key").value.trim();
      const gemini_key = document.getElementById("input-gemini-key").value.trim();

      try {
        const res = await fetch("/api/keys", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ grok_key, gemini_key })
        });
        const d = await res.json();
        alert(`API Key updated successfully! Active Engine: ${d.active_engine}`);
        if (currentEngineName) currentEngineName.textContent = d.active_engine;
      } catch (err) {
        alert("Failed to save key: " + err.message);
      }
    });
  }

  async function loadStats() {
    try {
      const res = await fetch("/api/stats");
      const s = await res.json();
      statTotal.textContent = s.total_guests;
      statConfirmed.textContent = s.confirmed;
      statDeclined.textContent = s.declined;
      statHeadcount.textContent = s.total_attendees_headcount;
    } catch (e) {
      console.error("Error loading stats:", e);
    }
  }

  async function loadGuests() {
    try {
      const res = await fetch("/api/guests");
      const guests = await res.json();
      
      // Update Dropdown in Call Simulator
      guestSelect.innerHTML = `<option value="">-- Direct Test / Ad-hoc Guest --</option>`;
      guestTableBody.innerHTML = "";

      guests.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = `${g.name} (${g.phone}) - ${g.status}`;
        guestSelect.appendChild(opt);

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><code>${g.id}</code></td>
          <td><strong>${g.name}</strong></td>
          <td>${g.phone}</td>
          <td>${g.preferred_language || 'Hindi'}</td>
          <td><span class="status-badge ${g.status}">${g.status}</span></td>
          <td>${g.attendees_count || 0}</td>
          <td>${g.dietary_preference || 'None'}</td>
          <td>
            <button class="btn-mini-call" data-id="${g.id}">Call</button>
          </td>
        `;
        guestTableBody.appendChild(tr);
      });

      // Bind quick call buttons
      document.querySelectorAll(".btn-mini-call").forEach(btn => {
        btn.addEventListener("click", () => {
          const id = btn.dataset.id;
          guestSelect.value = id;
          startCall();
        });
      });
    } catch (e) {
      console.error("Error loading guests:", e);
    }
  }

  // --- Voice Call Pipeline ---
  btnStartCall.addEventListener("click", startCall);
  btnSimCall.addEventListener("click", startSimCall);
  btnEndCall.addEventListener("click", endCall);
  btnToggleMic.addEventListener("click", toggleMic);
  btnClearTranscript.addEventListener("click", () => {
    transcriptStream.innerHTML = "";
  });

  async function startSimCall() {
    if (isCallActive || isWaitingSimAnswer) return;

    const selectedOpt = guestSelect.options[guestSelect.selectedIndex];
    const guestText = selectedOpt ? selectedOpt.textContent : "";
    let phone = "";
    
    // Extract phone from option text or prompt
    const match = guestText.match(/\+?\d[\d\s-]{7,}/);
    if (match) {
      phone = match[0];
    } else {
      phone = prompt("Enter phone number to dial via SIM card (e.g. +91 98765 43210):");
    }

    if (!phone) return;

    appendTranscript("system", `📞 Initiating cellular call via phone SIM to ${phone}...`);
    updateCallState("dialing");
    isWaitingSimAnswer = true;

    try {
      const res = await fetch("/api/dial-sim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone })
      });
      const data = await res.json();
      appendTranscript("system", `SIM Dialer: ${data.message}`);

      if (data.status === "error") {
        updateCallState("idle");
        isWaitingSimAnswer = false;
        return;
      }
      
      // Start monitoring Android telephony state (wait for ACTIVE before speaking!)
      startSimMonitor();
    } catch (err) {
      appendTranscript("system", `SIM Call error: ${err.message}`);
      updateCallState("idle");
      isWaitingSimAnswer = false;
    }
  }

  // Manual fallback input
  btnSendManual.addEventListener("click", sendManualText);
  manualTextInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendManualText();
  });

  function sendManualText() {
    const val = manualTextInput.value.trim();
    if (!val || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    clearSilenceTimer();
    appendTranscript("user", val);
    manualTextInput.value = "";
    ws.send(JSON.stringify({ type: "user_speech", text: val }));
  }

  function startCall() {
    if (isCallActive) return;

    const guestId = guestSelect.value;
    const lang = langSelect.value;
    const gender = genderSelect.value;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/call`;

    updateCallState("connecting");
    appendTranscript("system", `Dialing session initialized (${lang.toUpperCase()})...`);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isCallActive = true;
      shouldEndCallAfterSpeech = false;
      updateCallState("connected");
      startCallTimer();
      resetSilenceTimer();

      // Send initial handshake
      ws.send(JSON.stringify({
        guest_id: guestId,
        lang: lang,
        gender: gender
      }));

      // Initialize Web Speech Recognition
      initSpeechRecognition(lang);
    };

    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "agent_thinking") {
        clearSilenceTimer();
        updateCallState("thinking");
      } 
      else if (data.type === "agent_speech") {
        updateCallState("speaking");
        appendTranscript("agent", data.text);

        if (data.guest) {
          currentGuest = data.guest;
        }

        if (data.rsvp_update) {
          appendTranscript("system", `RSVP Updated: Status=${data.rsvp_update.status || 'Same'}, Headcount=${data.rsvp_update.attendees_count ?? '-'}`);
          loadGuests();
          loadStats();
        }

        shouldEndCallAfterSpeech = Boolean(data.is_closing);
        if (shouldEndCallAfterSpeech) {
          appendTranscript("system", "📞 Call wrap-up detected. Will disconnect naturally once agent finishes speaking.");
        }

        // Play received neural TTS audio
        if (data.audio_base64) {
          await playAudioBase64(data.audio_base64);
        } else if (shouldEndCallAfterSpeech) {
          setTimeout(() => {
            appendTranscript("system", "✅ Call ended automatically (RSVP recorded).");
            endCall();
          }, 1500);
        }
      }
      else if (data.type === "call_ended") {
        endCall();
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      appendTranscript("system", "Call network error occurred.");
      endCall();
    };

    ws.onclose = () => {
      if (isCallActive) endCall();
    };
  }

  function endCall() {
    isWaitingSimAnswer = false;
    clearSilenceTimer();
    stopSimMonitor();
    shouldEndCallAfterSpeech = false;
    isCallActive = false;
    stopCallTimer();
    stopAudio();
    stopSpeechRecognition();

    try {
      fetch("/api/end-sim", { method: "POST" });
    } catch (e) {}

    if (ws) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "hangup" }));
        ws.close();
      }
      ws = null;
    }

    updateCallState("idle");
    appendTranscript("system", "Call session concluded.");
    loadGuests();
    loadStats();
  }

  function toggleMic() {
    isMicMuted = !isMicMuted;
    if (isMicMuted) {
      btnToggleMic.classList.remove("mic-active");
      micLabel.textContent = "Unmute Mic";
      if (recognition) recognition.stop();
      appendTranscript("system", "Microphone muted.");
    } else {
      btnToggleMic.classList.add("mic-active");
      micLabel.textContent = "Mute Mic";
      if (recognition) {
        try { recognition.start(); } catch(e){}
      }
      appendTranscript("system", "Microphone active.");
    }
  }

  // --- Web Speech API (Free Indic STT) ---
  function initSpeechRecognition(lang) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      liveCue.textContent = "Browser STT not supported. Use text input box below.";
      return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = langLocales[lang] || "hi-IN";

    recognition.onresult = (e) => {
      const lastIndex = e.results.length - 1;
      const transcript = e.results[lastIndex][0].transcript.trim();

      if (transcript && ws && ws.readyState === WebSocket.OPEN && !isMicMuted) {
        clearSilenceTimer();
        appendTranscript("user", transcript);
        ws.send(JSON.stringify({ type: "user_speech", text: transcript }));
      }
    };

    recognition.onerror = (e) => {
      if (e.error !== "no-speech") {
        console.warn("Speech recognition error:", e.error);
      }
    };

    recognition.onend = () => {
      // Auto-restart recognition if call is active and unmuted
      if (isCallActive && !isMicMuted && recognition) {
        try { recognition.start(); } catch(e){}
      }
    };

    try {
      recognition.start();
      btnToggleMic.classList.add("mic-active");
    } catch (e) {
      console.warn("Could not start recognition:", e);
    }
  }

  function stopSpeechRecognition() {
    if (recognition) {
      recognition.stop();
      recognition = null;
    }
    btnToggleMic.classList.remove("mic-active");
  }

  // --- Audio Decoding & Animation ---
  async function playAudioBase64(b64) {
    stopAudio();

    const audioUrl = "data:audio/mp3;base64," + b64;
    currentAudio = new Audio(audioUrl);

    currentAudio.onplay = () => {
      waveContainer.classList.add("speaking");
      avatarRing.classList.add("call-active");
      liveCue.textContent = shouldEndCallAfterSpeech ? "Agent Priya is concluding call..." : "Agent Priya is speaking...";
    };

    currentAudio.onended = () => {
      waveContainer.classList.remove("speaking");
      avatarRing.classList.remove("call-active");

      if (shouldEndCallAfterSpeech) {
        liveCue.textContent = "Call concluded. Disconnecting...";
        setTimeout(() => {
          appendTranscript("system", "✅ Call ended automatically (RSVP recorded).");
          endCall();
        }, 1000);
        return;
      }

      updateCallState("listening");
      liveCue.textContent = "Listening to you... Speak into your microphone.";
      resetSilenceTimer();
    };

    currentAudio.onerror = (err) => {
      console.error("Audio playback error:", err);
      waveContainer.classList.remove("speaking");
      avatarRing.classList.remove("call-active");
      if (shouldEndCallAfterSpeech) {
        setTimeout(() => {
          appendTranscript("system", "✅ Call ended automatically (RSVP recorded).");
          endCall();
        }, 1000);
        return;
      }
      updateCallState("listening");
      resetSilenceTimer();
    };

    try {
      await currentAudio.play();
    } catch (e) {
      console.warn("Autoplay policy prevented audio:", e);
      waveContainer.classList.remove("speaking");
      avatarRing.classList.remove("call-active");
      if (shouldEndCallAfterSpeech) {
        setTimeout(() => {
          appendTranscript("system", "✅ Call ended automatically (RSVP recorded).");
          endCall();
        }, 1000);
        return;
      }
      updateCallState("listening");
      resetSilenceTimer();
    }
  }

  function stopAudio() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    waveContainer.classList.remove("speaking");
    avatarRing.classList.remove("call-active");
  }

  // --- UI State Helpers ---
  function updateCallState(state) {
    if (state === "idle") {
      callStatusDot.className = "status-dot";
      callStatusLabel.textContent = "Standby / Idle";
      btnStartCall.disabled = false;
      btnSimCall.disabled = false;
      btnToggleMic.disabled = true;
      btnEndCall.disabled = true;
      manualTextInput.disabled = true;
      btnSendManual.disabled = true;
      guestSelect.disabled = false;
      langSelect.disabled = false;
      genderSelect.disabled = false;
      liveCue.textContent = "Click 'Web Call' or 'Call via SIM' to begin conversational test";
    } else if (state === "dialing") {
      callStatusDot.className = "status-dot thinking";
      callStatusLabel.textContent = "Dialing Recipient...";
      btnStartCall.disabled = true;
      btnSimCall.disabled = true;
      btnToggleMic.disabled = true;
      btnEndCall.disabled = false;
      manualTextInput.disabled = true;
      btnSendManual.disabled = true;
      guestSelect.disabled = true;
      langSelect.disabled = true;
      genderSelect.disabled = true;
      liveCue.textContent = "📞 Ringing recipient... Waiting for them to pick up.";
    } else if (state === "connecting") {
      callStatusDot.className = "status-dot thinking";
      callStatusLabel.textContent = "Connecting...";
      btnStartCall.disabled = true;
      btnSimCall.disabled = true;
      btnToggleMic.disabled = true;
      btnEndCall.disabled = false;
      guestSelect.disabled = true;
      langSelect.disabled = true;
      genderSelect.disabled = true;
    } else if (state === "connected") {
      callStatusDot.className = "status-dot active";
      callStatusLabel.textContent = "In Call";
      btnStartCall.disabled = true;
      btnSimCall.disabled = true;
      btnToggleMic.disabled = false;
      btnEndCall.disabled = false;
      manualTextInput.disabled = false;
      btnSendManual.disabled = false;
      guestSelect.disabled = true;
      langSelect.disabled = true;
      genderSelect.disabled = true;
    } else if (state === "thinking") {
      callStatusDot.className = "status-dot thinking";
      liveCue.textContent = "Agent thinking...";
    } else if (state === "listening") {
      callStatusDot.className = "status-dot active";
      callStatusLabel.textContent = "Listening";
      liveCue.textContent = "Listening to you... Speak into microphone or type below.";
    } else if (state === "speaking") {
      callStatusDot.className = "status-dot active";
      callStatusLabel.textContent = "Agent Speaking";
    }
  }

  function startCallTimer() {
    callSeconds = 0;
    callTimerEl.textContent = "00:00";
    callTimerInterval = setInterval(() => {
      callSeconds++;
      const m = String(Math.floor(callSeconds / 60)).padStart(2, "0");
      const s = String(callSeconds % 60).padStart(2, "0");
      callTimerEl.textContent = `${m}:${s}`;
    }, 1000);
  }

  function stopCallTimer() {
    if (callTimerInterval) {
      clearInterval(callTimerInterval);
      callTimerInterval = null;
    }
    callTimerEl.textContent = "00:00";
  }

  function appendTranscript(role, text) {
    const msg = document.createElement("div");
    msg.className = `message ${role}-msg`;
    msg.textContent = text;
    transcriptStream.appendChild(msg);
    transcriptStream.scrollTop = transcriptStream.scrollHeight;
  }
});
