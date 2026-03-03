# Stock Prediction Algorithms - Comprehensive Research

## 1. Technical Analysis Algorithms

### Moving Averages
**Simple Moving Average (SMA)**
- Formula: `SMA = (P1 + P2 + ... + Pn) / n`
- Common periods: 20, 50, 100, 200 days
- Signals: Price crossing above SMA = bullish, below = bearish
- Golden Cross: 50-day SMA crosses above 200-day SMA (strong buy signal)
- Death Cross: 50-day SMA crosses below 200-day SMA (strong sell signal)

**Exponential Moving Average (EMA)**
- Formula: `EMA = (Price_today × k) + (EMA_yesterday × (1 - k))` where `k = 2/(n+1)`
- More responsive to recent price changes than SMA
- Common periods: 12, 26, 50, 200 days
- Used in MACD calculation

### Relative Strength Index (RSI)
- Formula: `RSI = 100 - (100 / (1 + RS))` where `RS = Average Gain / Average Loss`
- Range: 0-100
- **Signals:**
  - RSI > 70: Overbought (potential sell signal)
  - RSI < 30: Oversold (potential buy signal)
  - RSI divergence: Price makes new high but RSI doesn't = bearish divergence
- Period: Typically 14 days
- Implementation: Calculate average gains and losses over period, smooth with EMA

### MACD (Moving Average Convergence Divergence)
- Components:
  - MACD Line = 12-day EMA - 26-day EMA
  - Signal Line = 9-day EMA of MACD Line
  - Histogram = MACD Line - Signal Line
- **Signals:**
  - MACD crosses above Signal Line = bullish (buy)
  - MACD crosses below Signal Line = bearish (sell)
  - Histogram expanding = trend strengthening
  - Zero-line crossover = momentum shift

### Bollinger Bands
- Formula:
  - Middle Band = 20-day SMA
  - Upper Band = Middle Band + (2 × Standard Deviation)
  - Lower Band = Middle Band - (2 × Standard Deviation)
- **Signals:**
  - Price touches upper band = overbought
  - Price touches lower band = oversold
  - Bollinger Squeeze: Bands narrow = volatility breakout imminent
  - Price outside bands = strong trend or reversal signal
- Typically 95% of price action occurs within bands

### Volume-Weighted Indicators
**VWAP (Volume Weighted Average Price)**
- Formula: `VWAP = Σ(Price × Volume) / Σ(Volume)`
- Intraday indicator, resets daily
- Price above VWAP = bullish, below = bearish
- Institutional traders use as benchmark

**OBV (On-Balance Volume)**
- Formula: If close > previous close, OBV = previous OBV + volume; else OBV = previous OBV - volume
- Confirms price trends through volume
- Divergence between OBV and price = potential reversal

### Implementation in Trading Apps
- Real-time calculation on streaming price data
- Configurable parameters (periods, thresholds)
- Alert systems when signals trigger
- Backtesting engines to validate strategies
- Multi-timeframe analysis (1min, 5min, 1hr, daily)

---

## 2. Fundamental Analysis Algorithms

### P/E Ratio Analysis
**Price-to-Earnings Ratio**
- Formula: `P/E = Market Price per Share / Earnings per Share (EPS)`
- **Interpretation:**
  - Low P/E (< 15): Potentially undervalued or declining industry
  - High P/E (> 25): Growth expectations or overvalued
  - Compare to industry average and historical P/E
- **PEG Ratio** (P/E to Growth): `PEG = P/E / Annual EPS Growth Rate`
  - PEG < 1: Potentially undervalued
  - PEG > 1: Potentially overvalued

### DCF (Discounted Cash Flow) Model
**Formula:**
```
DCF = Σ [FCF_t / (1 + WACC)^t] + Terminal Value / (1 + WACC)^n

Where:
- FCF_t = Free Cash Flow in year t
- WACC = Weighted Average Cost of Capital
- Terminal Value = FCF_n × (1 + g) / (WACC - g)
- g = perpetual growth rate (typically 2-3%)
```

**Implementation Steps:**
1. Project free cash flows 5-10 years
2. Calculate WACC from cost of equity and debt
3. Discount future cash flows to present value
4. Calculate terminal value (Gordon Growth Model)
5. Sum all discounted cash flows
6. Compare to current market cap

