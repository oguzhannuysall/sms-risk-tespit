"""
Kural katmanı: Streamlit'e bağımlı olmayan saf Python fonksiyonları (test edilebilir).

İçerik: Türkçe metin normalleştirme, link analizi, kurum taklidi tespiti,
anahtar kelime kategorileri, kişisel veri maskeleme, güvenli HTML üretimi.
"""
import difflib
import html
import re

# ----------------------------------------------------------------------
# 1. METİN NORMALLEŞTİRME
# ----------------------------------------------------------------------
# ı ç ğ ö ş ü -> ASCII karşılığı. 1:1 çeviri olduğu için metin uzunluğu değişmez.
FOLD = str.maketrans("ıçğöşüâîû", "icgosuaiu")
LEET = str.maketrans({"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t"})
GIZLI_HARF_REGEX = re.compile(r"(?<=\b\w)[\.\-\_\s\*]+(?=\w\b)")


def fold(s):
    """Küçük harfe çevirir ve Türkçe karakterleri ASCII'ye indirger.
    'HESABINIZA' -> 'hesabiniza', 'İCRA' -> 'icra' (büyük I / İ sorunu çözülür)."""
    return s.replace("İ", "i").lower().translate(FOLD)


tr_lower = fold  # geriye dönük uyumluluk


def _leet_kelime(m):
    k = m.group(0)
    # Sadece harf VE rakam içeren kelimeleri çöz (p4r4, k4rgo). "4821" gibi saf sayılara dokunma.
    if any(c.isalpha() for c in k) and any(c.isdigit() for c in k):
        return k.translate(LEET)
    return k


def normalize(metin):
    """fold + leet çözümü + 'b.l.o.k.e' gibi harf arası işaretlerin silinmesi."""
    kucuk = fold(metin)
    kucuk = re.sub(r"\w+", _leet_kelime, kucuk)
    return GIZLI_HARF_REGEX.sub("", kucuk)


# ----------------------------------------------------------------------
# 2. LİNK ANALİZİ
# ----------------------------------------------------------------------
TLDLER = ("com|net|org|tr|info|ly|co|gd|me|io|cc|app|link|vip|buzz|live|cfd|shop|xyz|top|icu|click|site|"
          "online|store|cyou|sbs|work|biz|pw|ws|to|page|dev|cloud|today|fun|rest|art")
LINK_REGEX = re.compile(
    r"(https?://\S+|www\.\S+"
    r"|\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(?:/\S*)?"
    r"|\b[a-zA-Z0-9][a-zA-Z0-9.-]*\.(?:" + TLDLER + r")\b(?:/\S*)?)",
    re.IGNORECASE)
IP_REGEX = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

GUVENLI_GENEL = ["youtube.com", "youtu.be", "google.com", "instagram.com", "turkiye.gov.tr", "gov.tr",
                 "edu.tr", "whatsapp.com", "github.com", "twitter.com", "x.com", "linkedin.com", "wikipedia.org"]
# Herkesin içerik barındırabildiği alt alanlar: ana domain güvenli olsa bile güvenli SAYILMAZ.
KULLANICI_ICERIKLI = ["sites.google.com", "docs.google.com", "drive.google.com", "forms.google.com",
                      "script.google.com", "storage.googleapis.com", "github.io", "firebaseapp.com",
                      "web.app", "blogspot.com", "wordpress.com"]
KISALTILMIS_LINKLER = ["bit.ly", "tinyurl.com", "t.co", "ow.ly", "cutt.ly", "is.gd", "rb.gy", "shorturl.at"]
RISKLI_TLD = {"xyz", "top", "icu", "click", "site", "online", "buzz", "live", "cfd", "shop", "cyou", "sbs", "vip"}

