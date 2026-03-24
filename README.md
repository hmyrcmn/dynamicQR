# DynamicQR

DynamicQR, kurum icindeki dinamik QR kodlarini LDAP destekli kullanici girisi, departman bazli yetkilendirme, yonlendirme analitigi ve kurumsal yonetim paneli ile yonetmek icin gelistirilmis bir Django uygulamasidir.

Bu README iki amac icin yazildi:

1. Bu projeyi ilk kez gorecek birisinin sistemi bastan kurup calistirabilmesi
2. Linux sunucuda LDAP/Active Directory baglantisini gercek ortama yakin sekilde devreye alabilmesi

Bu belge kod tabaninin mevcut halini referans alir. Dokumandaki akislari izleyen biri, ayni projeyi ya da benzerini bastan kurabilecek seviyede teknik cerceveye sahip olur.

## 1. Projenin Amaci

Kurum icindeki birimler kendi QR kodlarini olusturur, duzenler, siler ve indirir. Her QR koda bir kisa ID atanir. Kullanici QR kodu okuttugunda sistem:

1. Kisa ID ile kaydi bulur
2. Hedef URL'yi alir
3. Taramayi analitik tablosuna kaydeder
4. Kullaniciya hedef URL'ye 302 yonlendirme yapar

Yonetim tarafi icin temel kural:

- LDAP ile giris yapan normal kullanici sadece kendi biriminin QR kayitlarini gorur ve yonetir
- Tek bir Super Admin tum birimleri gorebilir ve yonetebilir

## 2. Temel Ozellikler

- Dinamik QR olusturma, guncelleme, silme
- PNG formatinda QR indirme
- Kisa URL ile yonlendirme
- Tarama analitigi kaydi
- IP bilgisini hashleyerek KVKK/GDPR uyumlu saklama
- Departman bazli RBAC
- LDAP / Active Directory ile giris
- LDAP'den `department` alanini cekip kullaniciyi yerel birime esleme
- Tek bir global Super Admin kurali
- Kurumsal dashboard ve landing arayuzu

## 3. Kullanilan Teknolojiler

- Python
- Django
- django-auth-ldap
- python-ldap
- django-simple-history
- qrcode
- Pillow
- WhiteNoise
- Gunicorn
- Tailwind CSS

## 4. Sistem Mimarisi

Sistem 4 ana parca etrafinda kurulu:

1. Kimlik dogrulama
   LDAP aktifse kullanici AD uzerinden dogrulanir.
2. Yetkilendirme
   Kullanici sadece kendi `department` kayitlarini gorur.
3. QR yonetimi
   Dashboard uzerinden QR olusturma, guncelleme, silme ve indirme yapilir.
4. Redirect + analytics
   `/<short_id>/` endpoint'i hem yonlendirme hem de tarama kaydi yapar.

Basit akis:

```text
Kullanici -> /admin/login/ -> LDAP veya Django Auth
LDAP -> kullanici bilgisi + department
Sinyal -> Department modeline map et
Basarili giris -> /dashboard/
Dashboard -> kullanicinin yetkili oldugu QR kayitlari
QR tarama -> /<short_id>/ -> analytics kaydi -> hedef URL
```

## 5. Dizin Yapisi

```text
qr_project/
  settings.py          Django ayarlari, LDAP config, env okuma
  urls.py              Kök URL dagitimi
  wsgi.py              Gunicorn/WSGI giris noktasi

core/
  models.py            Department, CustomUser, QRCode, ScanAnalytics
  views.py             Landing, dashboard, QR CRUD, redirect, QR indirme
  forms.py             Whitelist kontrollu formlar
  admin.py             Django admin RBAC
  signals.py           LDAP login sonrasi department ve rol mapleme
  urls.py              Dashboard ve kısa ID URL'leri
  utils.py             short_id olusturma yardimcilari

templates/
  landing.html         Acilis ekrani
  dashboard.html       Yonetim paneli
  qr_create.html       QR olusturma formu
  qr_edit.html         QR guncelleme formu
  qr_confirm_delete.html
  admin/login.html     Ozellestirilmis giris ekrani

static/
  css/
  img/

deploy/linux/
  README.md                       Linux deploy notlari
  dynamicqr.service.example       systemd servis ornegi

.env.example            Ortam degiskenleri ornegi
requirements.txt        Python bagimliliklari
```

## 6. Veri Modeli

### 6.1 Department

Bir kurum birimini temsil eder.

Alanlar:

- `name`
- `is_active`

### 6.2 CustomUser