### Earnings Growth Rate
**Sustainable Growth Rate:**
- Formula: `SGR = ROE × (1 - Dividend Payout Ratio)`
- Measures growth without external financing
- Compare actual growth to SGR to assess sustainability

**Historical Growth Analysis:**
- Calculate CAGR: `CAGR = (Ending Value / Beginning Value)^(1/years) - 1`
- Analyze EPS growth over 3, 5, 10 years
- Look for consistent growth patterns

### Debt-to-Equity Ratio
- Formula: `D/E = Total Liabilities / Shareholders' Equity`
- **Interpretation:**
  - D/E < 1: Conservative, less risky
  - D/E > 2: Highly leveraged, higher risk
  - Varies by industry (utilities higher, tech lower)
- **Interest Coverage Ratio:** `EBIT / Interest Expense` (should be > 3)

### Free Cash Flow Analysis
- Formula: `FCF = Operating Cash Flow - Capital Expenditures`
- **FCF Yield:** `FCF / Market Cap` (higher = better value)
- Positive FCF = company can fund growth, pay dividends, buy back shares
- More reliable than earnings (harder to manipulate)

### Robo-Advisor Implementation
**Screening Algorithms:**
1. Filter universe by market cap, liquidity
2. Calculate fundamental ratios from financial statements
3. Score stocks on multiple factors (value, growth, quality)
4. Rank and select top percentile
5. Apply diversification constraints
6. Rebalance periodically (quarterly/annually)

**Factor Scoring Example:**
```python
value_score = normalize(1/PE) + normalize(1/PB) + normalize(FCF_yield)
growth_score = normalize(EPS_growth) + normalize(revenue_growth)
quality_score = normalize(ROE) + normalize(1/DE_ratio)
total_score = w1*value_score + w2*growth_score + w3*quality_score
```

---

## 3. Machine Learning Approaches

### LSTM (Long Short-Term Memory) Neural Networks
**Architecture:**
- Recurrent neural network designed for sequence data
- Handles long-term dependencies in time series
- Gates: Forget gate, Input gate, Output gate

**Implementation for Stock Prediction:**
```python
# Typical architecture
model = Sequential([
    LSTM(50, return_sequences=True, input_shape=(timesteps, features)),
    Dropout(0.2),
    LSTM(50, return_sequences=False),
    Dropout(0.2),
    Dense(25),
    Dense(1)  # Output: next day price
])
```

**Input Features:**
- Historical prices (OHLCV)
- Technical indicators (RSI, MACD, etc.)
- Volume patterns
- Market indices
- Window size: 30-60 days typical

**Challenges:**
- Overfitting to historical patterns
- Non-stationary data
- Market regime changes
- Requires large datasets

### Random Forests
**Approach:**
- Ensemble of decision trees
- Each tree trained on random subset of data and features
- Prediction = average/vote of all trees

**Features for Stock Prediction:**
- Technical indicators
- Fundamental ratios
- Sector performance
- Market sentiment scores
- Macroeconomic indicators

**Advantages:**
- Handles non-linear relationships
- Feature importance ranking
- Resistant to overfitting
- Works with mixed data types

**Implementation:**
```python
from sklearn.ensemble import RandomForestClassifier

# Binary classification: up/down
rf = RandomForestClassifier(n_estimators=100, max_depth=10)
rf.fit(X_train, y_train)  # y = 1 if price up, 0 if down

# Feature importance
importances = rf.feature_importances_
```

### Gradient Boosting (XGBoost, LightGBM)
**Approach:**
- Sequential ensemble: each tree corrects errors of previous
- Highly effective for tabular data
- Often wins Kaggle competitions

**Hyperparameters:**
- Learning rate: 0.01-0.1
- Max depth: 3-10
- Number of estimators: 100-1000
- Subsample: 0.8

**Use Cases:**
- Price direction prediction
- Volatility forecasting
- Anomaly detection
- Feature engineering automation

### Sentiment Analysis
**Data Sources:**
- Twitter/X (financial hashtags)
- Reddit (r/wallstreetbets, r/stocks)
- News headlines (Bloomberg, Reuters)
- SEC filings (10-K, 8-K)
- Earnings call transcripts

