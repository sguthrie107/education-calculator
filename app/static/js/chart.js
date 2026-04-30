// Family Education Dashboard — Chart.js and UI logic

let chartInstance = null;
let allChildrenData = [];
let householdLoanData = null;
const childSectionCollapsedState = new Map();
let deductionModeEnabled = false;
let deductionPathKey = 'direct_4yr';

const stressTierStyles = {
    5: { color: '#166534', bg: '#DCFCE7', border: '#86EFAC' },
    4: { color: '#3F6212', bg: '#ECFCCB', border: '#BEF264' },
    3: { color: '#92400E', bg: '#FEF3C7', border: '#FCD34D' },
    2: { color: '#9A3412', bg: '#FFEDD5', border: '#FDBA74' },
    1: { color: '#991B1B', bg: '#FEE2E2', border: '#FCA5A5' },
};

if (window.Chart) {
    Chart.defaults.font.family = 'Montserrat, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
    Chart.defaults.color = '#5C3D2E';
}

// Distinct color palette per child
const childColors = [
    { border: '#8E3A62', bg: 'rgba(142, 58, 98, 0.12)', actual: '#B9487B' },
    { border: '#C8A44D', bg: 'rgba(200, 164, 77, 0.14)', actual: '#A08030' },
    { border: '#2563EB', bg: 'rgba(37, 99, 235, 0.10)', actual: '#1D4ED8' },
];

const fmt = (n) => '$' + Math.round(n).toLocaleString();
const fmtYear = (n) => {
    if (!Number.isFinite(n)) return '';
    const rounded = Math.round(n);
    if (Math.abs(n - rounded) < 0.01) return String(rounded);
    return n.toFixed(2);
};

function formatTimestamp(timestamp) {
    if (!timestamp) return '—';
    try {
        let isoString = String(timestamp);
        if (!isoString.includes('Z') && !isoString.includes('+') && !isoString.includes('-', 10)) {
            isoString += 'Z';
        }
        const date = new Date(isoString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
        });
    } catch (_error) {
        return String(timestamp);
    }
}

function renderSplitLegend(datasets) {
    const accountsTarget = document.getElementById('legend529');
    const loansTarget = document.getElementById('legendLoans');
    if (!accountsTarget || !loansTarget) return;

    const toItem = (dataset) => {
        const color = dataset.borderColor || dataset.backgroundColor || '#8E3A62';
        const dashed = Array.isArray(dataset.borderDash) && dataset.borderDash.length > 0;
        const isPointOnly = dataset.showLine === false;
        const style = isPointOnly
            ? `style="background:${color};"`
            : `style="border-top-color:${color};${dashed ? 'border-top-style:dashed;' : ''}"`;
        const swatchClass = isPointOnly ? 'legend-swatch dot' : 'legend-swatch';
        return `<span class="legend-item"><span class="${swatchClass}" ${style}></span>${dataset.label}</span>`;
    };

    const accountItems = datasets
        .filter(ds => ds.datasetType === 'education')
        .map(toItem)
        .join('');
    const loanItems = datasets
        .filter(ds => ds.datasetType === 'loan')
        .map(toItem)
        .join('');

    accountsTarget.innerHTML = accountItems || '<span class="legend-item">No 529 series</span>';
    loansTarget.innerHTML = loanItems || '<span class="legend-item">No loan payoff series</span>';
}

// ── Chart rendering ────────────────────────────────────────────

