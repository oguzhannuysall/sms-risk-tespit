"""
SMS Güvenlik Asistanı v3  (kural + ML hibriti, Claude/API'siz)

KURULUM
  pip install -r requirements.txt
  streamlit run app.py

.streamlit/secrets.toml  (GitHub'a ASLA koyma, .gitignore'da):
  [ADMINS.alp]
  isim = "Muzaffer Alp Ergülcü"
  salt = "<hex>"
  hash = "<hex>"

  [ADMINS.oguzhan]
  isim = "Oğuzhan Uysal"
  salt = "<hex>"
  hash = "<hex>"

Salt + hash üretmek için (terminalde):
  python -c "import hashlib,os,getpass;s=os.urandom(16);print(s.hex(),hashlib.pbkdf2_hmac('sha256',getpass.getpass().encode(),s,200000).hex())"

VERİ KALICILIĞI (Streamlit Community Cloud'da disk geçicidir!)
  Yönetici panelindeki "Yedekle / Geri Yükle" bölümünden veriyi CSV olarak indirin.
  İndirdiğiniz dosyayı repoya `dataset.csv` adıyla koyarsanız, veritabanı boşken otomatik içe aktarılır.
  Kalıcı çözüm için Supabase / Turso gibi harici bir veritabanı kullanılabilir.
"""
import hashlib
import hmac
import os
import random
import sqlite3
import time
from contextlib import closing
from datetime import datetime

import pandas as pd
import streamlit as st

from kurallar import kural_analizi, maskele, metni_isaretle, normalize
from ml import ESIK, birlestir, degerlendir, egit, hazirla, metrikler as ml_metrikler, ml_skoru

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Istanbul")
except Exception:  # tzdata yoksa sunucu saatine düş
    TZ = None

DB_YOLU = os.environ.get("SMS_DB_YOLU", "sms_guvenlik.db")

