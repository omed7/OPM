const FIXTURE_LIMIT = 10;

const LEAGUE_FLAGS = {
    'premier_league': '🏴\u200d󠁢\u200d󠁥\u200d󠁢\u200d󠁧\u200d󠁿',
    'la_liga': '🇪🇸',
    'serie_a': '🇮🇹',
    'bundesliga': '🇩🇪',
    'ligue_1': '🇫🇷'
};

async function init() {
    const container = document.getElementById('fixtures-container');
    const versionTag = document.getElementById('version-tag');

    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Failed to fetch data');
        const data = await response.json();

        // Update version tag
        try {
            const versionResponse = await fetch('version.json');
            if (versionResponse.ok) {
                const versionData = await versionResponse.json();
                versionTag.textContent = `v${versionData.version}`;
            }
        } catch (e) {
            console.error('Failed to load version info', e);
        }

        if (!data.leagues || data.leagues.length === 0) {
            container.innerHTML = '<div class="no-fixtures">No leagues found.</div>';
            return;
        }

        // Create tab container and insert above the fixtures container
        const tabContainer = document.createElement('div');
        tabContainer.className = 'tab-container';
        container.parentNode.insertBefore(tabContainer, container);

        let activeLeagueId = data.leagues[0].id;

        function renderTabs() {
            tabContainer.innerHTML = '';
            data.leagues.forEach(league => {
                const btn = document.createElement('button');
                btn.className = 'tab-button';
                if (league.id === activeLeagueId) {
                    btn.classList.add('active');
                }
                const flag = LEAGUE_FLAGS[league.id] || '';
                btn.textContent = flag ? `${flag} ${league.name}` : league.name;
                btn.addEventListener('click', () => {
                    if (activeLeagueId === league.id) return;
                    activeLeagueId = league.id;

                    // Update active class on buttons
                    tabContainer.querySelectorAll('.tab-button').forEach(b => {
                        b.classList.toggle('active', b === btn);
                    });

                    // Render fixtures for active league
                    renderLeague(league);
                });
                tabContainer.appendChild(btn);
            });
        }

        function renderLeague(league) {
            container.innerHTML = '';

            if (!league.fixtures || league.fixtures.length === 0) {
                container.innerHTML = `<div class="no-fixtures">No upcoming ${league.name} fixtures found.</div>`;
                return;
            }

            // Copy, sort chronologically per league, and cap at FIXTURE_LIMIT
            const sortedFixtures = [...league.fixtures]
                .sort((a, b) => new Date(a.date) - new Date(b.date))
                .slice(0, FIXTURE_LIMIT);

            const metric = league.metric || 'xg';

            // Find max expected_{metric} for scale
            let maxSingleMetric = 0;
            sortedFixtures.forEach(f => {
                const homeVal = f[`home_expected_${metric}`];
                const awayVal = f[`away_expected_${metric}`];
                if (typeof homeVal === 'number') {
                    maxSingleMetric = Math.max(maxSingleMetric, homeVal);
                }
                if (typeof awayVal === 'number') {
                    maxSingleMetric = Math.max(maxSingleMetric, awayVal);
                }
            });

            // Add a bit of buffer (same as original, scaleMax has fallback to 3.0)
            const scaleMax = Math.max(maxSingleMetric * 1.1, 3.0);

            sortedFixtures.forEach(fixture => {
                container.appendChild(createFixtureCard(fixture, scaleMax, metric));
            });
        }

        // Initial setup
        renderTabs();
        renderLeague(data.leagues[0]);

    } catch (error) {
        console.error(error);
        container.innerHTML = '<div class="no-fixtures">Error loading fixtures. Please try again later.</div>';
    }
}