function renderAllChildrenChart(childrenData, householdLoanProjection = null) {
    allChildrenData = childrenData;
    householdLoanData = householdLoanProjection;
    const canvas = document.getElementById('educationChart');
    if (!canvas) return;

    if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
    }

    const datasets = [];
    const allXValues = [];

    childrenData.forEach((child, idx) => {
        const color = childColors[idx % childColors.length];
        const projectedRows = child.projected || [];
        let projectedPoints = projectedRows.map(p => ({
            x: Number(p.year),
            y: Number(p.balance),
        }));

        if (deductionModeEnabled) {
            const scenarios = child.withdrawal_scenarios?.scenarios || {};
            const selectedScenario = scenarios[deductionPathKey];
            const withdrawalTimeline = selectedScenario?.balance_timeline;

            if (Array.isArray(withdrawalTimeline) && withdrawalTimeline.length > 0) {
                const collegeStartYear = Number(selectedScenario.college_start_year);
                const preCollegePoints = projectedRows
                    .filter(p => Number(p.year) < collegeStartYear)
                    .map(p => ({ x: Number(p.year), y: Number(p.balance) }));
                const withdrawalPoints = withdrawalTimeline.map(point => ({
                    x: Number(point.year),
                    y: Number(point.balance),
                }));

                projectedPoints = [...preCollegePoints, ...withdrawalPoints];
            }
        }

        projectedPoints.forEach(point => allXValues.push(point.x));

        // Projected line
        datasets.push({
            label: child.child_name + ' (Projected)',
            data: projectedPoints,
            datasetType: 'education',
            borderColor: color.border,
            backgroundColor: color.bg,
            borderWidth: 2.5,
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 6,
            spanGaps: false,
        });

        // Actual dots (if any)
        if (child.actual && child.actual.length > 0) {
            const actualPoints = child.actual.map(a => ({
                x: Number(a.year),
                y: Number(a.balance),
            }));
            actualPoints.forEach(point => allXValues.push(point.x));
            datasets.push({
                label: child.child_name + ' (Actual)',
                data: actualPoints,
                datasetType: 'education',
                borderColor: color.actual,
                backgroundColor: color.actual,
                borderWidth: 0,
                pointRadius: 7,
                pointHoverRadius: 9,
                pointStyle: 'rectRounded',
                showLine: false,
                spanGaps: false,
            });
        }
    });

    if (householdLoanProjection) {
        // Plot actual loan balance dots if any exist
        const actualLoanBalances = Array.isArray(householdLoanProjection.actual_balances)
            ? householdLoanProjection.actual_balances
            : [];
        if (actualLoanBalances.length > 0) {
            const actualLoanPoints = actualLoanBalances.map(a => ({
                x: Number(a.fractional_year),
                y: Number(a.balance),
            }));
            actualLoanPoints.forEach(point => allXValues.push(point.x));
            datasets.push({
                label: 'Student Loan (Actual)',
                data: actualLoanPoints,
                datasetType: 'loan',
                borderColor: '#7C3AED',
                backgroundColor: '#7C3AED',
                borderWidth: 0,
                pointRadius: 7,
                pointHoverRadius: 9,
                pointStyle: 'rectRounded',
                showLine: false,
                spanGaps: false,
            });
        }

        const scenarioLines = Array.isArray(householdLoanProjection.scenarios)
            ? householdLoanProjection.scenarios
            : (householdLoanProjection.scenario ? [householdLoanProjection.scenario] : []);

        const loanScenarioStyles = {
            1500: { color: '#DC2626', dash: [10, 6], width: 2 },
            2000: { color: '#0891B2', dash: [8, 6], width: 2 },
            2500: { color: '#16A34A', dash: [4, 4], width: 2.3 },
        };

        scenarioLines.forEach((scenario) => {
            const payment = Math.round(Number(scenario.monthly_payment_total || 0));
            const style = loanScenarioStyles[payment] || { color: '#4B5563', dash: [8, 6], width: 2 };
            const lineData = (scenario.years || []).map(point => ({
                x: Number(point.year),
                y: Number(point.balance),
            }));
            lineData.forEach(point => allXValues.push(point.x));

            datasets.push({
                label: `Student Loan Balance ($${payment.toLocaleString()}/mo)`,
                data: lineData,
                datasetType: 'loan',
                borderColor: style.color,
                borderDash: style.dash,
                backgroundColor: 'rgba(0, 0, 0, 0)',
                borderWidth: style.width,
                fill: false,
                tension: 0.2,
                pointRadius: 2,
                pointHoverRadius: 5,
                spanGaps: false,
            });
        });
    }

    const minX = allXValues.length ? Math.min(...allXValues) : new Date().getFullYear();
    const maxX = allXValues.length ? Math.max(...allXValues) : minX + 1;
    const yearSpan = Math.ceil(maxX) - Math.floor(minX);
    const yearStep = yearSpan <= 30 ? 1 : (yearSpan <= 60 ? 2 : 5);

    renderSplitLegend(datasets);

    // Add phase boundary annotations via vertical dashed segments
    const ctx = canvas.getContext('2d');
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'x', intersect: false },
            layout: {
                padding: {
                    top: 12,
                    left: 28,
                    right: 10,
                },
            },
            datasets: {
                line: {
                    clip: 10,
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    mode: 'x',
                    intersect: false,
                    backgroundColor: 'rgba(45, 24, 16, 0.92)',
                    titleColor: '#FFF8F0',
                    bodyColor: '#F0D9C6',
                    borderColor: '#C8A44D',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        title: function(context) {
                            if (!context || context.length === 0) return '';
                            return 'Year ' + fmtYear(Number(context[0].parsed.x));
                        },
                        label: function(context) {
                            if (context.parsed.y == null) return null;
                            return context.dataset.label + ': ' + fmt(context.parsed.y) + ' @ ' + fmtYear(context.parsed.x);
                        },
                    },
                },
            },
            scales: {
                x: {
                    type: 'linear',
                    min: Math.floor(minX),
                    max: Math.ceil(maxX),
                    grid: { color: 'rgba(232, 221, 208, 0.5)' },
                    ticks: {
                        font: { size: 12, weight: '500' },
                        autoSkip: false,
                        stepSize: yearStep,
                        maxRotation: 0,
                        minRotation: 0,
                        callback: function(value) { return fmtYear(Number(value)); },
                    },
                },
                y: {
                    grid: { color: 'rgba(232, 221, 208, 0.5)' },
                    ticks: {
                        font: { size: 12, weight: '500' },
                        callback: function(value) { return fmt(value); },
                    },
                },
            },
        },
    });
}