**NLP Techniques:**
- **VADER:** Rule-based sentiment for social media
- **FinBERT:** BERT fine-tuned on financial text
- **Named Entity Recognition:** Extract company mentions
- **Topic Modeling:** LDA for theme extraction

**Implementation:**
```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

# Analyze sentiment
inputs = tokenizer(text, return_tensors="pt", padding=True)
outputs = model(**inputs)
sentiment_score = torch.nn.functional.softmax(outputs.logits, dim=-1)
# Returns: [negative, neutral, positive] probabilities
```

**Integration:**
- Aggregate sentiment scores over time windows
- Correlate with price movements (lag analysis)
- Combine with technical/fundamental signals
- Weight by source credibility

### Deep Learning Architectures
**CNN (Convolutional Neural Networks):**
- Treat price charts as images
- Extract visual patterns (head & shoulders, triangles)
- 1D convolutions on time series

**Transformer Models:**
- Attention mechanism for time series
- Capture long-range dependencies
- Recent research: Temporal Fusion Transformers

**Autoencoders:**
- Dimensionality reduction
- Anomaly detection (reconstruction error)
- Feature extraction from high-dimensional data

### Recent Research Directions
- **Reinforcement Learning:** DQN, PPO for trading agents
- **Ensemble Methods:** Combine multiple models
- **Transfer Learning:** Pre-train on multiple stocks
- **Graph Neural Networks:** Model stock relationships
- **Hybrid Models:** Combine ML with domain knowledge

---

## 4. Quantitative Finance Methods

### Modern Portfolio Theory (Markowitz)
**Objective:** Maximize return for given risk level

**Formula:**
```
Portfolio Return: E(Rp) = Σ wi × E(Ri)
Portfolio Variance: σp² = Σ Σ wi × wj × Cov(Ri, Rj)
Sharpe Ratio: (E(Rp) - Rf) / σp

Where:
- wi = weight of asset i
- E(Ri) = expected return of asset i
- Rf = risk-free rate
- Cov(Ri, Rj) = covariance between assets i and j
```

**Efficient Frontier:**
- Set of optimal portfolios
- Maximum return for each risk level
- Calculated via quadratic optimization

**Implementation:**
```python
import numpy as np
from scipy.optimize import minimize

def portfolio_variance(weights, cov_matrix):
    return weights.T @ cov_matrix @ weights

def optimize_portfolio(returns, cov_matrix, target_return):
    n_assets = len(returns)
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # weights sum to 1
        {'type': 'eq', 'fun': lambda w: returns @ w - target_return}
    ]
    bounds = [(0, 1) for _ in range(n_assets)]  # long-only
    result = minimize(portfolio_variance, x0=np.ones(n_assets)/n_assets,
                     args=(cov_matrix,), constraints=constraints, bounds=bounds)
    return result.x
```

### CAPM (Capital Asset Pricing Model)
**Formula:**
```
E(Ri) = Rf + βi × (E(Rm) - Rf)

Where:
- E(Ri) = expected return of asset i
- Rf = risk-free rate (T-bills)
- βi = beta of asset i (systematic risk)
- E(Rm) = expected market return
- (E(Rm) - Rf) = market risk premium
```

**Beta Calculation:**
```
β = Cov(Ri, Rm) / Var(Rm)

Interpretation:
- β = 1: Moves with market
- β > 1: More volatile than market (aggressive)
- β < 1: Less volatile than market (defensive)
- β < 0: Inverse correlation (rare, e.g., gold)
```

**Application:**
- Required return estimation
- Portfolio performance attribution
- Risk-adjusted performance measurement
- Security selection (alpha generation)

### Black-Scholes Model
**Options Pricing Formula:**
```
Call Option: C = S₀N(d₁) - Ke^(-rT)N(d₂)
Put Option: P = Ke^(-rT)N(-d₂) - S₀N(-d₁)

Where:
d₁ = [ln(S₀/K) + (r + σ²/2)T] / (σ√T)
d₂ = d₁ - σ√T

- S₀ = current stock price
- K = strike price
- r = risk-free rate
- T = time to expiration
- σ = volatility
- N(x) = cumulative normal distribution
```

**Greeks (Sensitivities):**
- **Delta (Δ):** ∂C/∂S (price sensitivity, 0-1 for calls)
- **Gamma (Γ):** ∂²C/∂S² (delta sensitivity)
- **Theta (Θ):** ∂C/∂T (time decay)
- **Vega (ν):** ∂C/∂σ (volatility sensitivity)
- **Rho (ρ):** ∂C/∂r (interest rate sensitivity)