# ======================================================================
# 1. SAYFA AYARLARI VE CSS
# ======================================================================
st.set_page_config(page_title="SMS Güvenlik Asistanı", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
/* Renkler Streamlit'in seçili temasına (açık/koyu/sistem) uyum sağlasın diye arka plan ve yazı rengi
   zorlanmaz; kartlar yarı saydam nötr tonlar kullanır, vurgu renkleri iki temada da okunur. */
.status-bar {background: rgba(128,128,128,0.10); border: 1px solid rgba(8,145,178,0.35);
  border-radius: 14px; padding: 12px 22px; margin-bottom: 24px; display: flex; justify-content: space-between;
  align-items: center;}
.status-badge {display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: #0891b2;
  background: rgba(8,145,178,0.12); padding: 5px 12px; border-radius: 20px; border: 1px solid rgba(8,145,178,0.35);}
div.stButton > button:first-child {border-radius: 12px; font-weight: 600; background: linear-gradient(135deg,#1e3c72 0%,#2a5298 100%);
  color: #fff; transition: all 0.25s ease; border: 1px solid rgba(0,242,254,0.2); padding: 0.55rem 1rem; box-shadow: 0 4px 14px rgba(0,0,0,0.2);}
div.stButton > button:first-child:hover {transform: translateY(-2px); box-shadow: 0 6px 22px rgba(0,114,255,0.35); border-color: #00c6ff; color: #fff;}
div.stButton > button[kind="primary"] {background: linear-gradient(135deg,#00c6ff 0%,#0072ff 100%); font-size: 16px; font-weight: 700; color: #fff;}
div[data-testid="metric-container"] {background: rgba(128,128,128,0.10); border: 1px solid rgba(8,145,178,0.30);
  padding: 18px 22px; border-radius: 16px;}
.stTextArea textarea, .stTextInput input {border-radius: 14px !important; border: 1px solid rgba(8,145,178,0.45) !important;
  font-size: 15px !important; padding: 14px !important;}
.highlight-box {background: rgba(128,128,128,0.10); border: 1px solid rgba(8,145,178,0.40); border-radius: 14px; padding: 18px;
  font-size: 15.5px; line-height: 1.8; margin-top: 10px; margin-bottom: 18px; overflow-wrap: anywhere;}
.danger-tag {background-color: rgba(255,75,75,0.18); color: #e53935; padding: 3px 8px; border-radius: 6px;
  border: 1px solid rgba(229,57,53,0.65); font-weight: 700;}
.safe-tag {background-color: rgba(8,145,178,0.15); color: #0891b2; padding: 3px 8px; border-radius: 6px;
  border: 1px solid rgba(8,145,178,0.55); font-weight: 700;}
.thermo-bg {width: 100%; background-color: rgba(128,128,128,0.25); border-radius: 12px; height: 22px; overflow: hidden; margin-top: 10px;
  border: 1px solid rgba(128,128,128,0.35);}
.thermo-fill {height: 100%; border-radius: 12px; transition: width 0.5s ease-out;}
.reason-card {background: rgba(128,128,128,0.08); border-left: 4px solid #0891b2; padding: 12px 16px;
  border-radius: 0 10px 10px 0; margin-bottom: 10px; font-size: 14.5px;}
</style>
""", unsafe_allow_html=True)


# ======================================================================
# 2. VERİTABANI
# ======================================================================
def simdi():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _baglan():
    con = sqlite3.connect(DB_YOLU, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")  # eşzamanlı okuma/yazmada kilitlenmeyi azaltır
    return con


def sorgu(sql, params=(), yaz=False):
    with closing(_baglan()) as con:
        cur = con.execute(sql, params)
        if yaz:
            con.commit()
            return cur.lastrowid
        return cur.fetchall()


def toplu_ekle(satirlar):
    """satirlar: [(mesaj, etiket), ...]"""
    if not satirlar:
        return
    with closing(_baglan()) as con:
        con.executemany("INSERT INTO mesajlar(mesaj, etiket) VALUES (?, ?)", satirlar)
        con.commit()


def veri_oku():
    with closing(_baglan()) as con:
        return pd.read_sql_query("SELECT id, mesaj, etiket FROM mesajlar", con)


@st.cache_resource(show_spinner=False)
def db_hazirla():
    with closing(_baglan()) as con:
        con.execute("CREATE TABLE IF NOT EXISTS mesajlar (id INTEGER PRIMARY KEY AUTOINCREMENT, mesaj TEXT NOT NULL, etiket INTEGER NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS oneriler (id INTEGER PRIMARY KEY AUTOINCREMENT, mesaj TEXT NOT NULL, etiket INTEGER NOT NULL, tarih TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS geri_bildirim (id INTEGER PRIMARY KEY AUTOINCREMENT, mesaj TEXT, risk INTEGER, dogru INTEGER, tarih TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS giris_denemeleri (id INTEGER PRIMARY KEY AUTOINCREMENT, kadi TEXT NOT NULL, zaman REAL NOT NULL)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_giris ON giris_denemeleri(kadi, zaman)")
        if con.execute("SELECT COUNT(*) FROM mesajlar").fetchone()[0] == 0:
            try:  # repodaki dataset.csv varsa bir kereliğine içe aktar
                eski = pd.read_csv("dataset.csv", on_bad_lines="skip").dropna(subset=["mesaj", "etiket"])
                satirlar = [(str(m), int(e)) for m, e in zip(eski["mesaj"], eski["etiket"])]
            except Exception:
                satirlar = [
                    ("PTT Kargo: Gonderiniz teslim edilemedi. Lutfen adresinizi guncelleyin: http://bit.ly/kargo-onay", 1),
                    ("Hakkınızda icra takibi başlatılmıştır. Borcunuzu ödemek için e-devlet-sorgu.com adresine giriniz.", 1),
                    ("Yarın saat 14:00'te toplantımız var, lütfen gecikmeyin.", 0),
                ]
            con.executemany("INSERT INTO mesajlar(mesaj, etiket) VALUES (?, ?)", satirlar)
        con.commit()
    return True


db_hazirla()


def veri_surumu():
    n, son = sorgu("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM mesajlar")[0]
    return (n, son)


def mesaj_var_mi(m):
    """Normalleşince aynı olan bir mesaj hem kayıtlarda hem bekleyen önerilerde aranır."""
    n = normalize(m)
    return any(normalize(x) == n for (x,) in sorgu("SELECT mesaj FROM mesajlar UNION SELECT mesaj FROM oneriler"))


def mesaj_var_mi_mesajlarda(m):
    n = normalize(m)
    return any(normalize(x) == n for (x,) in sorgu("SELECT mesaj FROM mesajlar"))


# ======================================================================
# 3. MODEL (önbellekli)
# ======================================================================
@st.cache_resource(show_spinner=False, max_entries=2)
def model_getir(surum):
    return egit(hazirla(veri_oku()))  # (model, guvenilir)


@st.cache_data(show_spinner=False, max_entries=2)
def degerlendirme_getir(surum):
    return degerlendir(veri_oku())


def mesaji_analiz_et(mesaj):
    k = kural_analizi(mesaj)
    model, guvenilir = model_getir(veri_surumu())
    ml = ml_skoru(model, mesaj)
    risk, kural, notlar = birlestir(k, ml, guvenilir)
    return {"risk": risk, "kural": kural, "ml": ml, "ml_guvenilir": guvenilir,
            "gerekceler": list(k["gerekceler"]) + notlar, "kelimeler": k["kelimeler"], "linkler": k["linkler"],
            "guvenli_link": k["guvenli"] and not k["tehlikeli"]}


# ======================================================================
# 4. DURUM, ÖRNEKLER, CALLBACK'LER
# ======================================================================
for anahtar, deger in {"aktif_mesaj": "", "otomatik_analiz": False, "son_sonuc": None, "admin_giris": False,
                       "aktif_yonetici": "", "fb_sayac": 0, "oneri_sayac": 0, "sayfa": "ana"}.items():
    st.session_state.setdefault(anahtar, deger)

# Sayfa değişince widget durumunun silinmemesi için (yazılan mesaj kaybolmasın)
if "aktif_mesaj" in st.session_state:
    st.session_state.aktif_mesaj = st.session_state.aktif_mesaj

ORNEK_HAVUZU = {
    "icra_banka": [
        "Sn. Vatandaş, hakkınızda açılacak cinsel taciz davası bulunmaktadır. Uzlaştırma bedeli olan 5000 TL'yi hemen hesaba yatırın: hukuk-odeme.com",
        "Ziraat Bankası: Hesabınızdan şüpheli işlem tespit edilmiştir. Bloke konulmaması için derhal doğrulayın: ziraat-guvenlik.xyz",
        "Hukuk Bürosu: Hakkınızda başlatılan icra takibini durdurmak için bugün mesai bitimine kadar 3.850 TL dosya masrafını IBAN'a gönderin.",
        "Garanti BBVA: Mobil şube erişiminiz güvenlik nedeniyle kısıtlanmıştır. Kimlik onayı için tıklayın: http://tinyurl.com/garanti-onay",
        "Ağır Ceza Mahkemesi: Yasa dışı bahis soruşturması kapsamında adınıza ceza kesilmiştir. Evrakları görmek için: uyap-vatandas.net"],
    "kargo_odul": [
        "PTT Kargo: Gönderiniz adres yetersizliği nedeniyle teslim edilemedi. Adresinizi güncellemek için tıklayın: http://bit.ly/ptt-guncelle",
        "MNG Kargo: Dağıtıma çıkan 482910 nolu kargonuz iade sürecine girmiştir. Tekrar dağıtım talebi için: mng-teslimat.xyz",
        "E-Devlet Kapısı: Aile destek paketi kapsamında 4.500 TL yardım başvurunuz onaylandı. Hesaba çekmek için: edevlet-destek.org",
        "Tebrikler! Trendyol çekilişinden 10.000 TL değerinde hediye çeki kazandınız. Süre bitiyor, hemen alın: trendyol-ikramiye.net",
        "Yurtiçi Kargo: Paketiniz gümrük vergisi ödenmediği için depoda bekletiliyor. 85 TL ödeme yapmak için: yurtici-gumruk.com"],
    "kelime_oyunu": [
        "Sayin musteri hesabiniza b.l.o.k.e konulmustur. Acil islem icin tiklayin: tinyurl.com/banka-onay",
        "Hakkınızda i.c.r.a takibi başlatılmıştır. Mağdur olmamak için bugün e-devlet-sorgu.xyz adresine giriniz.",
        "Uzlastirma burosu: d.a.v.a dosyanizin kapanmasi icin 6000 TL p4r4 transferini hemen yapiniz: uzlasma-merkezi.com",
        "PTT Kargo: K4rgonuz adres hatasi nedeniyle t.e.s.l.i.m edilemedi. Hemen tiklayin: bit.ly/kargo-takip"],
    "guvenli": [
        "Yarın saat 14:00'te proje toplantımız var, lütfen gecikmeyin. İyi çalışmalar.",
        "Şu faydalı eğitim videosuna mutlaka baksana: https://www.youtube.com/watch?v=aircAruvnKk",
        "Ziraat Bankası: 4821 nolu kartınızla 340,00 TL tutarında market alışverişi yapılmıştır. B001",
        "Yurtiçi Kargo: 84920192 takip numaralı gönderiniz teslim edilmek üzere çıkarılmıştır. B018",
        "Kanka akşam halı saha maçına geliyorsun değil mi? Kramponları unutma."],
}


def ornek_getir(kategori):
    havuz = ORNEK_HAVUZU[kategori]
    alternatifler = [m for m in havuz if m != st.session_state.aktif_mesaj]
    st.session_state.aktif_mesaj = random.choice(alternatifler) if alternatifler else havuz[0]
    st.session_state.otomatik_analiz = True


def kutuyu_temizle():
    st.session_state.aktif_mesaj = ""
    st.session_state.otomatik_analiz = False
    st.session_state.son_sonuc = None


def geri_bildirim_kaydet(mesaj, risk, dogru):
    son = st.session_state.son_sonuc
    if not son or son.get("fb"):
        return  # aynı sonuca tekrar oy verilemez
    if st.session_state.fb_sayac >= 20:
        st.toast("Bu oturum için geri bildirim sınırına ulaştınız.", icon="⚠️")
        return
    sorgu("INSERT INTO geri_bildirim(mesaj, risk, dogru, tarih) VALUES (?, ?, ?, ?)",
          (maskele(mesaj)[:1000], int(risk), int(dogru), simdi()), yaz=True)  # kişisel veriler maskelenerek saklanır
    son["fb"] = True
    st.session_state.fb_sayac += 1
    st.toast("Geri bildiriminiz için teşekkürler!", icon="🙏")


# ---- Yönetici girişi: deneme sınırı veritabanında (sayfa yenilemekle sıfırlanmaz) ----
KILIT_SURE, KILIT_ESIK, GLOBAL_ESIK = 900, 5, 50
DUMMY_TUZ = bytes(16)


def giris_kilitli_mi(kadi):
    sinir = time.time() - KILIT_SURE
    k = sorgu("SELECT COUNT(*) FROM giris_denemeleri WHERE kadi = ? AND zaman > ?", (kadi, sinir))[0][0]
    g = sorgu("SELECT COUNT(*) FROM giris_denemeleri WHERE zaman > ?", (sinir,))[0][0]
    return k >= KILIT_ESIK or g >= GLOBAL_ESIK


def admin_dogrula(kadi, sifre):
    """Kullanıcı yoksa da aynı maliyette hash hesaplanır (kullanıcı adı sızdırmamak için)."""
    try:
        adminler = st.secrets["ADMINS"]
        h = adminler[kadi] if kadi in adminler else None
        tuz = bytes.fromhex(h["salt"]) if h else DUMMY_TUZ
        denen = hashlib.pbkdf2_hmac("sha256", sifre.encode(), tuz, 200_000).hex()
        if h and hmac.compare_digest(denen, str(h["hash"]).strip().lower()):
            return h["isim"]
    except Exception:
        pass
    return None


def admin_tanimli_mi():
    try:
        return len(st.secrets["ADMINS"]) > 0
    except Exception:
        return False


# ======================================================================
# 5. SAYFALAR
# ======================================================================
def sayfa_ana():
    st.title("🛡️ SMS Güvenlik Asistanı")
    st.markdown("""
    ### Telefonunuza Gelen O Mesaj Gerçek mi, Tuzak mı?
    Günümüzde telefonlarımıza sürekli gelen **sahte kargo, ödül, e-Devlet veya icra** mesajları hayatımızı tehdit ediyor.
    Bu uygulama sayesinde şüpheli mesajları anında test edebilir, dolandırıcıların tuzaklarına karşı güvende kalabilirsiniz.
    """)
    sonuc = degerlendirme_getir(veri_surumu())
    f1 = f"%{sonuc['Hibrit']['f1'] * 100:.1f}" if sonuc else "Veri yetersiz"
    k1, k2, k3 = st.columns(3)
    k1.metric("Analiz Katmanı", "Kural + ML", "Hibrit sistem")
    k2.metric("Ölçülen F1 (hibrit)", f1, "Ayrılmış test seti")
    k3.metric("Kullanım Amacı", "Farkındalık", "Herkes İçin Kolay")
    st.write("")
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 HEMEN MESAJ TEST ET", type="primary", width="stretch"):
            st.session_state.sayfa = "analiz"
            st.rerun()


def sayfa_analiz():
    st.title("🛡️ SMS Güvenlik Kontrolü")
    st.write("Merak ettiğiniz mesajı kutuya yapıştırın ya da aşağıdaki örnek butonlarına tıklayın.")
    st.caption("🔒 Analiz tamamen bu sunucuda yapılır, mesajınız harici bir servise gönderilmez ve kaydedilmez. "
               "Yalnızca “Doğru/Yanlış” geri bildirimi verirseniz, kişisel veriler maskelenmiş hâliyle saklanır.")

    colA, colB, colC, colD = st.columns(4)
    colA.button("🚨 İcra / Banka Tuzağı", on_click=ornek_getir, args=("icra_banka",), width="stretch")
    colB.button("📦 Sahte Kargo / Ödül", on_click=ornek_getir, args=("kargo_odul",), width="stretch")
    colC.button("🕵️ Gizlenmiş Kelime", on_click=ornek_getir, args=("kelime_oyunu",), width="stretch")
    colD.button("✅ Güvenli Kurum Mesajı", on_click=ornek_getir, args=("guvenli",), width="stretch")

    mesaj_girdisi = st.text_area("Kontrol Edilecek SMS Metni:", key="aktif_mesaj", height=115, max_chars=1000,
                                 placeholder="Buraya test etmek istediğiniz mesajı yazın veya yapıştırın...")
    b1, b2 = st.columns([4, 1])
    analiz_baslat = b1.button("🔍 Mesajı Güvenli mi Diye Kontrol Et", type="primary", width="stretch")
    b2.button("🗑️ Temizle", on_click=kutuyu_temizle, width="stretch")

    mesaj = mesaj_girdisi.strip()
    son = st.session_state.son_sonuc
    otomatik = st.session_state.otomatik_analiz and mesaj and (not son or son["mesaj"] != mesaj)

    if analiz_baslat and not mesaj:
        st.warning("Lütfen kontrol edilecek bir mesaj yazın.")
    elif (analiz_baslat and mesaj) or otomatik:
        with st.spinner("Mesaj inceleniyor..."):
            st.session_state.son_sonuc = {"mesaj": mesaj, "sonuc": mesaji_analiz_et(mesaj), "fb": False}
        st.session_state.otomatik_analiz = False

    son = st.session_state.son_sonuc
    if not (son and mesaj and son["mesaj"] == mesaj):
        return

    s = son["sonuc"]
    risk = s["risk"]
    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric(label="Risk Oranı", value=f"%{risk}")
        renk = "#ff4b4b" if risk >= 70 else ("#ffa500" if risk >= 30 else "#00e676")
        durum = "TEHLİKELİ" if risk >= 70 else ("ŞÜPHELİ" if risk >= 30 else "GÜVENLİ")
        st.markdown(f"""
        <div class="thermo-bg"><div class="thermo-fill" style="width:{risk}%;background-color:{renk};"></div></div>
        <div style="display:flex;justify-content:space-between;font-size:12.5px;opacity:0.85;margin-top:6px;font-weight:600;">
          <span>Durum: <b style="color:{renk};">{durum}</b></span><span>%{risk}</span></div>
        """, unsafe_allow_html=True)
    with c2:
        if risk >= 70:
            st.error("🚨 **DİKKAT! Bu mesaj büyük ihtimalle bir dolandırıcılık tuzağıdır.** İçindeki linke tıklamayın, para göndermeyin, kişisel bilgilerinizi vermeyin.")
        elif risk >= 30:
            st.warning("⚠️ **ŞÜPHELİ DURUM!** Bu mesajda tehlikeli işaretler var. Kurumu kendi resmi telefonundan arayıp teyit etmeden adım atmayın.")
        else:
            st.success("✅ **GÖRÜNÜŞE GÖRE GÜVENLİ.** Bu mesajda belirgin bir dolandırıcılık izine rastlanmadı. Yine de tanımadığınız linklere dikkat edin.")

    if s["kelimeler"] or s["linkler"]:
        st.subheader("🖍️ Mesajda Tespit Edilen Riskli Bölümler:")
        st.markdown(f'<div class="highlight-box">{metni_isaretle(mesaj, s["kelimeler"], s["linkler"], s["guvenli_link"])}</div>',
                    unsafe_allow_html=True)

    if s["gerekceler"]:
        st.subheader("🔍 Bu Sonuca Neden Vardık?")
        for g in s["gerekceler"]:
            st.markdown(f'<div class="reason-card">{g}</div>', unsafe_allow_html=True)

    with st.expander("📊 Skor ayrıntısı"):
        if s["ml_guvenilir"]:
            st.write(f"Kural katmanı: **{s['kural']}** (ağırlık %70) · ML benzerliği: **{s['ml']}** (ağırlık %30) · Nihai: **{s['risk']}**")
        else:
            st.write(f"Kural katmanı: **{s['kural']}** · ML benzerliği: **{s['ml']}** (kayıtlı veri henüz yetersiz olduğu için skora katılmadı) · Nihai: **{s['risk']}**")

    if son["fb"]:
        st.caption("🙏 Geri bildiriminiz kaydedildi.")
    else:
        st.caption("Bu sonuç doğru muydu?")
        f1, f2, _ = st.columns([1, 1, 4])
        f1.button("👍 Doğru", key="fb_dogru", on_click=geri_bildirim_kaydet, args=(mesaj, risk, True))
        f2.button("👎 Yanlış", key="fb_yanlis", on_click=geri_bildirim_kaydet, args=(mesaj, risk, False))


def sayfa_oneri():
    st.title("📥 Yeni Mesaj Önerin")
    st.markdown("Bildiğiniz yeni bir dolandırıcılık mesajı veya güvenli bir örnek varsa buraya yazarak sistemin gelişimine katkıda bulunabilirsiniz.")
    st.caption("Telefon, TC, IBAN, kart ve e-posta gibi kişisel bilgiler gönderimde otomatik olarak maskelenir; yine de mümkünse siz de silin.")
    yeni_mesaj = st.text_area("Önermek istediğiniz SMS metni:", max_chars=500)
    etiket_secimi = st.radio("Bu mesajın türü nedir?", ["🚨 Dolandırıcılık / Tuzak Mesaj", "✅ Normal / Güvenli Mesaj"])

    if st.button("📤 İncelemeye Gönder", type="primary"):
        temiz = maskele(" ".join(yeni_mesaj.split()))
        if st.session_state.oneri_sayac >= 5:
            st.warning("Bu oturum için öneri sınırına (5) ulaştınız. Teşekkürler!")
        elif len(temiz) < 10:
            st.warning("Lütfen en az 10 karakterlik bir mesaj girin.")
        elif mesaj_var_mi(temiz):
            st.info("Bu mesaj zaten sistemde var. Teşekkürler!")
        else:
            sorgu("INSERT INTO oneriler(mesaj, etiket, tarih) VALUES (?, ?, ?)",
                  (temiz, 1 if "Dolandırıcılık" in etiket_secimi else 0, simdi()), yaz=True)
            st.session_state.oneri_sayac += 1
            st.success("✅ Öneriniz yönetici onayına gönderildi. Teşekkürler!")


def _metrik_tablosu(sonuc):
    satirlar = []
    for ad in ("Yalnız kural", "Yalnız ML", "Hibrit"):
        m = sonuc[ad]
        satirlar.append({"Sistem": ad, "Doğruluk": f"%{m['accuracy'] * 100:.1f}", "Kesinlik": f"%{m['precision'] * 100:.1f}",
                         "Yakalama": f"%{m['recall'] * 100:.1f}", "F1": f"%{m['f1'] * 100:.1f}"})
    return pd.DataFrame(satirlar)


def _cm_tablosu(cm):
    return pd.DataFrame(cm, index=["Gerçek: Güvenli", "Gerçek: Tuzak"], columns=["Tahmin: Güvenli", "Tahmin: Tuzak"])


def sayfa_sistem():
    st.title("🧠 Sistem Nasıl Çalışıyor?")
    tab1, tab2, tab3 = st.tabs(["🧪 Ölçülen Başarı", "📂 Kendi Test Setinle Ölç", "📘 Basit Çalışma Mantığı"])

    with tab1:
        st.subheader("🎯 Ayrılmış Test Seti Üzerinde Gerçek Metrikler")
        sonuc = degerlendirme_getir(veri_surumu())
        if sonuc:
            st.caption(f"Tekrar eden {sonuc['tekrar_elenen']} kayıt elendi. Kalan veri %75 eğitim ({sonuc['egitim_adet']}) / %25 test "
                       f"({sonuc['test_adet']}) olarak ayrıldı; ML modeli test mesajlarını eğitimde görmedi. "
                       f"Üç sistem aynı test setinde karşılaştırılır (risk ≥ %{ESIK} → “tuzak”). "
                       "Not: Kural katmanı eğitim gerektirmez ama kurallar bilinen örnekler görülerek yazıldığı için sonucu iyimser gösterebilir.")
            st.dataframe(_metrik_tablosu(sonuc), width="stretch", hide_index=True)
            cm = sonuc["Hibrit"]["cm"]
            st.markdown("**Hibrit sistem karışıklık matrisi**")
            st.dataframe(_cm_tablosu(cm), width="stretch")
            st.caption(f"Kaçırılan tuzak: {cm[1][0]} · Yanlış alarm: {cm[0][1]}")
        else:
            st.info("Anlamlı metrik için tekrarsız en az 30 kayıt ve her sınıftan en az 6 örnek gerekir. "
                    "Admin panelinden onaylanan öneriler arttıkça burası dolacak.")

    with tab2:
        st.subheader("📂 Kendi Test Setinle Ölç")
        st.write("Sistemin hiç görmediği mesajlarla gerçek başarıyı ölçmek için `mesaj` ve `etiket` (1=tuzak, 0=güvenli) "
                 "sütunlu bir CSV yükleyin (ör. Kaggle / Hugging Face'teki Türkçe SMS veri setlerinden). "
                 "Eğitim verisiyle aynı olan mesajlar otomatik elenir.")
        dosya = st.file_uploader("CSV dosyası", type="csv", key="test_csv")
        if dosya is not None and st.button("▶️ Ölç", type="primary", key="olc_btn"):
            try:
                t = pd.read_csv(dosya, on_bad_lines="skip").dropna(subset=["mesaj", "etiket"])
                t["etiket"] = t["etiket"].astype(int)
                t = t[t["etiket"].isin([0, 1])].head(2000)
                t["norm"] = t["mesaj"].astype(str).map(normalize)
                egitimdekiler = set(hazirla(veri_oku())["norm"])
                onceki = len(t)
                t = t[~t["norm"].isin(egitimdekiler)].drop_duplicates("norm")
                hata = None
            except Exception:
                t, hata, onceki = None, "CSV okunamadı. `mesaj` ve `etiket` sütunları olduğundan emin olun.", 0
            if hata:
                st.error(hata)
            elif len(t) < 10:
                st.warning("Eğitim verisiyle çakışanlar elendikten sonra en az 10 mesaj kalmalı.")
            else:
                tahmin = [int(mesaji_analiz_et(str(m))["risk"] >= ESIK) for m in t["mesaj"]]
                m = ml_metrikler(t["etiket"], tahmin)
                st.caption(f"{onceki - len(t)} mesaj elendi (eğitimde var/tekrar). Ölçülen mesaj sayısı: {len(t)}")
                a, b, c, d = st.columns(4)
                a.metric("Doğruluk", f"%{m['accuracy'] * 100:.1f}")
                b.metric("Kesinlik", f"%{m['precision'] * 100:.1f}", help="'Tuzak' dediklerinin kaçı gerçekten tuzak")
                c.metric("Yakalama", f"%{m['recall'] * 100:.1f}", help="Gerçek tuzakların kaçını yakaladı")
                d.metric("F1", f"%{m['f1'] * 100:.1f}")
                st.dataframe(_cm_tablosu(m["cm"]), width="stretch")

    with tab3:
        st.markdown("""
        ### Bu Asistan Mesajları Nasıl İnceliyor?
        1. **Link Kontrolü:** Adres resmi bir alan adı mı, kısaltılmış mı, IP ile mi verilmiş, bir kurumu taklit ediyor mu diye bakar. Mesajda adı geçen kurumun resmi sitesiyle linkin uyuşup uyuşmadığını da kontrol eder.
        2. **Tehlikeli İfadeler:** 'icra', 'bloke', 'acil', 'IBAN' gibi dolandırıcıların sık kullandığı ifadeleri tarar; Türkçe ekleri (davası, icradan) ve büyük/küçük harf farklarını tanır.
        3. **Kelime Oyunu Çözücü:** `i.c.r.a` veya `p4r4` gibi gizlemeleri çözüp asıl kelimeyi okur.
        4. **Yapay Zeka (ML):** Mesajın yazım tarzını kayıtlı örneklerle karşılaştırıp benzerlik yüzdesi çıkarır. Kayıtlı veri yetersizse ML skora katılmaz.
        5. **Birleştirme:** Nihai skor %70 kural + %30 ML'dir. Yalnızca bilinen güvenli adres içeren ve riskli ifade barındırmayan mesajların riski düşük tutulur.
        """)


def sayfa_admin():
    st.title("🔒 Yönetici Paneli")

    if not st.session_state.admin_giris:
        if not admin_tanimli_mi():
            st.warning("Yönetici hesabı tanımlı değil. `.streamlit/secrets.toml` içine `[ADMINS.kullanici]` bölümü ekleyin (dosyanın başındaki açıklamaya bakın).")
        else:
            st.write("Giriş yapın.")
            g1, g2, g3 = st.columns(3)
            kadi = g1.text_input("👤 Kullanıcı Adı:").strip().lower()[:40]
            sifre = g2.text_input("🔑 Şifre:", type="password")
            g3.write("")
            g3.write("")
            if g3.button("Giriş Yap", type="primary"):
                if giris_kilitli_mi(kadi):
                    st.error("Çok fazla hatalı deneme. Lütfen 15 dakika sonra tekrar deneyin.")
                else:
                    isim = admin_dogrula(kadi, sifre)
                    if isim:
                        sorgu("DELETE FROM giris_denemeleri WHERE kadi = ?", (kadi,), yaz=True)
                        st.session_state.admin_giris, st.session_state.aktif_yonetici = True, isim
                        st.rerun()
                    else:
                        sorgu("INSERT INTO giris_denemeleri(kadi, zaman) VALUES (?, ?)", (kadi, time.time()), yaz=True)
                        st.error("❌ Hatalı kullanıcı adı veya şifre!")

    if not st.session_state.admin_giris:
        return

    df = veri_oku()
    st.success(f"🔓 Hoş Geldiniz, **{st.session_state.aktif_yonetici}**.")
    if st.button("🚪 Çıkış Yap"):
        st.session_state.admin_giris, st.session_state.aktif_yonetici = False, ""
        st.rerun()

    st.divider()
    phishing_sayisi = int((df["etiket"] == 1).sum())
    guvenli_sayisi = int((df["etiket"] == 0).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Kayıtlı Mesaj", f"{len(df)}")
    c2.metric("Tuzak Mesaj", f"{phishing_sayisi}")
    c3.metric("Güvenli Mesaj", f"{guvenli_sayisi}")

    st.divider()
    st.subheader("📈 Veri Dağılımı")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Mesaj Türü Dağılımı**")
        st.bar_chart(pd.DataFrame({"Tür": ["Tuzak", "Güvenli"], "Adet": [phishing_sayisi, guvenli_sayisi]}).set_index("Tür"), color="#00f2fe")
    with g2:
        st.markdown("**En Sık Geçen Tehdit Kelimeleri**")
        metinler = " ".join(df[df["etiket"] == 1]["mesaj"].astype(str).map(normalize))
        aranan = ["kargo", "icra", "hesap", "bloke", "tl", "iptal", "link", "odeme"]
        st.bar_chart(pd.DataFrame({"Kelime": [k.upper() for k in aranan], "Sıklık": [metinler.count(k) for k in aranan]}).set_index("Kelime"), color="#ff4b4b")

    st.divider()
    st.subheader("💾 Yedekle / Geri Yükle")
    st.caption("Streamlit Cloud'da disk geçicidir: yeniden başlatmada veri silinir. Düzenli olarak yedek alın. "
               "İndirdiğiniz dosyayı repoya `dataset.csv` adıyla koyarsanız veritabanı boşken otomatik yüklenir.")
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Mesajları CSV indir", df[["mesaj", "etiket"]].to_csv(index=False).encode("utf-8-sig"),
                       file_name="dataset.csv", mime="text/csv")
    yuklenen = d2.file_uploader("CSV içe aktar (mesaj, etiket)", type="csv", key="admin_csv")
    if yuklenen is not None and d2.button("📥 İçe Aktar"):
        try:
            yeni = pd.read_csv(yuklenen, on_bad_lines="skip").dropna(subset=["mesaj", "etiket"])
            mevcut = {normalize(m) for m in df["mesaj"]}
            satirlar = []
            for m, e in zip(yeni["mesaj"], yeni["etiket"]):
                m = maskele(" ".join(str(m).split()))
                if int(e) in (0, 1) and len(m) >= 10 and normalize(m) not in mevcut:
                    mevcut.add(normalize(m))
                    satirlar.append((m, int(e)))
            toplu_ekle(satirlar)
            st.success(f"{len(satirlar)} yeni mesaj eklendi.")
            st.rerun()
        except Exception:
            st.error("CSV içe aktarılamadı. `mesaj` ve `etiket` sütunlarını kontrol edin.")

    st.divider()
    st.subheader("⏳ Onay Bekleyen Kullanıcı Önerileri")
    bekleyenler = sorgu("SELECT id, mesaj, etiket, tarih FROM oneriler ORDER BY id")
    if not bekleyenler:
        st.info("Onay bekleyen yeni öneri bulunmuyor.")
    for oid, omesaj, oetiket, otarih in bekleyenler:
        with st.container():
            st.text(omesaj)  # düz metin: kullanıcı içeriği asla HTML/markdown olarak render edilmez
            st.caption(f"Tür: {'🚨 Tuzak' if oetiket == 1 else '✅ Güvenli'} · {otarih}")
            b1, b2, _ = st.columns([1.3, 1, 4])
            if b1.button("✅ Onayla ve Ekle", key=f"ekle_{oid}"):
                if not mesaj_var_mi_mesajlarda(omesaj):
                    sorgu("INSERT INTO mesajlar(mesaj, etiket) VALUES (?, ?)", (omesaj, oetiket), yaz=True)
                sorgu("DELETE FROM oneriler WHERE id = ?", (oid,), yaz=True)
                st.rerun()  # veri sürümü değiştiği için model otomatik yeniden eğitilir
            if b2.button("🗑️ Sil", key=f"sil_{oid}"):
                sorgu("DELETE FROM oneriler WHERE id = ?", (oid,), yaz=True)
                st.rerun()
        st.markdown("---")

    st.divider()
    st.subheader("💬 Kullanıcıların “Yanlış” Dediği Sonuçlar")
    yanlislar = sorgu("SELECT id, mesaj, risk, tarih FROM geri_bildirim WHERE dogru = 0 ORDER BY id DESC LIMIT 50")
    if not yanlislar:
        st.info("Henüz olumsuz geri bildirim yok.")
    else:
        st.caption("Sistem yüksek risk verip kullanıcı “yanlış” dediyse mesaj büyük ihtimalle güvenlidir (ve tersi). "
                   "İnceleyip doğru etiketle veri setine ekleyebilirsiniz.")
    for fid, fmesaj, frisk, ftarih in yanlislar:
        onerilen = 0 if frisk >= ESIK else 1
        st.text(fmesaj)
        st.caption(f"Verilen risk: %{frisk} · Önerilen etiket: {'🚨 Tuzak' if onerilen else '✅ Güvenli'} · {ftarih}")
        f1, f2, _ = st.columns([2, 1, 4])
        if f1.button("➕ Önerilen etiketle ekle", key=f"fe_{fid}"):
            if not mesaj_var_mi_mesajlarda(fmesaj):
                sorgu("INSERT INTO mesajlar(mesaj, etiket) VALUES (?, ?)", (fmesaj, onerilen), yaz=True)
            sorgu("DELETE FROM geri_bildirim WHERE id = ?", (fid,), yaz=True)
            st.rerun()
        if f2.button("🗑️ Yoksay", key=f"fs_{fid}"):
            sorgu("DELETE FROM geri_bildirim WHERE id = ?", (fid,), yaz=True)
            st.rerun()
        st.markdown("---")


# ======================================================================
# 6. YAN MENÜ, ÜST ÇUBUK, SAYFA YÖNLENDİRME
# ======================================================================
SAYFALAR = {
    "ana": ("🏠 Ana Sayfa", sayfa_ana),
    "analiz": ("🛡️ SMS Kontrol Aracı", sayfa_analiz),
    "oneri": ("📥 Mesaj Öner", sayfa_oneri),
    "sistem": ("🧠 Sistem Nasıl Çalışır?", sayfa_sistem),
    "admin": ("👨‍💻 Yönetici Paneli", sayfa_admin),
}

st.sidebar.title("📌 Menü")
for anahtar, (etiket, _) in SAYFALAR.items():
    if st.sidebar.button(etiket, key=f"menu_{anahtar}", width="stretch"):
        st.session_state.sayfa = anahtar

st.sidebar.divider()

st.sidebar.markdown("""
<style>
.info-box {background: linear-gradient(135deg,#0f2027 0%,#203a43 50%,#2c5364 100%); border-radius: 14px; padding: 16px; color: #e0e6ed;
  font-size: 13px; line-height: 1.5; box-shadow: 0 8px 25px rgba(0,0,0,0.4); text-align: center; height: 175px; display: flex;
  flex-direction: column; position: relative; overflow: hidden; border: 1px solid rgba(38,208,206,0.3); margin-bottom: 20px;}
.info-header {font-weight: 800; font-size: 15px; margin-bottom: 8px; color: #00f2fe;}
.text-container {position: relative; height: 100%; width: 100%; display: flex; align-items: center; justify-content: center;}
.ticker-text {position: absolute; width: 100%; opacity: 0; animation: fadeCycle 60s infinite;}
.ticker-text:nth-child(1){animation-delay:0s}.ticker-text:nth-child(2){animation-delay:10s}.ticker-text:nth-child(3){animation-delay:20s}
.ticker-text:nth-child(4){animation-delay:30s}.ticker-text:nth-child(5){animation-delay:40s}.ticker-text:nth-child(6){animation-delay:50s}
@keyframes fadeCycle {0%{opacity:0;transform:translateY(8px)}3%{opacity:1;transform:translateY(0)}15%{opacity:1;transform:translateY(0)}
  18%{opacity:0;transform:translateY(-8px)}100%{opacity:0;transform:translateY(-8px)}}
.dev-card {background: linear-gradient(135deg,#161B22 0%,#0D1117 100%); border-radius: 14px; padding: 16px;
  border: 1px solid rgba(78,67,118,0.5); box-shadow: 0 6px 20px rgba(0,0,0,0.3);}
.dev-title {color: #a8c0ff; font-size: 13px; font-weight: 800; margin-bottom: 12px; text-transform: uppercase;}
.dev-item {display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: rgba(255,255,255,0.03);
  border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #00f2fe;}
.dev-name {color: #fff; font-size: 13.5px; font-weight: 600;}
.dev-badge {margin-left: auto; font-size: 10px; background: rgba(0,242,254,0.15); color: #00f2fe; padding: 2px 6px; border-radius: 4px; font-weight: 700;}
</style>
<div class="info-box">
  <div class="info-header">💡 Güvenlik İpuçları</div>
  <div class="text-container">
    <div class="ticker-text">Resmi kurumlar asla SMS içinde doğrudan şifre veya para transferi istemez.</div>
    <div class="ticker-text">Kısaltılmış linkler (<b>bit.ly</b> vb.) gerçek adresi gizler; tıklamadan önce düşünün.</div>
    <div class="ticker-text">Dolandırıcılar sizi <b>acele ettirerek</b> teyit etmenizi engellemeye çalışır.</div>
    <div class="ticker-text">Şüphelendiğinizde kurumu <b>kendi resmi hattından</b> arayıp teyit edin.</div>
    <div class="ticker-text">Tek kullanımlık şifrenizi (OTP) <b>kimseyle</b> paylaşmayın.</div>
    <div class="ticker-text">Adres çubuğunda yazan alan adı, kurumun gerçek adıyla <b>birebir</b> aynı mı?</div>
  </div>
</div>
<div class="dev-card">
  <div class="dev-title">⚡ Geliştirici Ekibi</div>
  <div class="dev-item"><span>👨‍💻</span><span class="dev-name">Muzaffer Alp Ergülcü</span><span class="dev-badge">Yazılım</span></div>
  <div class="dev-item" style="margin-bottom:0;border-left-color:#a8c0ff;"><span>👨‍💻</span><span class="dev-name">Oğuzhan Uysal</span>
    <span class="dev-badge" style="color:#a8c0ff;background:rgba(168,192,255,0.15);">Güvenlik</span></div>
</div>
""", unsafe_allow_html=True)

n_kayit = len(veri_oku())
st.markdown(f"""
<div class="status-bar">
  <div style="font-weight:700;font-size:14px;">🛡️ <b>KTO Karatay Üniversitesi</b> | SMS Güvenlik Asistanı</div>
  <div style="display:flex;gap:10px;">
    <span class="status-badge">🟢 Sistem Aktif ({n_kayit} Kayıt)</span>
    <span class="status-badge">🧠 Kural + ML</span>
  </div>
</div>
""", unsafe_allow_html=True)

SAYFALAR.get(st.session_state.sayfa, SAYFALAR["ana"])[1]()
