// 40hoursaday - Web Client Logic with Multilingual (EN/DE) Support & Dual Mixer (MIDI + PulseAudio)
(function() {
    'use strict';

    // Translations Dictionary
    const translations = {
        en: {
            appSubtitle: "MIDI Practice Partner",
            loadingPorts: "Loading ports...",
            noMidiPort: "No MIDI Port",
            panicTitle: "MIDI Panic (Stop all notes)",
            stateReady: "Ready",
            statePlaying: "Playing",
            statePaused: "Paused",
            noTrackSelected: "No piece selected",
            loopTitle: "Loop (Repeat)",
            loopLabel: "Loop",
            stopTitle: "Stop",
            playPauseTitle: "Play / Pause",
            playTitle: "Play",
            pauseTitle: "Pause",
            resumeTitle: "Resume",
            countinTitle: "Count-in Metronome",
            countinLabel: "Count-in",
            countinPillLabel: "Count-in:",
            countinOff: "Off",
            countin1Bar: "1 Bar",
            countin2Bars: "2 Bars",
            keyTranspose: "Key:",
            practiceTempo: "PRACTICE TEMPO",
            piecesTitle: "Practice Pieces",
            piecesCount: "{n} Pieces",
            pieceCountSingle: "1 Piece",
            uploadButton: "➕ New Piece",
            searchPlaceholder: "Search piece (e.g. Rieding, Bach, Etude)...",
            loadingPieces: "Loading pieces...",
            noPiecesFound: "No pieces found for search.",
            emptyLibrary: "No MIDI pieces in folder.",
            toastLoading: "Loading {file}...",
            toastPleaseSelect: "Please select a piece first",
            toastLoopOn: "Loop ON 🔁",
            toastLoopOff: "Loop OFF",
            toastCountinSet: "Count-in: {bars} bar{plural}",
            toastCountinOff: "Count-in OFF",
            toastPanic: "🚨 MIDI Reset sent!",
            toastPort: "MIDI Port: {port}",
            toastVolume: "MIDI Volume: {vol}%",
            toastChannelVolume: "Ch {ch} Volume: {vol}%",
            toastChannelMuted: "Channel {ch} muted 🔇",
            toastChannelUnmuted: "Channel {ch} unmuted 🔊",
            toastAllChannelsUnmuted: "All channels unmuted 🔊",
            toastChannelsReset: "All channels reset to 100% 🎛️",
            toastUploading: "Uploading {file}...",
            toastUploadSuccess: "✅ \"{title}\" added!",
            toastUploadError: "Upload failed: {error}",
            midiMixerTitle: "MIDI Mixer & Channels",
            pulseMixerTitle: "PulseAudio Mixer",
            midiMixerTab: "🎛️ MIDI Mixer",
            pulseMixerTab: "🎚️ Pulse Audio",
            midiMasterVolume: "MIDI MASTER VOLUME",
            midiChannelsMute: "MIDI CHANNELS (CH 1–10)",
            resetVolumes: "Reset 100%",
            unmuteAll: "Unmute All",
            barLabel: "BAR",
            beatLabel: "BEAT",
            mixerOutputs: "OUTPUT (MASTER)",
            mixerStreams: "APPLICATIONS & STREAMS",
            mixerLoading: "Loading audio streams...",
            mixerNoStreams: "No active application streams",
            mixerMute: "Mute",
            mixerUnmute: "Unmute"
        },
        de: {
            appSubtitle: "MIDI Übungsbegleiter",
            loadingPorts: "Lade Ports...",
            noMidiPort: "Kein MIDI Port",
            panicTitle: "NOTHALT! (Stoppe alle Töne)",
            stateReady: "Bereit",
            statePlaying: "Spielt",
            statePaused: "Pausiert",
            noTrackSelected: "Kein Stück ausgewählt",
            loopTitle: "Schleife (Wiederholen)",
            loopLabel: "Loop",
            stopTitle: "Stopp",
            playPauseTitle: "Abspielen / Pause",
            playTitle: "Abspielen",
            pauseTitle: "Pause",
            resumeTitle: "Fortsetzen",
            countinTitle: "Einzähler / Vorzähler Metronom",
            countinLabel: "Einzähler",
            countinPillLabel: "Einzähler:",
            countinOff: "Aus",
            countin1Bar: "1 Takt",
            countin2Bars: "2 Takte",
            keyTranspose: "Tonart:",
            practiceTempo: "ÜBUNGSTEMPO",
            piecesTitle: "Übungsstücke",
            piecesCount: "{n} Stücke",
            pieceCountSingle: "1 Stück",
            uploadButton: "➕ Neues Stück",
            searchPlaceholder: "Stück suchen (z.B. Rieding, Bach, Etüde)...",
            loadingPieces: "Lade Stücke...",
            noPiecesFound: "Keine Stücke gefunden für Suche.",
            emptyLibrary: "Keine MIDI-Stücke im Ordner.",
            toastLoading: "Lade {file}...",
            toastPleaseSelect: "Bitte erst ein Stück auswählen",
            toastLoopOn: "Wiederholung EIN 🔁",
            toastLoopOff: "Wiederholung AUS",
            toastCountinSet: "Einzähler: {bars} Takt{plural}",
            toastCountinOff: "Einzähler AUS",
            toastPanic: "🚨 MIDI Reset gesendet!",
            toastPort: "MIDI Port: {port}",
            toastVolume: "MIDI-Lautstärke: {vol}%",
            toastChannelVolume: "Kanal {ch} Lautstärke: {vol}%",
            toastChannelMuted: "Kanal {ch} stummgeschaltet 🔇",
            toastChannelUnmuted: "Kanal {ch} aktiviert 🔊",
            toastAllChannelsUnmuted: "Alle Kanäle aktiviert 🔊",
            toastChannelsReset: "Alle Kanäle auf 100% zurückgesetzt 🎛️",
            toastUploading: "Lade {file} hoch...",
            toastUploadSuccess: "✅ \"{title}\" hinzugefügt!",
            toastUploadError: "Upload-Fehler: {error}",
            midiMixerTitle: "MIDI-Mischpult & Kanäle",
            pulseMixerTitle: "PulseAudio-Mischpult",
            midiMixerTab: "🎛️ MIDI-Mixer",
            pulseMixerTab: "🎚️ PulseAudio",
            midiMasterVolume: "MIDI MASTER-LAUTSTÄRKE",
            midiChannelsMute: "MIDI-KANÄLE (CH 1–10)",
            resetVolumes: "Auf 100% zurücksetzen",
            unmuteAll: "Alle aktivieren",
            barLabel: "TAKT",
            beatLabel: "SCHLAG",
            mixerOutputs: "AUSGANG (MASTER)",
            mixerStreams: "ANWENDUNGEN & AUDIO-STREAMS",
            mixerLoading: "Lade Audio-Streams...",
            mixerNoStreams: "Keine aktiven Audio-Streams",
            mixerMute: "Stummschalten",
            mixerUnmute: "Stummschaltung aufheben"
        }
    };

    // Current Language
    let currentLang = localStorage.getItem('40hoursaday_lang') || 
                      (navigator.language && navigator.language.startsWith('de') ? 'de' : 'en');

    function t(key, vars = {}) {
        const dict = translations[currentLang] || translations.en;
        let str = dict[key] || translations.en[key] || key;
        for (const [k, v] of Object.entries(vars)) {
            str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
        }
        return str;
    }

    // State
    const state = {
        status: {
            state: 'idle',
            filename: null,
            filepath: null,
            position: 0,
            duration: 0,
            speed: 1.0,
            speed_percent: 100,
            volume: 1.0,
            volume_percent: 100,
            loop: false,
            transpose: 0,
            count_in_bars: 0,
            count_in_active: false,
            count_in_current_beat: 0,
            count_in_total_beats: 0,
            bar: 1,
            beat: 1,
            beat_fraction: 0.0,
            beats_per_bar: 4,
            time_sig_num: 4,
            time_sig_den: 4,
            muted_channels: [],
            channel_volumes: {},
            port: null,
            available_ports: [],
            bpm: 120,
            time_signature: '4/4'
        },
        files: [],
        filteredFiles: [],
        searchQuery: '',
        isUserSeeking: false,
        lastStatusUpdate: 0,
        lastStatusTime: performance.now()
    };

    // DOM Elements
    const elements = {
        langButtons: document.querySelectorAll('.lang-btn'),
        portSelect: document.getElementById('midi-port-select'),
        portIndicator: document.getElementById('port-indicator'),
        btnPcToggle: document.getElementById('btn-pc-toggle'),
        btnPanic: document.getElementById('btn-panic'),
        btnMidiMixer: document.getElementById('btn-midi-mixer'),
        btnPulseMixer: document.getElementById('btn-pulse-mixer'),
        
        currentTrackTitle: document.getElementById('current-track-title'),
        trackMeter: document.getElementById('track-meter'),
        trackBpm: document.getElementById('track-bpm'),
        stateBadge: document.getElementById('playback-state-badge'),
        
        // Metronome Deck
        metroDeck: document.getElementById('metronome-deck'),
        metroBarVal: document.getElementById('metro-bar-val'),
        metroBeatVal: document.getElementById('metro-beat-val'),
        metroBeatSub: document.getElementById('metro-beat-sub'),
        metroDotsRow: document.getElementById('metro-dots-row'),
        metroPulseBar: document.getElementById('metro-pulse-bar'),
        metroCountinBadge: document.getElementById('metro-countin-badge'),
        metroCountinBeat: document.getElementById('metro-countin-beat'),
        metroCountinTotal: document.getElementById('metro-countin-total'),

        timeCurrent: document.getElementById('time-current'),
        timeTotal: document.getElementById('time-total'),
        progressBar: document.getElementById('progress-bar'),
        seekSlider: document.getElementById('seek-slider'),
        
        btnPlayPause: document.getElementById('btn-play-pause'),
        btnStop: document.getElementById('btn-stop'),
        btnLoop: document.getElementById('btn-loop'),
        btnCountinToggle: document.getElementById('btn-countin-toggle'),
        countinSegments: document.getElementById('countin-segments'),
        
        transposeBadge: document.getElementById('transpose-val'),
        btnTransDown: document.getElementById('btn-trans-down'),
        btnTransUp: document.getElementById('btn-trans-up'),
        
        volumePercentText: document.getElementById('volume-percent-text'),
        volumeSlider: document.getElementById('volume-slider'),
        btnVolumeMute: document.getElementById('btn-volume-mute'),
        volumeIcon: document.getElementById('volume-icon'),
        volumePresetPills: document.querySelectorAll('.vol-preset'),

        tempoPercentText: document.getElementById('tempo-percent-text'),
        tempoCalcBpm: document.getElementById('tempo-calc-bpm'),
        tempoSlider: document.getElementById('tempo-slider'),
        btnTempoM5: document.getElementById('btn-tempo-m5'),
        btnTempoM1: document.getElementById('btn-tempo-m1'),
        btnTempo100: document.getElementById('btn-tempo-100'),
        btnTempoP1: document.getElementById('btn-tempo-p1'),
        btnTempoP5: document.getElementById('btn-tempo-p5'),
        presetPills: document.querySelectorAll('.preset-pill:not(.vol-preset)'),
        
        trackList: document.getElementById('track-list'),
        trackCount: document.getElementById('track-count'),
        searchInput: document.getElementById('search-input'),
        btnClearSearch: document.getElementById('btn-clear-search'),
        fileUploadInput: document.getElementById('file-upload-input'),
        toast: document.getElementById('toast'),
        
        // Modal & Dual Mixer
        mixerModal: document.getElementById('mixer-modal'),
        btnCloseMixer: document.getElementById('btn-close-mixer'),
        tabBtnMidi: document.getElementById('tab-btn-midi'),
        tabBtnPulse: document.getElementById('tab-btn-pulse'),
        mixerPanelMidi: document.getElementById('mixer-panel-midi'),
        mixerPanelPulse: document.getElementById('mixer-panel-pulse'),

        // MIDI Mixer
        midiChannelsList: document.getElementById('midi-channels-list'),
        btnResetChannels: document.getElementById('btn-reset-channels'),
        btnUnmuteAll: document.getElementById('btn-unmute-all'),

        // PulseAudio Mixer
        mixerRefreshBtn: document.getElementById('mixer-refresh-btn'),
        mixerSinksList: document.getElementById('mixer-sinks-list'),
        mixerStreamsList: document.getElementById('mixer-streams-list')
    };

    // Apply translations to DOM elements
    function applyLanguage(lang) {
        currentLang = lang;
        localStorage.setItem('40hoursaday_lang', lang);
        document.documentElement.lang = lang;

        // Update active class on language buttons
        elements.langButtons.forEach(btn => {
            if (btn.dataset.lang === lang) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Translate elements with data-i18n
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            el.textContent = t(key);
        });

        // Translate attributes
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.dataset.i18nTitle;
            el.title = t(key);
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.dataset.i18nPlaceholder;
            el.placeholder = t(key);
        });

        // Re-render dynamic text in UI
        updateUI(state.status);
        renderTrackList();
    }

    // Utilities
    function formatTime(seconds) {
        if (!seconds || isNaN(seconds) || seconds < 0) return "00:00";
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    function showToast(msg, duration = 2500) {
        elements.toast.textContent = msg;
        elements.toast.classList.add('show');
        setTimeout(() => {
            elements.toast.classList.remove('show');
        }, duration);
    }

    async function apiPost(endpoint, data = {}) {
        try {
            const res = await fetch(`/api/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await res.json();
        } catch (e) {
            console.error(`API POST ${endpoint} error:`, e);
            return { error: e.message };
        }
    }

    async function apiGet(endpoint) {
        try {
            const res = await fetch(`/api/${endpoint}`);
            return await res.json();
        } catch (e) {
            console.error(`API GET ${endpoint} error:`, e);
            return null;
        }
    }

    // UI Updates
    function updateUI(status) {
        state.status = { ...state.status, ...status };
        state.lastStatusTime = performance.now();
        const s = state.status;

        // Port & Program Change
        if (s.port) {
            elements.portIndicator.classList.add('connected');
        } else {
            elements.portIndicator.classList.remove('connected');
        }

        if (elements.btnPcToggle) {
            if (s.allow_program_change) {
                elements.btnPcToggle.classList.add('active');
                elements.btnPcToggle.title = "Program Change: ALLOWED (Instrument changes enabled)";
            } else {
                elements.btnPcToggle.classList.remove('active');
                elements.btnPcToggle.title = "Program Change: BLOCKED (Preset protected)";
            }
        }

        if (s.available_ports && document.activeElement !== elements.portSelect) {
            populatePorts(s.available_ports, s.port);
        }

        // Track Info
        elements.currentTrackTitle.textContent = s.filename ? s.filename.replace(/\.midi?$/i, '').replace(/[_-]/g, ' ') : t('noTrackSelected');
        elements.trackMeter.textContent = s.time_signature || "-- / --";
        elements.trackBpm.textContent = `${s.bpm || '--'} BPM`;

        // Playback State Badge & Button
        if (s.state === 'playing') {
            elements.stateBadge.textContent = t('statePlaying');
            elements.stateBadge.className = "badge badge-state playing";
            elements.btnPlayPause.innerHTML = "⏸";
            elements.btnPlayPause.title = t('pauseTitle');
        } else if (s.state === 'paused') {
            elements.stateBadge.textContent = t('statePaused');
            elements.stateBadge.className = "badge badge-state paused";
            elements.btnPlayPause.innerHTML = "▶";
            elements.btnPlayPause.title = t('resumeTitle');
        } else {
            elements.stateBadge.textContent = t('stateReady');
            elements.stateBadge.className = "badge badge-state";
            elements.btnPlayPause.innerHTML = "▶";
            elements.btnPlayPause.title = t('playTitle');
        }

        // Scrubber / Time
        elements.timeCurrent.textContent = formatTime(s.position);
        elements.timeTotal.textContent = formatTime(s.duration);
        
        if (!state.isUserSeeking) {
            const pct = s.duration > 0 ? (s.position / s.duration) * 100 : 0;
            elements.progressBar.style.width = `${pct}%`;
            elements.seekSlider.value = pct;
        }

        // Loop
        if (s.loop) {
            elements.btnLoop.classList.add('active');
        } else {
            elements.btnLoop.classList.remove('active');
        }

        // Count-in toggle highlight
        if (elements.btnCountinToggle) {
            if ((s.count_in_bars || 0) > 0) {
                elements.btnCountinToggle.classList.add('active');
            } else {
                elements.btnCountinToggle.classList.remove('active');
            }
        }

        // Count-in Segments (in modal)
        if (elements.countinSegments) {
            const countInButtons = elements.countinSegments.querySelectorAll('.seg-btn');
            countInButtons.forEach(btn => {
                const bars = parseInt(btn.dataset.countin, 10);
                if (bars === (s.count_in_bars || 0)) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }

        // Transpose
        if (elements.transposeBadge) {
            elements.transposeBadge.textContent = s.transpose > 0 ? `+${s.transpose}` : `${s.transpose || 0}`;
        }

        // Master Volume
        const volPct = Math.round((s.volume !== undefined ? s.volume : 1.0) * 100);
        if (elements.volumePercentText) {
            elements.volumePercentText.textContent = `${volPct}%`;
        }
        if (elements.volumeSlider && document.activeElement !== elements.volumeSlider) {
            elements.volumeSlider.value = volPct;
        }
        if (elements.volumeIcon) {
            if (volPct === 0) elements.volumeIcon.textContent = '🔇';
            else if (volPct < 35) elements.volumeIcon.textContent = '🔈';
            else if (volPct < 75) elements.volumeIcon.textContent = '🔉';
            else elements.volumeIcon.textContent = '🔊';
        }
        if (elements.volumePresetPills) {
            elements.volumePresetPills.forEach(pill => {
                const pillPct = Math.round(parseFloat(pill.dataset.volume) * 100);
                if (pillPct === volPct) {
                    pill.classList.add('active');
                } else {
                    pill.classList.remove('active');
                }
            });
        }

        // MIDI Channels (1-10) in MIDI Mixer
        updateMidiChannelsUI();

        // Tempo
        const pct = Math.round((s.speed || 1.0) * 100);
        elements.tempoPercentText.textContent = `${pct}%`;
        const calcBpm = Math.round((s.bpm || 120) * (s.speed || 1.0));
        elements.tempoCalcBpm.textContent = `(${calcBpm} BPM)`;
        
        if (document.activeElement !== elements.tempoSlider) {
            elements.tempoSlider.value = pct;
        }

        // Highlight active preset pill
        elements.presetPills.forEach(pill => {
            const pillPct = Math.round(parseFloat(pill.dataset.speed) * 100);
            if (pillPct === pct) {
                pill.classList.add('active');
            } else {
                pill.classList.remove('active');
            }
        });

        // Highlight active track item in library
        const trackItems = elements.trackList.querySelectorAll('.track-item');
        trackItems.forEach(item => {
            if (item.dataset.filepath === s.filepath) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    function formatPortLabel(portStr) {
        if (!portStr) return "";
        const parts = portStr.split(':');
        const mainName = parts[0].trim();
        const portNumMatch = portStr.match(/(\d+:\d+|\b\d+\b)$/);
        if (portNumMatch) {
            return `${mainName} (${portNumMatch[1]})`;
        }
        return mainName || portStr;
    }

    function findBestPortMatch(selectEl, targetPort) {
        if (!targetPort) return null;
        const options = Array.from(selectEl.options).filter(o => o.value);
        if (options.length === 0) return null;
        
        // 1. Exact match
        let found = options.find(o => o.value === targetPort);
        if (found) return found.value;

        // 2. Case-insensitive exact match
        const tLower = targetPort.toLowerCase().trim();
        found = options.find(o => o.value.toLowerCase().trim() === tLower);
        if (found) return found.value;

        // 3. Option contains target
        found = options.find(o => o.value.toLowerCase().includes(tLower));
        if (found) return found.value;

        // 4. Target contains option
        found = options.find(o => tLower.includes(o.value.toLowerCase()));
        if (found) return found.value;

        return null;
    }

    function populatePorts(ports, selectedPort) {
        if (!ports) ports = [];

        // Normalize unique non-empty ports
        const uniquePorts = [];
        const seen = new Set();
        ports.forEach(p => {
            if (p && !seen.has(p)) {
                seen.add(p);
                uniquePorts.push(p);
            }
        });

        const currentOptions = Array.from(elements.portSelect.options).map(o => o.value).filter(v => v !== '');
        const optionsSame = uniquePorts.length === currentOptions.length && 
                            uniquePorts.every((p, idx) => p === currentOptions[idx]);

        if (!optionsSame) {
            const previousVal = elements.portSelect.value || localStorage.getItem('40hoursaday_preferred_port');
            elements.portSelect.innerHTML = '';
            if (uniquePorts.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = t('noMidiPort');
                elements.portSelect.appendChild(opt);
            } else {
                uniquePorts.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p;
                    opt.textContent = formatPortLabel(p);
                    elements.portSelect.appendChild(opt);
                });
            }
            if (previousVal) {
                const prevMatch = findBestPortMatch(elements.portSelect, previousVal);
                if (prevMatch) elements.portSelect.value = prevMatch;
            }
        }

        const savedPort = localStorage.getItem('40hoursaday_preferred_port');
        const effectivePort = selectedPort || savedPort || state.status.port;

        if (effectivePort) {
            const matched = findBestPortMatch(elements.portSelect, effectivePort);
            if (matched && elements.portSelect.value !== matched) {
                elements.portSelect.value = matched;
                state.status.port = matched;
            }
        }
    }

    // Library Rendering
    function renderTrackList() {
        const query = state.searchQuery.toLowerCase().trim();
        const list = state.files.filter(f => {
            if (!query) return true;
            return (f.display_name && f.display_name.toLowerCase().includes(query)) ||
                   (f.filename && f.filename.toLowerCase().includes(query));
        });

        const countText = list.length === 1 ? t('pieceCountSingle') : t('piecesCount', { n: list.length });
        elements.trackCount.textContent = countText;

        if (list.length === 0) {
            elements.trackList.innerHTML = `
                <div class="empty-state">
                    ${query ? t('noPiecesFound') : t('emptyLibrary')}
                </div>
            `;
            return;
        }

        elements.trackList.innerHTML = list.map(item => `
            <div class="track-item ${state.status.filepath === item.filepath ? 'active' : ''}" data-filepath="${item.filepath}">
                <div class="track-main">
                    <div class="track-name" title="${item.filename}">${item.display_name}</div>
                    <div class="track-meta">
                        ${item.duration_str && item.duration_str !== '--:--' ? `<span>⏱ ${item.duration_str}</span>` : ''}
                        ${item.bpm ? `<span>🎵 ${item.bpm} BPM</span>` : ''}
                    </div>
                </div>
                <div class="track-actions">
                    <button class="btn-play-item" title="${t('playTitle')}">▶</button>
                </div>
            </div>
        `).join('');

        elements.trackList.querySelectorAll('.track-item').forEach(el => {
            el.addEventListener('click', () => {
                const fp = el.dataset.filepath;
                playFile(fp);
            });
        });
    }

    async function loadFiles() {
        const data = await apiGet('files');
        if (data && data.files) {
            state.files = data.files;
            renderTrackList();
        }
    }

    async function loadPorts() {
        const data = await apiGet('ports');
        if (data) {
            populatePorts(data.ports, data.current);
        }
    }

    // Actions
    async function playFile(filepath) {
        showToast(t('toastLoading', { file: filepath.split('/').pop() }));
        const savedPort = localStorage.getItem('40hoursaday_preferred_port');
        const currentPort = elements.portSelect.value || savedPort || state.status.port;
        const res = await apiPost('play', {
            file: filepath,
            speed: state.status.speed,
            volume: state.status.volume,
            port: currentPort,
            loop: state.status.loop,
            count_in: state.status.count_in_bars,
            transpose: state.status.transpose
        });
        if (res && res.status) {
            updateUI(res.status);
        }
    }

    async function togglePlayPause() {
        if (state.status.state === 'playing') {
            const res = await apiPost('pause');
            if (res.status) updateUI(res.status);
        } else if (state.status.state === 'paused') {
            const res = await apiPost('resume');
            if (res.status) updateUI(res.status);
        } else {
            const target = state.status.filepath || (state.files[0] && state.files[0].filepath);
            if (target) {
                playFile(target);
            } else {
                showToast(t('toastPleaseSelect'));
            }
        }
    }

    async function stopPlayback() {
        const res = await apiPost('stop');
        if (res.status) updateUI(res.status);
    }

    let volumeDebounceTimer = null;
    let lastNonZeroVolume = 1.0;
    function setVolumePercent(pct) {
        pct = Math.max(0, Math.min(100, Math.round(pct)));
        const volume = pct / 100.0;
        if (volume > 0) {
            lastNonZeroVolume = volume;
        }
        state.status.volume = volume;
        state.status.volume_percent = pct;
        updateUI({ volume, volume_percent: pct });

        clearTimeout(volumeDebounceTimer);
        volumeDebounceTimer = setTimeout(async () => {
            await apiPost('volume', { volume });
        }, 50);
    }

    let tempoDebounceTimer = null;
    function setTempoPercent(pct) {
        pct = Math.max(10, Math.min(200, Math.round(pct)));
        const speed = pct / 100.0;
        state.status.speed = speed;
        updateUI({ speed, speed_percent: pct });

        clearTimeout(tempoDebounceTimer);
        tempoDebounceTimer = setTimeout(async () => {
            await apiPost('speed', { speed });
        }, 60);
    }

    // Setup Events
    function setupEvents() {
        // Language Buttons
        elements.langButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                applyLanguage(btn.dataset.lang);
            });
        });

        // Play / Pause / Stop
        elements.btnPlayPause.addEventListener('click', togglePlayPause);
        elements.btnStop.addEventListener('click', stopPlayback);

        // Loop Toggle
        elements.btnLoop.addEventListener('click', async () => {
            const newLoop = !state.status.loop;
            const res = await apiPost('loop', { loop: newLoop });
            if (res.status) updateUI(res.status);
            showToast(newLoop ? t('toastLoopOn') : t('toastLoopOff'));
        });

        // Count-in toggle button (cycles 0 -> 1 -> 2 -> 0)
        if (elements.btnCountinToggle) {
            elements.btnCountinToggle.addEventListener('click', async () => {
                const current = state.status.count_in_bars || 0;
                const next = (current + 1) % 3;
                const res = await apiPost('count_in', { count_in_bars: next });
                if (res.status) updateUI(res.status);
                const plural = currentLang === 'de' ? (next > 1 ? 'e' : '') : (next > 1 ? 's' : '');
                showToast(next > 0 ? t('toastCountinSet', { bars: next, plural }) : t('toastCountinOff'));
            });
        }

        // Count-in Segments
        if (elements.countinSegments) {
            elements.countinSegments.querySelectorAll('.seg-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const bars = parseInt(btn.dataset.countin, 10);
                    const res = await apiPost('count_in', { count_in_bars: bars });
                    if (res.status) updateUI(res.status);
                    const plural = currentLang === 'de' ? (bars > 1 ? 'e' : '') : (bars > 1 ? 's' : '');
                    showToast(bars > 0 ? t('toastCountinSet', { bars, plural }) : t('toastCountinOff'));
                });
            });
        }

        // Transpose Controls
        if (elements.btnTransDown) {
            elements.btnTransDown.addEventListener('click', async () => {
                const newTrans = (state.status.transpose || 0) - 1;
                const res = await apiPost('transpose', { transpose: newTrans });
                if (res.status) updateUI(res.status);
            });
        }

        if (elements.btnTransUp) {
            elements.btnTransUp.addEventListener('click', async () => {
                const newTrans = (state.status.transpose || 0) + 1;
                const res = await apiPost('transpose', { transpose: newTrans });
                if (res.status) updateUI(res.status);
            });
        }

        // MIDI Panic
        elements.btnPanic.addEventListener('click', async () => {
            await apiPost('panic');
            showToast(t('toastPanic'));
        });

        // Port Selector
        elements.portSelect.addEventListener('change', async (e) => {
            const port = e.target.value;
            if (port) {
                state.status.port = port;
                try {
                    localStorage.setItem('40hoursaday_preferred_port', port);
                } catch (e) {}
                const res = await apiPost('port', { port });
                if (res && res.status) updateUI(res.status);
                showToast(t('toastPort', { port: formatPortLabel(port) }));
            }
        });

        // Program Change Per-Port Toggle
        if (elements.btnPcToggle) {
            elements.btnPcToggle.addEventListener('click', async () => {
                const currentPort = elements.portSelect.value || state.status.port;
                if (!currentPort) return;
                const newAllowed = !state.status.allow_program_change;
                state.status.allow_program_change = newAllowed;
                updateUI(state.status);

                const res = await apiPost('port/program_change', { port: currentPort, allow: newAllowed });
                if (res && res.status) {
                    updateUI(res.status);
                }
                showToast(newAllowed ? "Program Change: ALLOWED (Instrument switching enabled)" : "Program Change: BLOCKED (Preset protected)");
            });
        }

        // Master Volume Slider
        if (elements.volumeSlider) {
            elements.volumeSlider.addEventListener('input', (e) => {
                setVolumePercent(parseFloat(e.target.value));
            });
        }

        // Master Volume Mute Button
        if (elements.btnVolumeMute) {
            elements.btnVolumeMute.addEventListener('click', () => {
                if ((state.status.volume || 1.0) > 0) {
                    lastNonZeroVolume = state.status.volume || 1.0;
                    setVolumePercent(0);
                } else {
                    setVolumePercent(Math.round((lastNonZeroVolume || 1.0) * 100));
                }
            });
        }

        // Master Volume Presets
        if (elements.volumePresetPills) {
            elements.volumePresetPills.forEach(pill => {
                pill.addEventListener('click', () => {
                    const vol = parseFloat(pill.dataset.volume);
                    setVolumePercent(vol * 100);
                });
            });
        }

        // MIDI Mixer Action Buttons
        if (elements.btnResetChannels) {
            elements.btnResetChannels.addEventListener('click', async () => {
                const newVols = {};
                for (let ch = 1; ch <= 10; ch++) newVols[ch] = 100;
                state.status.channel_volumes = newVols;
                updateMidiChannelsUI();
                const res = await apiPost('channel/reset_volumes');
                if (res && res.status) updateUI(res.status);
                showToast(t('toastChannelsReset'));
            });
        }

        if (elements.btnUnmuteAll) {
            elements.btnUnmuteAll.addEventListener('click', async () => {
                state.status.muted_channels = [];
                updateMidiChannelsUI();
                const res = await apiPost('channel/unmute_all');
                if (res && res.status) updateUI(res.status);
                showToast(t('toastAllChannelsUnmuted'));
            });
        }

        // Tempo Slider
        elements.tempoSlider.addEventListener('input', (e) => {
            setTempoPercent(parseFloat(e.target.value));
        });

        // Stepper buttons
        elements.btnTempoM5.addEventListener('click', () => setTempoPercent((state.status.speed * 100) - 5));
        elements.btnTempoM1.addEventListener('click', () => setTempoPercent((state.status.speed * 100) - 1));
        elements.btnTempo100.addEventListener('click', () => setTempoPercent(100));
        elements.btnTempoP1.addEventListener('click', () => setTempoPercent((state.status.speed * 100) + 1));
        elements.btnTempoP5.addEventListener('click', () => setTempoPercent((state.status.speed * 100) + 5));

        // Presets
        elements.presetPills.forEach(pill => {
            pill.addEventListener('click', () => {
                const speed = parseFloat(pill.dataset.speed);
                setTempoPercent(speed * 100);
            });
        });

        // Scrubber / Seek
        elements.seekSlider.addEventListener('mousedown', () => { state.isUserSeeking = true; });
        elements.seekSlider.addEventListener('touchstart', () => { state.isUserSeeking = true; }, { passive: true });

        elements.seekSlider.addEventListener('input', (e) => {
            const pct = parseFloat(e.target.value);
            elements.progressBar.style.width = `${pct}%`;
            const dur = state.status.duration || 0;
            const targetSec = (pct / 100) * dur;
            elements.timeCurrent.textContent = formatTime(targetSec);
        });

        elements.seekSlider.addEventListener('change', async (e) => {
            state.isUserSeeking = false;
            const pct = parseFloat(e.target.value);
            const dur = state.status.duration || 0;
            const targetSec = (pct / 100) * dur;
            const res = await apiPost('seek', { position: targetSec });
            if (res.status) updateUI(res.status);
        });

        // Search Box
        elements.searchInput.addEventListener('input', (e) => {
            state.searchQuery = e.target.value;
            elements.btnClearSearch.style.display = state.searchQuery ? 'block' : 'none';
            renderTrackList();
        });

        elements.btnClearSearch.addEventListener('click', () => {
            state.searchQuery = '';
            elements.searchInput.value = '';
            elements.btnClearSearch.style.display = 'none';
            renderTrackList();
        });

        // File Upload
        elements.fileUploadInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            showToast(t('toastUploading', { file: file.name }));
            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.success && data.file) {
                    showToast(t('toastUploadSuccess', { title: data.file.display_name }));
                    await loadFiles();
                    playFile(data.file.filepath);
                } else {
                    showToast(t('toastUploadError', { error: data.error || 'Unknown' }));
                }
            } catch (err) {
                showToast(t('toastUploadError', { error: err.message }));
            }
            elements.fileUploadInput.value = '';
        });

        // Dual Mixer Modal Events
        if (elements.btnMidiMixer) {
            elements.btnMidiMixer.addEventListener('click', () => {
                if (isMixerOpen && activeMixerTab === 'midi') {
                    closeMixer();
                } else {
                    openMixer('midi');
                }
            });
        }

        if (elements.btnPulseMixer) {
            elements.btnPulseMixer.addEventListener('click', () => {
                if (isMixerOpen && activeMixerTab === 'pulse') {
                    closeMixer();
                } else {
                    openMixer('pulse');
                }
            });
        }

        if (elements.tabBtnMidi) {
            elements.tabBtnMidi.addEventListener('click', () => switchMixerTab('midi'));
        }

        if (elements.tabBtnPulse) {
            elements.tabBtnPulse.addEventListener('click', () => switchMixerTab('pulse'));
        }

        if (elements.btnCloseMixer) {
            elements.btnCloseMixer.addEventListener('click', closeMixer);
        }

        if (elements.mixerModal) {
            elements.mixerModal.addEventListener('click', (e) => {
                if (e.target === elements.mixerModal) {
                    closeMixer();
                }
            });
        }

        if (elements.mixerRefreshBtn) {
            elements.mixerRefreshBtn.addEventListener('click', () => {
                loadMixer();
            });
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isMixerOpen) {
                closeMixer();
            }
        });
    }

    // Dual Mixer Controller (MIDI & PulseAudio)
    let isMixerOpen = false;
    let activeMixerTab = 'midi';
    let mixerPollTimer = null;
    let isDraggingMixer = false;
    let isDraggingMidiMixer = false;
    let mixerDebounceTimers = {};
    let midiDebounceTimers = {};

    function switchMixerTab(tab) {
        activeMixerTab = tab;
        if (tab === 'midi') {
            if (elements.tabBtnMidi) elements.tabBtnMidi.classList.add('active');
            if (elements.tabBtnPulse) elements.tabBtnPulse.classList.remove('active');
            if (elements.mixerPanelMidi) elements.mixerPanelMidi.style.display = 'flex';
            if (elements.mixerPanelPulse) elements.mixerPanelPulse.style.display = 'none';
        } else {
            if (elements.tabBtnPulse) elements.tabBtnPulse.classList.add('active');
            if (elements.tabBtnMidi) elements.tabBtnMidi.classList.remove('active');
            if (elements.mixerPanelPulse) elements.mixerPanelPulse.style.display = 'flex';
            if (elements.mixerPanelMidi) elements.mixerPanelMidi.style.display = 'none';
            loadMixer();
        }
    }

    function openMixer(tab = 'midi') {
        isMixerOpen = true;
        switchMixerTab(tab);
        elements.mixerModal.style.display = 'flex';
        void elements.mixerModal.offsetWidth;
        elements.mixerModal.classList.add('open');
        if (tab === 'pulse') loadMixer();
        if (mixerPollTimer) clearInterval(mixerPollTimer);
        mixerPollTimer = setInterval(() => {
            if (isMixerOpen && activeMixerTab === 'pulse' && !isDraggingMixer) {
                loadMixer();
            }
        }, 1500);
    }

    function closeMixer() {
        isMixerOpen = false;
        elements.mixerModal.classList.remove('open');
        if (mixerPollTimer) {
            clearInterval(mixerPollTimer);
            mixerPollTimer = null;
        }
        setTimeout(() => {
            if (!isMixerOpen) {
                elements.mixerModal.style.display = 'none';
            }
        }, 200);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function debounceMixer(key, fn, delay = 50) {
        clearTimeout(mixerDebounceTimers[key]);
        mixerDebounceTimers[key] = setTimeout(fn, delay);
    }

    // MIDI Channels Strip Rendering
    const midiChannelDescriptions = {
        1: "Lead / Melody (Ch 1)",
        2: "Accompaniment (Ch 2)",
        3: "Bass / Harmony (Ch 3)",
        4: "Track 4",
        5: "Track 5",
        6: "Track 6",
        7: "Track 7",
        8: "Track 8",
        9: "Track 9",
        10: "Percussion / Drums 🥁 (Ch 10)"
    };

    function renderMidiChannels() {
        if (!elements.midiChannelsList) return;
        const muted = state.status.muted_channels || [];
        const volumes = state.status.channel_volumes || {};

        let html = '';
        for (let ch = 1; ch <= 10; ch++) {
            const isMuted = muted.includes(ch);
            const vol = (volumes[ch] !== undefined) ? volumes[ch] : 100;
            const icon = (ch === 10) ? '🥁' : '🎹';
            const sub = midiChannelDescriptions[ch] || `MIDI Channel ${ch}`;

            html += `
                <div class="midi-channel-card ${isMuted ? 'muted' : ''} ${ch === 10 ? 'drum' : ''}" id="midi-ch-card-${ch}">
                    <div class="mixer-channel-top">
                        <div class="mixer-channel-meta">
                            <span class="mixer-channel-icon">${icon}</span>
                            <div class="mixer-channel-names">
                                <span class="mixer-channel-title">Channel ${ch}</span>
                                <span class="mixer-channel-sub">${escapeHtml(sub)}</span>
                            </div>
                        </div>
                        <div class="mixer-channel-actions">
                            <span class="mixer-vol-badge" id="midi-ch-val-${ch}">${vol}%</span>
                            <button class="btn-mute ${isMuted ? 'is-muted' : ''}" data-midi-ch-mute="${ch}" data-muted="${isMuted}" title="${isMuted ? t('mixerUnmute') : t('mixerMute')}">
                                ${isMuted ? '🔇' : '🔊'}
                            </button>
                        </div>
                    </div>
                    <div class="mixer-slider-row">
                        <input type="range" class="mixer-slider" min="0" max="100" value="${vol}" data-midi-ch-slider="${ch}">
                    </div>
                </div>
            `;
        }
        elements.midiChannelsList.innerHTML = html;
        bindMidiChannelEvents();
    }

    function updateMidiChannelsUI() {
        const muted = state.status.muted_channels || [];
        const volumes = state.status.channel_volumes || {};

        for (let ch = 1; ch <= 10; ch++) {
            const card = document.getElementById(`midi-ch-card-${ch}`);
            const valBadge = document.getElementById(`midi-ch-val-${ch}`);
            const slider = elements.midiChannelsList ? elements.midiChannelsList.querySelector(`[data-midi-ch-slider="${ch}"]`) : null;
            const muteBtn = elements.midiChannelsList ? elements.midiChannelsList.querySelector(`[data-midi-ch-mute="${ch}"]`) : null;

            const isMuted = muted.includes(ch);
            const vol = (volumes[ch] !== undefined) ? volumes[ch] : 100;

            if (card) {
                if (isMuted) card.classList.add('muted');
                else card.classList.remove('muted');
            }
            if (muteBtn) {
                muteBtn.setAttribute('data-muted', isMuted);
                muteBtn.innerHTML = isMuted ? '🔇' : '🔊';
                if (isMuted) muteBtn.classList.add('is-muted');
                else muteBtn.classList.remove('is-muted');
                muteBtn.title = isMuted ? t('mixerUnmute') : t('mixerMute');
            }
            if (valBadge) {
                valBadge.textContent = `${vol}%`;
            }
            if (slider && !isDraggingMidiMixer && document.activeElement !== slider) {
                slider.value = vol;
            }
        }
    }

    function bindMidiChannelEvents() {
        if (!elements.midiChannelsList) return;

        // Channel sliders
        elements.midiChannelsList.querySelectorAll('[data-midi-ch-slider]').forEach(slider => {
            const ch = parseInt(slider.getAttribute('data-midi-ch-slider'), 10);
            const valBadge = document.getElementById(`midi-ch-val-${ch}`);

            const onInput = (e) => {
                isDraggingMidiMixer = true;
                const vol = parseInt(e.target.value, 10);
                if (valBadge) valBadge.textContent = `${vol}%`;
                if (!state.status.channel_volumes) state.status.channel_volumes = {};
                state.status.channel_volumes[ch] = vol;

                clearTimeout(midiDebounceTimers[`ch_${ch}`]);
                midiDebounceTimers[`ch_${ch}`] = setTimeout(() => {
                    apiPost('channel/volume', { channel: ch, volume: vol });
                }, 40);
            };

            const onChange = () => {
                isDraggingMidiMixer = false;
            };

            slider.addEventListener('input', onInput);
            slider.addEventListener('change', onChange);
            slider.addEventListener('touchend', onChange);
            slider.addEventListener('mouseup', onChange);
        });

        // Channel mute buttons
        elements.midiChannelsList.querySelectorAll('[data-midi-ch-mute]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const ch = parseInt(btn.getAttribute('data-midi-ch-mute'), 10);
                const isCurrentlyMuted = btn.getAttribute('data-muted') === 'true';
                const newMuteState = !isCurrentlyMuted;

                // Optimistic update
                if (newMuteState) {
                    if (!state.status.muted_channels) state.status.muted_channels = [];
                    if (!state.status.muted_channels.includes(ch)) state.status.muted_channels.push(ch);
                } else {
                    state.status.muted_channels = (state.status.muted_channels || []).filter(c => c !== ch);
                }
                updateMidiChannelsUI();

                const res = await apiPost('channel/mute', { channel: ch, mute: newMuteState });
                if (res && res.status) {
                    updateUI(res.status);
                }
                showToast(newMuteState ? t('toastChannelMuted', { ch }) : t('toastChannelUnmuted', { ch }));
            });
        });
    }

    // PulseAudio Streams & Sinks
    async function loadMixer() {
        try {
            const data = await apiGet('mixer');
            if (data && isMixerOpen && activeMixerTab === 'pulse' && !isDraggingMixer) {
                renderPulseMixer(data);
            }
        } catch (err) {
            console.error("Failed to load mixer:", err);
        }
    }

    function getStreamIcon(name, mediaName) {
        const str = ((name || '') + ' ' + (mediaName || '')).toLowerCase();
        if (str.includes('shairport') || str.includes('airplay')) return '📱';
        if (str.includes('pianoteq')) return '🎹';
        if (str.includes('spotify') || str.includes('librespot')) return '🎵';
        if (str.includes('browser') || str.includes('chrome') || str.includes('firefox')) return '🌐';
        return '🔊';
    }

    function getChannelClass(name) {
        const str = (name || '').toLowerCase();
        if (str.includes('shairport') || str.includes('airplay')) return 'shairport';
        if (str.includes('pianoteq')) return 'pianoteq';
        return '';
    }

    function renderPulseMixer(data) {
        const sinks = data.sinks || [];
        const streams = data.streams || [];

        // Render Sinks (Master Outputs)
        if (sinks.length === 0) {
            elements.mixerSinksList.innerHTML = `<div class="mixer-empty">${t('mixerLoading')}</div>`;
        } else {
            elements.mixerSinksList.innerHTML = sinks.map(s => `
                <div class="mixer-channel-card master ${s.mute ? 'muted' : ''}" id="sink-card-${s.id}">
                    <div class="mixer-channel-top">
                        <div class="mixer-channel-meta">
                            <span class="mixer-channel-icon">🔊</span>
                            <div class="mixer-channel-names">
                                <span class="mixer-channel-title">${escapeHtml(s.description)}</span>
                                <span class="mixer-channel-sub">${escapeHtml(s.name)}</span>
                            </div>
                        </div>
                        <div class="mixer-channel-actions">
                            <span class="mixer-vol-badge" id="sink-val-${s.id}">${s.volume}%</span>
                            <button class="btn-mute ${s.mute ? 'is-muted' : ''}" data-sink-mute="${s.id}" data-muted="${s.mute}" title="${s.mute ? t('mixerUnmute') : t('mixerMute')}">
                                ${s.mute ? '🔇' : '🔊'}
                            </button>
                        </div>
                    </div>
                    <div class="mixer-slider-row">
                        <input type="range" class="mixer-slider" min="0" max="100" value="${s.volume}" data-sink-slider="${s.id}">
                    </div>
                </div>
            `).join('');
        }

        // Render Streams (Application Inputs)
        if (streams.length === 0) {
            elements.mixerStreamsList.innerHTML = `<div class="mixer-empty">${t('mixerNoStreams')}</div>`;
        } else {
            elements.mixerStreamsList.innerHTML = streams.map(st => {
                const icon = getStreamIcon(st.name, st.raw_media);
                const cardClass = getChannelClass(st.name);
                return `
                    <div class="mixer-channel-card ${cardClass} ${st.mute ? 'muted' : ''}" id="stream-card-${st.id}">
                        <div class="mixer-channel-top">
                            <div class="mixer-channel-meta">
                                <span class="mixer-channel-icon">${icon}</span>
                                <div class="mixer-channel-names">
                                    <span class="mixer-channel-title">${escapeHtml(st.name)}</span>
                                    <span class="mixer-channel-sub">${escapeHtml(st.raw_media || st.raw_app || '')}</span>
                                </div>
                            </div>
                            <div class="mixer-channel-actions">
                                <span class="mixer-vol-badge" id="stream-val-${st.id}">${st.volume}%</span>
                                <button class="btn-mute ${st.mute ? 'is-muted' : ''}" data-stream-mute="${st.id}" data-muted="${st.mute}" title="${st.mute ? t('mixerUnmute') : t('mixerMute')}">
                                    ${st.mute ? '🔇' : '🔊'}
                                </button>
                            </div>
                        </div>
                        <div class="mixer-slider-row">
                            <input type="range" class="mixer-slider" min="0" max="100" value="${st.volume}" data-stream-slider="${st.id}">
                        </div>
                    </div>
                `;
            }).join('');
        }

        bindPulseMixerEvents();
    }

    function bindPulseMixerEvents() {
        // Sink sliders
        elements.mixerSinksList.querySelectorAll('[data-sink-slider]').forEach(slider => {
            const sinkId = parseInt(slider.getAttribute('data-sink-slider'), 10);
            const valBadge = document.getElementById(`sink-val-${sinkId}`);

            const onInput = (e) => {
                isDraggingMixer = true;
                const vol = parseInt(e.target.value, 10);
                if (valBadge) valBadge.textContent = `${vol}%`;
                debounceMixer(`sink_${sinkId}`, () => {
                    apiPost('mixer/sink/volume', { id: sinkId, volume: vol });
                }, 40);
            };

            const onChange = () => {
                isDraggingMixer = false;
            };

            slider.addEventListener('input', onInput);
            slider.addEventListener('change', onChange);
            slider.addEventListener('touchend', onChange);
            slider.addEventListener('mouseup', onChange);
        });

        // Sink mute buttons
        elements.mixerSinksList.querySelectorAll('[data-sink-mute]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const sinkId = parseInt(btn.getAttribute('data-sink-mute'), 10);
                const isCurrentlyMuted = btn.getAttribute('data-muted') === 'true';
                const res = await apiPost('mixer/sink/mute', { id: sinkId, mute: !isCurrentlyMuted });
                if (res && res.status) renderPulseMixer(res.status);
            });
        });

        // Stream sliders
        elements.mixerStreamsList.querySelectorAll('[data-stream-slider]').forEach(slider => {
            const streamId = parseInt(slider.getAttribute('data-stream-slider'), 10);
            const valBadge = document.getElementById(`stream-val-${streamId}`);

            const onInput = (e) => {
                isDraggingMixer = true;
                const vol = parseInt(e.target.value, 10);
                if (valBadge) valBadge.textContent = `${vol}%`;
                debounceMixer(`stream_${streamId}`, () => {
                    apiPost('mixer/stream/volume', { id: streamId, volume: vol });
                }, 40);
            };

            const onChange = () => {
                isDraggingMixer = false;
            };

            slider.addEventListener('input', onInput);
            slider.addEventListener('change', onChange);
            slider.addEventListener('touchend', onChange);
            slider.addEventListener('mouseup', onChange);
        });

        // Stream mute buttons
        elements.mixerStreamsList.querySelectorAll('[data-stream-mute]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const streamId = parseInt(btn.getAttribute('data-stream-mute'), 10);
                const isCurrentlyMuted = btn.getAttribute('data-muted') === 'true';
                const res = await apiPost('mixer/stream/mute', { id: streamId, mute: !isCurrentlyMuted });
                if (res && res.status) renderPulseMixer(res.status);
            });
        });
    }

    // 60 FPS Flashing Metronome & Bar Counter Animation Engine
    let lastRenderedBeatsPerBar = 0;
    let lastFlashedBeat = -1;
    let flashTimer = null;

    function renderMetronomeDots(beatsPerBar) {
        if (!elements.metroDotsRow) return;
        beatsPerBar = Math.max(1, beatsPerBar || 4);
        if (lastRenderedBeatsPerBar === beatsPerBar) return;
        lastRenderedBeatsPerBar = beatsPerBar;

        let html = '';
        for (let b = 1; b <= beatsPerBar; b++) {
            const isAccent = (b === 1);
            html += `<span class="metro-dot ${isAccent ? 'dot-accent' : ''}" data-beat="${b}"></span>`;
        }
        elements.metroDotsRow.innerHTML = html;
    }

    function updateMetronomeFrame() {
        const s = state.status;
        const beatsPerBar = s.time_sig_num || s.beats_per_bar || 4;
        renderMetronomeDots(beatsPerBar);

        // Count-in Active Mode
        if (s.count_in_active) {
            if (elements.metroCountinBadge) {
                elements.metroCountinBadge.style.display = 'block';
                if (elements.metroCountinBeat) elements.metroCountinBeat.textContent = s.count_in_current_beat || 1;
                if (elements.metroCountinTotal) elements.metroCountinTotal.textContent = s.count_in_total_beats || 4;
            }
            if (elements.metroDotsRow) elements.metroDotsRow.style.display = 'none';
            if (elements.metroBarVal) elements.metroBarVal.textContent = "0";
            if (elements.metroBeatVal) elements.metroBeatVal.textContent = s.count_in_current_beat || 1;
            if (elements.metroBeatSub) elements.metroBeatSub.textContent = `/ ${s.count_in_total_beats || 4}`;
            if (elements.metroPulseBar) elements.metroPulseBar.style.width = '100%';
            return;
        } else {
            if (elements.metroCountinBadge) elements.metroCountinBadge.style.display = 'none';
            if (elements.metroDotsRow) elements.metroDotsRow.style.display = 'flex';
        }

        let currentBar = s.bar || 1;
        let currentBeat = s.beat || 1;
        let beatFraction = s.beat_fraction || 0.0;

        // Smooth 60fps interpolation between SSE status updates
        if (s.state === 'playing') {
            const now = performance.now();
            const elapsedSec = (now - state.lastStatusTime) / 1000.0;
            const currentPos = Math.min(s.duration || 0, s.position + elapsedSec * (s.speed || 1.0));

            const effectiveBpm = Math.max(10, s.bpm || 120);
            const secPerBeat = 60.0 / effectiveBpm;
            const totalBeats = currentPos / secPerBeat;
            currentBar = Math.floor(totalBeats / beatsPerBar) + 1;
            currentBeat = (Math.floor(totalBeats) % beatsPerBar) + 1;
            beatFraction = totalBeats % 1.0;
        }

        // Update Counter Display
        if (elements.metroBarVal) elements.metroBarVal.textContent = currentBar;
        if (elements.metroBeatVal) elements.metroBeatVal.textContent = currentBeat;
        if (elements.metroBeatSub) elements.metroBeatSub.textContent = `/ ${beatsPerBar}`;
        if (elements.metroPulseBar) {
            elements.metroPulseBar.style.width = s.state === 'playing' ? `${Math.min(100, Math.max(0, beatFraction * 100))}%` : '0%';
        }

        // Trigger Flashing on Beat Transitions during active playback
        if (s.state === 'playing' && currentBeat !== lastFlashedBeat) {
            lastFlashedBeat = currentBeat;
            if (elements.metroDeck) {
                clearTimeout(flashTimer);
                elements.metroDeck.classList.remove('flash-accent', 'flash-beat');
                if (currentBeat === 1) {
                    elements.metroDeck.classList.add('flash-accent');
                    flashTimer = setTimeout(() => {
                        if (elements.metroDeck) elements.metroDeck.classList.remove('flash-accent');
                    }, 140);
                } else {
                    elements.metroDeck.classList.add('flash-beat');
                    flashTimer = setTimeout(() => {
                        if (elements.metroDeck) elements.metroDeck.classList.remove('flash-beat');
                    }, 100);
                }
            }
        } else if (s.state !== 'playing') {
            lastFlashedBeat = -1;
            if (elements.metroDeck) elements.metroDeck.classList.remove('flash-accent', 'flash-beat');
        }

        // Update Active LED Beat Dot
        if (elements.metroDotsRow) {
            elements.metroDotsRow.querySelectorAll('.metro-dot').forEach(dot => {
                const b = parseInt(dot.getAttribute('data-beat'), 10);
                if (b === currentBeat && s.state === 'playing') {
                    if (b === 1) {
                        dot.classList.add('active');
                        dot.classList.remove('beat-active');
                    } else {
                        dot.classList.add('beat-active');
                        dot.classList.remove('active');
                    }
                } else {
                    dot.classList.remove('active', 'beat-active');
                }
            });
        }
    }

    function startMetronomeLoop() {
        function loop() {
            updateMetronomeFrame();
            requestAnimationFrame(loop);
        }
        requestAnimationFrame(loop);
    }

    // Real-time Event Stream (SSE)
    function startEventStream() {
        if (!window.EventSource) {
            setInterval(async () => {
                const status = await apiGet('status');
                if (status) updateUI(status);
            }, 250);
            return;
        }

        const evtSource = new EventSource('/api/events');
        
        evtSource.onmessage = (e) => {
            try {
                const status = JSON.parse(e.data);
                updateUI(status);
            } catch (err) {
                console.error("SSE parse error:", err);
            }
        };

        evtSource.onerror = () => {
            // Automatic browser reconnection
        };
    }

    // Init
    async function init() {
        renderMidiChannels();
        setupEvents();
        applyLanguage(currentLang);

        const savedPort = localStorage.getItem('40hoursaday_preferred_port');
        if (savedPort) {
            await apiPost('port', { port: savedPort });
        }

        await loadPorts();
        await loadFiles();
        
        const initialStatus = await apiGet('status');
        if (initialStatus) {
            updateUI(initialStatus);
        }

        startMetronomeLoop();
        startEventStream();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
