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

function parsePastedLine(line, teamName, skipXG) {
    line = line.trim();
    if (!line) return null;

    // 1. Find date (YYYY-MM-DD) first and extract it to prevent hyphen collision with the score
    const dateMatch = line.match(/\b\d{4}-\d{2}-\d{2}\b/);
    const date = dateMatch ? dateMatch[0] : new Date().toISOString().split('T')[0];

    // Remove the date from the parsing string to avoid regex confusion
    let lineWithoutDate = line;
    if (dateMatch) {
        lineWithoutDate = lineWithoutDate.replace(dateMatch[0], '');
    }

    // 2. Find score/metric values (FOR-AGAINST), e.g. "1.5-2.2" or "1 - 1" or "2-1" from the date-free string
    const scoreMatch = lineWithoutDate.match(/(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)/);
    if (!scoreMatch) return null;
    const rawVal1 = parseFloat(scoreMatch[1]);
    const rawVal2 = parseFloat(scoreMatch[2]);
    const scoreStr = scoreMatch[0];

    // Find venue (H) or (A) or H or A
    let venue = 'home';
    const parenVenueMatch = lineWithoutDate.match(/\((H|A|home|away)\)/i);
    if (parenVenueMatch) {
        const v = parenVenueMatch[1].toUpperCase();
        if (v.startsWith('A')) {
            venue = 'away';
        }
    } else {
        const generalVenueMatch = lineWithoutDate.match(/\b(H|A|home|away)\b/i);
        if (generalVenueMatch) {
            const v = generalVenueMatch[1].toUpperCase();
            if (v.startsWith('A')) {
                venue = 'away';
            }
        }
    }

    // Extract opponent name from the original line to keep formatting where appropriate, minus date/score/venue
    let opponent = line;
    opponent = opponent.replace(scoreStr, '');
    if (dateMatch) {
        opponent = opponent.replace(dateMatch[0], '');
    }
    const venueMatchStr = parenVenueMatch ? parenVenueMatch[0] : (line.match(/\b(H|A|home|away)\b/i) ? line.match(/\b(H|A|home|away)\b/i)[0] : '');
    if (venueMatchStr) {
        opponent = opponent.replace(venueMatchStr, '');
    }
    // Clean up slashes, parentheses, brackets, extra spaces
    opponent = opponent.replace(/[/\(\)\[\]]/g, ' ');
    opponent = opponent.replace(/\s+/g, ' ').trim();
    if (!opponent) {
        opponent = 'Unknown Opponent';
    }

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
        rawLine: line
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

        const lines = pasteVal.split('\n');
        parsedHomeMatches = [];
        lines.forEach(line => {
            const parsed = parsePastedLine(line, manualHomeName.value.trim(), manualSkipXG.checked);
            if (parsed) {
                parsedHomeMatches.push(parsed);
            }
        });

        if (parsedHomeMatches.length === 0) {
            showSemiAlert('Could not parse any valid match records. Please verify format: Opponent / (H/A) date / FOR-AGAINST.', 'error');
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

        const lines = pasteVal.split('\n');
        parsedAwayMatches = [];
        lines.forEach(line => {
            const parsed = parsePastedLine(line, manualAwayName.value.trim(), manualSkipXG.checked);
            if (parsed) {
                parsedAwayMatches.push(parsed);
            }
        });

        if (parsedAwayMatches.length === 0) {
            showSemiAlert('Could not parse any valid match records. Please verify format: Opponent / (H/A) date / FOR-AGAINST.', 'error');
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
                const saveError = await saveRes.json();
                throw new Error(saveError.error || 'Server error saving matches');
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
                const predError = await predRes.json();
                throw new Error(predError.error || 'Server error computing prediction');
            }

            const prediction = await predRes.json();
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
        const homeTeam = homeTeamSelect.value;
        const awayTeam = awayTeamSelect.value;

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

document.addEventListener('DOMContentLoaded', () => {
    init();
    setupTheme();
    setupModeToggle();
    setupSemiAutoHandlers();
});
