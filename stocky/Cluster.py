import os
import django
import json
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stocky.settings")
django.setup()

from stocks.models import Stock
from portfolio.models import Portfolio


def backfill_all_stocks():
    """Fetch yfinance data for all stocks with empty prices and save to DB."""
    stocks = Stock.objects.filter(current_price__isnull=True)
    print(f"Backfilling {stocks.count()} stocks...")

    for stock in stocks:
        try:
            info = yf.Ticker(f"{stock.ticker.upper()}.NS").info

            price    = info.get("currentPrice") or info.get("regularMarketPrice")
            day_high = info.get("dayHigh") or info.get("regularMarketDayHigh")
            day_low  = info.get("dayLow") or info.get("regularMarketDayLow")
            high_52w = info.get("fiftyTwoWeekHigh")
            low_52w  = info.get("fiftyTwoWeekLow")
            chg_pct  = info.get("regularMarketChangePercent")
            pe       = info.get("trailingPE")
            dy       = info.get("dividendYield")

            stock.company_name   = info.get("longName") or info.get("shortName", stock.ticker)
            stock.current_price  = round(price, 2)    if price    else None
            stock.day_high       = round(day_high, 2) if day_high else None
            stock.day_low        = round(day_low, 2)  if day_low  else None
            stock.day_change_pct = round(chg_pct, 2)  if chg_pct  else None
            stock.week_52_high   = round(high_52w, 2) if high_52w else None
            stock.week_52_low    = round(low_52w, 2)  if low_52w  else None
            stock.pe_ratio       = round(pe, 2)        if pe       else None
            stock.market_cap     = info.get("marketCap")
            stock.volume         = info.get("regularMarketVolume") or info.get("volume")
            stock.dividend_yield = round(dy * 100, 2)  if dy       else None
            stock.save()

            print(f"✅ {stock.ticker} — ₹{stock.current_price}")
        except Exception as e:
            print(f"❌ {stock.ticker} — {e}")


def fetch_portfolio_stocks(portfolio_id: int) -> pd.DataFrame:
    """Fetch all stocks from portfolio, print JSON, save CSV, return DataFrame."""
    try:
        portfolio = Portfolio.objects.get(id=portfolio_id)
    except Portfolio.DoesNotExist:
        print(f"❌ Portfolio with id={portfolio_id} does not exist.")
        return pd.DataFrame()

    stocks = Stock.objects.filter(portfolio=portfolio)
    if not stocks.exists():
        print(f"⚠️  No stocks found in portfolio '{portfolio.name}'.")
        return pd.DataFrame()

    stocks_data = []
    for s in stocks:
        stocks_data.append({
            "id":             s.id,
            "ticker":         s.ticker,
            "company_name":   s.company_name,
            "current_price":  s.current_price,
            "day_high":       s.day_high,
            "day_low":        s.day_low,
            "day_change_pct": s.day_change_pct,
            "week_52_high":   s.week_52_high,
            "week_52_low":    s.week_52_low,
            "pe_ratio":       s.pe_ratio,
            "market_cap":     s.market_cap,
            "volume":         s.volume,
            "dividend_yield": s.dividend_yield,
            "last_updated":   str(s.last_updated) if s.last_updated else None,
            "added_at":       str(s.added_at),
        })

    print(f"\n📊 Portfolio: {portfolio.name} (id={portfolio_id})")
    print(f"📈 Total stocks: {len(stocks_data)}\n")
    print(json.dumps(stocks_data, indent=2))

    df = pd.DataFrame(stocks_data)
    csv_filename = f"{portfolio.name.replace(' ', '_')}_stocks.csv"
    df.to_csv(csv_filename, index=False)
    print(f"\n✅ CSV saved as: {csv_filename}")

    return df


