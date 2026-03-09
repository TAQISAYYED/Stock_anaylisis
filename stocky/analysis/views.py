from django.shortcuts import render

# Create your views here.
import numpy as np
import pandas as pd
import io
import base64
import matplotlib
matplotlib.use("Agg")          
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from stocks.models import Stock
from portfolio.models import Portfolio


# ── helpers ───────────────────────────────────────────────────────────────────
COLORS        = ["#f0c040", "#00d48c", "#ff4d6d", "#60a5fa", "#c084fc"]
CLUSTER_NAMES = {
    0: "Cluster 0  (Value)",
    1: "Cluster 1  (Growth)",
    2: "Cluster 2  (Blue Chip)",
}
BG    = "#080a10"
PANEL = "#111520"
DIM   = "#6b7494"
WHITE = "#e2e8f8"

def _fig_to_base64(fig):
    """Convert a matplotlib figure to a base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130,
                bbox_inches="tight", facecolor=BG)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{img_b64}"


def _sub_label(disc, pe):
    if disc < 15:
        val = "Near 52W High"
    elif disc < 40:
        val = "Mid Range"
    else:
        val = "Deep Discount"
    if pe < 15:
        pe_lbl = "Low PE"
    elif pe < 30:
        pe_lbl = "Mid PE"
    else:
        pe_lbl = "High PE"
    return f"{val} / {pe_lbl}"



class PortfolioListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolios = Portfolio.objects.filter(user=request.user).values("id", "name")
        return Response(list(portfolios))



class Stage1ClusterView(APIView):
    """
    POST /api/analysis/stage1/
    Body: { portfolio_id, n_clusters }
    Returns:
        - chart_base64   : PCA scatter plot as base64 PNG
        - clusters       : list of { ticker, pca_1, pca_2, cluster, ... }
        - variance       : [pc1_var, pc2_var]
        - cluster_summary: per-cluster stats
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        portfolio_id = request.data.get("portfolio_id")
        n_clusters   = int(request.data.get("n_clusters", 3))

        
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        except Portfolio.DoesNotExist:
            return Response({"error": "Portfolio not found."}, status=404)

        qs = Stock.objects.filter(portfolio=portfolio)
        if not qs.exists():
            return Response({"error": "No stocks in this portfolio."}, status=400)

        rows = []
        for s in qs:
            rows.append({
                "ticker":        s.ticker,
                "company_name":  s.company_name or s.ticker,
                "current_price": s.current_price,
                "pe_ratio":      s.pe_ratio,
                "market_cap":    s.market_cap,
                "day_change_pct":s.day_change_pct,
                "week_52_high":  s.week_52_high,
                "week_52_low":   s.week_52_low,
            })

        df = pd.DataFrame(rows)

        # ── feature prep ──────────────────────────────────────────────────────
        FEATURE_COLS = [
            "current_price", "pe_ratio", "market_cap",
            "day_change_pct", "week_52_high", "week_52_low",
        ]
        df_clean = df.dropna(subset=["current_price", "pe_ratio"]).copy()
        if df_clean.empty:
            return Response(
                {"error": "Not enough data — every stock needs current_price and pe_ratio."},
                status=400,
            )

        for col in FEATURE_COLS:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")
            df_clean[col] = df_clean[col].fillna(df_clean[col].median())

        n_clusters = min(n_clusters, len(df_clean))

        
        scaler     = StandardScaler()
        scaled     = scaler.fit_transform(df_clean[FEATURE_COLS])
        pca        = PCA(n_components=2)
        pca_result = pca.fit_transform(scaled)
        var_exp    = (pca.explained_variance_ratio_ * 100).tolist()

        df_clean["pca_1"] = pca_result[:, 0]
        df_clean["pca_2"] = pca_result[:, 1]

        # ── KMeans ────────────────────────────────────────────────────────────
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df_clean["cluster"] = kmeans.fit_predict(pca_result)

        # ── Chart ─────────────────────────────────────────────────────────────
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(PANEL)

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
                    fontsize=8, color=WHITE, alpha=0.9,
                )

        ax.set_xlabel(f"PC1  ({var_exp[0]:.1f}% variance)", color=DIM, fontsize=11)
        ax.set_ylabel(f"PC2  ({var_exp[1]:.1f}% variance)", color=DIM, fontsize=11)
        ax.set_title("Stage 1 — PCA KMeans  (All Stocks)",
                     color=WHITE, fontsize=13, pad=14)
        ax.tick_params(colors=DIM)
        for sp in ax.spines.values():
            sp.set_color("#1a1f2e")
        ax.legend(facecolor="#0d1018", edgecolor="#1a1f2e",
                  labelcolor=WHITE, fontsize=9)
        ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)
        plt.tight_layout()
        chart_b64 = _fig_to_base64(fig)

        # ── cluster summary ───────────────────────────────────────────────────
        summary = []
        for cid in range(n_clusters):
            sub = df_clean[df_clean["cluster"] == cid]
            summary.append({
                "cluster":    cid,
                "label":      CLUSTER_NAMES.get(cid, f"Cluster {cid}"),
                "tickers":    sub["ticker"].tolist(),
                "count":      len(sub),
                "avg_pe":     round(float(sub["pe_ratio"].mean()), 2),
                "avg_price":  round(float(sub["current_price"].mean()), 2),
            })

        # ── stocks payload ────────────────────────────────────────────────────
        stocks_out = df_clean[[
            "ticker", "company_name", "pca_1", "pca_2",
            "cluster", "current_price", "pe_ratio",
        ]].copy()
        stocks_out["pca_1"]   = stocks_out["pca_1"].round(4)
        stocks_out["pca_2"]   = stocks_out["pca_2"].round(4)
        stocks_out["cluster"] = stocks_out["cluster"].astype(int)

        return Response({
            "chart":           chart_b64,
            "variance":        [round(v, 2) for v in var_exp],
            "cluster_summary": summary,
            "stocks":          stocks_out.to_dict(orient="records"),
            "n_clusters":      n_clusters,
        })


