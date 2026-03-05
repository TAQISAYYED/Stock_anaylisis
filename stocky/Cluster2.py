# # ─────────────────────────────────────────────────────────────
# # cluster2.py (FINAL PROFESSIONAL VERSION - LABEL FIXED)
# # PCA + KMeans Clustering for Portfolio Stocks
# # ─────────────────────────────────────────────────────────────

# import os
# import django
# import pandas as pd
# import yfinance as yf
# import numpy as np
# import matplotlib.pyplot as plt

# from sklearn.preprocessing import StandardScaler
# from sklearn.decomposition import PCA
# from sklearn.cluster import KMeans
# from sklearn.metrics import silhouette_score

# # ── Django Setup ─────────────────────────────────────────────
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stocky.settings")
# django.setup()

# from stocks.models import Stock
# from portfolio.models import Portfolio


# # ─────────────────────────────────────────────────────────────
# # 1️⃣ Backfill Missing Stock Data
# # ─────────────────────────────────────────────────────────────
# def backfill_all_stocks():
#     stocks = Stock.objects.filter(current_price__isnull=True)
#     print(f"\n🔄 Backfilling {stocks.count()} stocks...")

#     for stock in stocks:
#         try:
#             info = yf.Ticker(f"{stock.ticker.upper()}.NS").info

#             stock.company_name   = info.get("longName") or stock.ticker
#             stock.current_price  = info.get("currentPrice")
#             stock.day_high       = info.get("dayHigh")
#             stock.day_low        = info.get("dayLow")
#             stock.day_change_pct = info.get("regularMarketChangePercent")
#             stock.week_52_high   = info.get("fiftyTwoWeekHigh")
#             stock.week_52_low    = info.get("fiftyTwoWeekLow")
#             stock.pe_ratio       = info.get("trailingPE")
#             stock.market_cap     = info.get("marketCap")
#             stock.volume         = info.get("volume")
#             stock.dividend_yield = info.get("dividendYield")

#             stock.save()
#             print(f"✅ {stock.ticker} updated")

#         except Exception as e:
#             print(f"❌ {stock.ticker}: {e}")


# # ─────────────────────────────────────────────────────────────
# # 2️⃣ Fetch Portfolio Stocks + Feature Engineering
# # ─────────────────────────────────────────────────────────────
# def fetch_portfolio_stocks(portfolio_id: int) -> pd.DataFrame:

#     try:
#         portfolio = Portfolio.objects.get(id=portfolio_id)
#     except Portfolio.DoesNotExist:
#         print("❌ Portfolio not found")
#         return pd.DataFrame()

#     stocks = Stock.objects.filter(portfolio=portfolio)

#     if not stocks.exists():
#         print("❌ No stocks in this portfolio")
#         return pd.DataFrame()

#     data = []
#     for s in stocks:

#         if not all([s.current_price, s.week_52_high, s.week_52_low]):
#             continue

#         week_range = s.week_52_high - s.week_52_low
#         price_position = (
#             (s.current_price - s.week_52_low) / week_range
#             if week_range and week_range != 0 else 0
#         )

#         volatility = abs(s.day_change_pct) if s.day_change_pct else 0
#         log_market_cap = np.log1p(s.market_cap) if s.market_cap else 0

#         data.append({
#             "ticker": s.ticker,
#             "current_price": s.current_price,
#             "pe_ratio": s.pe_ratio or 0,
#             "log_market_cap": log_market_cap,
#             "volatility": volatility,
#             "price_position_52w": price_position,
#             "dividend_yield": s.dividend_yield or 0,
#         })

#     df = pd.DataFrame(data)

#     if df.empty:
#         print("❌ Not enough data")
#         return df

#     df.to_csv("portfolio_engineered_data.csv", index=False)
#     print("✅ Engineered data saved")

#     return df


# # ─────────────────────────────────────────────────────────────
# # 3️⃣ Apply PCA
# # ─────────────────────────────────────────────────────────────
# def apply_pca(df: pd.DataFrame, variance_threshold=0.90):

