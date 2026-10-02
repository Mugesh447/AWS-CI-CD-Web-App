const refreshButton = document.querySelector('#refresh-button');
const lastChecked = document.querySelector('#last-checked');
const serviceStatus = document.querySelector('#service-status');
const copyButton = document.querySelector('#copy-button');
const clock = document.querySelector('#live-clock');
const deploymentSearch = document.querySelector('#deployment-search');
const notificationButton = document.querySelector('#notification-button');
const notificationMenu = document.querySelector('#notification-menu');
const deploymentModal = document.querySelector('#deployment-modal');
const modalClose = document.querySelector('#modal-close');
const modalTitle = document.querySelector('#modal-title');
const modalCommit = document.querySelector('#modal-commit');
const modalStatus = document.querySelector('#modal-status');
const rollbackButton = document.querySelector('#rollback-button');
const rollbackMessage = document.querySelector('#rollback-message');
const statusFilter = document.querySelector('#status-filter');
const autoRefresh = document.querySelector('#auto-refresh');
const themeButton = document.querySelector('#theme-button');
const exportButton = document.querySelector('#export-button');
const togglePassword = document.querySelector('#toggle-password');
const authForm = document.querySelector('#auth-form');
const authTitle = document.querySelector('#auth-title');
const authDescription = document.querySelector('#auth-description');
const authSubmit = document.querySelector('#auth-submit');
const newDeploymentButton = document.querySelector('#new-deployment-button');
const newDeploymentModal = document.querySelector('#new-deployment-modal');
const newDeploymentClose = document.querySelector('#new-deployment-close');
const newDeploymentCancel = document.querySelector('#new-deployment-cancel');
const newDeploymentForm = document.querySelector('#new-deployment-form');
const deploymentMessage = document.querySelector('#deployment-message');
const progressView = document.querySelector('#progress-view');
const progressBar = document.querySelector('#progress-bar');
const progressPercent = document.querySelector('#progress-percent');
const progressStage = document.querySelector('#progress-stage');
const progressMessage = document.querySelector('#progress-message');
const logViewer = document.querySelector('#log-viewer');
const logSearch = document.querySelector('#log-search');
const logLevel = document.querySelector('#log-level');
const logCount = document.querySelector('#log-count');
const refreshLogs = document.querySelector('#refresh-logs');
const refreshDeployments = document.querySelector('#refresh-deployments');
const deploymentBody = document.querySelector('#deployment-body');
const copyLogs = document.querySelector('#copy-logs');
const refreshCosts = document.querySelector('#refresh-costs');
const currentCost = document.querySelector('#current-cost');
const costForecast = document.querySelector('#cost-forecast');
const costBudget = document.querySelector('#cost-budget');
const budgetPercent = document.querySelector('#budget-percent');
const budgetBar = document.querySelector('#budget-bar');
const costBreakdown = document.querySelector('#cost-breakdown');
const costTrend = document.querySelector('#cost-trend');
const runDiagnostics = document.querySelector('#run-diagnostics');
const diagnosticStatus = document.querySelector('#diagnostic-status');
const diagnosticTime = document.querySelector('#diagnostic-time');
const diagnosticPulse = document.querySelector('#diagnostic-pulse');
const diagnosticGrid = document.querySelector('#diagnostic-grid');
const addProjectButton = document.querySelector('#add-project-button');
const projectModal = document.querySelector('#project-modal');

document.querySelectorAll('.nav-item[href^="#"]').forEach((item) => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.nav-item[href^="#"]').forEach((navItem) => navItem.classList.remove('active'));
        item.classList.add('active');
    });
});

