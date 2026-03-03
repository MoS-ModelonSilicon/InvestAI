let wizardStep = 0;
const wizardAnswers = {};

const WIZARD_STEPS = [
    {
        key: "goal", title: "What's your investment goal?",
        hint: "Your goal shapes which types of investments we recommend — growth stocks for wealth building, dividend stocks for income, etc.",
        options: [
            { value: "retirement", label: "Retirement", icon: "🏖️", desc: "Long-term wealth for retirement" },
            { value: "wealth_growth", label: "Wealth Growth", icon: "📈", desc: "Grow my money aggressively" },
            { value: "passive_income", label: "Passive Income", icon: "💰", desc: "Steady dividends and interest" },
            { value: "short_term", label: "Short-Term Savings", icon: "🎯", desc: "Save for a goal within 1-2 years" },
        ],
    },
    {
        key: "timeline", title: "What's your investment time horizon?",
        helpKey: "time_horizon",
        hint: "Longer time horizons allow for more aggressive investing since you have time to ride out market dips.",
        options: [
            { value: "less_1", label: "Less than 1 year", icon: "⏱️" },
            { value: "1_5", label: "1 – 5 years", icon: "📅" },
            { value: "5_10", label: "5 – 10 years", icon: "📆" },
            { value: "10_plus", label: "10+ years", icon: "🗓️" },
        ],
    },
    {
        key: "investment_style", title: "How are you looking to invest?",
        helpKey: "investment_style",
        hint: "Lump sum means investing a large amount at once. Dollar-cost averaging (monthly) spreads purchases over time, reducing the impact of market timing.",
        options: [
            { value: "lump_sum", label: "One-Time Investment", icon: "💎", desc: "I have a lump sum to invest now" },
            { value: "monthly", label: "Monthly Contributions", icon: "🔄", desc: "I'll invest a fixed amount each month" },
            { value: "both", label: "Both", icon: "⚡", desc: "Lump sum now, plus monthly contributions" },
        ],
    },
    {
        key: "_investment_amounts", title: "How much are you investing?",
        type: "investment_amounts",
        hint: "This helps us calibrate recommendations to your situation. Larger amounts may warrant a slightly more conservative approach to protect your capital.",
    },
    {
        key: "experience", title: "What's your investing experience?",
        hint: "Be honest — this helps us adjust the complexity of our recommendations and the jargon we use.",
        options: [
            { value: "beginner", label: "Beginner", icon: "🌱", desc: "New to investing" },
            { value: "intermediate", label: "Intermediate", icon: "📊", desc: "Some experience with stocks/funds" },
            { value: "advanced", label: "Advanced", icon: "🎓", desc: "Experienced with diverse portfolios" },
        ],
    },
    {
        key: "risk_reaction", title: "If your portfolio dropped 20% in a month, you would…",
        helpKey: "risk_reaction",
        hint: "There's no wrong answer. This reveals your true risk tolerance — what matters is what lets you sleep at night.",
        options: [
            { value: "sell_all", label: "Sell everything", icon: "🚪", desc: "I can't afford to lose money" },
            { value: "sell_some", label: "Sell some holdings", icon: "⚖️", desc: "Reduce exposure to limit losses" },
            { value: "hold", label: "Hold and wait", icon: "🧘", desc: "Stay the course, markets recover" },
            { value: "buy_more", label: "Buy more!", icon: "🛒", desc: "Great opportunity to buy the dip" },
        ],
    },
    {
        key: "income_stability", title: "How stable is your income?",
        helpKey: "income_stability",
        hint: "If your income is steady, you can absorb short-term losses without needing to sell investments to cover expenses.",
        options: [
            { value: "stable", label: "Very Stable", icon: "🏢", desc: "Steady salary, secure employment" },
            { value: "variable", label: "Variable", icon: "📉", desc: "Freelance or commission-based" },
            { value: "uncertain", label: "Uncertain", icon: "❓", desc: "Irregular or recently changed" },
        ],
    },
];

async function loadProfile() {
    const profileData = await api.get("/api/profile");
    const wizardEl = document.getElementById("wizard-container");
    const resultEl = document.getElementById("profile-result");

    if (profileData) {
        wizardEl.style.display = "none";
        resultEl.style.display = "block";
        renderProfileResult(profileData);
    } else {
        wizardEl.style.display = "block";
        resultEl.style.display = "none";
        wizardStep = 0;
        renderWizardStep();
    }
}

