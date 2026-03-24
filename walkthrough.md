# Dinamik QR Kod Yönetim Sistemi - Walkthrough
*(Yunus Emre Enstitüsü Resmi Yönlendirme Servisi)*

## Proje Başlangıcı ve Altyapı
Sistem baştan aşağıya kurumsal ihtiyaçlar (Departman izolasyonu, Rol Bazlı Güvenlik, ve Premium Görsellik) gözetilerek inşa edilmiştir.

### Teknik Kararlar & YAGNI Yaklaşımı:
- Geliştirme sürecinin başında Redis ve Celery gibi kompleks mimariler düşünülmüş, ancak "You Aren't Gonna Need It" (YAGNI) prensibi gözetilerek sistem senkron çalışacak şekilde optimize edilmiştir.
- Framework olarak Django 6.0 kullanılmış olup SQLite üzerinden hızlı bir MVP çıkarılmıştır.

### Veri Modelleri:
- **`Department` Modeli:** QR kodların ve kullanıcıların bağlandığı ana grup.
- **`CustomUser` Modeli:** Her kullanıcının bir departmanı olması zorunlu kılındı (Superadminler hariç).
- **`QRCode` Modeli:** Otomatik `short_id` üreten (NanoID benzeri), hedef URL, departman sahipliği ve 404/Aktiflik durumu kontrolü sağlayan ana model.

## Redirection ve Track Engine (Yönlendirme Motoru)
- Sistemin kalbini oluşturan yönlendirme mekanizmasına "Sonsuz Döngü Koruması" (Loop Protection) eklenmiştir.
- Hashing algoritması cihazın IP'sini şifreler (KVKK Uyumluluğu) ve `ScanAnalytics` tablosuna bir tıklama satırı atar.
- Yanlış veya pasif bağlantılar, kurumsal kimlik ile süslenmiş özel 404 sayfasına atılır.

## Güvenlik ve RBAC (Rol Bazlı Erişim Kontrolü)
- Sisteme hem Admin Paneli'ne hem de özel formlara (View/Edit/Delete) katı "QuerySet Filtreleme" kuralı eklendi.
- Bir personelin sadece bağlı olduğu birimi görmesi sağlandı.
- Güvenlik zafiyetlerini engellemek için, kabul edilebilir Domainler `ALLOWED_QR_DOMAINS` beyaz listesi (White-list) ile koruma altına alınmıştır.

## Sistem Entegrasyonları: Active Directory (LDAP) Desteği
- Kurumun iç ağındaki personelin Active Directory (LDAP) üzerinden Django ile şifresiz/güvenli olarak konuşması yapılandırılmıştır (`django-auth-ldap`).
- Personel LDAP ile giriş yaptığında, sunucu kullanıcının departman bilgisini çekip anında departman atamasını yapar. Bu işlem sonucunda personelin hiçbir ekstra yetkilendirmeye ihtiyacı kalmadan RBAC izolasyonuna girmesi sağlanır.

## Frontend & Corporate UI ("Apple Liquid Glass" Tasarımı)
- `base.html`, `landing.html` ve Admin UI sayfaları; bulanıklık (backdrop-blur-xl), akışkan mesh gradient'lar (liquid-pulse) ve transparan cam (.glass-card) görünümleriyle modern bir Apple arayüzü kalitesinde kodlanmıştır.
- Yunus Emre Enstitüsü kurumsal paleti (Siyan, Turkuaz, Gece Mavisi) projeye %100 entegre edilmiştir.

## Final MVP Operasyonları (Edit / Delete Akışları)
- Dashboard üzerindeki QR kod tablosuna "Amber" (Düzenle) ve "Rose" (Sil) butonları yerleştirilmiş, arkasındaki Controller operasyonları (`qr_edit_view`, `qr_delete_view`) Active Directory kuralları ve Departman rolü doğrultusunda güvenli hale getirilmiştir.
- Admin sayfalarına giriş/çıkışta istenmeyen çıplak Django Admin paneli arayüzlerinin engellenebilmesi için login formuna gizli `next` parametresi ve Logout (`custom_logout_view`) özel uç noktaları kurgulanmıştır.

## Profesyonel Kurumsal UI Güncellemesi (V2)
- Sistem arayüzü, daha kurumsal ve yönetilebilir bir formata (Navy/Teal renk paleti) geçirilmişti. 

## Apple Glass UI Güncellemesi (V3)
- Kullanıcının "Apple Glass (Glassmorphism)" tasarım talebi doğrultusunda sistem modern, iOS/macOS ekosistemi hissiyatlı bir arayüze geçirildi.
- **Arkaplan (Ambient Background):** Sayfa tabanına yavaşça hareket eden, birbirine geçen renkli mesh gradient küreler eklendi (Apple Blue ve Apple Teal tonlarında).
- **Glass Utilities (.apple-glass):** Kartlar, tablolar ve menüler beyazın arkasını bulanık gösteren (backdrop-blur-xl), pürüzsüz gölgeli ve ince kenarlıklı cam panellere dönüştürüldü.
## Backend & İşleyiş (Functionality) Düzeltmeleri (V4)
Projenin temel işleyişini bozan ve README içerisinde kasıtlı bırakılmış (Bilinen Eksikler) kritik *Python Backend* (Django) hataları tespit edilerek giderildi:
- **Analitik Yönlendirme Çökmesi:** IP maskeleme işlemini yapan `hash_ip` metodunda unutulan `import hashlib` hatası çözüldü, ScanAnalytics rotasındaki 500 çökmesi engellendi.
- **Departman Sinyal Hatası:** LDAP'dan dönen kullanıcılar için çalıştırılan `Department.objects.get_or_create` metodunda `description` keyword'ünün neden olduğu FieldError giderildi.
- **QR Kod Oluşturma Hatası:** Yeni bir kayıt oluşturulurken oturum açmış kullanıcının departmanı eğer boş ise (`user.department is None`) kaydın patlamaması için doğrulama eklendi; kullanıcıya 400 Bad Request döndürüldü.
- **Testler:** Arka planda `verify_frontend.py` ve `verify_redirection.py` çalıştırılarak hata kodlarının (Exit 1) sıfırlandığı doğrulandı.

## Tam Türkçe Yerelleştirme (Localization)
Sistem son kullanıcı ve yönetici için %100 Türkçe hale getirildi:
- **Arayüz:** Dashboard, Giriş sayfası ve Formlar tamamen Türkçe terimlerle güncellendi.
- **Admin Paneli:** Django Admin arayüzü başlıkları, model isimleri ve yardım metinleri ("QR İndir", "Tekil Ziyaretçi" vb.) yerelleştirildi.
- **Hata Mesajları:** URL güvenlik kontrolleri ve form doğrulama uyarıları kurumsal dil yapısına uygun hale getirildi.
