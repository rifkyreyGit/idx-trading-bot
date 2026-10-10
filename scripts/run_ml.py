"""Bandingkan model ML vs aturan MA/RSI vs 'beli sembarang hari' (data uji)."""
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from idxbot.config import load_settings
from idxbot.ml.dataset import FEATURES, build_dataset

pd.set_option("display.width", 170)


def ringkas(nama, mask, y, fwd, auc=None):
    n = int(mask.sum())
    return {
        "model": nama,
        "n_sinyal": n,
        "hit_rate%": y[mask].mean() * 100 if n else float("nan"),
        "rata2_return%": fwd[mask].mean() * 100 if n else float("nan"),
        "AUC": auc if auc is not None else float("nan"),
    }


def main() -> None:
    settings = load_settings()
    horizon = settings["ml"]["horizon_days"]
    split = pd.Timestamp(settings["evaluation"]["split_date"])

    train_parts, test_parts = [], []
    for t in settings["data"]["tickers"]:
        d = build_dataset(t, settings)
        # jeda (embargo): label baris terakhir sebelum split memakai data setelah split
        train_parts.append(d[d.index < split].iloc[:-horizon])
        test_parts.append(d[d.index >= split])
    train = pd.concat(train_parts)
    test = pd.concat(test_parts)

    base_rate = train["label"].mean()
    print(f"Latih: {len(train)} baris | Uji: {len(test)} baris | "
          f"Rasio hari untung (latih): {base_rate:.1%}")

    modelnya = {
        "Logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "GradBoost": HistGradientBoostingClassifier(
            max_depth=3, max_iter=100, learning_rate=0.05, random_state=42
        ),
    }

    for periode, data in (("UJI (2023 ke atas)", test), ("LATIH (cek overfitting)", train)):
        y, fwd = data["label"], data["fwd_return"]
        rows = [
            ringkas("Beli sembarang hari", pd.Series(True, index=data.index), y, fwd),
            ringkas("Aturan MA/RSI (BUY)", data["signal"] == "BUY", y, fwd),
        ]
        for nama, model in modelnya.items():
            model.fit(train[FEATURES], train["label"])
            proba = model.predict_proba(data[FEATURES])[:, 1]
            rows.append(
                ringkas(nama, pd.Series(proba > base_rate, index=data.index), y, fwd,
                        roc_auc_score(y, proba))
            )
        print(f"\n=== {periode} ===")
        print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    print("\nAUC 0.50 = tebakan acak. Sinyal berdekatan saling tumpang tindih (horizon "
          f"{horizon} hari), jadi n_sinyal lebih banyak dari sampel independen sebenarnya.")


if __name__ == "__main__":
    main()