# marka -> adlar (mesaj metninde geçen yazımlar), anahtar (alan adı parçalarında aranır), resmi (gerçek alan adları)
MARKALAR = {
    "ziraat": {"adlar": ["ziraat", "ziraatbank", "ziraat bankasi"], "anahtar": ["ziraat"], "resmi": ["ziraatbank.com.tr"]},
    "garanti": {"adlar": ["garanti bbva", "garantibbva", "garanti bankasi"], "anahtar": ["garanti"], "resmi": ["garantibbva.com.tr", "garanti.com.tr"]},
    "akbank": {"adlar": ["akbank"], "anahtar": ["akbank"], "resmi": ["akbank.com"]},
    "isbank": {"adlar": ["is bankasi", "isbank"], "anahtar": ["isbank", "isbankasi"], "resmi": ["isbank.com.tr", "isbank.com"]},
    "vakifbank": {"adlar": ["vakifbank", "vakif bank"], "anahtar": ["vakifbank", "vakif"], "resmi": ["vakifbank.com.tr"]},
    "halkbank": {"adlar": ["halkbank", "halk bank"], "anahtar": ["halkbank", "halk"], "resmi": ["halkbank.com.tr"]},
    "yapikredi": {"adlar": ["yapi kredi", "yapikredi"], "anahtar": ["yapikredi"], "resmi": ["yapikredi.com.tr"]},
    "ptt": {"adlar": ["ptt", "ptt kargo"], "anahtar": ["ptt", "pttkargo"], "resmi": ["ptt.gov.tr", "pttavm.com", "ptt.com.tr"]},
    "yurtici": {"adlar": ["yurtici kargo", "yurtici"], "anahtar": ["yurtici", "yurticikargo"], "resmi": ["yurticikargo.com"]},
    "aras": {"adlar": ["aras kargo"], "anahtar": ["aras", "araskargo"], "resmi": ["araskargo.com.tr"]},
    "mng": {"adlar": ["mng kargo"], "anahtar": ["mng", "mngkargo"], "resmi": ["mngkargo.com.tr"]},
    "trendyol": {"adlar": ["trendyol"], "anahtar": ["trendyol"], "resmi": ["trendyol.com"]},
    "hepsiburada": {"adlar": ["hepsiburada"], "anahtar": ["hepsiburada"], "resmi": ["hepsiburada.com"]},
    "papara": {"adlar": ["papara"], "anahtar": ["papara"], "resmi": ["papara.com"]},
    "binance": {"adlar": ["binance"], "anahtar": ["binance"], "resmi": ["binance.com"]},
    "sahibinden": {"adlar": ["sahibinden"], "anahtar": ["sahibinden"], "resmi": ["sahibinden.com"]},
    "edevlet": {"adlar": ["e-devlet", "edevlet", "e devlet", "turkiye.gov"], "anahtar": ["edevlet", "devlet"], "resmi": ["turkiye.gov.tr"]},
    "uyap": {"adlar": ["uyap"], "anahtar": ["uyap"], "resmi": ["uyap.gov.tr"]},
}


def _alt_alan_mi(domain, ana):
    return domain == ana or domain.endswith("." + ana)


def linkleri_bul(mesaj):
    gorulen, sonuc = set(), []
    for l in LINK_REGEX.findall(mesaj):
        l = l.rstrip(".,;:!?)\"'")
        if not l or l.lower() in gorulen:
            continue
        d = domain_cikar(l)
        if IP_REGEX.match(d) and any(int(p) > 255 or (len(p) > 1 and p[0] == "0") for p in d.split(".")):
            continue  # "1.000.000.000" gibi para tutarlarını IP sanma (gerçek IP'de başta sıfır olmaz)
        gorulen.add(l.lower())
        sonuc.append(l)
    return sonuc


def domain_cikar(link):
    d = re.sub(r"^https?://", "", link, flags=re.I)
    d = re.split(r"[/?#]", d)[0].split("@")[-1].split(":")[0].lower().rstrip(".")
    return d[4:] if d.startswith("www.") else d


def resmi_mi(domain, marka):
    return any(_alt_alan_mi(domain, r) for r in MARKALAR[marka]["resmi"])


