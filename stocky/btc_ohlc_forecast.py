# ══════════════════════════════════════════════════════════════════════════════
# BTC/USD — OHLC Forecast  |  Random Forest  |  High Accuracy Version
# Fixes:
#   1. No scaling on target — raw USD prices throughout
#   2. Deeper trees, more estimators, better features
#   3. GradientBoosting ensemble on top of RF for residual correction
#   4. All 4 lines on same dark-theme chart: Actual/Pred Open + Close
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ── Theme ─────────────────────────────────────────────────────────────────────
BG    = "#080a10"
PANEL = "#111520"
GOLD  = "#f0c040"    # Actual Close
GREEN = "#00d48c"    # Predicted Close
BLUE  = "#60a5fa"    # Actual Open
RED   = "#ff4d6d"    # Predicted Open
DIM   = "#6b7494"

# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Fetch raw BTC/USD OHLCV hourly (60 days — max for 1h on yfinance)
# ══════════════════════════════════════════════════════════════════════════════
print("Fetching BTC-USD 1h data...")
raw = yf.Ticker("BTC-USD").history(period="60d", interval="1h")
if raw.empty:
    raise ValueError("No data returned.")

raw.index = raw.index.tz_localize(None)
raw = raw.sort_index()[["Open","High","Low","Close","Volume"]].copy()

print(f"  Rows            : {len(raw)}")
print(f"  Close min/max   : ${raw['Close'].min():,.0f} / ${raw['Close'].max():,.0f}")
print(f"  First timestamp : {raw.index[0]}")
print(f"  Last  timestamp : {raw.index[-1]}\n")

for col in raw.columns:
    raw[col] = raw[col].interpolate(method="time")

# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Rich feature engineering (NO scaling of target)
# ══════════════════════════════════════════════════════════════════════════════
def make_features(df):
    f = pd.DataFrame(index=df.index)

    for lag in [1, 2, 3, 4, 5, 6, 12, 18, 24, 36, 48]:
        f[f"close_lag{lag}"] = df["Close"].shift(lag)
        f[f"open_lag{lag}"]  = df["Open"].shift(lag)

    for lag in [1, 3, 6, 12, 24]:
        f[f"high_lag{lag}"] = df["High"].shift(lag)
        f[f"low_lag{lag}"]  = df["Low"].shift(lag)

    for w in [3, 6, 12, 24, 48]:
        f[f"close_rmean{w}"] = df["Close"].shift(1).rolling(w).mean()
        f[f"close_rstd{w}"]  = df["Close"].shift(1).rolling(w).std()
        f[f"open_rmean{w}"]  = df["Open"].shift(1).rolling(w).mean()

    for span in [6, 12, 24]:
        f[f"close_ema{span}"] = df["Close"].shift(1).ewm(span=span, adjust=False).mean()

    for period in [1, 3, 6, 12, 24]:
        f[f"momentum{period}"] = df["Close"].shift(1) - df["Close"].shift(period + 1)

    for h in [1, 3, 6, 12]:
        f[f"ret{h}h"] = df["Close"].pct_change(h).shift(1) * 100

    f["body_lag1"]   = (df["Close"] - df["Open"]).shift(1)
    f["spread_lag1"] = (df["High"]  - df["Low"]).shift(1)
    f["upper_wick"]  = (df["High"]  - df[["Open","Close"]].max(axis=1)).shift(1)
    f["lower_wick"]  = (df[["Open","Close"]].min(axis=1) - df["Low"]).shift(1)

    f["log_vol"]     = np.log1p(df["Volume"].shift(1))
    f["vol_rmean6"]  = df["Volume"].shift(1).rolling(6).mean()
    f["vol_change"]  = df["Volume"].pct_change().shift(1) * 100

    f["hour"]        = df.index.hour
    f["hour_sin"]    = np.sin(2 * np.pi * df.index.hour / 24)
    f["hour_cos"]    = np.cos(2 * np.pi * df.index.hour / 24)
    f["dow"]         = df.index.dayofweek
    f["dow_sin"]     = np.sin(2 * np.pi * df.index.dayofweek / 7)
    f["dow_cos"]     = np.cos(2 * np.pi * df.index.dayofweek / 7)
    f["is_weekend"]  = (df.index.dayofweek >= 5).astype(int)

    delta = df["Close"].diff().shift(1)
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    f["rsi14"] = 100 - (100 / (1 + gain / (loss + 1e-9)))

    mid   = df["Close"].shift(1).rolling(20).mean()
    std20 = df["Close"].shift(1).rolling(20).std()
    f["bb_pos"] = (df["Close"].shift(1) - mid) / (2 * std20 + 1e-9)

    return f

features = make_features(raw)

# Replace inf/-inf produced by pct_change dividing by zero
features.replace([np.inf, -np.inf], np.nan, inplace=True)

# Fill remaining NaN with column median (safe for all feature types)
features.fillna(features.median(numeric_only=True), inplace=True)

