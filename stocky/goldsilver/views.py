"""
GoldSilver/views.py
GET /api/goldsilver/analysis/

- Graceful fallback: if shap/lime not installed, returns original data without crashing
- Feature engineering + GBM + SHAP + LIME when libraries are available
- Original LinearRegression payload always included for frontend compat
"""

import io, base64, warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

import yfinance as yf
from sklearn.linear_model    import LinearRegression
from sklearn.ensemble        import GradientBoostingRegressor
from sklearn.preprocessing   import StandardScaler
from sklearn.model_selection import cross_val_score

# ── Optional XAI imports (graceful fallback) ──────────
try:
    import shap as _shap
    SHAP_OK = True
except ImportError:
    SHAP_OK = False

try:
    import lime
    import lime.lime_tabular as _lime_tabular
    LIME_OK = True
except ImportError:
    LIME_OK = False

from rest_framework.views       import APIView
from rest_framework.response    import Response
from rest_framework.permissions import IsAuthenticated

# ── Chart palette ─────────────────────────────────────
BG     = "#0b0f1a"
PANEL  = "#111827"
INDIGO = "#6366f1"
GOLD_C = "#d97706"
SILVER_C="#94a3b8"
GREEN  = "#10b981"
RED    = "#ef4444"
DIM    = "#6b7280"
WHITE  = "#f1f5f9"
PURPLE = "#8b5cf6"


def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=BG)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def _style_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=DIM, labelsize=8)
    ax.grid(color="#1e2533", linestyle="--", linewidth=0.4, alpha=0.6)
    for sp in ax.spines.values():
        sp.set_color("#1e2533")
    if title:  ax.set_title(title,  color=WHITE, fontsize=11, pad=10)
    if xlabel: ax.set_xlabel(xlabel, color=DIM,   fontsize=9)
    if ylabel: ax.set_ylabel(ylabel, color=DIM,   fontsize=9)


# ── Feature labels ────────────────────────────────────
FEATURE_LABELS = {
    "gold_ret_1":      "Gold 1M Return",
    "gold_ret_3":      "Gold 3M Return",
    "gold_ret_6":      "Gold 6M Return",
    "gold_vol_3":      "Gold 3M Volatility",
    "gold_vol_6":      "Gold 6M Volatility",
    "gold_mom_3":      "Gold 3M Momentum",
    "gold_mom_6":      "Gold 6M Momentum",
    "gold_rsi_14":     "Gold RSI-14",
    "gold_zscore_12":  "Gold 12M Z-Score",
    "gold_price":      "Gold Price (raw)",
    "ratio_gs":        "Gold/Silver Ratio",
    "silver_ret_1":    "Silver 1M Return",
    "silver_vol_3":    "Silver 3M Volatility",
    "silver_mom_3":    "Silver 3M Momentum",
}


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _build_features(gold: pd.Series, silver: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame(index=gold.index)
    df["gold_price"]     = gold
    df["gold_ret_1"]     = gold.pct_change(1)
    df["gold_ret_3"]     = gold.pct_change(3)
    df["gold_ret_6"]     = gold.pct_change(6)
    df["gold_vol_3"]     = gold.pct_change(1).rolling(3).std()
    df["gold_vol_6"]     = gold.pct_change(1).rolling(6).std()
    df["gold_mom_3"]     = gold / gold.shift(3) - 1
    df["gold_mom_6"]     = gold / gold.shift(6) - 1
    df["gold_rsi_14"]    = _rsi(gold, 14)
    df["gold_zscore_12"] = (gold - gold.rolling(12).mean()) / (gold.rolling(12).std() + 1e-9)
    df["ratio_gs"]       = gold / (silver + 1e-9)
    df["silver_ret_1"]   = silver.pct_change(1)
    df["silver_vol_3"]   = silver.pct_change(1).rolling(3).std()
    df["silver_mom_3"]   = silver / silver.shift(3) - 1
    df["target"]         = silver
    return df.dropna()


# ── SHAP charts ───────────────────────────────────────
def _chart_shap_bar(shap_values, feature_names, title):
    mean_abs = np.abs(shap_values).mean(axis=0)
    order    = np.argsort(mean_abs)[::-1][:12]
    labels   = [FEATURE_LABELS.get(feature_names[i], feature_names[i]) for i in order]
    vals     = mean_abs[order]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    _style_ax(ax, title=title, xlabel="Mean |SHAP Value|")
    colors = [INDIGO if v >= vals[0] * 0.6 else PURPLE for v in vals]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], edgecolor=PANEL, height=0.6)
    for bar, val in zip(bars, vals[::-1]):
        ax.text(val + vals.max() * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.4f}", va="center", color=WHITE, fontsize=8)
    ax.set_xlim(0, vals.max() * 1.18)
    plt.tight_layout()
    return _b64(fig)