`AbstractUser`'dan turetilmistir.

Ek alanlar:

- `department`
- `role`

Roller:

- `SUPER_ADMIN`
- `DEPT_MANAGER`
- `DEPT_USER`

Not:

- Model seviyesinde sadece bir adet tam yetkili kullaniciya izin verilir.
- `is_superuser=True` veya `role='SUPER_ADMIN'` olan ikinci bir kayit kaydedilemez.

### 6.3 QRCode

Dinamik QR kaydidir.

Alanlar:

- `short_id`
- `department`
- `created_by`
- `title`
- `destination_url`
- `is_active`
- `created_at`
- `updated_at`
- `history`

### 6.4 ScanAnalytics

Her tarama icin bir kayit olusur.

Alanlar:

- `qr_code`
- `timestamp`
- `ip_address_hash`
- `user_agent`
- `country`
- `city`
- `device_type`

Not:

- Ham IP saklanmaz
- `hash_ip()` ile salt'li SHA-256 hash saklanir

## 7. Yetkilendirme Mantigi

Bu proje departman bazli izolasyon mantigi ile calisir.

### 7.1 Normal LDAP kullanicisi

- Sadece kendi biriminin QR kayitlarini gorur
- Sadece kendi biriminin QR kayitlarini duzenler
- Sadece kendi biriminin QR kayitlarini siler
- Sadece kendi biriminin QR kayitlarinin PNG'sini indirir
- QR olusturunca kayit otomatik kendi birimine yazilir

### 7.2 Super Admin

- Tum birimleri gorur
- Tum QR kayitlarini duzenler
- Tum analitikleri gorur
- Django admin icinde kullanici ve departman yonetimi yapabilir

### 7.3 Kritik not

Tek bir global admin kullanin:

- Ya 1 adet yerel Django superuser kullanin
- Ya da `LDAP_SUPER_ADMIN_USERNAME` ile 1 adet LDAP kullanicisini Super Admin yapin

Ikisini ayni anda tanimlamak dogru degildir. Model seviyesindeki tek-global-admin kurali buna engel olmak icin vardir.

## 8. URL Haritasi

### Genel

- `/` -> landing
- `/logout/` -> cikis
- `/<short_id>/` -> redirect motoru

### Dashboard

- `/dashboard/`
- `/dashboard/create/`
- `/dashboard/edit/<short_id>/`
- `/dashboard/delete/<short_id>/`
- `/download-qr/<short_id>/`

### Giris

- `/admin/login/` -> giris ekrani
- `/admin/logout/` -> cikis
- `/admin/` -> dashboard'a yonlenir

## 9. Uygulama Akislari

## 9.1 Giris Akisi

1. Kullanici `/admin/login/` ekranina gelir
2. `AUTHENTICATION_BACKENDS` sirasina gore dogrulama yapilir
3. LDAP aktifse `django_auth_ldap.backend.LDAPBackend` devreye girer
4. Kullanici basarili ise yerel `CustomUser` kaydi guncellenir veya olusturulur
5. `populate_user` sinyali ile LDAP `department` alani okunur
6. Yerel `Department` kaydi olusturulur veya bulunur
7. Kullanici `department` alanina atanir
8. Basarili giris sonrasi `/dashboard/` acilir

## 9.2 Dashboard Akisi

1. `get_accessible_qr_codes(user)` kullanilir
2. Kullanici Super Admin ise tum kayitlar gelir
3. Normal kullanici ise sadece `department_id=user.department_id` kayitlari gelir
4. Dashboard ust kartlari iki bagimsiz toggle filtre gibi calisir:
   - aktif kayitlar
   - en az bir kez tarananlar
5. Liste buna gore olusur

## 9.3 QR Olusturma Akisi

1. Kullanici `/dashboard/create/` ekranina girer
2. Form `title` ve `destination_url` alir
3. URL whitelist kontrolunden gecer
4. Kayit `request.user.department` ile otomatik ayni birime yazilir
5. Kullanici birime atanmis degilse hata doner

## 9.4 QR Guncelleme Akisi

1. `short_id` ile kayit bulunur
2. Kayit `get_accessible_qr_codes(user)` icinde degilse kullanici erisemez
3. Form dogrulanir
4. Normal kullanicida `department` degismez

## 9.5 QR Silme Akisi

1. Kullanici silme ekranina gelir
2. Kayit yine yetki filtresi icinden bulunur
3. POST ile silinir

## 9.6 Redirect Akisi