function renderSingleChildChart(childData, householdLoanProjection = null) {
    renderAllChildrenChart([childData], householdLoanProjection);
}

// ── View toggle ────────────────────────────────────────────────

function onChildSelectionChange() {
    const sel = document.getElementById('childSelect').value;
    if (sel === 'all') {
        // Reload all children
        fetch('/api/comparison-all')
            .then(r => r.json())
            .then(data => {
                allChildrenData = data.children;
                householdLoanData = data.household_loan || householdLoanData;
                renderAllChildrenChart(data.children, householdLoanData);
                renderPhaseCards(data.children);
                renderSnapshotCards(data.children, householdLoanData);
                renderFundingBreakdown(data.children);
                renderAllDeltaTables(data.children);
                renderLoanHistory(householdLoanData);
                renderStressTestHintForAllChildren();
            })
            .catch((error) => {
                const stressContent = document.getElementById('stressTestContent');
                if (stressContent) {
                    stressContent.innerHTML = `<p class="loading" style="color: #9A3412;">Unable to load data: ${error.message}</p>`;
                }
            });
    } else {
        fetch('/api/comparison/' + encodeURIComponent(sel))
            .then(r => r.json())
            .then(data => {
                allChildrenData = [data];
                renderSingleChildChart(data, householdLoanData);
                renderPhaseCards([data]);
                renderSnapshotCards([data], householdLoanData);
                renderFundingBreakdown([data]);
                renderAllDeltaTables([data]);
                renderLoanHistory(householdLoanData);
                loadStressTestResult(sel);
            })
            .catch((error) => {
                const stressContent = document.getElementById('stressTestContent');
                if (stressContent) {
                    stressContent.innerHTML = `<p class="loading" style="color: #9A3412;">Unable to load child data: ${error.message}</p>`;
                }
            });
    }
}

function renderStressTestHintForAllChildren() {
    const stressContent = document.getElementById('stressTestContent');
    const recalcBtn = document.getElementById('recalculateStressBtn');
    if (!stressContent) return;

    if (recalcBtn) {
        recalcBtn.disabled = false;
        recalcBtn.title = 'Select a specific child to run stress testing.';
        recalcBtn.textContent = 'Recalculate Stress Test';
    }

    stressContent.innerHTML = `
        <div class="stress-empty">
            <p>Stress testing runs one fund at a time.</p>
            <p>Select a specific child to load or recalculate their 4-year college Monte Carlo result.</p>
            <p>Clicking <strong>Recalculate Stress Test</strong> while viewing all children will keep this reminder visible.</p>
        </div>
    `;
}