def _chart_shap_waterfall(shap_row, feature_names, base_val, pred_val):
    order  = np.argsort(np.abs(shap_row))[::-1][:10]
    labels = [FEATURE_LABELS.get(feature_names[i], feature_names[i]) for i in order]
    values = shap_row[order]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    _style_ax(ax,
        title="SHAP Waterfall — Latest Prediction Breakdown",
        xlabel="SHAP Contribution to Silver Price")
    running = base_val
    lefts, widths, clrs = [], [], []
    for v in values:
        lefts.append(min(running, running + v))
        widths.append(abs(v))
        clrs.append(GREEN if v >= 0 else RED)
        running += v
    bars = ax.barh(labels[::-1], widths[::-1], left=lefts[::-1],
                   color=clrs[::-1], edgecolor=PANEL, height=0.6, alpha=0.88)
    ax.axvline(base_val, color=GOLD_C, lw=1.2, ls="--", alpha=0.7, label=f"Base: ${base_val:.2f}")
    ax.axvline(pred_val, color=GREEN,  lw=1.2, ls="--", alpha=0.7, label=f"Pred: ${pred_val:.2f}")
    for bar, v in zip(bars, values[::-1]):
        sign = "+" if v >= 0 else ""
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_y() + bar.get_height() / 2,
                f"{sign}{v:.3f}", ha="center", va="center",
                color=WHITE, fontsize=7.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor="#1e2533", labelcolor=WHITE, fontsize=8)
    plt.tight_layout()
    return _b64(fig)


def _chart_lime_bar(lime_exp, title="LIME — Feature Contributions (Latest Point)"):
    items  = lime_exp.as_list()
    labels = [FEATURE_LABELS.get(itm[0].split(" ")[0], itm[0]) for itm in items]
    values = [itm[1] for itm in items]
    order  = np.argsort(np.abs(values))[::-1]
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    colors = [GREEN if v >= 0 else RED for v in values]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    _style_ax(ax, title=title, xlabel="LIME Contribution Weight")
    ax.barh(labels[::-1], values[::-1], color=colors[::-1], edgecolor=PANEL, height=0.6, alpha=0.88)
    ax.axvline(0, color=WHITE, lw=0.8, alpha=0.4)
    vmax = max(abs(v) for v in values) if values else 1
    for i, v in enumerate(values[::-1]):
        sign = "+" if v >= 0 else ""
        offset = vmax * 0.02 if v >= 0 else -vmax * 0.02
        ax.text(v + offset, i, f"{sign}{v:.4f}", va="center",
                ha="left" if v >= 0 else "right", color=WHITE, fontsize=8)
    plt.tight_layout()
    return _b64(fig)