1. Kullanici `/<short_id>/` adresine gelir
2. Aktif QR kaydi bulunur
3. Redirect loop kontrolu yapilir
4. IP hash'lenir
5. `ScanAnalytics` kaydi olusturulur
6. Hedef URL'ye 302 yapilir

## 9.7 QR Indirme Akisi

1. Yetkili kullanici `/download-qr/<short_id>/`
2. Kayit yine yetki filtresiyle bulunur
3. PNG uretilir
4. `inline` veya `attachment` olarak doner

## 10. LDAP / Active Directory Entegrasyonu

Bu proje LDAP altyapisina hazirdir.

LDAP aktif oldugunda:

- Giris AD uzerinden dogrulanir
- Kullanici bilgileri yerel Django kullanicisi ile senkronlanir
- `department` alani yerel `Department` tablosuna map edilir
- `LDAP_SUPER_ADMIN_USERNAME` ile tek bir LDAP kullanicisi Super Admin seviyesine yukseltilir

### 10.1 Kullanilan ayarlar

LDAP ayarlari `qr_project/settings.py` icinde env tabanli okunur.

Temel degiskenler:

- `LDAP_ENABLED`
- `AUTH_LDAP_SERVER_URI`
- `AUTH_LDAP_BIND_DN`
- `AUTH_LDAP_BIND_PASSWORD`
- `AUTH_LDAP_USER_SEARCH_BASE_DN`
- `AUTH_LDAP_USER_SEARCH_FILTER`
- `AUTH_LDAP_START_TLS`
- `AUTH_LDAP_IGNORE_CERT_ERRORS`
- `AUTH_LDAP_ATTR_FIRST_NAME`
- `AUTH_LDAP_ATTR_LAST_NAME`
- `AUTH_LDAP_ATTR_EMAIL`
- `AUTH_LDAP_CACHE_TIMEOUT`
- `AUTH_LDAP_NETWORK_TIMEOUT`
- `LDAP_SUPER_ADMIN_USERNAME`

### 10.2 Department mapleme nasil calisir

`core/signals.py` icindeki `map_ldap_user_to_department` fonksiyonu:

1. LDAP kullanicisinin `department` attribute'unu okur
2. Yerel `Department` tablosunda ayni isimde kayit arar
3. Yoksa olusturur
4. Kullaniciyi o birime baglar
5. Kullaniciyi dashboard'a girebilmesi icin `is_staff=True` yapar

### 10.3 Super Admin nasil belirlenir

Sunucuda su env degerini girersiniz:

```env
LDAP_SUPER_ADMIN_USERNAME=ad_kullanici_adi
```

Bu kullanici LDAP ile giris yaptiginda:

- `role='SUPER_ADMIN'`
- `is_superuser=True`

olarak isaretlenir.

Tekrar hatirlatma:

- Yerel superuser ve LDAP super admin'i ayni anda kullanmayin
- Bir tanesini secin

## 11. Ortam Degiskenleri

Ornek dosya: `.env.example`

Bu proje `.env` dosyasini otomatik okuyabilir. Uretimde ise systemd `EnvironmentFile` kullanilmasi daha sagliklidir.

### Genel ayarlar

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,qr.example.org
IP_HASH_SALT=change-me-too
ALLOWED_QR_DOMAINS=yee.org.tr,gov.tr,youtube.com
```

### LDAP ayarlari

```env
LDAP_ENABLED=True
AUTH_LDAP_SERVER_URI=ldaps://dc01.yee.org.tr:636
AUTH_LDAP_BIND_DN=CN=LDAP Service,OU=Service Accounts,DC=yee,DC=org,DC=tr
AUTH_LDAP_BIND_PASSWORD=change-this
AUTH_LDAP_START_TLS=False
AUTH_LDAP_IGNORE_CERT_ERRORS=False
AUTH_LDAP_USER_SEARCH_BASE_DN=OU=Users,DC=yee,DC=org,DC=tr
AUTH_LDAP_USER_SEARCH_FILTER=(sAMAccountName=%(user)s)
AUTH_LDAP_ATTR_FIRST_NAME=givenName
AUTH_LDAP_ATTR_LAST_NAME=sn
AUTH_LDAP_ATTR_EMAIL=mail
AUTH_LDAP_CACHE_TIMEOUT=3600
AUTH_LDAP_NETWORK_TIMEOUT=5
LDAP_SUPER_ADMIN_USERNAME=ldap-admin-user
```

## 12. Lokal Gelistirme Ortami

### 12.1 Gerekenler

- Python 3.12+
- Node.js (sadece Tailwind gerekirse)

### 12.2 Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py check
python manage.py runserver
```