function createFixtureCard(fixture, scaleMax, metric) {
    const card = document.createElement('div');
    card.className = 'fixture-card';

    const homeInitials = getInitials(fixture.home_team);
    const awayInitials = getInitials(fixture.away_team);
    const homeColor = getColor(fixture.home_team);
    const awayColor = getColor(fixture.away_team);

    const combinedVal = fixture[`combined_expected_${metric}`] || 0;
    const homeExpectedVal = fixture[`home_expected_${metric}`] || 0;
    const awayExpectedVal = fixture[`away_expected_${metric}`] || 0;

    const homePercent = (homeExpectedVal / scaleMax) * 100;
    const awayPercent = (awayExpectedVal / scaleMax) * 100;

    // Find the history keys dynamically per the required pattern
    const homeHistoryKey = Object.keys(fixture).find(key => key.startsWith('home_last_') && key.endsWith('_matches'));
    const awayHistoryKey = Object.keys(fixture).find(key => key.startsWith('away_last_') && key.endsWith('_matches'));

    const homeHistoryArr = homeHistoryKey ? fixture[homeHistoryKey] : [];
    const awayHistoryArr = awayHistoryKey ? fixture[awayHistoryKey] : [];

    const homeHistory = (homeHistoryArr || []).map(m => {
        const valFor = m[`${metric}_for`] || 0;
        const valAgainst = m[`${metric}_against`] || 0;
        return `<div class="history-item">${valFor.toFixed(2)} - ${valAgainst.toFixed(2)} vs ${m.opponent}</div>`;
    }).join('');

    const awayHistory = (awayHistoryArr || []).map(m => {
        const valFor = m[`${metric}_for`] || 0;
        const valAgainst = m[`${metric}_against`] || 0;
        return `<div class="history-item">${valFor.toFixed(2)} - ${valAgainst.toFixed(2)} vs ${m.opponent}</div>`;
    }).join('');

    const metricLabel = metric.toLowerCase() === 'xg' ? 'XG' : (metric.charAt(0).toUpperCase() + metric.slice(1).toLowerCase());
    const combinedLabel = `${metricLabel} Combined`;

    card.innerHTML = `
        <div class="fixture-header">
            <div class="team">
                <div class="team-badge" style="background-color: ${homeColor}">${homeInitials}</div>
                <div class="team-name">${fixture.home_team}</div>
            </div>
            <div class="xg-center">
                <div class="combined-xg-label">${combinedLabel}</div>
                <div class="combined-xg">${combinedVal.toFixed(2)}</div>
                <div class="split-xg">${homeExpectedVal.toFixed(2)} - ${awayExpectedVal.toFixed(2)}</div>
            </div>
            <div class="team">
                <div class="team-badge" style="background-color: ${awayColor}">${awayInitials}</div>
                <div class="team-name">${fixture.away_team}</div>
            </div>
        </div>
        <div class="xg-bars">
            <div class="xg-bar-container" id="home-bar-container">
                <div class="xg-bar" style="width: ${homePercent}%"></div>
            </div>
            <div class="xg-bar-container" id="away-bar-container">
                <div class="xg-bar" style="width: ${awayPercent}%"></div>
            </div>
        </div>
        <div class="match-history">
            <div class="history-list home">
                ${homeHistory}
            </div>
            <div class="history-list away">
                ${awayHistory}
            </div>
        </div>
    `;

    return card;
}