function renderWizardStep() {
    const step = WIZARD_STEPS[wizardStep];
    const total = WIZARD_STEPS.length;
    const pct = ((wizardStep + 1) / total) * 100;

    const hintHtml = step.hint ? `<p class="wizard-hint">${step.hint}</p>` : "";

    let content = `
        <div class="wizard-progress"><div class="wizard-progress-fill" style="width:${pct}%"></div></div>
        <div class="wizard-step-label">Step ${wizardStep + 1} of ${total}</div>
        <h2 class="wizard-title">${step.title}</h2>
        ${hintHtml}`;

    if (step.type === "investment_amounts") {
        content += renderInvestmentAmountsStep();
    } else {
        content += '<div class="wizard-options">';
        step.options.forEach((opt) => {
            const selected = wizardAnswers[step.key] === opt.value ? "selected" : "";
            content += `
                <div class="wizard-option ${selected}" onclick="selectWizardOption('${step.key}','${opt.value}', this)">
                    <div class="wizard-option-icon">${opt.icon}</div>
                    <div class="wizard-option-text">
                        <div class="wizard-option-label">${opt.label}</div>
                        ${opt.desc ? `<div class="wizard-option-desc">${opt.desc}</div>` : ""}
                    </div>
                </div>`;
        });
        content += "</div>";
    }

    content += `<div class="wizard-nav">
        ${wizardStep > 0 ? '<button class="btn btn-ghost" onclick="prevWizardStep()">Back</button>' : "<div></div>"}
        <button class="btn btn-primary" id="wizard-next-btn" onclick="nextWizardStep()">${wizardStep === total - 1 ? "Get My Profile" : "Next"}</button>
    </div>`;

    document.getElementById("wizard-content").innerHTML = content;
}

function renderInvestmentAmountsStep() {
    const style = wizardAnswers.investment_style || "both";
    const showLump = style === "lump_sum" || style === "both";
    const showMonthly = style === "monthly" || style === "both";

    const lumpVal = wizardAnswers.initial_investment || 0;
    const monthVal = wizardAnswers.monthly_investment || 0;

    let html = '<div class="investment-amounts">';

    if (showLump) {
        html += `
            <div class="amount-input-group">
                <label class="amount-label">
                    <span class="amount-label-icon">💎</span>
                    Initial Investment
                </label>
                <div class="amount-input-wrapper">
                    <span class="amount-prefix">$</span>
                    <input type="number" id="input-initial" class="amount-input"
                        value="${lumpVal || ''}" min="100" step="1000"
                        placeholder="e.g. 50,000"
                        oninput="updateInvestmentSummary()">
                </div>
                <div class="amount-presets">
                    <button class="amount-preset" onclick="setAmount('initial', 10000)">$10K</button>
                    <button class="amount-preset" onclick="setAmount('initial', 50000)">$50K</button>
                    <button class="amount-preset" onclick="setAmount('initial', 100000)">$100K</button>
                    <button class="amount-preset" onclick="setAmount('initial', 500000)">$500K</button>
                    <button class="amount-preset" onclick="setAmount('initial', 1000000)">$1M</button>
                </div>
            </div>`;
    }

    if (showMonthly) {
        html += `
            <div class="amount-input-group">
                <label class="amount-label">
                    <span class="amount-label-icon">🔄</span>
                    Monthly Contribution
                </label>
                <div class="amount-input-wrapper">
                    <span class="amount-prefix">$</span>
                    <input type="number" id="input-monthly" class="amount-input"
                        value="${monthVal || ''}" min="0" step="100"
                        placeholder="e.g. 1,000"
                        oninput="updateInvestmentSummary()">
                </div>
                <div class="amount-presets">
                    <button class="amount-preset" onclick="setAmount('monthly', 250)">$250</button>
                    <button class="amount-preset" onclick="setAmount('monthly', 500)">$500</button>
                    <button class="amount-preset" onclick="setAmount('monthly', 1000)">$1K</button>
                    <button class="amount-preset" onclick="setAmount('monthly', 2500)">$2.5K</button>
                    <button class="amount-preset" onclick="setAmount('monthly', 5000)">$5K</button>
                </div>
            </div>`;
    }

    html += '<div class="investment-summary" id="investment-summary"></div>';
    html += '</div>';
    return html;
}

function setAmount(type, value) {
    const inputId = type === "initial" ? "input-initial" : "input-monthly";
    const el = document.getElementById(inputId);
    if (el) { el.value = value; updateInvestmentSummary(); }
}

function updateInvestmentSummary() {
    const style = wizardAnswers.investment_style || "both";
    const initialEl = document.getElementById("input-initial");
    const monthlyEl = document.getElementById("input-monthly");
    const initial = initialEl ? parseFloat(initialEl.value) || 0 : 0;
    const monthly = monthlyEl ? parseFloat(monthlyEl.value) || 0 : 0;

    const summaryEl = document.getElementById("investment-summary");
    if (!summaryEl) return;

    const yr1 = initial + (monthly * 12);
    const yr5 = initial + (monthly * 60);

    if (yr1 === 0) {
        summaryEl.innerHTML = '<span class="summary-hint">Enter an amount above</span>';
        return;
    }

    let html = '<div class="summary-grid">';
    if (initial > 0) html += `<div class="summary-item"><span class="summary-label">Starting with</span><span class="summary-value">${fmt(initial)}</span></div>`;
    if (monthly > 0) html += `<div class="summary-item"><span class="summary-label">Monthly</span><span class="summary-value">${fmt(monthly)}/mo</span></div>`;
    html += `<div class="summary-item"><span class="summary-label">Year 1 total</span><span class="summary-value">${fmt(yr1)}</span></div>`;
    if (monthly > 0) html += `<div class="summary-item"><span class="summary-label">Year 5 total</span><span class="summary-value">${fmt(yr5)}</span></div>`;
    html += '</div>';

    summaryEl.innerHTML = html;
}

