import streamlit as st
import pandas as pd
import re
import random
import os
import socket

# --- 1. PERFORMANS OPTİMİZASYONLARI ---
socket.setdefaulttimeout(2.0) 
LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+|\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b)", re.IGNORECASE)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# --- 2. SAYFA AYARLARI VE ESTETİK ÖZEL CSS (PROFESYONEL KOYU TEMA) ---
st.set_page_config(page_title="Akıllı SMS Analizörü", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    /* Genel Arka Plan ve Yazı Stili */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* Buton Tasarımları - Profesyonel Neon Geçişli */
    div.stButton > button:first-child {
        border-radius: 10px;
        font-weight: 600;
        background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
        color: white;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(78, 67, 118, 0.5);
        border-color: #26D0CE;
    }
    /* Metrik Kartları - Estetik Çerçeve */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(38, 208, 206, 0.2);
        padding: 15px 20px;
        border-radius: 14px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    /* Metin Giriş Kutusu Estetiği */
    .stTextArea textarea {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        background-color: #161B22;
        color: #FAFAFA;
    }
    /* Sidebar (Yan Menü) Tasarımı */
    [data-testid="stSidebar"] {
        background-color: #11161D;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MODEL YÜKLEME (Önbellekleme) ---
@st.cache_resource(show_spinner=False)
def modeli_yukle():
    try:
        df = pd.read_csv('dataset.csv')
    except:
        df = pd.DataFrame({'mesaj': ["Örnek sahte mesaj link.com", "Yarın geliyorum"], 'etiket': [1, 0]})
    
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB())
    model.fit(df['mesaj'], df['etiket'])
    return model, df

model, df = modeli_yukle()

# --- 4. KATEGORİ SÖZLÜKLERİ ---
KATEGORILER = {
    "kargo": ["ptt", "mng", "yurtiçi", "aras", "teslim", "adres", "kargonuz", "iade"],
    "icra_hukuk": ["icra", "dava", "uzlaştırma", "adliye", "sevk", "hapis", "tazminat", "savcılık", "ceza", "hukuk"],
    "banka_finans": ["bloke", "kredi kartı", "hesap", "şüpheli", "iptal", "ziraat", "garanti", "akbank", "papara"],
    "para_talebi": ["iban", "hesaba yatır", "ödeme", "tl", "bedeli", "masraf", "para transferi"]
}

if "sayfa" not in st.session_state:
    st.session_state.sayfa = "🏠 Karşılama Ekranı"

# --- YAN MENÜ (SIDEBAR) ---
st.sidebar.title("📌 Navigasyon")
if st.sidebar.button("🏠 Karşılama Ekranı", use_container_width=True):
    st.session_state.sayfa = "🏠 Karşılama Ekranı"
if st.sidebar.button("🛡️ SMS Analizörü", use_container_width=True):
    st.session_state.sayfa = "🛡️ SMS Analizörü"
if st.sidebar.button("📥 Sisteme Katkı Sağla", use_container_width=True):
    st.session_state.sayfa = "📥 Sisteme Katkı Sağla"
if st.sidebar.button("🧠 YZ ve Skorlama", use_container_width=True):
    st.session_state.sayfa = "🧠 YZ ve Skorlama"
if st.sidebar.button("👨‍💻 Admin Paneli", use_container_width=True):
    st.session_state.sayfa = "👨‍💻 Admin Paneli"

st.sidebar.divider()

# Dinamik Animasyonlu Bilgi Kutusu (Estetik Neon Tasarım)
dinamik_kutu_html = """
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
"""
st.sidebar.markdown(dinamik_kutu_html, unsafe_allow_html=True)
st.sidebar.info("👨‍💻 **Proje Geliştiricileri:**\n\n- Muzaffer Alp Ergülcü\n- Oğuzhan Uysal")


# --- SAYFA 1: KARŞILAMA EKRANI ---
if st.session_state.sayfa == "🏠 Karşılama Ekranı":
    st.title("Hoş Geldiniz! 🛡️ SMS Phishing Tespit Sistemi")
    st.markdown("""
    ### Siber Güvenliğiniz İçin Yeni Nesil Yapay Zeka Çözümü
    Günümüzde artan **sahte kargo, icra takibi ve banka dolandırıcılığı** mesajlarına karşı 
    geliştirdiğimiz bu akıllı sistem, gelen iletileri saniyeler içinde analiz eder.
    
    * ⚡ **Anında NLP Analizi:** Metin yapısını ve bağlamı saniyeler içinde çözer.
    * 🌍 **Canlı IP Çözümleme:** Bağlantıların arka plandaki gerçek sunucu IP adreslerini denetler.
    * 🧠 **Sürekli Öğrenme:** Kitle kaynaklı geri bildirimlerle kendini dinamik olarak günceller.
    """)
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 UYGULAMAYI BAŞLAT VE ANALİZ YAP", type="primary", use_container_width=True):
            st.session_state.sayfa = "🛡️ SMS Analizörü"
            st.rerun()

# --- SAYFA 2: SMS ANALİZÖR ---
elif st.session_state.sayfa == "🛡️ SMS Analizörü":
    st.title("🛡️ Akıllı SMS Analizörü")
    st.write("Şüpheli mesajınızı aşağıya yapıştırın veya hızlı test butonlarını kullanın.")
    
    if "mesaj_kutusu" not in st.session_state:
        st.session_state.mesaj_kutusu = ""

    icra_banka_mesajlari = [
        "Sn. (Adınız), hakkınızda açılacak cinsel taciz davası bulunmaktadır. Uzlaştırma bedeli için hesaba para yatırın. link.com",
        "Sayin musteri hesabiniza bloke konulmustur. Acil islem icin tiklayin: tinyurl.com/banka-onay",
        "Akbank: Hesabinizdan yurt disi kaynakli 10.000 TL transfer talebi alinmistir. İptal etmek icin: akbank-iptal.xyz"
    ]
    kargo_odul_mesajlari = [
        "PTT Kargo: Gonderiniz adres hatasi nedeniyle teslim edilemedi. Guncellemek icin tiklayin: http://bit.ly/kargo-onay",
        "Tebrikler! GSM operatorunuzden iPhone 15 Pro Max kazandiniz. Teslim alin: odul-kargo.net",
        "Trendyol: Yilbasi ozel 1000 TL indirim kuponunuz hesabiniza tanimlandi. Kullanmak icin: trendyol-firsat.net"
    ]
    guvenli_mesajlar = [
        "Yarın saat 14:00'te toplantımız var, lütfen gecikmeyin. İyi çalışmalar.",
        "Şu komik videoya baksana: https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "Kredi kartı ekstreniz e-posta adresinize gönderilmiştir. Ziraat Bankası"
    ]

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("🚨 Örnek İcra/Banka", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(icra_banka_mesajlari)
    with colB:
        if st.button("📦 Örnek Kargo/Ödül", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(kargo_odul_mesajlari)
    with colC:
        if st.button("✅ Örnek Güvenli", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(guvenli_mesajlar)

    mesaj_girdisi = st.text_area("Analiz Edilecek SMS Metni:", value=st.session_state.mesaj_kutusu, height=130)

    if st.button("🔍 Güvenlik Analizini Başlat", type="primary"):
        if mesaj_girdisi:
            gerekceler = []
            risk_skoru = 0
            mesaj_lower = mesaj_girdisi.lower()

            guvenli_domainler = ["youtube.com", "youtu.be", "google.com", "instagram.com", "turkiye.gov.tr", "edu.tr", "whatsapp.com", "github.com", "twitter.com"]
            kisaltilmis_linkler = ["bit.ly", "tinyurl.com", "t.co", "ow.ly", "cutt.ly", "is.gd"]
            
            bulunan_linkler = LINK_REGEX.findall(mesaj_girdisi)
            
            guvenli_link_var = False
            tehlikeli_link_var = False

            if bulunan_linkler:
                for link in bulunan_linkler:
                    domain = link.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                    
                    if any(guvenli in domain for guvenli in guvenli_domainler):
                        guvenli_link_var = True
                        gerekceler.append(f"🌐 **Güvenilir Bağlantı:** '{domain}' adresi sistemin güvenilir beyaz listesinde yer almaktadır.")
                    else:
                        tehlikeli_link_var = True
                        try:
                            ip_adresi = socket.gethostbyname(domain)
                            ip_detay = f"Sunucu IP: {ip_adresi}"
                        except:
                            ip_detay = "IP Gizlenmiş veya Ulaşılamıyor!"

                        if any(kisaltma in domain for kisaltma in kisaltilmis_linkler):
                            gerekceler.append(f"🔗 **Tehlikeli Link Kısaltması:** İzlenmeyi zorlaştıran kısaltılmış link ({domain}) kullanılmış! ({ip_detay})")
                            risk_skoru += 55
                        else:
                            gerekceler.append(f"🔗 **Bilinmeyen Bağlantı:** Doğrulanmamış bir web sitesine ({domain}) yönlendirme yapılıyor. ({ip_detay})")
                            risk_skoru += 45

            for kategori, kelimeler in KATEGORILER.items():
                if any(kelime in mesaj_lower for kelime in kelimeler):
                    if kategori == "icra_hukuk":
                        gerekceler.append("⚖️ **Hukuki Tehdit:** Korkutma, icra, dava kelimeleri kullanılmış.")
                        risk_skoru += 35
                    elif kategori == "banka_finans":
                        gerekceler.append("🏦 **Banka Oltalaması:** Hesap veya kredi kartı ile ilgili aciliyet var.")
                        risk_skoru += 30
                    elif kategori == "para_talebi":
                        gerekceler.append("💸 **Para/Ödeme Talebi:** IBAN veya para transferi isteniyor.")
                        risk_skoru += 35

            ml_tahmin = model.predict([mesaj_girdisi])[0]
            if ml_tahmin == 1:
                if guvenli_link_var and not tehlikeli_link_var and risk_skoru == 0:
                    gerekceler.append("🧠 **Yapay Zeka Notu:** Mesaj yapısı şüpheli bulunsa da bağlantı resmi bir kuruma ait olduğu için risk sıfırlandı.")
                    risk_skoru = 0
                else:
                    gerekceler.append("🧠 **Yapay Zeka Analizi:** NLP Motoru, bu cümlenin semantik yapısını dolandırıcılık vakalarıyla eşleştirdi.")
                    risk_skoru += 20

            toplam_risk = min(risk_skoru, 100)
            st.divider()
            
            sonuc_col1, sonuc_col2 = st.columns([1, 2])
            with sonuc_col1:
                st.metric(label="Hesaplanan Risk Skoru", value=f"%{toplam_risk}")
            with sonuc_col2:
                if toplam_risk >= 70:
                    st.error("🚨 KRİTİK RİSK: Bu mesaj %99 ihtimalle dolandırıcılık (phishing) amaçlıdır!")
                elif 30 <= toplam_risk < 70:
                    st.warning("⚠️ ŞÜPHELİ: Bu mesajda riskli unsurlar bulundu. Teyit etmeden işlem yapmayın.")
                else:
                    st.success("✅ GÜVENLİ: Bu mesajda belirgin bir siber güvenlik riski tespit edilmedi.")

            if toplam_risk >= 0 and len(gerekceler) > 0:
                st.subheader("🔍 Sistem Tarafından Tespit Edilen Nedenler:")
                for g in gerekceler:
                    st.markdown(g)
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
            temiz_mesaj = yeni_mesaj.replace('\n', ' ').replace('\r', '')
            
            yeni_veri = pd.DataFrame({"mesaj": [temiz_mesaj], "etiket": [etiket_degeri]})
            if not os.path.exists("onay_bekleyenler.csv"):
                yeni_veri.to_csv("onay_bekleyenler.csv", mode="w", index=False)
            else:
                yeni_veri.to_csv("onay_bekleyenler.csv", mode="a", header=False, index=False)
            st.success("✅ Mesajınız başarıyla yönetici onay havuzuna gönderildi!")

# --- SAYFA 4: YZ VE SKORLAMA ---
elif st.session_state.sayfa == "🧠 YZ ve Skorlama":
    st.title("🧠 Yapay Zeka ve Skorlama Altyapısı")
    st.markdown("""
    ### 1. Risk Skoru Neye Göre Hesaplanıyor?
    * **Şüpheli Linkler (URL/Kısaltma):** +45 Puan
    * **Hukuki Tehdit & Korkutma Dili:** +35 Puan
    * **Doğrudan Para/IBAN Talebi:** +35 Puan
    * **Yapay Zeka (Bağlam Eşleşmesi):** +20 Puan
    
    ### 2. IP Çözümleme Teknolojisi (DNS Lookup)
    Mesaj içerisindeki bağlantılar "Beyaz Liste" (Whitelist) taramasından geçirilir. Yabancı alan adları için DNS sorgusu yapılarak sunucu **IP adresi** raporlanır.
    
    ### 3. Makine Öğrenmesi (NLP) Motoru
    Scikit-Learn kütüphanesi üzerinde çalışan **TF-IDF Vectorizer** ve **Multinomial Naive Bayes** algoritmaları ile optimize edilmiştir.
    """)

# --- SAYFA 5: ADMİN PANELİ ---
elif st.session_state.sayfa == "👨‍💻 Admin Paneli":
    st.title("🔒 Yönetici (Admin) Paneli")
    girilen_sifre = st.text_input("Lütfen Yönetici Şifresini Giriniz:", type="password")
    
    if girilen_sifre == "admin123":
        st.success("Giriş Başarılı. Yönetici Paneline Hoş Geldiniz.")
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Toplam Eğitilmiş Mesaj", value=f"{len(df)}")
        with col2:
            st.metric(label="Dolandırıcılık (Phishing)", value=f"{len(df[df['etiket'] == 1])}")
        with col3:
            st.metric(label="Güvenli (Normal)", value=f"{len(df[df['etiket'] == 0])}")
            
        st.divider()
        st.subheader("⏳ Onay Bekleyen (Kullanıcılardan Gelen) Mesajlar")
        
        if os.path.exists("onay_bekleyenler.csv"):
            bekleyen_df = pd.read_csv("onay_bekleyenler.csv")
            if len(bekleyen_df) > 0:
                for idx, row in bekleyen_df.iterrows():
                    with st.container():
                        mesaj_turu = "🚨 Phishing" if row['etiket'] == 1 else "✅ Güvenli"
                        st.markdown(f"**Mesaj:** {row['mesaj']}")
                        st.markdown(f"**Önerilen Etiket:** {mesaj_turu}")
                        b1, b2, b3 = st.columns([1, 1, 4])
                        with b1:
                            if st.button("✅ Sisteme Ekle", key=f"ekle_{idx}"):
                                pd.DataFrame({"mesaj": [row['mesaj']], "etiket": [row['etiket']]}).to_csv("dataset.csv", mode="a", header=False, index=False)
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
    elif girilen_sifre != "":
        st.error("Hatalı Şifre! Lütfen tekrar deneyin.")
