import "./StocksCard.css";

export default function StocksCard({ stocks }) {

  return (
    <div className="stocks-container">

      <div className="stocks-header">
        <h2>Market Stocks</h2>
        <span className="gold-badge">Live Market Data</span>
      </div>

      <table className="stocks-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Price</th>
            <th>PE Ratio</th>
          </tr>
        </thead>

        <tbody>
          {stocks.map((stock, index) => {
            const priceClass = stock.price > 0 ? "price-green" : "price-red";

            return (
              <tr key={index}>
                <td className="symbol">{stock.symbol}</td>
                <td className={priceClass}>{stock.price}</td>
                <td className="pe-blue">{stock.pe_ratio}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

    </div>
  );
}