function selectWizardOption(key, value, el) {
    wizardAnswers[key] = value;
    document.querySelectorAll(".wizard-option").forEach((o) => o.classList.remove("selected"));
    el.classList.add("selected");
}

function prevWizardStep() {
    if (wizardStep > 0) { wizardStep--; renderWizardStep(); }
}

async function nextWizardStep() {
    const step = WIZARD_STEPS[wizardStep];

    if (step.type === "investment_amounts") {
        const initialEl = document.getElementById("input-initial");
        const monthlyEl = document.getElementById("input-monthly");
        wizardAnswers.initial_investment = initialEl ? parseFloat(initialEl.value) || 0 : 0;
        wizardAnswers.monthly_investment = monthlyEl ? parseFloat(monthlyEl.value) || 0 : 0;

        if (wizardAnswers.initial_investment === 0 && wizardAnswers.monthly_investment === 0) {
            alert("Please enter at least one investment amount.");
            return;
        }
        wizardAnswers._investment_amounts = true;
    } else if (!wizardAnswers[step.key]) {
        alert("Please make a selection before continuing.");
        return;
    }

    if (wizardStep < WIZARD_STEPS.length - 1) {
        wizardStep++;
        renderWizardStep();
    } else {
        await submitProfile();
    }
}

async function submitProfile() {
    document.getElementById("wizard-content").innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Analyzing your risk profile...</p></div>';

    const payload = {
        goal: wizardAnswers.goal,
        timeline: wizardAnswers.timeline,
        investment_style: wizardAnswers.investment_style,
        initial_investment: wizardAnswers.initial_investment || 0,
        monthly_investment: wizardAnswers.monthly_investment || 0,
        experience: wizardAnswers.experience,
        risk_reaction: wizardAnswers.risk_reaction,
        income_stability: wizardAnswers.income_stability,
    };

    const result = await api.post("/api/profile", payload);

    document.getElementById("wizard-container").style.display = "none";
    document.getElementById("profile-result").style.display = "block";
    renderProfileResult(result);
}

function renderProfileResult(profile) {
    const colors = {
        "Very Conservative": "#22c55e",
        "Conservative": "#10b981",
        "Moderate": "#3b82f6",
        "Growth": "#f97316",
        "Aggressive": "#ef4444",
    };
    const color = colors[profile.profile_label] || "#6366f1";
    const angle = (profile.risk_score / 10) * 180;

    const investParts = [];
    if (profile.initial_investment > 0) investParts.push(fmt(profile.initial_investment) + " initial");
    if (profile.monthly_investment > 0) investParts.push(fmt(profile.monthly_investment) + "/mo");
    const investStr = investParts.join(" + ") || "Not specified";

    const styleLabels = { lump_sum: "One-time", monthly: "Monthly", both: "Lump sum + Monthly" };

    document.getElementById("profile-result").innerHTML = `
        <div class="profile-result-card">
            <h2>Your Risk Profile</h2>
            <div class="risk-gauge">
                <div class="gauge-arc">
                    <svg viewBox="0 0 200 120" class="gauge-svg">
                        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="var(--border)" stroke-width="12" stroke-linecap="round"/>
                        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="${color}" stroke-width="12" stroke-linecap="round"
                            stroke-dasharray="${(angle / 180) * 251.3} 251.3"/>
                    </svg>
                    <div class="gauge-label" style="color:${color}">${profile.risk_score}/10</div>
                </div>
                <div class="gauge-profile" style="color:${color}">${profile.profile_label}</div>
            </div>
            <div class="profile-details">
                <div class="detail-row"><span>Goal</span><span>${profile.goal.replace(/_/g, " ")}</span></div>
                <div class="detail-row"><span>Timeline</span><span>${profile.timeline.replace(/_/g, " ")}</span></div>
                <div class="detail-row"><span>Strategy</span><span>${styleLabels[profile.investment_style] || profile.investment_style}</span></div>
                <div class="detail-row"><span>Investment</span><span>${investStr}</span></div>
                <div class="detail-row"><span>Experience</span><span>${profile.experience}</span></div>
            </div>
            <div class="profile-actions">
                <button class="btn btn-primary" onclick="navigateTo('recommendations')">View Recommendations</button>
                <button class="btn btn-ghost" onclick="retakeProfile()">Retake Quiz</button>
            </div>
        </div>`;
}

function retakeProfile() {
    wizardStep = 0;
    Object.keys(wizardAnswers).forEach((k) => delete wizardAnswers[k]);
    document.getElementById("profile-result").style.display = "none";
    document.getElementById("wizard-container").style.display = "block";
    renderWizardStep();
}
