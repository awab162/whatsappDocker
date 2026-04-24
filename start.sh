#!/usr/bin/env bash
set -e

DISPLAY_NUM=0
VNC_PORT=${VNC_PORT:-5900}
NOVNC_PORT=${NOVNC_PORT:-6080}
FLASK_PORT=${PORT:-5000}

log() { echo "[start.sh] $*"; }

# ── 1. Virtual Display (Xvfb) ─────────────────────────────────
log "Starting Xvfb on :${DISPLAY_NUM}..."
Xvfb ":${DISPLAY_NUM}" -screen 0 1280x800x24 &
export DISPLAY=":${DISPLAY_NUM}"
sleep 2

# ── 2. ADB ────────────────────────────────────────────────────
log "Starting ADB server..."
adb start-server
sleep 1

# ── 3. Android Emulator ───────────────────────────────────────
log "Booting Android Emulator (wa_device)..."
emulator \
  -avd wa_device \
  -no-audio \
  -no-window \
  -gpu swiftshader_indirect \
  -no-snapshot \
  -wipe-data \
  &

log "Waiting for emulator to boot..."
adb wait-for-device
adb shell "while [[ -z \$(getprop sys.boot_completed) ]]; do sleep 3; done"
log "Emulator ready."

# ── 4. Appium ─────────────────────────────────────────────────
log "Starting Appium Server..."
appium --address 0.0.0.0 --port 4723 \
       --log-level error \
       &
sleep 4

# ── 5. noVNC (يبدأ لكن لا يُشارك الشاشة حتى يطلبه العميل) ──
log "Starting noVNC websocket proxy on port ${NOVNC_PORT}..."
novnc_proxy \
  --vnc localhost:${VNC_PORT} \
  --listen ${NOVNC_PORT} \
  &

# ── 6. Flask API ──────────────────────────────────────────────
log "Starting Flask API on port ${FLASK_PORT}..."
exec python3 /app/server.py
