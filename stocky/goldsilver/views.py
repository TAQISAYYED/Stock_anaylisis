from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import yfinance as yf
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

class GoldSilverAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        end = datetime.today()
        start = end - timedelta(days=5*365)

        # Fetch data with auto_adjust
        gold_df = yf.download("GC=F", start=start, end=end, interval="1mo", auto_adjust=True)
        silver_df = yf.download("SI=F", start=start, end=end, interval="1mo", auto_adjust=True)

        # Get Close as Series directly
        gold = gold_df["Close"].squeeze().dropna()
        silver = silver_df["Close"].squeeze().dropna()

        # Align by common dates
        common = gold.index.intersection(silver.index)
        gold = gold.reindex(common).dropna()
        silver = silver.reindex(common).dropna()

        # Convert to numpy
        gold_arr = gold.values.flatten()
        silver_arr = silver.values.flatten()

        # Linear Regression
        X = gold_arr.reshape(-1, 1)
        y = silver_arr
        model = LinearRegression()
        model.fit(X, y)
        predicted = model.predict(X)

        # Correlation
        correlation = float(np.corrcoef(gold_arr, silver_arr)[0, 1])

        # Future predictions (next 6 months)
        last_gold = float(gold_arr[-1])
        future_gold = [last_gold * (1 + i * 0.02) for i in range(1, 7)]
        future_silver = model.predict(np.array(future_gold).reshape(-1, 1)).tolist()

        # Price history
        price_history = [
            {
                "date": str(date.date()),
                "gold": round(float(g), 2),
                "silver": round(float(s), 2),
            }
            for date, g, s in zip(common, gold_arr, silver_arr)
        ]

        # Regression data
        regression_data = [
            {
                "gold": round(float(g), 2),
                "silver_actual": round(float(s), 2),
                "silver_predicted": round(float(p), 2),
            }
            for g, s, p in zip(gold_arr, silver_arr, predicted)
        ]

        # Future predictions
        predictions = [
            {
                "month": f"Month +{i+1}",
                "gold": round(future_gold[i], 2),
                "silver_predicted": round(future_silver[i], 2),
            }
            for i in range(6)
        ]

        return Response({
            "correlation": round(correlation, 4),
            "r2_score": round(float(model.score(X, y)), 4),
            "slope": round(float(model.coef_[0]), 4),
            "price_history": price_history,
            "regression_data": regression_data,
            "predictions": predictions,
        })