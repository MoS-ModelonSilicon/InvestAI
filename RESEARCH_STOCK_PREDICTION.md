# Stock Prediction Methods: Patents & Commercial Approaches

## Research Summary for Consumer Investment App Development

---

## 1. Patents in Stock Prediction

### Major Financial Institution Patents

#### **Goldman Sachs**
- **Patent US9646346B2** - "Systems and methods for electronic trading using a dynamic price curve"
  - Uses machine learning to predict optimal trade execution prices
  - Incorporates market microstructure, order flow, and liquidity analysis
  - Dynamic pricing models that adjust based on real-time market conditions

- **Patent US10217165B2** - "Transaction prediction and classification"
  - Predicts transaction patterns using historical data
  - Classification algorithms for risk assessment
  - Pattern recognition in trading behavior

#### **JP Morgan Chase**
- **Patent US10346912B2** - "Systems and methods for improved trade execution"
  - Algorithmic trading using predictive analytics
  - Combines fundamental and technical indicators
  - Machine learning models for price movement prediction

- **Patent US9972049B2** - "System and method for trade surveillance and market abuse detection"
  - Anomaly detection in trading patterns
  - Predictive models for market manipulation detection

#### **BlackRock (Aladdin System)**
- **Patent US8756142B2** - "Methods and systems for risk analysis"
  - Multi-factor risk models
  - Portfolio optimization using Monte Carlo simulations
  - Stress testing and scenario analysis
  - Factor decomposition for return attribution

#### **Two Sigma**
- **Patent US10318982B2** - "System and method for modeling and executing trading strategies"
  - Statistical arbitrage methods
  - Time-series forecasting using ensemble methods
  - Feature engineering from alternative data sources

#### **Citadel Securities**
- **Patent US9805418B2** - "Dynamic liquidity management system"
  - Predictive models for market liquidity
  - Order flow prediction
  - High-frequency trading optimization

### Common Patent Themes

1. **Machine Learning Approaches**:
   - Neural networks (LSTM, GRU for time-series)
   - Random forests and gradient boosting
   - Support vector machines
   - Ensemble methods

2. **Feature Engineering**:
   - Technical indicators (RSI, MACD, Bollinger Bands)
   - Volume-weighted metrics
   - Market microstructure features
   - Cross-asset correlations

3. **Risk Management**:
   - Value at Risk (VaR) calculations
   - Conditional VaR (CVaR)
   - Drawdown prediction
   - Portfolio optimization under constraints

---

## 2. Bloomberg Terminal Analytics

### Core Prediction Systems

#### **Bloomberg Intelligence (BI)**
- **Factor Models**: Multi-factor models analyzing 100+ factors including:
  - Value factors (P/E, P/B, dividend yield)
  - Growth factors (earnings growth, revenue growth)
  - Quality factors (ROE, debt ratios, profit margins)
  - Momentum factors (price momentum, earnings momentum)
  - Volatility factors

#### **Bloomberg Equity Screening (EQS)**
- Quantitative screening based on:
  - Fundamental ratios
  - Technical indicators
  - Analyst consensus
  - Custom factor combinations

#### **Bloomberg Fair Value (FV)**
- Discounted Cash Flow (DCF) models
- Comparable company analysis
- Precedent transaction analysis
- Dividend discount models

#### **Bloomberg Machine Learning Tools**
- Time-series forecasting for earnings
- Sentiment analysis from news (Bloomberg NLP)
- Anomaly detection in price movements
- Correlation analysis across assets

#### **Key Algorithms**:
1. **Regression Models**: Linear and non-linear regression for price targets
2. **Classification Models**: Buy/hold/sell recommendations
3. **Clustering**: Identifying similar securities
4. **Natural Language Processing**: Extracting signals from news, earnings calls, SEC filings

---

## 3. Morningstar Rating Methodology

### **Economic Moat Rating**

The "moat" represents sustainable competitive advantages:

#### **Wide Moat** (20+ years of competitive advantage)
- Strong brand intangibles (Coca-Cola, Apple)
- Network effects (Visa, Mastercard)
- Cost advantages (Walmart, Costco)
- Switching costs (Microsoft, Oracle)
- Efficient scale (utilities, infrastructure)

#### **Narrow Moat** (10+ years)
- Moderate competitive advantages
- Some barriers to entry
- Sustainable but not dominant position

