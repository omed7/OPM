const FIXTURE_LIMIT = 10;


let teamBadgeManifest = { badges: {} };

const LEAGUE_COUNTRIES = {
    'premier_league': { code: 'gb-eng', name: 'England' },
    'la_liga': { code: 'es', name: 'Spain' },
    'serie_a': { code: 'it', name: 'Italy' },
    'bundesliga': { code: 'de', name: 'Germany' },
    'ligue_1': { code: 'fr', name: 'France' },
    'superliga-argentina': { code: 'ar', name: 'Argentina' },
    'admiral-bundesliga': { code: 'at', name: 'Austria' },
    'pro-league-belgium': { code: 'be', name: 'Belgium' },
    'serie-a-brazil': { code: 'br', name: 'Brazil' },
    'superliga-denmark': { code: 'dk', name: 'Denmark' },
    'league-one': { code: 'gb-sct', name: 'Scotland' },
    '2-bundesliga': { code: 'de', name: 'Germany' },
    'copa-libertadores': { code: 'un', name: 'South America' },
    'j-league': { code: 'jp', name: 'Japan' },
    'liga-mx': { code: 'mx', name: 'Mexico' },
    'eredivisie': { code: 'nl', name: 'Netherlands' },
    'eerste-divisie': { code: 'nl', name: 'Netherlands' },
    'eliteserien': { code: 'no', name: 'Norway' },
    'liga-portugal': { code: 'pt', name: 'Portugal' },
    'pro-league-saudi': { code: 'sa', name: 'Saudi Arabia' },
    'premiership': { code: 'gb-sct', name: 'Scotland' },
    'allsvenskan': { code: 'se', name: 'Sweden' },
    'super-lig': { code: 'tr', name: 'Türkiye' },
    'mls': { code: 'us', name: 'United States' },
    'veikkausliiga': { code: 'fi', name: 'Finland' }
};

function renderLeagueFlag(leagueId) {
    const country = LEAGUE_COUNTRIES[leagueId];
    if (!country) {
        return '<span class="league-flag-fallback" aria-label="Country unavailable">—</span>';
    }
    return `<img class="league-flag" src="assets/flags/${country.code}.svg" alt="${country.name} flag">`;
}