#     feature_cols = [
#         "current_price",
#         "pe_ratio",
#         "log_market_cap",
#         "volatility",
#         "price_position_52w",
#         "dividend_yield"
#     ]

#     scaler = StandardScaler()
#     scaled = scaler.fit_transform(df[feature_cols])

#     pca_full = PCA()
#     pca_full.fit(scaled)

#     cumulative_var = np.cumsum(pca_full.explained_variance_ratio_)
#     k = np.searchsorted(cumulative_var, variance_threshold) + 1

#     print(f"\n📊 Selected {k} PCA components")
#     print(f"📈 Variance retained: {cumulative_var[k-1]*100:.2f}%")

#     pca = PCA(n_components=k, random_state=42)
#     pca_data = pca.fit_transform(scaled)

#     explained = pca.explained_variance_ratio_

#     columns = [f"PC{i+1}" for i in range(k)]
#     df_pca = pd.DataFrame(pca_data, columns=columns)
#     df_pca["ticker"] = df["ticker"].values

#     df_pca.to_csv("portfolio_pca_components.csv", index=False)
#     print("✅ PCA components saved")

#     return df_pca, explained


# # ─────────────────────────────────────────────────────────────
# # 4️⃣ PCA + KMeans Clustering
# # ─────────────────────────────────────────────────────────────
# def cluster_with_pca(df_pca: pd.DataFrame, explained_variance, n_clusters=3):

#     if df_pca is None or df_pca.empty:
#         return

#     if "PC2" not in df_pca.columns:
#         print("❌ Need at least 2 PCA components for 2D plotting.")
#         return

#     features = df_pca.drop(columns=["ticker"])

#     n_clusters = min(n_clusters, len(df_pca) - 1)

#     kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
#     labels = kmeans.fit_predict(features)

#     df_pca["cluster"] = labels

#     silhouette = silhouette_score(features, labels)
#     print(f"\n📊 Silhouette Score: {silhouette:.3f}")

#     df_pca.to_csv("portfolio_pca_clusters.csv", index=False)
#     print("✅ Cluster results saved")

#     # ─── Plot ─────────────────────────────────
#     plt.figure(figsize=(10, 7))
#     plt.style.use("dark_background")

#     for cluster_id in range(n_clusters):
#         subset = df_pca[df_pca["cluster"] == cluster_id]

#         plt.scatter(
#             subset["PC1"],   # X from PC1
#             subset["PC2"],   # Y from PC2
#             s=180,
#            alpha=0.85,
#             label=f"Cluster {cluster_id}"
#         )

#         for _, row in subset.iterrows():
#             plt.annotate(
#                 row["ticker"],
#                 (row["PC1"], row["PC2"]),
#                 textcoords="offset points",
#                 xytext=(5, 5),
#                 fontsize=9
#             )

        

#     # ✅ ONLY CHANGE: CLEAR AXIS LABELING
#     plt.xlabel(
#         f"X-Axis: PC1 (Principal Component 1)\n"
#         f"Variance Explained: {explained_variance[0]*100:.2f}%",
#         fontsize=11
#     )

#     plt.ylabel(
#         f"Y-Axis: PC2 (Principal Component 2)\n"
#         f"Variance Explained: {explained_variance[1]*100:.2f}%",
#         fontsize=11
#     )

#     plt.title("Portfolio Clustering (X = PC1, Y = PC2)", fontsize=13)

#     plt.legend()
#     plt.grid(alpha=0.3)
#     plt.tight_layout()

#     plt.savefig("pca_cluster_plot.png", dpi=150)
#     print("✅ Plot saved")

#     plt.show()

#     print("\n📊 Cluster Summary:")
#     for cluster_id in range(n_clusters):
#         tickers = df_pca[df_pca["cluster"] == cluster_id]["ticker"].tolist()
#         print(f"Cluster {cluster_id}: {', '.join(tickers)}")


