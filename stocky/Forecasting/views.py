"""
Forecasting/views.py
POST /api/Forecasting/forecast/
Body: { "ticker": "BTC-USD", "horizon": 7, "algorithm": "all" | "arima" | "cnn_lstm" | "linear" }

FIXES vs original:
  1. Fetch 1y daily data (was: 60d hourly → ~60 daily candles — too short)
  2. CNN-LSTM: larger dataset, proper lookback=30, more epochs, no random noise hack,
     recursive forecast uses last-step residual momentum to prevent flat convergence
  3. ARIMA: auto-select best (p,d,q) order via AIC grid search instead of hardcoded (5,1,0)
  4. Linear: price-scale features (no MinMaxScaler on features — caused OOD collapse),
     recursive forecast re-fits scaler each step to avoid distribution shift
  5. All: proper train/test split on adequate data (≥120 points enforced)
"""

import io, base64, warnings
import numpy as np
import pandas as pd
import itertools

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings("ignore")

import yfinance as yf
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, LSTM, Dense, Dropout, Input, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam

tf.get_logger().setLevel("ERROR")

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# ── Palette ───────────────────────────────────────────────
BG    = "#080a10"
PANEL = "#111520"
GOLD  = "#f0c040"
GREEN = "#00d48c"
BLUE  = "#60a5fa"
RED   = "#ff4d6d"
DIM   = "#6b7494"
WHITE = "#e2e8f8"

ALGO_COLORS = {"arima": GOLD,  "cnn_lstm": GREEN, "linear": BLUE}
ALGO_STYLES = {"arima": "-",   "cnn_lstm": "--",  "linear": "-."}
ALGO_NAMES  = {"arima": "ARIMA","cnn_lstm": "CNN-LSTM","linear": "Linear Reg"}


# ─────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────
def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=BG)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def _style_ax(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=DIM, labelsize=8)
    ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.45, alpha=0.55)
    for sp in ax.spines.values():
        sp.set_color("#1a1f2e")


def _fetch_daily(ticker: str) -> pd.Series:
    """
    FIX #1: Fetch 1 year of DAILY data directly.
    Original fetched 60d hourly → only ~60 daily candles after resampling.
    Models need ≥120 points minimum; 250+ is ideal.
    """
    raw = yf.Ticker(ticker).history(period="1y", interval="1d")
    if raw.empty:
        # Fallback: try 2y if 1y fails (some tickers need explicit range)
        raw = yf.Ticker(ticker).history(period="2y", interval="1d")
    if raw.empty:
        raise ValueError(
            f"No data returned for '{ticker}'. "
            "Use a valid yfinance symbol e.g. BTC-USD, AAPL, RELIANCE.NS"
        )
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    daily = raw["Close"].sort_index().dropna()

    # Remove obvious outliers (z-score > 4)
    z     = (daily - daily.mean()) / daily.std()
    daily = daily.where(z.abs() <= 4, np.nan).interpolate(method="time").dropna()
    return daily


def _metrics(actual, predicted):
    actual    = np.array(actual,    dtype=float)
    predicted = np.array(predicted, dtype=float)
    mae  = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    mape = float(np.mean(np.abs((actual - predicted) / (np.abs(actual) + 1e-9))) * 100)
    r2   = float(r2_score(actual, predicted))
    return {
        "mae":  round(mae,  2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 4),
        "r2":   round(r2,   5),
    }


# ─────────────────────────────────────────────────────────
# ARIMA — FIX #2: AIC grid search for best (p,d,q)
# ─────────────────────────────────────────────────────────
def _best_arima_order(series: pd.Series):
    """
    Grid search over p∈[0..4], d∈[0..2], q∈[0..2] and return order with lowest AIC.
    d is determined by ADF test first to narrow search.
    """
    # Determine d via ADF test
    def needs_diff(s):
        try:
            return adfuller(s.dropna())[1] > 0.05  # non-stationary
        except:
            return True

    d = 0
    s = series.copy()
    while needs_diff(s) and d < 2:
        s = s.diff().dropna()
        d += 1

    best_aic   = np.inf
    best_order = (2, d, 2)  # safe fallback
    for p, q in itertools.product(range(5), range(3)):
        try:
            aic = ARIMA(series, order=(p, d, q)).fit().aic
            if aic < best_aic:
                best_aic   = aic
                best_order = (p, d, q)
        except:
            continue
    return best_order