async function init() {
    const container = document.getElementById('fixtures-container');
    const versionTag = document.getElementById('version-tag');
    const badgeAttribution = document.getElementById('badge-attribution');
    const dateStrip = document.getElementById('date-strip');

    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Failed to fetch data');
        const data = await response.json();

        try {
            const badgeResponse = await fetch('team_badges.json');
            if (badgeResponse.ok) {
                const badgeData = await badgeResponse.json();
                if (badgeData && badgeData.badges) {
                    teamBadgeManifest = badgeData;
                }
                if (badgeAttribution && badgeData && badgeData.source && badgeData.source.attribution) {
                    badgeAttribution.textContent = badgeData.source.attribution;
                }
            }
        } catch (e) {
            teamBadgeManifest = { badges: {} };
        }

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

            // Group by stable league ID so leagues with the same display name remain distinct.
            const grouped = {};
            fixturesOnDate.forEach(fixture => {
                if (!grouped[fixture.leagueId]) {
                    grouped[fixture.leagueId] = {
                        name: fixture.leagueName,
                        fixtures: [],
                    };
                }
                grouped[fixture.leagueId].fixtures.push(fixture);
            });

            // Render each league as an independently expandable section.
            for (const [leagueId, league] of Object.entries(grouped)) {
                const leagueFixtures = league.fixtures.sort((a, b) => a.timeObj - b.timeObj);
                const section = document.createElement('section');
                section.className = 'league-section';

                const storageKey = `league_expansion:${dateStr}:${leagueId}`;
                const isOpen = localStorage.getItem(storageKey) === 'open';
                const header = document.createElement('button');
                header.className = 'league-toggle';
                header.setAttribute('type', 'button');
                header.setAttribute('aria-expanded', String(isOpen));
                header.innerHTML = `
                    <span class="league-toggle-icon" aria-hidden="true">⌄</span>
                    ${renderLeagueFlag(leagueId)}
                    <span class="league-name">${league.name}</span>
                    <span class="league-count">${leagueFixtures.length}</span>
                `;

                const body = document.createElement('div');
                body.className = 'league-fixtures';
                if (!isOpen) body.classList.add('hidden');

                header.addEventListener('click', () => {
                    const nextOpen = header.getAttribute('aria-expanded') !== 'true';
                    header.setAttribute('aria-expanded', String(nextOpen));
                    if (nextOpen) {
                        body.classList.remove('hidden');
                        localStorage.setItem(storageKey, 'open');
                    } else {
                        body.classList.add('hidden');
                        localStorage.setItem(storageKey, 'closed');
                    }
                });

                const metric = leagueFixtures[0].metric;
                let maxSingleMetric = 0;
                leagueFixtures.forEach(fixture => {
                    const homeVal = fixture[`home_expected_${metric}`];
                    const awayVal = fixture[`away_expected_${metric}`];
                    if (typeof homeVal === 'number') maxSingleMetric = Math.max(maxSingleMetric, homeVal);
                    if (typeof awayVal === 'number') maxSingleMetric = Math.max(maxSingleMetric, awayVal);
                });

                const scaleMax = Math.max(maxSingleMetric * 1.1, 3.0);
                leagueFixtures.forEach(fixture => {
                    body.appendChild(createFixtureCard(fixture, scaleMax, metric));
                });

                section.appendChild(header);
                section.appendChild(body);
                container.appendChild(section);
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

        let predictionHtml = '';
        if (fixture.home_expected_xg !== undefined && fixture.home_expected_xg !== null) {
            const predHomeXg = fixture.home_expected_xg.toFixed(2);
            const predAwayXg = fixture.away_expected_xg.toFixed(2);
            let predHtml = `Pred xG: ${predHomeXg} - ${predAwayXg}`;

            if (fixture.home_expected_goals !== undefined && fixture.home_expected_goals !== null) {
                const predHomeGoals = fixture.home_expected_goals.toFixed(2);
                const predAwayGoals = fixture.away_expected_goals.toFixed(2);
                predHtml = `Pred Goals: ${predHomeGoals} - ${predAwayGoals} | ` + predHtml;
            }

            predictionHtml = `<div class="prediction-history" style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 8px; text-align: center; border-top: 1px dashed var(--xg-bar-bg); padding-top: 8px;">${predHtml}</div>`;
        }

        card.innerHTML = `
            <div class="fixture-header">
                <div class="team">
                    ${renderBadgeHtml(fixture.leagueId, fixture.home_team)}
                    <div class="team-name">${fixture.home_team}</div>
                </div>
                <div class="xg-center result-center">
                    <div class="combined-xg-label">FT Score</div>
                    <div class="combined-xg">${homeGoals} - ${awayGoals}</div>
                    <div class="split-xg">Act xG: ${homeXg} - ${awayXg}</div>
                </div>
                <div class="team">
                    ${renderBadgeHtml(fixture.leagueId, fixture.away_team)}
                    <div class="team-name">${fixture.away_team}</div>
                </div>
            </div>
            ${predictionHtml}
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
                ${renderBadgeHtml(fixture.leagueId, fixture.home_team)}
                <div class="team-name">${fixture.home_team}</div>
            </div>
            <div class="xg-center">
                <div class="combined-xg-label">${combinedLabel}</div>
                <div class="combined-xg">${combinedVal.toFixed(2)}</div>
                <div class="split-xg">${homeExpectedVal.toFixed(2)} - ${awayExpectedVal.toFixed(2)}</div>
            </div>
            <div class="team">
                ${renderBadgeHtml(fixture.leagueId, fixture.away_team)}
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

function getManifestTeamBadge(leagueId, teamName) {
    const leagueBadges = teamBadgeManifest.badges && teamBadgeManifest.badges[leagueId];
    const badge = leagueBadges && leagueBadges[teamName];
    return badge && badge.badge_url ? badge : null;
}

function renderBadgeHtml(leagueId, teamName) {
    const initials = getInitials(teamName);
    const color = getColor(teamName);
    const localLogoUrl = getTeamLogo(teamName);
    const manifestBadge = getManifestTeamBadge(leagueId, teamName);
    const logoUrl = localLogoUrl || (manifestBadge && manifestBadge.badge_url);
    if (logoUrl) {
        return `<div class="team-badge" data-team="${teamName}" style="background-color: transparent;" title="Click to change team logo"><img src="${logoUrl}" alt="${teamName} badge" onerror="this.remove(); this.parentElement.style.backgroundColor='${color}'; this.parentElement.textContent='${initials}';"></div>`;
    }
    return `<div class="team-badge" data-team="${teamName}" style="background-color: ${color}" title="Click to change team logo">${initials}</div>`;
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
});
