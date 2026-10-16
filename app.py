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

# --- 2. SAYFA AYARLARI VE PROFESYONEL ARAYÜZ CSS ---
st.set_page_config(page_title="SMS Güvenlik Asistanı", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at top right, #131B2E 0%, #0B0F19 60%, #070A10 100%);
        color: #F0F4F8;
    }
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
    div.stButton > button:first-child {
        border-radius: 12px;
        font-weight: 600;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: #ffffff;
        transition: all 0.25s ease;
        border: 1px solid rgba(0, 242, 254, 0.2);
        padding: 0.55rem 1rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 22px rgba(0, 242, 254, 0.35);
        border-color: #00f2fe;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);
        font-size: 16px;
        font-weight: 700;
    }
    div[data-testid="metric-container"] {
        background: rgba(22, 27, 34, 0.65);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 242, 254, 0.2);
        padding: 18px 22px;
        border-radius: 16px;
    }
    .stTextArea textarea, .stTextInput input {
        border-radius: 14px !important;
        border: 1px solid rgba(0, 242, 254, 0.25) !important;
        background-color: rgba(17, 22, 29, 0.85) !important;
        color: #FFFFFF !important;
        font-size: 15px !important;
        padding: 14px !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0D1117 0%, #111827 100%);
        border-right: 1px solid rgba(0, 242, 254, 0.12);
    }
    .highlight-box {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(0, 242, 254, 0.25);
        border-radius: 14px;
        padding: 18px;
        font-size: 15.5px;
        line-height: 1.8;
        margin-top: 10px;
        margin-bottom: 18px;
    }
    .danger-tag {
        background-color: rgba(255, 75, 75, 0.25);
        color: #ff8080;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(255, 75, 75, 0.65);
        font-weight: 700;
    }
    .safe-tag {
        background-color: rgba(0, 242, 254, 0.15);
        color: #00f2fe;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(0, 242, 254, 0.45);
        font-weight: 700;
    }
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

# --- 3. MODEL YÜKLEME ---
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

