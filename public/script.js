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
