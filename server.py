#!/usr/bin/env python3
"""
HTTP & SSE Server for 40hoursaday Practice Partner.
Copyright (c) 2026 Mathias Menzel-Nielsen
Licensed under the GNU General Public License v3.0 (GPL-3.0)

Pure Python standard library implementation with zero external web framework dependencies.
Supports REST API, Server-Sent Events (SSE) for 10Hz live progress, file uploads,
and static web UI hosting.
"""

import json
import mimetypes
import os
import sys
import time
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional

from player import MidiPlayer
from library import MidiLibrary
from mixer import PulseMixer

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class PracticePartnerHandler(SimpleHTTPRequestHandler):
    player: MidiPlayer = None
    library: MidiLibrary = None
    static_dir: str = os.path.join(os.path.dirname(__file__), "static")

    def log_message(self, format, *args):
        try:
            msg = format % args
            if "/api/events" in msg or "/api/status" in msg:
                return
            sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    def _send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status_code: int = 400):
        self._send_json({"error": message, "success": False}, status_code=status_code)

    def _parse_json_body(self) -> Optional[dict]:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            if not raw.strip():
                return {}
            return json.loads(raw)
        except Exception as e:
            return {}

    def do_OPTIONS(self):
        # CORS preflight
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/status":
            self._send_json(self.player.get_status())
            return

        if path == "/api/files":
            files = self.library.scan_files()
            self._send_json({"files": files, "count": len(files)})
            return

        if path == "/api/ports":
            ports = self.player.get_available_ports()
            self._send_json({"ports": ports, "current": self.player.target_port_name})
            return

        if path == "/api/mixer":
            self._send_json(PulseMixer.get_status())
            return

        if path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            try:
                while True:
                    status = self.player.get_status(include_beat_map=False)
                    msg = f"data: {json.dumps(status)}\n\n".encode("utf-8")
                    self.wfile.write(msg)
                    self.wfile.flush()
                    time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        # Serve static web UI files
        if path == "/" or path == "":
            path = "/index.html"

        safe_path = os.path.normpath(path.lstrip("/"))
        file_path = os.path.join(self.static_dir, safe_path)

        if os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"

            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type else mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_error(str(e), status_code=500)
        else:
            self.send_error(404, f"File {path} not found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/play":
            body = self._parse_json_body() or {}
            filepath = body.get("file")
            speed = body.get("speed")
            volume = body.get("volume")
            port = body.get("port")
            clean_port = str(port).strip() if port and str(port).strip() else None
            loop = body.get("loop")
            count_in = body.get("count_in")
            transpose = body.get("transpose")

            ok = self.player.play(
                filepath=filepath,
                speed=speed,
                volume=volume,
                port=clean_port,
                loop=loop,
                count_in=count_in,
                transpose=transpose
            )
            if ok:
                self._send_json({"success": True, "status": self.player.get_status()})
            else:
                self._send_error("Failed to start playback. Check file path or MIDI port.")
            return

        if path == "/api/pause":
            self.player.pause()
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/resume":
            self.player.resume()
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/stop":
            self.player.stop()
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/speed":
            body = self._parse_json_body() or {}
            speed = body.get("speed")
            if speed is None:
                self._send_error("Missing 'speed' parameter")
                return
            self.player.set_speed(float(speed))
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/volume":
            body = self._parse_json_body() or {}
            volume = body.get("volume")
            if volume is None:
                self._send_error("Missing 'volume' parameter")
                return
            self.player.set_volume(float(volume))
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/seek":
            body = self._parse_json_body() or {}
            position = body.get("position")
            if position is None:
                self._send_error("Missing 'position' parameter")
                return
            self.player.seek(float(position))
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/port":
            body = self._parse_json_body() or {}
            port = body.get("port")
            if not port:
                self._send_error("Missing 'port' parameter")
                return
            ok = self.player.set_port(port)
            self._send_json({"success": ok, "port": self.player.target_port_name, "status": self.player.get_status()})
            return

        if path == "/api/port/program_change":
            body = self._parse_json_body() or {}
            port = body.get("port") or self.player.target_port_name
            allow = body.get("allow")
            if port and allow is not None:
                ok = self.player.set_port_program_change(str(port), bool(allow))
                self._send_json({"success": ok, "status": self.player.get_status()})
            else:
                self._send_error("Missing 'allow' parameter")
            return

        if path == "/api/loop":
            body = self._parse_json_body() or {}
            loop = body.get("loop", False)
            self.player.set_loop(bool(loop))
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/transpose":
            body = self._parse_json_body() or {}
            transpose = body.get("transpose", 0)
            self.player.set_transpose(int(transpose))
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/count_in":
            body = self._parse_json_body() or {}
            bars = body.get("count_in_bars", 0)
            self.player.set_count_in(int(bars))
            self._send_json({"success": True, "status": self.player.get_status()})
            return

        if path == "/api/channel/volume" or path == "/api/channel_volume":
            body = self._parse_json_body() or {}
            channel = body.get("channel")
            volume = body.get("volume")
            if channel is not None and volume is not None:
                ok = self.player.set_channel_volume(int(channel), float(volume))
                self._send_json({"success": ok, "status": self.player.get_status()})
            else:
                self._send_error("Missing 'channel' or 'volume' parameter")
            return

        if path == "/api/meter":
            body = self._parse_json_body() or {}
            num = body.get("numerator")
            den = body.get("denominator")
            mult = body.get("multiplier")
            ok = self.player.set_meter(
                numerator=int(num) if num is not None else None,
                denominator=int(den) if den is not None else None,
                multiplier=float(mult) if mult is not None else None
            )
            self._send_json({"success": ok, "status": self.player.get_status()})
            return

        if path == "/api/channel/reset_volumes" or path == "/api/channel_reset_volumes":
            ok = self.player.reset_channel_volumes()
            self._send_json({"success": ok, "status": self.player.get_status()})
            return

        if path == "/api/channel/mute" or path == "/api/channel_mute":
            body = self._parse_json_body() or {}
            channel = body.get("channel")
            mute = body.get("mute")
            if channel is not None and mute is not None:
                ok = self.player.set_channel_mute(int(channel), bool(mute))
                self._send_json({"success": ok, "status": self.player.get_status()})
            else:
                self._send_error("Missing 'channel' or 'mute' parameter")
            return

        if path == "/api/channel/unmute_all" or path == "/api/channel_unmute_all":
            ok = self.player.unmute_all_channels()
            self._send_json({"success": ok, "status": self.player.get_status()})
            return

        if path == "/api/panic":
            self.player.panic()
            self._send_json({"success": True, "message": "Panic / All notes reset sent"})
            return

        if path == "/api/mixer/sink/volume":
            body = self._parse_json_body() or {}
            sink_id = body.get("id")
            vol = body.get("volume")
            if sink_id is not None and vol is not None:
                ok = PulseMixer.set_sink_volume(int(sink_id), int(vol))
                self._send_json({"success": ok, "status": PulseMixer.get_status()})
            else:
                self._send_error("Missing 'id' or 'volume' parameter")
            return

        if path == "/api/mixer/sink/mute":
            body = self._parse_json_body() or {}
            sink_id = body.get("id")
            mute = body.get("mute")
            if sink_id is not None and mute is not None:
                ok = PulseMixer.set_sink_mute(int(sink_id), bool(mute))
                self._send_json({"success": ok, "status": PulseMixer.get_status()})
            else:
                self._send_error("Missing 'id' or 'mute' parameter")
            return

        if path == "/api/mixer/stream/volume":
            body = self._parse_json_body() or {}
            stream_id = body.get("id")
            vol = body.get("volume")
            if stream_id is not None and vol is not None:
                ok = PulseMixer.set_stream_volume(int(stream_id), int(vol))
                self._send_json({"success": ok, "status": PulseMixer.get_status()})
            else:
                self._send_error("Missing 'id' or 'volume' parameter")
            return

        if path == "/api/mixer/stream/mute":
            body = self._parse_json_body() or {}
            stream_id = body.get("id")
            mute = body.get("mute")
            if stream_id is not None and mute is not None:
                ok = PulseMixer.set_stream_mute(int(stream_id), bool(mute))
                self._send_json({"success": ok, "status": PulseMixer.get_status()})
            else:
                self._send_error("Missing 'id' or 'mute' parameter")
            return

        if path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            length = int(self.headers.get("Content-Length", 0))

            if "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[-1].strip().encode('utf-8')
                raw_data = self.rfile.read(length)
                
                parts = raw_data.split(b"--" + boundary)
                uploaded_meta = None
                for part in parts:
                    if b'filename="' in part:
                        headers_part, file_body = part.split(b"\r\n\r\n", 1)
                        file_body = file_body.rstrip(b"\r\n")
                        header_lines = headers_part.decode("utf-8", errors="ignore").split("\r\n")
                        filename = "uploaded.mid"
                        for h in header_lines:
                            if 'filename="' in h:
                                filename = h.split('filename="')[1].split('"')[0]
                        uploaded_meta = self.library.save_uploaded_file(filename, file_body)
                        break

                if uploaded_meta:
                    self._send_json({"success": True, "file": uploaded_meta})
                else:
                    self._send_error("Failed to parse multipart file upload")
                return

            elif "application/json" in content_type:
                import base64
                body = self._parse_json_body() or {}
                filename = body.get("filename", "piece.mid")
                b64content = body.get("content", "")
                try:
                    file_bytes = base64.b64decode(b64content)
                    meta = self.library.save_uploaded_file(filename, file_bytes)
                    if meta:
                        self._send_json({"success": True, "file": meta})
                    else:
                        self._send_error("Failed to save MIDI file")
                except Exception as e:
                    self._send_error(f"Upload error: {e}")
                return
            else:
                self._send_error("Unsupported content type for upload")
                return

        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/files":
            body = self._parse_json_body() or {}
            filepath = body.get("filepath")
            if not filepath:
                self._send_error("Missing 'filepath' parameter")
                return
            ok = self.library.delete_file(filepath)
            if ok:
                self._send_json({"success": True, "message": "File deleted"})
            else:
                self._send_error("Could not delete file")
            return

        self.send_error(404, "Endpoint not found")