def herhangi_resmi_mi(domain):
    return any(resmi_mi(domain, m) for m in MARKALAR)


def guvenli_domain_mu(domain):
    # Alt dizgi DEĞİL: tam eşleşme veya gerçek alt alan adı (google.com.evil.xyz güvenli sayılmaz).
    if any(_alt_alan_mi(domain, k) for k in KULLANICI_ICERIKLI):
        return False
    return any(_alt_alan_mi(domain, g) for g in GUVENLI_GENEL) or herhangi_resmi_mi(domain)


def taklit_edilen_marka(domain):
    """Resmi olmayan bir alan adı bir markanın adını taşıyorsa markayı döndürür."""
    parcalar = [p for p in re.split(r"[.\-_]", domain) if p]
    for marka, bilgi in MARKALAR.items():
        for a in bilgi["anahtar"]:
            for p in parcalar:
                if p == a:
                    return marka
                if len(a) >= 5 and (p.startswith(a) or a in p):
                    return marka
                if len(a) >= 5 and len(p) >= 5 and difflib.SequenceMatcher(None, p, a).ratio() >= 0.85:
                    return marka
    return None


def markalar_metinde(kucuk):
    """Mesaj metninde adı geçen markalar (fold edilmiş metin üzerinde)."""
    bulunan = []
    for marka, bilgi in MARKALAR.items():
        if any(re.search(r"\b" + re.escape(a) + r"\b", kucuk) for a in bilgi["adlar"]):
            bulunan.append(marka)
    return bulunan


# ----------------------------------------------------------------------
# 3. ANAHTAR KELİME KATEGORİLERİ
# ----------------------------------------------------------------------
# Sonundaki "*" = Türkçe ek alabilir (dava -> davası, icra -> icradan). Liste ASCII yazılır; fold ile eşleşir.
KATEGORILER = {
    "kargo": ["teslim edilemedi", "adres hatasi", "adres yetersizligi", "adres eksikligi", "kargonuz", "iade*", "gumruk*"],
    "icra_hukuk": ["icra*", "dava*", "uzlastirma*", "adliye*", "sevk", "hapis*", "tazminat*", "savcilik*", "ceza*",
                   "hukuk*", "bahis*", "taciz*", "sorusturma*", "uyap"],
    "banka_finans": ["bloke*", "kredi karti*", "hesabiniz*", "supheli*", "iptal*", "papara", "aidat*", "binance"],
    "odul_yardim": ["tebrikler", "hediye*", "kazandiniz", "askida fatura*", "ikramiye*", "cekilis*", "bonus*", "kupon*",
                    "destek paketi*"],
    "para_talebi": ["iban", "hesaba yatir*", "odeme*", "bedeli*", "masraf*", "para transfer*", "borcunuz*"],
    "aciliyet": ["acil", "acilen", "hemen", "derhal", "bugun", "son gun", "sure bitiyor", "24 saat", "12 saat",
                 "mesai bitimine"],
}
KATEGORI_BILGI = {  # kategori: (gerekçe, puan)
    "icra_hukuk": ("⚖️ <b>Korkutma ve Tehdit Dili:</b> İcra, dava veya ceza gibi korkutucu kelimelerle panik yaratılmak isteniyor.", 35),
    "banka_finans": ("🏦 <b>Sahte Banka Uyarısı:</b> Hesap blokesi veya kart sorunu bahanesiyle kişisel bilgileriniz isteniyor.", 30),
    "kargo": ("📦 <b>Sahte Kargo Mesajı:</b> Teslimat sorunu bahanesiyle dolandırıcılık sitelerine yönlendiriliyor.", 30),
    "odul_yardim": ("🎁 <b>Bedava Hediye Tuzağı:</b> Gerçek olamayacak kadar cazip hediye veya yardım vaadiyle kandırma girişimi.", 30),
    "para_talebi": ("💸 <b>Doğrudan Para İsteme:</b> Mesajda açıkça para, borç ödemesi veya IBAN transferi talep ediliyor.", 35),
    "aciliyet": ("⏱️ <b>Acele Ettirme Taktiği:</b> Düşünmenize izin vermeden hemen işlem yapmanız için baskı kuruluyor.", 15),
}


