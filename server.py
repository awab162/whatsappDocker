#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
from flask import Flask, request, jsonify
from whatsapp_controller import WhatsAppController

# ─────────────────────────────────────────────────────────────────
# الإعداد
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("server")

app = Flask(__name__)
wa = WhatsAppController(
    appium_url=os.getenv("APPIUM_URL", "http://localhost:4723/wd/hub")
)

# حالة VNC
_vnc_process = None

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def ok(data: dict = None, **kwargs):
    payload = {"ok": True}
    if data:
        payload.update(data)
    payload.update(kwargs)
    return jsonify(payload), 200


def err(message: str, code: int = 400):
    return jsonify({"ok": False, "error": message}), code


# ─────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    """حالة السيرفر والاتصال بـ WhatsApp"""
    global _vnc_process
    return ok(
        state=wa.state,
        screen_active=_vnc_process is not None and _vnc_process.poll() is None,
        vnc_port=int(os.getenv("VNC_PORT", 5900)),
        novnc_port=int(os.getenv("NOVNC_PORT", 6080)),
    )


@app.post("/api/connect")
def connect():
    """الاتصال بـ Appium وبدء جلسة جديدة"""
    if wa.state != "disconnected":
        return err("already connected")
    if not wa.connect():
        return err("failed to connect to Appium", 500)
    return ok(state=wa.state)


@app.post("/api/login/request")
def login_request():
    """
    الخطوة 1 من تسجيل الدخول.
    يُدخل رقم الهاتف ويضغط Next.
    يتوقف عند ظهور شاشة OTP وينتظر.

    Body JSON:
        { "phone": "+201012345678" }

    Returns:
        { "ok": true }  →  بانتظار OTP من العميل
    """
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "").strip()

    if not phone:
        return err("phone is required")
    if not phone.startswith("+"):
        return err("phone must be in international format e.g. +201012345678")
    if wa.state == "disconnected":
        return err("not connected - call /api/connect first")

    result = wa.request_otp(phone)
    if not result["ok"]:
        return err(result["error"], 500)

    return ok(message="OTP sent to your phone. Submit it via /api/login/verify")


@app.post("/api/login/verify")
def login_verify():
    """
    الخطوة 2 من تسجيل الدخول.
    يُدخل كود OTP الذي استلمه المستخدم.

    Body JSON:
        { "otp": "123456" }

    Returns:
        { "ok": true, "state": "logged_in" }
    """
    data = request.get_json(silent=True) or {}
    otp = str(data.get("otp", "")).strip()

    if not otp or len(otp) != 6 or not otp.isdigit():
        return err("otp must be exactly 6 digits")
    if wa.state != "awaiting_otp":
        return err("not in awaiting_otp state")

    result = wa.submit_otp(otp)
    if not result["ok"]:
        return err(result["error"], 500)

    return ok(state=wa.state)


@app.post("/api/logout")
def logout():
    """
    تسجيل الخروج وحذف بيانات التطبيق كلياً.
    لا توجد جلسة محفوظة - يبدأ من الصفر في المرة القادمة.
    """
    result = wa.logout()
    if not result["ok"]:
        return err(result["error"], 500)
    return ok(state=wa.state)


@app.post("/api/screen")
def screen_control():
    """
    تشغيل أو إيقاف عرض شاشة WhatsApp عبر noVNC.

    Body JSON:
        { "action": "on" }   ← تشغيل
        { "action": "off" }  ← إيقاف

    عند التشغيل:
        الشاشة تظهر على المتصفح عبر: http://<server>:6080

    Returns:
        { "ok": true, "screen_active": true, "url": "http://..." }
    """
    global _vnc_process

    data = request.get_json(silent=True) or {}
    action = data.get("action", "").lower()

    if action not in ("on", "off"):
        return err("action must be 'on' or 'off'")

    if action == "on":
        if _vnc_process and _vnc_process.poll() is None:
            return ok(screen_active=True, message="screen already active")

        try:
            # تشغيل x11vnc على العرض الافتراضي للـ emulator
            _vnc_process = subprocess.Popen(
                [
                    "x11vnc",
                    "-display", os.getenv("DISPLAY", ":0"),
                    "-nopw",
                    "-listen", "localhost",
                    "-xkb",
                    "-forever",
                    "-shared",
                    "-rfbport", os.getenv("VNC_PORT", "5900"),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            novnc_port = os.getenv("NOVNC_PORT", "6080")
            host = os.getenv("SERVER_HOST", "localhost")
            url = f"http://{host}:{novnc_port}/vnc.html"
            logger.info(f"Screen sharing started → {url}")
            return ok(screen_active=True, url=url)

        except FileNotFoundError:
            return err("x11vnc not installed in container", 500)
        except Exception as e:
            return err(str(e), 500)

    else:  # off
        if _vnc_process and _vnc_process.poll() is None:
            _vnc_process.terminate()
            _vnc_process = None
            logger.info("Screen sharing stopped.")
        return ok(screen_active=False)


# ─────────────────────────────────────────────────────────────────
# تشغيل السيرفر
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting WhatsApp Automation Server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
