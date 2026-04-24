#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsAppClient
==============
يمكن استيراد هذا الملف في أي مشروع Python.

مثال سريع:
    from whatsapp_client import WhatsAppClient

    wa = WhatsAppClient("http://YOUR_SERVER_IP:5000")
    wa.connect()
    wa.login("+201012345678")
    otp = input("OTP: ")
    wa.verify(otp)
    ...
    wa.logout()
"""

import webbrowser
import logging
from dataclasses import dataclass, field
from typing import Optional
import requests

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# نوع الاستجابة الموحّد
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Result:
    ok: bool
    data: dict = field(default_factory=dict)
    error: str = ""

    def __bool__(self):
        return self.ok


# ──────────────────────────────────────────────────────────────────────
# العميل الرئيسي
# ──────────────────────────────────────────────────────────────────────

class WhatsAppClient:
    """
    عميل HTTP للتواصل مع WhatsApp Automation Server.

    Args:
        server_url: عنوان السيرفر مثل http://1.2.3.4:5000
        timeout:    timeout بالثواني لكل طلب
    """

    def __init__(self, server_url: str = "http://localhost:5000", timeout: int = 30):
        self.base = server_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ─── الاتصال بالسيرفر ─────────────────────────────────────────────

    def connect(self) -> Result:
        """يُنشئ جلسة Appium على السيرفر."""
        return self._post("/api/connect")

    # ─── تسجيل الدخول - الخطوة 1 ─────────────────────────────────────

    def login(self, phone: str) -> Result:
        """
        يُرسل رقم الهاتف إلى WhatsApp ويطلب OTP.
        يتوقف بعد ظهور شاشة OTP - لا يُدخله.

        Args:
            phone: رقم دولي مثل +201012345678

        Returns:
            Result.ok == True  →  اذهب للخطوة التالية (verify)
        """
        return self._post("/api/login/request", {"phone": phone})

    # ─── تسجيل الدخول - الخطوة 2 ─────────────────────────────────────

    def verify(self, otp: str) -> Result:
        """
        يُكمل تسجيل الدخول بإدخال كود OTP.

        Args:
            otp: الرمز المكوّن من 6 أرقام

        Returns:
            Result.ok == True  →  مسجّل دخول بنجاح
        """
        return self._post("/api/login/verify", {"otp": str(otp)})

    # ─── تسجيل الخروج ─────────────────────────────────────────────────

    def logout(self) -> Result:
        """
        يُسجّل الخروج ويمسح بيانات التطبيق كلياً.
        لا توجد جلسة محفوظة.
        """
        return self._post("/api/logout")

    # ─── حالة السيرفر ─────────────────────────────────────────────────

    def status(self) -> Result:
        """
        يُعيد حالة السيرفر الحالية.

        Result.data يحتوي:
            state         : disconnected | connected | awaiting_otp | logged_in
            screen_active : bool
            vnc_port      : int
            novnc_port    : int
        """
        return self._get("/api/status")

    # ─── التحكم في الشاشة ────────────────────────────────────────────

    def screen_on(self, open_browser: bool = True) -> Result:
        """
        يُشغّل مشاركة شاشة WhatsApp عبر noVNC.

        Args:
            open_browser: إذا True يفتح تلقائياً في المتصفح.

        Returns:
            Result.data["url"]  →  رابط المشاهدة في المتصفح
        """
        result = self._post("/api/screen", {"action": "on"})
        if result.ok and open_browser:
            url = result.data.get("url", "")
            if url:
                webbrowser.open(url)
                logger.info(f"Screen opened in browser: {url}")
        return result

    def screen_off(self) -> Result:
        """يُوقف مشاركة الشاشة."""
        return self._post("/api/screen", {"action": "off"})

    # ─── أدوات داخلية ─────────────────────────────────────────────────

    def _get(self, path: str) -> Result:
        try:
            r = self._session.get(f"{self.base}{path}", timeout=self.timeout)
            return self._parse(r)
        except requests.ConnectionError:
            return Result(ok=False, error="cannot connect to server")
        except requests.Timeout:
            return Result(ok=False, error="request timed out")
        except Exception as e:
            return Result(ok=False, error=str(e))

    def _post(self, path: str, body: dict = None) -> Result:
        try:
            r = self._session.post(
                f"{self.base}{path}",
                json=body or {},
                timeout=self.timeout,
            )
            return self._parse(r)
        except requests.ConnectionError:
            return Result(ok=False, error="cannot connect to server")
        except requests.Timeout:
            return Result(ok=False, error="request timed out")
        except Exception as e:
            return Result(ok=False, error=str(e))

    @staticmethod
    def _parse(response: requests.Response) -> Result:
        try:
            data = response.json()
        except Exception:
            return Result(ok=False, error=f"invalid JSON (HTTP {response.status_code})")

        ok = data.pop("ok", False)
        error = data.pop("error", "")
        return Result(ok=ok, data=data, error=error)


# ──────────────────────────────────────────────────────────────────────
# واجهة CLI بسيطة (اختياري - للتجربة السريعة)
# ──────────────────────────────────────────────────────────────────────

def _cli():
    """
    تشغيل تفاعلي مبسّط من سطر الأوامر.
    
    يمكنك استخدامه هكذا:
        python whatsapp_client.py
    """
    import sys

    server = input("Server URL [http://localhost:5000]: ").strip() or "http://localhost:5000"
    wa = WhatsAppClient(server)

    def _print(label: str, result: Result):
        status_icon = "✓" if result.ok else "✗"
        line = f"  {status_icon} {label}"
        if result.data:
            line += f" → {result.data}"
        if result.error:
            line += f" | error: {result.error}"
        print(line)

    while True:
        print("\n─────────────────────────────")
        print("  1 · اتصل بالسيرفر (connect)")
        print("  2 · سجّل دخول     (login)")
        print("  3 · أدخل OTP       (verify)")
        print("  4 · سجّل خروج     (logout)")
        print("  5 · حالة السيرفر  (status)")
        print("  6 · شاشة ON        (screen on)")
        print("  7 · شاشة OFF       (screen off)")
        print("  0 · خروج")
        print("─────────────────────────────")
        choice = input("اختر: ").strip()

        if choice == "0":
            print("Bye.")
            sys.exit(0)

        elif choice == "1":
            _print("connect", wa.connect())

        elif choice == "2":
            phone = input("  رقم الهاتف (+201012345678): ").strip()
            r = wa.login(phone)
            _print("login", r)
            if r.ok:
                print("  → ستتلقى رسالة OTP على هاتفك.")
                print("  → اختر الخيار 3 وأدخل الكود.")

        elif choice == "3":
            otp = input("  أدخل الكود (6 أرقام): ").strip()
            _print("verify", wa.verify(otp))

        elif choice == "4":
            _print("logout", wa.logout())

        elif choice == "5":
            r = wa.status()
            _print("status", r)

        elif choice == "6":
            open_b = input("  افتح في المتصفح؟ [y/n]: ").strip().lower() != "n"
            r = wa.screen_on(open_browser=open_b)
            _print("screen on", r)
            if r.ok and not open_b:
                print(f"  → URL: {r.data.get('url', '-')}")

        elif choice == "7":
            _print("screen off", wa.screen_off())

        else:
            print("  اختيار غير صحيح.")


if __name__ == "__main__":
    _cli()