**Implementation in Apps:**
- Options pricing calculators
- Implied volatility calculation (solve for σ)
- Risk management (hedge ratios)
- Volatility surface modeling

### Monte Carlo Simulations
**Approach:** Simulate thousands of possible price paths

**Geometric Brownian Motion:**
```
S(t+Δt) = S(t) × exp[(μ - σ²/2)Δt + σε√Δt]

Where:
- μ = drift (expected return)
- σ = volatility
- ε ~ N(0,1) (random normal)
```

**Implementation:**
```python
import numpy as np

def monte_carlo_simulation(S0, mu, sigma, T, dt, n_simulations):
    n_steps = int(T / dt)
    paths = np.zeros((n_simulations, n_steps))
    paths[:, 0] = S0
    
    for t in range(1, n_steps):
        z = np.random.standard_normal(n_simulations)
        paths[:, t] = paths[:, t-1] * np.exp((mu - 0.5*sigma**2)*dt + sigma*np.sqrt(dt)*z)
    
    return paths

# Value at Risk (VaR) calculation
final_prices = paths[:, -1]
VaR_95 = np.percentile(final_prices - S0, 5)  # 95% confidence
```

**Applications:**
- Portfolio risk assessment (VaR, CVaR)
- Options pricing (exotic options)
- Scenario analysis
- Stress testing

### Factor Models (Fama-French)
**Three-Factor Model:**
```
E(Ri) - Rf = αi + β₁(Rm - Rf) + β₂SMB + β₃HML + εi

Where:
- SMB = Small Minus Big (size factor)
- HML = High Minus Low (value factor)
- Rm - Rf = market risk premium
```

**Five-Factor Model (adds):**
- **RMW:** Robust Minus Weak (profitability)
- **CMA:** Conservative Minus Aggressive (investment)

**Implementation:**
- Regression analysis to estimate factor loadings
- Portfolio construction based on factor exposures
- Risk attribution and performance analysis
- Smart beta strategies

**Factor Calculation:**
```python
# SMB: Return of small cap portfolio - large cap portfolio
# HML: Return of high book-to-market - low book-to-market

# Regression
import statsmodels.api as sm

X = pd.DataFrame({
    'Market': market_premium,
    'SMB': smb_factor,
    'HML': hml_factor
})
X = sm.add_constant(X)
y = stock_returns - risk_free_rate

model = sm.OLS(y, X).fit()
alpha = model.params['const']  # Jensen's alpha
factor_betas = model.params[1:]
```

---

## 5. Momentum and Mean Reversion Strategies

### Momentum Strategies
**Core Principle:** "The trend is your friend" - assets that performed well recently will continue to perform well

**Types:**
1. **Cross-Sectional Momentum:**
   - Rank stocks by past returns (e.g., 3-12 months)
   - Buy top decile, short bottom decile
   - Rebalance monthly

2. **Time-Series Momentum:**
   - Buy if asset's return > 0 over lookback period
   - Sell/short if return < 0
   - Applied to each asset independently

**Implementation:**
```python
# 12-month momentum with 1-month skip (avoid reversal)
def calculate_momentum(prices, lookback=252, skip=21):
    momentum = (prices.shift(skip) / prices.shift(lookback + skip)) - 1
    return momentum

# Signal generation
signals = momentum.rank(pct=True)  # Percentile rank
long_positions = signals > 0.8  # Top 20%
short_positions = signals < 0.2  # Bottom 20%
```

**Risk Management:**
- Stop-loss orders (e.g., -10% trailing stop)
- Position sizing based on volatility
- Sector diversification
- Avoid overcrowding (momentum crashes)

**Optimal Timeframes:**
- **Short-term:** 1-3 months (higher turnover, transaction costs)
- **Medium-term:** 6-12 months (classic momentum)
- **Long-term:** 12-24 months (lower Sharpe ratio)
- Avoid 1-month (reversal effect)

**Momentum Indicators:**
- **Rate of Change (ROC):** `(Price_today - Price_n_days_ago) / Price_n_days_ago × 100`
- **Momentum Oscillator:** `Price_today - Price_n_days_ago`
- **Relative Strength:** Compare stock to market/sector

