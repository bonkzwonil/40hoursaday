// 40hoursaday - Web Client Logic with Multilingual (EN/DE) Support
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
            toastUploading: "Uploading {file}...",
            toastUploadSuccess: "✅ \"{title}\" added!",
            toastUploadError: "Upload failed: {error}"
        },
        de: {
            appSubtitle: "MIDI Übungsbegleiter",
            loadingPorts: "Lade Ports...",
            noMidiPort: "Kein MIDI Port",
            panicTitle: "MIDI Panic (Stoppe alle Töne)",
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
            toastUploading: "Lade {file} hoch...",
            toastUploadSuccess: "✅ \"{title}\" hinzugefügt!",
            toastUploadError: "Upload-Fehler: {error}"
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
            loop: false,
            transpose: 0,
            count_in_bars: 0,
            port: null,
            available_ports: [],
            bpm: 120,
            time_signature: '4/4'
        },
        files: [],
        filteredFiles: [],
        searchQuery: '',
        isUserSeeking: false,
        lastStatusUpdate: 0
    };

    // DOM Elements
    const elements = {
        langButtons: document.querySelectorAll('.lang-btn'),
        portSelect: document.getElementById('midi-port-select'),
        portIndicator: document.getElementById('port-indicator'),
        btnPanic: document.getElementById('btn-panic'),
        
        currentTrackTitle: document.getElementById('current-track-title'),
        trackMeter: document.getElementById('track-meter'),
        trackBpm: document.getElementById('track-bpm'),
        stateBadge: document.getElementById('playback-state-badge'),
        
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
        
        tempoPercentText: document.getElementById('tempo-percent-text'),
        tempoCalcBpm: document.getElementById('tempo-calc-bpm'),
        tempoSlider: document.getElementById('tempo-slider'),
        btnTempoM5: document.getElementById('btn-tempo-m5'),
        btnTempoM1: document.getElementById('btn-tempo-m1'),
        btnTempo100: document.getElementById('btn-tempo-100'),
        btnTempoP1: document.getElementById('btn-tempo-p1'),
        btnTempoP5: document.getElementById('btn-tempo-p5'),
        presetPills: document.querySelectorAll('.preset-pill'),
        
        trackList: document.getElementById('track-list'),
        trackCount: document.getElementById('track-count'),
        searchInput: document.getElementById('search-input'),
        btnClearSearch: document.getElementById('btn-clear-search'),
        fileUploadInput: document.getElementById('file-upload-input'),
        toast: document.getElementById('toast')
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
        const s = state.status;

        // Port
        if (s.port) {
            elements.portIndicator.classList.add('connected');
        } else {
            elements.portIndicator.classList.remove('connected');
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

        // Count-in Segments
        const countInButtons = elements.countinSegments.querySelectorAll('.seg-btn');
        countInButtons.forEach(btn => {
            const bars = parseInt(btn.dataset.countin, 10);
            if (bars === (s.count_in_bars || 0)) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Transpose
        elements.transposeBadge.textContent = s.transpose > 0 ? `+${s.transpose}` : `${s.transpose || 0}`;

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

        // Check if options actually changed to avoid blowing away user selection / DOM state
        const currentOptions = Array.from(elements.portSelect.options).map(o => o.value).filter(v => v !== '');
        const optionsSame = uniquePorts.length === currentOptions.length && 
                            uniquePorts.every((p, idx) => p === currentOptions[idx]);

        if (!optionsSame) {
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
        }

        // Set selected value without resetting if user is currently interacting
        if (selectedPort) {
            const hasOption = Array.from(elements.portSelect.options).some(o => o.value === selectedPort);
            if (hasOption && elements.portSelect.value !== selectedPort) {
                elements.portSelect.value = selectedPort;
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
                        <span>⏱ ${item.duration_str}</span>
                        <span>🎵 ${item.bpm} BPM</span>
                    </div>
                </div>
                <div class="track-actions">
                    <button class="btn-play-item" title="${t('playTitle')}">▶</button>
                </div>
            </div>
        `).join('');

        // Attach item click listeners
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
        const currentPort = elements.portSelect.value || state.status.port;
        const res = await apiPost('play', {
            file: filepath,
            speed: state.status.speed,
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

    // Event Listeners Setup
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
        elements.countinSegments.querySelectorAll('.seg-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const bars = parseInt(btn.dataset.countin, 10);
                const res = await apiPost('count_in', { count_in_bars: bars });
                if (res.status) updateUI(res.status);
                const plural = currentLang === 'de' ? (bars > 1 ? 'e' : '') : (bars > 1 ? 's' : '');
                showToast(bars > 0 ? t('toastCountinSet', { bars, plural }) : t('toastCountinOff'));
            });
        });

        // Transpose Controls
        elements.btnTransDown.addEventListener('click', async () => {
            const newTrans = (state.status.transpose || 0) - 1;
            const res = await apiPost('transpose', { transpose: newTrans });
            if (res.status) updateUI(res.status);
        });

        elements.btnTransUp.addEventListener('click', async () => {
            const newTrans = (state.status.transpose || 0) + 1;
            const res = await apiPost('transpose', { transpose: newTrans });
            if (res.status) updateUI(res.status);
        });

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
                const res = await apiPost('port', { port });
                if (res && res.status) updateUI(res.status);
                showToast(t('toastPort', { port: formatPortLabel(port) }));
            }
        });

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
        setupEvents();
        applyLanguage(currentLang);
        await loadPorts();
        await loadFiles();
        
        const initialStatus = await apiGet('status');
        if (initialStatus) {
            updateUI(initialStatus);
        }

        startEventStream();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