Windows'ta:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py check
python manage.py runserver
```

### 12.3 Tailwind

Bu projede `tailwindcss.exe` ve `node_modules` bulunuyor. CSS yeniden derlemek icin:

```bash
./tailwindcss.exe -i ./static/css/input.css -o ./static/css/tailwind.css --minify
```

Linux'ta npm ile yeniden kurmak isterseniz:

```bash
npm install
npx tailwindcss -i ./static/css/input.css -o ./static/css/tailwind.css --minify
```

## 13. Linux Sunucuda LDAP ile Kurulum

Bu bolum, gercek Linux sunucuda LDAP/AD ile calistirmak icin yazildi.

Assume edilen ortam:

- Ubuntu 22.04 / 24.04 veya Debian
- Nginx reverse proxy
- Gunicorn
- Python virtualenv

### 13.1 Sistem paketleri

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential \
    libldap2-dev libsasl2-dev libssl-dev nginx
```

Bu paketler ozellikle `python-ldap` icin gereklidir.

### 13.2 Projeyi sunucuya alin

```bash
sudo mkdir -p /opt/dynamicqr
sudo chown $USER:$USER /opt/dynamicqr
cd /opt/dynamicqr
git clone <REPO_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 13.3 Environment dosyasini olusturun

Yerel test icin:

```bash
cp .env.example .env
nano .env
```

Uretim icin tavsiye edilen:

```bash
sudo cp .env.example /etc/dynamicqr.env
sudo nano /etc/dynamicqr.env
sudo chmod 600 /etc/dynamicqr.env
```

### 13.4 LDAP bilgilerini doldurun

Ornek:

```env
LDAP_ENABLED=True
AUTH_LDAP_SERVER_URI=ldaps://dc01.yee.org.tr:636
AUTH_LDAP_BIND_DN=CN=LDAP Service,OU=Service Accounts,DC=yee,DC=org,DC=tr
AUTH_LDAP_BIND_PASSWORD=very-secret-password
AUTH_LDAP_USER_SEARCH_BASE_DN=OU=Users,DC=yee,DC=org,DC=tr
AUTH_LDAP_USER_SEARCH_FILTER=(sAMAccountName=%(user)s)
LDAP_SUPER_ADMIN_USERNAME=kurumsal.superadmin
```

### 13.5 LDAP baglantisini dogrulayin

Sunucudan AD'ye erisim oldugunu once ag seviyesinde test edin:

```bash
nc -vz dc01.yee.org.tr 636
```

LDAP bind testi icin `ldap-utils` kurup deneyebilirsiniz:

```bash
sudo apt install -y ldap-utils
ldapsearch -x -H ldaps://dc01.yee.org.tr:636 \
  -D "CN=LDAP Service,OU=Service Accounts,DC=yee,DC=org,DC=tr" \
  -W \
  -b "OU=Users,DC=yee,DC=org,DC=tr" \
  "(sAMAccountName=test.user)"
```

Bu adim Django'dan once ag ve LDAP tarafini dogrulamak icin onemlidir.

### 13.6 Django hazirligi

```bash
cd /opt/dynamicqr
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

### 13.7 Gunicorn

Test calistirmasi:

```bash
source /opt/dynamicqr/.venv/bin/activate
gunicorn qr_project.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 120
```

### 13.8 systemd

Projede ornek servis dosyasi var:

- `deploy/linux/dynamicqr.service.example`

Kurulum:

```bash
sudo cp deploy/linux/dynamicqr.service.example /etc/systemd/system/dynamicqr.service
sudo systemctl daemon-reload
sudo systemctl enable dynamicqr
sudo systemctl start dynamicqr
sudo systemctl status dynamicqr
```

### 13.9 Nginx

Ornek Nginx server block:

