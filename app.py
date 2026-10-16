import streamlit as st
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# 1. Sayfa Ayarları (Uygulama tam ekran ve geniş görünecek)
st.set_page_config(page_title="Akıllı SMS Analizörü", page_icon="🛡️", layout="wide")

# 2. Veri Seti ve Modeli Önbelleğe Alma (Sayfalar arası geçişi hızlandırır)
@st.cache_resource
def modeli_yukle():
    try:
        df = pd.read_csv('dataset.csv')
    except:
        # Eğer dataset.csv bulunamazsa yedek mini veri seti
        df = pd.DataFrame({'mesaj': ["Örnek sahte mesaj link.com", "Yarın geliyorum"], 'etiket': [1, 0]})
    
    # NLP Modeli: TF-IDF ve Naive Bayes
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

# 4. Sayfa Yönlendirme Altyapısı (Session State)
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "🏠 Karşılama Ekranı"

# --- YAN MENÜ (SIDEBAR) TASARIMI ---
st.sidebar.title("📌 Navigasyon")
st.sidebar.markdown("Menüden gitmek istediğiniz sayfayı seçin:")

if st.sidebar.button("🏠 Karşılama Ekranı", use_container_width=True):
    st.session_state.sayfa = "🏠 Karşılama Ekranı"
if st.sidebar.button("🛡️ SMS Analizörü", use_container_width=True):
    st.session_state.sayfa = "🛡️ SMS Analizörü"
if st.sidebar.button("🧠 YZ ve Skorlama", use_container_width=True):
    st.session_state.sayfa = "🧠 YZ ve Skorlama"
if st.sidebar.button("👨‍💻 Geliştirici Ekranı", use_container_width=True):
    st.session_state.sayfa = "👨‍💻 Geliştirici Ekranı"

st.sidebar.divider()
st.sidebar.info("Proje Sahipleri:\n\n- Muzaffer Alp Ergülcü\n- Oğuzhan Uysal")


# --- SAYFA 1: KARŞILAMA EKRANI ---
if st.session_state.sayfa == "🏠 Karşılama Ekranı":
    st.title("Hoş Geldiniz! 🛡️ SMS Phishing (Oltalama) Tespit Sistemi")
    st.markdown("""
    ### Siber Güvenliğiniz İçin Akıllı Çözüm
    Günümüzde artan **sahte kargo, icra takibi ve banka dolandırıcılığı** mesajlarına karşı 
    geliştirdiğimiz bu yapay zeka sistemi, SMS'lerinizi analiz ederek sizi tehlikelere karşı uyarır.
    
    * **Anında Analiz:** Şüpheli mesajı sisteme yapıştırın, saniyeler içinde sonuç alın.
    * **Detaylı Gerekçeler:** Sadece "tehlikeli" demez, tehlikenin nedenini (kısaltılmış link, aciliyet dili vb.) açıklar.
    * **Yapay Zeka Destekli:** Geleneksel yöntemlerin aksine, metnin bağlamını Makine Öğrenmesi (NLP) ile anlar.
    """)
    
    st.write("") # Boşluk
    # Farklı amaca hizmet eden BAŞLA butonu
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 UYGULAMAYI BAŞLAT VE SMS ANALİZİ YAP", type="primary", use_container_width=True):
            st.session_state.sayfa = "🛡️ SMS Analizörü"
            st.rerun()