def _chart_top_feature_scatter(df, feature, pred_series):
    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor(BG)
    label = FEATURE_LABELS.get(feature, feature)
    _style_ax(ax, title=f"Top Feature: {label}  vs  Silver Price",
              xlabel=label, ylabel="Silver Price ($)")
    ax.scatter(df[feature], df["target"], c=SILVER_C, alpha=0.65, s=30, zorder=3, label="Actual")
    ax.scatter(df[feature], pred_series,  c=INDIGO,   alpha=0.55, s=20, zorder=4, marker="^", label="Predicted (GBM)")
    ax.legend(facecolor=PANEL, edgecolor="#1e2533", labelcolor=WHITE, fontsize=8)
    plt.tight_layout()
    return _b64(fig)


# ── View ──────────────────────────────────────────────
class GoldSilverAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        end   = datetime.today()
        start = end - timedelta(days=5 * 365)

        # ── Fetch data ────────────────────────────────
        try:
            gold_df   = yf.download("GC=F", start=start, end=end, interval="1mo", auto_adjust=True, progress=False)
            silver_df = yf.download("SI=F", start=start, end=end, interval="1mo", auto_adjust=True, progress=False)
        except Exception as e:
            return Response({"error": f"Data fetch failed: {str(e)}"}, status=400)

        if gold_df.empty or silver_df.empty:
            return Response({"error": "No market data returned. Check your internet connection."}, status=400)

        gold   = gold_df["Close"].squeeze().dropna()
        silver = silver_df["Close"].squeeze().dropna()
        common = gold.index.intersection(silver.index)
        gold   = gold.reindex(common).dropna()
        silver = silver.reindex(common).dropna()

        if len(gold) < 15:
            return Response({"error": "Insufficient market data. Try again later."}, status=400)

        # Ensure plain 1D arrays
        gold_arr   = np.array(gold.values).flatten().astype(float)
        silver_arr = np.array(silver.values).flatten().astype(float)

        # ── Original LinearRegression ─────────────────
        X_lin = gold_arr.reshape(-1, 1)
        lin   = LinearRegression().fit(X_lin, silver_arr)
        predicted_lin = lin.predict(X_lin)
        correlation   = float(np.corrcoef(gold_arr, silver_arr)[0, 1])

        last_gold    = float(gold_arr[-1])
        future_gold  = [last_gold * (1 + i * 0.02) for i in range(1, 7)]
        future_silver= lin.predict(np.array(future_gold).reshape(-1, 1)).tolist()

        price_history = [
            {"date": str(d.date()), "gold": round(float(g), 2), "silver": round(float(s), 2)}
            for d, g, s in zip(common, gold_arr, silver_arr)
        ]
        regression_data = [
            {"gold": round(float(g), 2), "silver_actual": round(float(s), 2),
             "silver_predicted": round(float(p), 2)}
            for g, s, p in zip(gold_arr, silver_arr, predicted_lin)
        ]
        predictions = [
            {"month": f"Month +{i+1}", "gold": round(future_gold[i], 2),
             "silver_predicted": round(float(future_silver[i]), 2)}
            for i in range(6)
        ]

        # ── Base response (always returned) ──────────
        base_resp = {
            "correlation":    round(correlation, 4),
            "r2_score":       round(float(lin.score(X_lin, silver_arr)), 4),
            "slope":          round(float(lin.coef_[0]), 4),
            "price_history":  price_history,
            "regression_data":regression_data,
            "predictions":    predictions,
            # XAI fields default to None — filled below if libs available
            "gbm_r2_cv":      None,
            "top_features":   [],
            "lime_features":  [],
            "gbm_importances":[],
            "shap_base_value":None,
            "gbm_pred_latest":None,
            "charts":         {},
            "xai_available":  SHAP_OK and LIME_OK,
        }

        # ── Feature Engineering + GBM ─────────────────
        try:
            df     = _build_features(gold, silver)
            FCOLS  = [c for c in df.columns if c != "target"]
            X      = df[FCOLS].values
            y      = df["target"].values
            feat_names = FCOLS

            if len(X) < 15:
                return Response({**base_resp, "error_xai": "Not enough data for XAI."})

            scaler = StandardScaler()
            X_s    = scaler.fit_transform(X)

            gbm = GradientBoostingRegressor(
                n_estimators=200, max_depth=3, learning_rate=0.05,
                subsample=0.8, min_samples_leaf=2, random_state=42
            )
            gbm.fit(X_s, y)
            gbm_pred = gbm.predict(X_s)
            cv_folds = min(5, len(X) // 3)
            cv_r2    = float(np.mean(cross_val_score(gbm, X_s, y, cv=cv_folds, scoring="r2"))) if cv_folds >= 2 else None

            base_resp["gbm_r2_cv"]      = round(cv_r2, 4) if cv_r2 else None
            base_resp["gbm_pred_latest"]= round(float(gbm_pred[-1]), 2)

            # GBM built-in importances (always available, no extra lib)
            base_resp["gbm_importances"] = sorted(
                [{"feature": FEATURE_LABELS.get(f, f), "importance": round(float(v), 5)}
                 for f, v in zip(feat_names, gbm.feature_importances_)],
                key=lambda x: x["importance"], reverse=True
            )

        except Exception as e:
            return Response({**base_resp, "error_xai": f"GBM failed: {str(e)}"})

        # ── SHAP ──────────────────────────────────────
        shap_values  = None
        base_value   = None
        shap_latest  = None

        if SHAP_OK:
            try:
                explainer   = _shap.TreeExplainer(gbm)
                shap_values = explainer.shap_values(X_s)
                base_value  = float(explainer.expected_value)
                shap_latest = shap_values[-1]

                mean_abs_shap = np.abs(shap_values).mean(axis=0)
                shap_rank     = np.argsort(mean_abs_shap)[::-1]

                base_resp["shap_base_value"] = round(base_value, 2)
                base_resp["top_features"] = [
                    {
                        "feature":     feat_names[i],
                        "label":       FEATURE_LABELS.get(feat_names[i], feat_names[i]),
                        "importance":  round(float(mean_abs_shap[i]), 5),
                        "shap_latest": round(float(shap_latest[i]),   5),
                        "direction":   "positive" if shap_latest[i] >= 0 else "negative",
                    }
                    for i in shap_rank[:10]
                ]

                # SHAP charts
                try:
                    base_resp["charts"]["shap_bar"] = _chart_shap_bar(
                        shap_values, feat_names,
                        "SHAP — Global Feature Importance (GBM → Silver Price)")
                except: pass

                try:
                    base_resp["charts"]["shap_waterfall"] = _chart_shap_waterfall(
                        shap_latest, feat_names, base_value, float(gbm_pred[-1]))
                except: pass

                # Top feature scatter
                try:
                    top_feat = feat_names[shap_rank[0]]
                    base_resp["charts"]["top_feature_scatter"] = _chart_top_feature_scatter(
                        df, top_feat, pd.Series(gbm_pred, index=df.index))
                except: pass

            except Exception as e:
                base_resp["error_shap"] = str(e)

        # ── LIME ──────────────────────────────────────
        if LIME_OK:
            try:
                lime_explainer = _lime_tabular.LimeTabularExplainer(
                    training_data = X_s,
                    feature_names = feat_names,
                    mode          = "regression",
                    random_state  = 42,
                )
                lime_exp = lime_explainer.explain_instance(
                    X_s[-1], gbm.predict, num_features=10)

                base_resp["lime_features"] = [
                    {
                        "feature":   FEATURE_LABELS.get(itm[0].split(" ")[0], itm[0]),
                        "weight":    round(float(itm[1]), 5),
                        "direction": "positive" if itm[1] >= 0 else "negative",
                    }
                    for itm in lime_exp.as_list()
                ]

                try:
                    base_resp["charts"]["lime_bar"] = _chart_lime_bar(lime_exp)
                except: pass

            except Exception as e:
                base_resp["error_lime"] = str(e)

        return Response(base_resp)
