import streamlit as st
import pandas as pd
import re
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# 1. Sayfa Ayarları
st.set_page_config(page_title="Akıllı SMS Analizörü", page_icon="🛡️", layout="wide")

# 2. Veri Seti ve Modeli Yükleme (Önbelleğe Alma)
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
if st.sidebar.button("👨‍💻 Geliştirici Ekranı", use_container_width=True):
    st.session_state.sayfa = "👨‍💻 Geliştirici Ekranı"

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

# --- SAYFA 2: SMS ANALİZÖRÜ (DİNAMİK ÖRNEKLERLE GÜNCELLENDİ) ---
elif st.session_state.sayfa == "🛡️ SMS Analizörü":
    st.title("🛡️ Akıllı SMS Analizörü")
    
    if "mesaj_kutusu" not in st.session_state:
        st.session_state.mesaj_kutusu = ""

    # DİNAMİK MESAJ HAVUZLARI
    icra_banka_mesajlari = [
        "Sn. (Adınız), hakkınızda açılacak cinsel taciz davası bulunmaktadır. Uzlaştırma bedeli için hesaba para yatırın. link.com",
        "Sayin musteri hesabiniza bloke konulmustur. Acil islem icin tiklayin: tinyurl.com/banka-onay",
        "Yasa disi bahis oynadiginiz tespit edilmistir. 45.000 TL cezanizi odemek icin iletisime gecin.",
        "Dosyanız adliyeye sevk edilecektir. Mağdur olmamak için hemen dönüş yapınız."
    ]
    
    kargo_odul_mesajlari = [
        "PTT Kargo: Gonderiniz adres hatasi nedeniyle teslim edilemedi. Guncellemek icin tiklayin: http://bit.ly/kargo-onay",
        "MNG Kargo: Dağıtıma çıkan kargonuz adres yetersizliğinden iade edilmiştir. Detay: kargo-takip.xyz",
        "Yurtiçi Kargo: Teslimatınız başarısız oldu. Yeniden dağıtım ücretini ödemek için linke girin: kargo-odeme.net",
        "Tebrikler! 10.000 TL degerinde hediye ceki kazandiniz. Hemen alin: odul-al.net"
    ]
    
    guvenli_mesajlar = [
        "Yarın saat 14:00'te toplantımız var, lütfen gecikmeyin. İyi çalışmalar.",
        "Kanka yarın akşam halı saha maçımız var, gelmeyi unutma.",
        "Kredi kartı ekstreniz e-posta adresinize gönderilmiştir. Ziraat Bankası",
        "Ders programı güncellendi WhatsApp grubundan bakabilirsiniz.",
        "Kiranızı ayın 5'ine kadar yatırmanızı rica ederim."
    ]

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("🚨 Örnek İcra/Banka (Rastgele)", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(icra_banka_mesajlari)
    with colB:
        if st.button("📦 Örnek Kargo/Ödül (Rastgele)", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(kargo_odul_mesajlari)
    with colC:
        if st.button("✅ Örnek Güvenli (Rastgele)", use_container_width=True):
            st.session_state.mesaj_kutusu = random.choice(guvenli_mesajlar)

    mesaj_girdisi = st.text_area("Mesajınız:", value=st.session_state.mesaj_kutusu, height=130)

    if st.button("🔍 Mesajı Analiz Et", type="primary"):
        if mesaj_girdisi:
            gerekceler = []
            risk_skoru = 0
            mesaj_lower = mesaj_girdisi.lower()

            link_regex = r"(http://|https://|bit\.ly|tinyurl\.com|t\.co|[a-zA-Z0-9.-]+\.(com|net|org|tr))"
            if re.search(link_regex, mesaj_girdisi, re.IGNORECASE):
                gerekceler.append("🔗 **Şüpheli Bağlantı:** Yönlendirme linki (URL) tespit edildi.")
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

            if toplam_risk > 0:
                st.subheader("🔍 Tespit Edilen Risk Nedenleri:")
                for g in gerekceler:
                    st.markdown(g)

# --- SAYFA 3: SİSTEME KATKI SAĞLA ---
elif st.session_state.sayfa == "📥 Sisteme Katkı Sağla":
    st.title("📥 Veri Setine Katkıda Bulunun")
    st.markdown("""
    Yapay zekanın **sürekli öğrenme (continuous learning)** yeteneğini kullanarak sistemi daha akıllı hale getirebilirsiniz. 
    Bildiğiniz yeni bir dolandırıcılık SMS'ini veya güvenli bir mesajı aşağıdan ekleyerek modelimizi anında eğitebilirsiniz.
    """)
    
    yeni_mesaj = st.text_area("Veri tabanına eklenecek mesajı yazın:")
    
    etiket_secimi = st.radio("Bu mesajın türü nedir?", [
        "🚨 Dolandırıcılık / Oltalama Mesajı (Phishing)", 
        "✅ Normal / Güvenli Mesaj"
    ])
    
    if st.button("💾 Mesajı Sisteme Öğret", type="primary"):
        if yeni_mesaj.strip() == "":
            st.warning("Lütfen boş bir mesaj eklemeyin.")
        else:
            etiket_degeri = 1 if "Dolandırıcılık" in etiket_secimi else 0
            temiz_mesaj = yeni_mesaj.replace('\n', ' ').replace('\r', '')
            
            yeni_veri = pd.DataFrame({"mesaj": [temiz_mesaj], "etiket": [etiket_degeri]})
            yeni_veri.to_csv("dataset.csv", mode="a", header=False, index=False)
            
            st.cache_resource.clear()
            
            st.success("🎉 Harika! Mesajınız başarıyla veri setine eklendi. Yapay zeka modeli şu an yeni verinizle yeniden eğitildi.")
            st.balloons()

# --- SAYFA 4: YZ VE SKORLAMA ---
elif st.session_state.sayfa == "🧠 YZ ve Skorlama":
    st.title("🧠 Yapay Zeka ve Skorlama Altyapısı")
    st.markdown("""
    ### 1. Risk Skoru Neye Göre Hesaplanıyor?
    * **Şüpheli Linkler (URL/Kısaltma):** +45 Puan
    * **Hukuki Tehdit & Korkutma Dili:** +35 Puan
    * **Doğrudan Para/IBAN Talebi:** +35 Puan
    * **Yapay Zeka (Bağlam Eşleşmesi):** +20 Puan
    
    ### 2. Hangi Yapay Zeka Kullanıldı?
    **TF-IDF Vectorizer** ve **Multinomial Naive Bayes** kullanılmıştır. Sistem kitle kaynaklı (crowdsourced) verilerle kendini anında yenileyebilen dinamik bir yapıya sahiptir.
    """)

# --- SAYFA 5: GELİŞTİRİCİ EKRANI ---
elif st.session_state.sayfa == "👨‍💻 Geliştirici Ekranı":
    st.title("👨‍💻 Geliştirici ve Veri Bilimi Ekranı")
    st.info("💡 Sisteme Katkı Sağla sayfasından eklediğiniz yeni mesajların bu veri tabanına otomatik eklendiğini görebilirsiniz.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Toplam Eğitim Verisi", value=f"{len(df)} Mesaj")
    with col2:
        st.metric(label="Dolandırıcılık Örneği", value=f"{len(df[df['etiket'] == 1])}")
    with col3:
        st.metric(label="Güvenli Mesaj Örneği", value=f"{len(df[df['etiket'] == 0])}")
        
    st.subheader("📊 Arka Plan Veri Seti (dataset.csv)")
    st.dataframe(df, use_container_width=True)
