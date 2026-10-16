import streamlit as st
import pandas as pd
import re
import random
import os
import socket  # IP Adresi çözümlemek için eklendi

# İnternet yavaşlığında sistemin kilitlenmemesi için IP aramasına 2 saniye sınır koyuyoruz
socket.setdefaulttimeout(2.0) 

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# 1. Sayfa Ayarları
st.set_page_config(page_title="Akıllı SMS Analizörü", page_icon="🛡️", layout="wide")

# 2. Veri Seti ve Modeli Yükleme
@st.cache_resource
def modeli_yukle():
    try:
        df = pd.read_csv('dataset.csv')
    except:
        df = pd.DataFrame({'mesaj': ["Örnek sahte mesaj link.com", "Yarın geliyorum"], 'etiket': [1, 0]})
    
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB())
    model.fit(df['mesaj'], df['etiket'])
    return model, df

model, df = modeli_yukle()

# 3. Kategori Sözlükleri
KATEGORILER = {
    "kargo": ["ptt", "mng", "yurtiçi", "aras", "teslim", "adres", "kargonuz", "iade"],
    "icra_hukuk": ["icra", "dava", "uzlaştırma", "adliye", "sevk", "hapis", "tazminat", "savcılık", "ceza"],
    "banka_finans": ["bloke", "kredi kartı", "hesap", "şüpheli", "iptal", "ziraat", "garanti"],
    "para_talebi": ["iban", "hesaba yatır", "ödeme", "tl", "bedeli", "masraf", "para transferi"]
}

if "sayfa" not in st.session_state:
    st.session_state.sayfa = "🏠 Karşılama Ekranı"

# --- YAN MENÜ ---
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
st.sidebar.info("Proje Sahipleri:\n- Muzaffer Alp Ergülcü\n- Oğuzhan Uysal")

# --- SAYFA 1: KARŞILAMA EKRANI ---
if st.session_state.sayfa == "🏠 Karşılama Ekranı":
    st.title("Hoş Geldiniz! 🛡️ SMS Phishing Tespit Sistemi")
    st.markdown("""
    ### Siber Güvenliğiniz İçin Akıllı Çözüm
    Günümüzde artan **sahte kargo, icra takibi ve banka dolandırıcılığı** mesajlarına karşı 
    geliştirdiğimiz bu yapay zeka sistemi, SMS'lerinizi analiz ederek sizi tehlikelere karşı uyarır.
    """)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 UYGULAMAYI BAŞLAT VE SMS ANALİZİ YAP", type="primary", use_container_width=True):
            st.session_state.sayfa = "🛡️ SMS Analizörü"
            st.rerun()

