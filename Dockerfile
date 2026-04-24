FROM ubuntu:22.04

# ─── متغيرات البيئة ───────────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH="${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/emulator:${ANDROID_HOME}/platform-tools:${PATH}"
ENV LD_LIBRARY_PATH="${ANDROID_HOME}/emulator/lib64"
ENV DISPLAY=:0
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# ─── 1. حزم النظام الأساسية ─────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-11-jdk \
    android-tools-adb \
    python3 python3-pip \
    git curl wget unzip \
    ca-certificates \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── 2. حزم العرض المرئي و KVM ──────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc \
    qemu-kvm libvirt-daemon-system libvirt-clients \
    cpu-checker \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── 3. Android Command-Line Tools ──────────────────────────────
# تم إضافة timeout و retries لضمان استقرار التحميل
RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" \
  && wget --timeout=60 --tries=10 -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
        -O /tmp/cmdtools.zip \
  && unzip -q /tmp/cmdtools.zip -d /tmp/cmdtools \
  && mv /tmp/cmdtools/cmdline-tools "${ANDROID_HOME}/cmdline-tools/latest" \
  && rm -rf /tmp/cmdtools /tmp/cmdtools.zip

# ─── 4. SDK Components (مقسمة لدعم الكاش) ───────────────────────

# أ. الأدوات الأساسية والمنصة
RUN yes | sdkmanager --sdk_root="${ANDROID_HOME}" "platform-tools" "platforms;android-33"

# ب. محرك المحاكي (Emulator Engine)
RUN yes | sdkmanager --sdk_root="${ANDROID_HOME}" "emulator"

# ج. صورة النظام (الأكبر حجماً - مفصولة تماماً)
RUN yes | sdkmanager --sdk_root="${ANDROID_HOME}" "system-images;android-33;google_apis;x86_64"

# د. إنشاء الجهاز الوهمي (AVD)
RUN echo "no" | avdmanager -s create avd \
    --name "wa_device" \
    --package "system-images;android-33;google_apis;x86_64" \
    --device "pixel_4a" \
    --force

# ─── 5. أدوات الويب (noVNC & Appium) ──────────────────────────

RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc \
  && ln -s /opt/novnc/utils/novnc_proxy /usr/local/bin/novnc_proxy

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
  && npm install -g appium@2 \
  && appium driver install uiautomator2 \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── 6. ملفات التطبيق والمكتبات ────────────────────────────────

WORKDIR /app
# ملاحظة: تأكد من وجود ملف باسم requirements.txt في المجلد
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY server.py .
COPY whatsapp_controller.py .
COPY start.sh .
RUN chmod +x start.sh

# ─── الإعدادات النهائية ────────────────────────────────────────

EXPOSE 5000 5900 6080
CMD ["/app/start.sh"]