# # ─────────────────────────────────────────────────────────────
# # 5️⃣ MAIN EXECUTION
# # ─────────────────────────────────────────────────────────────
# if __name__ == "__main__":

#     print("\n🚀 PROFESSIONAL PCA + KMeans Portfolio Clustering")

#     backfill_all_stocks()

#     portfolio_id = int(input("\nEnter Portfolio ID: "))
#     df = fetch_portfolio_stocks(portfolio_id)

#     if not df.empty:
#         try:
#             n = int(input("Enter number of clusters (default 3): ") or 3)
#         except ValueError:
#             n = 3

#         df_pca, explained = apply_pca(df)
#         cluster_with_pca(df_pca, explained, n_clusters=n)






import os
import django
import json
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stocky.settings")
django.setup()

from stocks.models import Stock
from portfolio.models import Portfolio


# ── STEP 0: Backfill missing yfinance data ────────────────────────────────────
def backfill_all_stocks():
    """Fetch yfinance data for all stocks with empty prices and save to DB."""
    stocks = Stock.objects.filter(current_price__isnull=True)
    print(f"Backfilling {stocks.count()} stocks...")

    for stock in stocks:
        try:
            info = yf.Ticker(f"{stock.ticker.upper()}.NS").info

            price    = info.get("currentPrice") or info.get("regularMarketPrice")
            day_high = info.get("dayHigh") or info.get("regularMarketDayHigh")
            day_low  = info.get("dayLow")  or info.get("regularMarketDayLow")
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

            print(f"  [OK] {stock.ticker} — {stock.current_price}")
        except Exception as e:
            print(f"  [FAIL] {stock.ticker} — {e}")


# ── STEP 1: Load portfolio from DB → CSV ─────────────────────────────────────
def fetch_portfolio_stocks(portfolio_id: int) -> pd.DataFrame:
    """Fetch all stocks from portfolio, print JSON, save CSV, return DataFrame."""
    try:
        portfolio = Portfolio.objects.get(id=portfolio_id)
    except Portfolio.DoesNotExist:
        print(f"Portfolio with id={portfolio_id} does not exist.")
        return pd.DataFrame()

    stocks = Stock.objects.filter(portfolio=portfolio)
    if not stocks.exists():
        print(f"No stocks found in portfolio '{portfolio.name}'.")
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

    print(f"\nPortfolio : {portfolio.name}  (id={portfolio_id})")
    print(f"Stocks    : {len(stocks_data)}\n")

    df = pd.DataFrame(stocks_data)
    csv_filename = f"{portfolio.name.replace(' ', '_')}_stocks.csv"
    df.to_csv(csv_filename, index=False)
    print(f"CSV saved : {csv_filename}")
    return df


