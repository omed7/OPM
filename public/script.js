const FIXTURE_LIMIT = 10;

// Team identity store (name -> logo mapping)
const TeamIdentityStore = {
    getLogo(teamName) {
        if (!teamName) return null;
        try {
            const logos = JSON.parse(localStorage.getItem('team_logos') || '{}');
            return logos[teamName] || null;
        } catch (e) {
            console.error('Failed to parse team logos from localStorage', e);
            return null;
        }
    },
    setLogo(teamName, url) {
        if (!teamName) return;
        try {
            const logos = JSON.parse(localStorage.getItem('team_logos') || '{}');
            if (url) {
                logos[teamName] = url;
            } else {
                delete logos[teamName];
            }
            localStorage.setItem('team_logos', JSON.stringify(logos));
            // Trigger custom event so the UI updates
            window.dispatchEvent(new CustomEvent('team-logo-updated', { detail: { teamName, url } }));
        } catch (e) {
            console.error('Failed to save team logo to localStorage', e);
        }
    },
    getAllLogos() {
        try {
            return JSON.parse(localStorage.getItem('team_logos') || '{}');
        } catch (e) {
            return {};
        }
    }
};

const LEAGUE_FLAGS = {
    'premier_league': '🏴\u200d󠁢\u200d󠁥\u200d󠁢\u200d󠁧\u200d󠁿',
    'la_liga': '🇪🇸',
    'serie_a': '🇮🇹',
    'bundesliga': '🇩🇪',
    'ligue_1': '🇫🇷'
};

let databaseTeams = [];