### Mean Reversion Strategies
**Core Principle:** Prices tend to revert to their historical average

**Statistical Basis:**
- Identify "fair value" (moving average, fundamental value)
- Buy when price significantly below fair value
- Sell when price significantly above fair value

**Z-Score Method:**
```python
def calculate_zscore(prices, window=20):
    ma = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    zscore = (prices - ma) / std
    return zscore

# Trading signals
zscore = calculate_zscore(prices)
buy_signal = zscore < -2  # 2 std below mean
sell_signal = zscore > 2   # 2 std above mean
exit_signal = abs(zscore) < 0.5  # Near mean
```

**Pairs Trading:**
- Find cointegrated stock pairs (e.g., Coca-Cola vs Pepsi)
- Calculate spread: `spread = stock_A - β × stock_B`
- Trade when spread deviates from mean
- Market-neutral strategy

**Bollinger Band Mean Reversion:**
```python
# Buy at lower band, sell at upper band
middle = prices.rolling(20).mean()
std = prices.rolling(20).std()
upper = middle + 2 * std
lower = middle - 2 * std

buy = prices < lower
sell = prices > upper
```

**Optimal Timeframes:**
- **Intraday:** Minutes to hours (high-frequency)
- **Short-term:** 1-5 days (swing trading)
- **Medium-term:** 1-4 weeks
- Works best in range-bound markets

### Pattern Detection Algorithms
**Bollinger Squeeze:**
- Bandwidth = (Upper Band - Lower Band) / Middle Band
- Low bandwidth → high volatility breakout imminent
- Trade in direction of breakout

**RSI Divergence:**
```python
def detect_divergence(prices, rsi):
    # Bullish divergence: price makes lower low, RSI makes higher low
    price_lows = prices[prices == prices.rolling(20).min()]
    rsi_lows = rsi[prices == prices.rolling(20).min()]
    
    if len(price_lows) >= 2:
        if price_lows.iloc[-1] < price_lows.iloc[-2] and \
           rsi_lows.iloc[-1] > rsi_lows.iloc[-2]:
            return "bullish_divergence"
    return None
```

**Moving Average Crossovers:**
- Golden Cross: Fast MA crosses above slow MA (momentum)
- Death Cross: Fast MA crosses below slow MA (reversal)

### Regime Detection
**Identify Market State:**
- **Trending:** High momentum, low mean reversion
- **Mean-Reverting:** Low momentum, high mean reversion
- **High Volatility:** Increase position size for mean reversion
- **Low Volatility:** Favor momentum strategies

**Implementation:**
```python
# Hurst exponent (H < 0.5 = mean reversion, H > 0.5 = momentum)
def hurst_exponent(prices, lags=range(2, 20)):
    tau = [np.std(np.subtract(prices[lag:], prices[:-lag])) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0
```

---

## 6. Python Libraries for Stock Analysis

### TA-Lib (Technical Analysis Library)
**Installation:**
```bash
# Windows (requires Visual C++)
pip install TA-Lib

# Or use ta-lib wrapper
pip install ta-lib
```

**Key Functions:**
```python
import talib

# Moving averages
sma = talib.SMA(close, timeperiod=20)
ema = talib.EMA(close, timeperiod=20)

# Momentum indicators
rsi = talib.RSI(close, timeperiod=14)
macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

# Volatility
upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
atr = talib.ATR(high, low, close, timeperiod=14)

# Volume
obv = talib.OBV(close, volume)

# Pattern recognition (150+ patterns)
cdl_doji = talib.CDLDOJI(open, high, low, close)
cdl_hammer = talib.CDLHAMMER(open, high, low, close)
```

**Advantages:**
- 150+ technical indicators
- Optimized C implementation (fast)
- Industry standard
- Pattern recognition

### pandas-ta
**Installation:**
```bash
pip install pandas-ta
```