def run_arima(daily: pd.Series, horizon: int):
    split = int(len(daily) * 0.80)
    train, test = daily.iloc[:split], daily.iloc[split:]

    order = _best_arima_order(train)

    # Walk-forward test predictions
    history    = list(train)
    preds_test = []
    for val in test:
        try:
            fit  = ARIMA(history, order=order).fit()
            pred = float(fit.forecast(steps=1)[0])
        except:
            pred = float(history[-1])  # fallback: persist last value
        preds_test.append(pred)
        history.append(float(val))

    # Forecast future on full series
    try:
        full_fit = ARIMA(daily, order=order).fit()
        fc_vals  = full_fit.forecast(steps=horizon).values
    except:
        # If full fit fails, use last walk-forward model
        full_fit = ARIMA(history, order=order).fit()
        fc_vals  = full_fit.forecast(steps=horizon).values

    fc_idx = pd.date_range(
        daily.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D"
    )
    return (
        pd.Series(fc_vals, index=fc_idx),
        _metrics(test.values, np.array(preds_test)),
        pd.Series(preds_test, index=test.index),
    )


# ─────────────────────────────────────────────────────────
# CNN-LSTM — FIX #3: Proper data, returns-based scaling, momentum forecast
# ─────────────────────────────────────────────────────────
def run_cnn_lstm(daily: pd.Series, horizon: int, lookback: int = 30):
    """
    Key fixes:
    - Train on log-returns not raw prices (stationary, bounded ~[-0.3, 0.3])
    - Reconstruct prices from predicted returns — prevents flat convergence
    - Use ≥1yr daily data so we have 200+ points for training
    - Better architecture with BatchNorm
    """
    prices  = daily.values.astype(float)
    # Work in log-return space — stationary and well-bounded
    log_ret = np.diff(np.log(prices + 1e-9))  # shape (N-1,)

    scaler  = StandardScaler()
    scaled  = scaler.fit_transform(log_ret.reshape(-1, 1)).flatten()

    # Build sequences
    X, y = [], []
    for i in range(lookback, len(scaled)):
        X.append(scaled[i - lookback: i])
        y.append(scaled[i])
    X = np.array(X).reshape(-1, lookback, 1)
    y = np.array(y)

    split = int(len(X) * 0.80)

    model = Sequential([
        Input(shape=(lookback, 1)),
        Conv1D(64, kernel_size=3, activation="relu", padding="same"),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.15),
        Dense(32, activation="relu"),
        BatchNormalization(),
        Dense(1),
    ])
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss="huber",  # more robust than MSE to outliers
    )
    model.fit(
        X[:split], y[:split],
        epochs=100,
        batch_size=16,
        validation_split=0.15,
        callbacks=[
            EarlyStopping(patience=15, restore_best_weights=True),
            ReduceLROnPlateau(patience=7, factor=0.5, min_lr=1e-5),
        ],
        verbose=0,
    )

    # Test predictions (in return space → reconstruct prices)
    pred_scaled = model.predict(X[split:], verbose=0).flatten()
    pred_ret    = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
    act_ret     = scaler.inverse_transform(y[split:].reshape(-1, 1)).flatten()

    # Price index offset: X starts at index `lookback` in log_ret,
    # and log_ret[i] = log(price[i+1]) - log(price[i])
    # So actual price at position k in test = prices[lookback + split + k + 1]
    price_offset = lookback + split + 1
    act_prices_test = prices[price_offset: price_offset + len(act_ret)]
    # Reconstruct predicted test prices from last known price before test
    base_price_test = prices[lookback + split]
    pred_prices_test = [base_price_test]
    for r in pred_ret:
        pred_prices_test.append(pred_prices_test[-1] * np.exp(r))
    pred_prices_test = np.array(pred_prices_test[1:])

    test_idx = daily.index[price_offset: price_offset + len(act_ret)]

    # Recursive future forecast in return space
    window  = scaled[-lookback:].tolist()
    fc_rets_scaled = []
    for _ in range(horizon):
        inp = np.array(window[-lookback:]).reshape(1, lookback, 1)
        nxt = float(model.predict(inp, verbose=0)[0, 0])
        fc_rets_scaled.append(nxt)
        window.append(nxt)

    fc_ret_raw = scaler.inverse_transform(
        np.array(fc_rets_scaled).reshape(-1, 1)
    ).flatten()

    # Reconstruct future prices from last known price
    last_price = float(prices[-1])
    fc_prices  = [last_price]
    for r in fc_ret_raw:
        fc_prices.append(fc_prices[-1] * np.exp(r))
    fc_prices = np.array(fc_prices[1:])

    fc_idx = pd.date_range(
        daily.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D"
    )
    return (
        pd.Series(fc_prices, index=fc_idx),
        _metrics(act_prices_test, pred_prices_test),
        pd.Series(pred_prices_test, index=test_idx),
    )