# --- SAYFA 2: SMS ANALİZÖRÜ ---
elif st.session_state.sayfa == "🛡️ SMS Analizörü":
    st.title("🛡️ Akıllı SMS Analizörü")
    st.write("Şüpheli mesajı aşağıya yapıştırın veya örnek mesajlardan birini hızlıca test edin.")

    # Farklı amaçlara hizmet eden TEST BUTONLARI (Hocanın istediği özellik)
    if "mesaj_kutusu" not in st.session_state:
        st.session_state.mesaj_kutusu = ""

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("🚨 Örnek İcra/Dolandırıcı Mesajı", use_container_width=True):
            st.session_state.mesaj_kutusu = "Sn. (Adınız), hakkınızda açılacak cinsel taciz davası bulunmaktadır. Uzlaştırma bedeli için hesaba para yatırın. link.com"
    with colB:
        if st.button("📦 Örnek Sahte Kargo Mesajı", use_container_width=True):
            st.session_state.mesaj_kutusu = "PTT Kargo: Gonderiniz adres hatasi nedeniyle teslim edilemedi. Guncellemek icin tiklayin: http://bit.ly/kargo-onay"
    with colC:
        if st.button("✅ Örnek Güvenli Mesaj", use_container_width=True):
            st.session_state.mesaj_kutusu = "Yarın saat 14:00'te toplantımız var, lütfen gecikmeyin. İyi çalışmalar."

    # Kullanıcı Metin Girişi
    mesaj_girdisi = st.text_area("Mesajınız:", value=st.session_state.mesaj_kutusu, height=130)

    if st.button("🔍 Mesajı Analiz Et", type="primary"):
        if mesaj_girdisi:
            gerekceler = []
            risk_skoru = 0
            mesaj_lower = mesaj_girdisi.lower()

            # Kural 1: Link Analizi
            link_regex = r"(http://|https://|bit\.ly|tinyurl\.com|t\.co|[a-zA-Z0-9.-]+\.(com|net|org|tr))"
            if re.search(link_regex, mesaj_girdisi, re.IGNORECASE):
                gerekceler.append("🔗 **Şüpheli Bağlantı:** Yönlendirme linki (URL) tespit edildi.")
                risk_skoru += 45

            # Kural 2: Kategori Kelimeleri
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

            # Kural 3: Yapay Zeka (NLP) Bağlam Analizi
            ml_tahmin = model.predict([mesaj_girdisi])[0]
            if ml_tahmin == 1:
                gerekceler.append("🧠 **Yapay Zeka Analizi:** AI, bu cümlenin genel yapısını dolandırıcılık vakalarıyla eşleştirdi.")
                risk_skoru += 20

            # Sonuç Ekranı
            toplam_risk = min(risk_skoru, 100)
            st.divider()
            
            # İki kolonlu şık gösterim
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
        else:
            st.warning("Lütfen analiz edilecek bir metin girin.")

# --- SAYFA 3: YZ VE SKORLAMA (Hocanın istediği şeffaflık) ---
elif st.session_state.sayfa == "🧠 YZ ve Skorlama":
    st.title("🧠 Yapay Zeka ve Skorlama Altyapısı")
    st.markdown("""
    ### 1. Risk Skoru Neye Göre Hesaplanıyor?
    Uygulamamız, metin içerisindeki tehlikeleri ağırlıklandırarak **100 üzerinden bir risk skoru** çıkarır:
    * **Şüpheli Linkler (URL/Kısaltma):** +45 Puan *(En yaygın phishing taktiği)*
    * **Hukuki Tehdit & Korkutma Dili:** +35 Puan *(İcra, dava, adliye kelimeleri)*
    * **Doğrudan Para/IBAN Talebi:** +35 Puan
    * **Yapay Zeka (Bağlam Eşleşmesi):** +20 Puan
    
    *(Not: Matematiksel toplam 100'ü geçse dahi sistem tavan skoru %100 olarak limitler.)*
    
    ---
    
    ### 2. Hangi Yapay Zeka Kullanıldı?
    Projemizde Scikit-Learn kütüphanesi üzerinden **Doğal Dil İşleme (NLP)** ve **Makine Öğrenmesi** teknikleri kullanılmıştır:
    
    * **TF-IDF Vectorizer:** Metinlerde geçen kelimelerin metin içindeki önem sırasını matematiksel vektörlere (sayılara) dönüştürür.
    * **Multinomial Naive Bayes:** Olasılık tabanlı bir sınıflandırma algoritmasıdır. Eğitim veri setindeki (dataset.csv) dolandırıcı mesajlarını analiz eder ve yeni gelen bir mesajın öncekilere benzeme ihtimalini (olasılığını) hesaplar.
    * **Gelecek Hedefi:** Projenin bir sonraki aşamasında, kelime bazlı eşleşmeden ziyade Türkçe dilinin semantiğini (anlamını) derinlemesine anlayan **BERTurk (Derin Öğrenme)** dil modeline geçilmesi planlanmaktadır.
    """)

# --- SAYFA 4: GELİŞTİRİCİ EKRANI (Hocanın istediği veri gösterimi) ---
elif st.session_state.sayfa == "👨‍💻 Geliştirici Ekranı":
    st.title("👨‍💻 Geliştirici ve Veri Bilimi Ekranı")
    st.write("Bu panel, uygulamanın arka planında çalışan eğitim verilerini ve model metriklerini gösterir.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Toplam Eğitim Verisi", value=f"{len(df)} Mesaj")
    with col2:
        st.metric(label="Dolandırıcılık (Phishing) Örneği", value=f"{len(df[df['etiket'] == 1])}")
    with col3:
        st.metric(label="Güvenli (Normal) Mesaj Örneği", value=f"{len(df[df['etiket'] == 0])}")
        
    st.subheader("📊 Arka Plan Veri Seti (dataset.csv)")
    st.dataframe(df, use_container_width=True)
    
    st.subheader("⚙️ Model Pipeline (Boru Hattı)")
    st.code("make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB())", language="python")