**Usage:**
```python
import pandas_ta as ta

# Add indicators to DataFrame
df.ta.sma(length=20, append=True)
df.ta.rsi(length=14, append=True)
df.ta.macd(fast=12, slow=26, signal=9, append=True)
df.ta.bbands(length=20, std=2, append=True)

# Strategy (multiple indicators at once)
MyStrategy = ta.Strategy(
    name="Momo and Volatility",
    description="SMA, RSI, MACD, BBands",
    ta=[
        {"kind": "sma", "length": 20},
        {"kind": "rsi", "length": 14},
        {"kind": "macd", "fast": 12, "slow": 26, "signal": 9},
        {"kind": "bbands", "length": 20, "std": 2}
    ]
)
df.ta.strategy(MyStrategy)
```

**Advantages:**
- Pure Python (easier installation)
- Pandas integration
- 130+ indicators
- Custom strategy builder

### Backtrader
**Installation:**
```bash
pip install backtrader
```

**Basic Strategy:**
```python
import backtrader as bt

class SMAStrategy(bt.Strategy):
    params = (('sma_period', 20),)
    
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.sma_period)
    
    def next(self):
        if not self.position:  # Not in market
            if self.data.close[0] > self.sma[0]:
                self.buy()
        else:  # In market
            if self.data.close[0] < self.sma[0]:
                self.sell()

# Run backtest
cerebro = bt.Cerebro()
cerebro.addstrategy(SMAStrategy)
cerebro.adddata(data)
cerebro.broker.setcash(100000)
cerebro.broker.setcommission(commission=0.001)
cerebro.run()
cerebro.plot()
```

**Features:**
- Event-driven backtesting
- Multiple data feeds
- Position sizing
- Commission/slippage modeling
- Performance metrics
- Built-in indicators
- Live trading integration

### Zipline
**Installation:**
```bash
pip install zipline-reloaded  # Maintained fork
```

**Features:**
- Quantopian-style backtesting
- Pipeline API for data processing
- Factor analysis
- Risk metrics
- Realistic market simulation

**Example:**
```python
from zipline import run_algorithm
from zipline.api import order_target_percent, symbol

def initialize(context):
    context.asset = symbol('AAPL')

def handle_data(context, data):
    ma_short = data.history(context.asset, 'price', 20, '1d').mean()
    ma_long = data.history(context.asset, 'price', 50, '1d').mean()
    
    if ma_short > ma_long:
        order_target_percent(context.asset, 1.0)
    else:
        order_target_percent(context.asset, 0.0)

results = run_algorithm(
    start=pd.Timestamp('2020-01-01', tz='UTC'),
    end=pd.Timestamp('2023-01-01', tz='UTC'),
    initialize=initialize,
    handle_data=handle_data,
    capital_base=100000
)
```

### PyFolio
**Installation:**
```bash
pip install pyfolio
```

**Performance Analysis:**
```python
import pyfolio as pf

# Analyze returns
pf.create_full_tear_sheet(
    returns=strategy_returns,
    positions=positions,
    transactions=transactions,
    benchmark_rets=spy_returns
)

# Metrics calculated:
# - Annual return, volatility, Sharpe ratio
# - Max drawdown, Calmar ratio
# - Alpha, beta
# - Rolling metrics
# - Underwater plot
# - Monthly/annual returns heatmap
```

**Key Metrics:**
- **Sharpe Ratio:** `(Return - RiskFree) / Volatility`
- **Sortino Ratio:** Uses downside deviation only
- **Calmar Ratio:** `Annual Return / Max Drawdown`
- **Alpha:** Excess return vs benchmark
- **Beta:** Correlation to benchmark

### QuantLib
**Installation:**
```bash
pip install QuantLib-Python
```

**Capabilities:**
- Options pricing (Black-Scholes, binomial trees)
- Interest rate models
- Bond pricing
- Exotic derivatives
- Risk management

**Example:**
```python
import QuantLib as ql

# Black-Scholes option pricing
spot = 100
strike = 105
rate = 0.05
volatility = 0.2
maturity = 1.0

option = ql.EuropeanOption(
    ql.PlainVanillaPayoff(ql.Option.Call, strike),
    ql.EuropeanExercise(ql.Date(15, 6, 2025))
)

spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
flat_ts = ql.YieldTermStructureHandle(
    ql.FlatForward(0, ql.NullCalendar(), rate, ql.Actual365Fixed())
)
flat_vol_ts = ql.BlackVolTermStructureHandle(
    ql.BlackConstantVol(0, ql.NullCalendar(), volatility, ql.Actual365Fixed())
)

bs_process = ql.BlackScholesProcess(spot_handle, flat_ts, flat_vol_ts)
option.setPricingEngine(ql.AnalyticEuropeanEngine(bs_process))

price = option.NPV()
delta = option.delta()
gamma = option.gamma()
```