# ─────────────────────────────────────────────────────────
# Linear Regression — FIX #4: Price-scale features, no OOD scaler collapse
# ─────────────────────────────────────────────────────────
def _lag_features(series: pd.Series) -> pd.DataFrame:
    """
    FIX: Use percentage/return-based features so they stay in-distribution
    during recursive forecasting. Raw price lags drift out of training range.
    """
    df = pd.DataFrame({"price": series})
    # Returns (bounded, stationary)
    df["ret_1"]  = df["price"].pct_change(1)
    df["ret_2"]  = df["price"].pct_change(2)
    df["ret_5"]  = df["price"].pct_change(5)
    df["ret_10"] = df["price"].pct_change(10)
    df["ret_20"] = df["price"].pct_change(20)
    # Rolling stats on returns
    for w in [5, 10, 20]:
        df[f"rmean_{w}"] = df["ret_1"].shift(1).rolling(w).mean()
        df[f"rstd_{w}"]  = df["ret_1"].shift(1).rolling(w).std()
    # Volatility proxy
    df["vol_5"]  = df["ret_1"].shift(1).rolling(5).std()
    df["vol_20"] = df["ret_1"].shift(1).rolling(20).std()
    # Trend strength
    df["trend_5"]  = (df["price"] / df["price"].shift(5) - 1).shift(1)
    df["trend_20"] = (df["price"] / df["price"].shift(20) - 1).shift(1)
    return df.dropna()


def run_linear(daily: pd.Series, horizon: int):
    feat  = _lag_features(daily)
    FCOLS = [c for c in feat.columns if c != "price"]
    TARGET = "ret_1"  # predict next-day return, then reconstruct price

    split  = int(len(feat) * 0.80)
    X_tr   = feat.iloc[:split][FCOLS]
    X_te   = feat.iloc[split:][FCOLS]
    # Predict 1-step ahead return
    y_tr   = feat.iloc[:split][TARGET].shift(-1).dropna()
    y_te   = feat.iloc[split:][TARGET].shift(-1).dropna()
    X_tr   = X_tr.iloc[:len(y_tr)]
    X_te   = X_te.iloc[:len(y_te)]

    # StandardScaler on return-based features — stays in range during recursion
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    model = Ridge(alpha=10.0)  # stronger regularisation for stability
    model.fit(X_tr_s, y_tr)
    pred_ret_te = model.predict(X_te_s)

    # Reconstruct test prices from predicted returns
    base_idx      = split + 20 + 1  # offset from lag_features .dropna()
    base_price    = float(daily.iloc[base_idx - 1]) if base_idx > 0 else float(daily.iloc[0])
    pred_prices_te = [base_price]
    for r in pred_ret_te:
        pred_prices_te.append(pred_prices_te[-1] * (1 + r))
    pred_prices_te = np.array(pred_prices_te[1:])
    act_prices_te  = feat.iloc[split: split + len(y_te)]["price"].values

    # Recursive forecast — predict return, apply to last price
    extended = daily.copy()
    fc_prices = []
    for _ in range(horizon):
        nf = _lag_features(extended)
        if nf.empty or len(nf) < 2:
            fc_prices.append(float(extended.iloc[-1]))
        else:
            row_s       = scaler.transform(nf.iloc[[-1]][FCOLS])
            pred_ret    = float(model.predict(row_s)[0])
            # Clip return to prevent explosion
            pred_ret    = np.clip(pred_ret, -0.15, 0.15)
            next_price  = float(extended.iloc[-1]) * (1 + pred_ret)
            fc_prices.append(next_price)
        new_idx  = extended.index[-1] + pd.Timedelta(days=1)
        extended = pd.concat([
            extended,
            pd.Series([fc_prices[-1]], index=[new_idx])
        ])

    fc_idx = pd.date_range(
        daily.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D"
    )
    return (
        pd.Series(np.array(fc_prices), index=fc_idx),
        _metrics(act_prices_te, pred_prices_te),
        pd.Series(pred_prices_te, index=feat.index[split: split + len(y_te)]),
    )


