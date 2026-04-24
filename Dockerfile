FROM ubuntu:22.04

# ─── متغيرات البيئة ───────────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH="${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/emulator:${ANDROID_HOME}/platform-tools:${PATH}"
ENV LD_LIBRARY_PATH="${ANDROID_HOME}/emulator/lib64"
ENV DISPLAY=:0
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# ─── 1. تحديث النظام وتثبيت الأساسيات ──────────────────────────
# تم إضافة تحسينات لتثبيت Node.js v20 (LTS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk \
    android-tools-adb \
    python3 python3-pip \
    git curl wget unzip ca-certificates \
    xvfb x11vnc qemu-kvm libvirt-daemon-system libvirt-clients cpu-checker \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── 2. Android Command-Line Tools ──────────────────────────────
RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" \
  && wget --timeout=120 --tries=15 -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
        -O /tmp/cmdtools.zip \
  && unzip -q /tmp/cmdtools.zip -d /tmp/cmdtools \
  && mv /tmp/cmdtools/cmdline-tools "${ANDROID_HOME}/cmdline-tools/latest" \
  && rm -rf /tmp/cmdtools /tmp/cmdtools.zip

# ─── 3. SDK Components (تعديل للمعمارية ARM64) ──────────────────

# أ. الأدوات والمنصة الأساسية
RUN yes | sdkmanager --sdk_root="${ANDROID_HOME}" "platform-tools" "platforms;android-33"

# ب. محرك المحاكي (Emulator Engine)
RUN yes | sdkmanager --sdk_root="${ANDROID_HOME}" "emulator"

# ج. صورة النظام (تغيير حاسم لـ ARM64 تماشياً مع معالج Oracle)
RUN yes | sdkmanager --sdk_root="${ANDROID_HOME}" "system-images;android-33;google_apis;arm64-v8a"

# د. إنشاء الجهاز الوهمي (AVD)
RUN echo "no" | avdmanager -s create avd \
    --name "wa_device" \
    --package "system-images;android-33;google_apis;arm64-v8a" \
    --device "pixel_4a" \
    --force

# ─── 4. أدوات الويب (noVNC & Appium) ──────────────────────────
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc \
  && ln -s /opt/novnc/utils/novnc_proxy /usr/local/bin/novnc_proxy

# تثبيت Appium وإصدار مستقر من التعريف لتجنب مشاكل التوافق مع v3.0-rc
RUN npm install -g appium@latest \
  && appium driver install uiautomator2@2.34.2 \
  && npm cache clean --force

# ─── 5. ملفات التطبيق والمكتبات ────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY server.py .
COPY whatsapp_controller.py .
COPY start.sh .
RUN chmod +x start.sh

# ─── 6. الإعدادات النهائية ────────────────────────────────────────
EXPOSE 5000 5900 6080
CMD ["/app/start.sh"]
