// Family Education Dashboard — Chart.js and UI logic

let chartInstance = null;
let allChildrenData = [];
let householdLoanData = null;

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
        const projectedPoints = (child.projected || []).map(p => ({
            x: Number(p.year),
            y: Number(p.balance),
        }));
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
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    backgroundColor: 'rgba(45, 24, 16, 0.92)',
                    titleColor: '#FFF8F0',
                    bodyColor: '#F0D9C6',
                    borderColor: '#C8A44D',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
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
                renderAllDeltaTables(data.children);
            });
    } else {
        fetch('/api/comparison/' + encodeURIComponent(sel))
            .then(r => r.json())
            .then(data => {
                allChildrenData = [data];
                renderSingleChildChart(data, householdLoanData);
                renderPhaseCards([data]);
                renderSnapshotCards([data], householdLoanData);
                renderAllDeltaTables([data]);
            });
    }
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
                    <span class="snapshot-value">${fmt(householdLoanProjection.principal || 70000)}</span>
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

    let html = `<div class="child-delta-block">
        <div class="child-delta-header">
            <h3>${child.child_name} <span>(Born ${child.birth_year})</span></h3>
            <p>Initial: ${fmt(child.initial_investment_nominal || 2500)} nominal (${fmt(child.initial_investment_2026 || 2500)} in 2026 dollars)</p>
        </div>
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

    html += '</tbody></table></div></div>';
    return html;
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

// ── Expose on window for inline handlers ───────────────────────

window.renderAllChildrenChart = renderAllChildrenChart;
window.renderSingleChildChart = renderSingleChildChart;
window.onChildSelectionChange = onChildSelectionChange;
window.renderPhaseCards = renderPhaseCards;
window.renderSnapshotCards = renderSnapshotCards;
window.renderAllDeltaTables = renderAllDeltaTables;
window.showBalanceForm = showBalanceForm;
window.hideBalanceForm = hideBalanceForm;
window.submitBalance = submitBalance;
window.showEditBalanceForm = showEditBalanceForm;
window.hideEditBalanceForm = hideEditBalanceForm;
window.submitEditBalance = submitEditBalance;
window.deleteBalance = deleteBalance;
