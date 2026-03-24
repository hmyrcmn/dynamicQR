# Linux LDAP Deployment

Bu proje Linux sunucuda LDAP/AD ile calismak uzere hazirlandi. Asagidaki akis Ubuntu/Debian tabanli bir sunucu icindir.

## 1. Sistem paketleri

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential \
    libldap2-dev libsasl2-dev libssl-dev nginx
```

## 2. Proje klasoru

```bash
sudo mkdir -p /opt/dynamicqr
sudo chown $USER:$USER /opt/dynamicqr
cd /opt/dynamicqr
git clone <repo-url> .
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Environment dosyasi

`/etc/dynamicqr.env` dosyasini `.env.example` temel alarak olusturun.

```bash
sudo cp /opt/dynamicqr/.env.example /etc/dynamicqr.env
sudo nano /etc/dynamicqr.env
sudo chmod 600 /etc/dynamicqr.env
```

## 4. Django hazirligi

```bash
cd /opt/dynamicqr
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

## 5. Systemd

Ornek servis dosyasi `deploy/linux/dynamicqr.service.example` icinde.

```bash
sudo cp deploy/linux/dynamicqr.service.example /etc/systemd/system/dynamicqr.service
sudo systemctl daemon-reload
sudo systemctl enable dynamicqr
sudo systemctl start dynamicqr
sudo systemctl status dynamicqr
```

## 6. Nginx reverse proxy

Gunicorn `127.0.0.1:8000` uzerinde calisir. Nginx ile `proxy_pass http://127.0.0.1:8000;` seklinde yayinlayin.

## 7. LDAP dogrulama

`LDAP_ENABLED=True` oldugunda uygulama `django-auth-ldap` ile baglanir.

- LDAP login yapan kullanici `department` alanindan birime eslenir.
- Tum LDAP kullanicilari dashboard girisi icin `is_staff=True` olarak isaretlenir.
- `LDAP_SUPER_ADMIN_USERNAME` ile tek bir LDAP kullanicisi `SUPER_ADMIN` + `is_superuser` olur.

## 8. Notlar

- Public sunucudan kurum AD'sine ulasilacaksa LDAPS veya VPN gerekecektir.
- `AUTH_LDAP_IGNORE_CERT_ERRORS=True` yalnizca test icin kullanilmali.
- Uretimde `DJANGO_DEBUG=False` kalmalidir.