document.querySelectorAll('.person').forEach((person) => {
    person.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) node.textContent = node.textContent.replace('Mugesh Kumar', 'CloudEngineer');
    });
});
const projectClose = document.querySelector('#project-close');
const projectCancel = document.querySelector('#project-cancel');
const projectForm = document.querySelector('#project-form');
const projectMessage = document.querySelector('#project-message');
const metricsCanvas = document.querySelector('#metrics-chart');
const chartTooltip = document.querySelector('#chart-tooltip');
const chartResponse = document.querySelector('#chart-response');
const chartRequests = document.querySelector('#chart-requests');
let progressTimer;
let selectedDeploymentId = null;
let autoRefreshTimer;

if (!refreshButton) {
    togglePassword.addEventListener('click', () => {
        const password = document.querySelector('#password');
        const visible = password.type === 'text';
        password.type = visible ? 'password' : 'text';
        togglePassword.setAttribute('aria-label', visible ? 'Show password' : 'Hide password');
    });
    document.querySelectorAll('.auth-tab').forEach((tab) => {
        tab.addEventListener('click', () => {
            const registerMode = tab.dataset.mode === 'register';
            document.querySelectorAll('.auth-tab').forEach((item) => item.classList.toggle('active', item === tab));
            document.querySelectorAll('.register-only').forEach((section) => { section.hidden = !registerMode; });
            document.querySelector('#name').required = registerMode;
            document.querySelector('#email').required = registerMode;
            document.querySelector('#confirm-password').required = registerMode;
            document.querySelector('#password').minLength = registerMode ? 6 : 0;
            authForm.action = registerMode ? '/register' : '/login';
            authTitle.textContent = registerMode ? 'Create your account' : 'Sign in to your workspace';
            authDescription.textContent = registerMode ? 'Set up your developer profile for the deployment dashboard.' : 'Continue to the AWS CI/CD deployment dashboard.';
            authSubmit.innerHTML = `${registerMode ? 'Create account' : 'Sign in'} <span>→</span>`;
        });
    });
    authForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        authSubmit.disabled = true;
        authSubmit.innerHTML = 'Signing in... <span>◌</span>';
        const response = await fetch(authForm.action, { method: 'POST', body: new FormData(authForm), redirect: 'manual' });
        if (response.type === 'opaqueredirect' || response.status === 302 || response.ok) {
            window.location.href = '/';
            return;
        }
        const error = document.querySelector('.login-error') || document.createElement('div');
        error.className = 'login-error';
        error.setAttribute('role', 'alert');
        error.textContent = 'Username or password is incorrect. Try again.';
        if (!error.parentElement) authForm.parentElement.insertBefore(error, authForm);
        authSubmit.disabled = false;
        authSubmit.innerHTML = 'Sign in <span>→</span>';
    });
} else if (localStorage.getItem('dashboard-theme') === 'dark') {
    document.body.classList.add('dark');
}

if (refreshButton) {

function updateClock() {
    clock.textContent = new Intl.DateTimeFormat([], {
        dateStyle: 'medium',
        timeStyle: 'medium'
    }).format(new Date());
}

updateClock();
setInterval(updateClock, 1000);

async function refreshStatus() {
    refreshButton.disabled = true;
    refreshButton.classList.add('is-loading');
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        serviceStatus.textContent = data.status === 'operational' ? 'Operational' : 'Degraded';
        lastChecked.textContent = 'just now';
        await Promise.all([loadLogs(), loadCosts(), loadDeployments()]);
    } catch (error) {
        serviceStatus.textContent = 'Unavailable';
        lastChecked.textContent = 'check failed';
    } finally {
        refreshButton.disabled = false;
        refreshButton.classList.remove('is-loading');
    }
}

refreshButton.addEventListener('click', () => {
    refreshButton.disabled = true;
    refreshButton.classList.add('is-loading');
    refreshButton.innerHTML = '↻ <span>Refreshing...</span>';
    window.location.reload();
});
copyButton.addEventListener('click', async () => {
    await navigator.clipboard.writeText(window.location.origin);
    copyButton.textContent = '✓';
    setTimeout(() => { copyButton.textContent = '▣'; }, 1200);
});