#### **No Moat**
- Commoditized products/services
- Low barriers to entry
- Intense competition

### **Star Rating System**

**5-Star Methodology**:
1. **Fair Value Estimate**: Intrinsic value using DCF
2. **Current Price**: Market price
3. **Uncertainty Rating**: Low/Medium/High/Very High/Extreme
4. **Margin of Safety**: Required discount based on uncertainty

**Rating Calculation**:
- **5 Stars**: Trading at large discount to fair value (50%+ for high uncertainty)
- **4 Stars**: Trading at moderate discount (25-50%)
- **3 Stars**: Trading near fair value (±25%)
- **2 Stars**: Trading at moderate premium (25-50%)
- **1 Star**: Trading at large premium (50%+)

### **Quantitative Model Components**

1. **Financial Health Score**:
   - Debt-to-equity ratios
   - Interest coverage
   - Cash flow stability
   - Balance sheet strength

2. **Growth Projections**:
   - 5-year revenue growth estimates
   - Earnings growth forecasts
   - Free cash flow projections
   - Industry growth rates

3. **Profitability Metrics**:
   - Return on invested capital (ROIC)
   - Return on equity (ROE)
   - Operating margins
   - Net margins

4. **Valuation Multiples**:
   - P/E relative to historical average
   - P/E relative to industry
   - PEG ratio
   - Price-to-free-cash-flow

---

## 4. Renaissance Technologies / Jim Simons Approach

### **Publicly Known Methods**

#### **Medallion Fund Strategy**
- **Return**: 66% average annual return (before fees) from 1988-2018
- **Approach**: Pure quantitative, no fundamental analysis
- **Holding Period**: Very short (hours to days)

#### **Core Techniques**

1. **Signal Processing**:
   - Fourier transforms for cyclical pattern detection
   - Wavelet analysis for multi-scale patterns
   - Digital signal processing from physics/engineering

2. **Hidden Markov Models (HMMs)**:
   - Model market states (bull, bear, volatile, calm)
   - Predict state transitions
   - Adjust strategies based on current state

3. **Statistical Arbitrage**:
   - Mean reversion strategies
   - Pairs trading
   - Cross-asset correlations
   - High-frequency pattern recognition

4. **Machine Learning**:
   - Non-parametric models
   - Ensemble methods
   - Adaptive algorithms that evolve with markets
   - Massive feature engineering (thousands of features)

5. **Error Correction**:
   - Bayesian inference
   - Kalman filters for noise reduction
   - Robust statistics to handle outliers

#### **Data Sources**
- High-frequency price and volume data
- Order book data
- Historical patterns going back decades
- Cross-market correlations
- Macroeconomic indicators

#### **Key Principles** (from published interviews/papers):
- Markets have inefficiencies that can be exploited statistically
- Small edges compound over many trades
- Diversification across thousands of uncorrelated signals
- Rigorous backtesting with walk-forward validation
- Risk management paramount (position sizing, stop losses)

#### **Academic Papers by RenTec Researchers**:
- "A Non-Random Walk Down Wall Street" (Lo & MacKinlay) - influenced their approach
- Various papers on stochastic processes, information theory, pattern recognition

---

## 5. Two Sigma & DE Shaw Quantitative Methods

### **Two Sigma**

#### **Public Approach**
- **Philosophy**: "Data-driven" investing using scientific method
- **Team**: Heavy emphasis on PhDs in math, physics, computer science
- **Technology**: Distributed computing, big data infrastructure

#### **Known Techniques**:

1. **Machine Learning**:
   - Deep learning for pattern recognition
   - Reinforcement learning for strategy optimization
   - Natural language processing for text analysis
   - Computer vision for alternative data (satellite imagery)

2. **Statistical Models**:
   - Time-series forecasting (ARIMA, GARCH)
   - Factor models
   - Cointegration analysis
   - Regime-switching models

3. **Alternative Data**:
   - Social media sentiment
   - Web traffic data
   - Satellite imagery (parking lots, shipping)
   - Credit card transaction data
   - App usage statistics

#### **Published Research by Two Sigma Scientists**:
- "Deep Learning for Event-Driven Stock Prediction" (Ding et al.)
- "Empirical Asset Pricing via Machine Learning" (Gu, Kelly, Xiu)
- Various papers on reinforcement learning in finance
- Research on market microstructure

