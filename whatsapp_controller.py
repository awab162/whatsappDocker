#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

CAPS = {
    "platformName": "Android",
    "platformVersion": "13",
    "deviceName": "whatsapp_device",
    "appPackage": "com.whatsapp",
    "appActivity": "com.whatsapp.HomeActivity",
    "automationName": "UiAutomator2",
    "noReset": False,        # لا نحتفظ بأي بيانات جلسة
    "fullReset": False,
    "autoGrantPermissions": True,
    "newCommandTimeout": 120,
}


class WhatsAppController:
    """
    يتحكم في WhatsApp داخل Android Emulator عبر Appium.
    لا يحفظ أي جلسة - كل تشغيل يبدأ من الصفر.
    """

    def __init__(self, appium_url: str = "http://localhost:4723/wd/hub"):
        self.appium_url = appium_url
        self.driver = None
        self._state = "disconnected"   # disconnected | connected | awaiting_otp | logged_in

    # ─────────────────────────────────────────────────────
    # الاتصال والانفصال
    # ─────────────────────────────────────────────────────

    def connect(self) -> bool:
        try:
            logger.info("Connecting to Appium...")
            self.driver = webdriver.Remote(self.appium_url, CAPS)
            self._state = "connected"
            logger.info("Appium connected.")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Appium connection failed: {e}")
            return False

    def disconnect(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.driver = None
        self._state = "disconnected"

    # ─────────────────────────────────────────────────────
    # تسجيل الدخول (خطوة 1) - إدخال رقم الهاتف فقط
    # ─────────────────────────────────────────────────────

    def request_otp(self, phone: str) -> dict:
        """
        يفتح WhatsApp ويدخل رقم الهاتف ثم يضغط Next.
        يتوقف عند ظهور شاشة OTP ويُعيد للعميل طلب الإدخال.

        Args:
            phone: رقم دولي مثل +201012345678

        Returns:
            {"ok": True}  أو  {"ok": False, "error": "..."}
        """
        if not self.driver:
            return {"ok": False, "error": "not connected"}

        try:
            self._restart_app()
            time.sleep(3)

            # ── شاشة الاتفاقية (إن ظهرت) ──
            self._dismiss_agree_screen()

            # ── النقر على "موافق وإكمال" أو زر البدء ──
            self._click_if_exists("com.whatsapp:id/submit", timeout=5)

            # ── إدخال رقم الهاتف ──
            phone_field = self._wait_element(
                AppiumBy.ID, "com.whatsapp:id/registration_phone", timeout=10
            )
            phone_field.clear()
            phone_field.send_keys(phone)
            logger.info(f"Phone entered: {phone}")

            # ── ضغط Next ──
            next_btn = self._wait_element(
                AppiumBy.ID, "com.whatsapp:id/registration_submit", timeout=5
            )
            next_btn.click()
            time.sleep(2)

            # ── تأكيد رسالة "هل رقمك صحيح؟" ──
            self._click_if_exists(
                "com.whatsapp:id/ok_btn", timeout=5
            )
            time.sleep(3)

            # ── التحقق أن شاشة OTP ظهرت ──
            otp_screen = self._element_exists(
                AppiumBy.ID, "com.whatsapp:id/verify_sms_code_input", timeout=12
            )
            if not otp_screen:
                return {"ok": False, "error": "OTP screen did not appear"}

            self._state = "awaiting_otp"
            logger.info("OTP screen reached - waiting for user input.")
            return {"ok": True}

        except Exception as e:
            logger.exception("request_otp failed")
            return {"ok": False, "error": str(e)}

    # ─────────────────────────────────────────────────────
    # تسجيل الدخول (خطوة 2) - إدخال OTP
    # ─────────────────────────────────────────────────────

    def submit_otp(self, otp: str) -> dict:
        """
        يُدخل كود OTP في شاشة التحقق.

        Args:
            otp: الرمز المكوّن من 6 أرقام

        Returns:
            {"ok": True}  أو  {"ok": False, "error": "..."}
        """
        if self._state != "awaiting_otp":
            return {"ok": False, "error": "not in awaiting_otp state"}

        try:
            otp_field = self._wait_element(
                AppiumBy.ID, "com.whatsapp:id/verify_sms_code_input", timeout=10
            )
            otp_field.send_keys(otp)
            logger.info(f"OTP submitted: {otp}")
            time.sleep(2)

            # ── انتظر صفحة الرئيسية ──
            logged_in = self._element_exists(
                AppiumBy.ID, "com.whatsapp:id/conversations_row_contact_name",
                timeout=20
            )
            if logged_in:
                self._state = "logged_in"
                logger.info("Login successful.")
                return {"ok": True}

            return {"ok": False, "error": "Login did not complete"}

        except Exception as e:
            logger.exception("submit_otp failed")
            return {"ok": False, "error": str(e)}

    # ─────────────────────────────────────────────────────
    # تسجيل الخروج
    # ─────────────────────────────────────────────────────

    def logout(self) -> dict:
        """
        يُسجّل الخروج من WhatsApp ويمسح البيانات.
        """
        try:
            # مسح بيانات التطبيق عبر ADB (أسرع وأنظف من الواجهة)
            import subprocess
            subprocess.run(
                ["adb", "shell", "pm", "clear", "com.whatsapp"],
                capture_output=True, timeout=10
            )
            self._state = "connected"
            logger.info("Logged out (app data cleared).")
            return {"ok": True}
        except Exception as e:
            logger.exception("logout failed")
            return {"ok": False, "error": str(e)}

    # ─────────────────────────────────────────────────────
    # الحالة
    # ─────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    # ─────────────────────────────────────────────────────
    # أدوات داخلية
    # ─────────────────────────────────────────────────────

    def _restart_app(self):
        self.driver.terminate_app("com.whatsapp")
        time.sleep(1)
        self.driver.activate_app("com.whatsapp")

    def _dismiss_agree_screen(self):
        try:
            agree = self.driver.find_element(
                AppiumBy.ID, "com.whatsapp:id/agree_btn"
            )
            agree.click()
            time.sleep(1)
        except NoSuchElementException:
            pass

    def _wait_element(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def _element_exists(self, by, value, timeout=10) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def _click_if_exists(self, resource_id: str, timeout=3):
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((AppiumBy.ID, resource_id))
            )
            el.click()
        except TimeoutException:
            pass