# ── STEP 2: PCA + Stage-1 KMeans (3 clusters on whole portfolio) ──────────────
def stage1_pca_kmeans(df: pd.DataFrame, n_clusters: int = 3):
    """
    Run PCA on 6 features, then KMeans(k=3) on the 2 principal components.
    Returns df_clean with 'pca_1', 'pca_2', 'cluster' columns added.
    Also plots the PCA scatter so user can visually see the 3 clusters.
    """
    FEATURE_COLS = [
        "current_price", "pe_ratio", "market_cap",
        "day_change_pct", "week_52_high", "week_52_low",
    ]

    # Need at least current_price and pe_ratio
    df_clean = df.dropna(subset=["current_price", "pe_ratio"]).copy()
    if df_clean.empty:
        print("Not enough data (need current_price + pe_ratio for every stock).")
        return pd.DataFrame()

    # Fill remaining nulls with column median
    for col in FEATURE_COLS:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(df_clean[col].median())

    n_clusters = min(n_clusters, len(df_clean))

    # Scale → PCA(2) → KMeans
    scaler  = StandardScaler()
    scaled  = scaler.fit_transform(df_clean[FEATURE_COLS])

    pca     = PCA(n_components=2)
    pca_result = pca.fit_transform(scaled)
    df_clean["pca_1"] = pca_result[:, 0]
    df_clean["pca_2"] = pca_result[:, 1]

    kmeans  = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_clean["cluster"] = kmeans.fit_predict(pca_result)

    var_explained = pca.explained_variance_ratio_ * 100

    # ── Plot Stage-1 PCA scatter ──────────────────────────────────────────────
    COLORS        = ["#f0c040", "#00d48c", "#ff4d6d", "#60a5fa", "#c084fc"]
    CLUSTER_NAMES = {0: "Cluster 0  (Value)", 1: "Cluster 1  (Growth)", 2: "Cluster 2  (Blue Chip)"}

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 7))
    fig.patch.set_facecolor("#080a10")
    ax.set_facecolor("#111520")

    for cid in range(n_clusters):
        mask   = df_clean["cluster"] == cid
        subset = df_clean[mask]
        ax.scatter(
            subset["pca_1"], subset["pca_2"],
            c=COLORS[cid % len(COLORS)],
            label=CLUSTER_NAMES.get(cid, f"Cluster {cid}"),
            s=140, alpha=0.88,
            edgecolors="#1a1f2e", linewidths=1,
        )
        for _, row in subset.iterrows():
            ax.annotate(
                row["ticker"],
                (row["pca_1"], row["pca_2"]),
                textcoords="offset points", xytext=(8, 4),
                fontsize=8, color="#e2e8f8", alpha=0.9,
            )

    ax.set_xlabel(f"PC 1  ({var_explained[0]:.1f}% variance)", color="#6b7494", fontsize=11)
    ax.set_ylabel(f"PC 2  ({var_explained[1]:.1f}% variance)", color="#6b7494", fontsize=11)
    ax.set_title("Stage 1 — PCA KMeans  (All Stocks)", color="#e2e8f8", fontsize=13, pad=14)
    ax.tick_params(colors="#6b7494")
    for spine in ax.spines.values():
        spine.set_color("#1a1f2e")
    ax.legend(facecolor="#0d1018", edgecolor="#1a1f2e", labelcolor="#e2e8f8", fontsize=9)
    ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    plt.savefig("stage1_pca_clusters.png", dpi=150, bbox_inches="tight", facecolor="#080a10")
    print("\nStage-1 plot saved : stage1_pca_clusters.png")
    plt.show()

    # ── Print cluster membership ───────────────────────────────────────────────
    print("\nStage-1 Cluster Summary:")
    print(f"  (PCA explained variance: PC1={var_explained[0]:.1f}%  PC2={var_explained[1]:.1f}%)\n")
    for cid in range(n_clusters):
        subset  = df_clean[df_clean["cluster"] == cid]
        name    = CLUSTER_NAMES.get(cid, f"Cluster {cid}")
        tickers = ", ".join(subset["ticker"].tolist())
        avg_pe  = subset["pe_ratio"].mean()
        avg_px  = subset["current_price"].mean()
        print(f"  {name}")
        print(f"    Tickers       : {tickers}")
        print(f"    Avg PE        : {avg_pe:.1f}")
        print(f"    Avg Price     : {avg_px:.1f}")
        print()

    return df_clean