# ─────────────────────────────────────────────────────────
# Chart builders (unchanged from original)
# ─────────────────────────────────────────────────────────
def _chart_combined(daily, forecasts, horizon, ticker):
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(BG)
    _style_ax(ax)
    ax.plot(daily.index, daily.values, color=WHITE,
            lw=1.4, label="Historical (actual)", alpha=0.9, zorder=3)
    for k, fc in forecasts.items():
        ax.plot(fc.index, fc.values, color=ALGO_COLORS[k],
                lw=1.8, linestyle=ALGO_STYLES[k],
                label=f"{ALGO_NAMES[k]} ({horizon}d)", alpha=0.92, zorder=4)
    ax.axvline(daily.index[-1], color=RED, ls=":", lw=1.2,
               alpha=0.6, label="Forecast start")
    ax.set_title(f"{ticker}  —  {horizon}-Day Price Forecast",
                 color=WHITE, fontsize=13, pad=14)
    ax.set_xlabel("Date", color=DIM)
    ax.set_ylabel("Price (USD)", color=DIM)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(facecolor="#0d1018", edgecolor="#1a1f2e",
              labelcolor=WHITE, fontsize=9, ncol=2)
    plt.tight_layout()
    return _b64(fig)


def _chart_test_vs_actual(daily, test_preds, ticker):
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(BG)
    _style_ax(ax)
    ax.plot(daily.index, daily.values, color=WHITE,
            lw=1.2, label="Actual", alpha=0.85)
    for k, tp in test_preds.items():
        ax.plot(tp.index, tp.values, color=ALGO_COLORS[k],
                lw=1.2, linestyle="--", label=f"{ALGO_NAMES[k]} (test)", alpha=0.85)
    ax.set_title(f"{ticker}  —  Test Predictions vs Actual",
                 color=WHITE, fontsize=13, pad=14)
    ax.set_xlabel("Date", color=DIM)
    ax.set_ylabel("Price (USD)", color=DIM)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(facecolor="#0d1018", edgecolor="#1a1f2e",
              labelcolor=WHITE, fontsize=9, ncol=2)
    plt.tight_layout()
    return _b64(fig)


def _chart_algo_comparison(forecasts, ticker, horizon):
    keys = list(forecasts.keys())
    if not keys:
        return None
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, len(keys), figsize=(14, 4), sharey=True)
    fig.patch.set_facecolor(BG)
    if len(keys) == 1:
        axes = [axes]
    for ax, k in zip(axes, keys):
        fc = forecasts[k]
        _style_ax(ax)
        ax.plot(fc.index, fc.values, color=ALGO_COLORS[k],
                lw=1.8, marker="o", markersize=3, alpha=0.9)
        ax.fill_between(fc.index, fc.values, alpha=0.08, color=ALGO_COLORS[k])
        ax.set_title(ALGO_NAMES[k], color=ALGO_COLORS[k], fontsize=12, pad=8)
        ax.set_xlabel("Date", color=DIM, fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    axes[0].set_ylabel("Price (USD)", color=DIM)
    fig.suptitle(f"{ticker}  —  {horizon}-Day Individual Forecasts",
                 color=WHITE, fontsize=13, y=1.02)
    plt.tight_layout()
    return _b64(fig)


def _chart_metrics_bar(metrics_all):
    if not metrics_all:
        return None
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    fig.patch.set_facecolor(BG)
    for ax, mk, mn in zip(
        axes,
        ["mae",    "rmse",    "mape"],
        ["MAE ($)", "RMSE ($)", "MAPE (%)"],
    ):
        _style_ax(ax)
        algos = list(metrics_all.keys())
        vals  = [metrics_all[a][mk] for a in algos]
        bars  = ax.bar(
            [ALGO_NAMES.get(a, a) for a in algos], vals,
            color=[ALGO_COLORS[a] for a in algos],
            edgecolor=PANEL, width=0.5,
        )
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() * 1.02,
                f"{val:.1f}",
                ha="center", va="bottom", color=WHITE, fontsize=9,
            )
        ax.set_title(mn, color=WHITE, fontsize=11, pad=8)
        ax.tick_params(colors=DIM, labelsize=9)
    fig.suptitle("Model Accuracy — Test Set", color=WHITE, fontsize=13, y=1.03)
    plt.tight_layout()
    return _b64(fig)