async function loadStressTestResult(childName) {
    const stressContent = document.getElementById('stressTestContent');
    const recalcBtn = document.getElementById('recalculateStressBtn');
    if (!stressContent || !childName || childName === 'all') {
        return;
    }

    if (recalcBtn) {
        recalcBtn.disabled = false;
        recalcBtn.title = '';
    }

    stressContent.innerHTML = '<p class="loading">Loading latest stress test...</p>';

    try {
        const response = await fetch(`/api/stress-test/${encodeURIComponent(childName)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const payload = await response.json();
        renderStressTestResult(payload.result, childName);
    } catch (error) {
        stressContent.innerHTML = `<p class="loading" style="color: #9A3412;">Unable to load stress test: ${error.message}</p>`;
    }
}

function renderStressTestResult(result, childName) {
    const stressContent = document.getElementById('stressTestContent');
    if (!stressContent) return;

    if (!result) {
        stressContent.innerHTML = `
            <div class="stress-empty">
                <p>No stress test is stored yet for ${childName}.</p>
                <p>Run <strong>Recalculate Stress Test</strong> to generate the latest Monte Carlo result.</p>
            </div>
        `;
        return;
    }

    const probability = Number(result.success_probability_pct || 0);
    const markerLeft = Math.max(0, Math.min(100, probability));
    const tier = Number(result.rating_tier || 1);
    const tierStyle = stressTierStyles[tier] || stressTierStyles[1];

    stressContent.innerHTML = `
        <div class="stress-card">
            <div class="stress-card-top">
                <div class="stress-score">
                    <span class="stress-score-percent" style="color: ${tierStyle.color};">${probability.toFixed(1)}%</span>
                    <span class="stress-rating-chip" style="color: ${tierStyle.color}; background: ${tierStyle.bg}; border-color: ${tierStyle.border};">
                        ${result.rating_grade} · ${result.rating_label}
                    </span>
                </div>
            </div>

            <div class="stress-gauge" aria-label="Probability of fully paying for 4-year college">
                <div class="stress-gauge-track">
                    <div class="stress-gauge-marker" style="left: ${markerLeft}%;"></div>
                </div>
                <div class="stress-ticks">
                    <span class="tick-edge-left" style="left: 0%;">0%</span>
                    <span style="left: 60%;">60%</span>
                    <span style="left: 75%;">75%</span>
                    <span style="left: 85%;">85%</span>
                    <span style="left: 92%;">92%</span>
                    <span class="tick-edge-right" style="left: 100%;">100%</span>
                </div>
            </div>

            <div class="stress-meta">
                <div class="stress-meta-item">
                    <span class="stress-meta-label">Simulations</span>
                    <span class="stress-meta-value">${Number(result.simulation_count || 0).toLocaleString()}</span>
                </div>
                <div class="stress-meta-item">
                    <span class="stress-meta-label">Expected Return</span>
                    <span class="stress-meta-value">${Number(result.mean_return_pct || 0).toFixed(2)}%</span>
                </div>
                <div class="stress-meta-item">
                    <span class="stress-meta-label">Volatility</span>
                    <span class="stress-meta-value">${Number(result.volatility_pct || 0).toFixed(2)}%</span>
                </div>
                <div class="stress-meta-item">
                    <span class="stress-meta-label">Inflation</span>
                    <span class="stress-meta-value">${Number(result.inflation_pct || 0).toFixed(2)}%</span>
                </div>
                <div class="stress-meta-item">
                    <span class="stress-meta-label">P50 Terminal Balance</span>
                    <span class="stress-meta-value">${fmt(Number(result.p50_terminal_balance || 0))}</span>
                </div>
                <div class="stress-meta-item">
                    <span class="stress-meta-label">Last Calculated</span>
                    <span class="stress-meta-value">${formatTimestamp(result.created_at)}</span>
                </div>
            </div>
        </div>
    `;
}

async function recalculateStressTest() {
    const select = document.getElementById('childSelect');
    const childName = select ? String(select.value || '') : '';
    const stressContent = document.getElementById('stressTestContent');
    const btn = document.getElementById('recalculateStressBtn');

    if (!childName || childName === 'all') {
        renderStressTestHintForAllChildren();
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Running Monte Carlo...';
    }
    if (stressContent) {
        stressContent.innerHTML = '<p class="loading">Running stress test simulation...</p>';
    }

    try {
        const response = await fetch(`/api/stress-test/${encodeURIComponent(childName)}/recalculate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ simulation_count: 10000 }),
        });
        if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.detail || `HTTP ${response.status}`);
        }
        const payload = await response.json();
        renderStressTestResult(payload.result, childName);
    } catch (error) {
        if (stressContent) {
            stressContent.innerHTML = `<p class="loading" style="color: #9A3412;">Unable to recalculate: ${error.message}</p>`;
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Recalculate Stress Test';
        }
    }
}

function onDeductionToggleChange() {
    const toggle = document.getElementById('deductionToggle');
    const pathSelect = document.getElementById('deductionPathSelect');
    deductionModeEnabled = Boolean(toggle?.checked);
    if (pathSelect) pathSelect.disabled = !deductionModeEnabled;
    renderAllChildrenChart(allChildrenData, householdLoanData);
    renderFundingBreakdown(allChildrenData);
}

function onDeductionPathChange() {
    const pathSelect = document.getElementById('deductionPathSelect');
    deductionPathKey = pathSelect?.value || 'direct_4yr';
    renderAllChildrenChart(allChildrenData, householdLoanData);
    renderFundingBreakdown(allChildrenData);
}

