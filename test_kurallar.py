"""Kural katmanı (kurallar.py) ve ML yardımcıları (ml.py) için testler.

Çalıştırma (proje ana klasöründen):
    pytest -v
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kurallar import (domain_cikar, fold, guvenli_domain_mu, kural_analizi, linkleri_bul, maskele,  # noqa: E402
                      normalize, taklit_edilen_marka)
from ml import ESIK, birlestir, degerlendir, hazirla, yeterli_mi  # noqa: E402


# ---------------------------------------------------------------- normalleştirme
def test_fold_turkce_karakterler_ve_buyuk_i():
    assert fold("HESABINIZA") == "hesabiniza"
    assert fold("İCRA") == "icra"
    assert fold("Şüpheli İşlem") == "supheli islem"


def test_normalize_harf_arasi_isaretleri_siler():
    assert "bloke" in normalize("hesabiniz b.l.o.k.e edildi")


def test_normalize_leet_cozer_ama_saf_sayiya_dokunmaz():
    assert "para" in normalize("6000 TL p4r4 transferi")
    assert "4821" in normalize("4821 nolu kart")


# ---------------------------------------------------------------- link analizi
def test_domain_cikar():
    assert domain_cikar("https://www.Google.com/arama?q=1") == "google.com"
    assert domain_cikar("http://bit.ly/abc") == "bit.ly"


def test_linkleri_bul_kisaltma_ve_ip():
    assert "bit.ly/abc" in linkleri_bul("tıkla: bit.ly/abc")
    assert "http://192.168.1.10/giris" in linkleri_bul("git: http://192.168.1.10/giris")


def test_para_tutari_ip_sanilmaz():
    assert linkleri_bul("Tutar 1.000.000.000 TL") == []


def test_guvenli_domain_tam_eslesme_ve_alt_alan():
    assert guvenli_domain_mu("youtube.com")
    assert guvenli_domain_mu("m.youtube.com")
    assert guvenli_domain_mu("turkiye.gov.tr")


def test_guvenli_domain_taklit_ve_kullanici_icerigi_guvenli_degil():
    assert not guvenli_domain_mu("google.com.evil.xyz")
    assert not guvenli_domain_mu("sites.google.com")
    assert not guvenli_domain_mu("ziraat-guvenlik.xyz")


def test_taklit_edilen_marka():
    assert taklit_edilen_marka("ziraat-guvenlik.xyz") == "ziraat"
    assert taklit_edilen_marka("ziraatbank.com.tr") == "ziraat"  # çağıran önce resmi mi diye bakar
    assert taklit_edilen_marka("ornek-site.com") is None


# ---------------------------------------------------------------- kural analizi
def test_masum_mesaj_sifir_skor():
    k = kural_analizi("Anne akşam eve geç geleceğim, yemek yapma.")
    assert k["skor"] == 0
    assert k["linkler"] == []


def test_guvenli_link_tehlikeli_sayilmaz():
    k = kural_analizi("Şu videoya bak: https://www.youtube.com/watch?v=abc")
    assert k["guvenli"] and not k["tehlikeli"]
    assert k["skor"] == 0


def test_kisaltilmis_link_yuksek_skor():
    k = kural_analizi("Hesabin bloke oldu simdi dogrula: bit.ly/3xYz")
    assert k["tehlikeli"]
    assert k["skor"] >= 50


def test_ip_adresli_link_yakalanir():
    k = kural_analizi("Paketiniz icin tıklayın: http://185.12.44.9/kargo")
    assert k["tehlikeli"]
    assert any("IP" in g for g in k["gerekceler"])


def test_kurum_taklidi_yakalanir():
    k = kural_analizi("Ziraat Bankası: Hesabınızdan şüpheli işlem tespit edildi. Doğrulayın: ziraat-guvenlik.xyz")
    assert k["skor"] >= 70
    assert any("Kurum Taklidi" in g for g in k["gerekceler"])


def test_kelime_oyunu_yakalanir():
    k = kural_analizi("Hakkınızda i.c.r.a takibi başlatılmıştır, bugün e-devlet-sorgu.xyz adresine giriniz.")
    assert any("Gizlenmiş Kelime" in g for g in k["gerekceler"])
    assert k["skor"] >= 70


def test_turkce_ekler_taninir():
    assert "icra*" in kural_analizi("Hakkınızda icradan işlem var, hemen arayın.")["kelimeler"]


def test_tl_tek_basina_risk_degil():
    assert kural_analizi("Kartınızla 340,00 TL market alışverişi yapılmıştır.")["skor"] == 0


def test_html_gerekceleri_kullanici_metnini_kacirir():
    k = kural_analizi("Tıkla: http://x.xyz/<script>alert(1)</script>")
    assert all("<script>" not in g for g in k["gerekceler"])


# ---------------------------------------------------------------- maskeleme
def test_maskele_kisisel_veriler():
    m = maskele("TC 12345678901 tel 05321234567 iban TR330006100519786457841326 "
                "mail a@b.com kart 4111 1111 1111 1111")
    for etiket in ("[TC]", "[TEL]", "[IBAN]", "[EPOSTA]", "[KART]"):
        assert etiket in m
    for ham in ("12345678901", "05321234567", "a@b.com", "4111"):
        assert ham not in m


def test_maskele_normal_metne_dokunmaz():
    assert maskele("Yarın saat 14:00'te toplantı var.") == "Yarın saat 14:00'te toplantı var."


# ---------------------------------------------------------------- ML yardımcıları
def _df(n_tuzak, n_guvenli):
    satirlar = [(f"Hesabınız bloke edildi {i} hemen tıklayın: banka-onay{i}.xyz", 1) for i in range(n_tuzak)]
    satirlar += [(f"Yarın {i}. toplantı için ofiste buluşalım", 0) for i in range(n_guvenli)]
    return pd.DataFrame(satirlar, columns=["mesaj", "etiket"])


def test_hazirla_tekrarlari_eler():
    df = pd.DataFrame({"mesaj": ["Merhaba nasılsın", "MERHABA nasilsin", "Başka mesaj"], "etiket": [0, 0, 0]})
    assert len(hazirla(df)) == 2


def test_yeterli_mi_esikler():
    assert not yeterli_mi(hazirla(_df(3, 3)))
    assert yeterli_mi(hazirla(_df(20, 20)))


def test_birlestir_veri_azsa_yalniz_kural():
    k = {"skor": 80, "guvenli": False, "tehlikeli": True}
    assert birlestir(k, ml=0, guvenilir=False)[0] == 80


def test_birlestir_agirliklar():
    k = {"skor": 80, "guvenli": False, "tehlikeli": True}
    assert birlestir(k, ml=50, guvenilir=True)[0] == round(0.7 * 80 + 0.3 * 50)


def test_birlestir_sadece_guvenli_link_riski_dusuk_tutar():
    k = {"skor": 0, "guvenli": True, "tehlikeli": False}
    assert birlestir(k, ml=95, guvenilir=True)[0] <= 10


def test_birlestir_sinirlar():
    k = {"skor": 500, "guvenli": False, "tehlikeli": True}
    assert 0 <= birlestir(k, ml=100, guvenilir=True)[0] <= 100


def test_degerlendir_veri_yetersizse_none():
    assert degerlendir(_df(3, 3)) is None


def test_degerlendir_uc_sistemi_dondurur():
    r = degerlendir(_df(20, 20))
    assert set(("Yalnız kural", "Yalnız ML", "Hibrit")) <= set(r)
    assert r["egitim_adet"] + r["test_adet"] == 40
    assert 0 <= r["Hibrit"]["f1"] <= 1


def test_esik_degeri():
    assert ESIK == 50