# ── STEP 3: Stage-2 KMeans on a chosen cluster ───────────────────────────────
def stage2_subcluster(df_stage1: pd.DataFrame, chosen_cluster: int, n_sub: int = 3):
    """
    Take only the stocks from `chosen_cluster`.
    Compute:
        discount_pct = (52W_High - Current_Price) / (52W_High - 52W_Low) * 100
                       (how far the stock is from its 52W high — 0% = at high, 100% = at low)
    Then KMeans(k=n_sub) on:
        X axis : discount_pct
        Y axis : pe_ratio
    Plot a single annotated scatter with cluster centroids marked.
    """
    subset = df_stage1[df_stage1["cluster"] == chosen_cluster].copy()

    if subset.empty:
        print(f"Cluster {chosen_cluster} has no stocks.")
        return

    # Need all three price fields
    subset = subset.dropna(subset=["week_52_high", "week_52_low", "current_price", "pe_ratio"])
    if subset.empty:
        print(f"Cluster {chosen_cluster} has no stocks with complete price + PE data.")
        return

    # Guard: avoid division by zero when 52W high == 52W low
    price_range = subset["week_52_high"] - subset["week_52_low"]
    subset = subset[price_range > 0].copy()
    price_range = subset["week_52_high"] - subset["week_52_low"]

    # Discount from 52W high  (0 = stock is AT 52W high; 100 = stock is AT 52W low)
    subset["discount_pct"] = (
        (subset["week_52_high"] - subset["current_price"]) / subset["week_52_high"] * 100
    ).round(2)

    if len(subset) < 2:
        print(f"Cluster {chosen_cluster} has only {len(subset)} usable stock(s). Need at least 2.")
        return

    n_sub = min(n_sub, len(subset))

    # Scale and cluster
    feats  = subset[["discount_pct", "pe_ratio"]].values
    scaler = StandardScaler()
    scaled = scaler.fit_transform(feats)

    km     = KMeans(n_clusters=n_sub, random_state=42, n_init=10)
    subset["sub_cluster"] = km.fit_predict(scaled)

    # Centroids back in original space
    centroids_scaled = km.cluster_centers_
    centroids_orig   = scaler.inverse_transform(centroids_scaled)

    # ── Interpret sub-clusters ────────────────────────────────────────────────
    # Label each sub-cluster by its centroid's discount and PE
    sub_labels = {}
    for i, (disc, pe) in enumerate(centroids_orig):
        if disc < 15:
            valuation = "Near 52W High"
        elif disc < 40:
            valuation = "Mid Range"
        else:
            valuation = "Deep Discount"

        if pe < 15:
            pe_label = "Low PE"
        elif pe < 30:
            pe_label = "Mid PE"
        else:
            pe_label = "High PE"

        sub_labels[i] = f"Sub-{i}  ({valuation} / {pe_label})"

    # ── Plot ──────────────────────────────────────────────────────────────────
    COLORS = ["#f0c040", "#00d48c", "#ff4d6d", "#60a5fa", "#c084fc"]
    CLUSTER_NAMES = {0: "Cluster 0  (Value)", 1: "Cluster 1  (Growth)", 2: "Cluster 2  (Blue Chip)"}

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("#080a10")
    ax.set_facecolor("#111520")

    for scid in range(n_sub):
        mask2   = subset["sub_cluster"] == scid
        sub_sub = subset[mask2]
        ax.scatter(
            sub_sub["discount_pct"], sub_sub["pe_ratio"],
            c=COLORS[scid % len(COLORS)],
            label=sub_labels[scid],
            s=160, alpha=0.88,
            edgecolors="#1a1f2e", linewidths=1.2,
            zorder=3,
        )
        # Ticker labels
        for _, row in sub_sub.iterrows():
            ax.annotate(
                row["ticker"],
                (row["discount_pct"], row["pe_ratio"]),
                textcoords="offset points", xytext=(9, 5),
                fontsize=9, color="#e2e8f8", alpha=0.92,
            )

    # Plot centroids as X markers
    for i, (disc, pe) in enumerate(centroids_orig):
        ax.scatter(
            disc, pe,
            marker="X", s=280,
            c=COLORS[i % len(COLORS)],
            edgecolors="white", linewidths=1.5,
            zorder=5,
        )
        ax.annotate(
            f"centroid {i}",
            (disc, pe),
            textcoords="offset points", xytext=(-10, -16),
            fontsize=7.5, color="white", alpha=0.7,
        )

    # Reference lines
    ax.axvline(x=20,  color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)
    ax.axvline(x=40,  color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(y=15,  color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(y=30,  color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)

    # Zone annotations
    ax.text(2,  ax.get_ylim()[1] * 0.97 if ax.get_ylim()[1] else 60,
            "Near High", color="#3a4060", fontsize=8, va="top")
    ax.text(22, ax.get_ylim()[1] * 0.97 if ax.get_ylim()[1] else 60,
            "Mid Range", color="#3a4060", fontsize=8, va="top")
    ax.text(42, ax.get_ylim()[1] * 0.97 if ax.get_ylim()[1] else 60,
            "Deep Discount", color="#3a4060", fontsize=8, va="top")

    parent_name = CLUSTER_NAMES.get(chosen_cluster, f"Cluster {chosen_cluster}")
    ax.set_xlabel(
        "Discount from 52W High  (%)\n"
        "[ 0% = at 52W High    100% = at 52W Low ]",
        color="#6b7494", fontsize=11,
    )
    ax.set_ylabel("PE Ratio", color="#6b7494", fontsize=11)
    ax.set_title(
        f"Stage 2 — Sub-Cluster of  {parent_name}\n"
        f"PE Ratio vs Discount from 52-Week High",
        color="#e2e8f8", fontsize=13, pad=14,
    )
    ax.tick_params(colors="#6b7494")
    for spine in ax.spines.values():
        spine.set_color("#1a1f2e")
    ax.legend(facecolor="#0d1018", edgecolor="#1a1f2e", labelcolor="#e2e8f8", fontsize=9)
    ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    out_file = f"stage2_cluster{chosen_cluster}_subcluster.png"
    plt.savefig(out_file, dpi=150, bbox_inches="tight", facecolor="#080a10")
    print(f"\nStage-2 plot saved : {out_file}")
    plt.show()

    # ── Print sub-cluster summary ─────────────────────────────────────────────
    print(f"\nStage-2 Sub-Cluster Summary  (parent: {parent_name}):")
    print(f"  Features: X = Discount from 52W High (%)   Y = PE Ratio\n")
    for scid in range(n_sub):
        sub_sub = subset[subset["sub_cluster"] == scid]
        tickers = ", ".join(sub_sub["ticker"].tolist())
        avg_disc = sub_sub["discount_pct"].mean()
        avg_pe   = sub_sub["pe_ratio"].mean()
        avg_px   = sub_sub["current_price"].mean()
        print(f"  {sub_labels[scid]}")
        print(f"    Tickers       : {tickers}")
        print(f"    Avg Discount  : {avg_disc:.1f}% below 52W High")
        print(f"    Avg PE        : {avg_pe:.1f}")
        print(f"    Avg Price     : {avg_px:.1f}")
        print()

    # Save sub-cluster CSV
    out_cols = ["ticker", "company_name", "current_price",
                "week_52_high", "week_52_low", "discount_pct",
                "pe_ratio", "market_cap", "sub_cluster"]
    out_csv  = f"stage2_cluster{chosen_cluster}_substocks.csv"
    subset[out_cols].to_csv(out_csv, index=False)
    print(f"Sub-cluster CSV saved : {out_csv}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # Step 0: backfill
    backfill_all_stocks()

    # Step 1: load portfolio
    portfolio_id = int(input("\nEnter portfolio ID: "))
    df = fetch_portfolio_stocks(portfolio_id)

    if df.empty:
        print("No data. Exiting.")
        exit()

    # Step 2: Stage-1 PCA KMeans
    print("\n--- Stage 1: PCA KMeans on full portfolio ---")
    df_stage1 = stage1_pca_kmeans(df, n_clusters=3)

    if df_stage1.empty:
        print("Stage 1 failed. Exiting.")
        exit()

    # Step 3: Ask which cluster to drill into
    print("\n--- Stage 2: Sub-cluster drill-down ---")
    print("Available clusters: 0, 1, 2")
    try:
        chosen = int(input("Which cluster do you want to sub-cluster? (0 / 1 / 2): "))
        if chosen not in [0, 1, 2]:
            raise ValueError
    except ValueError:
        print("Invalid input. Defaulting to cluster 0.")
        chosen = 0

    try:
        n_sub = int(input("Number of sub-clusters (default 3): ") or 3)
    except ValueError:
        n_sub = 3

    stage2_subcluster(df_stage1, chosen_cluster=chosen, n_sub=n_sub)