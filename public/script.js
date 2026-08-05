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
                ${renderBadgeHtml(fixture.home_team)}
                <div class="team-name">${fixture.home_team}</div>
            </div>
            <div class="xg-center">
                <div class="combined-xg-label">${combinedLabel}</div>
                <div class="combined-xg">${combinedVal.toFixed(2)}</div>
                <div class="split-xg">${homeExpectedVal.toFixed(2)} - ${awayExpectedVal.toFixed(2)}</div>
            </div>
            <div class="team">
                ${renderBadgeHtml(fixture.away_team)}
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

function getTeamLogo(teamName) {
    if (!teamName) return null;
    try {
        const teamLogos = JSON.parse(localStorage.getItem('team_logos') || '{}');
        return teamLogos[teamName] || null;
    } catch (e) {
        return null;
    }
}

function renderBadgeHtml(teamName) {
    const initials = getInitials(teamName);
    const color = getColor(teamName);
    const logoUrl = getTeamLogo(teamName);
    if (logoUrl) {
        return `<div class="team-badge" data-team="${teamName}" style="background-color: transparent;" title="Click to change team logo"><img src="${logoUrl}" alt="${initials}"></div>`;
    } else {
        return `<div class="team-badge" data-team="${teamName}" style="background-color: ${color}" title="Click to change team logo">${initials}</div>`;
    }
}

let allTeamNames = new Set();

async function loadTeamNames() {
    try {
        const response = await fetch('match_database.json');
        if (response.ok) {
            const matches = await response.json();
            matches.forEach(m => {
                if (m.team) allTeamNames.add(m.team);
                if (m.opponent) allTeamNames.add(m.opponent);
            });
        }
    } catch (e) {
        console.error('Failed to load match_database.json', e);
    }

    // Add any names that have been given a logo in localStorage
    try {
        const teamLogos = JSON.parse(localStorage.getItem('team_logos') || '{}');
        Object.keys(teamLogos).forEach(name => allTeamNames.add(name));
    } catch (e) {}

    updateAutocompleteDatalist();
}

function updateAutocompleteDatalist() {
    let datalist = document.getElementById('team-names-datalist');
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = 'team-names-datalist';
        document.body.appendChild(datalist);
    }

    datalist.innerHTML = '';

    // Sort team names alphabetically
    const sortedNames = Array.from(allTeamNames).sort();
    sortedNames.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        datalist.appendChild(option);
    });

    // Wire it up to the existing inputs if they exist
    const homeInput = document.getElementById('manual-home-name');
    const awayInput = document.getElementById('manual-away-name');
    if (homeInput) {
        homeInput.setAttribute('list', 'team-names-datalist');
    }
    if (awayInput) {
        awayInput.setAttribute('list', 'team-names-datalist');
    }
}

