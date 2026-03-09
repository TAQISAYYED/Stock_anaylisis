# ══════════════════════════════════════════════════════════════════════════════
# BTC/USD — Hourly Time Series Analysis & Forecasting with Random Forest
# Data Source : Yahoo Finance (yfinance)
# Steps       : Fetch → EDA → Clean → Decompose → Feature Engineering →
#               Train/Test Split → Random Forest → Forecast → Evaluate
# ══════════════════════════════════════════════════════════════════════════════

# ── Step 1: Install dependencies ──────────────────────────────────────────────
# pip install yfinance pandas numpy matplotlib seaborn statsmodels scikit-learn

# ── Step 2: Import libraries ──────────────────────────────────────────────────
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Fetch Live BTC/USD Hourly Data (last 60 days — yfinance max for 1h)
# ══════════════════════════════════════════════════════════════════════════════
print("Fetching BTC-USD hourly data from Yahoo Finance...")
ticker = yf.Ticker("BTC-USD")
raw    = ticker.history(period="7d", interval="1h")   # max allowed for 1h

if raw.empty:
    raise ValueError("No data returned. Check internet connection.")

# Keep only Close price, drop timezone from index
data = raw[["Close"]].copy()
data.index = data.index.tz_localize(None)
data.columns = ["Price"]
data = data.sort_index()