### Additional Libraries

**yfinance** (Data Download):
```python
import yfinance as yf

# Download historical data
data = yf.download('AAPL', start='2020-01-01', end='2024-01-01')

# Get company info
ticker = yf.Ticker('AAPL')
info = ticker.info  # P/E, market cap, etc.
financials = ticker.financials
balance_sheet = ticker.balance_sheet
```

**alpha_vantage** (API for data):
```python
from alpha_vantage.timeseries import TimeSeries

ts = TimeSeries(key='YOUR_API_KEY')
data, meta = ts.get_daily(symbol='AAPL', outputsize='full')
```

**scikit-learn** (Machine Learning):
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Feature engineering
features = df[['rsi', 'macd', 'bb_width', 'volume_ratio']]
target = (df['close'].shift(-1) > df['close']).astype(int)

# Train model
X_train, X_test, y_train, y_test = train_test_split(features, target)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = RandomForestClassifier(n_estimators=100)
model.fit(X_train_scaled, y_train)
predictions = model.predict(X_test_scaled)
```

---

## Implementation Example: Complete Technical Analysis System

```python
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
from datetime import datetime, timedelta

class StockAnalyzer:
    def __init__(self, ticker, start_date, end_date):
        self.ticker = ticker
        self.data = yf.download(ticker, start=start_date, end=end_date)
        self.signals = pd.DataFrame(index=self.data.index)
        
    def add_technical_indicators(self):
        """Calculate all technical indicators"""
        df = self.data
        
        # Moving averages
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        
        # RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # MACD
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        
        # Bollinger Bands
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        
        # Volume indicators
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        
        self.data = df
        return self
    
    def generate_signals(self):
        """Generate buy/sell signals"""
        df = self.data
        
        # Signal 1: SMA crossover
        self.signals['SMA_Signal'] = np.where(
            df['SMA_20'] > df['SMA_50'], 1, -1
        )
        
        # Signal 2: RSI
        self.signals['RSI_Signal'] = np.where(
            df['RSI'] < 30, 1,  # Oversold - buy
            np.where(df['RSI'] > 70, -1, 0)  # Overbought - sell
        )
        
        # Signal 3: MACD
        self.signals['MACD_Signal'] = np.where(
            df['MACD_12_26_9'] > df['MACDs_12_26_9'], 1, -1
        )
        
        # Signal 4: Bollinger Bands
        self.signals['BB_Signal'] = np.where(
            df['Close'] < df['BBL_20_2.0'], 1,  # Below lower band - buy
            np.where(df['Close'] > df['BBU_20_2.0'], -1, 0)  # Above upper - sell
        )
        
        # Combined signal (majority vote)
        self.signals['Combined'] = (
            self.signals['SMA_Signal'] + 
            self.signals['RSI_Signal'] + 
            self.signals['MACD_Signal'] + 
            self.signals['BB_Signal']
        )
        
        # Final decision
        self.signals['Position'] = np.where(
            self.signals['Combined'] >= 2, 1,  # Buy
            np.where(self.signals['Combined'] <= -2, -1, 0)  # Sell
        )
        
        return self
    
    def backtest(self, initial_capital=100000):
        """Simple backtest"""
        positions = self.signals['Position'].diff()
        
        # Calculate returns
        self.data['Returns'] = self.data['Close'].pct_change()
        self.data['Strategy_Returns'] = self.data['Returns'] * self.signals['Position'].shift(1)
        
        # Cumulative returns
        self.data['Cumulative_Market_Returns'] = (1 + self.data['Returns']).cumprod()
        self.data['Cumulative_Strategy_Returns'] = (1 + self.data['Strategy_Returns']).cumprod()
        
        # Performance metrics
        total_return = self.data['Cumulative_Strategy_Returns'].iloc[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(self.data)) - 1
        volatility = self.data['Strategy_Returns'].std() * np.sqrt(252)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        cumulative = self.data['Cumulative_Strategy_Returns']
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        results = {
            'Total Return': f"{total_return:.2%}",
            'Annual Return': f"{annual_return:.2%}",
            'Volatility': f"{volatility:.2%}",
            'Sharpe Ratio': f"{sharpe_ratio:.2f}",
            'Max Drawdown': f"{max_drawdown:.2%}",
            'Final Value': f"${initial_capital * (1 + total_return):,.2f}"
        }
        
        return results
    
    def get_current_recommendation(self):
        """Get latest trading recommendation"""
        latest = self.signals.iloc[-1]
        price = self.data['Close'].iloc[-1]
        
        recommendation = {
            'Ticker': self.ticker,
            'Current Price': f"${price:.2f}",
            'RSI': f"{self.data['RSI'].iloc[-1]:.2f}",
            'MACD Signal': 'Bullish' if latest['MACD_Signal'] == 1 else 'Bearish',
            'Position': 'BUY' if latest['Position'] == 1 else 'SELL' if latest['Position'] == -1 else 'HOLD',
            'Signal Strength': abs(latest['Combined'])
        }
        
        return recommendation

