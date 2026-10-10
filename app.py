import streamlit as st
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# --- 1. GENİŞLETİLMİŞ EĞİTİM VERİ SETİ (ML MODELİ İÇİN) ---
# 1. Eğitim Veri Setini CSV Dosyasından Okuma
df = pd.read_csv('dataset.csv')

# --- 2. MAKİNE ÖĞRENMESİ MODELİ EĞİTİMİ ---
model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB())
model.fit(df['mesaj'], df['etiket'])

# --- 3. KAPSAMLI DOLANDIRICILIK SÖZLÜKLERİ ---
KATEGORILER = {
    "kargo": ["ptt", "mng", "yurtiçi", "aras", "teslim edilemedi", "adres yetersizliği", "kargonuz", "gönderiniz", "iade"],
    "icra_hukuk": ["icra", "dava", "uzlaştırma", "adliye", "sevk", "hapis", "tazminat", "savcılık", "ceza", "dosya", "yasa dışı", "bahis", "taciz"],
    "banka_finans": ["bloke", "kredi kartı", "hesap", "şüpheli işlem", "iptal", "ziraat", "garanti", "akbank", "iş bankası"],
    "odul_yardim": ["tebrikler", "hediye", "çek", "kazandınız", "askıda fatura", "yardım", "e-devlet"],
    "para_talebi": ["iban", "hesaba yatır", "ödeme", "tl", "bedeli", "masraf", "para transferi"]
}

# --- 4. STREAMLIT ARAYÜZÜ ---
st.set_page_config(page_title="SMS Phishing Tespit", page_icon="🛡️", layout="centered")

st.title("🛡️ Akıllı SMS Oltalama (Phishing) Analizörü")
st.markdown("""
Bu sistem, Doğal Dil İşleme (NLP) ve Makine Öğrenmesi kullanarak size gelen SMS'lerin 
dolandırıcılık (phishing) amacı taşıyıp taşımadığını saniyeler içinde analiz eder.
""")

mesaj_girdisi = st.text_area("Şüpheli mesajı aşağıya yapıştırın:", height=150)

if st.button("Mesajı Analiz Et", type="primary"):
    if mesaj_girdisi:
        gerekceler = []
        risk_skoru = 0
        tespit_edilen_kategoriler = []
        mesaj_lower = mesaj_girdisi.lower()

        # Kural 1: Link Analizi (Çok daha hassas)
        link_regex = r"(http://|https://|bit\.ly|tinyurl\.com|t\.co|ow\.ly|is\.gd|cutt\.ly|[a-zA-Z0-9.-]+\.(com|net|org|tr|xyz|info))"
        if re.search(link_regex, mesaj_girdisi, re.IGNORECASE):
            gerekceler.append("🔗 **Şüpheli Bağlantı:** Mesaj, sizi dış bir web sitesine yönlendiren bir link içeriyor. Dolandırıcılar genellikle sahte sitelere yönlendirmek için link kullanır.")
            risk_skoru += 45

        # Kural 2: Kategori Bazlı Kelime Analizi
        for kategori, kelimeler in KATEGORILER.items():
            if any(kelime in mesaj_lower for kelime in kelimeler):
                tespit_edilen_kategoriler.append(kategori)
                if kategori == "icra_hukuk":
                    gerekceler.append("⚖️ **Hukuki Tehdit:** Korkutma, icra, dava veya uzlaştırma gibi yasal kelimeler kullanılarak panik yaratılmaya çalışılıyor.")
                    risk_skoru += 35
                elif kategori == "banka_finans":
                    gerekceler.append("🏦 **Banka Oltalaması:** Hesabınızla veya kartınızla ilgili acil işlem yapmanızı gerektirecek bankacılık terimleri tespit edildi.")
                    risk_skoru += 30
                elif kategori == "kargo":
                    gerekceler.append("📦 **Sahte Kargo:** Kargonuzun teslim edilemediği veya adresin yanlış olduğu bahanesiyle sahte sitelere yönlendirme taktiği.")
                    risk_skoru += 30
                elif kategori == "odul_yardim":
                    gerekceler.append("🎁 **Sahte Ödül/Yardım:** Gerçek olamayacak kadar iyi vaatler (hediye, bedava para, yardım) ile tuzağa çekme girişimi.")
                    risk_skoru += 30
                elif kategori == "para_talebi":
                    gerekceler.append("💸 **Para/Ödeme Talebi:** Doğrudan para transferi, IBAN veya ödeme (bedel, masraf) isteniyor.")
                    risk_skoru += 35

        # Kural 3: Aciliyet Dili (Zaman Baskısı)
        aciliyet_kelimeleri = ["acil", "hemen", "derhal", "bugün", "son gün", "süre bitiyor"]
        if any(kelime in mesaj_lower for kelime in aciliyet_kelimeleri):
            gerekceler.append("⏱️ **Zaman Baskısı:** Mantıklı düşünmenizi engellemek için işlemin çok acil veya hemen yapılması gerektiği vurgulanıyor.")
            risk_skoru += 15

        # Kural 4: Yapay Zeka Makine Öğrenmesi (Bağlam Analizi)
        ml_tahmin = model.predict([mesaj_girdisi])[0]
        if ml_tahmin == 1:
            gerekceler.append("🧠 **Yapay Zeka Analizi:** Yapay zeka, cümlenin genel yapısını ve anlamını önceki binlerce dolandırıcılık vakasıyla eşleştirdi.")
            risk_skoru += 20
        elif ml_tahmin == 0 and risk_skoru == 0:
             # Eğer risk skoru 0 ise ve model de güvenli dediyse
             pass

        # Çıktı ve Ekrana Yazdırma
        toplam_risk = min(risk_skoru, 100) # Skor 100'ü geçmesin
        
        st.divider() # Araya çizgi çek
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric(label="Hesaplanan Risk Skoru", value=f"%{toplam_risk}")
            
        with col2:
            if toplam_risk >= 70:
                st.error("🚨 KRİTİK RİSK: Bu mesaj %99 ihtimalle dolandırıcılık (phishing) amaçlıdır! Kesinlikle içindeki linke tıklamayın ve para göndermeyin.")
            elif 30 <= toplam_risk < 70:
                st.warning("⚠️ ŞÜPHELİ: Bu mesajda riskli unsurlar bulundu. Teyit etmeden işlem yapmayınız.")
            else:
                st.success("✅ GÜVENLİ: Bu mesajda belirgin bir dolandırıcılık riski tespit edilmedi.")

        if toplam_risk > 0:
            st.subheader("🔍 Tespit Edilen Risk Nedenleri (Gerekçeler):")
            for g in gerekceler:
                st.markdown(g)
            
            # Formda bahsettiğiniz siber güvenlik farkındalığı uyarısı
            st.info("💡 **Tavsiye:** Kurumlar (Bankalar, PTT, e-Devlet) sizden SMS ile şifre veya doğrudan IBAN'a para istemez. Şüphelendiğiniz durumlarda kurumun resmi numarasını kendiniz tuşlayarak arayın.")