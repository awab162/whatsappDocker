FROM ubuntu:22.04

# ─── متغيرات البيئة ───────────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH="${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/emulator:${ANDROID_HOME}/platform-tools:${PATH}"
ENV LD_LIBRARY_PATH="${ANDROID_HOME}/emulator/lib64"
ENV DISPLAY=:0
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# ─── حزم النظام ───────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Java
    openjdk-11-jdk \
    # ADB & tools
    android-tools-adb \
    # Python
    python3 python3-pip \
    # Virtual display + VNC
    xvfb x11vnc \
    # noVNC deps
    git curl wget unzip \
    # KVM / hardware acceleration
    qemu-kvm libvirt-daemon-system libvirt-clients \
    cpu-checker \
    # misc
    ca-certificates \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── Android Command-Line Tools ───────────────────────────────
RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" \
  && wget -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
       -O /tmp/cmdtools.zip \
  && unzip -q /tmp/cmdtools.zip -d /tmp/cmdtools \
  && mv /tmp/cmdtools/cmdline-tools "${ANDROID_HOME}/cmdline-tools/latest" \
  && rm -rf /tmp/cmdtools /tmp/cmdtools.zip

# ─── SDK: Platform + Emulator image ──────────────────────────
RUN yes | sdkmanager --sdk_root="${ANDROID_HOME}" \
      "platform-tools" \
      "emulator" \
      "platforms;android-33" \
      "system-images;android-33;google_apis;x86_64" \
  && echo "no" | avdmanager -s create avd \
       --name "wa_device" \
       --package "system-images;android-33;google_apis;x86_64" \
       --device "pixel_4a" \
       --force

# ─── noVNC (web-based VNC viewer) ─────────────────────────────
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc \
  && ln -s /opt/novnc/utils/novnc_proxy /usr/local/bin/novnc_proxy

# ─── Appium ───────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
  && npm install -g appium@2 \
  && appium driver install uiautomator2 \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── Python dependencies ──────────────────────────────────────
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# ─── Application files ────────────────────────────────────────
WORKDIR /app
COPY server.py .
COPY whatsapp_controller.py .
COPY start.sh .
RUN chmod +x start.sh

# ─── Exposed ports ────────────────────────────────────────────
# 5000 → Flask API
# 5900 → VNC (raw)
# 6080 → noVNC (web browser)
EXPOSE 5000 5900 6080

CMD ["/app/start.sh"]