function setupLogoClickHandlers() {
    document.body.addEventListener('click', (e) => {
        const badge = e.target.closest('.team-badge');
        if (badge) {
            const teamName = badge.dataset.team;
            if (!teamName) return;

            let teamLogos = {};
            try {
                teamLogos = JSON.parse(localStorage.getItem('team_logos') || '{}');
            } catch (err) {}

            const currentLogoUrl = teamLogos[teamName] || '';
            const newLogoUrl = prompt(`Enter custom logo URL for ${teamName} (leave blank to remove):`, currentLogoUrl);
            if (newLogoUrl === null) return; // User cancelled

            const trimmedLogoUrl = newLogoUrl.trim();
            if (trimmedLogoUrl) {
                teamLogos[teamName] = trimmedLogoUrl;
            } else {
                delete teamLogos[teamName];
            }

            try {
                localStorage.setItem('team_logos', JSON.stringify(teamLogos));
            } catch (err) {}

            // Propagate across all badges of this team in real-time
            const badges = document.querySelectorAll(`[data-team="${teamName}"]`);
            const initials = getInitials(teamName);
            badges.forEach(b => {
                if (trimmedLogoUrl) {
                    b.style.backgroundColor = 'transparent';
                    b.innerHTML = `<img src="${trimmedLogoUrl}" alt="${initials}">`;
                } else {
                    b.style.backgroundColor = getColor(teamName);
                    b.innerHTML = initials;
                }
            });

            // Also add team to autocomplete Set and update datalist in case this was a newly seen team name
            if (typeof allTeamNames !== 'undefined' && !allTeamNames.has(teamName)) {
                allTeamNames.add(teamName);
                if (typeof updateAutocompleteDatalist === 'function') {
                    updateAutocompleteDatalist();
                }
            }
        }
    });
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
let homeOverrides = {};
let awayOverrides = {};
let currentPrediction = null;

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
    if (!leagueSelect || leagueSelect.querySelector('option[value="mls"]')) return; // Already loaded

    function populateLeagues(leagues) {
        // Insert leagues before the manual option
        const manualOpt = leagueSelect.querySelector('option[value="manual"]');
        leagues.forEach(l => {
            const opt = document.createElement('option');
            opt.value = l.id;
            opt.textContent = `${l.flag} ${l.name}`;
            if (manualOpt) {
                leagueSelect.insertBefore(opt, manualOpt);
            } else {
                leagueSelect.appendChild(opt);
            }
        });
    }

    try {
        const res = await fetch('/api/leagues');
        if (!res.ok) throw new Error('Failed to fetch leagues list');
        let leagues;
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            leagues = await res.json();
        } else {
            throw new Error(`Invalid response format: HTTP ${res.status} ${res.statusText}`);
        }
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

// Client-side chronological tier-based weight redistribution logic
function getTiers(methodologyId, numMatches) {
    if (numMatches === 0) return [];
    if (methodologyId === 1) {
        return [{
            indices: Array.from({length: numMatches}, (_, i) => i),
            target_weight: 1.0
        }];
    } else if (methodologyId === 2) {
        if (numMatches <= 4) {
            return [{
                indices: Array.from({length: numMatches}, (_, i) => i),
                target_weight: 1.0
            }];
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
            const weights = [];
            for (let i = 0; i < numMatches; i++) {
                if (i < 4) {
                    weights.push(0.70 / 4);
                } else {
                    weights.push(0.30 / (numMatches - 4));
                }
            }
            return weights;
        }
    }
    return [];
}

function normalizeWeights(numMatches, defaultWeights, overrides, methodologyId) {
    if (numMatches === 0) return [];
    const weights = [...defaultWeights];
    const tiers = getTiers(methodologyId, numMatches);

    for (const tier of tiers) {
        const tierIndices = tier.indices;
        const targetTotal = tier.target_weight;

        const overriddenIndices = [];
        const unoverriddenIndices = [];

        for (const idx of tierIndices) {
            if (overrides !== null && overrides !== undefined && (idx in overrides || String(idx) in overrides)) {
                let val = overrides[idx] !== undefined ? overrides[idx] : overrides[String(idx)];
                val = parseFloat(val);
                if (isNaN(val)) val = 0.0;
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

function parsePastedLine(line1, line2, line3, teamName, skipXG) {
    if (!line1 || !line2 || !line3) return null;
    line1 = line1.trim();
    line2 = line2.trim();
    line3 = line3.trim();

    // 1. From line 1: extract the opponent name (strip the trailing league-position ordinal, e.g. "6th")
    const opponent = line1.replace(/\s+\d+(?:st|nd|rd|th)\s*$/i, '').trim() || 'Unknown Opponent';

    // 2. From line 2: extract venue from leading (H)/(A) and parse date
    let venue = 'home';
    const venueMatch = line2.match(/^\s*\(?(H|A)\)?/i);
    if (venueMatch && venueMatch[1].toUpperCase() === 'A') {
        venue = 'away';
    }

    // Parse the date e.g. "26th Jul"
    let date = new Date().toISOString().split('T')[0];
    const dateMatch = line2.match(/(\d+)(?:st|nd|rd|th)\s+([A-Za-z]{3,})/i);
    if (dateMatch) {
        const day = parseInt(dateMatch[1]);
        const monthAbbr = dateMatch[2].toLowerCase();
        const months = {
            jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
            jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11
        };
        if (months[monthAbbr] !== undefined) {
            const monthIndex = months[monthAbbr];
            const now = new Date();
            const currentMonthIndex = now.getMonth();
            const currentYear = now.getFullYear();
            let year = currentYear;
            if (monthIndex > currentMonthIndex) {
                year = currentYear - 1;
            }
            const formattedMonth = String(monthIndex + 1).padStart(2, '0');
            const formattedDay = String(day).padStart(2, '0');
            date = `${year}-${formattedMonth}-${formattedDay}`;
        }
    }

    // 3. From line 3: parse score (FOR-AGAINST), e.g. "2.5-1.8"
    const scoreMatch = line3.match(/(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)/);
    if (!scoreMatch) return null;
    const rawVal1 = parseFloat(scoreMatch[1]);
    const rawVal2 = parseFloat(scoreMatch[2]);

    // Apply venue flip!
    // If venue is (A), the RIGHT-hand number is this team's own value (for), left is against.
    // If (H), left is for, right is against.
    let valFor, valAgainst;
    let flipApplied = false;
    if (venue === 'away') {
        valFor = rawVal2;
        valAgainst = rawVal1;
        flipApplied = true;
    } else {
        valFor = rawVal1;
        valAgainst = rawVal2;
    }

    // Sanity checks
    const warnings = [];
    if (valFor < 0 || valAgainst < 0) {
        warnings.push('Negative numbers are implausible.');
    }
    if (skipXG) {
        if (valFor > 12) warnings.push(`Implausibly high Goals for: ${valFor}`);
        if (valAgainst > 12) warnings.push(`Implausibly high Goals against: ${valAgainst}`);
        if (!Number.isInteger(valFor) || !Number.isInteger(valAgainst)) {
            warnings.push('Goals are typically integers.');
        }
    } else {
        if (valFor > 7.0) warnings.push(`Implausibly high xG for: ${valFor}`);
        if (valAgainst > 7.0) warnings.push(`Implausibly high xG against: ${valAgainst}`);
    }

    return {
        opponent,
        venue,
        date,
        valFor,
        valAgainst,
        flipApplied,
        rawVal1,
        rawVal2,
        warnings,
        rawLine: `${line1} | ${line2} | ${line3}`
    };
}

function renderParsedMatches(parsedMatches, containerEl, teamName, skipXG) {
    containerEl.innerHTML = '';
    if (parsedMatches.length === 0) {
        containerEl.innerHTML = '<div class="no-matches-parsed">No valid matches parsed. Please check the paste format.</div>';
        return;
    }

    parsedMatches.forEach((m, idx) => {
        const item = document.createElement('div');
        item.className = 'parsed-match-item';

        let warningsHtml = '';
        if (m.warnings.length > 0) {
            warningsHtml = `
                <div class="parsed-warnings">
                    ⚠️ Warning: ${m.warnings.join(' ')}
                </div>
            `;
        }

        const metricLabel = skipXG ? 'Goals' : 'xG';
        const flipText = m.flipApplied
            ? `<strong>Venue flip applied (Away Match):</strong> Right-hand value (${m.rawVal2}) is FOR, left-hand value (${m.rawVal1}) is AGAINST.`
            : `<strong>No flip applied (Home Match):</strong> Left-hand value (${m.rawVal1}) is FOR, right-hand value (${m.rawVal2}) is AGAINST.`;

        item.innerHTML = `
            <div class="parsed-match-header">
                <span class="match-index">Match #${idx + 1}</span>
                <span class="match-date">${m.date}</span>
            </div>
            <div class="parsed-match-details">
                <p>Opponent: <strong>${m.opponent}</strong></p>
                <p>Venue: <strong>${m.venue.charAt(0).toUpperCase() + m.venue.slice(1)}</strong></p>
                <p>Derived ${metricLabel} FOR: <strong class="derived-value">${m.valFor.toFixed(2)}</strong></p>
                <p>Derived ${metricLabel} AGAINST: <strong class="derived-value">${m.valAgainst.toFixed(2)}</strong></p>
                <p class="flip-explanation">${flipText}</p>
            </div>
            ${warningsHtml}
        `;
        containerEl.appendChild(item);
    });
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

    // Manual Paste wizard elements
    const standardFields = document.getElementById('semi-standard-fields');
    const manualWizard = document.getElementById('semi-manual-wizard');

    // Wizard Step buttons & inputs
    const manualLeagueName = document.getElementById('manual-league-name');
    const manualHomeName = document.getElementById('manual-home-name');
    const manualAwayName = document.getElementById('manual-away-name');
    const manualSkipXG = document.getElementById('manual-skip-xg');

    const manualToStep2Btn = document.getElementById('manual-to-step-2');
    const manualBackToStep1Btn = document.getElementById('manual-back-to-step-1');
    const manualToStep3Btn = document.getElementById('manual-to-step-3');
    const manualBackToStep2Btn = document.getElementById('manual-back-to-step-2');
    const manualToStep4Btn = document.getElementById('manual-to-step-4');
    const manualBackToStep3Btn = document.getElementById('manual-back-to-step-3');
    const manualToStep5Btn = document.getElementById('manual-to-step-5');
    const manualBackToStep4Btn = document.getElementById('manual-back-to-step-4');
    const manualSavePredictBtn = document.getElementById('manual-save-predict');

    const manualHomePaste = document.getElementById('manual-home-paste');
    const manualAwayPaste = document.getElementById('manual-away-paste');
    const manualHomeParsedList = document.getElementById('manual-home-parsed-list');
    const manualAwayParsedList = document.getElementById('manual-away-parsed-list');

    // Step Divs
    const step1Div = document.getElementById('manual-step-1');
    const step2Div = document.getElementById('manual-step-2');
    const step3Div = document.getElementById('manual-step-3');
    const step4Div = document.getElementById('manual-step-4');
    const step5Div = document.getElementById('manual-step-5');

    // Manual Wizard State
    let parsedHomeMatches = [];
    let parsedAwayMatches = [];

    function showStep(stepNum) {
        [step1Div, step2Div, step3Div, step4Div, step5Div].forEach((div, idx) => {
            if (idx + 1 === stepNum) {
                div.classList.remove('hidden');
            } else {
                div.classList.add('hidden');
            }
        });
    }

    if (!fetchBtn) return;

    // Reset teams when league changes
    leagueSelect.addEventListener('change', () => {
        const val = leagueSelect.value;
        if (val === 'manual') {
            standardFields.classList.add('hidden');
            manualWizard.classList.remove('hidden');
            showStep(1);
        } else {
            standardFields.classList.remove('hidden');
            manualWizard.classList.add('hidden');

            teamGroup.classList.add('hidden');
            predictBtn.classList.add('hidden');
            homeTeamSelect.innerHTML = '<option value="">-- Choose Home Team --</option>';
            awayTeamSelect.innerHTML = '<option value="">-- Choose Away Team --</option>';
            resultDiv.innerHTML = '';
            fetchedTeams = [];
        }
    });

    // Wizard navigation & parsing logic
    manualToStep2Btn.addEventListener('click', () => {
        const leagueName = manualLeagueName.value.trim();
        const homeName = manualHomeName.value.trim();
        const awayName = manualAwayName.value.trim();

        if (!leagueName || !homeName || !awayName) {
            showSemiAlert('Please provide League Name, Home Team Name, and Away Team Name.', 'error');
            return;
        }
        if (homeName.toLowerCase() === awayName.toLowerCase()) {
            showSemiAlert('Home and Away teams must be different.', 'error');
            return;
        }

        // Clear alerts
        resultDiv.innerHTML = '';

        // Update titles
        document.getElementById('manual-home-title').textContent = `Step 2: ${homeName} History`;
        document.getElementById('manual-home-confirm-title').textContent = `Confirm ${homeName} Matches`;
        document.getElementById('manual-away-title').textContent = `Step 4: ${awayName} History`;
        document.getElementById('manual-away-confirm-title').textContent = `Confirm ${awayName} Matches`;

        showStep(2);
    });

    manualBackToStep1Btn.addEventListener('click', () => {
        showStep(1);
    });

    manualToStep3Btn.addEventListener('click', () => {
        const pasteVal = manualHomePaste.value.trim();
        if (!pasteVal) {
            showSemiAlert('Please paste Home Team matches history.', 'error');
            return;
        }

        // Clear alerts
        resultDiv.innerHTML = '';

        const lines = pasteVal.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        parsedHomeMatches = [];
        for (let i = 0; i < lines.length; i += 3) {
            if (i + 2 < lines.length) {
                const parsed = parsePastedLine(lines[i], lines[i+1], lines[i+2], manualHomeName.value.trim(), manualSkipXG.checked);
                if (parsed) {
                    parsedHomeMatches.push(parsed);
                }
            }
        }

        if (parsedHomeMatches.length === 0) {
            showSemiAlert('Could not parse any valid match records. Please verify format (3 lines per match):\nLine 1: Opponent Name (e.g. Brann 6th)\nLine 2: Venue and Date (e.g. (A) 26th Jul)\nLine 3: Scores (e.g. 2.5-1.8)', 'error');
            return;
        }

        renderParsedMatches(parsedHomeMatches, manualHomeParsedList, manualHomeName.value.trim(), manualSkipXG.checked);
        showStep(3);
    });

    manualBackToStep2Btn.addEventListener('click', () => {
        showStep(2);
    });

    manualToStep4Btn.addEventListener('click', () => {
        showStep(4);
    });

    manualBackToStep3Btn.addEventListener('click', () => {
        showStep(3);
    });

    manualToStep5Btn.addEventListener('click', () => {
        const pasteVal = manualAwayPaste.value.trim();
        if (!pasteVal) {
            showSemiAlert('Please paste Away Team matches history.', 'error');
            return;
        }

        // Clear alerts
        resultDiv.innerHTML = '';

        const lines = pasteVal.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        parsedAwayMatches = [];
        for (let i = 0; i < lines.length; i += 3) {
            if (i + 2 < lines.length) {
                const parsed = parsePastedLine(lines[i], lines[i+1], lines[i+2], manualAwayName.value.trim(), manualSkipXG.checked);
                if (parsed) {
                    parsedAwayMatches.push(parsed);
                }
            }
        }

        if (parsedAwayMatches.length === 0) {
            showSemiAlert('Could not parse any valid match records. Please verify format (3 lines per match):\nLine 1: Opponent Name (e.g. Brann 6th)\nLine 2: Venue and Date (e.g. (A) 26th Jul)\nLine 3: Scores (e.g. 2.5-1.8)', 'error');
            return;
        }

        renderParsedMatches(parsedAwayMatches, manualAwayParsedList, manualAwayName.value.trim(), manualSkipXG.checked);
        showStep(5);
    });

    manualBackToStep4Btn.addEventListener('click', () => {
        showStep(4);
    });

    manualSavePredictBtn.addEventListener('click', async () => {
        const leagueName = manualLeagueName.value.trim();
        const leagueId = leagueName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        const homeTeam = manualHomeName.value.trim();
        const awayTeam = manualAwayName.value.trim();
        const skipXG = manualSkipXG.checked;

        manualSavePredictBtn.disabled = true;
        manualSavePredictBtn.textContent = 'Saving Matches...';

        try {
            // Save manual matches
            const saveRes = await fetch('/api/save_manual', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    league_id: leagueId,
                    league_name: leagueName,
                    home_team: homeTeam,
                    away_team: awayTeam,
                    skip_xg: skipXG,
                    home_matches: parsedHomeMatches,
                    away_matches: parsedAwayMatches
                })
            });

            if (!saveRes.ok) {
                let errorMsg = `HTTP ${saveRes.status} ${saveRes.statusText}`;
                try {
                    const contentType = saveRes.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const saveError = await saveRes.json();
                        errorMsg = saveError.error || errorMsg;
                    } else {
                        await saveRes.text(); // consume body
                    }
                } catch (e) {
                    // Ignore parse errors
                }
                throw new Error(`Failed to save matches: ${errorMsg}`);
            }

            manualSavePredictBtn.textContent = 'Calculating Prediction...';

            // Calculate prediction
            const metric = skipXG ? 'goals' : 'xg';
            const predRes = await fetch(`/api/predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    league: leagueId,
                    home_team: homeTeam,
                    away_team: awayTeam,
                    metric: metric,
                    methodology: 2
                })
            });

            if (!predRes.ok) {
                let errorMsg = `HTTP ${predRes.status} ${predRes.statusText}`;
                try {
                    const contentType = predRes.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const predError = await predRes.json();
                        errorMsg = predError.error || errorMsg;
                    } else {
                        await predRes.text(); // consume body
                    }
                } catch (e) {
                    // Ignore parse errors
                }
                throw new Error(`Failed to compute prediction: ${errorMsg}`);
            }

            let prediction;
            const predContentType = predRes.headers.get('content-type');
            if (predContentType && predContentType.includes('application/json')) {
                prediction = await predRes.json();
            } else {
                throw new Error(`Invalid response format: HTTP ${predRes.status} ${predRes.statusText}`);
            }
            resultDiv.innerHTML = '';

            // Render prediction beautifully!
            const metricSuffix = skipXG ? 'goals' : 'xg';
            const cardFixture = {
                home_team: prediction.home_team,
                away_team: prediction.away_team,
                date: 'Upcoming Manual Prediction'
            };
            cardFixture[`home_expected_${metricSuffix}`] = prediction[`home_expected_${metricSuffix}`];
            cardFixture[`away_expected_${metricSuffix}`] = prediction[`away_expected_${metricSuffix}`];
            cardFixture[`combined_expected_${metricSuffix}`] = prediction[`combined_expected_${metricSuffix}`];
            cardFixture[`home_last_${metricSuffix}_matches`] = prediction[`home_last_${metricSuffix}_matches`].map(m => ({
                opponent: m.opponent,
                [`${metricSuffix}_for`]: m[`${metricSuffix}_for`],
                [`${metricSuffix}_against`]: m[`${metricSuffix}_against`]
            }));
            cardFixture[`away_last_${metricSuffix}_matches`] = prediction[`away_last_${metricSuffix}_matches`].map(m => ({
                opponent: m.opponent,
                [`${metricSuffix}_for`]: m[`${metricSuffix}_for`],
                [`${metricSuffix}_against`]: m[`${metricSuffix}_against`]
            }));

            const maxVal = Math.max(prediction[`home_expected_${metricSuffix}`], prediction[`away_expected_${metricSuffix}`]);
            const scaleMax = Math.max(maxVal * 1.1, 3.0);

            const card = createFixtureCard(cardFixture, scaleMax, metricSuffix);
            resultDiv.appendChild(card);

            showSemiAlert('Prediction successfully calculated and saved!', 'success');

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error: ${err.message}`, 'error');
        } finally {
            manualSavePredictBtn.disabled = false;
            manualSavePredictBtn.textContent = 'Save & Predict';
        }
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

            let data;
            const resContentType = res.headers.get('content-type');
            if (resContentType && resContentType.includes('application/json')) {
                data = await res.json();
            } else {
                throw new Error(`Invalid response format: HTTP ${res.status} ${res.statusText}`);
            }
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
            predictBtn.classList.remove('hidden');

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error fetching teams: ${err.message}`, 'error');
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.textContent = 'Load Teams';
        }
    });

    let lastLeague = '';
    let lastHomeTeam = '';
    let lastAwayTeam = '';
    let lastMethodology = '';

    async function calculateSemiPrediction(useOverrides = true) {
        const league = leagueSelect.value;
        const homeTeam = homeTeamSelect.value;
        const awayTeam = awayTeamSelect.value;
        const methodology = parseInt(document.getElementById('semi-methodology-select').value);
        const metric = document.getElementById('semi-metric-select').value;

        if (!league || !homeTeam || !awayTeam) {
            showSemiAlert('Please select both Home and Away teams to calculate predictions.', 'error');
            return;
        }

        if (homeTeam.toLowerCase() === awayTeam.toLowerCase()) {
            showSemiAlert('Home and Away teams must be different.', 'error');
            return;
        }

        // Reset overrides if the fixture or methodology changed
        if (league !== lastLeague || homeTeam !== lastHomeTeam || awayTeam !== lastAwayTeam || methodology !== lastMethodology) {
            if (!useOverrides) {
                homeOverrides = {};
                awayOverrides = {};
            }
            lastLeague = league;
            lastHomeTeam = homeTeam;
            lastAwayTeam = awayTeam;
            lastMethodology = methodology;
        }

        predictBtn.disabled = true;
        predictBtn.textContent = 'Calculating Prediction...';

        const pastedHtml = htmlPaste.value.trim();

        try {
            const payload = {
                league,
                home_team: homeTeam,
                away_team: awayTeam,
                methodology: methodology,
                metric: metric,
                home_overrides: homeOverrides,
                away_overrides: awayOverrides
            };

            if (pastedHtml) {
                payload.html = pastedHtml;
            }

            const res = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                let errorMsg = `HTTP ${res.status} ${res.statusText}`;
                try {
                    const contentType = res.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await res.json();
                        errorMsg = errorData.error || errorMsg;
                    } else {
                        await res.text(); // consume body
                    }
                } catch (e) {
                    // Ignore parse errors
                }
                throw new Error(`Server error computing prediction: ${errorMsg}`);
            }

            let prediction;
            const predContentType2 = res.headers.get('content-type');
            if (predContentType2 && predContentType2.includes('application/json')) {
                prediction = await res.json();
            } else {
                throw new Error(`Invalid response format: HTTP ${res.status} ${res.statusText}`);
            }
            currentPrediction = prediction;

            renderSemiPredictionResult(prediction, methodology, metric);

        } catch (err) {
            console.error(err);
            showSemiAlert(`Error calculating prediction: ${err.message}`, 'error');
        } finally {
            predictBtn.disabled = false;
            predictBtn.textContent = 'Calculate Prediction';
        }
    }

    function renderSemiPredictionResult(prediction, activeMethodology, activeMetric) {
        resultDiv.innerHTML = '';

        // 1. Render primary prediction card
        const metricSuffix = activeMetric === 'xg' ? 'xg' : 'goals';

        // Set dynamic scaleMax
        const homeVal = prediction[`home_expected_${metricSuffix}`] || prediction.home_expected || 0;
        const awayVal = prediction[`away_expected_${metricSuffix}`] || prediction.away_expected || 0;
        const maxVal = Math.max(homeVal, awayVal);
        const scaleMax = Math.max(maxVal * 1.1, 3.0);

        const cardFixture = {
            home_team: prediction.home_team,
            away_team: prediction.away_team,
            date: 'Upcoming Prediction'
        };
        cardFixture[`home_expected_${metricSuffix}`] = homeVal;
        cardFixture[`away_expected_${metricSuffix}`] = awayVal;
        cardFixture[`combined_expected_${metricSuffix}`] = homeVal + awayVal;

        // Find historical matches array to show on the primary card
        const homeMatchesArr = prediction[`home_last_${metricSuffix}_matches`] || [];
        const awayMatchesArr = prediction[`away_last_${metricSuffix}_matches`] || [];

        cardFixture[`home_last_${metricSuffix}_matches`] = homeMatchesArr;
        cardFixture[`away_last_${metricSuffix}_matches`] = awayMatchesArr;

        const card = createFixtureCard(cardFixture, scaleMax, metricSuffix);
        resultDiv.appendChild(card);

        // 2. Render comparisons 2x2 grid
        renderComparisonsGrid(prediction.comparisons, activeMethodology, activeMetric, resultDiv);

        // 3. Render interactive match-weight editor
        renderMatchWeightEditor(prediction, activeMethodology, activeMetric, resultDiv);
    }

    function renderComparisonsGrid(comparisons, activeMethodology, activeMetric, parentEl) {
        if (!comparisons) return;

        const title = document.createElement('h3');
        title.className = 'comparisons-grid-title';
        title.textContent = '📊 Methodology Comparisons';
        parentEl.appendChild(title);

        const grid = document.createElement('div');
        grid.className = 'comparisons-grid';

        const items = [
            { mId: 1, mMetric: 'xg', label: 'M1 × xG' },
            { mId: 1, mMetric: 'goals', label: 'M1 × Goals' },
            { mId: 2, mMetric: 'xg', label: 'M2 × xG' },
            { mId: 2, mMetric: 'goals', label: 'M2 × Goals' }
        ];

        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'comparison-card';

            const isActive = (item.mId === activeMethodology && item.mMetric === activeMetric);
            if (isActive) {
                card.classList.add('active');
            }

            const data = comparisons[`methodology_${item.mId}`]?.[item.mMetric];
            let valuesHtml = '';
            if (data) {
                valuesHtml = `
                    <div class="comparison-values">${data.home_expected.toFixed(2)} - ${data.away_expected.toFixed(2)}</div>
                    <div class="comparison-combined">Sum: ${data.combined_expected.toFixed(2)}</div>
                `;
            } else {
                valuesHtml = `<div class="comparison-values">N/A</div>`;
            }

            card.innerHTML = `
                <div class="comparison-title">${item.label} ${isActive ? '⭐' : ''}</div>
                ${valuesHtml}
            `;

            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                document.getElementById('semi-methodology-select').value = String(item.mId);
                document.getElementById('semi-metric-select').value = item.mMetric;
                calculateSemiPrediction(true); // Recalculate using active overrides
            });

            grid.appendChild(card);
        });

        parentEl.appendChild(grid);
    }

    function renderMatchWeightEditor(prediction, activeMethodology, activeMetric, parentEl) {
        const metricSuffix = activeMetric === 'xg' ? 'xg' : 'goals';
        const homeMatches = prediction[`home_last_${metricSuffix}_matches`] || [];
        const awayMatches = prediction[`away_last_${metricSuffix}_matches`] || [];

        const editorCard = document.createElement('div');
        editorCard.className = 'weight-editor-card';
        editorCard.id = 'semi-weight-editor-container';

        editorCard.innerHTML = `
            <h3>⚖️ Interactive Match-Weight Editor</h3>
            <p class="step-desc">Adjust the weights of individual matches below. The remaining matches in the same tier will redistribute proportionally in real time.</p>
            <div class="weight-editor-columns">
                <div class="weight-editor-col" id="editor-home-col">
                    <h4>${prediction.home_team} (Home)</h4>
                    <div class="editor-matches-list" id="editor-home-matches-list"></div>
                </div>
                <div class="weight-editor-col" id="editor-away-col">
                    <h4>${prediction.away_team} (Away)</h4>
                    <div class="editor-matches-list" id="editor-away-matches-list"></div>
                </div>
            </div>
        `;

        parentEl.appendChild(editorCard);

        renderEditorMatchesList(prediction, 'home', homeMatches, activeMethodology);
        renderEditorMatchesList(prediction, 'away', awayMatches, activeMethodology);
    }

    function renderEditorMatchesList(prediction, type, matches, methodologyId) {
        const listContainer = document.getElementById(`editor-${type}-matches-list`);
        listContainer.innerHTML = '';

        if (matches.length === 0) {
            listContainer.innerHTML = '<div class="no-fixtures">No historical matches found.</div>';
            return;
        }

        const overrides = type === 'home' ? homeOverrides : awayOverrides;
        const numMatches = matches.length;
        const defaultWeights = getDefaultWeights(methodologyId, numMatches);

        matches.forEach((m, idx) => {
            const row = document.createElement('div');
            row.className = 'match-weight-row';
            row.id = `editor-${type}-match-${idx}`;

            const currentWeight = m.weight !== undefined ? m.weight : defaultWeights[idx];
            const displayPercent = (currentWeight * 100).toFixed(1) + '%';

            if (currentWeight === 0.0) {
                row.classList.add('zeroed');
            }

            const tiers = getTiers(methodologyId, numMatches);
            const matchTier = tiers.find(tier => tier.indices.includes(idx));
            const targetTotal = matchTier ? matchTier.target_weight : 1.0;

            const goalsFor = m.goals_for !== null && m.goals_for !== undefined ? m.goals_for : '-';
            const goalsAgainst = m.goals_against !== null && m.goals_against !== undefined ? m.goals_against : '-';
            const xgFor = m.xg_for !== null && m.xg_for !== undefined ? m.xg_for.toFixed(2) : '-';
            const xgAgainst = m.xg_against !== null && m.xg_against !== undefined ? m.xg_against.toFixed(2) : '-';

            const venueLabel = m.venue === 'home' ? 'H' : 'A';

            const actionButtonHtml = (currentWeight === 0.0)
                ? `<button class="restore-match-btn" title="Restore Match">🔄 Restore</button>`
                : `<button class="remove-match-btn" title="Remove Match">🗑️ Remove</button>`;

            row.innerHTML = `
                <div class="match-weight-header">
                    <span>vs ${m.opponent} (${venueLabel})</span>
                    <span class="weight-percentage" id="percent-${type}-${idx}">${displayPercent}</span>
                </div>
                <div class="match-weight-details">
                    Date: ${m.date} | Goals: ${goalsFor}-${goalsAgainst} | xG: ${xgFor}-${xgAgainst}
                </div>
                <div class="match-weight-controls">
                    <input type="range" class="weight-slider" id="slider-${type}-${idx}"
                           min="0" max="${targetTotal}" step="0.01" value="${currentWeight}">
                    ${actionButtonHtml}
                </div>
            `;

            const slider = row.querySelector('.weight-slider');
            const removeRestoreBtn = row.querySelector('.remove-match-btn, .restore-match-btn');

            slider.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value);
                overrides[idx] = val;
                updateLiveWeightRedistribution(type, matches, methodologyId);
            });

            slider.addEventListener('change', () => {
                calculateSemiPrediction(true);
            });

            removeRestoreBtn.addEventListener('click', () => {
                if (currentWeight === 0.0) {
                    delete overrides[idx];
                } else {
                    overrides[idx] = 0.0;
                }
                calculateSemiPrediction(true);
            });

            listContainer.appendChild(row);
        });
    }

    function updateLiveWeightRedistribution(type, matches, methodologyId) {
        const overrides = type === 'home' ? homeOverrides : awayOverrides;
        const numMatches = matches.length;
        const defaultWeights = getDefaultWeights(methodologyId, numMatches);
        const redistributedWeights = normalizeWeights(numMatches, defaultWeights, overrides, methodologyId);

        redistributedWeights.forEach((w, idx) => {
            const slider = document.getElementById(`slider-${type}-${idx}`);
            const percentLabel = document.getElementById(`percent-${type}-${idx}`);
            const row = document.getElementById(`editor-${type}-match-${idx}`);

            if (percentLabel) {
                percentLabel.textContent = (w * 100).toFixed(1) + '%';
            }
            if (slider) {
                slider.value = w;
            }
            if (row) {
                if (w === 0.0) {
                    row.classList.add('zeroed');
                    const removeBtn = row.querySelector('.remove-match-btn');
                    if (removeBtn) {
                        removeBtn.outerHTML = `<button class="restore-match-btn" title="Restore Match">🔄 Restore</button>`;
                        const newBtn = row.querySelector('.restore-match-btn');
                        newBtn.addEventListener('click', () => {
                            delete overrides[idx];
                            calculateSemiPrediction(true);
                        });
                    }
                } else {
                    row.classList.remove('zeroed');
                    const restoreBtn = row.querySelector('.restore-match-btn');
                    if (restoreBtn) {
                        restoreBtn.outerHTML = `<button class="remove-match-btn" title="Remove Match">🗑️ Remove</button>`;
                        const newBtn = row.querySelector('.remove-match-btn');
                        newBtn.addEventListener('click', () => {
                            overrides[idx] = 0.0;
                            calculateSemiPrediction(true);
                        });
                    }
                }
            }
        });
    }

    predictBtn.addEventListener('click', () => {
        calculateSemiPrediction(false); // Reset overrides on direct calculation trigger
    });

    const methodologySelect = document.getElementById('semi-methodology-select');
    const metricSelect = document.getElementById('semi-metric-select');

    if (methodologySelect) {
        methodologySelect.addEventListener('change', () => {
            const homeTeam = homeTeamSelect.value;
            const awayTeam = awayTeamSelect.value;
            if (homeTeam && awayTeam) {
                calculateSemiPrediction(false); // Reset overrides on methodology change
            }
        });
    }

    if (metricSelect) {
        metricSelect.addEventListener('change', () => {
            const homeTeam = homeTeamSelect.value;
            const awayTeam = awayTeamSelect.value;
            if (homeTeam && awayTeam) {
                calculateSemiPrediction(true); // Keep overrides on metric change
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    init();
    setupTheme();
    setupModeToggle();
    setupSemiAutoHandlers();
    setupLogoClickHandlers();
    loadTeamNames();
});