function renderFundingBreakdown(childrenData) {
    const container = document.getElementById('fundingBreakdownCards');
    if (!container) return;

    if (!childrenData || !childrenData.length) {
        container.innerHTML = '<p class="loading">No funding breakdown available</p>';
        return;
    }

    const percent = (value) => `${Number(value || 0).toFixed(1)}%`;

    const cardHtml = childrenData.map((child) => {
        const scenarios = child.withdrawal_scenarios?.scenarios || {};
        const direct = scenarios.direct_4yr?.summary;
        const blended = scenarios.blended_2plus2?.summary;

        const scenarioRow = (title, summary) => {
            if (!summary) {
                return `<div class="snapshot-item"><span class="snapshot-label">${title}</span><span class="snapshot-value">N/A</span></div>`;
            }
            return `
                <div class="snapshot-item"><span class="snapshot-label">${title} Paid by 529</span><span class="snapshot-value">${fmt(summary.paid_by_529 || 0)} (${percent(summary.percent_paid_by_529)})</span></div>
                <div class="snapshot-item"><span class="snapshot-label">${title} Remaining</span><span class="snapshot-value">${fmt(summary.remaining_cost || 0)}</span></div>
            `;
        };

        return `
            <div class="snapshot-card snapshot-card-funding">
                <h3>${child.child_name}</h3>
                <div class="snapshot-grid">
                    ${scenarioRow('University (4-Year)', direct)}
                    ${scenarioRow('Community College + University', blended)}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = cardHtml;
}

// ── Phase allocation cards ─────────────────────────────────────

function renderPhaseCards(childrenData) {
    const container = document.getElementById('phaseCards');
    if (!container) return;

    // Just show phases from first child (they're identical across children)
    const child = childrenData[0];
    if (!child || !child.projected || !child.projected.length) {
        container.innerHTML = '<p class="loading">No projection data</p>';
        return;
    }

    // Derive phases from the projected data
    const phases = [
        { key: 'phase_1', name: 'Aggressive Growth', ages: 'Age 0–12', cssClass: 'phase-1' },
        { key: 'phase_2', name: 'Moderate Growth', ages: 'Age 13–17', cssClass: 'phase-2' },
        { key: 'phase_3', name: 'Conservative', ages: 'Age 18–20', cssClass: 'phase-3' },
    ];

    const allocations = {
        phase_1: [
            { label: 'Vanguard Total US Stock Market', pct: 70, ticker: 'VTSAX' },
            { label: 'Vanguard Total Intl Stock Market', pct: 30, ticker: 'VTIAX' },
        ],
        phase_2: [
            { label: 'Vanguard Total US Stock Market', pct: 60, ticker: 'VTSAX' },
            { label: 'Vanguard Total Intl Stock Market', pct: 20, ticker: 'VTIAX' },
            { label: 'Vanguard Total US Bond Market', pct: 20, ticker: 'VBTLX' },
        ],
        phase_3: [
            { label: 'Vanguard Total US Stock Market', pct: 40, ticker: 'VTSAX' },
            { label: 'Vanguard Total Intl Stock Market', pct: 20, ticker: 'VTIAX' },
            { label: 'Vanguard Total US Bond Market', pct: 40, ticker: 'VBTLX' },
        ],
    };

    let html = '';
    phases.forEach(ph => {
        const alloc = allocations[ph.key] || [];
        html += `<div class="phase-card">
            <div class="phase-card-title">${ph.name}</div>
            <div class="phase-card-subtitle">${ph.ages}</div>`;
        alloc.forEach(a => {
            html += `<div class="alloc-row">
                <span class="alloc-label">${a.label}</span>
                <span class="alloc-pct">${a.pct}%</span>
                <span class="alloc-ticker">${a.ticker}</span>
            </div>`;
        });
        html += '</div>';
    });
    container.innerHTML = html;
}

// ── Snapshot cards ──────────────────────────────────────────────

function renderSnapshotCards(childrenData, householdLoanProjection = null) {
    const container = document.getElementById('snapshotCards');
    if (!container) return;
    if (!childrenData || !childrenData.length) {
        container.innerHTML = '<p class="loading">No snapshot data available</p>';
        return;
    }

    let html = '';
    childrenData.forEach((child) => {
        const finalPoint = child.projected?.[child.projected.length - 1];
        const firstPoint = child.projected?.[0];
        const inflationText = child.inflation_rate_pct ? `${child.inflation_rate_pct.toFixed(2)}%` : '3.00%';

        html += `<div class="snapshot-card">
            <h3>${child.child_name}</h3>
            <div class="snapshot-grid">
                <div class="snapshot-item">
                    <span class="snapshot-label">Birth Year</span>
                    <span class="snapshot-value">${child.birth_year}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Initial (2026 $)</span>
                    <span class="snapshot-value">${fmt(child.initial_investment_2026 || 2500)}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Initial (Nominal)</span>
                    <span class="snapshot-value">${fmt(child.initial_investment_nominal || firstPoint?.contributions_ytd || 2500)}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Inflation Rate</span>
                    <span class="snapshot-value">${inflationText}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Projected at Age 20</span>
                    <span class="snapshot-value">${fmt(finalPoint?.balance || 0)}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Total Contributions</span>
                    <span class="snapshot-value">${fmt(finalPoint?.contributions_ytd || 0)}</span>
                </div>
            </div>
        </div>`;
    });

    if (householdLoanProjection && householdLoanProjection.scenario) {
        const scenario = householdLoanProjection.scenario;
        const loanScenarios = Array.isArray(householdLoanProjection.scenarios)
            ? householdLoanProjection.scenarios
            : [scenario];
        const exampleSummary = loanScenarios
            .map(item => {
                const payment = Math.round(Number(item.monthly_payment_total || 0));
                const payoffYear = Number(item.payoff_year_estimate || 0);
                const payoffLabel = payoffYear > 0 ? fmtYear(payoffYear) : 'N/A';
                return `<div class="snapshot-item"><span class="snapshot-label">$${payment.toLocaleString()}/mo Payoff</span><span class="snapshot-value">${payoffLabel}</span></div>`;
            })
            .join('');

        html += `<div class="snapshot-card snapshot-card-household">
            <h3>Household Student Loan</h3>
            <div class="snapshot-grid">
                <div class="snapshot-item">
                    <span class="snapshot-label">Starting Balance</span>
                    <span class="snapshot-value">${fmt(householdLoanProjection.principal || 60000)}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Interest Rate</span>
                    <span class="snapshot-value">${((householdLoanProjection.annual_interest_rate || 0.05) * 100).toFixed(2)}%</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Monthly Payment (Assumed)</span>
                    <span class="snapshot-value">${fmt(householdLoanProjection.assumed_total_monthly_payment || 2000)}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Projected Payoff Year</span>
                    <span class="snapshot-value">${fmtYear(Number(scenario.payoff_year_estimate || 0))}</span>
                </div>
                <div class="snapshot-item">
                    <span class="snapshot-label">Months to Payoff</span>
                    <span class="snapshot-value">${scenario.months_to_payoff || 0} months</span>
                </div>
                ${exampleSummary}
            </div>
        </div>`;
    }

    container.innerHTML = html;
}

// ── Delta / comparison tables ──────────────────────────────────

function renderAllDeltaTables(childrenData) {
    const container = document.getElementById('deltaContent');
    if (!container) return;

    if (!childrenData || !childrenData.length) {
        container.innerHTML = '<p class="loading">No data available</p>';
        return;
    }

    let html = '';
    childrenData.forEach((child) => {
        html += renderChildDeltaBlock(child);
    });
    container.innerHTML = html;
}

function renderChildDeltaBlock(child) {
    const phaseKeyFor = (phaseName) => {
        if (phaseName.includes('Aggressive') || phaseName.includes('0-12') || phaseName.includes('0–12')) return 'phase-1';
        if (phaseName.includes('Moderate') || phaseName.includes('13-17') || phaseName.includes('13–17')) return 'phase-2';
        return 'phase-3';
    };

    const childKey = `${child.child_name}-${child.birth_year}`;
    const blockId = 'child-delta-' + childKey.replace(/[^a-zA-Z0-9_-]/g, '-');
    const hasActualData = Array.isArray(child.actual) && child.actual.length > 0;
    const hasDeltaData = Array.isArray(child.deltas) && child.deltas.length > 0;
    const hasComparisonData = hasActualData || hasDeltaData;
    const isCollapsed = childSectionCollapsedState.has(childKey)
        ? childSectionCollapsedState.get(childKey)
        : !hasComparisonData;
    const arrow = isCollapsed ? '▸' : '▾';

    let html = `<div class="child-delta-block ${isCollapsed ? 'collapsed' : ''}" id="${blockId}" data-child-key="${childKey}">
        <div class="child-delta-header">
            <h3>${child.child_name} <span>(Born ${child.birth_year})</span></h3>
            <p>Initial: ${fmt(child.initial_investment_nominal || 2500)} nominal (${fmt(child.initial_investment_2026 || 2500)} in 2026 dollars)</p>
            <button
                type="button"
                class="child-toggle-btn"
                onclick="toggleChildDeltaBlock('${blockId}')"
                aria-expanded="${isCollapsed ? 'false' : 'true'}"
                title="${isCollapsed ? 'Expand section' : 'Collapse section'}"
            >${arrow}</button>
        </div>
        <div class="child-delta-content">
        <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Year</th>
                    <th>Age</th>
                    <th>Phase</th>
                    <th>Projected</th>
                    <th>Actual</th>
                    <th>Delta</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>`;

    // Build actual lookup
    const actualByYear = {};
    const deltaByYear = {};
    if (child.actual) child.actual.forEach(a => { actualByYear[a.year] = a; });
    if (child.deltas) child.deltas.forEach(d => { deltaByYear[d.year] = d; });

    child.projected.forEach(p => {
        const act = actualByYear[p.year];
        const delta = deltaByYear[p.year];
        const pk = phaseKeyFor(p.phase);
        const actualStr = act ? fmt(act.balance) : '—';
        let deltaStr = '—';
        let deltaClass = '';
        if (delta) {
            deltaStr = (delta.delta >= 0 ? '+' : '') + fmt(delta.delta) + ' (' + delta.delta_pct.toFixed(1) + '%)';
            deltaClass = delta.delta >= 0 ? 'positive' : 'negative';
        }

        const actionBtns = act
            ? `<div class="action-buttons">
                <button class="btn-edit" onclick="showEditBalanceForm(${act.id}, ${p.year}, ${act.balance}, '${(act.notes || '').replace(/'/g, "\\'")}')">✏️</button>
                <button class="btn-delete" onclick="deleteBalance(${act.id}, '${child.child_name}')">🗑️</button>
               </div>`
            : '';

        html += `<tr>
            <td>${p.year}</td>
            <td>${p.age}</td>
            <td><span class="phase-tag ${pk}">${p.phase}</span></td>
            <td>${fmt(p.balance)}</td>
            <td>${actualStr}</td>
            <td class="${deltaClass}">${deltaStr}</td>
            <td>${actionBtns}</td>
        </tr>`;
    });

    html += '</tbody></table></div></div></div>';
    return html;
}

function toggleChildDeltaBlock(blockId) {
    const block = document.getElementById(blockId);
    if (!block) return;

    const childKey = block.dataset.childKey;
    const btn = block.querySelector('.child-toggle-btn');
    const nowCollapsed = !block.classList.contains('collapsed');

    block.classList.toggle('collapsed', nowCollapsed);
    childSectionCollapsedState.set(childKey, nowCollapsed);

    if (btn) {
        btn.textContent = nowCollapsed ? '▸' : '▾';
        btn.setAttribute('aria-expanded', nowCollapsed ? 'false' : 'true');
        btn.setAttribute('title', nowCollapsed ? 'Expand section' : 'Collapse section');
    }
}

// ── Balance CRUD ───────────────────────────────────────────────

function showBalanceForm() {
    const yearSelect = document.getElementById('balanceYear');
    yearSelect.innerHTML = '<option value="">-- Select a year --</option>';
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= 2026; y--) {
        yearSelect.innerHTML += `<option value="${y}">${y}</option>`;
    }
    document.getElementById('balanceModal').style.display = 'flex';
}

function hideBalanceForm() {
    document.getElementById('balanceModal').style.display = 'none';
    document.getElementById('balanceForm').reset();
}

function submitBalance(e) {
    e.preventDefault();
    const childName = document.getElementById('balanceChild').value;
    const year = parseInt(document.getElementById('balanceYear').value);
    const balance = parseFloat(document.getElementById('balanceAmount').value);
    const notes = document.getElementById('balanceNotes').value || null;

    fetch('/api/balances/' + encodeURIComponent(childName), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year, balance, notes }),
    })
        .then(r => {
            if (!r.ok) return r.json().then(d => { throw new Error(d.detail || 'Save failed'); });
            return r.json();
        })
        .then(() => {
            hideBalanceForm();
            onChildSelectionChange(); // Refresh
        })
        .catch(err => alert(err.message));
}

function showEditBalanceForm(balanceId, year, balance, notes) {
    document.getElementById('editBalanceId').value = balanceId;
    document.getElementById('editYear').value = year;
    document.getElementById('editAmount').value = balance;
    document.getElementById('editNotes').value = notes || '';
    document.getElementById('editBalanceModal').style.display = 'flex';
}

function hideEditBalanceForm() {
    document.getElementById('editBalanceModal').style.display = 'none';
}

function submitEditBalance(e) {
    e.preventDefault();
    const balanceId = document.getElementById('editBalanceId').value;
    const balance = parseFloat(document.getElementById('editAmount').value);
    const notes = document.getElementById('editNotes').value || null;

    fetch('/api/balances/' + balanceId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ balance, notes }),
    })
        .then(r => {
            if (!r.ok) return r.json().then(d => { throw new Error(d.detail || 'Update failed'); });
            return r.json();
        })
        .then(() => {
            hideEditBalanceForm();
            onChildSelectionChange();
        })
        .catch(err => alert(err.message));
}

function deleteBalance(balanceId, childName) {
    if (!confirm('Delete this balance entry?')) return;

    fetch('/api/balances/' + balanceId, { method: 'DELETE' })
        .then(r => {
            if (!r.ok) throw new Error('Delete failed');
            onChildSelectionChange();
        })
        .catch(err => alert(err.message));
}

// ── Loan balance CRUD ──────────────────────────────────────────

const MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function renderLoanHistory(householdLoanProjection) {
    const container = document.getElementById('loanHistoryContent');
    if (!container) return;

    const entries = householdLoanProjection?.actual_balances || [];

    if (!entries.length) {
        container.innerHTML = '<p class="loading">No loan balance entries yet. Click <strong>Add Loan Balance</strong> to record your first entry.</p>';
        return;
    }

    let html = '<div class="table-wrap"><table><thead><tr>' +
        '<th>Month</th><th>Year</th><th>Balance</th><th>Notes</th><th>Recorded</th><th>Actions</th>' +
        '</tr></thead><tbody>';

    entries.forEach(entry => {
        const monthName = MONTH_NAMES[entry.month] || entry.month;
        html += `<tr>
            <td>${monthName}</td>
            <td>${entry.year}</td>
            <td>${fmt(entry.balance)}</td>
            <td>${entry.notes ? entry.notes.replace(/</g, '&lt;') : '—'}</td>
            <td>${formatTimestamp(entry.recorded_at)}</td>
            <td><div class="action-buttons">
                <button class="btn-edit" onclick="showEditLoanBalanceForm(${entry.id}, ${entry.year}, ${entry.month}, ${entry.balance}, '${(entry.notes || '').replace(/'/g, "\\'")}')">✏️</button>
                <button class="btn-delete" onclick="deleteLoanBalance(${entry.id})">🗑️</button>
            </div></td>
        </tr>`;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function showLoanBalanceForm() {
    const yearSelect = document.getElementById('loanBalanceYear');
    yearSelect.innerHTML = '';
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= 2020; y--) {
        yearSelect.innerHTML += `<option value="${y}"${y === currentYear ? ' selected' : ''}>${y}</option>`;
    }
    // Pre-select current month
    const currentMonth = new Date().getMonth() + 1;
    document.getElementById('loanBalanceMonth').value = String(currentMonth);
    document.getElementById('loanBalanceModal').style.display = 'flex';
}

function hideLoanBalanceForm() {
    document.getElementById('loanBalanceModal').style.display = 'none';
    document.getElementById('loanBalanceForm').reset();
}

function submitLoanBalance(e) {
    e.preventDefault();
    const year = parseInt(document.getElementById('loanBalanceYear').value);
    const month = parseInt(document.getElementById('loanBalanceMonth').value);
    const balance = parseFloat(document.getElementById('loanBalanceAmount').value);
    const notes = document.getElementById('loanBalanceNotes').value || null;

    fetch('/api/loan-balances', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year, month, balance, notes }),
    })
        .then(r => {
            if (!r.ok) return r.json().then(d => { throw new Error(d.detail || 'Save failed'); });
            return r.json();
        })
        .then(() => {
            hideLoanBalanceForm();
            refreshLoanData();
        })
        .catch(err => alert(err.message));
}

function showEditLoanBalanceForm(id, year, month, balance, notes) {
    document.getElementById('editLoanBalanceId').value = id;
    document.getElementById('editLoanPeriod').value = `${MONTH_NAMES[month] || month} ${year}`;
    document.getElementById('editLoanAmount').value = balance;
    document.getElementById('editLoanNotes').value = notes || '';
    document.getElementById('editLoanBalanceModal').style.display = 'flex';
}

function hideEditLoanBalanceForm() {
    document.getElementById('editLoanBalanceModal').style.display = 'none';
}

function submitEditLoanBalance(e) {
    e.preventDefault();
    const id = document.getElementById('editLoanBalanceId').value;
    const balance = parseFloat(document.getElementById('editLoanAmount').value);
    const notes = document.getElementById('editLoanNotes').value || null;

    fetch('/api/loan-balances/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ balance, notes }),
    })
        .then(r => {
            if (!r.ok) return r.json().then(d => { throw new Error(d.detail || 'Update failed'); });
            return r.json();
        })
        .then(() => {
            hideEditLoanBalanceForm();
            refreshLoanData();
        })
        .catch(err => alert(err.message));
}

function deleteLoanBalance(id) {
    if (!confirm('Delete this loan balance entry?')) return;

    fetch('/api/loan-balances/' + id, { method: 'DELETE' })
        .then(r => {
            if (!r.ok) throw new Error('Delete failed');
            refreshLoanData();
        })
        .catch(err => alert(err.message));
}

function refreshLoanData() {
    fetch('/api/comparison-all')
        .then(r => r.json())
        .then(data => {
            householdLoanData = data.household_loan || householdLoanData;
            renderLoanHistory(householdLoanData);
            // Redraw chart to update actual loan dots
            const sel = document.getElementById('childSelect');
            if (sel && sel.value !== 'all') {
                renderSingleChildChart(allChildrenData[0] || null, householdLoanData);
            } else {
                renderAllChildrenChart(allChildrenData, householdLoanData);
            }
            renderSnapshotCards(allChildrenData, householdLoanData);
        })
        .catch(err => alert('Failed to refresh loan data: ' + err.message));
}

// ── Expose on window for inline handlers ───────────────────────

window.renderAllChildrenChart = renderAllChildrenChart;
window.renderSingleChildChart = renderSingleChildChart;
window.onChildSelectionChange = onChildSelectionChange;
window.renderPhaseCards = renderPhaseCards;
window.renderSnapshotCards = renderSnapshotCards;
window.renderFundingBreakdown = renderFundingBreakdown;
window.renderAllDeltaTables = renderAllDeltaTables;
window.toggleChildDeltaBlock = toggleChildDeltaBlock;
window.onDeductionToggleChange = onDeductionToggleChange;
window.onDeductionPathChange = onDeductionPathChange;
window.renderStressTestHintForAllChildren = renderStressTestHintForAllChildren;
window.loadStressTestResult = loadStressTestResult;
window.recalculateStressTest = recalculateStressTest;
window.showBalanceForm = showBalanceForm;
window.hideBalanceForm = hideBalanceForm;
window.submitBalance = submitBalance;
window.showEditBalanceForm = showEditBalanceForm;
window.hideEditBalanceForm = hideEditBalanceForm;
window.submitEditBalance = submitEditBalance;
window.deleteBalance = deleteBalance;
window.renderLoanHistory = renderLoanHistory;
window.showLoanBalanceForm = showLoanBalanceForm;
window.hideLoanBalanceForm = hideLoanBalanceForm;
window.submitLoanBalance = submitLoanBalance;
window.showEditLoanBalanceForm = showEditLoanBalanceForm;
window.hideEditLoanBalanceForm = hideEditLoanBalanceForm;
window.submitEditLoanBalance = submitEditLoanBalance;
window.deleteLoanBalance = deleteLoanBalance;
window.refreshLoanData = refreshLoanData;
