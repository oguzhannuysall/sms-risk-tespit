# 🛡️ SMS Güvenlik Asistanı

Telefonunuza gelen bir SMS'in **dolandırıcılık (smishing) tuzağı mı, güvenli bir mesaj mı** olduğunu analiz eden, Türkçe için geliştirilmiş bir web uygulaması.

KTO Karatay Üniversitesi – Yapay Zeka dersi projesi.

Uygulama bir **hibrit sistem** kullanır: elle yazılmış **kural katmanı** ile **makine öğrenmesi (ML)** modelini birleştirir. Harici bir API veya yapay zeka servisi kullanmaz; analiz tamamen kendi sunucusunda yapılır.

---

## ✨ Özellikler

- **Risk skoru (0–100):** Mesaj "Güvenli", "Şüpheli" veya "Tehlikeli" olarak sınıflandırılır.
- **Açıklanabilir sonuç:** "Bu sonuca neden vardık?" bölümü, skoru hangi işaretlerin yükselttiğini gösterir. Riskli kelimeler ve linkler mesaj üzerinde işaretlenir.
- **Link analizi:** Kısaltılmış link (bit.ly vb.), IP adresli link, riskli uzantı (.xyz, .top…), punycode ve kurum taklidi tespiti. Mesajda adı geçen kurum ile linkin resmi alan adının uyuşup uyuşmadığı kontrol edilir.
- **Türkçe metin işleme:** Büyük/küçük harf ve Türkçe karakter farkları ile ekler (icra → icradan) tanınır.
- **Kelime oyunu çözücü:** `b.l.o.k.e` veya `p4r4` gibi filtreyi atlatma denemeleri çözülür.
- **Kişisel veri maskeleme:** Kaydedilen metinlerde IBAN, kart, telefon, TC kimlik no ve e-posta otomatik maskelenir.
- **Ölçülebilir başarı:** Ayrılmış test seti üzerinde doğruluk, kesinlik, yakalama, F1 ve karışıklık matrisi; "yalnız kural", "yalnız ML" ve "hibrit" yan yana karşılaştırılır.
- **Kendi test setinle ölç:** Sistemin görmediği bir CSV yükleyerek gerçek başarı ölçülebilir.
- **Yönetici paneli:** Kullanıcı önerilerini onaylama, "Yanlış" geri bildirimlerini inceleme, veri yedekleme ve geri yükleme.

---

## 🧠 Nasıl Çalışır?

```
SMS metni
   │
   ├─► Kural katmanı (kurallar.py)  → kural skoru (0–100)
   │      link analizi · anahtar kelime kategorileri · kurum taklidi · kelime oyunu
   │
   ├─► ML katmanı (ml.py)           → tuzak olasılığı (0–100)
   │      TF-IDF (karakter n-gram) + Lojistik Regresyon
   │
   └─► Birleştirme
          nihai risk = 0.7 × kural + 0.3 × ML
          (veri yetersizse yalnızca kural kullanılır)
```

- Yalnızca bilinen güvenli bir adres içeren ve riskli ifade barındırmayan mesajların riski düşük tutulur.
- Eğitim verisi yetersizse (30'dan az kayıt ya da her sınıftan 6'dan az örnek) ML skora katılmaz.
- Risk ≥ 70 **Tehlikeli**, 30–69 **Şüpheli**, 30'un altı **Güvenli** olarak gösterilir.

---

## 📁 Proje Yapısı

| Dosya | Görevi |
|---|---|
| `app.py` | Streamlit arayüzü, veritabanı, sayfalar, yönetici paneli |
| `kurallar.py` | Kural katmanı: normalleştirme, link analizi, anahtar kelimeler, maskeleme |
| `ml.py` | ML katmanı: eğitim, skorlama, kural+ML birleştirme, değerlendirme |
| `dataset.csv` | Başlangıç veri seti (`mesaj`, `etiket`; 1 = tuzak, 0 = güvenli) |
| `requirements.txt` | Python bağımlılıkları |
| `.devcontainer/` | GitHub Codespaces ayarları |