deploymentSearch.addEventListener('input', (event) => {
    const query = event.target.value.toLowerCase();
    filterDeployments(query, statusFilter.value);
});

function filterDeployments(query, status) {
    document.querySelectorAll('.deployment-row').forEach((row) => {
        const matchesText = row.textContent.toLowerCase().includes(query);
        const matchesStatus = status === 'all' || row.dataset.status.toLowerCase() === status;
        row.hidden = !(matchesText && matchesStatus);
    });
}

statusFilter.addEventListener('change', () => {
    filterDeployments(deploymentSearch.value.toLowerCase(), statusFilter.value);
});

autoRefresh.addEventListener('click', () => {
    const enabled = autoRefresh.getAttribute('aria-pressed') === 'true';
    autoRefresh.setAttribute('aria-pressed', String(!enabled));
    autoRefresh.classList.toggle('enabled', !enabled);
    autoRefresh.textContent = !enabled ? '◷ Auto refresh on' : '◷ Auto refresh';
    if (!enabled) {
        autoRefreshTimer = setInterval(refreshStatus, 30000);
    } else {
        clearInterval(autoRefreshTimer);
    }
});

themeButton.addEventListener('click', () => {
    const isDark = document.body.classList.toggle('dark');
    localStorage.setItem('dashboard-theme', isDark ? 'dark' : 'light');
    themeButton.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
});

exportButton.addEventListener('click', () => {
    const rows = [...document.querySelectorAll('.deployment-row:not([hidden])')];
    const csv = ['Status,Version,Commit,Time', ...rows.map((row) => {
        const cells = row.querySelectorAll('td');
        return `${row.dataset.status},${cells[1].innerText},${row.dataset.commit},${cells[4].innerText}`;
    })].join('\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    link.download = 'aws-cicd-deployments.csv';
    link.click();
    URL.revokeObjectURL(link.href);
});

notificationButton.addEventListener('click', () => {
    const isOpen = notificationMenu.classList.toggle('open');
    notificationButton.setAttribute('aria-expanded', isOpen);
});

function closeReleaseModal() {
    deploymentModal.hidden = true;
}

document.querySelectorAll('.deployment-row').forEach((row) => {
    row.addEventListener('click', () => {
    selectedDeploymentId = row.dataset.commit;
        modalTitle.textContent = `Release ${row.dataset.version}`;
        modalCommit.textContent = row.dataset.commit;
        modalStatus.textContent = row.dataset.status === 'Success' ? '✓ Success' : '! Failed';
        modalStatus.className = `modal-status ${row.dataset.status.toLowerCase()}`;
        deploymentModal.hidden = false;
    });
});

rollbackButton.addEventListener('click', async () => {
    if (!selectedDeploymentId || !window.confirm('Queue a rollback for this release?')) return;
    rollbackButton.disabled = true;
    const response = await fetch(`/api/deployments/${selectedDeploymentId}/rollback`, { method: 'POST' });
    const data = await response.json();
    rollbackMessage.textContent = response.ok ? `${data.message} Target: ${data.target_version}.` : data.error;
    rollbackMessage.className = `form-message ${response.ok ? 'success' : 'error'}`;
    rollbackButton.disabled = false;
});

modalClose.addEventListener('click', closeReleaseModal);
deploymentModal.addEventListener('click', (event) => {
    if (event.target === deploymentModal) closeReleaseModal();
});
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeReleaseModal();
});

const metricData = {
    '24H': { response: [118, 132, 126, 145, 139, 151, 142, 136, 148, 142], requests: [55, 61, 58, 67, 63, 71, 68, 74, 70, 78], average: '142ms', total: '24.8k' },
    '7D': { response: [152, 147, 141, 138, 145, 139, 142], requests: [62, 68, 66, 74, 71, 79, 83], average: '143ms', total: '168.4k' },
    '30D': { response: [176, 162, 158, 151, 146, 143, 142, 139, 142, 142], requests: [48, 55, 61, 58, 67, 70, 73, 77, 81, 86], average: '149ms', total: '712.6k' }
};
let activeRange = '24H';

