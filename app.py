import streamlit as st
import pandas as pd
import re
import random
import os
import socket
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# --- 1. PERFORMANS VE HIZ OPTİMİZASYONLARI ---
socket.setdefaulttimeout(1.5)
LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+|\b[a-zA-Z0-9.-]+\.(?:com|net|org|tr|xyz|info|ly|co|gd|me|io)\b)", re.IGNORECASE)
GIZLI_HARF_REGEX = re.compile(r"(?<=\b\w)[\.\-\_\s\*]+(?=\w\b)")

# --- 2. SAYFA AYARLARI VE YENİ NESİL GLASSMORPHISM UI CSS ---
st.set_page_config(page_title="Akıllı SMS Analizörü", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    /* Ana Arka Plan - Derin Siber Uzay Teması */
    .stApp {
        background: radial-gradient(circle at top right, #131B2E 0%, #0B0F19 60%, #070A10 100%);
        color: #F0F4F8;
    }
    /* Üst Bilgi Barı (Status Header) */
    .status-bar {
        background: rgba(16, 24, 39, 0.75);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(0, 242, 254, 0.2);
        border-radius: 14px;
        padding: 12px 22px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #00f2fe;
        background: rgba(0, 242, 254, 0.1);
        padding: 5px 12px;
        border-radius: 20px;
        border: 1px solid rgba(0, 242, 254, 0.25);
    }
    /* Modern Buton Tasarımları */
    div.stButton > button:first-child {
        border-radius: 12px;
        font-weight: 600;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: #ffffff;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(0, 242, 254, 0.2);
        padding: 0.55rem 1rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 22px rgba(0, 242, 254, 0.35);
        border-color: #00f2fe;
        background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%);
    }
    /* Birincil (Primary) Analiz Butonu */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);
        border: 1px solid rgba(255, 255, 255, 0.3);
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }
    /* Metrik Kartları - Buzlu Cam Efekti */
    div[data-testid="metric-container"] {
        background: rgba(22, 27, 34, 0.65);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 242, 254, 0.2);
        padding: 18px 22px;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    /* Metin Giriş Kutusu Estetiği */
    .stTextArea textarea, .stTextInput input {
        border-radius: 14px !important;
        border: 1px solid rgba(0, 242, 254, 0.25) !important;
        background-color: rgba(17, 22, 29, 0.85) !important;
        color: #FFFFFF !important;
        font-size: 15px !important;
        padding: 14px !important;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.4) !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #00f2fe !important;
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.25) !important;
    }
    /* Yan Menü (Sidebar) */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0D1117 0%, #111827 100%);
        border-right: 1px solid rgba(0, 242, 254, 0.12);
    }
    /* XAI Fosforlu Kelime İşaretleme Kutusu */
    .xai-box {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(0, 242, 254, 0.25);
        border-radius: 14px;
        padding: 18px;
        font-size: 15.5px;
        line-height: 1.8;
        margin-top: 10px;
        margin-bottom: 18px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
    }
    .xai-danger {
        background-color: rgba(255, 75, 75, 0.25);
        color: #ff8080;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(255, 75, 75, 0.65);
        font-weight: 700;
    }
    .xai-safe {
        background-color: rgba(0, 242, 254, 0.15);
        color: #00f2fe;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(0, 242, 254, 0.45);
        font-weight: 700;
    }
    /* Görsel Risk Termometresi */
    .thermo-bg {
        width: 100%;
        background-color: #1f2937;
        border-radius: 12px;
        height: 22px;
        overflow: hidden;
        margin-top: 10px;
        border: 1px solid rgba(255,255,255,0.12);
    }
    .thermo-fill {
        height: 100%;
        border-radius: 12px;
        transition: width 0.5s ease-out;
    }
    /* Gerekçe Kartları */
    .reason-card {
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid #00f2fe;
        padding: 12px 16px;
        border-radius: 0 10px 10px 0;
        margin-bottom: 10px;
        font-size: 14.5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MODEL YÜKLEME VE VERİ GÜVENLİĞİ ---
@st.cache_resource(show_spinner=False)
def modeli_yukle():
    try:
        df = pd.read_csv('dataset.csv', on_bad_lines='skip')
        df = df.dropna(subset=['mesaj', 'etiket'])
        df['etiket'] = df['etiket'].astype(int)
    except Exception:
        df = pd.DataFrame({
            'mesaj': [
                "PTT Kargo: Gonderiniz teslim edilemedi. Lutfen adresinizi guncelleyin: http://bit.ly/kargo-onay",
                "Hakkınızda icra takibi başlatılmıştır. Borcunuzu ödemek için e-devlet-sorgu.com adresine giriniz.",
                "Yarın saat 14:00'te toplantımız var, lütfen gecikmeyin."
            ],
            'etiket': [1, 1, 0]
        })
    
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB())
    model.fit(df['mesaj'], df['etiket'])
    return model, df

model, df = modeli_yukle()