# Usage example
if __name__ == "__main__":
    analyzer = StockAnalyzer(
        ticker='AAPL',
        start_date='2020-01-01',
        end_date='2024-01-01'
    )
    
    analyzer.add_technical_indicators()
    analyzer.generate_signals()
    
    # Backtest results
    results = analyzer.backtest()
    print("Backtest Results:")
    for key, value in results.items():
        print(f"{key}: {value}")
    
    # Current recommendation
    print("\nCurrent Recommendation:")
    recommendation = analyzer.get_current_recommendation()
    for key, value in recommendation.items():
        print(f"{key}: {value}")
```

---

## Key Takeaways

### Best Practices
1. **Combine Multiple Signals:** No single indicator is perfect
2. **Risk Management:** Always use stop-losses and position sizing
3. **Backtesting:** Test strategies on historical data before live trading
4. **Transaction Costs:** Account for commissions and slippage
5. **Overfitting:** Avoid optimizing too much on past data
6. **Market Regimes:** Different strategies work in different market conditions
7. **Diversification:** Don't put all capital in one strategy/asset

### Common Pitfalls
- **Look-ahead bias:** Using future information in backtests
- **Survivorship bias:** Only testing on stocks that still exist
- **Data snooping:** Testing too many strategies until one works
- **Ignoring transaction costs:** Erodes returns significantly
- **Over-leverage:** Magnifies losses
- **Curve fitting:** Strategy works on past but fails on new data

### Realistic Expectations
- **Sharpe Ratio:** 1.0-2.0 is good, >2.0 is excellent
- **Annual Returns:** 10-20% is realistic for retail traders
- **Win Rate:** 50-60% is typical (profitability comes from risk/reward)
- **Drawdowns:** Expect 20-30% drawdowns even in good strategies
- **Market Efficiency:** Hard to consistently beat market after costs

### Recommended Learning Path
1. Start with technical analysis (easier to implement)
2. Learn backtesting frameworks (backtrader, zipline)
3. Study risk management and position sizing
4. Explore machine learning (after mastering basics)
5. Paper trade before risking real money
6. Continuously monitor and adapt strategies

---

## Additional Resources

### Academic Papers
- "Momentum Strategies" - Jegadeesh & Titman (1993)
- "A Five-Factor Asset Pricing Model" - Fama & French (2015)
- "Deep Learning for Stock Prediction" - Various recent papers on arXiv

### Books
- "Quantitative Trading" by Ernest Chan
- "Algorithmic Trading" by Andreas Clenow
- "Machine Learning for Asset Managers" by Marcos López de Prado
- "Python for Finance" by Yves Hilpisch

### Platforms for Learning
- **QuantConnect:** Cloud-based algorithmic trading platform
- **Alpaca:** Commission-free API trading
- **Interactive Brokers:** Professional API access
- **Kaggle:** Competitions and datasets for ML models

### APIs and Data Sources
- **Yahoo Finance (yfinance):** Free historical data
- **Alpha Vantage:** Free API with technical indicators
- **Quandl:** Financial and economic data
- **IEX Cloud:** Real-time and historical data
- **Polygon.io:** Market data API

---

*This research document provides a comprehensive overview of stock prediction algorithms. For implementation in your finance tracker app, focus on technical indicators (Section 1) and Python libraries (Section 6) as starting points.*