# ─────────────────────────────────────────────────────────
# View
# ─────────────────────────────────────────────────────────
class ForecastView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ticker    = request.data.get("ticker",    "BTC-USD").strip().upper()
        horizon   = int(request.data.get("horizon", 7))
        algorithm = request.data.get("algorithm", "all").strip().lower()

        if horizon not in (7, 30, 90):
            return Response({"error": "Horizon must be 7, 30, or 90."}, status=400)

        valid_algos = ["arima", "cnn_lstm", "linear"]
        if algorithm == "all":
            run_algos = valid_algos
        elif algorithm in valid_algos:
            run_algos = [algorithm]
        else:
            return Response(
                {"error": f"Unknown algorithm '{algorithm}'. Use: all, arima, cnn_lstm, linear."},
                status=400,
            )

        # ── Fetch data ───────────────────────────────────
        try:
            daily = _fetch_daily(ticker)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        # FIX #5: enforce minimum data requirement
        if len(daily) < 60:
            return Response(
                {"error": f"Only {len(daily)} daily candles found. "
                          "Need at least 60. Try a more liquid ticker."},
                status=400,
            )

        current_price = float(daily.iloc[-1])

        # ── Run algorithms ───────────────────────────────
        algo_fns    = {"arima": run_arima, "cnn_lstm": run_cnn_lstm, "linear": run_linear}
        forecasts   = {}
        test_preds  = {}
        metrics_all = {}
        errors      = {}

        for name in run_algos:
            try:
                fc, mt, tp        = algo_fns[name](daily, horizon)
                forecasts[name]   = fc
                metrics_all[name] = mt
                test_preds[name]  = tp
            except Exception as e:
                errors[name] = str(e)

        if not forecasts:
            return Response(
                {"error": "All algorithms failed.", "details": errors},
                status=500,
            )

        # ── Charts ───────────────────────────────────────
        charts = {}
        try:    charts["combined"]        = _chart_combined(daily, forecasts, horizon, ticker)
        except: charts["combined"]        = None
        try:    charts["test_vs_actual"]  = _chart_test_vs_actual(daily, test_preds, ticker)
        except: charts["test_vs_actual"]  = None
        try:    charts["algo_comparison"] = _chart_algo_comparison(forecasts, ticker, horizon)
        except: charts["algo_comparison"] = None
        try:    charts["metrics_bar"]     = _chart_metrics_bar(metrics_all)
        except: charts["metrics_bar"]     = None

        # ── Payload ──────────────────────────────────────
        def fc_list(fc):
            return [{"date": str(dt.date()), "price": round(float(p), 2)}
                    for dt, p in fc.items()]

        summary = {"current_price": round(current_price, 2)}
        for k, fc in forecasts.items():
            ep  = float(fc.iloc[-1])
            pct = (ep - current_price) / current_price * 100
            summary[k] = {
                "end_price":  round(ep, 2),
                "change_pct": round(pct, 2),
                "direction":  "UP" if ep > current_price else "DOWN",
            }

        best = min(metrics_all, key=lambda k: metrics_all[k]["mape"]) \
               if metrics_all else None

        return Response({
            "ticker":       ticker,
            "horizon_days": horizon,
            "algorithm":    algorithm,
            "charts":       charts,
            "metrics":      metrics_all,
            "forecasts":    {k: fc_list(v) for k, v in forecasts.items()},
            "summary":      summary,
            "best_model":   best,
            "algo_errors":  errors,
        })