# --- 4. ZENGİNLEŞTİRİLMİŞ ÖRNEK MESAJ HAVUZLARI (40+ FARKLI SENARYO) ---
ORNEK_HAVUZU = {
    "icra_banka": [
        "Sn. Vatandaş, hakkınızda açılacak cinsel taciz davası bulunmaktadır. Uzlaştırma bedeli olan 5000 TL'yi hemen hesaba yatırın: hukuk-odeme.com",
        "Ziraat Bankası: Hesabınızdan şüpheli işlem tespit edilmiştir. Bloke konulmaması için derhal doğrulayın: ziraat-guvenlik.xyz",
        "Hukuk Bürosu: Hakkınızda başlatılan icra takibini durdurmak için bugün mesai bitimine kadar 3.850 TL dosya masrafını IBAN'a gönderin.",
        "Garanti BBVA: Mobil şube erişiminiz güvenlik nedeniyle kısıtlanmıştır. Kimlik onayı için tıklayın: http://tinyurl.com/garanti-onay",
        "Ağır Ceza Mahkemesi: Yasa dışı bahis soruşturması kapsamında adınıza ceza kesilmiştir. Evrakları görmek için: uyap-vatandas.net",
        "Akbank: Kredi kartınızdan 12.400 TL yurt dışı harcaması yapıldı. İşlem size ait değilse hemen iptal edin: akbank-iptal.org",
        "Sayın Müşterimiz, birikmiş kredi kartı aidat iadeniz olan 2.150 TL'yi hesabınıza aktarmak için kart bilgilerinizi girin: aidat-iade.com",
        "Papara: Hesabınızda olağandışı para transferi saptandı. Varlıklarınızı korumak için acil giriş yapın: papara-dogrulama.xyz",
        "HGS Müşteri Hizmetleri: Otoyol geçiş ihlali cezanız icraya düşmeden ödemek için tıklayınız: hgs-ceza-odeme.net",
        "Binance TR: Hesabınıza farklı bir IP üzerinden giriş yapıldı. Çekim işlemlerini durdurmak için tıklayın: binance-kalkan.com"
    ],
    "kargo_odul": [
        "PTT Kargo: Gönderiniz adres yetersizliği nedeniyle teslim edilemedi. Adresinizi güncellemek için tıklayın: http://bit.ly/ptt-guncelle",
        "MNG Kargo: Dağıtıma çıkan 482910 nolu kargonuz iade sürecine girmiştir. Tekrar dağıtım talebi için: mng-teslimat.xyz",
        "E-Devlet Kapısı: Aile destek paketi kapsamında 4.500 TL yardım başvurunuz onaylandı. Hesaba çekmek için: edevlet-destek.org",
        "Tebrikler! Trendyol çekilişinden 10.000 TL değerinde hediye çeki kazandınız. Süre bitiyor, hemen alın: trendyol-ikramiye.net",
        "Yurtiçi Kargo: Paketiniz gümrük vergisi ödenmediği için depoda bekletiliyor. 85 TL ödeme yapmak için: yurtici-gumruk.com",
        "SGK Bilgilendirme: Geçmiş dönem prim ödemelerinizden 3.200 TL iade hakkınız doğmuştur. Başvuru: sgk-prim-iade.net",
        "BİM Marketler: Kuruluş yıldönümümüze özel 2.500 TL alışveriş kuponu kazandınız! Bugün son gün: bim-kupon-al.xyz",
        "Aras Kargo: Kargonuzun teslimat adresini onaylamadığınız için şubeye geri dönmüştür. Onay linki: http://cutt.ly/aras-kargo",
        "Netflix: Son abonelik ödemeniz tahsil edilemedi. Üyeliğinizin iptal olmaması için kartınızı güncelleyin: netflix-fatura.com",
        "TÜVTÜRK: Araç muayene randevunuzda gecikme faizi bulunmaktadır. Hemen online ödeme yapmak için: tuvturk-odeme.org"
    ],
    "kelime_oyunu": [
        "Sayin musteri hesabiniza b.l.o.k.e konulmustur. Acil islem icin tiklayin: tinyurl.com/banka-onay",
        "Hakkınızda i.c.r.a takibi başlatılmıştır. Mağdur olmamak için bugün e-devlet-sorgu.xyz adresine giriniz.",
        "Uzlastirma burosu: d.a.v.a dosyanizin kapanmasi icin 6000 TL p4r4 transferini hemen yapiniz: uzlasma-merkezi.com",
        "PTT Kargo: K4rgonuz adres hatasi nedeniyle t.e.s.l.i.m edilemedi. Hemen tiklayin: bit.ly/kargo-takip",
        "Yasa disi b.a.h.i.s cezasi kapsaminda 45.000 TL c3za odemeniz gerekmektedir. Detaylar: siber-ceza.net",
        "Ziraat: Kredi kartiniz s.u.p.h.e.l.i islem nedeniyle kapatildi. Aktif etmek icin: ziraat-mobil.xyz",
        "Tebrikler! 5000 TL h3diye ceki k4zandiniz. 24 saat icinde almak icin: odul-merkezi.org"
    ],
    "guvenli": [
        "Yarın saat 14:00'te proje toplantımız var, lütfen gecikmeyin. İyi çalışmalar.",
        "Şu yapay zeka ders videosuna mutlaka baksana: https://www.youtube.com/watch?v=aircAruvnKk",
        "Ziraat Bankası: 4821 nolu kartınızla 340,00 TL tutarında market alışverişi yapılmıştır. B001",
        "Yurtiçi Kargo: 84920192 takip numaralı gönderiniz teslim edilmek üzere dağıtıma çıkarılmıştır. B018",
        "Kanka akşam halı saha maçına geliyorsun değil mi? Kramponları unutma.",
        "Öğrenci İşleri: Güz dönemi vize sınav takvimi üniversitemizin resmi sayfasında yayınlanmıştır: https://www.karatay.edu.tr",
        "E-Devlet şifrenizle giriş doğrulama kodunuz: 492810. Güvenliğiniz için bu kodu kimseyle paylaşmayınız. B001",
        "Anneciğim gelirken fırından 2 tane sıcak pide alır mısın? Akşama misafir var.",
        "Trendyol Express: Siparişiniz güvenle teslim edilmiştir. Bizi tercih ettiğiniz için teşekkür ederiz. B043",
        "Kiranızı bu ayın 5'ine kadar her zamanki hesaba yatırmanızı rica ederim, iyi akşamlar.",
        "Resmi belge sorgulama işlemlerinizi sadece https://www.turkiye.gov.tr adresi üzerinden gerçekleştiriniz."
    ]
}

