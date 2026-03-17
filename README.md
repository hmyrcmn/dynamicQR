# DynamicQR — Kurumsal Dinamik QR Yönlendirme Sistemi

Bu doküman, mevcut kod tabanını esas alarak projenin tüm bileşenlerini, işleyişini, kullanılan teknolojileri, güvenlik yaklaşımını, LDAP/AD entegrasyonunun nasıl çalışacağını, kullanıcı yaşam döngüsünü ve mevcut açıkları detaylı şekilde açıklar.

## 1) Proje Özeti ve Amaç

DynamicQR, kurumsal bağlantıların QR kodları üzerinden güvenli ve yönetilebilir şekilde yönlendirilmesini amaçlayan bir Django uygulamasıdır. Temel kullanım senaryosu:

- Kurum içindeki birimler, kendilerine ait QR kodlarını oluşturur ve yönetir.
- Her QR kodun hedef URL’si dinamik olarak güncellenebilir.
- QR kodlar tarandığında güvenli bir yönlendirme yapılır ve analiz kaydı tutulur.
- Rol ve departman bazlı yetkilendirme ile erişim sınırlandırılır.

## 2) Hedef Kullanıcılar ve Roller

Sistem iki ana kullanıcı tipine hizmet eder:

- Kurum içi personel: Yönetim paneli üzerinden QR oluşturur, düzenler, siler ve kendi departmanı için raporları görür.
- Kamu/ziyaretçi: QR kodu taradığında yalnızca yönlendirme alır.

Rol modeli:

- `SUPER_ADMIN`: Tüm departman ve kullanıcıları görür, her şey üzerinde tam yetkilidir.
- `DEPT_MANAGER`: Sadece kendi departmanındaki kullanıcı ve QR’ları yönetir.
- `DEPT_USER`: Sadece kendi departmanındaki QR’ları görür. (Admin modülleri kısıtlıdır.)

## 3) Teknoloji Yığını ve Kullanım Amaçları

Kodda kullanılan başlıca teknolojiler ve nerede/ne için kullanıldıkları:

- **Django 6.0**
  - MVC benzeri yapı, ORM, admin paneli ve güvenlik middleware’leri.
  - `core/models.py`, `core/views.py`, `core/admin.py`, `core/forms.py`, `core/urls.py`.
- **django-simple-history**
  - QRCode modelinde değişiklik tarihçesi tutmak için.
  - `core/models.py` (HistoricalRecords), `core/admin.py` (SimpleHistoryAdmin).
- **qrcode**
  - QR görseli üretmek için.
  - `core/views.py` → `generate_qr_image_view`.
- **nanoid**
  - Kısa, güvenli `short_id` üretimi için.
  - `core/utils.py` → `generate_short_id`.
- **django-auth-ldap + python-ldap** (opsiyonel)
  - Active Directory/LDAP entegrasyonu için.
  - `qr_project/settings.py`, `core/signals.py`.
- **Celery** (hazırlık var, aktif kullanım yok)
  - Async işleme için altyapı tanımlı, fakat görevler mevcut değil.
  - `qr_project/celery.py`.
- **WhiteNoise**
  - Statik dosyaları servis etmek için.
  - `qr_project/settings.py` (middleware ve storage ayarı).
- **Tailwind CSS (CDN)**
  - Arayüz stilleri ve “glass” tasarım.
  - `templates/*.html`.
- **SQLite**
  - Varsayılan veri tabanı.
  - `db.sqlite3`.

## 4) Proje Yapısı ve Kritik Dosyalar

- `manage.py`: Django yönetim komutları.
- `qr_project/settings.py`: Uygulama ayarları, LDAP, cache, static.
- `qr_project/urls.py`: Kökteki URL yönlendirmeleri.
- `qr_project/celery.py`: Celery yapılandırması.
- `core/models.py`: Departman, kullanıcı, QR ve analiz modelleri.
- `core/views.py`: Landing, dashboard, QR oluşturma/düzenleme/silme, redirect, QR indirme.
- `core/forms.py`: Domain whitelist kontrolü yapan formlar.
- `core/admin.py`: Admin panel yetki kısıtları, CSV export, audit.
- `core/signals.py`: LDAP login sonrası departman eşleme.
- `core/urls.py`: App bazlı URL’ler.
- `templates/`: Landing, dashboard, CRUD, base şablonları.
- `verify_*.py`: Manuel doğrulama ve test scriptleri.

## 5) Veri Modeli ve İlişkiler

Ana modeller:

- `Department`
  - `name`: Departman adı.
  - `is_active`: Aktiflik.
- `CustomUser` (AbstractUser’dan türetilmiş)
  - `department`: Departman FK.
  - `role`: `SUPER_ADMIN`, `DEPT_MANAGER`, `DEPT_USER`.