function getInitials(name) {
    if (!name) return '??';
    const parts = name.split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

function getColor(name) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 60%, 40%)`;
}

// Theme toggle functionality
function setupTheme() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) return;

    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    toggleBtn.textContent = currentTheme === 'dark' ? '☀️' : '🌙';

    toggleBtn.addEventListener('click', () => {
        const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        toggleBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
    });
}

// State to track whether we've loaded upcoming fixtures for the currently selected league
let fetchedFixtures = [];

function setupModeToggle() {
    const modeBtn = document.getElementById('mode-toggle');
    const autoMain = document.getElementById('fixtures-container');
    const semiMain = document.getElementById('semi-auto-container');

    if (!modeBtn) return;

    modeBtn.addEventListener('click', () => {
        const isSemiActive = !semiMain.classList.contains('hidden');
        const tabContainer = document.querySelector('.tab-container');
        if (isSemiActive) {
            // Switch to Automatic mode
            semiMain.classList.add('hidden');
            autoMain.classList.remove('hidden');
            if (tabContainer) tabContainer.classList.remove('hidden');
            modeBtn.textContent = '🔮 Semi-Auto';
        } else {
            // Switch to Semi-Automatic mode
            autoMain.classList.add('hidden');
            if (tabContainer) tabContainer.classList.add('hidden');
            semiMain.classList.remove('hidden');
            modeBtn.textContent = '📊 Auto Mode';

            // Lazy load leagues list once when toggled
            initSemiAuto();
        }
    });
}

async function initSemiAuto() {
    const leagueSelect = document.getElementById('semi-league-select');
    if (!leagueSelect || leagueSelect.children.length > 1) return; // Already loaded

    function populateLeagues(leagues) {
        leagues.forEach(l => {
            const opt = document.createElement('option');
            opt.value = l.id;
            opt.textContent = `${l.flag} ${l.name}`;
            leagueSelect.appendChild(opt);
        });
    }

    try {
        const res = await fetch('/api/leagues');
        if (!res.ok) throw new Error('Failed to fetch leagues list');
        const leagues = await res.json();
        populateLeagues(leagues);
    } catch (err) {
        console.warn('API /api/leagues not reachable. Using fallback leagues list.', err);
        const fallbackLeagues = [
            {"id": "mls", "name": "Major League Soccer", "flag": "🇺🇸"},
            {"id": "eliteserien", "name": "Eliteserien", "flag": "🇳🇴"},
            {"id": "premiership", "name": "Premiership", "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿"},
            {"id": "superliga-denmark", "name": "Superliga", "flag": "🇩🇰"},
            {"id": "veikkausliiga", "name": "Veikkausliiga", "flag": "🇫🇮"},
            {"id": "canadian-premier-league", "name": "Canadian Premier League", "flag": "🇨🇦"}
        ];
        populateLeagues(fallbackLeagues);
    }
}

function showSemiAlert(msg, type = 'error') {
    const resultDiv = document.getElementById('semi-prediction-result');
    if (!resultDiv) return;

    resultDiv.innerHTML = `
        <div class="alert-message ${type}">
            ${msg}
        </div>
    `;
}

function setupSemiAutoHandlers() {
    const leagueSelect = document.getElementById('semi-league-select');
    const htmlPaste = document.getElementById('semi-html-paste');
    const fetchBtn = document.getElementById('semi-fetch-btn');
    const fixtureGroup = document.getElementById('semi-fixture-selection-group');
    const fixtureSelect = document.getElementById('semi-fixture-select');
    const predictBtn = document.getElementById('semi-predict-btn');
    const resultDiv = document.getElementById('semi-prediction-result');

    if (!fetchBtn) return;

    // Reset fixtures when league changes
    leagueSelect.addEventListener('change', () => {
        fixtureGroup.classList.add('hidden');
        predictBtn.classList.add('hidden');
        fixtureSelect.innerHTML = '<option value="">-- Choose a Fixture --</option>';
        resultDiv.innerHTML = '';
        fetchedFixtures = [];
    });

    fetchBtn.addEventListener('click', async () => {
        const league = leagueSelect.value;
        if (!league) {
            showSemiAlert('Please select a league first.', 'error');
            return;
        }

        const pastedHtml = htmlPaste.value.trim();
        fetchBtn.disabled = true;
        fetchBtn.textContent = 'Loading Fixtures...';
        resultDiv.innerHTML = '';
        fixtureGroup.classList.add('hidden');
        predictBtn.classList.add('hidden');
        fixtureSelect.innerHTML = '<option value="">-- Choose a Fixture --</option>';

        try {
            let res;
            if (pastedHtml) {
                // If HTML pasted, make a POST request with the source
                res = await fetch(`/api/upcoming?league=${league}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ html: pastedHtml })
                });
            } else {
                // Otherwise do a GET which triggers direct fetching on the server
                res = await fetch(`/api/upcoming?league=${league}`);
            }

            if (!res.ok) {
                const errorData = await res.json();
                if (errorData.blocked) {
                    showSemiAlert('Cloudflare protected OddAlerts is blocking direct server fetching. Please right-click the OddAlerts page, select "View Page Source", copy all, and paste it into the HTML box below.', 'error');
                } else {
                    throw new Error(errorData.error || 'Server returned an error');
                }
                return;
            }

            const data = await res.json();
            fetchedFixtures = data.fixtures || [];

            // Filter for upcoming fixtures (where is_result is false, or format nicely)
            const upcoming = fetchedFixtures.filter(f => !f.is_result);
            if (upcoming.length === 0) {
                // If no upcoming found, let them predict on recent results just in case, but warn them
                showSemiAlert('No upcoming fixtures found in the source. You can still select from played matches below if desired.', 'success');
            } else {
                showSemiAlert(`Successfully loaded ${upcoming.length} upcoming fixtures. Select one below to calculate prediction!`, 'success');
            }

            // Populate fixtures drop down
            const displayFixtures = fetchedFixtures.length > 0 ? fetchedFixtures : [];
            displayFixtures.forEach((f, idx) => {
                const opt = document.createElement('option');
                opt.value = idx;
                const statusTag = f.is_result ? `(Result: ${f.status})` : `(Upcoming: ${f.status})`;
                opt.textContent = `${f.date} - ${f.home_team} vs ${f.away_team} ${statusTag}`;
                fixtureSelect.appendChild(opt);
            });

            fixtureGroup.classList.remove('hidden');
            predictBtn.classList.remove('hidden');

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error fetching fixtures: ${err.message}`, 'error');
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.textContent = 'Load Fixtures';
        }
    });

    predictBtn.addEventListener('click', async () => {
        const league = leagueSelect.value;
        const fixtureIdx = fixtureSelect.value;
        if (!league || fixtureIdx === '') {
            showSemiAlert('Please select a fixture to calculate predictions.', 'error');
            return;
        }

        const selectedFixture = fetchedFixtures[fixtureIdx];
        const pastedHtml = htmlPaste.value.trim();

        predictBtn.disabled = true;
        predictBtn.textContent = 'Calculating Prediction...';

        try {
            let res;
            const payload = {
                league,
                home_team: selectedFixture.home_team,
                away_team: selectedFixture.away_team
            };

            if (pastedHtml) {
                payload.html = pastedHtml;
                res = await fetch('/api/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                const queryStr = new URLSearchParams(payload).toString();
                res = await fetch(`/api/predict?${queryStr}`);
            }

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.error || 'Server error computing prediction');
            }

            const prediction = await res.json();

            // Clear loading and render the prediction card beautifully
            resultDiv.innerHTML = '';

            // Format prediction matching standard createFixtureCard component
            // createFixtureCard expects (fixture, scaleMax, metric)
            // Let's adapt prediction to fixture schema
            const cardFixture = {
                home_team: prediction.home_team,
                away_team: prediction.away_team,
                home_expected_xg: prediction.home_expected_xg,
                away_expected_xg: prediction.away_expected_xg,
                combined_expected_xg: prediction.combined_expected_xg,
                home_last_xg_matches: prediction.home_last_xg_matches,
                away_last_xg_matches: prediction.away_last_xg_matches,
                date: selectedFixture.date
            };

            // Set dynamic scaleMax
            const maxVal = Math.max(prediction.home_expected_xg, prediction.away_expected_xg);
            const scaleMax = Math.max(maxVal * 1.1, 3.0);

            const card = createFixtureCard(cardFixture, scaleMax, 'xg');
            resultDiv.appendChild(card);

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error calculating prediction: ${err.message}`, 'error');
        } finally {
            predictBtn.disabled = false;
            predictBtn.textContent = 'Calculate Prediction';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    init();
    setupTheme();
    setupModeToggle();
    setupSemiAutoHandlers();
});