function drawChart() {
    const rect = metricsCanvas.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    metricsCanvas.width = rect.width * scale;
    metricsCanvas.height = rect.height * scale;
    const context = metricsCanvas.getContext('2d');
    context.scale(scale, scale);
    const width = rect.width;
    const height = rect.height;
    const padding = { top: 12, right: 14, bottom: 25, left: 30 };
    const data = metricData[activeRange];
    const allValues = [...data.response, ...data.requests];
    const min = Math.min(...allValues) - 10;
    const max = Math.max(...allValues) + 10;
    const x = (index) => padding.left + index * ((width - padding.left - padding.right) / (data.response.length - 1));
    const y = (value) => height - padding.bottom - ((value - min) / (max - min)) * (height - padding.top - padding.bottom);
    context.strokeStyle = '#e9edf3';
    context.lineWidth = 1;
    [0, .33, .66, 1].forEach((line) => { const lineY = padding.top + line * (height - padding.top - padding.bottom); context.beginPath(); context.moveTo(padding.left, lineY); context.lineTo(width - padding.right, lineY); context.stroke(); });
    function plot(values, color) { context.beginPath(); values.forEach((value, index) => index ? context.lineTo(x(index), y(value)) : context.moveTo(x(index), y(value))); context.strokeStyle = color; context.lineWidth = 2.5; context.stroke(); values.forEach((value, index) => { context.beginPath(); context.fillStyle = '#fff'; context.arc(x(index), y(value), 3.5, 0, Math.PI * 2); context.fill(); context.strokeStyle = color; context.lineWidth = 2; context.stroke(); }); }
    plot(data.response, '#3667dc');
    plot(data.requests, '#11b5c8');
    context.fillStyle = '#9aa5b4'; context.font = '10px Trebuchet MS'; context.fillText(activeRange === '24H' ? 'Now' : 'Today', width - 35, height - 6); context.fillText(activeRange === '30D' ? '30 days ago' : activeRange === '7D' ? '7 days ago' : '24 hours ago', padding.left, height - 6);
    chartResponse.textContent = data.average;
    chartRequests.textContent = data.total;
}

document.querySelectorAll('.chart-range').forEach((button) => {
    button.addEventListener('click', () => { activeRange = button.dataset.range; document.querySelectorAll('.chart-range').forEach((item) => item.classList.toggle('active', item === button)); drawChart(); });
});
metricsCanvas.addEventListener('mousemove', (event) => { const data = metricData[activeRange]; const index = Math.max(0, Math.min(data.response.length - 1, Math.round((event.offsetX - 30) / ((metricsCanvas.clientWidth - 44) / (data.response.length - 1))))); chartTooltip.textContent = `${data.response[index]}ms response · ${data.requests[index]}k requests`; chartTooltip.style.display = 'block'; chartTooltip.style.left = `${Math.min(event.offsetX + 12, metricsCanvas.clientWidth - 175)}px`; chartTooltip.style.top = `${Math.max(event.offsetY - 35, 0)}px`; });
metricsCanvas.addEventListener('mouseleave', () => { chartTooltip.style.display = 'none'; });
window.addEventListener('resize', drawChart);
drawChart();

function closeNewDeployment() {
    newDeploymentModal.hidden = true;
    deploymentMessage.textContent = '';
    newDeploymentForm.hidden = false;
    progressView.hidden = true;
    clearInterval(progressTimer);
}

