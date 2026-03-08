const HELP = {
    // Screener filters
    pe_ratio: "Price-to-Earnings ratio — compares a stock's price to its annual profit per share. Low P/E (under 15) may mean it's undervalued; high P/E (over 30) may mean investors expect high growth.",
    market_cap: "Market Capitalization — the total value of all a company's shares. Large-cap ($10B+) = stable & established. Mid-cap ($2-10B) = growing. Small-cap (<$2B) = riskier but higher potential.",
    dividend_yield: "Dividend Yield — annual dividends paid as a percentage of the stock price. A 3% yield on a $100 stock means $3/year in passive income per share.",
    beta: "Beta measures how much a stock moves relative to the overall market. Beta = 1 means it moves with the market. Beta > 1 = more volatile (bigger swings). Beta < 1 = more stable.",
    sector: "The industry group a company belongs to (e.g., Technology, Healthcare, Finance). Diversifying across sectors reduces risk.",
    region: "Filter by the stock's home market — US, China/Hong Kong, Japan, Europe, India, and more. Investing globally diversifies your portfolio across different economies and currencies.",
    asset_type: "Stocks are shares in individual companies. ETFs (Exchange-Traded Funds) are baskets of many stocks/bonds bundled together — great for instant diversification.",

    // Screener presets
    preset_value: "Value investing looks for stocks trading below their true worth — typically low P/E ratios and solid dividends. Think Warren Buffett's approach.",
    preset_growth: "Growth investing targets companies expected to grow revenues and earnings faster than average, often in tech. Higher risk, higher potential reward.",
    preset_dividend: "Dividend investing focuses on stocks that pay regular cash dividends — ideal for passive income. These tend to be mature, stable companies.",
    preset_etf: "ETFs bundle many assets into one trade. They're low-cost, diversified, and great for beginners or anyone who wants broad market exposure.",

    // Recommendations
    match_score: "How well this investment fits your risk profile, goals, and timeline. 90%+ = excellent fit. Below 50% = not ideal for your situation.",
    risk_level: "Our assessment of this investment's volatility. Low = steady & predictable. Medium = some ups and downs. High = can swing significantly.",
    allocation_stocks: "Stocks (equities) offer the highest long-term growth but also the most short-term volatility. Your % depends on your risk tolerance and timeline.",
    allocation_bonds: "Bonds are loans to governments or companies that pay steady interest. They're more stable than stocks but grow slower. Good for preserving capital.",
    allocation_cash: "Cash and cash equivalents (money market, CDs, savings) — safest but lowest returns. Acts as a buffer for emergencies or buying opportunities.",

    // Profile
    time_horizon: "How long before you'll need this money. Longer horizons allow more risk because you have time to recover from market dips.",
    investment_style: "Lump sum = investing a large amount at once. Monthly contributions = investing a fixed amount regularly (dollar-cost averaging). Both approaches have pros and cons.",
    risk_reaction: "This question reveals your real risk tolerance. There's no right answer — it's about what lets you sleep at night.",
    income_stability: "Stable income lets you take more investment risk since you won't need to sell investments during downturns to cover living expenses.",

    // Screener signals
    signal: "Our recommendation based on analyst consensus, valuation (P/E), dividends, volatility, and yearly performance. Buy = looks favorable. Hold = no strong reason to act. Avoid = caution advised.",

    // Market
    volume: "Number of shares traded today. High volume = lots of buying/selling activity. Low volume can mean less interest or harder to trade.",
    day_range: "The lowest and highest prices the stock traded at today — shows how much it moved in a single session.",

    // Portfolio
    portfolio_value: "The current total value of all your holdings based on real-time market prices.",
    gain_loss: "The difference between your current portfolio value and what you originally paid. Green = profit, red = loss.",
    sector_allocation: "How your investments are spread across different industries. Good diversification means no single sector dominates.",

    // Alerts
    price_alert: "Set a target price to get notified when a stock reaches that level — either rising above or dropping below your target.",

    // Comparison
    normalized_chart: "Shows each stock's performance starting from the same point (0%). Useful for comparing stocks at different price levels on equal footing.",

    // Trading Advisor — category tabs
    ta_hidden_gems: "Hidden Gems are stocks flying under the radar — they show early signs of momentum like price-volume divergences or quiet accumulation before the crowd notices. These are higher-risk but can deliver outsized returns if you catch them early.",
    ta_smart_money: "Smart Money Flow tracks unusual volume and trading patterns that suggest big institutions (hedge funds, banks) are quietly buying. When the 'smart money' moves in, the stock often follows upward.",
    ta_momentum: "Momentum Plays are stocks already trending up with strong technical signals. The idea is simple: winners tend to keep winning in the short term. Ride the wave, but use a stop-loss in case it reverses.",
    ta_swing: "Swing Trades target stocks at key turning points — bouncing off support levels or breaking through resistance. You hold for a few days to a couple of weeks, aiming to catch a price 'swing' in your favor.",
    ta_oversold: "Oversold Bargains are stocks that have dropped significantly and may be due for a bounce. Technical indicators (like RSI below 30) suggest selling is overdone. These are patient-buyer opportunities — the price may recover.",

    // Trading Advisor — edge badges
    ta_divergence: "Divergence means the price is moving one way but a key indicator (like RSI or MACD) is moving the other way. This often signals the current trend is losing steam and a reversal may be coming.",
    ta_smart_money_badge: "This stock shows unusual volume patterns — possibly large institutions quietly building a position. When big players accumulate shares, it's often a bullish sign.",
    ta_outperformer: "This stock is beating its sector or the overall market in relative strength. Outperformers tend to keep outperforming, making them attractive momentum plays.",
    ta_squeeze: "A Bollinger Band squeeze means the stock's price range has gotten very tight — like a coiled spring. When it 'uncoils', a big move often follows. The direction isn't guaranteed, but combined with other signals it can be powerful.",

    // Trading Advisor — pick card fields
    ta_entry: "Entry Price — the suggested price to buy the stock at. Try to get in at or below this level for the best risk/reward setup.",
    ta_target: "Target Price — where the analysis expects the stock to reach. This is your potential profit level. Consider selling some or all of your position here.",
    ta_stop_loss: "Stop-Loss — the price where you should sell to limit your loss if the trade goes against you. Always use a stop-loss to protect your capital. No trade is guaranteed.",
    ta_risk_reward: "Risk/Reward Ratio — compares the potential profit to the potential loss. A 2:1 ratio means you could gain $2 for every $1 you risk. Higher is better; aim for at least 1.5x.",
    ta_confidence: "Confidence shows how many technical signals agree on this trade setup. Higher confidence means more indicators are aligned, but no score guarantees success.",
    ta_score: "A composite score (0–100) combining trend strength, momentum, volume patterns, and risk signals. Higher scores suggest a stronger overall setup.",

    // Trading Advisor — market mood
    ta_market_mood: "Market Mood shows the overall sentiment across all scanned stocks. Bullish = most stocks trending up. Bearish = most trending down. Mixed = no clear direction. This helps you decide how aggressive to be.",
    ta_risk_level: "Risk Level indicates how volatile this trading strategy is. Low = smaller price swings, steadier. Medium = moderate ups and downs. High = big potential gains but also bigger losses.",
};