- `QRCode`
  - `short_id`: Ana anahtar, NanoID ile üretilir.
  - `department`: QR’ın ait olduğu departman.
  - `created_by`: Oluşturan kullanıcı.
  - `destination_url`: Yönlendirme hedefi.
  - `is_active`: Aktif/pasif.
  - `history`: simple_history ile değişiklik geçmişi.
- `ScanAnalytics`
  - `qr_code`: Hangi QR’ın tarandığı.
  - `timestamp`, `ip_address_hash`, `user_agent`.
  - `country`, `city`, `device_type` alanları ileride doldurulmak için hazır.

## 6) Sistem Nasıl Çalışır (Akışlar)

### 6.1 Landing ve Giriş Akışı

1. `/` landing sayfası açılır.
2. Kullanıcı `/admin/` veya kurum SSO/LDAP ile giriş yapar.
3. Giriş yapan kullanıcı rolüne göre yönetim ekranına erişir.

### 6.2 QR Oluşturma Akışı

1. Kullanıcı `/dashboard/create/` sayfasından formu doldurur.
2. Form, hedef URL için domain whitelist kontrolü yapar.
3. `QRCode` kaydı oluşturulur, `created_by` ve `department` atanır.
4. `short_id` otomatik üretilir.

### 6.3 QR Yönlendirme Akışı

1. Ziyaretçi `/ABCD1234/` gibi kısa URL’yi açar.
2. `QRCode` aktifse bulunur.
3. “Loop” kontrolü yapılır (kendi hostuna yönlendirme engeli).
4. IP adresi salt ile hashlenir ve `ScanAnalytics` kaydı oluşturulur.
5. 302 ile hedef URL’ye yönlendirilir.

### 6.4 QR Görseli İndirme

1. `/download-qr/<short_id>/` endpoint’i çağrılır.
2. QR kod görseli dinamik üretilir.
3. PNG olarak indirilir.

## 7) Yetkilendirme (RBAC) ve Modül Kısıtları

Admin panelindeki kısıtlar:

- Department yönetimi: `SUPER_ADMIN` ve `DEPT_MANAGER` görebilir.
- User yönetimi: `SUPER_ADMIN` ve `DEPT_MANAGER` görebilir.
- QR yönetimi: Her kullanıcı kendi departmanındaki QR’ları görür.
- Analitik: Sadece kendi departmanına ait QR analizleri görünür.

Dashboard ekranındaki kısıtlar:

- `SUPER_ADMIN`: Tüm QR’ları görür.
- Diğer roller: Sadece kendi departmanındaki QR’lar.
- Düzenleme ve silme işlemlerinde departman kontrolü yapılır.

## 8) LDAP / Active Directory Entegrasyonu (Mevcut Kod Davranışı)

LDAP entegrasyonu opsiyonel olarak yapılandırılmıştır ve python-ldap yüklüyse aktif olur.

### 8.1 Aktif Olduğunda Neler Olur

1. Django authentication backend sırasına LDAP backend eklenir.
2. Kullanıcı AD’de doğrulanır.
3. AD kullanıcı bilgileri `first_name`, `last_name`, `email` alanlarına eşlenir.
4. `core.signals.map_ldap_user_to_department` sinyali tetiklenir.
5. Kullanıcının AD `department` attribute’u okunur.
6. Bu departman adıyla yerel `Department` kaydı bulunur veya oluşturulur.
7. Kullanıcı otomatik olarak bu departmana atanır.
8. Rolü yoksa varsayılan `DEPT_USER` atanır.

### 8.2 Kimler Kullanabilecek

LDAP aktifken giriş yapabilen herkes:

- AD’de ilgili OU altında bulunan ve `sAMAccountName` ile bulunabilen kullanıcılar.
- Ancak admin paneline erişebilmek için `is_staff=True` olmalıdır. Bu alan LDAP entegrasyonunda otomatik set edilmiyor.
- Bu nedenle admin erişimi için lokal tarafta kullanıcıya `is_staff` ve rol ataması yapılması gerekir.

### 8.3 LDAP Gelince Sistem Nasıl Kalacak

LDAP aktif olduğunda sistemin temel davranışı değişmez, sadece kimlik doğrulama kaynağı AD olur:

- Giriş doğrulaması AD’den gelir.
- Kullanıcı kaydı lokal DB’de açılır ve güncellenir.
- Yetkiler hâlâ `role` ve `department` alanlarına bağlıdır.
- Departman eşlemesi AD `department` alanı ile otomatik yapılır.
- LDAP devre dışıysa, standart Django kullanıcıları ile çalışır.

### 8.4 LDAP Ayarları (settings.py)

Mevcut yapılandırma:

- `AUTH_LDAP_SERVER_URI`
- `AUTH_LDAP_BIND_DN`
- `AUTH_LDAP_BIND_PASSWORD`
- `AUTH_LDAP_USER_SEARCH`
- `AUTH_LDAP_USER_ATTR_MAP`
- `AUTH_LDAP_ALWAYS_UPDATE_USER`