newDeploymentButton.addEventListener('click', () => { newDeploymentModal.hidden = false; document.querySelector('#deploy-version').focus(); });
newDeploymentClose.addEventListener('click', closeNewDeployment);
newDeploymentCancel.addEventListener('click', closeNewDeployment);
newDeploymentModal.addEventListener('click', (event) => { if (event.target === newDeploymentModal) closeNewDeployment(); });
newDeploymentForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(newDeploymentForm);
    const response = await fetch('/api/deployments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(formData))
    });
    const data = await response.json();
    deploymentMessage.textContent = response.ok ? data.message : data.error;
    deploymentMessage.className = `form-message ${response.ok ? 'success' : 'error'}`;
    if (response.ok) {
        newDeploymentForm.reset();
        newDeploymentForm.hidden = true;
        progressView.hidden = false;
        watchDeployment(data.deployment.id, formData.get('notify_email') === 'on');
    }
});

async function watchDeployment(deploymentId, notifyEmail) {
    clearInterval(progressTimer);
    const updateProgress = async () => {
        const response = await fetch(`/api/deployments/${deploymentId}`);
        const data = await response.json();
        progressBar.style.width = `${data.progress}%`;
        progressPercent.textContent = `${data.progress}%`;
        progressStage.textContent = data.status === 'Completed' ? 'Deployment complete' : `${data.stage} in progress`;
        progressMessage.textContent = data.status === 'Completed' ? 'Release is now live in production.' : `Running ${data.stage.toLowerCase()} stage...`;

        if (Array.isArray(data.timeline)) {
            document.querySelectorAll('.progress-stages span').forEach((stage, index) => {
                const item = data.timeline[index];
                stage.textContent = item.name;
                stage.classList.toggle('active', item.status === 'In progress' || item.status === 'Completed');
            });
        }

        if (data.status === 'Completed') {
            clearInterval(progressTimer);
            const notificationResponse = notifyEmail && await fetch('/api/notifications/email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ deployment_id: deploymentId })
            });
            if (notificationResponse && notificationResponse.ok) {
                progressMessage.textContent = 'Release is live. Email notification queued.';
            }
            setTimeout(closeNewDeployment, 1800);
        }
    };
    await updateProgress();
    progressTimer = setInterval(updateProgress, 500);
}

let serviceLogs = [];
function renderLogs() {
    const query = logSearch.value.toLowerCase();
    const level = logLevel.value;
    const filtered = serviceLogs.filter((log) => (level === 'ALL' || log.level === level) && log.message.toLowerCase().includes(query));
    logViewer.innerHTML = filtered.length ? filtered.map((log) => `<div class="log-line"><time>${log.time}</time><b class="log-${log.level.toLowerCase()}">${log.level}</b><span>${log.message}</span></div>`).join('') : '<div class="log-empty">No logs match your filters.</div>';
    logCount.textContent = `${filtered.length} event${filtered.length === 1 ? '' : 's'}`;
}
async function loadLogs() {
    refreshLogs.disabled = true;
    try { const response = await fetch('/api/logs'); if (response.ok) { serviceLogs = (await response.json()).logs; renderLogs(); } } finally { refreshLogs.disabled = false; }
}
logSearch.addEventListener('input', renderLogs);
logLevel.addEventListener('change', renderLogs);
refreshLogs.addEventListener('click', loadLogs);
copyLogs.addEventListener('click', async () => { await navigator.clipboard.writeText(serviceLogs.map((log) => `${log.time} ${log.level} ${log.message}`).join('\n')); copyLogs.textContent = '✓ Copied'; setTimeout(() => { copyLogs.textContent = '▣ Copy'; }, 1200); });
loadLogs();

async function loadCosts() {
    refreshCosts.disabled = true;
    try { const response = await fetch('/api/costs'); if (response.ok) {
        const data = await response.json();
        const money = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: data.currency, minimumFractionDigits: 2 }).format(value);
        currentCost.textContent = money(data.current_month);
        costForecast.textContent = money(data.forecast);
        costBudget.textContent = money(data.budget);
        const percentage = (data.current_month / data.budget * 100).toFixed(1);
        budgetPercent.textContent = `${percentage}%`;
        budgetBar.style.width = `${percentage}%`;
        costBreakdown.innerHTML = Object.entries(data.services).map(([service, amount]) => `<span>${service}<b>${money(amount)}</b></span>`).join('');
        if (Array.isArray(data.trend) && costTrend) {
            costTrend.innerHTML = data.trend.map((entry) => `<div><span>${entry.month}</span><strong>${money(entry.amount)}</strong></div>`).join('');
        }
    } } finally { refreshCosts.disabled = false; }
}
refreshCosts.addEventListener('click', loadCosts);
loadCosts();

