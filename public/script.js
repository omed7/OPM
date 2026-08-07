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
    const dateStrip = document.getElementById('date-strip');

    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Failed to fetch data');
        const data = await response.json();

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

        // Build a mapping of all fixtures with normalized dates
        let allFixtures = [];
        data.leagues.forEach(league => {
            if (league.fixtures) {
                league.fixtures.forEach(fixture => {

                    let d;
                    if (fixture.date.length === 10) {
                        d = new Date(fixture.date + "T00:00:00");
                    } else {
                        d = new Date(fixture.date.replace(' ', 'T') + "Z");
                    }
                    // normalize to local date string YYYY-MM-DD
                    const localDateStr = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
                    allFixtures.push({
                        ...fixture,
                        leagueId: league.id,
                        leagueName: league.name,
                        metric: league.metric || 'xg',
                        localDateStr: localDateStr,
                        timeObj: d
                    });
                });
            }
        });

        const today = new Date();
        const todayStr = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');

        let activeDateStr = todayStr;

        function renderDateStrip() {
            dateStrip.innerHTML = '';
            // 7 days window: today - 3 to today + 3
            for (let i = -3; i <= 3; i++) {
                const d = new Date(today);
                d.setDate(today.getDate() + i);

                const dStr = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');

                const btn = document.createElement('div');
                btn.className = 'date-button';
                if (dStr === activeDateStr) {
                    btn.classList.add('active');
                }

                const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
                const dayName = days[d.getDay()];
                const dayNum = d.getDate();

                btn.innerHTML = `<div class="day-name">${dayName}</div><div class="day-num">${dayNum}</div>`;

                btn.addEventListener('click', () => {
                    if (activeDateStr === dStr) return;
                    activeDateStr = dStr;
                    renderDateStrip(); // re-render to update active class
                    renderFixturesForDate(activeDateStr);
                });

                dateStrip.appendChild(btn);
            }
        }

        function renderFixturesForDate(dateStr) {
            container.innerHTML = '';

            const fixturesOnDate = allFixtures.filter(f => f.localDateStr === dateStr);

            if (fixturesOnDate.length === 0) {
                container.innerHTML = '<div class="no-fixtures">No fixtures on this date.</div>';
                return;
            }

            // Group by league
            const grouped = {};
            fixturesOnDate.forEach(f => {
                if (!grouped[f.leagueName]) grouped[f.leagueName] = [];
                grouped[f.leagueName].push(f);
            });

            // Sort fixtures in each group chronologically
            for (const leagueName in grouped) {
                grouped[leagueName].sort((a, b) => a.timeObj - b.timeObj);
            }

            // Render
            for (const leagueName in grouped) {
                const leagueHeader = document.createElement('div');
                leagueHeader.className = 'league-header';
                const leagueId = grouped[leagueName][0].leagueId;
                const flag = LEAGUE_FLAGS[leagueId] || '';
                leagueHeader.textContent = flag ? `${flag} ${leagueName}` : leagueName;
                container.appendChild(leagueHeader);

                const leagueFixtures = grouped[leagueName];

                const metric = leagueFixtures[0].metric;
                let maxSingleMetric = 0;
                leagueFixtures.forEach(f => {
                    const homeVal = f[`home_expected_${metric}`];
                    const awayVal = f[`away_expected_${metric}`];
                    if (typeof homeVal === 'number') maxSingleMetric = Math.max(maxSingleMetric, homeVal);
                    if (typeof awayVal === 'number') maxSingleMetric = Math.max(maxSingleMetric, awayVal);
                });

                const scaleMax = Math.max(maxSingleMetric * 1.1, 3.0);

                leagueFixtures.forEach(fixture => {
                    container.appendChild(createFixtureCard(fixture, scaleMax, metric));
                });
            }
        }

        renderDateStrip();
        renderFixturesForDate(activeDateStr);

    } catch (error) {
        console.error(error);
        container.innerHTML = '<div class="no-fixtures">Error loading fixtures. Please try again later.</div>';
    }
}
function createFixtureCard(fixture, scaleMax, metric) {
    const card = document.createElement('div');
    card.className = 'fixture-card';

    if (fixture.status === 'FINISHED') {
        const homeGoals = fixture.home_goals !== null ? fixture.home_goals : '-';
        const awayGoals = fixture.away_goals !== null ? fixture.away_goals : '-';
        const homeXg = fixture.home_xg !== null && fixture.home_xg !== undefined ? fixture.home_xg.toFixed(2) : '-';
        const awayXg = fixture.away_xg !== null && fixture.away_xg !== undefined ? fixture.away_xg.toFixed(2) : '-';

        card.innerHTML = `
            <div class="fixture-header">
                <div class="team">
                    ${renderBadgeHtml(fixture.home_team)}
                    <div class="team-name">${fixture.home_team}</div>
                </div>
                <div class="xg-center result-center">
                    <div class="combined-xg-label">FT Score</div>
                    <div class="combined-xg">${homeGoals} - ${awayGoals}</div>
                    <div class="split-xg">xG: ${homeXg} - ${awayXg}</div>
                </div>
                <div class="team">
                    ${renderBadgeHtml(fixture.away_team)}
                    <div class="team-name">${fixture.away_team}</div>
                </div>
            </div>
        `;
        return card;
    }

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

document.addEventListener('DOMContentLoaded', () => {
    init();
    setupTheme();
    setupLogoClickHandlers();
    loadTeamNames();
});