let activeTooltip = null;

function initTooltips() {
    document.addEventListener("mouseover", showTooltip);
    document.addEventListener("mouseout", hideTooltip);
    document.addEventListener("click", (e) => {
        if (e.target.closest("[data-help]")) {
            e.preventDefault();
            e.stopPropagation();
            const el = e.target.closest("[data-help]");
            if (activeTooltip && activeTooltip._helpTarget === el) {
                hideTooltipNow();
            } else {
                showTooltipFor(el);
            }
        } else if (activeTooltip) {
            hideTooltipNow();
        }
    });
}

function showTooltip(e) {
    const el = e.target.closest("[data-help]");
    if (!el) return;
    showTooltipFor(el);
}

function hideTooltip(e) {
    const el = e.target.closest("[data-help]");
    if (!el) return;
    if (activeTooltip && activeTooltip._helpTarget === el) {
        hideTooltipNow();
    }
}

function showTooltipFor(el) {
    hideTooltipNow();
    const key = el.getAttribute("data-help");
    const text = HELP[key];
    if (!text) return;

    const tip = document.createElement("div");
    tip.className = "help-tooltip";
    tip.innerHTML = `<div class="help-tooltip-content">${text}</div>`;
    tip._helpTarget = el;
    document.body.appendChild(tip);
    activeTooltip = tip;

    const rect = el.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();

    let top = rect.top - tipRect.height - 10;
    let left = rect.left + (rect.width / 2) - (tipRect.width / 2);
    let arrowClass = "arrow-bottom";

    if (top < 8) {
        top = rect.bottom + 10;
        arrowClass = "arrow-top";
    }
    left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));

    tip.style.top = top + window.scrollY + "px";
    tip.style.left = left + "px";
    tip.classList.add(arrowClass);

    requestAnimationFrame(() => tip.classList.add("visible"));
}

function hideTooltipNow() {
    if (activeTooltip) {
        activeTooltip.remove();
        activeTooltip = null;
    }
}

function helpIcon(key) {
    if (!HELP[key]) return "";
    return `<span class="help-icon" data-help="${key}" tabindex="0" role="button" aria-label="Help">?</span>`;
}

initTooltips();