Not: Şu anda bu değerler için varsayılan sabit değerler bulunuyor. Üretimde mutlaka ortam değişkenleriyle override edilmelidir.

## 9) Güvenlik Önlemleri (Mevcut)

Uygulamada mevcut güvenlik mekanizmaları:

- `SecurityMiddleware`, `CSRF`, `XFrameOptions` middleware aktif.
- QR hedef URL’lerde domain whitelist kontrolü var.
- IP adresi ham olarak saklanmıyor; salt’lı SHA-256 hash tutuluyor.
- RBAC ile departman izolasyonu var.
- Admin panelde `ScanAnalytics` kayıtları sadece okunabilir.
- QR değişiklik geçmişi tutuluyor (audit trail).
- Redirect loop koruması var.

## 10) Açık Riskler ve Eksikler (Mevcut Koddan Tespit)

Bu bölüm, doğrudan kodda görülen açıkları listeler:

- `SECRET_KEY` ve LDAP bind şifresi varsayılan olarak kod içinde. Bu üretim için kritik zafiyettir.
- `IP_HASH_SALT` sabit; ortam değişkeni değil.
- `hash_ip` fonksiyonunda `hashlib` import edilmemiş, runtime hatası üretir.
- `core/signals.py` içinde `Department` oluşturulurken `description` alanı kullanılıyor, fakat modelde yok; LDAP login sırasında hata üretir.
- `verify_performance.py` ve bazı verify scriptleri mevcut kodla uyumlu değil (cache ve celery task’lar yok).
- `celery` yapılandırması var ama gerçek task yok; async analitik yok.
- QR oluşturma ekranı super admin için departman atanmadıysa hata verebilir (department null olamaz).
- `ALLOWED_QR_DOMAINS` sabit listesi konfigüre edilebilir değil; yönetim paneli yok.
- Rate limiting, brute-force koruması, IP bloklama gibi mekanizmalar yok.
- HTTPS zorunluluğu ve HSTS ayarları tanımlı değil.
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` gibi production güvenlik ayarları yok.
- `landing.html` dış linkte `rel="noopener noreferrer"` yok (tabnabbing riski).
- `db.sqlite3` depo içinde; gerçek veri içeriyorsa risk.
- Harici CDN (Tailwind/Google Fonts) kullanımı, CSP/mahremiyet açısından risk oluşturabilir.

## 11) Doğrulama / Test Scriptleri

Proje kökünde manuel doğrulama amaçlı scriptler bulunur:

- `verify_core.py`: Model oluşturma ve simple_history kontrolü.
- `verify_security.py`: Domain whitelist testi.
- `verify_rbac.py`: Admin RBAC kontrolü.
- `verify_redirection.py`: Redirect ve analitik kaydı testi.
- `verify_qr.py`: QR PNG üretimi testi.
- `verify_analytics.py`: Analitik sayımı ve RBAC.
- `verify_frontend.py`: Landing ve routing doğrulaması (metinler güncel değil).
- `verify_performance.py`: Cache/Celery testleri (uyumsuz).

## 12) Kurulum ve Çalıştırma (Önerilen)

Bu repo içinde requirements dosyası yok; bağımlılıklar importlardan çıkarılmıştır:

- Django 6.0
- qrcode (Pillow backend)
- nanoid
- django-simple-history
- whitenoise
- celery
- django-auth-ldap + python-ldap (opsiyonel)

Örnek kurulum adımları:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install django qrcode pillow nanoid django-simple-history whitenoise celery django-auth-ldap python-ldap
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 13) Konfigürasyon (Önerilen Ortam Değişkenleri)

Production için önerilen env değişkenleri:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `AUTH_LDAP_SERVER_URI`
- `AUTH_LDAP_BIND_DN`
- `AUTH_LDAP_BIND_PASSWORD`
- `IP_HASH_SALT`

## 14) Üretim Notları

- SQLite yerine kurumsal DB (PostgreSQL) önerilir.
- Statik dosyalar için WhiteNoise yeterli olabilir; yüksek trafikte CDN önerilir.
- LDAP kullanımı için python-ldap kurulumu Windows ortamında sorun çıkarabilir.
- IP hash salt ve LDAP bind şifreleri kod içinde tutulmamalıdır.
- `ALLOWED_QR_DOMAINS` dinamik bir yönetim ekranına taşınmalıdır.
- Audit log büyüyebilir; arşiv/retention planı gerekir.

## 15) Özet

Bu sistem; departman temelli RBAC, domain whitelist, audit logging ve QR yönlendirme altyapısı sunar. LDAP entegrasyonu için gerekli altyapı kısmen hazırdır, ancak bazı kritik güvenlik ve stabilite eksikleri giderilmeden üretime alınması uygun değildir.
