# 🎻 40 Hours a Day — MIDI Practice Partner

A modern, mobile-first MIDI practice assistant for musicians (violin, piano, etc.) designed to play accompaniment pieces directly to ALSA/Pianoteq or any MIDI sound generator on your local machine or network server.

Optimized for smartphones on music stands: quick piece selection, touch-friendly UI, real-time dynamic tempo scaling (10% – 200%), loop mode, metronome count-in, and ALSA MIDI output device selection.

<p align="center">
  <img src="screenshot.png" alt="40 Hours a Day - Web Interface Screenshot" width="480">
</p>

---

## 🇬🇧 English Documentation

### ✨ Features

- 📱 **Mobile-First Web UI**: Tailored for smartphone screens on a music stand or piano desk (large touch buttons, high-contrast dark theme).
- 🌍 **Multilingual (EN / DE)**: Quick language toggle in the header, automatic browser locale detection, and persistent preference.
- 🎚 **Real-time Tempo Adjustment (10% – 200%)**:
  - Continuous slider showing current percentage and effective BPM.
  - Fine-tuning stepper buttons (`-5%`, `-1%`, `100% Reset`, `+1%`, `+5%`).
  - Quick preset buttons (`50%`, `65%`, `75%`, `85%`, `90%`, `100%`, `110%`, `125%`).
  - Live updates without interrupting playback.
- ⏱ **Metronome Count-In (Lead-in)**: Selectable (`Off`, `1 Bar`, `2 Bars`). Plays woodblock click beats matching the piece's time signature and tempo so you have time to set your bow and start right on beat 1.
- 🔁 **Loop Mode**: Seamless repeat for practicing difficult musical passages.
- ⏩ **Interactive Scrubber**: Seek forward and backward to any section in the piece.
- ♯♭ **Pitch Transpose**: Transpose pitch up or down in semitone steps.
- 🎹 **MIDI Device / ALSA Port Selector**: Automatically detects all available ALSA output ports (`Midi Through`, `Pianoteq STAGE`, `USB Midi Cable`, etc.).
- 🚨 **MIDI Panic Button**: Instantly sends *All-Notes-Off* (CC 123), *All-Sound-Off* (CC 120), and releases sustain pedals (CC 64) across all 16 channels to kill any stuck notes.
- 📁 **MIDI File Library & Browser Upload**:
  - Automatically scans `.mid` / `.midi` files in `~/40hoursaday/midi_files`, `~/Music`, `~/Documents`.
  - Search and filter by piece name / composer.
  - Upload new MIDI files directly from your phone's browser (`+ New Piece`).
- ⚡ **Zero-Framework Backend**: Pure Python standard library HTTP server with Server-Sent Events (SSE) for 10Hz smooth timeline updates. Requires only `mido` and `python-rtmidi`.

---

### 🌐 Accessing the Web App

- **Locally on the machine:**
  👉 **[http://localhost:8090](http://localhost:8090)**
- **From your smartphone or other devices on the same local network:**
  👉 **`http://<your-device-ip-or-hostname>:8090`**

---

### 🛠 Systemd Service Management (Optional Linux Service)

To run the application continuously as a user-level `systemd` background service:

```bash
# Check service status
systemctl --user status 40hoursaday.service

# Restart service
systemctl --user restart 40hoursaday.service

# Follow live service logs
journalctl --user -u 40hoursaday.service -f
```

---

### 🚀 Running Locally & Deploying

#### 1. Run locally
```bash
python3 app.py --port 8090
```

#### 2. Deploy to a remote server / Raspberry Pi
```bash
./deploy.sh <user@host-or-ip>
```

---

### 📂 Repository Structure

- [`app.py`](app.py) – Main entrypoint & server CLI configuration
- [`player.py`](player.py) – Core MIDI playback engine (delta-timing, dynamic speed, seek, loop, transpose, count-in)
- [`library.py`](library.py) – MIDI file scanner, metadata extractor, and file upload handler
- [`server.py`](server.py) – REST API & SSE Real-time streaming server
- [`static/`](static/) – Mobile-first Single-Page Web Application ([`index.html`](static/index.html), [`style.css`](static/style.css), [`app.js`](static/app.js))
- [`screenshot.png`](screenshot.png) – Application screenshot
- [`systemd/40hoursaday.service`](systemd/40hoursaday.service) – Systemd unit file
- [`deploy.sh`](deploy.sh) – Deployment and service reload script

---

### 📄 License

Copyright (c) 2026 Mathias Menzel-Nielsen

This project is licensed under the **GNU General Public License v3.0** (GPL-3.0) — see the [`LICENSE`](LICENSE) file for details.

---

## 🇩🇪 Deutsche Kurzanleitung

### ✨ Hauptfunktionen

- **Smartphone-Bedienung**: Für den Notenständer optimiert (große Touch-Elemente, Dark Mode).
- **Zweisprachig (EN / DE)**: Sprachwechsler direkt in der Kopfzeile.
- **Tempo-Regelung (10% – 200%)**: Nahtlose Anpassung während des Spielens per Slider, Schnellwahl oder `±1%` / `±5%`.
- **Einzähler (1 Takt / 2 Takte)**: Gibt Vorzähler-Klicks im Stücktaktmaß aus, um entspannt anzusetzen.
- **Loop-Modus**: Endlosschleife zum Üben kniffliger Passagen.
- **Direkter Upload**: `.mid`-Dateien direkt im Smartphone-Browser hochladen.
- **MIDI-Port & Panic**: Schnelle Geräteauswahl und Noten-Reset bei hängenden Tönen.

### 🌐 Aufruf im Browser:
👉 **[http://localhost:8090](http://localhost:8090)** *(bzw. `http://<server-ip>:8090` im lokalen Netzwerk)*