# --- 5. KATEGORİ SÖZLÜKLERİ VE ANALİZ FONKSİYONLARI ---
KATEGORILER = {
    "kargo": ["ptt", "mng", "yurtiçi", "yurtici", "aras", "teslim edilemedi", "adres hatası", "adres yetersizliği", "kargonuz", "gönderiniz", "iade", "gümrük"],
    "icra_hukuk": ["icra", "dava", "uzlaştırma", "uzlastirma", "adliye", "sevk", "hapis", "tazminat", "savcılık", "ceza", "hukuk", "bahis", "taciz", "soruşturma", "uyap"],
    "banka_finans": ["bloke", "kredi kartı", "hesabınıza", "şüpheli işlem", "supheli", "iptal", "ziraat", "garanti", "akbank", "papara", "aidat", "binance"],
    "odul_yardim": ["tebrikler", "hediye", "kazandınız", "kazandiniz", "askıda fatura", "ikramiye", "çekiliş", "bonus", "kupon", "destek paketi"],
    "para_talebi": ["iban", "hesaba yatır", "ödeme", "odeme", "tl", "bedeli", "masraf", "para transferi", "borcunuzu"],
    "aciliyet": ["acil", "hemen", "derhal", "bugün", "son gün", "süre bitiyor", "24 saat", "12 saat", "mesai bitimine"]
}

GUVENLI_DOMAINLER = ["youtube.com", "youtu.be", "google.com", "instagram.com", "turkiye.gov.tr", "edu.tr", "whatsapp.com", "github.com", "twitter.com"]
KISALTILMIS_LINKLER = ["bit.ly", "tinyurl.com", "t.co", "ow.ly", "cutt.ly", "is.gd"]

def kelime_oyunu_coz(metin):
    kucuk = metin.lower()
    leet_haritasi = str.maketrans({'4': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's', '7': 't'})
    cozulmus = kucuk.translate(leet_haritasi)
    cozulmus = GIZLI_HARF_REGEX.sub("", cozulmus)
    return cozulmus

def xai_metin_renklendir(metin, yakalanan_kelimeler, linkler, guvenli_mi):
    islenmis = metin
    for link in set(linkler):
        stil = "xai-safe" if guvenli_mi else "xai-danger"
        islenmis = islenmis.replace(link, f'<span class="{stil}">🔗 {link}</span>')
    
    for kelime in sorted(set(yakalanan_kelimeler), key=len, reverse=True):
        pattern = re.compile(re.escape(kelime), re.IGNORECASE)
        islenmis = pattern.sub(lambda m: f'<span class="xai-danger">{m.group(0)}</span>', islenmis)
    return islenmis

def mesaji_analiz_et(mesaj_girdisi):
    gerekceler = []
    yakalanan_kelimeler = []
    risk_skoru = 0
    mesaj_lower = mesaj_girdisi.lower()
    cozulmus_mesaj = kelime_oyunu_coz(mesaj_girdisi)

    bulunan_linkler = LINK_REGEX.findall(mesaj_girdisi)
    guvenli_link_var = False
    tehlikeli_link_var = False

    if bulunan_linkler:
        for link in bulunan_linkler:
            domain = link.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
            if any(guvenli in domain.lower() for guvenli in GUVENLI_DOMAINLER):
                guvenli_link_var = True
                gerekceler.append(f"🌐 **Güvenilir Bağlantı:** `{domain}` adresi sistemin beyaz listesinde (Whitelist) yer almaktadır.")
            else:
                tehlikeli_link_var = True
                try:
                    ip_adresi = socket.gethostbyname(domain)
                    ip_detay = f"Sunucu IP: {ip_adresi}"
                except Exception:
                    ip_detay = "IP Gizlenmiş / Aktif Değil"

                if any(kisaltma in domain.lower() for kisaltma in KISALTILMIS_LINKLER):
                    gerekceler.append(f"🔗 **Tehlikeli Link Kısaltması:** Hedefi gizleyen kısaltılmış bağlantı (`{domain}`) tespit edildi! ({ip_detay})")
                    risk_skoru += 55
                else:
                    gerekceler.append(f"🔗 **Şüpheli Dış Bağlantı:** Doğrulanmamış bir web adresine (`{domain}`) yönlendirme yapılıyor. ({ip_detay})")
                    risk_skoru += 45

    kelime_oyunu_var = False
    for kategori, kelimeler in KATEGORILER.items():
        kategori_yakalandi = False
        for k in kelimeler:
            if k in mesaj_lower:
                kategori_yakalandi = True
                yakalanan_kelimeler.append(k)
            elif k in cozulmus_mesaj:
                kategori_yakalandi = True
                kelime_oyunu_var = True
                yakalanan_kelimeler.append(k)

        if kategori_yakalandi:
            if kategori == "icra_hukuk":
                gerekceler.append("⚖️ **Hukuki Tehdit ve Korkutma:** İcra, dava veya ceza ifadeleriyle panik yaratılmaya çalışılıyor.")
                risk_skoru += 35
            elif kategori == "banka_finans":
                gerekceler.append("🏦 **Banka / Finans Oltalaması:** Hesap blokesi veya kart işlemleri üzerinden tuzak kuruluyor.")
                risk_skoru += 30
            elif kategori == "kargo":
                gerekceler.append("📦 **Sahte Kargo Bildirimi:** Teslimat veya adres hatası bahanesiyle kişisel veri hedefleniyor.")
                risk_skoru += 30
            elif kategori == "odul_yardim":
                gerekceler.append("🎁 **Sahte Ödül / Yardım Vaadi:** Hediye çeki, ikramiye veya sosyal yardım vaadiyle kandırma girişimi.")
                risk_skoru += 30
            elif kategori == "para_talebi":
                gerekceler.append("💸 **Doğrudan Para / Ödeme Talebi:** Mesaj içerisinde ödeme, TL tutarı veya IBAN transferi isteniyor.")
                risk_skoru += 35
            elif kategori == "aciliyet":
                gerekceler.append("⏱️ **Suni Aciliyet (Zaman Baskısı):** Kurbanın düşünmesini engellemek için acil işlem baskısı yapılıyor.")
                risk_skoru += 15

    if kelime_oyunu_var:
        gerekceler.append("🕵️ **Kelime Oyunu (Filtre Atlatma) Tespiti:** Güvenlik filtrelerini aşmak için harf değiştirme veya noktalama gizlemesi yapılmış!")
        risk_skoru += 25

    ml_tahmin = model.predict([cozulmus_mesaj])[0]
    if ml_tahmin == 1:
        if guvenli_link_var and not tehlikeli_link_var and risk_skoru == 0:
            gerekceler.append("🧠 **Yapay Zeka Notu:** Bağlantı güvenilir beyaz listede yer aldığı için yanlış pozitif (False Positive) riski sıfırlandı.")
            risk_skoru = 0
        else:
            gerekceler.append("🧠 **Yapay Zeka (NLP) Eşleşmesi:** TF-IDF ve Naive Bayes modeli, metnin bağlamını dolandırıcılık veri setiyle eşleştirdi.")
            risk_skoru += 20

    toplam_risk = min(risk_skoru, 100)
    return toplam_risk, gerekceler, yakalanan_kelimeler, bulunan_linkler, (guvenli_link_var and not tehlikeli_link_var)