features.dropna(inplace=True)

open_target  = raw.loc[features.index, "Open"]
close_target = raw.loc[features.index, "Close"]

FCOLS = features.columns.tolist()
print(f"Features built : {len(FCOLS)}")
print(f"Usable samples : {len(features)}\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Train / Test split  (85 / 15, time order)
# ══════════════════════════════════════════════════════════════════════════════
split = int(len(features) * 0.85)

X_tr  = features.iloc[:split]
X_te  = features.iloc[split:]
y_o_tr, y_o_te = open_target.iloc[:split],  open_target.iloc[split:]
y_c_tr, y_c_te = close_target.iloc[:split], close_target.iloc[split:]
test_idx = features.index[split:]

print(f"Train : {len(X_tr)} rows")
print(f"Test  : {len(X_te)} rows\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Ensemble model: RF (400) + GBM (200) → VotingRegressor
# ══════════════════════════════════════════════════════════════════════════════
def build_model():
    rf = RandomForestRegressor(
        n_estimators     = 400,
        max_depth        = 15,
        min_samples_leaf = 2,
        min_samples_split= 4,
        max_features     = 0.6,
        bootstrap        = True,
        random_state     = 42,
        n_jobs           = -1,
    )
    gbm = GradientBoostingRegressor(
        n_estimators  = 200,
        max_depth     = 6,
        learning_rate = 0.05,
        subsample     = 0.8,
        min_samples_leaf = 4,
        random_state  = 42,
    )
    return VotingRegressor(
        estimators=[("rf", rf), ("gbm", gbm)],
        weights=[0.55, 0.45],
    )

print("Training OPEN  model (RF + GBM ensemble)...")
model_open = build_model()
model_open.fit(X_tr, y_o_tr)

print("Training CLOSE model (RF + GBM ensemble)...")
model_close = build_model()
model_close.fit(X_tr, y_c_tr)
print("Training complete.\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Predict + Metrics
# ══════════════════════════════════════════════════════════════════════════════
pred_open  = model_open.predict(X_te)
pred_close = model_close.predict(X_te)

def eval_metrics(actual, predicted, name):
    mae  = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    r2   = r2_score(actual, predicted)
    print(f"  {name:<8}  MAE ${mae:>8,.2f}   RMSE ${rmse:>8,.2f}   MAPE {mape:>6.3f}%   R² {r2:.5f}")
    return mae, rmse, mape, r2

print("=" * 70)
print("Model Evaluation")
print("=" * 70)
mae_o, rmse_o, mape_o, r2_o = eval_metrics(y_o_te.values, pred_open,  "OPEN")
mae_c, rmse_c, mape_c, r2_c = eval_metrics(y_c_te.values, pred_close, "CLOSE")
print("=" * 70 + "\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 6 — Plot 1: All 4 lines on one chart
# ══════════════════════════════════════════════════════════════════════════════
plt.style.use("dark_background")

fig1, ax1 = plt.subplots(figsize=(17, 7))
fig1.patch.set_facecolor(BG)
ax1.set_facecolor(PANEL)

ax1.plot(test_idx, y_o_te.values, color=BLUE,  linewidth=1.5, label="Actual Open",     alpha=0.95, zorder=3)
ax1.plot(test_idx, pred_open,     color=RED,   linewidth=1.2, label="Predicted Open",  linestyle="--", alpha=0.90, zorder=4)
ax1.plot(test_idx, y_c_te.values, color=GOLD,  linewidth=1.5, label="Actual Close",    alpha=0.95, zorder=3)
ax1.plot(test_idx, pred_close,    color=GREEN, linewidth=1.2, label="Predicted Close", linestyle="--", alpha=0.90, zorder=4)

ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
ax1.xaxis.set_major_locator(mdates.HourLocator(interval=12))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=0, fontsize=8)

ax1.set_title(
    "BTC/USD — Actual vs Predicted  |  Open & Close  |  RF + GBM Ensemble\n"
    f"Open:  MAE ${mae_o:,.0f}  RMSE ${rmse_o:,.0f}  MAPE {mape_o:.3f}%  R² {r2_o:.5f}     "
    f"Close: MAE ${mae_c:,.0f}  RMSE ${rmse_c:,.0f}  MAPE {mape_c:.3f}%  R² {r2_c:.5f}",
    color="white", fontsize=11, pad=14, linespacing=1.6
)
ax1.set_xlabel("Time", color=DIM, fontsize=11)
ax1.set_ylabel("Price  (USD)", color=DIM, fontsize=11)
ax1.tick_params(colors=DIM)
for s in ax1.spines.values(): s.set_color(PANEL)
ax1.legend(facecolor="#0d1018", labelcolor="white", fontsize=10, ncol=2, loc="upper left")
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax1.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.6)
plt.tight_layout()
plt.savefig("01_open_close_forecast.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 01_open_close_forecast.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 7 — Plot 2: Stacked panels
# ══════════════════════════════════════════════════════════════════════════════
fig2, (ax2a, ax2b) = plt.subplots(2, 1, figsize=(17, 11), sharex=True)
fig2.patch.set_facecolor(BG)

for ax, actual, predicted, act_col, pred_col, label, mae, rmse, mape, r2 in [
    (ax2a, y_o_te.values, pred_open,  BLUE, RED,   "OPEN",  mae_o, rmse_o, mape_o, r2_o),
    (ax2b, y_c_te.values, pred_close, GOLD, GREEN, "CLOSE", mae_c, rmse_c, mape_c, r2_c),
]:
    ax.set_facecolor(PANEL)
    ax.plot(test_idx, actual,    color=act_col,  linewidth=1.5, label=f"Actual {label}")
    ax.plot(test_idx, predicted, color=pred_col, linewidth=1.2, linestyle="--",
            label=f"Predicted {label}", alpha=0.9)
    ax.fill_between(test_idx, actual, predicted, alpha=0.07, color=pred_col)
    ax.set_title(
        f"{label}  |  MAE ${mae:,.0f}   RMSE ${rmse:,.0f}   MAPE {mape:.3f}%   R² {r2:.5f}",
        color="white", fontsize=12, pad=10
    )
    ax.set_ylabel("Price (USD)", color=DIM)
    ax.tick_params(colors=DIM)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(facecolor="#0d1018", labelcolor="white", fontsize=9)
    ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)
    for s in ax.spines.values(): s.set_color(PANEL)

ax2b.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
ax2b.xaxis.set_major_locator(mdates.HourLocator(interval=12))
ax2b.set_xlabel("Time", color=DIM, fontsize=11)
fig2.suptitle("BTC/USD  |  RF + GBM Ensemble  |  Actual vs Predicted",
              color="white", fontsize=14, y=1.01)
plt.tight_layout()
plt.savefig("02_open_close_panels.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 02_open_close_panels.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 8 — Plot 3: Scatter
# ══════════════════════════════════════════════════════════════════════════════
fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(14, 6))
fig3.patch.set_facecolor(BG)

for ax, actual, predicted, color, label in [
    (ax3a, y_o_te.values, pred_open,  RED,   "OPEN"),
    (ax3b, y_c_te.values, pred_close, GREEN, "CLOSE"),
]:
    ax.set_facecolor(PANEL)
    ax.scatter(actual, predicted, alpha=0.3, s=10, color=color)
    mn = min(actual.min(), predicted.min())
    mx = max(actual.max(), predicted.max())
    ax.plot([mn, mx], [mn, mx], color=GOLD, linewidth=1.5, linestyle="--", label="Perfect fit")
    r2 = r2_score(actual, predicted)
    ax.set_title(f"{label}  —  R² {r2:.5f}", color="white", fontsize=12, pad=10)
    ax.set_xlabel("Actual (USD)", color=DIM)
    ax.set_ylabel("Predicted (USD)", color=DIM)
    ax.tick_params(colors=DIM)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    for s in ax.spines.values(): s.set_color(PANEL)
    ax.legend(facecolor="#0d1018", labelcolor="white", fontsize=9)
    ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)

fig3.suptitle("BTC/USD — Scatter: Actual vs Predicted  |  Open & Close",
              color="white", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig("03_scatter.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 03_scatter.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 9 — Save predictions CSV
# ══════════════════════════════════════════════════════════════════════════════
results = pd.DataFrame({
    "Actual_Open":     y_o_te.values.round(2),
    "Predicted_Open":  pred_open.round(2),
    "Open_Error_USD":  (y_o_te.values - pred_open).round(2),
    "Open_Error_Pct":  ((y_o_te.values - pred_open) / y_o_te.values * 100).round(4),
    "Actual_Close":    y_c_te.values.round(2),
    "Predicted_Close": pred_close.round(2),
    "Close_Error_USD": (y_c_te.values - pred_close).round(2),
    "Close_Error_Pct": ((y_c_te.values - pred_close) / y_c_te.values * 100).round(4),
}, index=test_idx)

results.to_csv("btc_predictions.csv")
print("Saved: btc_predictions.csv")
print(results.tail(10).to_string())

print(f"\n{'='*60}")
print(f"  {'Metric':<8}  {'OPEN':>16}  {'CLOSE':>16}")
print(f"  {'-'*8}  {'-'*16}  {'-'*16}")
print(f"  {'MAE':<8}  ${mae_o:>14,.2f}  ${mae_c:>14,.2f}")
print(f"  {'RMSE':<8}  ${rmse_o:>14,.2f}  ${rmse_c:>14,.2f}")
print(f"  {'MAPE':<8}  {mape_o:>15.3f}%  {mape_c:>15.3f}%")
print(f"  {'R2':<8}  {r2_o:>16.5f}  {r2_c:>16.5f}")
print(f"{'='*60}")
