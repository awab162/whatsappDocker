# 🚀 النشر المجاني على Oracle Cloud

## لماذا Oracle Cloud؟

| الخاصية | Oracle Cloud Free | Railway | Render | Fly.io |
|---------|------------------|---------|--------|--------|
| RAM مجاني | **24 GB** | 512 MB | 512 MB | 256 MB |
| CPU | 4 Cores ARM | 0.5 vCPU | 0.1 vCPU | مشترك |
| Docker | ✅ | ✅ | ✅ | ✅ |
| KVM (emulator) | ✅ | ❌ | ❌ | ❌ |
| مجاني للأبد | ✅ | ❌ مدة | ❌ مدة | ❌ مدة |

> الـ Android Emulator يحتاج KVM وRAM كبيرة - Oracle هو الوحيد يوفرها مجاناً.

---

## خطوات الإعداد

### 1. إنشاء الحساب

اذهب إلى: https://www.oracle.com/cloud/free  
أنشئ حساباً وأدخل بطاقة ائتمان (لن تُشحن).

---

### 2. إنشاء VM (Compute Instance)

```
الإعدادات المطلوبة:
  Shape:  VM.Standard.A1.Flex (ARM)
  OCPU:   4
  RAM:    24 GB
  OS:     Ubuntu 22.04
  Storage: 50 GB Boot Volume
```

**في المنفذ المفتوح (Security List) أضف:**
- TCP 5000  (Flask API)
- TCP 6080  (noVNC Web)
- TCP 5900  (VNC raw - اختياري)

---

### 3. الاتصال بالـ VM

```bash
ssh ubuntu@<YOUR_VM_IP> -i ~/.ssh/oci_key
```

---

### 4. تثبيت Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
newgrp docker
```

---

### 5. تفعيل KVM

```bash
# تحقق من دعم KVM
sudo apt install -y cpu-checker
kvm-ok

# ستظهر: "KVM acceleration can be used"
```

---

### 6. نشر السيرفر

```bash
# نسخ ملفات السيرفر إلى الـ VM
scp -i ~/.ssh/oci_key -r ./server ubuntu@<YOUR_VM_IP>:~/wa-server

# الدخول والتشغيل
ssh ubuntu@<YOUR_VM_IP>
cd ~/wa-server

# تعديل SERVER_HOST في docker-compose.yml
sed -i 's/SERVER_HOST: "localhost"/SERVER_HOST: "<YOUR_VM_IP>"/' docker-compose.yml

# بناء وتشغيل
docker compose build
docker compose up -d

# مراقبة السجلات
docker compose logs -f
```

---

### 7. فتح جدار الحماية على الـ VM

```bash
sudo iptables -I INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 6080 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 5900 -j ACCEPT
sudo netfilter-persistent save
```

---

### 8. تعديل العميل على الـ Laptop

```python
# في whatsapp_client.py أو مشروعك:
wa = WhatsAppClient("http://<YOUR_VM_IP>:5000")
```

---

## التحقق من النشر

```bash
# من أي مكان:
curl http://<YOUR_VM_IP>:5000/api/status

# الاستجابة المتوقعة:
# {"ok": true, "state": "disconnected", "screen_active": false, ...}
```

---

## مشاهدة الشاشة (noVNC)

افتح في المتصفح:
```
http://<YOUR_VM_IP>:6080/vnc.html
```

أو استخدم العميل:
```python
wa.screen_on()   # يفتح تلقائياً في المتصفح
```

---

## إيقاف السيرفر وتشغيله

```bash
# إيقاف
docker compose down

# تشغيل
docker compose up -d

# إعادة تشغيل
docker compose restart
```

---

## ملاحظات مهمة

- **الـ Emulator يأخذ 3-5 دقائق للتشغيل** عند بدء الحاوية
- **لا تُوقف الـ VM** أو ستُعاد جلسة Appium من الصفر
- **Oracle تحذف الـ VM** إذا كان idle لأكثر من 7 أيام → شغّل cron ping بسيط

```bash
# Cron ping كل 6 ساعات لمنع الإيقاف
echo "0 */6 * * * curl -sf http://localhost:5000/api/status" | crontab -
```