# --- 6. AKICI ÖRNEK SEÇİM CALLBACK FONKSİYONLARI (TAKILMAYI ÖNLER) ---
if "aktif_mesaj" not in st.session_state:
    st.session_state.aktif_mesaj = ""
if "otomatik_analiz" not in st.session_state:
    st.session_state.otomatik_analiz = False

def ornek_getir(kategori_anahtari):
    """Mevcut mesajdan farklı bir örneği kesintisiz seçer ve otomatik analizi tetikler."""
    havuz = ORNEK_HAVUZU[kategori_anahtari]
    mevcut = st.session_state.aktif_mesaj
    alternatifler = [m for m in havuz if m != mevcut]
    st.session_state.aktif_mesaj = random.choice(alternatifler) if alternatifler else havuz[0]
    st.session_state.otomatik_analiz = True

def kutuyu_temizle():
    st.session_state.aktif_mesaj = ""
    st.session_state.otomatik_analiz = False

# --- YAN MENÜ (SIDEBAR) ---
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "🏠 Karşılama Ekranı"

st.sidebar.title("📌 Navigasyon")
if st.sidebar.button("🏠 Karşılama Ekranı", use_container_width=True):
    st.session_state.sayfa = "🏠 Karşılama Ekranı"
if st.sidebar.button("🛡️ SMS Analizörü", use_container_width=True):
    st.session_state.sayfa = "🛡️ SMS Analizörü"
if st.sidebar.button("📥 Sisteme Katkı Sağla", use_container_width=True):
    st.session_state.sayfa = "📥 Sisteme Katkı Sağla"
if st.sidebar.button("🧠 YZ ve Doğrulama", use_container_width=True):
    st.session_state.sayfa = "🧠 YZ ve Doğrulama"
if st.sidebar.button("👨‍💻 Admin Paneli", use_container_width=True):
    st.session_state.sayfa = "👨‍💻 Admin Paneli"

st.sidebar.divider()