# ── View 3: Stage-2  Sub-cluster on chosen cluster ───────────────────────────
class Stage2SubClusterView(APIView):
    """
    POST /api/analysis/stage2/
    Body: { portfolio_id, chosen_cluster, n_sub }
    Requires stage-1 to have been run first (re-runs stage-1 internally
    so we do not need to store session state).
    Returns:
        - chart_base64  : sub-cluster scatter as base64 PNG
        - stocks        : list of sub-clustered stocks
        - centroids     : list of centroid coords
        - sub_summary   : per sub-cluster stats
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        portfolio_id    = request.data.get("portfolio_id")
        chosen_cluster  = int(request.data.get("chosen_cluster", 0))
        n_sub           = int(request.data.get("n_sub", 3))
        n_stage1        = int(request.data.get("n_clusters", 3))

        # ── re-run stage 1 to get cluster assignments ─────────────────────────
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        except Portfolio.DoesNotExist:
            return Response({"error": "Portfolio not found."}, status=404)

        qs = Stock.objects.filter(portfolio=portfolio)
        rows = []
        for s in qs:
            rows.append({
                "ticker":        s.ticker,
                "company_name":  s.company_name or s.ticker,
                "current_price": s.current_price,
                "pe_ratio":      s.pe_ratio,
                "market_cap":    s.market_cap,
                "day_change_pct":s.day_change_pct,
                "week_52_high":  s.week_52_high,
                "week_52_low":   s.week_52_low,
            })

        df = pd.DataFrame(rows)
        FEATURE_COLS = [
            "current_price", "pe_ratio", "market_cap",
            "day_change_pct", "week_52_high", "week_52_low",
        ]
        df_clean = df.dropna(subset=["current_price", "pe_ratio"]).copy()
        if df_clean.empty:
            return Response({"error": "Not enough data."}, status=400)

        for col in FEATURE_COLS:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")
            df_clean[col] = df_clean[col].fillna(df_clean[col].median())

        n_stage1 = min(n_stage1, len(df_clean))
        scaler   = StandardScaler()
        scaled   = scaler.fit_transform(df_clean[FEATURE_COLS])
        pca      = PCA(n_components=2)
        pca_res  = pca.fit_transform(scaled)
        df_clean["pca_1"]   = pca_res[:, 0]
        df_clean["pca_2"]   = pca_res[:, 1]
        kmeans1  = KMeans(n_clusters=n_stage1, random_state=42, n_init=10)
        df_clean["cluster"] = kmeans1.fit_predict(pca_res)

        # ── isolate chosen cluster ────────────────────────────────────────────
        subset = df_clean[df_clean["cluster"] == chosen_cluster].copy()
        if subset.empty:
            return Response(
                {"error": f"Cluster {chosen_cluster} has no stocks."}, status=400)

        subset = subset.dropna(
            subset=["week_52_high", "week_52_low", "current_price", "pe_ratio"]
        )
        price_range = subset["week_52_high"] - subset["week_52_low"]
        subset = subset[price_range > 0].copy()
        price_range = subset["week_52_high"] - subset["week_52_low"]

        if len(subset) < 2:
            return Response(
                {"error": f"Cluster {chosen_cluster} needs at least 2 stocks with full data."},
                status=400,
            )

        # real market discount formula
        subset["discount_pct"] = (
            (subset["week_52_high"] - subset["current_price"])
            / subset["week_52_high"] * 100
        ).round(2)

        n_sub = min(n_sub, len(subset))

        feats2  = subset[["discount_pct", "pe_ratio"]].values
        scaler2 = StandardScaler()
        scaled2 = scaler2.fit_transform(feats2)
        km2     = KMeans(n_clusters=n_sub, random_state=42, n_init=10)
        subset["sub_cluster"] = km2.fit_predict(scaled2)

        centroids_orig = scaler2.inverse_transform(km2.cluster_centers_)

        
        sub_labels = {}
        for i, (disc, pe) in enumerate(centroids_orig):
            sub_labels[i] = _sub_label(disc, pe)

        
        parent_name = CLUSTER_NAMES.get(chosen_cluster, f"Cluster {chosen_cluster}")

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(11, 7))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(PANEL)

        for scid in range(n_sub):
            mask2   = subset["sub_cluster"] == scid
            sub_sub = subset[mask2]
            ax.scatter(
                sub_sub["discount_pct"], sub_sub["pe_ratio"],
                c=COLORS[scid % len(COLORS)],
                label=f"Sub-{scid}  ({sub_labels[scid]})",
                s=160, alpha=0.88,
                edgecolors="#1a1f2e", linewidths=1.2, zorder=3,
            )
            for _, row in sub_sub.iterrows():
                ax.annotate(
                    row["ticker"],
                    (row["discount_pct"], row["pe_ratio"]),
                    textcoords="offset points", xytext=(9, 5),
                    fontsize=9, color=WHITE, alpha=0.92,
                )

        for i, (disc, pe) in enumerate(centroids_orig):
            ax.scatter(disc, pe, marker="X", s=280,
                       c=COLORS[i % len(COLORS)],
                       edgecolors="white", linewidths=1.5, zorder=5)
            ax.annotate(f"centroid {i}", (disc, pe),
                        textcoords="offset points", xytext=(-10, -16),
                        fontsize=7.5, color="white", alpha=0.7)

        ax.axvline(x=20, color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)
        ax.axvline(x=40, color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)
        ax.axhline(y=15, color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)
        ax.axhline(y=30, color="#2a3050", linestyle="--", linewidth=1, alpha=0.6)

        ylim = ax.get_ylim()
        top  = ylim[1] * 0.97 if ylim[1] else 60
        ax.text(2,  top, "Near High",    color="#3a4060", fontsize=8, va="top")
        ax.text(22, top, "Mid Range",    color="#3a4060", fontsize=8, va="top")
        ax.text(42, top, "Deep Discount",color="#3a4060", fontsize=8, va="top")

        ax.set_xlabel(
            "Discount from 52W High (%)\n[ 0% = at 52W High   50%+ = deep discount ]",
            color=DIM, fontsize=11,
        )
        ax.set_ylabel("PE Ratio", color=DIM, fontsize=11)
        ax.set_title(
            f"Stage 2 — Sub-Cluster of {parent_name}\nPE Ratio vs Discount from 52W High",
            color=WHITE, fontsize=13, pad=14,
        )
        ax.tick_params(colors=DIM)
        for sp in ax.spines.values():
            sp.set_color("#1a1f2e")
        ax.legend(facecolor="#0d1018", edgecolor="#1a1f2e",
                  labelcolor=WHITE, fontsize=9)
        ax.grid(color="#1a1f2e", linestyle="--", linewidth=0.5, alpha=0.5)
        plt.tight_layout()
        chart_b64 = _fig_to_base64(fig)

      
        sub_summary = []
        for scid in range(n_sub):
            sub_sub = subset[subset["sub_cluster"] == scid]
            sub_summary.append({
                "sub_cluster":   scid,
                "label":         sub_labels[scid],
                "tickers":       sub_sub["ticker"].tolist(),
                "count":         len(sub_sub),
                "avg_discount":  round(float(sub_sub["discount_pct"].mean()), 2),
                "avg_pe":        round(float(sub_sub["pe_ratio"].mean()), 2),
                "avg_price":     round(float(sub_sub["current_price"].mean()), 2),
            })

        centroids_payload = [
            {
                "sub_cluster": i,
                "discount_pct": round(float(d), 2),
                "pe_ratio":     round(float(p), 2),
                "label":        sub_labels[i],
            }
            for i, (d, p) in enumerate(centroids_orig)
        ]

        out_cols = [
            "ticker", "company_name", "current_price",
            "week_52_high", "week_52_low", "discount_pct",
            "pe_ratio", "sub_cluster",
        ]
        stocks_out = subset[out_cols].copy()
        stocks_out["sub_cluster"] = stocks_out["sub_cluster"].astype(int)
        stocks_out["sub_label"]   = stocks_out["sub_cluster"].map(sub_labels)

        return Response({
            "chart":         chart_b64,
            "parent_cluster":chosen_cluster,
            "parent_label":  parent_name,
            "sub_summary":   sub_summary,
            "centroids":     centroids_payload,
            "stocks":        stocks_out.to_dict(orient="records"),
        })