# --- SAYFA 2: SMS ANALİZÖRÜ ---
elif st.session_state.sayfa == "🛡️ SMS Analizörü":
    st.title("🛡️ Akıllı SMS Analizörü")
    
    if "mesaj_kutusu" not in st.session_state:
        st.session_state.mesaj_kutusu = ""

    icra_banka_mesajlari = [
        "Sn. (Adınız), hakkınızda açılacak cinsel taciz davası bulunmaktadır. Uzlaştırma bedeli için hesaba para yatırın. link.com",
        "Sayin musteri hesabiniza bloke konulmustur. Acil islem icin tiklayin: tinyurl.com/banka-onay"
    ]
    kargo_odul_mesajlari = [
        "PTT Kargo: Gonderiniz adres hatasi nedeniyle teslim edilemedi. Guncellemek icin tiklayin: http://bit.ly/kargo-onay",
        "Tebrikler! 10.000 TL degerinde hediye ceki kazandiniz. Hemen alin: odul-al.net"
    ]
    guvenli_mesajlar = [
        "Yarın saat 14:00'te toplantımız var, lütfen gecikmeyin. İyi çalışmalar.",
        "Şu komik videoya baksana: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ]

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("🚨 Örnek İcra/Banka", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(icra_banka_mesajlari)
    with colB:
        if st.button("📦 Örnek Kargo/Ödül", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(kargo_odul_mesajlari)
    with colC:
        if st.button("✅ Örnek Güvenli (YouTube)", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(guvenli_mesajlar)

    mesaj_girdisi = st.text_area("Mesajınız:", value=st.session_state.mesaj_kutusu, height=130)

    if st.button("🔍 Mesajı Analiz Et", type="primary"):
        if mesaj_girdisi:
            gerekceler = []
            risk_skoru = 0
            mesaj_lower = mesaj_girdisi.lower()

            # --- YENİ BÖLÜM: BEYAZ LİSTE VE IP ÇÖZÜMLEME SİSTEMİ ---
            guvenli_domainler = ["youtube.com", "youtu.be", "google.com", "instagram.com", "turkiye.gov.tr", "edu.tr", "whatsapp.com", "github.com", "twitter.com"]
            kisaltilmis_linkler = ["bit.ly", "tinyurl.com", "t.co", "ow.ly", "cutt.ly", "is.gd"]
            
            link_regex = r"(https?://\S+|www\.\S+|\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b)"
            bulunan_linkler = re.findall(link_regex, mesaj_girdisi)
            
            guvenli_link_var = False
            tehlikeli_link_var = False

            if bulunan_linkler:
                for link in bulunan_linkler:
                    # Domaini temizle
                    domain = link.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                    
                    # Beyaz Liste Kontrolü
                    if any(guvenli in domain for guvenli in guvenli_domainler):
                        guvenli_link_var = True
                        gerekceler.append(f"🌐 **Güvenilir Bağlantı:** '{domain}' adresi sistemin güvenilir beyaz listesinde (Whitelist) yer almaktadır.")
                    else:
                        tehlikeli_link_var = True
                        # IP Çözümleme
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

            # Kural 2: Kelime Analizi
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

            # Kural 3: Yapay Zeka
            ml_tahmin = model.predict([mesaj_girdisi])[0]
            if ml_tahmin == 1:
                # EĞER SADECE GÜVENLİ LİNK VARSA VE BAŞKA RİSK YOKSA YZ'NİN ÖNYARGISINI EZ (Override)
                if guvenli_link_var and not tehlikeli_link_var and risk_skoru == 0:
                    gerekceler.append("🧠 **Yapay Zeka Notu:** Mesaj yapısı şüpheli bulunsa da, içindeki bağlantı resmi bir kuruma ait olduğu için YZ riski sıfırlandı.")
                    risk_skoru = 0
                else:
                    gerekceler.append("🧠 **Yapay Zeka Analizi:** AI, bu cümlenin yapısını dolandırıcılık vakalarıyla eşleştirdi.")
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
                    st.success("✅ GÜVENLİ: Bu mesajda belirgin bir dolandırıcılık riski tespit edilmedi.")

            if toplam_risk >= 0 and len(gerekceler) > 0:
                st.subheader("🔍 Tespit Edilen Analiz Nedenleri:")
                for g in gerekceler:
                    st.markdown(g)

# --- SAYFA 3, 4, 5 (Aynı Kaldı) ---
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

elif st.session_state.sayfa == "🧠 YZ ve Skorlama":
    st.title("🧠 Yapay Zeka ve Skorlama Altyapısı")
    st.markdown("""
    ### 1. Risk Skoru Neye Göre Hesaplanıyor?
    * **Şüpheli Linkler (URL/Kısaltma):** +45 Puan
    * **Hukuki Tehdit & Korkutma Dili:** +35 Puan
    * **Doğrudan Para/IBAN Talebi:** +35 Puan
    * **Yapay Zeka (Bağlam Eşleşmesi):** +20 Puan
    
    ### 2. IP Çözümleme Teknolojisi (DNS Lookup)
    Mesaj içerisinde tespit edilen her bağlantı, sistem tarafından "Beyaz Liste" (Whitelist) taramasından geçirilir. Yabancı bir alan adı tespit edilirse, sistem arka planda bir DNS sorgusu çalıştırarak dolandırıcı sunucunun **IP adresini** tespit edip raporlar.
    """)

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