def _derle(kelime):
    yildiz = kelime.endswith("*")
    govde = fold(kelime.rstrip("*"))
    ek = r"\w{0,6}" if yildiz else ""
    return govde, re.compile(r"\b" + re.escape(govde) + ek + r"\b"), yildiz


KALIPLAR = {kat: [_derle(k) for k in liste] for kat, liste in KATEGORILER.items()}


# ----------------------------------------------------------------------
# 4. KURAL ANALİZİ
# ----------------------------------------------------------------------
def kural_analizi(mesaj):
    gerekceler, yakalanan, skor = [], [], 0
    kucuk = fold(mesaj)
    cozulmus = normalize(mesaj)
    kelime_oyunu_var = False

    linkler = linkleri_bul(mesaj)
    domainler = [domain_cikar(l) for l in linkler]
    guvenli_link_var = tehlikeli_link_var = False
    taklit_markalar = set()

    for domain in domainler:
        d = html.escape(domain)
        if guvenli_domain_mu(domain):
            guvenli_link_var = True
            gerekceler.append(f"🌐 <b>Güvenilir Bağlantı:</b> <code>{d}</code> bilinen güvenli alan adları listesinde.")
            continue
        tehlikeli_link_var = True
        if IP_REGEX.match(domain):
            gerekceler.append(f"🔢 <b>IP Adresli Bağlantı:</b> Gerçek bir site adı yerine doğrudan IP adresi (<code>{d}</code>) kullanılmış!")
            skor += 50
        elif any(_alt_alan_mi(domain, k) for k in KISALTILMIS_LINKLER):
            gerekceler.append(f"🔗 <b>Gizlenmiş Link:</b> Gerçek adresi saklayan kısaltma (<code>{d}</code>) kullanılmış!")
            skor += 55
        else:
            gerekceler.append(f"🔗 <b>Bilinmeyen Bağlantı:</b> Güvenliği onaylanmamış bir adrese (<code>{d}</code>) yönlendiriyor.")
            skor += 45
        marka = taklit_edilen_marka(domain)
        if marka:
            taklit_markalar.add(marka)
            gerekceler.append(f"🎭 <b>Kurum Taklidi:</b> <code>{d}</code> adresi “{html.escape(marka)}” adını içeriyor ama resmi site değil.")
            skor += 20
        tld = domain.rsplit(".", 1)[-1]
        if tld in RISKLI_TLD:
            gerekceler.append(f"⚠️ <b>Riskli Uzantı:</b> <code>.{html.escape(tld)}</code> uzantısı dolandırıcılıkta sık kullanılıyor.")
            skor += 10
        if domain.startswith("xn--") or ".xn--" in domain:
            gerekceler.append(f"🔤 <b>Sahte Karakterli Adres:</b> <code>{d}</code> görünüşte tanıdık harfler taklit eden (punycode) bir adres.")
            skor += 30
        if domain.count("-") >= 2:
            skor += 5

    # Mesajda adı geçen kurum ile linkin resmi alan adı uyuşuyor mu?
    if linkler:
        for marka in markalar_metinde(kucuk):
            if marka in taklit_markalar:
                continue
            if not any(resmi_mi(d, marka) for d in domainler):
                gerekceler.append(f"🏷️ <b>Kurum–Bağlantı Uyuşmazlığı:</b> Mesaj “{html.escape(marka)}” adına yazılmış ama link bu kurumun resmi sitesi değil.")
                skor += 20
                break

    para_bulundu = False
    for kategori, kalip_listesi in KALIPLAR.items():
        bulundu = False
        for govde, rx, yildiz in kalip_listesi:
            normal = rx.search(kucuk)
            coz = rx.search(cozulmus)
            if normal or coz:
                bulundu = True
                isaret = govde + ("*" if yildiz else "")
                if isaret not in yakalanan:
                    yakalanan.append(isaret)
                if coz and not normal:
                    kelime_oyunu_var = True
        if bulundu:
            metin, puan = KATEGORI_BILGI[kategori]
            gerekceler.append(metin)
            skor += puan
            if kategori == "para_talebi":
                para_bulundu = True

    # TL tek başına risk değildir (banka işlem bildirimlerinde de geçer); başka bir işaret varsa anlam kazanır.
    if skor > 0 and (re.search(r"\b(?:tl|lira)\b", kucuk) or re.search(r"\btl\b", cozulmus)):
        yakalanan.append("tl")
        if not para_bulundu:
            gerekceler.append("💸 <b>Para Birimi Tespiti:</b> Diğer şüpheli işaretlerle birlikte mesajda para miktarı (TL) geçiyor.")
            skor += 15

    if kelime_oyunu_var:
        gerekceler.append("🕵️ <b>Gizlenmiş Kelime Tespiti:</b> Filtreleri atlatmak için harflerin arasına nokta veya işaret konmuş!")
        skor += 25

    return {"skor": skor, "gerekceler": gerekceler, "kelimeler": yakalanan, "linkler": linkler,
            "guvenli": guvenli_link_var, "tehlikeli": tehlikeli_link_var}