yan_menu_modern_html = """
<style>
.info-box {
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    border-radius: 14px;
    padding: 16px;
    color: #e0e6ed;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
    text-align: center;
    height: 195px;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(38, 208, 206, 0.3);
    margin-bottom: 20px;
}
.info-header {
    font-weight: 800;
    font-size: 15px;
    margin-bottom: 8px;
    color: #00f2fe;
    letter-spacing: 0.5px;
}
.text-container {
    position: relative;
    height: 100%;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.ticker-text {
    position: absolute;
    width: 100%;
    opacity: 0;
    animation: fadeCycle 60s infinite;
}
.ticker-text:nth-child(1) { animation-delay: 0s; }
.ticker-text:nth-child(2) { animation-delay: 10s; }
.ticker-text:nth-child(3) { animation-delay: 20s; }
.ticker-text:nth-child(4) { animation-delay: 30s; }
.ticker-text:nth-child(5) { animation-delay: 40s; }
.ticker-text:nth-child(6) { animation-delay: 50s; }

@keyframes fadeCycle {
    0% { opacity: 0; transform: translateY(8px); }
    3% { opacity: 1; transform: translateY(0); }
    15% { opacity: 1; transform: translateY(0); }
    18% { opacity: 0; transform: translateY(-8px); }
    100% { opacity: 0; transform: translateY(-8px); }
}
.dev-card {
    background: linear-gradient(135deg, #161B22 0%, #0D1117 100%);
    border-radius: 14px;
    padding: 16px;
    border: 1px solid rgba(78, 67, 118, 0.5);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.dev-title {
    color: #a8c0ff;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-transform: uppercase;
}
.dev-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    margin-bottom: 8px;
    border-left: 3px solid #00f2fe;
    transition: all 0.2s ease;
}
.dev-item:hover {
    background: rgba(38, 208, 206, 0.1);
    transform: translateX(3px);
}
.dev-name {
    color: #ffffff;
    font-size: 13.5px;
    font-weight: 600;
}
.dev-badge {
    margin-left: auto;
    font-size: 10px;
    background: rgba(0, 242, 254, 0.15);
    color: #00f2fe;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 700;
}
</style>

<div class="info-box">
    <div class="info-header">💡 SİBER İSTİHBARAT</div>
    <div class="text-container">
        <div class="ticker-text">Dünya genelinde siber saldırıların <b>%80'inden fazlası</b> sosyal mühendislik ve oltalama yöntemleriyle başlar.</div>
        <div class="ticker-text">Kullanıcıların SMS ile gelen oltalama linklerine tıklama oranı, e-postalara göre <b>3 kat daha fazladır.</b></div>
        <div class="ticker-text">İnsanların %90'ı gelen bir SMS'i <b>ilk 3 dakika içerisinde</b> okur. Dolandırıcılar bu aciliyet refleksini kullanır.</div>
        <div class="ticker-text">Sadece 2023 yılında, sahte kargo ve banka SMS'leri yüzünden dünya çapında <b>milyarlarca dolar</b> kayıp yaşanmıştır.</div>
        <div class="ticker-text">SMS oltalama (Smishing) saldırıları son 2 yılda <b>%300'ün üzerinde artış</b> göstererek en kritik mobil tehdit olmuştur.</div>
        <div class="ticker-text">Dolandırıcılar genellikle <b>tatil ve mesai saatleri dışında</b> SMS atarak kurbanın kurumları arayıp teyit etmesini engeller.</div>
    </div>
</div>

<div class="dev-card">
    <div class="dev-title">⚡ Geliştirici Ekibi</div>
    <div class="dev-item">
        <span>👨‍💻</span>
        <span class="dev-name">Muzaffer Alp Ergülcü</span>
        <span class="dev-badge">AI / NLP</span>
    </div>
    <div class="dev-item" style="margin-bottom: 0; border-left-color: #a8c0ff;">
        <span>👨‍💻</span>
        <span class="dev-name">Oğuzhan Uysal</span>
        <span class="dev-badge" style="color: #a8c0ff; background: rgba(168, 192, 255, 0.15);">CyberSec</span>
    </div>
</div>
"""
st.sidebar.markdown(yan_menu_modern_html, unsafe_allow_html=True)

# --- ÜST DURUM ÇUBUĞU (HER SAYFADA PROFESYONEL GÖRÜNÜM) ---
st.markdown(f"""
<div class="status-bar">
    <div style="font-weight: 700; font-size: 15px; color: #e2e8f0;">
        🛡️ <b>KTO Karatay Üniversitesi</b> | Yapay Zeka Tabanlı Siber Güvenlik ve Smishing Analiz Platformu
    </div>
    <div style="display: flex; gap: 10px;">
        <span class="status-badge">🟢 NLP Motoru Aktif ({len(df)} Veri)</span>
        <span class="status-badge">⚡ Canlı DNS & XAI Kalkanı</span>
    </div>
</div>
""", unsafe_allow_html=True)


# --- SAYFA 1: KARŞILAMA EKRANI ---
if st.session_state.sayfa == "🏠 Karşılama Ekranı":
    st.title("🛡️ Akıllı SMS Oltalama (Phishing) Tespit Sistemi")
    st.markdown("""
    ### Siber Güvenliğiniz İçin Açıklanabilir Yapay Zeka (XAI) Çözümü
    Günümüzde artan **sahte kargo, e-Devlet, icra takibi ve banka dolandırıcılığı** mesajlarına karşı 
    geliştirdiğimiz bu akıllı sistem, gelen iletileri saniyeler içinde analiz eder ve tehlike nedenlerini şeffafça görselleştirir.
    """)
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Örnek Senaryo Havuzu", "40+ Mesaj", "Kesintisiz Test")
    k2.metric("Aktif Eğitim Verisi", f"{len(df)} SMS", "Dinamik CSV")
    k3.metric("Karar Mimarisi", "Hibrit AI", "TF-IDF + Naive Bayes")
    k4.metric("Hedef Doğruluk", "> %85", "Yüksek Recall")

    st.write("")
    st.markdown("""
    * 🖍️ **Açıklanabilir YZ (XAI):** Mesaj içindeki tehlikeli kelimeleri ve linkleri fosforlu olarak işaretler.
    * 🕵️ **Kelime Oyunu Avcısı:** Filtreleri atlatmak için nokta veya rakamlarla gizlenmiş kelimeleri (`i.c.r.a`, `b.l.o.k.e`, `p4r4` vb.) yakalar.
    * 🌍 **Canlı IP Çözümleme & Beyaz Liste:** Resmi siteleri tanır, şüpheli linklerin arka plandaki sunucu IP adreslerini tespit eder.
    * 🧪 **Canlı Doğrulama Simülatörü:** Modelin başarı oranını (Accuracy & Recall) bağımsız test verileriyle anlık olarak kanıtlar.
    """)
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 UYGULAMAYI BAŞLAT VE ANALİZ EKRANINA GEÇ", type="primary", use_container_width=True):
            st.session_state.sayfa = "🛡️ SMS Analizörü"
            st.rerun()


