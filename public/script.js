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

    // Find the history keys dynamically per the required pattern and active metric
    let homeHistoryKey = Object.keys(fixture).find(key => key.startsWith('home_last_') && key.endsWith('_matches') && key.includes(metric));
    let awayHistoryKey = Object.keys(fixture).find(key => key.startsWith('away_last_') && key.endsWith('_matches') && key.includes(metric));

    if (!homeHistoryKey) {
        homeHistoryKey = Object.keys(fixture).find(key => key.startsWith('home_last_') && key.endsWith('_matches'));
    }
    if (!awayHistoryKey) {
        awayHistoryKey = Object.keys(fixture).find(key => key.startsWith('away_last_') && key.endsWith('_matches'));
    }

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

// State to track loaded teams for the currently selected league
let fetchedTeams = [];

// Storage for team matches retrieved for the selected teams
let homeMatchesData = [];
let awayMatchesData = [];

// Current user overrides for weights { index: weight_value }
let homeOverrides = {};
let awayOverrides = {};

function getTiers(methodologyId, numMatches) {
    if (numMatches === 0) return [];
    if (methodologyId === 1) {
        return [
            {
                indices: Array.from({length: numMatches}, (_, i) => i),
                target_weight: 1.0
            }
        ];
    } else if (methodologyId === 2) {
        if (numMatches <= 4) {
            return [
                {
                    indices: Array.from({length: numMatches}, (_, i) => i),
                    target_weight: 1.0
                }
            ];
        } else {
            return [
                {
                    indices: [0, 1, 2, 3],
                    target_weight: 0.70
                },
                {
                    indices: Array.from({length: numMatches - 4}, (_, i) => i + 4),
                    target_weight: 0.30
                }
            ];
        }
    }
    return [];
}

function getDefaultWeights(methodologyId, numMatches) {
    if (numMatches === 0) return [];
    if (methodologyId === 1) {
        return Array(numMatches).fill(1.0 / numMatches);
    } else if (methodologyId === 2) {
        if (numMatches <= 4) {
            return Array(numMatches).fill(1.0 / numMatches);
        } else {
            const tier1Count = 4;
            const tier2Count = numMatches - 4;
            const weights = [];
            for (let i = 0; i < numMatches; i++) {
                if (i < 4) {
                    weights.push(0.70 / tier1Count);
                } else {
                    weights.push(0.30 / tier2Count);
                }
            }
            return weights;
        }
    }
    return [];
}