```nginx
server {
    listen 80;
    server_name qr.example.org;

    client_max_body_size 20M;

    location /static/ {
        alias /opt/dynamicqr/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Aktif etme:

```bash
sudo ln -s /etc/nginx/sites-available/dynamicqr /etc/nginx/sites-enabled/dynamicqr
sudo nginx -t
sudo systemctl reload nginx
```

### 13.10 LDAP login testi

1. Tarayicidan `/admin/login/` acin
2. Kurumdaki AD kullanicisi ile giris yapin
3. Basarili giriste `/dashboard/` acilmali
4. Django shell ile kullaniciyi kontrol edin:

```bash
python manage.py shell
```

```python
from core.models import CustomUser
u = CustomUser.objects.get(username="test.user")
print(u.department, u.role, u.is_staff, u.is_superuser)
```

Beklenen:

- Normal LDAP kullanicisi: `is_staff=True`, `role=DEPT_USER`, `department` dolu
- Super Admin LDAP kullanicisi: `is_staff=True`, `is_superuser=True`, `role=SUPER_ADMIN`

## 14. Guvenlik Notlari

### Uretimde yapilmasi gerekenler

- `DJANGO_DEBUG=False`
- Gercek `DJANGO_SECRET_KEY`
- Gercek `IP_HASH_SALT`
- `ALLOWED_HOSTS` sinirli olmali
- Mümkunse `ldaps://` kullanin
- LDAP sertifika dogrulamayi kapatmayin
- SQLite yerine PostgreSQL kullanin
- Nginx arkasinda TLS kullanin
- Gunicorn'u systemd ile yonetin

### Sadece test icin

```env
AUTH_LDAP_IGNORE_CERT_ERRORS=True
```

Bu ayari sadece testte kullanin. Uretimde kullanmayin.

## 15. Bu Projeyi Bastan Ayni Mantikla Yapmak Istersem

Bu sistemi sifirdan yeniden kurmak icin su sirayi izleyin:

1. Django proje ve `core` app olusturun
2. `AUTH_USER_MODEL` olarak `CustomUser` tanimlayin
3. `Department`, `QRCode`, `ScanAnalytics` modellerini kurun
4. `hash_ip()` ile IP hash mantigini ekleyin
5. `django-simple-history` ile `QRCode.history` ekleyin
6. `get_accessible_qr_codes(user)` gibi merkezi RBAC filtre fonksiyonu yazin
7. Dashboard, create, edit, delete ve download view'larini bu filtre uzerinden calistirin
8. Redirect view'da analytics kaydi ve loop korumasi yapin
9. `django-auth-ldap` ile LDAP backend'i ekleyin
10. `populate_user` sinyaliyle `department` alanini AD'den map edin
11. Tek global admin kuralini model seviyesinde zorlayin
12. Whitelist kontrollu URL formu yazin
13. Gunicorn + Nginx + systemd ile Linux deploy edin

Bu repo tam olarak bu mimariyi uygular.

## 16. Sik Karsilasilan Sorunlar

### `python-ldap module not found`

Sebep:

- `python-ldap` kurulu degil
- Linux'ta gerekli `libldap2-dev`, `libsasl2-dev`, `libssl-dev` paketleri eksik

Cozum:

```bash
sudo apt install -y libldap2-dev libsasl2-dev libssl-dev
pip install python-ldap django-auth-ldap
```

### LDAP kullanicisi giris yapiyor ama dashboard acilmiyor

Kontrol edin:

- `user.is_staff` true mu
- `department` dolu mu
- `LDAP_ENABLED=True` mi
- `AUTH_LDAP_USER_SEARCH_BASE_DN` dogru mu

### Kullanici giris yapiyor ama birim gelmiyor

Muhtemel sebepler:

- AD'de `department` bos
- Farkli attribute kullaniliyor
- Bind hesabi o alani okuyamiyor

Gerekirse `core/signals.py` icinde `department` yerine kurumun kullandigi alan adina gecin.

### Super Admin calismiyor

Kontrol edin:

- `LDAP_SUPER_ADMIN_USERNAME` dogru mu
- Kullanici adi AD'deki `sAMAccountName` ile birebir ayni mi
- Ayni anda bir yerel superuser daha var mi

### Public test sunucusu LDAP'a baglanamiyor

Sebep genelde ag erisimidir. Kurum AD'si public internetten kapaliysa:

- VPN
- site-to-site tunnel
- ya da kurum ici test sunucusu

gerekir.

## 17. Kontrol Komutlari

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py shell
```

RBAC ve temel davranis dogrulamalari icin repo icinde su scriptler de bulunur:

- `verify_core.py`
- `verify_security.py`
- `verify_rbac.py`
- `verify_redirection.py`
- `verify_qr.py`
- `verify_analytics.py`

## 18. Son Not

Bu repo artik su senaryoya gore hazirdir:

- Linux sunucuda calisir
- LDAP/AD ile giris alir
- LDAP'den birim bilgisini ceker
- QR kayitlarini birim bazli izole eder
- Tek bir Super Admin kullaniciyi tam yetkili tutar

Gercek ortama gecmeden once en dogru test sirası:

1. Linux test sunucusu
2. LDAP bind testi
3. Uygulama login testi
4. Departman izolasyon testi
5. Super Admin testi
6. Redirect ve analytics testi
