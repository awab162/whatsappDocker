#!/usr/bin/env bash
# لا تستخدم set -e هنا لكي لا يتوقف السكربت إذا فشل أمر فرعي
# set -e 

DISPLAY_NUM=0
VNC_PORT=${VNC_PORT:-5900}
NOVNC_PORT=${NOVNC_PORT:-6080}
FLASK_PORT=${PORT:-5000}

log() { echo "[start.sh] $*"; }

# ── 1. Virtual Display ────────────────────────────────────────
log "Starting Xvfb on :${DISPLAY_NUM}..."
Xvfb ":${DISPLAY_NUM}" -screen 0 1280x800x24 &
export DISPLAY=":${DISPLAY_NUM}"
sleep 2

# ── 2. ADB Server ─────────────────────────────────────────────
log "Starting ADB server..."
adb start-server &
sleep 2

# ── 3. Android Emulator (Background) ──────────────────────────
# اخترنا وضع المحاكاة البرمجية لأنه الأضمن لـ Render
ACCEL_FLAG="-accel off"
if [ -e /dev/kvm ]; then ACCEL_FLAG="-accel on"; fi

log "Booting Emulator in background (Mode: ${ACCEL_FLAG})..."
emulator \
  -avd wa_device \
  -no-audio \
  -no-window \
  -gpu swiftshader_indirect \
  -no-snapshot \
  -no-boot-anim \
  ${ACCEL_FLAG} \
  &

# ── 4. Appium & noVNC (Background) ───────────────────────────
log "Starting Appium and noVNC..."
appium --address 0.0.0.0 --port 4723 --log-level error &
novnc_proxy --vnc localhost:${VNC_PORT} --listen ${NOVNC_PORT} &

# ── 5. Flask API (Main Process - Blocking) ───────────────────
# تشغيل الفلاسك فوراً هو أهم خطوة لكي ينجح الـ Port Scan في Render
log "Starting Flask API on port ${FLASK_PORT}..."
# ننتظر ثانية واحدة للتأكد من جاهزية الشبكة
sleep 1
exec python3 /app/server.py