# --- 4. SÖZLÜKLER VE KONTROL FONKSİYONLARI ---
KATEGORILER = {
    "kargo": ["ptt", "mng", "yurtiçi", "yurtici", "aras", "teslim edilemedi", "adres hatası", "adres yetersizliği", "kargonuz", "gönderiniz", "iade", "gümrük"],
    "icra_hukuk": ["icra", "dava", "uzlaştırma", "uzlastirma", "adliye", "sevk", "hapis", "tazminat", "savcılık", "ceza", "hukuk", "bahis", "taciz", "soruşturma", "uyap"],
    "banka_finans": ["bloke", "kredi kartı", "hesabınıza", "şüpheli işlem", "supheli", "iptal", "ziraat", "garanti", "akbank", "papara", "aidat", "binance"],
    "odul_yardim": ["tebrikler", "hediye", "kazandınız", "kazandiniz", "askıda fatura", "ikramiye", "çekiliş", "bonus", "kupon", "destek paketi"],
    "para_talebi": ["iban", "hesaba yatır", "ödeme", "odeme", "bedeli", "masraf", "para transferi", "borcunuzu"],
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

def metni_isaretle(metin, yakalanan_kelimeler, linkler, guvenli_mi):
    islenmis = metin
    for link in set(linkler):
        stil = "safe-tag" if guvenli_mi else "danger-tag"
        islenmis = islenmis.replace(link, f'<span class="{stil}">🔗 {link}</span>')
    
    for kelime in sorted(set(yakalanan_kelimeler), key=len, reverse=True):
        pattern = re.compile(r'\b' + re.escape(kelime) + r'\b', re.IGNORECASE)
        islenmis = pattern.sub(lambda m: f'<span class="danger-tag">{m.group(0)}</span>', islenmis)
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
                gerekceler.append(f"🌐 **Güvenilir Bağlantı:** `{domain}` adresi resmi ve güvenli bir internet sitesidir.")
            else:
                tehlikeli_link_var = True
                try:
                    ip_adresi = socket.gethostbyname(domain)
                    ip_detay = f"Sunucu IP: {ip_adresi}"
                except Exception:
                    ip_detay = "Sunucu adresi doğrulanamadı"

                if any(kisaltma in domain.lower() for kisaltma in KISALTILMIS_LINKLER):
                    gerekceler.append(f"🔗 **Gizlenmiş Link:** Gerçek adresi saklayan şüpheli kısaltma (`{domain}`) kullanılmış! ({ip_detay})")
                    risk_skoru += 55
                else:
                    gerekceler.append(f"🔗 **Bilinmeyen Bağlantı:** Güvenliği onaylanmamış bir internet adresine (`{domain}`) yönlendiriyor. ({ip_detay})")
                    risk_skoru += 45

    def kelime_ara(kelime_listesi, metin_kontrol):
        bulundu = False
        for k in kelime_listesi:
            desen = r'\b' + re.escape(k) + r'\b'
            if re.search(desen, metin_kontrol, re.IGNORECASE):
                bulundu = True
                yakalanan_kelimeler.append(k)
        return bulundu

    for kategori, kelimeler in KATEGORILER.items():
        kategori_yakalandi = kelime_ara(kelimeler, mesaj_lower)
        if not kategori_yakalandi:
            if kelime_ara(kelimeler, cozulmus_mesaj):
                kategori_yakalandi = True
                kelime_oyunu_var = True

        if kategori_yakalandi:
            if kategori == "icra_hukuk":
                gerekceler.append("⚖️ **Korkutma ve Tehdit Dili:** İcra, dava veya ceza gibi korkutucu kelimelerle panik yaratılmak isteniyor.")
                risk_skoru += 35
            elif kategori == "banka_finans":
                gerekceler.append("🏦 **Sahte Banka Uyarısı:** Hesap blokesi veya kart sorunu bahanesiyle kişisel bilgileriniz isteniyor.")
                risk_skoru += 30
            elif kategori == "kargo":
                gerekceler.append("📦 **Sahte Kargo Mesajı:** Teslimat sorunu bahanesiyle dolandırıcılık sitelerine yönlendiriliyor.")
                risk_skoru += 30
            elif kategori == "odul_yardim":
                gerekceler.append("🎁 **Bedava Hediye Tuzağı:** Gerçek olamayacak kadar cazip hediye veya yardım vaadiyle kandırma girişimi.")
                risk_skoru += 30
            elif kategori == "para_talebi":
                gerekceler.append("💸 **Doğrudan Para İsteme:** Mesajda açıkça para, borç ödemesi veya IBAN transferi talep ediliyor.")
                risk_skoru += 35
            elif kategori == "aciliyet":
                gerekceler.append("⏱️ **Acele Ettirme Taktiği:** Düşünmenize izin vermeden hemen işlem yapmanız için baskı kuruluyor.")
                risk_skoru += 15

    if re.search(r'\btl\b', mesaj_lower) or re.search(r'\btl\b', cozulmus_mesaj):
        yakalanan_kelimeler.append("tl")
        if not any("Para İsteme" in g for g in gerekceler):
            gerekceler.append("💸 **Para Birimi Tespiti:** Mesajda para miktarı veya Türk Lirası (TL) geçmektedir.")
            risk_skoru += 15

    if kelime_oyunu_var:
        gerekceler.append("🕵️ **Gizlenmiş Kelime Tespiti:** Güvenlik sistemlerini atlatmak için kelimelerin arasına nokta veya işaretler konulmuş!")
        risk_skoru += 25

    ml_tahmin = model.predict([cozulmus_mesaj])[0]
    if ml_tahmin == 1:
        if guvenli_link_var and not tehlikeli_link_var and risk_skoru == 0:
            gerekceler.append("✅ Bu mesaj resmi bir internet sitesi içerdiği için güvenli kabul edildi.")
            risk_skoru = 0
        else:
            gerekceler.append("⚠️ Bu mesajın yazılış tarzı daha önce tespit edilen dolandırıcılık mesajlarıyla büyük benzerlik gösteriyor.")
            risk_skoru += 20

    toplam_risk = min(risk_skoru, 100)
    return toplam_risk, gerekceler, yakalanan_kelimeler, bulunan_linkler, (guvenli_link_var and not tehlikeli_link_var)

# --- 5. ÖRNEK SEÇİM CALLBACK FONKSİYONLARI ---
if "aktif_mesaj" not in st.session_state:
    st.session_state.aktif_mesaj = ""
if "otomatik_analiz" not in st.session_state:
    st.session_state.otomatik_analiz = False

ORNEK_HAVUZU = {
    "icra_banka": [
        "Sn. Vatandaş, hakkınızda açılacak cinsel taciz davası bulunmaktadır. Uzlaştırma bedeli olan 5000 TL'yi hemen hesaba yatırın: hukuk-odeme.com",
        "Ziraat Bankası: Hesabınızdan şüpheli işlem tespit edilmiştir. Bloke konulmaması için derhal doğrulayın: ziraat-guvenlik.xyz",
        "Hukuk Bürosu: Hakkınızda başlatılan icra takibini durdurmak için bugün mesai bitimine kadar 3.850 TL dosya masrafını IBAN'a gönderin.",
        "Garanti BBVA: Mobil şube erişiminiz güvenlik nedeniyle kısıtlanmıştır. Kimlik onayı için tıklayın: http://tinyurl.com/garanti-onay",
        "Ağır Ceza Mahkemesi: Yasa dışı bahis soruşturması kapsamında adınıza ceza kesilmiştir. Evrakları görmek için: uyap-vatandas.net"
    ],
    "kargo_odul": [
        "PTT Kargo: Gönderiniz adres yetersizliği nedeniyle teslim edilemedi. Adresinizi güncellemek için tıklayın: http://bit.ly/ptt-guncelle",
        "MNG Kargo: Dağıtıma çıkan 482910 nolu kargonuz iade sürecine girmiştir. Tekrar dağıtım talebi için: mng-teslimat.xyz",
        "E-Devlet Kapısı: Aile destek paketi kapsamında 4.500 TL yardım başvurunuz onaylandı. Hesaba çekmek için: edevlet-destek.org",
        "Tebrikler! Trendyol çekilişinden 10.000 TL değerinde hediye çeki kazandınız. Süre bitiyor, hemen alın: trendyol-ikramiye.net",
        "Yurtiçi Kargo: Paketiniz gümrük vergisi ödenmediği için depoda bekletiliyor. 85 TL ödeme yapmak için: yurtici-gumruk.com"
    ],
    "kelime_oyunu": [
        "Sayin musteri hesabiniza b.l.o.k.e konulmustur. Acil islem icin tiklayin: tinyurl.com/banka-onay",
        "Hakkınızda i.c.r.a takibi başlatılmıştır. Mağdur olmamak için bugün e-devlet-sorgu.xyz adresine giriniz.",
        "Uzlastirma burosu: d.a.v.a dosyanizin kapanmasi icin 6000 TL p4r4 transferini hemen yapiniz: uzlasma-merkezi.com",
        "PTT Kargo: K4rgonuz adres hatasi nedeniyle t.e.s.l.i.m edilemedi. Hemen tiklayin: bit.ly/kargo-takip"
    ],
    "guvenli": [
        "Yarın saat 14:00'te proje toplantımız var, lütfen gecikmeyin. İyi çalışmalar.",
        "Şu faydalı eğitim videosuna mutlaka baksana: https://www.youtube.com/watch?v=aircAruvnKk",
        "Ziraat Bankası: 4821 nolu kartınızla 340,00 TL tutarında market alışverişi yapılmıştır. B001",
        "Yurtiçi Kargo: 84920192 takip numaralı gönderiniz teslim edilmek üzere çıkarılmıştır. B018",
        "Kanka akşam halı saha maçına geliyorsun değil mi? Kramponları unutma."
    ]
}

def ornek_getir(kategori_anahtari):
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

st.sidebar.title("📌 Menü")
if st.sidebar.button("🏠 Ana Sayfa", use_container_width=True):
    st.session_state.sayfa = "🏠 Karşılama Ekranı"
if st.sidebar.button("🛡️ SMS Kontrol Aracı", use_container_width=True):
    st.session_state.sayfa = "🛡️ SMS Analizörü"
if st.sidebar.button("📥 Mesaj Öner", use_container_width=True):
    st.session_state.sayfa = "📥 Sisteme Katkı Sağla"
if st.sidebar.button("🧠 Sistem Nasıl Çalışır?", use_container_width=True):
    st.session_state.sayfa = "🧠 YZ ve Doğrulama"
if st.sidebar.button("👨‍💻 Yönetici Paneli", use_container_width=True):
    st.session_state.sayfa = "👨‍💻 Admin Paneli"

st.sidebar.divider()

yan_menu_modern_html = """
<style>
.info-box {
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    border-radius: 14px;
    padding: 16px;
    color: #e0e6ed;
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
}
.dev-title {
    color: #a8c0ff;
    font-size: 13px;
    font-weight: 800;
    margin-bottom: 12px;
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
    <div class="info-header">💡 Biliyor musunuz?</div>
    <div class="text-container">
        <div class="ticker-text">Siber saldırıların <b>%80'inden fazlası</b> oltalama (phishing) yöntemleriyle başlar.</div>
        <div class="ticker-text">SMS ile gelen şüpheli linklere tıklama oranı, e-postalara göre <b>3 kat daha fazladır.</b></div>
        <div class="ticker-text">İnsanların %90'ı gelen bir SMS'i <b>ilk 3 dakika içinde</b> okur; dolandırıcılar bunu kullanır.</div>
        <div class="ticker-text">Sahte kargo ve banka SMS'leri yüzünden her yıl <b>milyarlarca dolar</b> kaybedilmektedir.</div>
        <div class="ticker-text">Dolandırıcılar genellikle <b>tatil ve mesai dışı saatlerde</b> mesaj atarak teyit etmenizi engeller.</div>
        <div class="ticker-text">Resmi kurumlar asla SMS içinde doğrudan şifre veya para transferi istemez.</div>
    </div>
</div>

<div class="dev-card">
    <div class="dev-title">⚡ Geliştirici Ekibi</div>
    <div class="dev-item">
        <span>👨‍💻</span>
        <span class="dev-name">Muzaffer Alp Ergülcü</span>
        <span class="dev-badge">Yazılım</span>
    </div>
    <div class="dev-item" style="margin-bottom: 0; border-left-color: #a8c0ff;">
        <span>👨‍💻</span>
        <span class="dev-name">Oğuzhan Uysal</span>
        <span class="dev-badge" style="color: #a8c0ff; background: rgba(168, 192, 255, 0.15);">Güvenlik</span>
    </div>
</div>
"""
st.sidebar.markdown(yan_menu_modern_html, unsafe_allow_html=True)

# ÜST DURUM ÇUBUĞU
st.markdown(f"""
<div class="status-bar">
    <div style="font-weight: 700; font-size: 14px; color: #e2e8f0;">
        🛡️ <b>KTO Karatay Üniversitesi</b> | SMS Güvenlik Asistanı
    </div>
    <div style="display: flex; gap: 10px;">
        <span class="status-badge">🟢 Sistem Aktif ({len(df)} Kayıt)</span>
        <span class="status-badge">⚡ Hızlı Tarama Korunuyor</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SAYFA 1: ANA SAYFA ---
if st.session_state.sayfa == "🏠 Karşılama Ekranı":
    st.title("🛡️ SMS Güvenlik Asistanı")
    st.markdown("""
    ### Telefonunuza Gelen O Mesaj Gerçek mi, Tuzak mı?
    Günümüzde telefonlarımıza sürekli gelen **sahte kargo, ödül, e-Devlet veya icra** mesajları hayatımızı tehdit ediyor. 
    Bu uygulama sayesinde şüpheli mesajları anında test edebilir, dolandırıcıların tuzaklarına karşı güvende kalabilirsiniz.
    """)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Test Senaryosu", "40+ Çeşit", "Farklı Örnekler")
    k2.metric("Koruma Seviyesi", "Yüksek", "Anlık Tarama")
    k3.metric("Kullanım Amacı", "Farkındalık", "Herkes İçin Kolay")

    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 HEMEN MESAJ TEST ET", type="primary", use_container_width=True):
            st.session_state.sayfa = "🛡️ SMS Analizörü"
            st.rerun()

# --- SAYFA 2: SMS KONTROL ARACI ---
elif st.session_state.sayfa == "🛡️ SMS Analizörü":
    st.title("🛡️ SMS Güvenlik Kontrolü")
    st.write("Merak ettiğiniz mesajı kutuya yapıştırın ya da aşağıdaki örnek test butonlarına tıklayarak sistemin nasıl çalıştığını görün.")

    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.button("🚨 İcra / Banka Tuzağı", on_click=ornek_getir, args=("icra_banka",), use_container_width=True)
    with colB:
        st.button("📦 Sahte Kargo / Ödül", on_click=ornek_getir, args=("kargo_odul",), use_container_width=True)
    with colC:
        st.button("🕵️ Gizlenmiş Kelime", on_click=ornek_getir, args=("kelime_oyunu",), use_container_width=True)
    with colD:
        st.button("✅ Güvenli Kurum Mesajı", on_click=ornek_getir, args=("guvenli",), use_container_width=True)

    mesaj_girdisi = st.text_area("Kontrol Edilecek SMS Metni:", key="aktif_mesaj", height=115, placeholder="Buraya test etmek istediğiniz mesajı yazın veya yapıştırın...")

    btn_col1, btn_col2 = st.columns([4, 1])
    with btn_col1:
        analiz_baslat = st.button("🔍 Mesajı Güvenli mi Diye Kontrol Et", type="primary", use_container_width=True)
    with btn_col2:
        st.button("🗑️ Temizle", on_click=kutuyu_temizle, use_container_width=True)

    if analiz_baslat or (st.session_state.otomatik_analiz and mesaj_girdisi.strip()):
        if mesaj_girdisi.strip():
            toplam_risk, gerekceler, yakalanan_kelimeler, bulunan_linkler, guvenli_link_mi = mesaji_analiz_et(mesaj_girdisi)
            
            st.divider()
            sonuc_col1, sonuc_col2 = st.columns([1, 2])
            
            with sonuc_col1:
                st.metric(label="Risk Oranı", value=f"%{toplam_risk}")
                bar_renk = "#ff4b4b" if toplam_risk >= 70 else ("#ffa500" if toplam_risk >= 30 else "#00e676")
                risk_metni = "TEHLİKELİ" if toplam_risk >= 70 else ("ŞÜPHELİ" if toplam_risk >= 30 else "GÜVENLİ")
                st.markdown(f"""
                <div class="thermo-bg">
                    <div class="thermo-fill" style="width: {toplam_risk}%; background-color: {bar_renk};"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12.5px; color: #cbd5e1; margin-top: 6px; font-weight: 600;">
                    <span>Durum: <b style="color:{bar_renk};">{risk_metni}</b></span>
                    <span>%{toplam_risk}</span>
                </div>
                """, unsafe_allow_html=True)

            with sonuc_col2:
                if toplam_risk >= 70:
                    st.error("🚨 **DİKKAT! Bu mesaj bir dolandırıcılık tuzağıdır.** Kesinlikle içindeki linke tıklamayın, para göndermeyin ve kişisel bilgilerinizi vermeyin.")
                elif 30 <= toplam_risk < 70:
                    st.warning("⚠️ **ŞÜPHELİ DURUM!** Bu mesajda tehlikeli işaretler var. Kurumu kendi resmi telefonundan arayıp teyit etmeden adım atmayın.")
                else:
                    st.success("✅ **GÖRÜNÜŞE GÖRE GÜVENLİ.** Bu mesajda herhangi bir dolandırıcılık izine rastlanmadı.")

            if yakalanan_kelimeler or bulunan_linkler:
                st.subheader("🖍️ Mesajda Tespit Edilen Riskli Kelimeler:")
                isaretlenmis_metin = metni_isaretle(mesaj_girdisi, yakalanan_kelimeler, bulunan_linkler, guvenli_link_mi)
                st.markdown(f'<div class="highlight-box">{isaretlenmis_metin}</div>', unsafe_allow_html=True)

            if len(gerekceler) > 0:
                st.subheader("🔍 Bu Sonuca Neden Vardık?:")
                for g in gerekceler:
                    st.markdown(f'<div class="reason-card">{g}</div>', unsafe_allow_html=True)
        else:
            st.warning("Lütfen kontrol edilecek bir mesaj yazın.")

# --- SAYFA 3: MESAJ ÖNER ---
elif st.session_state.sayfa == "📥 Sisteme Katkı Sağla":
    st.title("📥 Yeni Mesaj Önerin")
    st.markdown("Bildiğiniz yeni bir dolandırıcılık mesajı veya güvenli bir örnek varsa buraya yazarak sistemin gelişimine katkıda bulunabilirsiniz.")
    
    yeni_mesaj = st.text_area("Önermek istediğiniz SMS metni:")
    etiket_secimi = st.radio("Bu mesajın türü nedir?", ["🚨 Dolandırıcılık / Tuzak Mesaj", "✅ Normal / Güvenli Mesaj"])
    
    if st.button("📤 İncelemeye Gönder", type="primary"):
        if yeni_mesaj.strip() == "":
            st.warning("Lütfen boş bir mesaj göndermeyin.")
        else:
            etiket_degeri = 1 if "Dolandırıcılık" in etiket_secimi else 0
            temiz_mesaj = yeni_mesaj.replace('\n', ' ').replace('\r', '').replace(',', ' ')
            
            yeni_veri = pd.DataFrame({"mesaj": [temiz_mesaj], "etiket": [etiket_degeri]})
            if not os.path.exists("onay_bekleyenler.csv"):
                yeni_veri.to_csv("onay_bekleyenler.csv", mode="w", index=False)
            else:
                yeni_veri.to_csv("onay_bekleyenler.csv", mode="a", header=False, index=False)
            st.success("✅ Öneriniz başarıyla yönetici onayına gönderildi. Teşekkürler!")

# --- SAYFA 4: SİSTEM NASIL ÇALIŞIR ---
elif st.session_state.sayfa == "🧠 YZ ve Doğrulama":
    st.title("🧠 Sistem Nasıl Çalışıyor?")
    
    tab1, tab2 = st.tabs(["🧪 Test ve Başarı Raporu", "📘 Basit Çalışma Mantığı"])
    
    with tab1:
        st.subheader("🎯 Sistem Doğruluk Testi")
        st.markdown("Sistemin ne kadar doğru sonuç verdiğini görmek için önceden hazırlanmış 10 farklı örnek testi anında çalıştırabilirsiniz.")
        
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
        
        if st.button("▶️ 10 Testi Otomatik Çalıştır", type="primary"):
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
                    "Gerçek Durum": "🚨 Tuzak" if veri["gercek"] == 1 else "✅ Güvenli",
                    "Sistem Kararı": "🚨 Tuzak" if tahmin == 1 else "✅ Güvenli",
                    "Risk": f"%{skor}",
                    "Sonuç": "✔️ Doğru" if basarili_mi else "❌ Yanlış"
                })
                
            accuracy = int((dogru_sayisi / 10) * 100)
            
            m1, m2 = st.columns(2)
            m1.metric("Genel Başarı Oranı", f"%{accuracy}", "Hedef: > %80")
            m2.metric("Doğru Karar Sayısı", f"{dogru_sayisi} / 10", "Test Tamamlandı")
            
            st.dataframe(pd.DataFrame(sonuc_tablosu), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("""
        ### Bu Asistan Mesajları Nasıl İnceliyor?
        1. **Link Kontrolü:** Mesaj içinde bir internet adresi varsa resmi ve güvenli bir yer mi diye bakar. Kısaltılmış veya şüpheli linkleri hemen yakalar.
        2. **Tehlikeli Kelimeler:** 'İcra', 'bloke', 'acil', 'IBAN' gibi dolandırıcıların sık kullandığı kelimeleri tarar.
        3. **Kelime Oyunu Çözücü:** Dolandırıcıların filtrelerden kaçmak için araya koyduğu nokta veya işaretleri (`i.c.r.a` gibi) temizleyerek asıl kelimeyi okur.
        4. **Yapay Zeka Kararı:** Cümlenin genel anlamını binlerce örnekle karşılaştırarak risk oranını yüzde olarak hesaplar.
        """)

# --- SAYFA 5: YÖNETİCİ PANELİ (BUTONLU GİRİŞ SİSTEMİ) ---
elif st.session_state.sayfa == "👨‍💻 Admin Paneli":
    st.title("🔒 Yönetici Paneli")
    st.write("Gelen mesaj önerilerini incelemek ve onaylamak için kullanıcı adı ve şifrenizle giriş yapın.")
    
    ADMIN_HESAPLARI = {
        "alp": {"sifre": "alp123", "isim": "Muzaffer Alp Ergülcü"},
        "oguzhan": {"sifre": "oguzhan123", "isim": "Oğuzhan Uysal"}
    }
    
    # Oturumda giriş yapıldı mı kontrolü
    if "admin_giris" not in st.session_state:
        st.session_state.admin_giris = False
    if "aktif_yonetici" not in st.session_state:
        st.session_state.aktif_yonetici = ""

    if not st.session_state.admin_giris:
        col_giris1, col_giris2, col_giris3 = st.columns([1, 1, 1])
        with col_giris1:
            kullanici_adi = st.text_input("👤 Kullanıcı Adı:").strip().lower()
        with col_giris2:
            girilen_sifre = st.text_input("🔑 Şifre:", type="password")
        with col_giris3:
            st.write("") # Boşluk hizalama için
            st.write("")
            giris_butonu = st.button("Giriş Yap", type="primary")

        if giris_butonu:
            if kullanici_adi in ADMIN_HESAPLARI and ADMIN_HESAPLARI[kullanici_adi]["sifre"] == girilen_sifre:
                st.session_state.admin_giris = True
                st.session_state.aktif_yonetici = ADMIN_HESAPLARI[kullanici_adi]["isim"]
                st.rerun()
            else:
                st.error("❌ Hatalı kullanıcı adı veya şifre!")
    
    # Giriş yapıldıysa Admin Paneli İçeriğini Göster
    if st.session_state.admin_giris:
        st.success(f"🔓 Giriş Başarılı! Hoş Geldiniz, **{st.session_state.aktif_yonetici}**.")
        
        if st.button("🚪 Çıkış Yap"):
            st.session_state.admin_giris = False
            st.session_state.aktif_yonetici = ""
            st.rerun()

        st.divider()
        
        col1, col2, col3 = st.columns(3)
        phishing_sayisi = len(df[df['etiket'] == 1])
        guvenli_sayisi = len(df[df['etiket'] == 0])
        
        with col1:
            st.metric(label="Toplam Kayıtlı Mesaj", value=f"{len(df)}")
        with col2:
            st.metric(label="Tuzak Mesaj Sayısı", value=f"{phishing_sayisi}")
        with col3:
            st.metric(label="Güvenli Mesaj Sayısı", value=f"{guvenli_sayisi}")
            
        st.divider()
        st.subheader("📈 Veri Dağılımı Grafikleri")
        grafik_col1, grafik_col2 = st.columns(2)
        
        with grafik_col1:
            st.markdown("**Mesaj Türü Dağılımı**")
            sinif_df = pd.DataFrame({
                "Tür": ["Tuzak", "Güvenli"],
                "Adet": [phishing_sayisi, guvenli_sayisi]
            }).set_index("Tür")
            st.bar_chart(sinif_df, color="#00f2fe")
            
        with grafik_col2:
            st.markdown("**En Sık Geçen Tehdit Kelimeleri**")
            phishing_metinleri = " ".join(df[df['etiket'] == 1]['mesaj'].astype(str)).lower()
            aranan_kelimeler = ["kargo", "icra", "hesap", "bloke", "tl", "iptal", "link", "ödeme"]
            kelime_sayilari = {k.upper(): phishing_metinleri.count(k) for k in aranan_kelimeler}
            kelime_df = pd.DataFrame(list(kelime_sayilari.items()), columns=["Kelime", "Sıklık"]).set_index("Kelime")
            st.bar_chart(kelime_df, color="#ff4b4b")

        st.divider()
        st.subheader("⏳ Onay Bekleyen Kullanıcı Önerileri")
        
        if os.path.exists("onay_bekleyenler.csv"):
            bekleyen_df = pd.read_csv("onay_bekleyenler.csv", on_bad_lines='skip')
            if len(bekleyen_df) > 0:
                for idx, row in bekleyen_df.iterrows():
                    with st.container():
                        mesaj_turu = "🚨 Tuzak" if row['etiket'] == 1 else "✅ Güvenli"
                        st.markdown(f"**Mesaj:** {row['mesaj']}")
                        st.markdown(f"**Tür:** {mesaj_turu}")
                        b1, b2, b3 = st.columns([1, 1, 4])
                        with b1:
                            if st.button("✅ Onayla ve Ekle", key=f"ekle_{idx}"):
                                temiz_kayit = str(row['mesaj']).replace(',', ' ')
                                pd.DataFrame({"mesaj": [temiz_kayit], "etiket": [int(row['etiket'])]}).to_csv("dataset.csv", mode="a", header=False, index=False)
                                bekleyen_df = bekleyen_df.drop(idx)
                                bekleyen_df.to_csv("onay_bekleyenler.csv", index=False)
                                st.cache_resource.clear()
                                st.rerun()
                        with b2:
                            if st.button("🗑️ Sil", key=f"sil_{idx}"):
                                bekleyen_df = bekleyen_df.drop(idx)
                                bekleyen_df.to_csv("onay_bekleyenler.csv", index=False)
                                st.rerun()
                    st.markdown("---")
            else:
                st.info("Onay bekleyen yeni öneri bulunmuyor.")
        else:
            st.info("Onay bekleyen yeni öneri bulunmuyor.")