function attachDeploymentRows() {
    document.querySelectorAll('.deployment-row').forEach((row) => {
        row.addEventListener('click', () => {
            selectedDeploymentId = row.dataset.commit;
            modalTitle.textContent = `Release ${row.dataset.version}`;
            modalCommit.textContent = row.dataset.commit;
            modalStatus.textContent = row.dataset.status === 'Success' ? '✓ Success' : '! Failed';
            modalStatus.className = `modal-status ${row.dataset.status.toLowerCase()}`;
            deploymentModal.hidden = false;
        });
    });
}
async function loadDeployments() {
    refreshDeployments.disabled = true;
    try {
        const response = await fetch('/api/deployments');
        if (!response.ok) return;
        const data = await response.json();
        deploymentBody.innerHTML = data.deployments.map((deployment) => `<tr class="deployment-row" data-version="${deployment.version}" data-commit="${deployment.commit}" data-status="${deployment.status}"><td><span class="status-label ${deployment.status.toLowerCase()}"><i>${deployment.status === 'Success' ? '✓' : '!'}</i> ${deployment.status}</span></td><td><strong>${deployment.version}</strong></td><td>${deployment.triggered_by}</td><td><code>${deployment.commit}</code></td><td>${deployment.time}</td><td class="row-arrow">→</td></tr>`).join('');
        attachDeploymentRows();
        filterDeployments(deploymentSearch.value.toLowerCase(), statusFilter.value);
    } finally { refreshDeployments.disabled = false; }
}
refreshDeployments.addEventListener('click', loadDeployments);
loadDeployments();

async function loadDiagnostics() {
    runDiagnostics.disabled = true;
    runDiagnostics.textContent = 'Checking...';
    try {
        const response = await fetch('/api/diagnostics');
        const data = await response.json();
        diagnosticStatus.textContent = data.status === 'healthy' ? 'All systems operational' : 'Attention required';
        diagnosticPulse.classList.toggle('diagnostic-warning', data.status !== 'healthy');
        diagnosticGrid.innerHTML = data.checks.map((check) => `<div><span>✓</span><label>${check.name}<b class="${check.status === 'Operational' ? 'check-ok' : 'check-warning'}">${check.status}</b></label></div>`).join('');
        diagnosticTime.textContent = `Checked ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
    } catch (error) {
        diagnosticStatus.textContent = 'Diagnostics unavailable';
        diagnosticPulse.classList.add('diagnostic-warning');
    } finally {
        runDiagnostics.disabled = false;
        runDiagnostics.textContent = 'Run diagnostics';
    }
}
runDiagnostics.addEventListener('click', loadDiagnostics);
loadDiagnostics();

function closeProjectModal() {
    projectModal.hidden = true;
    projectMessage.textContent = '';
    projectForm.reset();
}
addProjectButton.addEventListener('click', () => { projectModal.hidden = false; document.querySelector('#project-name').focus(); });
projectClose.addEventListener('click', closeProjectModal);
projectCancel.addEventListener('click', closeProjectModal);
projectModal.addEventListener('click', (event) => { if (event.target === projectModal) closeProjectModal(); });
projectForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const response = await fetch('/api/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(projectForm))) });
    const data = await response.json();
    projectMessage.textContent = response.ok ? `${data.project} linked successfully.` : data.error;
    projectMessage.className = `form-message ${response.ok ? 'success' : 'error'}`;
    if (response.ok) setTimeout(closeProjectModal, 1200);
});
}