function normalizeWeightsJS(numMatches, defaultWeights, overrides, methodologyId) {
    if (numMatches === 0) return [];
    const weights = [...defaultWeights];
    const tiers = getTiers(methodologyId, numMatches);

    for (const tier of tiers) {
        const tierIndices = tier.indices;
        const targetTotal = tier.target_weight;

        const overriddenIndices = [];
        const unoverriddenIndices = [];

        for (const idx of tierIndices) {
            let hasOverride = false;
            let overrideVal = null;
            if (overrides !== null && overrides !== undefined) {
                if (idx in overrides) {
                    hasOverride = true;
                    overrideVal = overrides[idx];
                } else if (String(idx) in overrides) {
                    hasOverride = true;
                    overrideVal = overrides[String(idx)];
                }
            }

            if (hasOverride) {
                let val = parseFloat(overrideVal);
                if (isNaN(val)) {
                    val = 0.0;
                }
                overriddenIndices.push({ idx, val });
            } else {
                unoverriddenIndices.push(idx);
            }
        }

        if (overriddenIndices.length > 0) {
            const totalOverride = overriddenIndices.reduce((sum, item) => sum + item.val, 0);

            if (unoverriddenIndices.length === 0) {
                if (totalOverride > 0) {
                    for (const item of overriddenIndices) {
                        weights[item.idx] = (item.val / totalOverride) * targetTotal;
                    }
                } else {
                    for (const item of overriddenIndices) {
                        weights[item.idx] = targetTotal / overriddenIndices.length;
                    }
                }
            } else {
                if (totalOverride >= targetTotal) {
                    for (const idx of unoverriddenIndices) {
                        weights[idx] = 0.0;
                    }
                    if (totalOverride > 0) {
                        for (const item of overriddenIndices) {
                            weights[item.idx] = (item.val / totalOverride) * targetTotal;
                        }
                    } else {
                        for (const item of overriddenIndices) {
                            weights[item.idx] = targetTotal / overriddenIndices.length;
                        }
                    }
                } else {
                    for (const item of overriddenIndices) {
                        weights[item.idx] = item.val;
                    }
                    const remainingTarget = targetTotal - totalOverride;
                    const totalDefault = unoverriddenIndices.reduce((sum, idx) => sum + defaultWeights[idx], 0);

                    if (totalDefault > 0) {
                        for (const idx of unoverriddenIndices) {
                            weights[idx] = (defaultWeights[idx] / totalDefault) * remainingTarget;
                        }
                    } else {
                        for (const idx of unoverriddenIndices) {
                            weights[idx] = remainingTarget / unoverriddenIndices.length;
                        }
                    }
                }
            }
        }
    }

    return weights;
}

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
            {"id": "superliga-denmark", "name": "Superliga", "flag": "🇩🇰"}
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
    const teamGroup = document.getElementById('semi-team-selection-group');
    const homeTeamSelect = document.getElementById('semi-home-team-select');
    const awayTeamSelect = document.getElementById('semi-away-team-select');
    const predictBtn = document.getElementById('semi-predict-btn');
    const resultDiv = document.getElementById('semi-prediction-result');

    if (!fetchBtn) return;

    // Reset teams when league changes
    leagueSelect.addEventListener('change', () => {
        teamGroup.classList.add('hidden');
        document.getElementById('semi-config-group').classList.add('hidden');
        document.getElementById('semi-weight-editor-container').classList.add('hidden');
        predictBtn.classList.add('hidden');
        homeTeamSelect.innerHTML = '<option value="">-- Choose Home Team --</option>';
        awayTeamSelect.innerHTML = '<option value="">-- Choose Away Team --</option>';
        resultDiv.innerHTML = '';
        fetchedTeams = [];
        homeMatchesData = [];
        awayMatchesData = [];
        homeOverrides = {};
        awayOverrides = {};
    });

    fetchBtn.addEventListener('click', async () => {
        const league = leagueSelect.value;
        if (!league) {
            showSemiAlert('Please select a league first.', 'error');
            return;
        }

        const pastedHtml = htmlPaste.value.trim();
        fetchBtn.disabled = true;
        fetchBtn.textContent = 'Loading Teams...';
        resultDiv.innerHTML = '';
        teamGroup.classList.add('hidden');
        predictBtn.classList.add('hidden');
        homeTeamSelect.innerHTML = '<option value="">-- Choose Home Team --</option>';
        awayTeamSelect.innerHTML = '<option value="">-- Choose Away Team --</option>';

        try {
            let res;
            if (pastedHtml) {
                // If HTML pasted, make a POST request with the source (no teams parameters to trigger extraction)
                res = await fetch(`/api/predict`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ league, html: pastedHtml })
                });
            } else {
                // Otherwise do a GET with only league which triggers direct fetching and team extraction
                res = await fetch(`/api/predict?league=${league}`);
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
            fetchedTeams = data.teams || [];

            if (fetchedTeams.length === 0) {
                showSemiAlert('No teams found in the source. Please check your pasted HTML or try again.', 'error');
                return;
            }

            showSemiAlert(`Successfully loaded ${fetchedTeams.length} teams. Choose Home & Away teams below to predict!`, 'success');

            // Populate team dropdowns
            fetchedTeams.forEach(team => {
                const optH = document.createElement('option');
                optH.value = team;
                optH.textContent = team;
                homeTeamSelect.appendChild(optH);

                const optA = document.createElement('option');
                optA.value = team;
                optA.textContent = team;
                awayTeamSelect.appendChild(optA);
            });

            teamGroup.classList.remove('hidden');

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error fetching teams: ${err.message}`, 'error');
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.textContent = 'Load Teams';
        }
    });

    // Helper to fetch and build the weight editor whenever teams, methodology, or metric change
    async function loadMatchesForSelectedTeams() {
        const league = leagueSelect.value;
        const homeTeam = homeTeamSelect.value;
        const awayTeam = awayTeamSelect.value;
        const methodology = document.getElementById('semi-methodology-select').value;
        const metric = document.getElementById('semi-metric-select').value;

        if (!league || !homeTeam || !awayTeam) {
            document.getElementById('semi-config-group').classList.add('hidden');
            document.getElementById('semi-weight-editor-container').classList.add('hidden');
            predictBtn.classList.add('hidden');
            return;
        }

        const pastedHtml = htmlPaste.value.trim();

        try {
            // Fetch default prediction for both teams to get their balanced matches list
            // API /api/predict handles returning matches
            const payload = {
                league,
                home_team: homeTeam,
                away_team: awayTeam,
                methodology,
                metric
            };

            let res;
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
                throw new Error('Could not load matches for prediction configuration.');
            }

            const data = await res.json();

            // Extract history matches
            const homeKey = `home_last_${metric}_matches`;
            const awayKey = `away_last_${metric}_matches`;

            homeMatchesData = data[homeKey] || data.home_last_xg_matches || [];
            awayMatchesData = data[awayKey] || data.away_last_xg_matches || [];

            // Reset overrides if the matches list changed size
            homeOverrides = {};
            awayOverrides = {};

            document.getElementById('semi-config-group').classList.remove('hidden');
            renderWeightEditor();
            predictBtn.classList.remove('hidden');

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error loading team match histories: ${err.message}`, 'error');
        }
    }

    homeTeamSelect.addEventListener('change', loadMatchesForSelectedTeams);
    awayTeamSelect.addEventListener('change', loadMatchesForSelectedTeams);
    document.getElementById('semi-methodology-select').addEventListener('change', loadMatchesForSelectedTeams);
    document.getElementById('semi-metric-select').addEventListener('change', loadMatchesForSelectedTeams);

    function renderWeightEditor() {
        const container = document.getElementById('semi-weight-editor-container');
        if (!container) return;

        const methodologyId = parseInt(document.getElementById('semi-methodology-select').value);
        const metric = document.getElementById('semi-metric-select').value;

        const homeDefaults = getDefaultWeights(methodologyId, homeMatchesData.length);
        const awayDefaults = getDefaultWeights(methodologyId, awayMatchesData.length);

        const homeNormalized = normalizeWeightsJS(homeMatchesData.length, homeDefaults, homeOverrides, methodologyId);
        const awayNormalized = normalizeWeightsJS(awayMatchesData.length, awayDefaults, awayOverrides, methodologyId);

        container.innerHTML = `
            <div class="weight-editor-grid">
                <div class="weight-col">
                    <h3>🏠 ${homeTeamSelect.value} Matches</h3>
                    <div class="match-list-editor" id="home-match-editor"></div>
                </div>
                <div class="weight-col">
                    <h3>✈️ ${awayTeamSelect.value} Matches</h3>
                    <div class="match-list-editor" id="away-match-editor"></div>
                </div>
            </div>
        `;

        const homeList = container.querySelector('#home-match-editor');
        const awayList = container.querySelector('#away-match-editor');

        // Render Home Matches
        homeMatchesData.forEach((match, idx) => {
            const normalizedW = homeNormalized[idx];
            const displayNormalized = (normalizedW * 100).toFixed(1);
            const userVal = homeOverrides[idx] !== undefined ? homeOverrides[idx] : '';

            const item = document.createElement('div');
            item.className = `match-editor-item ${normalizedW === 0 ? 'deleted-match' : ''}`;

            const scoreFor = match.goals_for !== null && match.goals_for !== undefined ? match.goals_for : (match.xg_for !== null ? match.xg_for : 0);
            const scoreAgainst = match.goals_against !== null && match.goals_against !== undefined ? match.goals_against : (match.xg_against !== null ? match.xg_against : 0);

            item.innerHTML = `
                <div class="match-info">
                    <span class="match-date">${match.date}</span>
                    <span class="match-detail">(${match.venue === 'home' ? 'H' : 'A'}) vs ${match.opponent}</span>
                    <span class="match-score">Score: ${scoreFor} - ${scoreAgainst}</span>
                    <span class="match-xg">xG: ${(match.xg_for || 0).toFixed(2)} - ${(match.xg_against || 0).toFixed(2)}</span>
                </div>
                <div class="match-weight-inputs">
                    <div class="input-wrap">
                        <label>Override:</label>
                        <input type="number" step="0.01" min="0" max="1" placeholder="Auto" value="${userVal}" data-idx="${idx}" class="home-weight-input">
                    </div>
                    <div class="normalized-badge">
                        <span>${displayNormalized}%</span>
                    </div>
                    <button class="delete-match-btn" data-idx="${idx}" title="Remove Match">❌</button>
                </div>
            `;
            homeList.appendChild(item);
        });

        // Render Away Matches
        awayMatchesData.forEach((match, idx) => {
            const normalizedW = awayNormalized[idx];
            const displayNormalized = (normalizedW * 100).toFixed(1);
            const userVal = awayOverrides[idx] !== undefined ? awayOverrides[idx] : '';

            const item = document.createElement('div');
            item.className = `match-editor-item ${normalizedW === 0 ? 'deleted-match' : ''}`;

            const scoreFor = match.goals_for !== null && match.goals_for !== undefined ? match.goals_for : (match.xg_for !== null ? match.xg_for : 0);
            const scoreAgainst = match.goals_against !== null && match.goals_against !== undefined ? match.goals_against : (match.xg_against !== null ? match.xg_against : 0);

            item.innerHTML = `
                <div class="match-info">
                    <span class="match-date">${match.date}</span>
                    <span class="match-detail">(${match.venue === 'home' ? 'H' : 'A'}) vs ${match.opponent}</span>
                    <span class="match-score">Score: ${scoreFor} - ${scoreAgainst}</span>
                    <span class="match-xg">xG: ${(match.xg_for || 0).toFixed(2)} - ${(match.xg_against || 0).toFixed(2)}</span>
                </div>
                <div class="match-weight-inputs">
                    <div class="input-wrap">
                        <label>Override:</label>
                        <input type="number" step="0.01" min="0" max="1" placeholder="Auto" value="${userVal}" data-idx="${idx}" class="away-weight-input">
                    </div>
                    <div class="normalized-badge">
                        <span>${displayNormalized}%</span>
                    </div>
                    <button class="delete-match-btn" data-idx="${idx}" title="Remove Match">❌</button>
                </div>
            `;
            awayList.appendChild(item);
        });

        // Add Input Event Listeners for real-time update
        homeList.querySelectorAll('.home-weight-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                const val = e.target.value.trim();
                if (val === '') {
                    delete homeOverrides[idx];
                } else {
                    const parsed = parseFloat(val);
                    homeOverrides[idx] = isNaN(parsed) ? 0.0 : parsed;
                }
                // Recalculate and update domestic weights
                updateWeightsRealTime('home', e.target);
            });
        });

        awayList.querySelectorAll('.away-weight-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                const val = e.target.value.trim();
                if (val === '') {
                    delete awayOverrides[idx];
                } else {
                    const parsed = parseFloat(val);
                    awayOverrides[idx] = isNaN(parsed) ? 0.0 : parsed;
                }
                // Recalculate and update domestic weights
                updateWeightsRealTime('away', e.target);
            });
        });

        // Delete handlers
        homeList.querySelectorAll('.delete-match-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const idx = parseInt(btn.dataset.idx);
                homeOverrides[idx] = 0.0;
                renderWeightEditor();
            });
        });

        awayList.querySelectorAll('.delete-match-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const idx = parseInt(btn.dataset.idx);
                awayOverrides[idx] = 0.0;
                renderWeightEditor();
            });
        });

        container.classList.remove('hidden');
    }

    function updateWeightsRealTime(side, activeInput) {
        const methodologyId = parseInt(document.getElementById('semi-methodology-select').value);
        const matchesData = side === 'home' ? homeMatchesData : awayMatchesData;
        const overrides = side === 'home' ? homeOverrides : awayOverrides;

        const defaults = getDefaultWeights(methodologyId, matchesData.length);
        const normalized = normalizeWeightsJS(matchesData.length, defaults, overrides, methodologyId);

        const listContainer = document.getElementById(`${side}-match-editor`);
        const items = listContainer.querySelectorAll('.match-editor-item');

        items.forEach((item, idx) => {
            const w = normalized[idx];

            // Toggle deletion styling
            if (w === 0) {
                item.classList.add('deleted-match');
            } else {
                item.classList.remove('deleted-match');
            }

            // Update badge value
            const badge = item.querySelector('.normalized-badge span');
            if (badge) {
                badge.textContent = `${(w * 100).toFixed(1)}%`;
            }

            // Update input field if it's not the active input to prevent resetting cursor
            const input = item.querySelector(`.${side}-weight-input`);
            if (input && input !== activeInput) {
                const userVal = overrides[idx];
                input.value = userVal !== undefined ? userVal : '';
            }
        });
    }

    predictBtn.addEventListener('click', async () => {
        const league = leagueSelect.value;
        const homeTeam = homeTeamSelect.value;
        const awayTeam = awayTeamSelect.value;
        const methodology = document.getElementById('semi-methodology-select').value;
        const metric = document.getElementById('semi-metric-select').value;

        if (!league || !homeTeam || !awayTeam) {
            showSemiAlert('Please select both Home and Away teams to calculate predictions.', 'error');
            return;
        }

        if (homeTeam.toLowerCase() === awayTeam.toLowerCase()) {
            showSemiAlert('Home and Away teams must be different.', 'error');
            return;
        }

        const pastedHtml = htmlPaste.value.trim();

        predictBtn.disabled = true;
        predictBtn.textContent = 'Calculating Prediction...';

        try {
            let res;
            const payload = {
                league,
                home_team: homeTeam,
                away_team: awayTeam,
                methodology,
                metric,
                home_overrides: JSON.stringify(homeOverrides),
                away_overrides: JSON.stringify(awayOverrides)
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

            // Clear loading/alerts and render the prediction card beautifully
            resultDiv.innerHTML = '';

            // Format prediction matching standard createFixtureCard component
            const metricKeyPart = metric === 'xg' ? 'xg' : 'goals';
            const cardFixture = {
                home_team: prediction.home_team,
                away_team: prediction.away_team,
                [`home_expected_${metricKeyPart}`]: prediction[`home_expected_${metricKeyPart}`],
                [`away_expected_${metricKeyPart}`]: prediction[`away_expected_${metricKeyPart}`],
                [`combined_expected_${metricKeyPart}`]: prediction[`combined_expected_${metricKeyPart}`],
                [`home_last_${metricKeyPart}_matches`]: prediction[`home_last_${metricKeyPart}_matches`],
                [`away_last_${metricKeyPart}_matches`]: prediction[`away_last_${metricKeyPart}_matches`],
                date: 'Upcoming Prediction'
            };

            // Set dynamic scaleMax
            const expectedHome = prediction[`home_expected_${metricKeyPart}`] || 0;
            const expectedAway = prediction[`away_expected_${metricKeyPart}`] || 0;
            const maxVal = Math.max(expectedHome, expectedAway);
            const scaleMax = Math.max(maxVal * 1.1, 3.0);

            // Create main result card
            const mainCardTitle = document.createElement('h3');
            mainCardTitle.className = 'prediction-section-title';
            mainCardTitle.textContent = `🎯 Expected Prediction (${metric.toUpperCase()})`;
            resultDiv.appendChild(mainCardTitle);

            const card = createFixtureCard(cardFixture, scaleMax, metricKeyPart);
            resultDiv.appendChild(card);

            // Show Comparisons Grid if available
            if (prediction.comparisons) {
                const compSection = document.createElement('div');
                compSection.className = 'comparisons-section';
                compSection.innerHTML = `
                    <h3 class="prediction-section-title">📊 Multi-Methodology Comparison</h3>
                    <div class="comparisons-table-container">
                        <table class="comparisons-table">
                            <thead>
                                <tr>
                                    <th>Methodology</th>
                                    <th>Metric</th>
                                    <th>Home (${prediction.home_team})</th>
                                    <th>Away (${prediction.away_team})</th>
                                    <th>Combined</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr class="${methodology == '1' && metric == 'xg' ? 'active-combo-row' : ''}">
                                    <td>Methodology 1 (Equal)</td>
                                    <td>xG</td>
                                    <td>${(prediction.comparisons.methodology_1.xg?.home_expected ?? 0).toFixed(2)}</td>
                                    <td>${(prediction.comparisons.methodology_1.xg?.away_expected ?? 0).toFixed(2)}</td>
                                    <td><strong>${(prediction.comparisons.methodology_1.xg?.combined_expected ?? 0).toFixed(2)}</strong></td>
                                </tr>
                                <tr class="${methodology == '1' && metric == 'goals' ? 'active-combo-row' : ''}">
                                    <td>Methodology 1 (Equal)</td>
                                    <td>Goals</td>
                                    <td>${(prediction.comparisons.methodology_1.goals?.home_expected ?? 0).toFixed(2)}</td>
                                    <td>${(prediction.comparisons.methodology_1.goals?.away_expected ?? 0).toFixed(2)}</td>
                                    <td><strong>${(prediction.comparisons.methodology_1.goals?.combined_expected ?? 0).toFixed(2)}</strong></td>
                                </tr>
                                <tr class="${methodology == '2' && metric == 'xg' ? 'active-combo-row' : ''}">
                                    <td>Methodology 2 (70/30 Split)</td>
                                    <td>xG</td>
                                    <td>${(prediction.comparisons.methodology_2.xg?.home_expected ?? 0).toFixed(2)}</td>
                                    <td>${(prediction.comparisons.methodology_2.xg?.away_expected ?? 0).toFixed(2)}</td>
                                    <td><strong>${(prediction.comparisons.methodology_2.xg?.combined_expected ?? 0).toFixed(2)}</strong></td>
                                </tr>
                                <tr class="${methodology == '2' && metric == 'goals' ? 'active-combo-row' : ''}">
                                    <td>Methodology 2 (70/30 Split)</td>
                                    <td>Goals</td>
                                    <td>${(prediction.comparisons.methodology_2.goals?.home_expected ?? 0).toFixed(2)}</td>
                                    <td>${(prediction.comparisons.methodology_2.goals?.away_expected ?? 0).toFixed(2)}</td>
                                    <td><strong>${(prediction.comparisons.methodology_2.goals?.combined_expected ?? 0).toFixed(2)}</strong></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                `;
                resultDiv.appendChild(compSection);
            }

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