def plot_clusters(df: pd.DataFrame, n_clusters: int = 3) -> None:
    """
    Perform KMeans clustering on stocks using PE Ratio vs Current Price
    and Market Cap vs Day Change % and plot both scatter plots.
    """
    if df.empty:
        print("❌ No data to plot.")
        return

    # ── Features for clustering ───────────────────────────────────────────────
    feature_cols = ["current_price", "pe_ratio", "market_cap", "day_change_pct",
                    "week_52_high", "week_52_low"]

    # Drop rows where ALL feature cols are null
    df_clean = df.dropna(subset=["current_price", "pe_ratio"]).copy()

    if df_clean.empty:
        print("❌ Not enough data with current_price and pe_ratio to cluster.")
        return

    # Fill remaining nulls with column median
    for col in feature_cols:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(df_clean[col].median())

    # Cap clusters to available data points
    n_clusters = min(n_clusters, len(df_clean))

    # ── Scale features ────────────────────────────────────────────────────────
    scaler = StandardScaler()
    scaled = scaler.fit_transform(df_clean[feature_cols].fillna(0))

    # ── KMeans ────────────────────────────────────────────────────────────────
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_clean["cluster"] = kmeans.fit_predict(scaled)

    # Cluster label mapping
    cluster_labels = {
        0: "Value Stocks",
        1: "Growth Stocks",
        2: "Blue Chip",
        3: "Speculative",
        4: "Dividend Stocks",
    }

    # ── Color palette ─────────────────────────────────────────────────────────
    colors = ["#f0c040", "#00d48c", "#ff4d6d", "#60a5fa", "#c084fc"]

    # ── Dark theme style ──────────────────────────────────────────────────────
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#080a10")
    fig.suptitle(
        "Stock Portfolio Cluster Analysis",
        fontsize=16,
        fontweight="bold",
        color="#e2e8f8",
        y=1.01,
    )

    # ── Plot 1: PE Ratio vs Current Price ─────────────────────────────────────
    ax1 = axes[0]
    ax1.set_facecolor("#111520")

    for cluster_id in range(n_clusters):
        mask = df_clean["cluster"] == cluster_id
        subset = df_clean[mask]
        label = cluster_labels.get(cluster_id, f"Cluster {cluster_id}")
        ax1.scatter(
            subset["pe_ratio"],
            subset["current_price"],
            c=colors[cluster_id % len(colors)],
            label=label,
            s=120,
            alpha=0.85,
            edgecolors="#1a1f2e",
            linewidths=1,
        )
        # Annotate each point with ticker
        for _, row in subset.iterrows():
            ax1.annotate(
                row["ticker"],
                (row["pe_ratio"], row["current_price"]),
                textcoords="offset points",
                xytext=(8, 4),
                fontsize=8,
                color="#e2e8f8",
                alpha=0.9,
            )

    ax1.set_xlabel("PE Ratio", color="#6b7494", fontsize=11)
    ax1.set_ylabel("Current Price (₹)", color="#6b7494", fontsize=11)
    ax1.set_title("PE Ratio vs Current Price", color="#e2e8f8", fontsize=12, pad=12)
    ax1.tick_params(colors="#6b7494")
    ax1.spines["bottom"].set_color("#1a1f2e")
    ax1.spines["left"].set_color("#1a1f2e")
    ax1.spines["top"].set_color("#1a1f2e")
    ax1.spines["right"].set_color("#1a1f2e")
    ax1.legend(
        facecolor="#0d1018",
        edgecolor="#1a1f2e",
        labelcolor="#e2e8f8",
        fontsize=9,
    )
    ax1.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)

    # ── Plot 2: 52W High vs 52W Low ───────────────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor("#111520")

    df_52 = df_clean.dropna(subset=["week_52_high", "week_52_low"])

    if not df_52.empty:
        for cluster_id in range(n_clusters):
            mask = df_52["cluster"] == cluster_id
            subset = df_52[mask]
            label = cluster_labels.get(cluster_id, f"Cluster {cluster_id}")
            ax2.scatter(
                subset["week_52_low"],
                subset["week_52_high"],
                c=colors[cluster_id % len(colors)],
                label=label,
                s=120,
                alpha=0.85,
                edgecolors="#1a1f2e",
                linewidths=1,
            )
            for _, row in subset.iterrows():
                ax2.annotate(
                    row["ticker"],
                    (row["week_52_low"], row["week_52_high"]),
                    textcoords="offset points",
                    xytext=(8, 4),
                    fontsize=8,
                    color="#e2e8f8",
                    alpha=0.9,
                )

        # Diagonal reference line (52W Low == 52W High)
        all_vals = pd.concat([df_52["week_52_low"], df_52["week_52_high"]])
        mn, mx = all_vals.min(), all_vals.max()
        ax2.plot(
            [mn, mx], [mn, mx],
            color="#3a4060",
            linestyle="--",
            linewidth=1,
            alpha=0.6,
            label="Equal line",
        )
    else:
        ax2.text(
            0.5, 0.5, "No 52W data available",
            transform=ax2.transAxes,
            ha="center", va="center",
            color="#6b7494", fontsize=12,
        )

    ax2.set_xlabel("52W Low (₹)", color="#6b7494", fontsize=11)
    ax2.set_ylabel("52W High (₹)", color="#6b7494", fontsize=11)
    ax2.set_title("52-Week High vs Low", color="#e2e8f8", fontsize=12, pad=12)
    ax2.tick_params(colors="#6b7494")
    ax2.spines["bottom"].set_color("#1a1f2e")
    ax2.spines["left"].set_color("#1a1f2e")
    ax2.spines["top"].set_color("#1a1f2e")
    ax2.spines["right"].set_color("#1a1f2e")
    ax2.legend(
        facecolor="#0d1018",
        edgecolor="#1a1f2e",
        labelcolor="#e2e8f8",
        fontsize=9,
    )
    ax2.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)

    plt.tight_layout()

    # Save and show
    plot_filename = "portfolio_clusters.png"
    plt.savefig(plot_filename, dpi=150, bbox_inches="tight", facecolor="#080a10")
    print(f"\n✅ Cluster plot saved as: {plot_filename}")
    plt.show()

    # Print cluster summary
    print("\n📊 Cluster Summary:")
    for cluster_id in range(n_clusters):
        subset = df_clean[df_clean["cluster"] == cluster_id]
        label  = cluster_labels.get(cluster_id, f"Cluster {cluster_id}")
        tickers = ", ".join(subset["ticker"].tolist())
        print(f"  {label}: {tickers}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    backfill_all_stocks()

    portfolio_id = int(input("\nEnter portfolio ID: "))
    df = fetch_portfolio_stocks(portfolio_id)

    if not df.empty:
        try:
            n = int(input("Enter number of clusters (default 3): ") or 3)
        except ValueError:
            n = 3
        plot_clusters(df, n_clusters=n)