print(f"  Records fetched : {len(data)}")
print(f"  From            : {data.index[0]}")
print(f"  To              : {data.index[-1]}")
print(f"  Price range     : ${data['Price'].min():,.2f}  —  ${data['Price'].max():,.2f}\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 4: EDA — Basic statistics
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("EDA — Descriptive Statistics")
print("=" * 60)
print(data.describe().round(2))
print(f"\nMissing values : {data['Price'].isna().sum()}")
print(f"Duplicates     : {data.index.duplicated().sum()}\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 5: Visualise the raw time series
# ══════════════════════════════════════════════════════════════════════════════
plt.style.use("dark_background")
BG    = "#080a10"
PANEL = "#111520"
GOLD  = "#f0c040"
GREEN = "#00d48c"
RED   = "#ff4d6d"
BLUE  = "#60a5fa"
DIM   = "#6b7494"

fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor(BG)
ax.set_facecolor(PANEL)
ax.plot(data.index, data["Price"], color=GOLD, linewidth=1, label="BTC/USD Close")
ax.fill_between(data.index, data["Price"], alpha=0.08, color=GOLD)
ax.set_title("BTC/USD — Hourly Price (Last 60 Days)", color="white", fontsize=14, pad=12)
ax.set_xlabel("Time", color=DIM)
ax.set_ylabel("Price (USD)", color=DIM)
ax.tick_params(colors=DIM)
for s in ax.spines.values(): s.set_color(PANEL)
ax.legend(facecolor="#0d1018", labelcolor="white", fontsize=9)
ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.6)
plt.tight_layout()
plt.savefig("01_raw_timeseries.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 01_raw_timeseries.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 6: Handle missing values (interpolate)
# ══════════════════════════════════════════════════════════════════════════════
data["Price"] = data["Price"].interpolate(method="time")
print(f"After interpolation — missing: {data['Price'].isna().sum()}\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 7: Outlier detection and cleaning (z-score method)
# ══════════════════════════════════════════════════════════════════════════════
z = np.abs((data["Price"] - data["Price"].mean()) / data["Price"].std())
n_outliers = (z > 3).sum()
data["Price_clean"] = np.where(z > 3, data["Price"].median(), data["Price"])
print(f"Outliers detected (z > 3): {n_outliers}")
print(f"Replaced with series median: ${data['Price'].median():,.2f}\n")

# Work with clean prices from here
data["Value"] = data["Price_clean"]

# ══════════════════════════════════════════════════════════════════════════════
# Step 8: Time series decomposition (period=24 for hourly — 1 day cycle)
# ══════════════════════════════════════════════════════════════════════════════
print("Running seasonal decomposition (period=24 hours)...")
decomp = seasonal_decompose(data["Value"], model="additive", period=24)

fig2 = plt.figure(figsize=(14, 10))
fig2.patch.set_facecolor(BG)
gs   = gridspec.GridSpec(4, 1, hspace=0.45)

panels = [
    (decomp.observed,  "Observed",   GOLD),
    (decomp.trend,     "Trend",      BLUE),
    (decomp.seasonal,  "Seasonality (24h cycle)", GREEN),
    (decomp.resid,     "Residuals",  RED),
]
for i, (series, title, color) in enumerate(panels):
    ax = fig2.add_subplot(gs[i])
    ax.set_facecolor(PANEL)
    ax.plot(series, color=color, linewidth=0.9)
    ax.set_title(title, color="white", fontsize=11, pad=6)
    ax.tick_params(colors=DIM, labelsize=8)
    ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.4, alpha=0.5)
    for s in ax.spines.values(): s.set_color(PANEL)

fig2.suptitle("BTC/USD — Seasonal Decomposition (Hourly)", color="white", fontsize=14, y=1.01)
plt.savefig("02_decomposition.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 02_decomposition.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 9: Stationarity test (Augmented Dickey-Fuller)
# ══════════════════════════════════════════════════════════════════════════════
adf_result = adfuller(data["Value"].dropna())
print("Augmented Dickey-Fuller Test:")
print(f"  ADF Statistic : {adf_result[0]:.4f}")
print(f"  p-value       : {adf_result[1]:.4f}")
print(f"  Stationary    : {'YES' if adf_result[1] < 0.05 else 'NO — differencing needed'}\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 10: Feature Engineering for Random Forest
#   Lag features      : price at t-1, t-2, t-3, t-6, t-12, t-24
#   Rolling features  : rolling mean and std over 6h and 24h windows
#   Calendar features : hour of day, day of week
#   Returns           : 1h percent change
# ══════════════════════════════════════════════════════════════════════════════
print("Engineering features...")
df = data[["Value"]].copy()

# Lag features
for lag in [1, 2, 3, 6, 12, 24]:
    df[f"lag_{lag}"] = df["Value"].shift(lag)

# Rolling statistics
for window in [6, 24]:
    df[f"rolling_mean_{window}"] = df["Value"].shift(1).rolling(window).mean()
    df[f"rolling_std_{window}"]  = df["Value"].shift(1).rolling(window).std()

# Calendar
df["hour"]       = df.index.hour
df["day_of_week"] = df.index.dayofweek
df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)

# 1h return
df["return_1h"] = df["Value"].pct_change().shift(1) * 100

# Target
df["target"] = df["Value"]

df.dropna(inplace=True)
print(f"  Features : {df.shape[1] - 1}")
print(f"  Samples  : {len(df)}\n")

FEATURE_COLS = [c for c in df.columns if c != "target"]

# ══════════════════════════════════════════════════════════════════════════════
# Step 11: Train / Test split  (80% train — 20% test, no shuffle — time order)
# ══════════════════════════════════════════════════════════════════════════════
split = int(len(df) * 0.80)
train = df.iloc[:split]
test  = df.iloc[split:]

X_train, y_train = train[FEATURE_COLS], train["target"]
X_test,  y_test  = test[FEATURE_COLS],  test["target"]

print(f"Train : {len(train)} rows  ({train.index[0].date()} → {train.index[-1].date()})")
print(f"Test  : {len(test)}  rows  ({test.index[0].date()} → {test.index[-1].date()})\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 12: Random Forest model
# ══════════════════════════════════════════════════════════════════════════════
print("Training Random Forest...")
rf = RandomForestRegressor(
    n_estimators     = 300,
    max_depth        = 10,
    min_samples_leaf = 4,
    max_features     = "sqrt",
    random_state     = 42,
    n_jobs           = -1,
)
rf.fit(X_train, y_train)
print("  Training complete.\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 13: Evaluate on test set
# ══════════════════════════════════════════════════════════════════════════════
y_pred = rf.predict(X_test)

mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2   = r2_score(y_test, y_pred)
mape = np.mean(np.abs((y_test.values - y_pred) / y_test.values)) * 100

print("=" * 60)
print("Model Evaluation — Test Set")
print("=" * 60)
print(f"  MAE   (Mean Absolute Error)       : ${mae:,.2f}")
print(f"  RMSE  (Root Mean Squared Error)   : ${rmse:,.2f}")
print(f"  MAPE  (Mean Absolute % Error)     : {mape:.2f}%")
print(f"  R²    (Coefficient of Det.)       : {r2:.4f}\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 14: Forecast on test set and plot results
# ══════════════════════════════════════════════════════════════════════════════
fig3, ax3 = plt.subplots(figsize=(14, 6))
fig3.patch.set_facecolor(BG)
ax3.set_facecolor(PANEL)

ax3.plot(train.index, y_train,         color=BLUE,  linewidth=0.8, label="Training Data",     alpha=0.7)
ax3.plot(test.index,  y_test,          color=GOLD,  linewidth=1.5, label="Actual Values")
ax3.plot(test.index,  y_pred,          color=GREEN, linewidth=1.2, label="RF Forecasted",     linestyle="--")

# Confidence band: ± 1 RMSE
ax3.fill_between(test.index,
                 y_pred - rmse, y_pred + rmse,
                 alpha=0.12, color=GREEN, label=f"±1 RMSE  (${rmse:,.0f})")

ax3.set_title(
    f"BTC/USD — Random Forest Forecast vs Actual\n"
    f"MAE ${mae:,.0f}   RMSE ${rmse:,.0f}   MAPE {mape:.2f}%   R² {r2:.4f}",
    color="white", fontsize=13, pad=12
)
ax3.set_xlabel("Time", color=DIM)
ax3.set_ylabel("Price (USD)", color=DIM)
ax3.tick_params(colors=DIM)
for s in ax3.spines.values(): s.set_color(PANEL)
ax3.legend(facecolor="#0d1018", labelcolor="white", fontsize=9)
ax3.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)
plt.tight_layout()
plt.savefig("03_forecast_vs_actual.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 03_forecast_vs_actual.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 15: Feature Importance
# ══════════════════════════════════════════════════════════════════════════════
importance_df = pd.DataFrame({
    "Feature":    FEATURE_COLS,
    "Importance": rf.feature_importances_,
}).sort_values("Importance", ascending=True)

fig4, ax4 = plt.subplots(figsize=(10, 7))
fig4.patch.set_facecolor(BG)
ax4.set_facecolor(PANEL)

colors_bar = [GOLD if v > importance_df["Importance"].median() else BLUE
              for v in importance_df["Importance"]]
ax4.barh(importance_df["Feature"], importance_df["Importance"],
         color=colors_bar, edgecolor=PANEL, height=0.7)
ax4.set_title("Random Forest — Feature Importances", color="white", fontsize=13, pad=12)
ax4.set_xlabel("Importance Score", color=DIM)
ax4.tick_params(colors=DIM, labelsize=9)
for s in ax4.spines.values(): s.set_color(PANEL)
ax4.grid(axis="x", color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)
plt.tight_layout()
plt.savefig("04_feature_importance.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 04_feature_importance.png\n")

# Top 3 features
top3 = importance_df.sort_values("Importance", ascending=False).head(3)
print("Top 3 most important features:")
for _, row in top3.iterrows():
    print(f"  {row['Feature']:25s}  {row['Importance']:.4f}")

# ══════════════════════════════════════════════════════════════════════════════
# Step 16: Residual analysis
# ══════════════════════════════════════════════════════════════════════════════
residuals = y_test.values - y_pred

fig5, axes5 = plt.subplots(1, 2, figsize=(14, 5))
fig5.patch.set_facecolor(BG)

# Residuals over time
ax5a = axes5[0]
ax5a.set_facecolor(PANEL)
ax5a.plot(test.index, residuals, color=RED, linewidth=0.8)
ax5a.axhline(0, color=DIM, linestyle="--", linewidth=1)
ax5a.set_title("Residuals over Time", color="white", fontsize=12, pad=10)
ax5a.set_xlabel("Time", color=DIM)
ax5a.set_ylabel("Residual (USD)", color=DIM)
ax5a.tick_params(colors=DIM)
for s in ax5a.spines.values(): s.set_color(PANEL)
ax5a.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)

# Residual distribution
ax5b = axes5[1]
ax5b.set_facecolor(PANEL)
ax5b.hist(residuals, bins=40, color=GOLD, edgecolor=PANEL, alpha=0.85)
ax5b.axvline(0,                  color=RED,   linestyle="--", linewidth=1.5, label="Zero")
ax5b.axvline(residuals.mean(),   color=GREEN, linestyle="--", linewidth=1.2, label=f"Mean ${residuals.mean():,.0f}")
ax5b.set_title("Residual Distribution", color="white", fontsize=12, pad=10)
ax5b.set_xlabel("Residual (USD)", color=DIM)
ax5b.set_ylabel("Frequency", color=DIM)
ax5b.tick_params(colors=DIM)
for s in ax5b.spines.values(): s.set_color(PANEL)
ax5b.legend(facecolor="#0d1018", labelcolor="white", fontsize=9)
ax5b.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)

fig5.suptitle("BTC/USD Random Forest — Residual Analysis", color="white", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig("05_residuals.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 05_residuals.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Step 17: Forecast next 24 hours (1 day ahead — recursive)
# ══════════════════════════════════════════════════════════════════════════════
print("Generating 24-hour ahead forecast (recursive)...")

last_known = df.iloc[-1].copy()
future_prices  = []
future_times   = []
current_window = df["Value"].values.copy()

for h in range(1, 25):
    next_time = df.index[-1] + pd.Timedelta(hours=h)

    # Build feature row from last known state
    row = {}
    for lag in [1, 2, 3, 6, 12, 24]:
        idx = len(current_window) - lag
        row[f"lag_{lag}"] = current_window[idx] if idx >= 0 else current_window[0]

    for window in [6, 24]:
        tail = current_window[-window:] if len(current_window) >= window else current_window
        row[f"rolling_mean_{window}"] = tail.mean()
        row[f"rolling_std_{window}"]  = tail.std()

    row["hour"]        = next_time.hour
    row["day_of_week"] = next_time.dayofweek
    row["is_weekend"]  = int(next_time.dayofweek >= 5)
    row["return_1h"]   = (current_window[-1] - current_window[-2]) / current_window[-2] * 100 \
                         if len(current_window) >= 2 else 0.0

    X_future = pd.DataFrame([row])[FEATURE_COLS]
    pred     = rf.predict(X_future)[0]

    future_prices.append(pred)
    future_times.append(next_time)
    current_window = np.append(current_window, pred)

future_df = pd.DataFrame({"Forecast": future_prices}, index=future_times)

# Plot 24h ahead forecast
fig6, ax6 = plt.subplots(figsize=(14, 6))
fig6.patch.set_facecolor(BG)
ax6.set_facecolor(PANEL)

# Show last 72 hours of actual data as context
context = data["Value"].iloc[-72:]
ax6.plot(context.index, context.values,     color=GOLD,  linewidth=1.2, label="Actual (last 72h)")
ax6.plot(future_df.index, future_df["Forecast"],
         color=GREEN, linewidth=1.8, linestyle="--", label="24h Forecast", marker="o", markersize=3)

# Uncertainty band widens over time
for i, (t, p) in enumerate(zip(future_df.index, future_df["Forecast"])):
    band = rmse * (1 + i * 0.04)   # uncertainty grows with horizon
    ax6.fill_between([t], [p - band], [p + band], alpha=0.06, color=GREEN)

ax6.axvline(data.index[-1], color=RED, linestyle="--", linewidth=1, alpha=0.6, label="Forecast start")

last_actual   = context.values[-1]
last_forecast = future_df["Forecast"].iloc[-1]
direction     = "UP" if last_forecast > last_actual else "DOWN"
change_pct    = (last_forecast - last_actual) / last_actual * 100

ax6.set_title(
    f"BTC/USD — 24-Hour Ahead Forecast\n"
    f"Current ${last_actual:,.2f}   →   24h Forecast ${last_forecast:,.2f}   "
    f"({change_pct:+.2f}%  {direction})",
    color="white", fontsize=13, pad=12
)
ax6.set_xlabel("Time", color=DIM)
ax6.set_ylabel("Price (USD)", color=DIM)
ax6.tick_params(colors=DIM)
for s in ax6.spines.values(): s.set_color(PANEL)
ax6.legend(facecolor="#0d1018", labelcolor="white", fontsize=9)
ax6.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)
plt.tight_layout()
plt.savefig("06_24h_forecast.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.show()
print("Saved: 06_24h_forecast.png\n")

# ══════════════════════════════════════════════════════════════════════════════
# Final Summary
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
print(f"  Asset           : BTC/USD")
print(f"  Interval        : 1 hour")
print(f"  Data period     : 60 days")
print(f"  Total samples   : {len(df)}")
print(f"  Train / Test    : {len(train)} / {len(test)}")
print(f"  Model           : Random Forest  (n_estimators=300)")
print(f"  MAE             : ${mae:,.2f}")
print(f"  RMSE            : ${rmse:,.2f}")
print(f"  MAPE            : {mape:.2f}%")
print(f"  R²              : {r2:.4f}")
print(f"  Current Price   : ${last_actual:,.2f}")
print(f"  24h Prediction  : ${last_forecast:,.2f}  ({change_pct:+.2f}%)")
print("=" * 60)
print("\nPlots saved:")
for f in ["01_raw_timeseries.png","02_decomposition.png","03_forecast_vs_actual.png",
          "04_feature_importance.png","05_residuals.png","06_24h_forecast.png"]:
    print(f"  {f}")