# ----------------------------------------------------------------------
# 5. KİŞİSEL VERİ MASKELEME (kayıt öncesi)
# ----------------------------------------------------------------------
def maskele(m):
    m = re.sub(r"TR\d{2}(?:[ ]?\d){22}", "[IBAN]", m, flags=re.I)
    m = re.sub(r"\b(?:\d[ -]?){15}\d\b", "[KART]", m)
    # +90 532 123 45 67 / 0532 123 45 67 / 05321234567 / 532-123-4567
    m = re.sub(r"(?<!\d)(?:\+?90[\s-]?|0[\s-]?)?\(?5\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)", "[TEL]", m)
    m = re.sub(r"\b[1-9]\d{10}\b", "[TC]", m)
    return re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[EPOSTA]", m)


# ----------------------------------------------------------------------
# 6. GÜVENLİ HTML ÜRETİMİ
# ----------------------------------------------------------------------
TERS_LEET = {"a": "[a4â]", "c": "[cç]", "e": "[e3]", "g": "[gğ]", "i": "[i1ıİI]", "o": "[o0ö]",
             "s": "[s5ş]", "t": "[t7]", "u": "[uü]"}


def html_guvenli(metin):
    """Kullanıcı metnini HTML'e çevirir. Satır sonları <br> olur: boş satır kalmadığı için
    Streamlit'in markdown ayrıştırıcısı metni (ör. [tıkla](http://...)) asla markdown olarak işlemez."""
    return html.escape(metin).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def metni_isaretle(metin, kelimeler, linkler, guvenli_mi):
    kacisli = html.escape(metin).replace("\r\n", "\n").replace("\r", "\n")
    desenler = [re.escape(html.escape(l)) for l in sorted(set(linkler), key=len, reverse=True)]
    link_kume = {html.escape(l) for l in linkler}
    for k in sorted(set(kelimeler), key=len, reverse=True):
        yildiz = k.endswith("*")
        govde = k.rstrip("*")
        harfler = r"[\.\-_\s\*]*".join(TERS_LEET.get(c, re.escape(c)) for c in govde)
        desenler.append(r"\b" + harfler + (r"\w{0,6}" if yildiz else "") + r"\b")
    if not desenler:
        return kacisli.replace("\n", "<br>")
    birlesik = re.compile("|".join(desenler), re.IGNORECASE)

    def degistir(m):
        t = m.group(0)
        if t in link_kume:
            return f'<span class="{"safe-tag" if guvenli_mi else "danger-tag"}">🔗 {t}</span>'
        return f'<span class="danger-tag">{t}</span>'

    return birlesik.sub(degistir, kacisli).replace("\n", "<br>")