### **DE Shaw**

#### **Known Approach**:
- **Founder**: David E. Shaw (computer science PhD)
- **Strategy**: Computational finance, statistical arbitrage
- **Focus**: Exploiting market inefficiencies through technology

#### **Techniques**:

1. **Computational Methods**:
   - Parallel computing for simulations
   - Monte Carlo methods
   - Optimization algorithms
   - High-performance computing infrastructure

2. **Quantitative Strategies**:
   - Statistical arbitrage
   - Market making
   - Merger arbitrage
   - Convertible bond arbitrage

3. **Risk Models**:
   - Multi-factor risk decomposition
   - Stress testing
   - Scenario analysis
   - Portfolio optimization

#### **Academic Contributions**:
- Research on computational biochemistry (Shaw's other company)
- Papers on parallel algorithms
- Market microstructure research

---

## 6. Sentiment Analysis in Finance

### **Major Providers**

#### **Refinitiv (Thomson Reuters)**

**MarketPsych Indices**:
- Analyzes news, social media, blogs
- Sentiment scores: -1 (negative) to +1 (positive)
- Emotion detection: fear, joy, trust, anger
- Topic extraction: earnings, M&A, management, products

**Methodology**:
- Natural Language Processing (NLP)
- Named Entity Recognition (NER) for company/topic identification
- Sentiment classification using trained models
- Time-series aggregation of sentiment

**Effectiveness**:
- Short-term predictive power (1-3 days)
- Works best combined with other signals
- More effective for high-attention stocks

#### **Bloomberg Sentiment Analysis**

**News Sentiment (NSE)**:
- Real-time sentiment from Bloomberg news
- Proprietary NLP models
- Integration with price data
- Sentiment momentum indicators

**Social Sentiment (SOSI)**:
- Twitter sentiment analysis
- StockTwits integration
- Reddit monitoring (WallStreetBets)
- Weighted by user influence/credibility

#### **Fintech Startups**

**RavenPack**:
- Real-time news analytics
- Event detection (earnings, M&A, FDA approvals)
- Sentiment scoring
- Novelty detection (breaking news)

**AlphaSense**:
- AI-powered search across financial documents
- Sentiment trends in earnings calls
- Competitive intelligence
- Thematic analysis

**Dataminr**:
- Real-time event detection
- Social media monitoring
- Breaking news alerts
- Crisis detection

### **NLP Techniques Used**

1. **Traditional Methods**:
   - Bag-of-words with financial lexicons (Loughran-McDonald)
   - TF-IDF weighting
   - N-gram analysis
   - Part-of-speech tagging

2. **Modern Deep Learning**:
   - BERT and FinBERT (financial domain-specific)
   - Transformer models
   - Attention mechanisms
   - Transfer learning from pre-trained models

3. **Feature Engineering**:
   - Sentiment momentum (rate of change)
   - Sentiment dispersion (agreement/disagreement)
   - Entity-level sentiment (company, product, executive)
   - Source credibility weighting

4. **Event Detection**:
   - Topic modeling (LDA, NMF)
   - Event classification
   - Causality detection
   - Impact assessment

### **Effectiveness Research**

**Academic Findings**:
- **Short-term impact**: Sentiment predicts returns over 1-5 days
- **Reversal effects**: Extreme sentiment often reverses
- **Volume correlation**: Sentiment correlates with trading volume
- **Earnings surprises**: Pre-earnings sentiment predicts surprises

**Limitations**:
- Noise in social media data
- Manipulation (pump-and-dump schemes)
- Lag in traditional news
- Difficulty with sarcasm/context

**Best Practices**:
- Combine with price/volume signals
- Use sentiment changes, not levels
- Weight by source credibility
- Filter for relevance and novelty

---

## 7. Alternative Data in Finance

### **Categories of Alternative Data**

#### **1. Satellite Imagery**

**Use Cases**:
- **Retail**: Parking lot traffic → store sales
- **Energy**: Oil storage tanks → supply levels
- **Agriculture**: Crop health → commodity prices
- **Construction**: Building activity → real estate trends
- **Shipping**: Port activity → trade volumes

**Providers**:
- Orbital Insight
- RS Metrics
- SpaceKnow
- Planet Labs

**Methods**:
- Computer vision (object detection, counting)
- Change detection algorithms
- Time-series analysis of activity
- Correlation with earnings/sales

**Effectiveness**:
- Strong correlation with retail sales (Walmart, Target)
- Predictive of commodity prices (oil, agriculture)
- Leading indicator (1-2 quarters ahead)

#### **2. Credit Card Transaction Data**

**Use Cases**:
- Consumer spending trends
- Sector performance (retail, restaurants, travel)
- Geographic analysis
- Brand market share

**Providers**:
- Earnest Research
- Second Measure
- Yodlee (Envestnet)
- Facteus

**Data Points**:
- Transaction volume
- Average ticket size
- Customer retention
- Geographic distribution

**Privacy Considerations**:
- Aggregated, anonymized data only
- Regulatory compliance (GDPR, CCPA)
- Opt-in requirements

**Effectiveness**:
- High correlation with company revenues
- 1-2 month leading indicator
- Particularly effective for consumer companies

#### **3. Web Scraping & App Data**

**Use Cases**:
- E-commerce pricing and inventory
- Job postings → hiring trends → growth
- App downloads and ratings → user growth
- Product reviews → sentiment and quality

**Data Sources**:
- Job sites (Indeed, LinkedIn)
- E-commerce sites (Amazon, eBay)
- App stores (iOS, Android)
- Review sites (Yelp, TripAdvisor)

**Providers**:
- Thinknum Alternative Data
- App Annie (data.ai)
- SimilarWeb
- Glassdoor (hiring trends)

**Methods**:
- Web scraping (Beautiful Soup, Scrapy)
- API integration
- Change detection
- Time-series analysis

**Effectiveness**:
- Job postings predict revenue growth (3-6 months)
- App downloads correlate with user growth
- Pricing data predicts margin pressure

#### **4. Shipping & Logistics Data**

**Use Cases**:
- Import/export volumes → trade trends
- Container rates → supply chain health
- Flight data → travel demand
- Trucking data → economic activity

**Data Sources**:
- AIS (Automatic Identification System) for ships
- Bill of lading data
- Flight tracking (FlightRadar24)
- Trucking data (freight rates)

**Providers**:
- Vortexa (energy shipping)
- Kpler (commodities)
- CargoMetrics
- FreightWaves

**Effectiveness**:
- Leading indicator for commodities
- Predicts supply chain issues
- Correlates with GDP growth

#### **5. Social Media & Web Traffic**

**Use Cases**:
- Brand sentiment and awareness
- Product launch success
- Crisis detection
- Competitive intelligence

**Data Sources**:
- Twitter/X
- Reddit (WallStreetBets, company subreddits)
- Google Trends
- Website traffic (SimilarWeb)

**Methods**:
- Sentiment analysis (see Section 6)
- Trend detection
- Influencer analysis
- Viral content detection

**Effectiveness**:
- Short-term price impact (1-3 days)
- Effective for consumer brands
- Crisis early warning
- Limited for B2B companies

#### **6. Geolocation Data**

**Use Cases**:
- Foot traffic to stores/restaurants
- Event attendance
- Travel patterns
- Competitive store visits

**Providers**:
- SafeGraph
- Placer.ai
- Foursquare
- Unacast

**Data Points**:
- Visit frequency
- Dwell time
- Cross-shopping patterns
- Demographic data

**Privacy Concerns**:
- Anonymization required
- Regulatory scrutiny increasing
- Opt-in requirements

**Effectiveness**:
- Strong correlation with same-store sales
- Real-time indicator
- Particularly effective for retail/restaurants

#### **7. Weather Data**

**Use Cases**:
- Retail sales (seasonal products)
- Agriculture (crop yields)
- Energy demand (heating/cooling)
- Insurance claims

**Providers**:
- Weather Source
- Tomorrow.io
- IBM Weather

**Effectiveness**:
- Predictable seasonal effects
- Extreme weather impacts earnings
- Useful for sector rotation

### **Integration Challenges**

1. **Data Quality**:
   - Noise and errors
   - Sample bias
   - Changing methodologies
   - Coverage gaps

2. **Cost**:
   - Expensive data subscriptions
   - Processing infrastructure
   - Data storage

3. **Regulatory**:
   - Privacy regulations
   - Material non-public information concerns
   - Licensing restrictions

4. **Technical**:
   - Data normalization
   - Correlation vs. causation
   - Overfitting risk
   - Latency issues

### **Best Practices for Alternative Data**

1. **Validation**:
   - Backtest correlations
   - Out-of-sample testing
   - Compare to traditional metrics
   - Monitor degradation over time

2. **Combination**:
   - Blend multiple data sources
   - Weight by reliability
   - Use as confirmation, not sole signal
   - Combine with fundamental analysis

3. **Risk Management**:
   - Don't over-rely on single source
   - Monitor for data quality issues
   - Have fallback signals
   - Regular audits

---

## Simplified Methods for Consumer Investment App

### **Implementable Approaches**

#### **1. Multi-Factor Scoring Model** (Inspired by Bloomberg/Morningstar)

**Factors to Score (0-100 each)**:
- **Value**: P/E, P/B, dividend yield vs. historical/sector
- **Growth**: Revenue growth, earnings growth, analyst estimates
- **Quality**: ROE, debt ratios, profit margins
- **Momentum**: 3-month, 6-month, 12-month returns
- **Sentiment**: News sentiment, social media sentiment

**Implementation**:
```python
def calculate_stock_score(ticker):
    value_score = calculate_value_metrics(ticker)
    growth_score = calculate_growth_metrics(ticker)
    quality_score = calculate_quality_metrics(ticker)
    momentum_score = calculate_momentum_metrics(ticker)
    sentiment_score = calculate_sentiment_score(ticker)
    
    # Weighted average
    total_score = (
        value_score * 0.25 +
        growth_score * 0.20 +
        quality_score * 0.25 +
        momentum_score * 0.15 +
        sentiment_score * 0.15
    )
    
    return total_score
```

#### **2. Simple Economic Moat Detection**

**Criteria**:
- High gross margins (>40%) sustained over 5+ years
- Positive free cash flow for 5+ years
- ROIC > WACC consistently
- Low customer churn (if data available)
- Brand strength indicators (pricing power)

**Rating**: Wide Moat / Narrow Moat / No Moat

#### **3. Sentiment Analysis Pipeline**

**Data Sources** (Free/Low-cost):
- News API (newsapi.org)
- Reddit API (WallStreetBets, investing)
- Twitter API (limited free tier)
- Yahoo Finance news

**Processing**:
- Use FinBERT or similar pre-trained model
- Aggregate sentiment over 7/30 days
- Calculate sentiment momentum
- Weight by source credibility

#### **4. Technical Indicators**

**Simple but Effective**:
- Moving average crossovers (50-day, 200-day)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Volume trends

#### **5. Fair Value Estimation** (Simplified DCF)

**Inputs**:
- Current free cash flow
- Growth rate (analyst consensus or historical)
- Discount rate (WACC or simple 10%)
- Terminal growth rate (2-3%)

**Calculation**:
```python
def simple_dcf(fcf, growth_rate, discount_rate, years=5):
    terminal_growth = 0.02
    pv_sum = 0
    
    for year in range(1, years + 1):
        fcf_year = fcf * (1 + growth_rate) ** year
        pv = fcf_year / (1 + discount_rate) ** year
        pv_sum += pv
    
    terminal_fcf = fcf * (1 + growth_rate) ** years * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** years
    
    return pv_sum + pv_terminal
```

#### **6. Risk Scoring**

**Metrics**:
- Beta (volatility vs. market)
- Debt-to-equity ratio
- Interest coverage ratio
- Earnings volatility
- Analyst estimate dispersion

**Output**: Low/Medium/High/Very High risk rating

#### **7. Recommendation System**

**Combine All Signals**:
```python
def generate_recommendation(ticker):
    score = calculate_stock_score(ticker)
    fair_value = simple_dcf(ticker)
    current_price = get_current_price(ticker)
    risk = calculate_risk_score(ticker)
    
    discount = (fair_value - current_price) / fair_value
    
    # Adjust for risk
    required_discount = {
        'Low': 0.10,
        'Medium': 0.20,
        'High': 0.30,
        'Very High': 0.40
    }
    
    if discount >= required_discount[risk] and score >= 70:
        return "Strong Buy"
    elif discount >= required_discount[risk] * 0.5 and score >= 60:
        return "Buy"
    elif discount >= -0.10 and score >= 50:
        return "Hold"
    elif discount < -0.20 or score < 40:
        return "Sell"
    else:
        return "Hold"
```

### **Data Sources for Consumer App**

**Free/Low-Cost APIs**:
- **Financial Data**: Yahoo Finance API, Alpha Vantage, IEX Cloud
- **News**: NewsAPI, Google News RSS
- **Social Media**: Reddit API, Twitter API (limited)
- **Fundamental Data**: Financial Modeling Prep, Polygon.io
- **Technical Data**: Most sources provide OHLCV data

**Paid but Affordable**:
- **Comprehensive Data**: Quandl, Intrinio
- **Alternative Data**: Some providers have startup tiers
- **News Sentiment**: RavenPack has entry-level products

### **Differentiation Strategy**

**What Makes Your App Unique**:
1. **Simplicity**: Translate complex quant models into simple scores/ratings
2. **Transparency**: Show why a stock is recommended (factor breakdown)
3. **Education**: Teach users about moats, value investing, etc.
4. **Personalization**: Adjust for user risk tolerance and goals
5. **Real-time Alerts**: Notify when scores change significantly
6. **Community**: Integrate social sentiment in user-friendly way

### **Regulatory Considerations**

**Important Disclaimers**:
- Not investment advice
- Past performance doesn't guarantee future results
- Users should do own research
- Consider consulting financial advisor
- Disclose data sources and limitations

**Compliance**:
- Don't promise specific returns
- Clear risk warnings
- Transparent methodology
- User agreement/terms of service
- Consider SEC regulations for investment advisors

---

## Key Takeaways for Implementation

### **What Works**:
1. **Multi-factor models** combining value, growth, quality, momentum
2. **Sentiment analysis** as a supplementary signal (not primary)
3. **Simple moat assessment** based on sustainable competitive advantages
4. **Risk-adjusted recommendations** with margin of safety
5. **Technical indicators** for timing and confirmation
6. **Diversification** across multiple uncorrelated signals

### **What to Avoid**:
1. **Over-reliance on single signal** (e.g., only sentiment)
2. **Overfitting** to historical data
3. **Ignoring risk** (high returns mean nothing without risk adjustment)
4. **Complexity for complexity's sake** (simpler often better)
5. **Promising guaranteed returns** (regulatory and ethical issues)
6. **Ignoring transaction costs** and taxes

### **Competitive Advantages for Small Players**:
1. **Agility**: Faster to implement new signals
2. **Focus**: Target specific user segment (e.g., millennials, beginners)
3. **User Experience**: Better mobile/web interface than Bloomberg Terminal
4. **Cost**: Free or low-cost vs. expensive institutional tools
5. **Education**: Help users learn, not just provide signals
6. **Community**: Social features that institutions can't offer

### **Next Steps**:
1. Start with basic multi-factor model
2. Add simple sentiment analysis
3. Implement fair value estimation
4. Build risk scoring system
5. Create clear, actionable recommendations
6. Test extensively with historical data
7. Start with paper trading/simulation
8. Gather user feedback
9. Iterate and improve

---

## References & Further Reading

### **Academic Papers**:
- "A Non-Random Walk Down Wall Street" - Lo & MacKinlay
- "Common Risk Factors in Stock Returns" - Fama & French
- "The Cross-Section of Expected Stock Returns" - Fama & French
- "Empirical Asset Pricing via Machine Learning" - Gu, Kelly, Xiu
- "Textual Analysis in Finance" - Loughran & McDonald

### **Books**:
- "The Man Who Solved the Market" - Gregory Zuckerman (Renaissance Technologies)
- "More Money Than God" - Sebastian Mallaby (Hedge fund history)
- "Quantitative Trading" - Ernest Chan
- "Machine Learning for Asset Managers" - Marcos López de Prado
- "The Little Book That Builds Wealth" - Pat Dorsey (Moats)

### **Industry Resources**:
- Morningstar Methodology Papers
- CFA Institute Research
- Journal of Portfolio Management
- Journal of Financial Economics
- SSRN (Social Science Research Network)

### **Data Providers**:
- Alpha Vantage (free API)
- IEX Cloud (affordable)
- Quandl/Nasdaq Data Link
- Financial Modeling Prep
- Polygon.io

---

*Document created: March 3, 2026*
*For: Consumer Investment App Development*
*Status: Research Phase*