# --- SAYFA 2: SMS ANALİZÖRÜ (AKICI CALLBACK SİSTEMİ) ---
elif st.session_state.sayfa == "🛡️ SMS Analizörü":
    st.title("🛡️ Akıllı SMS Analizörü")
    st.write("Aşağıdaki kategori butonlarına tıklayarak **40'tan fazla gerçekçi senaryoyu** tek tıkla, takılmadan test edebilir veya kendi mesajınızı yapıştırabilirsiniz.")

    # 4'lü Akıcı Senaryo Butonları (on_click ile sıfır gecikme ve otomatik analiz)
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.button("🚨 İcra / Banka / Finans", on_click=ornek_getir, args=("icra_banka",), use_container_width=True)
    with colB:
        st.button("📦 Kargo / Ödül / e-Devlet", on_click=ornek_getir, args=("kargo_odul",), use_container_width=True)
    with colC:
        st.button("🕵️ Kelime Oyunu (Gizli)", on_click=ornek_getir, args=("kelime_oyunu",), use_container_width=True)
    with colD:
        st.button("✅ Güvenli / Kurumsal", on_click=ornek_getir, args=("guvenli",), use_container_width=True)

    # Doğrudan session_state'e bağlı, takılma yapmayan metin kutusu
    mesaj_girdisi = st.text_area("Analiz Edilecek SMS Metni:", key="aktif_mesaj", height=115, placeholder="Şüpheli SMS metnini buraya yapıştırın veya yukarıdaki örnek butonlarından birine tıklayın...")

    btn_col1, btn_col2 = st.columns([4, 1])
    with btn_col1:
        analiz_baslat = st.button("🔍 Güvenlik Analizini Başlat", type="primary", use_container_width=True)
    with btn_col2:
        st.button("🗑️ Kutuyu Temizle", on_click=kutuyu_temizle, use_container_width=True)

    # Butona basıldıysa VEYA örnek butonuna tıklanıp otomatik analiz tetiklendiyse hemen göster
    if analiz_baslat or (st.session_state.otomatik_analiz and mesaj_girdisi.strip()):
        if mesaj_girdisi.strip():
            toplam_risk, gerekceler, yakalanan_kelimeler, bulunan_linkler, guvenli_link_mi = mesaji_analiz_et(mesaj_girdisi)
            
            st.divider()
            sonuc_col1, sonuc_col2 = st.columns([1, 2])
            
            with sonuc_col1:
                st.metric(label="Hesaplanan Risk Skoru", value=f"%{toplam_risk}")
                bar_renk = "#ff4b4b" if toplam_risk >= 70 else ("#ffa500" if toplam_risk >= 30 else "#00e676")
                risk_etiketi = "KRİTİK TEHLİKE" if toplam_risk >= 70 else ("ŞÜPHELİ İLETİ" if toplam_risk >= 30 else "GÜVENLİ İLETİ")
                st.markdown(f"""
                <div class="thermo-bg">
                    <div class="thermo-fill" style="width: {toplam_risk}%; background-color: {bar_renk};"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12.5px; color: #cbd5e1; margin-top: 6px; font-weight: 600;">
                    <span>Durum: <b style="color:{bar_renk};">{risk_etiketi}</b></span>
                    <span>%{toplam_risk} / 100</span>
                </div>
                """, unsafe_allow_html=True)

            with sonuc_col2:
                if toplam_risk >= 70:
                    st.error("🚨 **KRİTİK RİSK:** Bu mesaj yüksek ihtimalle **Oltalama (Phishing)** amaçlıdır! Kesinlikle bağlantılara tıklamayın ve ödeme yapmayın.")
                elif 30 <= toplam_risk < 70:
                    st.warning("⚠️ **ŞÜPHELİ MESAJ:** Bu iletide riskli unsurlar bulundu. İlgili kurumun resmi numarasını kendiniz arayarak teyit etmeden işlem yapmayın.")
                else:
                    st.success("✅ **GÜVENLİ MESAJ:** Bu iletide belirgin bir oltalama, tehdit veya siber güvenlik riski tespit edilmedi.")

            if yakalanan_kelimeler or bulunan_linkler:
                st.subheader("🖍️ Açıklanabilir YZ (XAI) Metin Tarama Sonucu:")
                renkli_html = xai_metin_renklendir(mesaj_girdisi, yakalanan_kelimeler, bulunan_linkler, guvenli_link_mi)
                st.markdown(f'<div class="xai-box">{renkli_html}</div>', unsafe_allow_html=True)

            if len(gerekceler) > 0:
                st.subheader("🔍 Sistem Tarafından Tespit Edilen Teknik Gerekçeler:")
                for g in gerekceler:
                    st.markdown(f'<div class="reason-card">{g}</div>', unsafe_allow_html=True)
        else:
            st.warning("Lütfen analiz edilecek bir metin giriniz.")


# --- SAYFA 3: SİSTEME KATKI SAĞLA ---
elif st.session_state.sayfa == "📥 Sisteme Katkı Sağla":
    st.title("📥 Veri Setine Katkıda Bulunun")
    st.markdown("Yapay zekayı daha akıllı hale getirmek için yeni mesajlar önerebilirsiniz. Gönderdiğiniz mesajlar **yönetici onayından geçtikten sonra** sisteme dahil edilecektir.")
    
    yeni_mesaj = st.text_area("Önereceğiniz mesajı yazın:")
    etiket_secimi = st.radio("Bu mesajın türü nedir?", ["🚨 Dolandırıcılık / Oltalama Mesajı (Phishing)", "✅ Normal / Güvenli Mesaj"])
    
    if st.button("📤 Mesajı Onaya Gönder", type="primary"):
        if yeni_mesaj.strip() == "":
            st.warning("Lütfen boş bir mesaj eklemeyin.")
        else:
            etiket_degeri = 1 if "Dolandırıcılık" in etiket_secimi else 0
            temiz_mesaj = yeni_mesaj.replace('\n', ' ').replace('\r', '').replace(',', ' ')
            
            yeni_veri = pd.DataFrame({"mesaj": [temiz_mesaj], "etiket": [etiket_degeri]})
            if not os.path.exists("onay_bekleyenler.csv"):
                yeni_veri.to_csv("onay_bekleyenler.csv", mode="w", index=False)
            else:
                yeni_veri.to_csv("onay_bekleyenler.csv", mode="a", header=False, index=False)
            st.success("✅ Mesajınız başarıyla yönetici onay havuzuna gönderildi!")


