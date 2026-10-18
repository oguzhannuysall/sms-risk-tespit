"""ML katmanı (Streamlit'e bağımlı değil): eğitim, skorlama, kural+ML birleştirme, dürüst değerlendirme."""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

from kurallar import kural_analizi, normalize

MIN_KAYIT = 30   # anlamlı model/metrik için en az toplam kayıt
MIN_SINIF = 6    # her sınıftan en az örnek
ESIK = 50        # risk >= ESIK ise "tuzak" sayılır (değerlendirme için)


def yeni_pipeline():
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True),
        LogisticRegression(max_iter=1000, class_weight="balanced"))


def hazirla(df):
    """Normalleştirilmiş metin sütunu ekler ve tekrar eden (normalleşince aynı olan) mesajları eler.
    Şablon benzeri tekrarlar train/test arasında sızıntı yapıp metrikleri şişirir."""
    df = df.copy()
    df["norm"] = df["mesaj"].astype(str).map(normalize)
    df["etiket"] = df["etiket"].astype(int)
    return df.drop_duplicates("norm").reset_index(drop=True)


def yeterli_mi(df):
    y = df["etiket"]
    return len(df) >= MIN_KAYIT and y.nunique() == 2 and int(y.value_counts().min()) >= MIN_SINIF


def egit(df):
    """(model, guvenilir) döndürür. Veri azsa model skora katılmaz (guvenilir=False)."""
    if df["etiket"].nunique() < 2:
        return None, False
    model = yeni_pipeline().fit(df["norm"], df["etiket"])
    return model, yeterli_mi(df)


def ml_skoru(model, mesaj):
    """Tuzak olma olasılığı, 0-100."""
    if model is None:
        return 0
    p = model.predict_proba([normalize(mesaj)])[0]
    return int(round(100 * p[list(model.classes_).index(1)]))


def birlestir(k, ml, guvenilir):
    """Kural sonucu + ML skorundan nihai risk. (risk, kural, ek_gerekceler) döndürür."""
    kural = min(k["skor"], 100)
    risk = round(0.7 * kural + 0.3 * ml) if guvenilir else kural
    notlar = []
    if k["guvenli"] and not k["tehlikeli"] and kural == 0:
        risk = min(risk, 10)
        notlar.append("✅ Mesajda yalnızca bilinen güvenli adres var, riskli ifade bulunmadı.")
    elif guvenilir and ml >= 60:
        notlar.append(f"⚠️ Mesajın yazılış tarzı daha önce kaydedilen dolandırıcılık mesajlarına çok benziyor (benzerlik %{ml}).")
    return max(0, min(100, int(risk))), kural, notlar


def metrikler(y_gercek, tahmin):
    p, r, f, _ = precision_recall_fscore_support(y_gercek, tahmin, pos_label=1, average="binary", zero_division=0)
    return {"accuracy": accuracy_score(y_gercek, tahmin), "precision": p, "recall": r, "f1": f,
            "cm": confusion_matrix(y_gercek, tahmin, labels=[0, 1])}


def degerlendir(df_ham):
    """Aynı ayrılmış test seti üzerinde üç sistemi karşılaştırır: yalnız kural / yalnız ML / hibrit.
    Veri yetersizse None döner."""
    df = hazirla(df_ham)
    tekrar = len(df_ham) - len(df)
    if not yeterli_mi(df):
        return None
    egitim_idx, test_idx = train_test_split(df.index, test_size=0.25, stratify=df["etiket"], random_state=42)
    model = yeni_pipeline().fit(df.loc[egitim_idx, "norm"], df.loc[egitim_idx, "etiket"])
    test = df.loc[test_idx]
    kural_t, ml_t, hibrit_t = [], [], []
    for m in test["mesaj"].astype(str):
        k = kural_analizi(m)
        ml = ml_skoru(model, m)
        kural_t.append(int(min(k["skor"], 100) >= ESIK))
        ml_t.append(int(ml >= ESIK))
        hibrit_t.append(int(birlestir(k, ml, True)[0] >= ESIK))
    y = test["etiket"]
    return {"Yalnız kural": metrikler(y, kural_t), "Yalnız ML": metrikler(y, ml_t), "Hibrit": metrikler(y, hibrit_t),
            "test_adet": len(test), "egitim_adet": len(egitim_idx), "tekrar_elenen": tekrar}
