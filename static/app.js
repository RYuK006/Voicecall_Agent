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

  // DOM Elements - Method A Bluetooth Direct Audio Routing
  const selectAudioInput = document.getElementById("select-audio-input");
  const selectAudioOutput = document.getElementById("select-audio-output");
  const btPillStatus = document.getElementById("bt-pill-status");
  const vuMeterFill = document.getElementById("vu-meter-fill");
  const btnRefreshAudioDevices = document.getElementById("btn-refresh-audio-devices");
  const btnTestAudioOutput = document.getElementById("btn-test-audio-output");
  const inputBridgeUrl = document.getElementById("input-bridge-url");
  const btnSaveBridgeUrl = document.getElementById("btn-save-bridge-url");
  const btnLaunchPhoneLink = document.getElementById("btn-launch-phone-link");
  const pickupOverrideContainer = document.getElementById("pickup-override-container");
  const btnForcePickup = document.getElementById("btn-force-pickup");

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

  // Audio Device State (Method A Bluetooth Routing)
  let selectedInputDeviceId = "default";
  let selectedOutputDeviceId = "default";
  let audioContext = null;
  let micMediaStream = null;
  let vuAnimationId = null;

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
            // Telephony state active (answered)
            onRecipientAnswered();
          }
          else if (data.state === "idle" && pollCount > 6) {
            // Call was rejected or hung up before answer
            isWaitingSimAnswer = false;
            stopSimMonitor();
            if (pickupOverrideContainer) pickupOverrideContainer.style.display = "none";
            appendTranscript("system", "❌ Call disconnected on phone before answer.");
            updateCallState("idle");
            stopSpeechRecognition();
          }
          else if (pollCount === 12) {
            appendTranscript("system", "⏳ Phone is ringing... AI will start automatically when recipient says 'Hello', or click 'Recipient Answered' above.");
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

  function onRecipientAnswered(initialSpeech = null) {
    if (!isWaitingSimAnswer) return;
    isWaitingSimAnswer = false;
    if (pickupOverrideContainer) pickupOverrideContainer.style.display = "none";
    appendTranscript("system", "🟢 Recipient answered! Starting Priya AI...");
    startCall(initialSpeech);
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
  checkBluetoothPhoneStatus();
  loadBridgeConfig();
  refreshAudioDevices();
  setInterval(checkBluetoothPhoneStatus, 12000);

  // --- Method A: Audio Device Routing & VU Meter ---
  async function checkBluetoothPhoneStatus() {
    try {
      const res = await fetch("/api/bluetooth-status");
      const data = await res.json();
      if (data.status === "connected") {
        btPillStatus.textContent = `🟢 ${data.connected_phone} Ready`;
        btPillStatus.className = "bt-pill";
      } else {
        btPillStatus.textContent = "⚠️ Connect Phone via Bluetooth";
        btPillStatus.className = "bt-pill warning";
      }
    } catch (e) {
      btPillStatus.textContent = "Bluetooth Ready";
    }
  }

  async function refreshAudioDevices() {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          tempStream.getTracks().forEach(t => t.stop());
        } catch (e) {}
      }

      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;

      const devices = await navigator.mediaDevices.enumerateDevices();
      selectAudioInput.innerHTML = "";
      selectAudioOutput.innerHTML = "";

      let foundBtInput = false;
      let foundBtOutput = false;

      devices.forEach(device => {
        const option = document.createElement("option");
        option.value = device.deviceId;
        const label = device.label || `${device.kind} (${device.deviceId.slice(0, 5)}...)`;
        option.textContent = label;

        const isBt = /bluetooth|hands-free|hfp|sco|headset|iqoo|phone/i.test(label);

        if (device.kind === "audioinput") {
          selectAudioInput.appendChild(option);
          if (isBt && !foundBtInput) {
            selectAudioInput.value = device.deviceId;
            selectedInputDeviceId = device.deviceId;
            foundBtInput = true;
          }
        } else if (device.kind === "audiooutput") {
          selectAudioOutput.appendChild(option);
          if (isBt && !foundBtOutput) {
            selectAudioOutput.value = device.deviceId;
            selectedOutputDeviceId = device.deviceId;
            foundBtOutput = true;
          }
        }
      });

      if (!selectAudioInput.children.length) {
        selectAudioInput.innerHTML = `<option value="default">Default Input Microphone</option>`;
      }
      if (!selectAudioOutput.children.length) {
        selectAudioOutput.innerHTML = `<option value="default">Default Output Speaker</option>`;
      }

      initVUMeter(selectedInputDeviceId);
    } catch (err) {
      console.warn("Could not enumerate audio devices:", err);
    }
  }

  function initVUMeter(deviceId) {
    if (vuAnimationId) cancelAnimationFrame(vuAnimationId);
    if (micMediaStream) {
      micMediaStream.getTracks().forEach(t => t.stop());
      micMediaStream = null;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;

    const constraints = {
      audio: deviceId && deviceId !== "default" ? { deviceId: { exact: deviceId } } : true
    };

    navigator.mediaDevices.getUserMedia(constraints).then(stream => {
      micMediaStream = stream;
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioContext.state === "suspended") {
        audioContext.resume();
      }
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      function updateMeter() {
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const percent = Math.min(100, Math.round((avg / 128) * 100));
        vuMeterFill.style.width = percent + "%";
        vuAnimationId = requestAnimationFrame(updateMeter);
      }
      updateMeter();
    }).catch(err => {
      console.warn("VU meter stream unavailable:", err);
    });
  }

  selectAudioInput.addEventListener("change", () => {
    selectedInputDeviceId = selectAudioInput.value;
    initVUMeter(selectedInputDeviceId);
    appendTranscript("system", `Audio Input switched to: ${selectAudioInput.options[selectAudioInput.selectedIndex].text}`);
  });

  selectAudioOutput.addEventListener("change", () => {
    selectedOutputDeviceId = selectAudioOutput.value;
    appendTranscript("system", `Audio Output switched to: ${selectAudioOutput.options[selectAudioOutput.selectedIndex].text}`);
  });

  btnRefreshAudioDevices.addEventListener("click", () => {
    refreshAudioDevices();
    checkBluetoothPhoneStatus();
    appendTranscript("system", "Rescanning audio devices & Bluetooth phone connection...");
  });

  btnTestAudioOutput.addEventListener("click", async () => {
    btnTestAudioOutput.disabled = true;
    btnTestAudioOutput.textContent = "Testing...";
    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: "Priya AI: Bluetooth Hands-Free digital audio output is verified and working perfectly.",
          lang: langSelect.value || "en",
          gender: genderSelect.value || "female"
        })
      });
      const data = await res.json();
      if (data.audio_base64) {
        const testAudio = new Audio("data:audio/mp3;base64," + data.audio_base64);
        if (selectedOutputDeviceId && selectedOutputDeviceId !== "default" && typeof testAudio.setSinkId === "function") {
          try { await testAudio.setSinkId(selectedOutputDeviceId); } catch(e){}
        }
        await testAudio.play();
        appendTranscript("system", "🔊 Test voice phrase played through selected output device.");
      }
    } catch(e) {
      appendTranscript("system", "Test voice error: " + e.message);
    } finally {
      btnTestAudioOutput.disabled = false;
      btnTestAudioOutput.textContent = "Test Voice";
    }
  });

  async function loadBridgeConfig() {
    try {
      const res = await fetch("/api/bridge-config");
      const data = await res.json();
      if (data.bridge_url && inputBridgeUrl) {
        inputBridgeUrl.value = data.bridge_url;
        // Check live connection status on initial load
        fetch("/api/bridge-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: data.bridge_url })
        }).then(r => r.json()).then(testData => {
          if (testData.status === "connected" && btnSaveBridgeUrl) {
            btnSaveBridgeUrl.textContent = "✓ Connected";
            btnSaveBridgeUrl.style.color = "var(--accent-green)";
            btnSaveBridgeUrl.style.borderColor = "var(--accent-green)";
          }
        }).catch(() => {});
      }
    } catch (e) {}
  }

  if (inputBridgeUrl) {
    inputBridgeUrl.addEventListener("blur", () => {
      let v = inputBridgeUrl.value.trim();
      if (v) {
        v = v.replace(/^http:\s*\/*/, "http://");
        v = v.replace(/(\d+\.\d+\.\d+\.\d+)\.(\d+)$/, "$1:$2");
        if (!v.startsWith("http://") && !v.startsWith("https://")) {
          v = "http://" + v;
        }
        inputBridgeUrl.value = v;
      }
    });
  }

  if (btnSaveBridgeUrl && inputBridgeUrl) {
    btnSaveBridgeUrl.addEventListener("click", async () => {
      let val = inputBridgeUrl.value.trim();
      val = val.replace(/^http:\s*\/*/, "http://");
      val = val.replace(/(\d+\.\d+\.\d+\.\d+)\.(\d+)$/, "$1:$2");
      if (val && !val.startsWith("http://") && !val.startsWith("https://")) {
        val = "http://" + val;
      }
      inputBridgeUrl.value = val;

      btnSaveBridgeUrl.disabled = true;
      btnSaveBridgeUrl.textContent = "Connecting...";
      btnSaveBridgeUrl.style.color = "";
      btnSaveBridgeUrl.style.borderColor = "";

      try {
        const res = await fetch("/api/bridge-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: val })
        });
        const data = await res.json();
        if (data.status === "connected") {
          inputBridgeUrl.value = data.bridge_url;
          btnSaveBridgeUrl.textContent = "✓ Connected";
          btnSaveBridgeUrl.style.color = "var(--accent-green)";
          btnSaveBridgeUrl.style.borderColor = "var(--accent-green)";
          appendTranscript("system", `📱 Connected to Termux Phone Bridge at ${data.bridge_url}`);
        } else {
          btnSaveBridgeUrl.textContent = "⚠️ Unreachable";
          btnSaveBridgeUrl.style.color = "#f59e0b";
          btnSaveBridgeUrl.style.borderColor = "#f59e0b";
          appendTranscript("system", `⚠️ Could not reach Termux at ${val}. Error: ${data.message || "Connection refused"}. Make sure 'python termux_bridge.py' is running on your phone!`);
          setTimeout(() => {
            btnSaveBridgeUrl.textContent = "Connect";
            btnSaveBridgeUrl.style.color = "";
            btnSaveBridgeUrl.style.borderColor = "";
          }, 3500);
        }
      } catch (err) {
        btnSaveBridgeUrl.textContent = "Error";
        appendTranscript("system", `Bridge connection error: ${err.message}`);
        setTimeout(() => {
          btnSaveBridgeUrl.textContent = "Connect";
        }, 3000);
      } finally {
        btnSaveBridgeUrl.disabled = false;
      }
    });
  }

  if (btnLaunchPhoneLink) {
    btnLaunchPhoneLink.addEventListener("click", async () => {
      btnLaunchPhoneLink.disabled = true;
      btnLaunchPhoneLink.textContent = "Opening...";
      try {
        await fetch("/api/launch-phone-link", { method: "POST" });
        appendTranscript("system", "🔗 Opening Microsoft Phone Link on Windows...");
      } catch (e) {
        appendTranscript("system", "Error opening Phone Link: " + e.message);
      } finally {
        setTimeout(() => {
          btnLaunchPhoneLink.disabled = false;
          btnLaunchPhoneLink.textContent = "Open Phone Link";
        }, 3000);
      }
    });
  }

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
    if (pickupOverrideContainer) pickupOverrideContainer.style.display = "block";
    liveCue.textContent = "📞 Dialing... AI is listening silently and will speak when recipient says 'Hello'.";

    // Start speech recognition in listening mode right away so if caller says "Hello", we catch it immediately!
    initSpeechRecognition(langSelect.value);

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
        if (pickupOverrideContainer) pickupOverrideContainer.style.display = "none";
        stopSpeechRecognition();
        return;
      }
      
      // Start monitoring Android telephony state
      startSimMonitor();
    } catch (err) {
      appendTranscript("system", `SIM Call error: ${err.message}`);
      updateCallState("idle");
      isWaitingSimAnswer = false;
      if (pickupOverrideContainer) pickupOverrideContainer.style.display = "none";
      stopSpeechRecognition();
    }
  }

  if (btnForcePickup) {
    btnForcePickup.addEventListener("click", () => {
      onRecipientAnswered();
    });
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

  function startCall(initialSpeech = null) {
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

      // Send initial handshake with optional initial_speech
      ws.send(JSON.stringify({
        guest_id: guestId,
        lang: lang,
        gender: gender,
        initial_speech: initialSpeech
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
    if (pickupOverrideContainer) pickupOverrideContainer.style.display = "none";
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

      if (isWaitingSimAnswer && transcript) {
        // Voice Activity Detection: recipient said something like "Hello"!
        appendTranscript("user", transcript);
        onRecipientAnswered(transcript);
        return;
      }

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

    // Method A: Route audio output directly into Bluetooth Hands-Free / phone line
    if (selectedOutputDeviceId && selectedOutputDeviceId !== "default" && typeof currentAudio.setSinkId === "function") {
      try {
        await currentAudio.setSinkId(selectedOutputDeviceId);
      } catch (err) {
        console.warn("Could not set audio sinkId on currentAudio:", err);
      }
    }

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