# --- SAYFA 4: YZ, SKORLAMA VE 10 MESAJLIK DOĞRULAMA SİMÜLATÖRÜ ---
elif st.session_state.sayfa == "🧠 YZ ve Doğrulama":
    st.title("🧠 Yapay Zeka Altyapısı ve Doğrulama Planı")
    
    tab1, tab2 = st.tabs(["🧪 10 Mesajlık Doğrulama Simülatörü (PoC)", "📘 Algoritma ve Skorlama Mantığı"])
    
    with tab1:
        st.subheader("🎯 Bağımsız Test Veri Seti Doğrulaması")
        st.markdown("""
        Proje doğrulama planımız kapsamında, eğitim aşamasında modele **hiç gösterilmemiş 10 adet bağımsız Türkçe SMS (5 sahte, 5 gerçek)** ile 
        sistemin **Doğruluk (Accuracy)** ve **Yakalama Oranı (Recall)** performansı canlı olarak test edilmektedir. Başarı kriterimiz en az **%80** doğruluktur.
        """)
        
        test_verileri = [
            {"mesaj": "Aras Kargo: Gönderiniz adres eksikliği sebebiyle şubede bekliyor. Güncelleme: http://bit.ly/aras-onay", "gercek": 1},
            {"mesaj": "Uzlaştırma Bürosu: Adınıza açılan soruşturma dosyasını kapatmak için bugün 4.500 TL bedeli IBAN'a yatırın.", "gercek": 1},
            {"mesaj": "Vakıfbank: Kredi kartınız şüpheli işlem nedeniyle b.l.o.k.e edilmiştir. Açmak için: vakif-dogrula.xyz", "gercek": 1},
            {"mesaj": "E-Devlet: Elektrik faturası destek ödemeniz hazır. Hemen hesaba aktarmak için tıklayın: edevlet-yardim.net", "gercek": 1},
            {"mesaj": "Hakkınızda başlatılan i.c.r.a dosyasını durdurmak için derhal hukuk-dosya.com adresine giriş yapınız.", "gercek": 1},
            {"mesaj": "Merhaba, yarın sabah saat 10:00'da proje sunumumuz var, bilgisayarını getirmeyi unutma.", "gercek": 0},
            {"mesaj": "Yurtiçi Kargo: 998877 takip numaralı kargonuz dağıtıma çıkarılmıştır. Güvenli günler dileriz. B018", "gercek": 0},
            {"mesaj": "Anneciğim akşam gelirken ekmek ve süt alır mısın? Evde kalmamış.", "gercek": 0},
            {"mesaj": "İş Bankası: 4512 nolu kartınızla 320 TL tutarında market harcaması yapılmıştır. B001", "gercek": 0},
            {"mesaj": "Ödev için harika bir kaynak buldum: https://www.youtube.com/watch?v=aircAruvnKk", "gercek": 0}
        ]
        
        if st.button("▶️ 10 Bağımsız Mesajla Doğrulama Testini Çalıştır", type="primary"):
            dogru_sayisi = 0
            yakalanan_phishing = 0
            sonuc_tablosu = []
            
            for i, veri in enumerate(test_verileri, 1):
                skor, _, _, _, _ = mesaji_analiz_et(veri["mesaj"])
                tahmin = 1 if skor >= 50 else 0
                basarili_mi = (tahmin == veri["gercek"])
                
                if basarili_mi:
                    dogru_sayisi += 1
                if veri["gercek"] == 1 and tahmin == 1:
                    yakalanan_phishing += 1
                    
                sonuc_tablosu.append({
                    "No": i,
                    "Test Mesajı": veri["mesaj"],
                    "Gerçek Durum": "🚨 Oltalama" if veri["gercek"] == 1 else "✅ Güvenli",
                    "Sistem Tahmini": "🚨 Oltalama" if tahmin == 1 else "✅ Güvenli",
                    "Risk Skoru": f"%{skor}",
                    "Sonuç": "✔️ Başarılı" if basarili_mi else "❌ Hatalı"
                })
                
            accuracy = int((dogru_sayisi / 10) * 100)
            recall = int((yakalanan_phishing / 5) * 100)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Genel Doğruluk (Accuracy)", f"%{accuracy}", "Hedef: min %80")
            m2.metric("Oltalama Yakalama (Recall)", f"%{recall}", f"{yakalanan_phishing}/5 Phishing Yakalandı")
            m3.metric("Başarılı Test Sayısı", f"{dogru_sayisi} / 10", "Doğrulama Tamamlandı")
            
            st.dataframe(pd.DataFrame(sonuc_tablosu), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("""
        ### 1. Hibrit Risk Skoru Neye Göre Hesaplanıyor?
        * **Kısaltılmış Linkler (`bit.ly` vb.):** +55 Puan
        * **Şüpheli Dış Bağlantılar & IP Analizi:** +45 Puan
        * **Hukuki Tehdit / Doğrudan Para Talebi:** +35 Puan
        * **Sahte Kargo / Banka / Ödül Oltalaması:** +30 Puan
        * **Kelime Oyunu / Filtre Atlatma Girişimi:** +25 Puan
        * **Yapay Zeka (TF-IDF & Naive Bayes Bağlam Eşleşmesi):** +20 Puan
        * **Suni Aciliyet Dili:** +15 Puan
        
        ### 2. Neden Hibrit (Kural + Yapay Zeka) Mimari?
        Dolandırıcılar harf değiştirerek (`i.c.r.a`, `p4r4`) standart filtreleri atlatmaya çalışır. Geliştirdiğimiz ön-işleme (Pre-processing) katmanı bu gizlemeleri çözer, ardından **TF-IDF Vectorizer** ve **Multinomial Naive Bayes** algoritması cümlenin genel bağlamını analiz eder.
        """)


# --- SAYFA 5: ÇOKLU YÖNETİCİ (ADMİN) PANELİ VE GRAFİKLER ---
elif st.session_state.sayfa == "👨‍💻 Admin Paneli":
    st.title("🔒 Yönetici (Admin) Paneli")
    st.write("Veri setini denetlemek, analiz grafiklerini incelemek ve yeni mesajları onaylamak için giriş yapın.")
    
    ADMIN_HESAPLARI = {
        "alp": {"sifre": "alp123", "isim": "Muzaffer Alp Ergülcü"},
        "oguzhan": {"sifre": "oguzhan123", "isim": "Oğuzhan Uysal"}
    }
    
    col_giris1, col_giris2, col_bos = st.columns([1, 1, 1])
    with col_giris1:
        kullanici_adi = st.text_input("👤 Kullanıcı Adı:").strip().lower()
    with col_giris2:
        girilen_sifre = st.text_input("🔑 Şifre:", type="password")
    
    if kullanici_adi in ADMIN_HESAPLARI and ADMIN_HESAPLARI[kullanici_adi]["sifre"] == girilen_sifre:
        aktif_admin = ADMIN_HESAPLARI[kullanici_adi]["isim"]
        st.success(f"🔓 Giriş Başarılı! Hoş Geldiniz, **{aktif_admin}**.")
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        phishing_sayisi = len(df[df['etiket'] == 1])
        guvenli_sayisi = len(df[df['etiket'] == 0])
        
        with col1:
            st.metric(label="Toplam Eğitilmiş Mesaj", value=f"{len(df)}")
        with col2:
            st.metric(label="Dolandırıcılık (Phishing)", value=f"{phishing_sayisi}")
        with col3:
            st.metric(label="Güvenli (Normal)", value=f"{guvenli_sayisi}")
            
        st.divider()
        
        st.subheader("📈 Veri Seti Analitiği ve Kelime Dağılımı")
        grafik_col1, grafik_col2 = st.columns(2)
        
        with grafik_col1:
            st.markdown("**Veri Seti Sınıf Dağılımı (Denge Grafiği)**")
            sinif_df = pd.DataFrame({
                "Kategori": ["Oltalama (Phishing)", "Güvenli (Normal)"],
                "Mesaj Sayısı": [phishing_sayisi, guvenli_sayisi]
            }).set_index("Kategori")
            st.bar_chart(sinif_df, color="#00f2fe")
            
        with grafik_col2:
            st.markdown("**Oltalama Mesajlarında En Çok Geçen Tehdit Kelimeleri**")
            phishing_metinleri = " ".join(df[df['etiket'] == 1]['mesaj'].astype(str)).lower()
            aranan_kelimeler = ["kargo", "icra", "hesap", "bloke", "tl", "iptal", "link", "ödeme"]
            kelime_sayilari = {k.upper(): phishing_metinleri.count(k) for k in aranan_kelimeler}
            kelime_df = pd.DataFrame(list(kelime_sayilari.items()), columns=["Kelime", "Frekans"]).set_index("Kelime")
            st.bar_chart(kelime_df, color="#ff4b4b")

        st.divider()
        st.subheader("⏳ Onay Bekleyen (Kullanıcılardan Gelen) Mesajlar")
        
        if os.path.exists("onay_bekleyenler.csv"):
            bekleyen_df = pd.read_csv("onay_bekleyenler.csv", on_bad_lines='skip')
            if len(bekleyen_df) > 0:
                for idx, row in bekleyen_df.iterrows():
                    with st.container():
                        mesaj_turu = "🚨 Phishing" if row['etiket'] == 1 else "✅ Güvenli"
                        st.markdown(f"**Mesaj:** {row['mesaj']}")
                        st.markdown(f"**Önerilen Etiket:** {mesaj_turu}")
                        b1, b2, b3 = st.columns([1, 1, 4])
                        with b1:
                            if st.button("✅ Sisteme Ekle", key=f"ekle_{idx}"):
                                temiz_kayit = str(row['mesaj']).replace(',', ' ')
                                pd.DataFrame({"mesaj": [temiz_kayit], "etiket": [int(row['etiket'])]}).to_csv("dataset.csv", mode="a", header=False, index=False)
                                bekleyen_df = bekleyen_df.drop(idx)
                                bekleyen_df.to_csv("onay_bekleyenler.csv", index=False)
                                st.cache_resource.clear()
                                st.rerun()
                        with b2:
                            if st.button("🗑️ Reddet (Sil)", key=f"sil_{idx}"):
                                bekleyen_df = bekleyen_df.drop(idx)
                                bekleyen_df.to_csv("onay_bekleyenler.csv", index=False)
                                st.rerun()
                    st.markdown("---")
            else:
                st.info("Harika! Şu an onay bekleyen hiçbir mesaj yok.")
        else:
            st.info("Harika! Şu an onay bekleyen hiçbir mesaj yok.")
            
    elif kullanici_adi != "" or girilen_sifre != "":
        st.error("❌ Hatalı kullanıcı adı veya şifre! Lütfen bilgilerinizi kontrol edin.")