async function init() {
    const container = document.getElementById('fixtures-container');
    const versionTag = document.getElementById('version-tag');

    try {
        // Fetch match database for autocomplete
        try {
            const dbResponse = await fetch('match_database.json');
            if (dbResponse.ok) {
                const dbData = await dbResponse.json();
                const teamsSet = new Set();
                dbData.forEach(entry => {
                    if (entry.team) teamsSet.add(entry.team);
                    if (entry.opponent) teamsSet.add(entry.opponent);
                });
                databaseTeams = Array.from(teamsSet).sort();
            }
        } catch (e) {
            console.error('Failed to load match_database.json for autocomplete', e);
        }

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

function escapeHtmlAttr(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#39;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;');
}

function renderBadgeHTML(teamName) {
    const logoUrl = TeamIdentityStore.getLogo(teamName);
    const initials = getInitials(teamName);
    const color = getColor(teamName);
    if (logoUrl) {
        const escapedUrl = escapeHtmlAttr(logoUrl);
        const escapedTeam = escapeHtmlAttr(teamName);
        return `<div class="team-badge with-logo" data-team="${escapedTeam}" title="Click to edit logo"><img src="${escapedUrl}" alt="${escapedTeam}" onerror="handleLogoError(this, '${escapedTeam}')"></div>`;
    }
    const escapedTeam = escapeHtmlAttr(teamName);
    return `<div class="team-badge" style="background-color: ${color}" data-team="${escapedTeam}" title="Click to edit logo">${initials}</div>`;
}

function handleLogoError(img, teamName) {
    // If logo fails to load, gracefully fall back to the initials placeholder
    const container = img.parentElement;
    if (container) {
        container.classList.remove('with-logo');
        container.style.backgroundColor = getColor(teamName);
        container.textContent = getInitials(teamName);
    }
}

function createFixtureCard(fixture, scaleMax, metric) {
    const card = document.createElement('div');
    card.className = 'fixture-card';

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
                ${renderBadgeHTML(fixture.home_team)}
                <div class="team-name">${fixture.home_team}</div>
            </div>
            <div class="xg-center">
                <div class="combined-xg-label">${combinedLabel}</div>
                <div class="combined-xg">${combinedVal.toFixed(2)}</div>
                <div class="split-xg">${homeExpectedVal.toFixed(2)} - ${awayExpectedVal.toFixed(2)}</div>
            </div>
            <div class="team">
                ${renderBadgeHTML(fixture.away_team)}
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

function getAutocompleteDataset() {
    const dataset = new Set();
    databaseTeams.forEach(t => dataset.add(t));
    const logos = TeamIdentityStore.getAllLogos();
    Object.keys(logos).forEach(t => dataset.add(t));
    fetchedTeams.forEach(t => dataset.add(t));
    return Array.from(dataset).sort();
}

function setupAutocomplete(input, listContainer) {
    let currentFocus = -1;

    function renderMatches(val) {
        listContainer.innerHTML = '';
        const dataset = getAutocompleteDataset();
        const matches = val
            ? dataset.filter(team => team.toLowerCase().includes(val.toLowerCase()))
            : (fetchedTeams.length > 0 ? fetchedTeams : []);

        if (matches.length === 0) {
            listContainer.classList.add('hidden');
            return;
        }

        listContainer.classList.remove('hidden');

        matches.forEach((team, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            if (index === currentFocus) {
                item.classList.add('autocomplete-active');
            }

            const logoUrl = TeamIdentityStore.getLogo(team);
            const initials = getInitials(team);
            const color = getColor(team);

            let badgeHTML = '';
            if (logoUrl) {
                const escapedUrl = escapeHtmlAttr(logoUrl);
                const escapedTeam = escapeHtmlAttr(team);
                badgeHTML = `<div class="mini-badge"><img src="${escapedUrl}" alt="" onerror="handleLogoError(this, '${escapedTeam}')"></div>`;
            } else {
                badgeHTML = `<div class="mini-badge" style="background-color: ${color}">${initials}</div>`;
            }

            let boldedName = team;
            if (val) {
                const startIdx = team.toLowerCase().indexOf(val.toLowerCase());
                if (startIdx >= 0) {
                    const prefix = team.substring(0, startIdx);
                    const matchPart = team.substring(startIdx, startIdx + val.length);
                    const suffix = team.substring(startIdx + val.length);
                    boldedName = `${prefix}<strong>${matchPart}</strong>${suffix}`;
                }
            }

            item.innerHTML = `${badgeHTML}<span>${boldedName}</span>`;

            item.addEventListener('mousedown', function(e) {
                // Prevent input blur before click registers
                e.preventDefault();
                input.value = team;
                closeAllLists();
            });

            listContainer.appendChild(item);
        });
    }

    input.addEventListener('input', function() {
        currentFocus = -1;
        renderMatches(this.value);
    });

    input.addEventListener('focus', function() {
        currentFocus = -1;
        renderMatches(this.value);
    });

    input.addEventListener('blur', function() {
        // Delay to allow mousedown to register clicks
        setTimeout(() => {
            closeAllLists();
        }, 150);
    });

    input.addEventListener('keydown', function(e) {
        let items = listContainer.getElementsByClassName('autocomplete-item');
        if (e.keyCode === 40) { // Arrow Down
            e.preventDefault();
            currentFocus++;
            addActive(items);
        } else if (e.keyCode === 38) { // Arrow Up
            e.preventDefault();
            currentFocus--;
            addActive(items);
        } else if (e.keyCode === 13) { // Enter
            e.preventDefault();
            if (currentFocus > -1) {
                if (items[currentFocus]) {
                    const teamSpan = items[currentFocus].querySelector('span');
                    if (teamSpan) {
                        input.value = teamSpan.textContent;
                    }
                    closeAllLists();
                }
            } else if (items.length > 0) {
                const teamSpan = items[0].querySelector('span');
                if (teamSpan) {
                    input.value = teamSpan.textContent;
                }
                closeAllLists();
            }
        }
    });

    function addActive(items) {
        if (!items) return false;
        removeActive(items);
        if (currentFocus >= items.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = items.length - 1;
        items[currentFocus].classList.add('autocomplete-active');
        items[currentFocus].scrollIntoView({ block: 'nearest' });
    }

    function removeActive(items) {
        for (let i = 0; i < items.length; i++) {
            items[i].classList.remove('autocomplete-active');
        }
    }

    function closeAllLists() {
        listContainer.innerHTML = '';
        listContainer.classList.add('hidden');
    }
}

function setupSemiAutoHandlers() {
    const leagueSelect = document.getElementById('semi-league-select');
    const htmlPaste = document.getElementById('semi-html-paste');
    const fetchBtn = document.getElementById('semi-fetch-btn');
    const teamGroup = document.getElementById('semi-team-selection-group');
    const homeTeamSelect = document.getElementById('semi-home-team-select');
    const awayTeamSelect = document.getElementById('semi-away-team-select');
    const homeList = document.getElementById('semi-home-autocomplete-list');
    const awayList = document.getElementById('semi-away-autocomplete-list');
    const predictBtn = document.getElementById('semi-predict-btn');
    const resultDiv = document.getElementById('semi-prediction-result');

    if (!fetchBtn) return;

    // Initialize autocomplete on inputs
    setupAutocomplete(homeTeamSelect, homeList);
    setupAutocomplete(awayTeamSelect, awayList);

    // Reset teams when league changes
    leagueSelect.addEventListener('change', () => {
        teamGroup.classList.add('hidden');
        predictBtn.classList.add('hidden');
        homeTeamSelect.value = '';
        awayTeamSelect.value = '';
        resultDiv.innerHTML = '';
        fetchedTeams = [];
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
        homeTeamSelect.value = '';
        awayTeamSelect.value = '';

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

            teamGroup.classList.remove('hidden');
            predictBtn.classList.remove('hidden');

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error fetching teams: ${err.message}`, 'error');
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.textContent = 'Load Teams';
        }
    });

    predictBtn.addEventListener('click', async () => {
        const league = leagueSelect.value;
        const homeTeam = homeTeamSelect.value.trim();
        const awayTeam = awayTeamSelect.value.trim();

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
                away_team: awayTeam
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
            const cardFixture = {
                home_team: prediction.home_team,
                away_team: prediction.away_team,
                home_expected_xg: prediction.home_expected_xg,
                away_expected_xg: prediction.away_expected_xg,
                combined_expected_xg: prediction.combined_expected_xg,
                home_last_xg_matches: prediction.home_last_xg_matches,
                away_last_xg_matches: prediction.away_last_xg_matches,
                date: 'Upcoming Prediction'
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

// Badge click and real-time update handling
function setupBadgeLogoPrompt() {
    // Click event delegation for team badges
    document.addEventListener('click', (e) => {
        const badge = e.target.closest('.team-badge');
        if (!badge) return;

        const teamName = badge.getAttribute('data-team');
        if (!teamName) return;

        const currentLogo = TeamIdentityStore.getLogo(teamName) || '';
        const newLogoUrl = prompt(`Enter logo URL for ${teamName} (leave blank to clear):`, currentLogo);

        if (newLogoUrl !== null) {
            const cleanUrl = newLogoUrl.trim();
            TeamIdentityStore.setLogo(teamName, cleanUrl || null);
        }
    });

    // Listen for custom 'team-logo-updated' event to update UI in real-time
    window.addEventListener('team-logo-updated', (e) => {
        const { teamName, url } = e.detail;

        const escapedTeam = escapeHtmlAttr(teamName);
        // Find all badges for this team on the page and update them
        document.querySelectorAll(`.team-badge[data-team="${escapedTeam}"]`).forEach(badge => {
            if (url) {
                const escapedUrl = escapeHtmlAttr(url);
                badge.classList.add('with-logo');
                badge.style.backgroundColor = '';
                badge.innerHTML = `<img src="${escapedUrl}" alt="${escapedTeam}" onerror="handleLogoError(this, '${escapedTeam}')">`;
            } else {
                badge.classList.remove('with-logo');
                badge.style.backgroundColor = getColor(teamName);
                badge.textContent = getInitials(teamName);
            }
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    init();
    setupTheme();
    setupModeToggle();
    setupSemiAutoHandlers();
    setupBadgeLogoPrompt();
});