---

## 🚀 Kurulum ve Çalıştırma

Python 3.11 önerilir.

```bash
# 1. Repoyu indirin
git clone <repo-adresi>
cd sms-risk-tespit-main

# 2. Bağımlılıkları kurun
pip install -r requirements.txt

# 3. Uygulamayı başlatın
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` adresi açılır. İlk çalıştırmada `dataset.csv` içindeki mesajlar otomatik olarak veritabanına (`sms_guvenlik.db`) aktarılır.

---

## 🔒 Yönetici Paneli Kurulumu (isteğe bağlı)

Yönetici paneline girmek için `.streamlit/secrets.toml` dosyası oluşturun. **Bu dosya `.gitignore` içindedir; GitHub'a asla yüklemeyin.**

```toml
[ADMINS.kullanici]
isim = "Ad Soyad"
salt = "<hex>"
hash = "<hex>"
```

`salt` ve `hash` değerlerini terminalde şu komutla üretin (şifre sorulur, ekranda görünmez):

```bash
python -c "import hashlib,os,getpass;s=os.urandom(16);print(s.hex(),hashlib.pbkdf2_hmac('sha256',getpass.getpass().encode(),s,200000).hex())"
```

Çıktının ilk kısmı `salt`, ikinci kısmı `hash` değeridir. Şifre düz metin olarak hiçbir yerde saklanmaz. Art arda hatalı girişlerde hesap 15 dakika kilitlenir.

---

## 📊 Başarı Ölçümü

Başlangıç veri seti 81 mesajdan oluşur (41 tuzak, 40 güvenli). Veri küçük olduğu için tek bir train/test bölmesi sonucu şans eseri değiştirebilir; bu yüzden birden fazla yöntemle ölçülmüştür:

- **5 katlı çapraz doğrulama (yalnız ML):** F1 ≈ %91
- **20 farklı rastgele bölmenin ortalaması (doğruluk):** hibrit ≈ %96,7 · yalnız kural ≈ %95,2 · yalnız ML ≈ %92,4

Güncel değerler uygulamadaki **"🧠 Sistem Nasıl Çalışır? → Ölçülen Başarı"** sekmesinde görülebilir.

---

## ⚠️ Sınırlılıklar

- Veri seti küçüktür; daha fazla ve çeşitli mesaj eklendikçe sonuçlar güvenilirleşir.
- Kurallar bilinen örnekler görülerek yazıldığı için kural katmanının ölçülen başarısı iyimser olabilir. Kesin ölçüm için sistemin hiç görmediği, dışarıdan alınmış bir test seti kullanılmalıdır.
- Linki olmayan, yalnızca metinle yönlendiren mesajlar (ör. "kartınız bloke edildi, şu numarayı arayın") düşük risk alabilir.
- Anahtar kelime tabanlı olduğu için "icra", "bloke" gibi kelimeleri uyarı amacıyla kullanan masum mesajlar yanlış alarm verebilir.
- Yalnızca Türkçe mesajlar için tasarlanmıştır; İngilizce mesajlarda başarı düşüktür.
- Streamlit Community Cloud'da disk geçicidir; uygulama yeniden başlayınca veritabanı sıfırlanır. Yönetici panelinden düzenli CSV yedeği alın ve `dataset.csv` olarak repoya koyun. Kalıcı çözüm için harici bir veritabanı (Supabase, Turso vb.) kullanılabilir.

---

## 👥 Geliştirici Ekibi

- **Muzaffer Alp Ergülcü** – Yazılım
- **Oğuzhan Uysal** – Güvenlik

---

> Bu uygulama bir **farkındalık ve eğitim aracıdır**. Sonuçlar kesin hüküm değildir; şüphelendiğiniz mesajlar için ilgili kurumu kendi resmi iletişim kanalından arayarak teyit edin.
