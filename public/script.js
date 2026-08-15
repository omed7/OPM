const FIXTURE_LIMIT = 10;
const FAVORITES_STORAGE_KEY = 'opm:favorites:v1';

let teamBadgeManifest = { badges: {} };
let appState = {
    fixtureData: null,
    standingsData: { leagues: [] },
    allFixtures: [],
    activeDate: null,
    activeTab: 'home',
    activeLeagueId: null,
    activeSeasonId: null,
    activeView: 'overall',
};

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
    'veikkausliiga': { code: 'fi', name: 'Finland' },
};

function renderLeagueFlag(leagueId) {
    const country = LEAGUE_COUNTRIES[leagueId];
    if (!country) {
        return '<span class="league-flag-fallback" aria-label="Country unavailable">—</span>';
    }
    return `<img class="league-flag" src="assets/flags/${country.code}.svg" alt="${country.name} flag">`;
}

function localDateString(value) {
    if (!value) return '';
    return String(value).slice(0, 10);
}

function currentLocalDateString() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function fixtureTimeObject(fixture) {
    const date = localDateString(fixture.date);
    const time = fixture.kickoff_time || '00:00';
    const parsed = new Date(`${date}T${time}:00`);
    return Number.isNaN(parsed.getTime()) ? new Date(`${date}T00:00:00`) : parsed;
}

function fixtureKey(fixture) {
    return [fixture.leagueId, localDateString(fixture.date), fixture.home_team, fixture.away_team].join('|');
}

function readFavoriteKeys() {
    try {
        const parsed = JSON.parse(localStorage.getItem(FAVORITES_STORAGE_KEY) || '[]');
        return new Set(Array.isArray(parsed) ? parsed.filter(value => typeof value === 'string') : []);
    } catch (error) {
        return new Set();
    }
}

function writeFavoriteKeys(keys) {
    try {
        localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify([...keys]));
    } catch (error) {
        // Local favorites are optional and must not break the fixture experience.
    }
}

function toggleFavorite(fixture) {
    const key = fixtureKey(fixture);
    const favorites = readFavoriteKeys();
    if (favorites.has(key)) {
        favorites.delete(key);
    } else {
        favorites.add(key);
    }
    writeFavoriteKeys(favorites);
    renderActiveTab();
}

function isFavorite(fixture) {
    return readFavoriteKeys().has(fixtureKey(fixture));
}

function formatSourceKickoff(fixture) {
    return fixture.kickoff_time ? `UTC+03:00 · ${fixture.kickoff_time}` : 'UTC+03:00 · TBD';
}

function formatNumber(value) {
    return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '—';
}

function formatSigned(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
    if (Math.abs(value) < 0.005) return '0.00';
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}`;
}

function formatPa(metric) {
    if (!metric) return '—';
    return `${formatSigned(metric.total)} / ${formatSigned(metric.average)}`;
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
    return `hsl(${Math.abs(hash % 360)}, 60%, 40%)`;
}

function getTeamLogo(teamName) {
    if (!teamName) return null;
    try {
        const teamLogos = JSON.parse(localStorage.getItem('team_logos') || '{}');
        return teamLogos[teamName] || null;
    } catch (error) {
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

function fixtureDetailsHtml(fixture, scaleMax, metric) {
    if (fixture.status === 'FINISHED') {
        const goals = `${fixture.home_goals ?? '—'} - ${fixture.away_goals ?? '—'}`;
        const actualXg = `${formatNumber(fixture.home_xg)} - ${formatNumber(fixture.away_xg)}`;
        const predictionParts = [];
        if (fixture.home_expected_goals !== undefined && fixture.home_expected_goals !== null) {
            predictionParts.push(`Pred Goals: ${formatNumber(fixture.home_expected_goals)} - ${formatNumber(fixture.away_expected_goals)}`);
        }
        if (fixture.home_expected_xg !== undefined && fixture.home_expected_xg !== null) {
            predictionParts.push(`Pred xG: ${formatNumber(fixture.home_expected_xg)} - ${formatNumber(fixture.away_expected_xg)}`);
        }
        return `
            <div class="fixture-detail-result">
                <div><span>FT Score</span><strong>${goals}</strong></div>
                <div><span>Actual xG</span><strong>${actualXg}</strong></div>
            </div>
            <div class="prediction-history">${predictionParts.length ? predictionParts.join(' | ') : 'No stored pre-match prediction.'}</div>
        `;
    }

    const homeExpected = fixture[`home_expected_${metric}`];
    const awayExpected = fixture[`away_expected_${metric}`];
    const combined = fixture[`combined_expected_${metric}`];
    const safeScale = Math.max(scaleMax || 3, 0.1);
    const homePercent = typeof homeExpected === 'number' ? Math.max(0, Math.min(100, (homeExpected / safeScale) * 100)) : 0;
    const awayPercent = typeof awayExpected === 'number' ? Math.max(0, Math.min(100, (awayExpected / safeScale) * 100)) : 0;
    const homeHistoryKey = Object.keys(fixture).find(key => key.startsWith('home_last_') && key.endsWith('_matches'));
    const awayHistoryKey = Object.keys(fixture).find(key => key.startsWith('away_last_') && key.endsWith('_matches'));
    const historyHtml = (records, side) => (records || []).map(match => {
        const valueFor = match[`${metric}_for`];
        const valueAgainst = match[`${metric}_against`];
        return `<div class="history-item">${formatNumber(valueFor)} - ${formatNumber(valueAgainst)} vs ${match.opponent}</div>`;
    }).join('') || '<div class="history-item">No history available.</div>';
    const metricLabel = metric === 'xg' ? 'xG' : 'Goals';

    return `
        <div class="fixture-detail-prediction">
            <div class="detail-metric-label">Predicted ${metricLabel}</div>
            <div class="detail-metric-value">${formatNumber(combined)}</div>
            <div class="detail-metric-split">${formatNumber(homeExpected)} - ${formatNumber(awayExpected)}</div>
        </div>
        <div class="xg-bars" aria-hidden="true">
            <div class="xg-bar-container home-bar-container"><div class="xg-bar" style="width: ${homePercent}%"></div></div>
            <div class="xg-bar-container away-bar-container"><div class="xg-bar" style="width: ${awayPercent}%"></div></div>
        </div>
        <div class="match-history">
            <div class="history-list home">${historyHtml(fixture[homeHistoryKey], 'home')}</div>
            <div class="history-list away">${historyHtml(fixture[awayHistoryKey], 'away')}</div>
        </div>
    `;
}

function createFixtureCard(fixture, scaleMax, metric) {
    const card = document.createElement('article');
    let expanded = false;

    function renderCard() {
        const favorite = isFavorite(fixture);
        card.className = `fixture-card ${expanded ? 'expanded' : 'compact'}`;
        card.setAttribute('aria-expanded', String(expanded));
        card.setAttribute('tabindex', '0');
        card.innerHTML = `
            <div class="fixture-summary">
                <div class="team">
                    ${renderBadgeHtml(fixture.leagueId, fixture.home_team)}
                    <div class="team-name">${fixture.home_team}</div>
                </div>
                <div class="fixture-time" aria-label="Kickoff ${formatSourceKickoff(fixture)}">
                    <span>Kickoff</span>
                    <strong>${formatSourceKickoff(fixture)}</strong>
                </div>
                <div class="team">
                    ${renderBadgeHtml(fixture.leagueId, fixture.away_team)}
                    <div class="team-name">${fixture.away_team}</div>
                </div>
            </div>
            <div class="fixture-card-actions">
                <button class="favorite-toggle" type="button" aria-pressed="${favorite}" aria-label="${favorite ? 'Remove' : 'Save'} ${fixture.home_team} versus ${fixture.away_team} ${favorite ? 'from' : 'to'} favorites">${favorite ? 'Saved' : 'Save'}</button>
                <span class="fixture-detail-hint">${expanded ? 'Hide details' : 'Show details'}</span>
            </div>
            <div class="fixture-details ${expanded ? '' : 'hidden'}">${expanded ? fixtureDetailsHtml(fixture, scaleMax, metric) : ''}</div>
        `;
    }

    renderCard();
    card.addEventListener('click', event => {
        const target = event.target;
        if (target && typeof target.closest === 'function' && target.closest('.team-badge')) return;
        if (target && typeof target.closest === 'function' && target.closest('.favorite-toggle')) {
            if (typeof event.preventDefault === 'function') event.preventDefault();
            if (typeof event.stopPropagation === 'function') event.stopPropagation();
            toggleFavorite(fixture);
            return;
        }
        expanded = !expanded;
        renderCard();
    });
    card.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
            if (typeof event.preventDefault === 'function') event.preventDefault();
            expanded = !expanded;
            renderCard();
        }
    });
    return card;
}

function renderDateStrip() {
    const dateStrip = document.getElementById('date-strip');
    dateStrip.innerHTML = '';
    const today = new Date();
    for (let offset = -3; offset <= 3; offset += 1) {
        const date = new Date(today);
        date.setDate(today.getDate() + offset);
        const dateString = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        const button = document.createElement('button');
        button.className = `date-button ${dateString === appState.activeDate ? 'active' : ''}`;
        button.setAttribute('type', 'button');
        button.setAttribute('aria-pressed', String(dateString === appState.activeDate));
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        button.innerHTML = `<div class="day-name">${dayNames[date.getDay()]}</div><div class="day-num">${date.getDate()}</div>`;
        button.addEventListener('click', () => {
            appState.activeDate = dateString;
            renderActiveTab();
        });
        dateStrip.appendChild(button);
    }
}

function renderHome() {
    const container = document.getElementById('fixtures-container');
    const dateStrip = document.getElementById('date-strip');
    dateStrip.className = 'date-strip';
    renderDateStrip();
    container.innerHTML = '';

    const fixturesOnDate = appState.allFixtures.filter(fixture => fixture.localDateStr === appState.activeDate);
    if (fixturesOnDate.length === 0) {
        container.innerHTML = '<div class="no-fixtures">No fixtures on this date.</div>';
        return;
    }

    const grouped = {};
    fixturesOnDate.forEach(fixture => {
        if (!grouped[fixture.leagueId]) grouped[fixture.leagueId] = { name: fixture.leagueName, fixtures: [] };
        grouped[fixture.leagueId].fixtures.push(fixture);
    });

    Object.entries(grouped).forEach(([leagueId, league]) => {
        const leagueFixtures = league.fixtures.sort((left, right) => left.timeObj - right.timeObj).slice(0, FIXTURE_LIMIT);
        const section = document.createElement('section');
        section.className = 'league-section';
        const storageKey = `league_expansion:${appState.activeDate}:${leagueId}`;
        const open = localStorage.getItem(storageKey) === 'open';
        const header = document.createElement('button');
        header.className = 'league-toggle';
        header.setAttribute('type', 'button');
        header.setAttribute('aria-expanded', String(open));
        header.innerHTML = `<span class="league-toggle-icon" aria-hidden="true">⌄</span>${renderLeagueFlag(leagueId)}<span class="league-name">${league.name}</span><span class="league-count">${leagueFixtures.length}</span>`;
        const body = document.createElement('div');
        body.className = `league-fixtures ${open ? '' : 'hidden'}`;
        header.addEventListener('click', () => {
            const nextOpen = header.getAttribute('aria-expanded') !== 'true';
            header.setAttribute('aria-expanded', String(nextOpen));
            body.className = `league-fixtures ${nextOpen ? '' : 'hidden'}`;
            localStorage.setItem(storageKey, nextOpen ? 'open' : 'closed');
        });
        const metric = leagueFixtures[0].metric || 'xg';
        const maxMetric = leagueFixtures.reduce((maximum, fixture) => Math.max(
            maximum,
            typeof fixture[`home_expected_${metric}`] === 'number' ? fixture[`home_expected_${metric}`] : 0,
            typeof fixture[`away_expected_${metric}`] === 'number' ? fixture[`away_expected_${metric}`] : 0,
        ), 0);
        const scaleMax = Math.max(maxMetric * 1.1, 3.0);
        leagueFixtures.forEach(fixture => body.appendChild(createFixtureCard(fixture, scaleMax, metric)));
        section.appendChild(header);
        section.appendChild(body);
        container.appendChild(section);
    });
}

function allLeagueOptions() {
    const options = new Map();
    (appState.fixtureData.leagues || []).forEach(league => options.set(league.id, league.name));
    (appState.standingsData.leagues || []).forEach(league => options.set(league.id, league.name));
    return [...options.entries()]
        .map(([id, name]) => ({ id, name }))
        .sort((left, right) => left.name.localeCompare(right.name));
}

function selectedLeagueSummary() {
    return (appState.standingsData.leagues || []).find(league => league.id === appState.activeLeagueId) || null;
}

function renderLeagueList() {
    const container = document.getElementById('fixtures-container');
    container.innerHTML = '<h2 class="tab-heading">Leagues</h2><p class="tab-description">Choose a league to view team prediction accuracy by season.</p>';
    const list = document.createElement('div');
    list.className = 'league-directory';
    const options = allLeagueOptions();
    if (options.length === 0) {
        list.innerHTML = '<div class="no-fixtures">No leagues are available.</div>';
    }
    options.forEach(league => {
        const button = document.createElement('button');
        button.className = 'league-directory-item';
        button.setAttribute('type', 'button');
        button.innerHTML = `${renderLeagueFlag(league.id)}<span>${league.name}</span><span aria-hidden="true">›</span>`;
        button.addEventListener('click', () => {
            appState.activeLeagueId = league.id;
            const summary = selectedLeagueSummary();
            appState.activeSeasonId = summary && summary.seasons.length ? summary.seasons[0].id : null;
            appState.activeView = 'overall';
            renderActiveTab();
        });
        list.appendChild(button);
    });
    container.appendChild(list);
}

function renderSeasonSelector(summary, selectedSeason) {
    const wrapper = document.createElement('div');
    wrapper.className = 'season-selector';
    const toggle = document.createElement('button');
    toggle.className = 'season-selector-toggle';
    toggle.setAttribute('type', 'button');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.textContent = selectedSeason ? selectedSeason.label : 'No retained season';
    const menu = document.createElement('div');
    menu.className = 'season-selector-menu hidden';
    if (!summary || !summary.seasons.length) {
        menu.innerHTML = '<span>No retained season data.</span>';
    } else {
        summary.seasons.forEach(season => {
            const option = document.createElement('button');
            option.className = 'season-option';
            option.setAttribute('type', 'button');
            option.setAttribute('aria-pressed', String(selectedSeason && season.id === selectedSeason.id));
            option.textContent = season.label;
            option.addEventListener('click', () => {
                appState.activeSeasonId = season.id;
                renderActiveTab();
            });
            menu.appendChild(option);
        });
    }
    toggle.addEventListener('click', () => {
        const open = toggle.getAttribute('aria-expanded') !== 'true';
        toggle.setAttribute('aria-expanded', String(open));
        menu.className = `season-selector-menu ${open ? '' : 'hidden'}`;
    });
    wrapper.appendChild(toggle);
    wrapper.appendChild(menu);
    return wrapper;
}

function renderLeagueDetail() {
    const container = document.getElementById('fixtures-container');
    container.innerHTML = '';
    const summary = selectedLeagueSummary();
    const heading = document.createElement('div');
    heading.className = 'league-detail-heading';
    const back = document.createElement('button');
    back.className = 'back-button';
    back.setAttribute('type', 'button');
    back.textContent = 'All leagues';
    back.addEventListener('click', () => {
        appState.activeLeagueId = null;
        appState.activeSeasonId = null;
        renderActiveTab();
    });
    const title = document.createElement('h2');
    title.className = 'tab-heading';
    title.textContent = summary ? summary.name : (allLeagueOptions().find(league => league.id === appState.activeLeagueId) || {}).name || 'League';
    heading.appendChild(back);
    heading.appendChild(title);
    container.appendChild(heading);

    const selectedSeason = summary && summary.seasons.find(season => season.id === appState.activeSeasonId) || (summary && summary.seasons[0]);
    container.appendChild(renderSeasonSelector(summary, selectedSeason));

    if (!selectedSeason) {
        container.innerHTML += '<div class="no-fixtures">No retained standings data is available for this league yet.</div>';
        return;
    }

    const legend = document.createElement('p');
    legend.className = 'pa-legend';
    const provenanceText = {
        reconstructed_historical: 'Reconstructed historical prediction: OPM replayed the active formula using only earlier calendar-date results. ',
        stored_pre_match: 'Stored pre-match prediction: values were retained before the fixture. ',
        mixed: 'Mixed prediction sources: stored forecasts take priority; other eligible fixtures use reconstructed historical predictions. ',
        unavailable: '',
    }[selectedSeason.prediction_provenance] || '';
    legend.textContent = `${provenanceText}PA is actual minus predicted. Values closer to 0 are more predictable. Each entry shows season total / per-match average.`;
    container.appendChild(legend);

    const viewControls = document.createElement('div');
    viewControls.className = 'pa-view-controls';
    [['overall', 'Overall'], ['for', 'For'], ['against', 'Against']].forEach(([viewId, label]) => {
        const button = document.createElement('button');
        button.className = `pa-view-button ${appState.activeView === viewId ? 'active' : ''}`;
        button.setAttribute('type', 'button');
        button.setAttribute('aria-pressed', String(appState.activeView === viewId));
        button.textContent = label;
        button.addEventListener('click', () => {
            appState.activeView = viewId;
            renderActiveTab();
        });
        viewControls.appendChild(button);
    });
    container.appendChild(viewControls);

    const hasPredictionAccuracy = selectedSeason.teams.some(team => team.views.overall.xg || team.views.overall.goals);
    if (!hasPredictionAccuracy) {
        const note = document.createElement('p');
        note.className = 'season-unavailable-note';
        note.textContent = 'Matches played is retained for this season. Prediction accuracy is unavailable because original pre-match predictions were not stored.';
        container.appendChild(note);
    }

    const teams = [...selectedSeason.teams].sort((left, right) => {
        const leftMetric = left.views[appState.activeView].xg_goals;
        const rightMetric = right.views[appState.activeView].xg_goals;
        const leftValue = leftMetric ? Math.abs(leftMetric.average) : Number.POSITIVE_INFINITY;
        const rightValue = rightMetric ? Math.abs(rightMetric.average) : Number.POSITIVE_INFINITY;
        return leftValue - rightValue || left.name.localeCompare(right.name);
    });
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'standings-table-wrapper';
    const table = document.createElement('table');
    table.className = 'standings-table';
    table.innerHTML = `
        <thead><tr><th scope="col">Team</th><th scope="col">Matches played</th><th scope="col">xG PA</th><th scope="col">Goals PA</th><th scope="col">xG/G PA</th></tr></thead>
        <tbody>${teams.map(team => {
            const view = team.views[appState.activeView];
            return `<tr><th scope="row">${team.name}</th><td>${team.matches_played}</td><td>${formatPa(view.xg)}</td><td>${formatPa(view.goals)}</td><td>${formatPa(view.xg_goals)}</td></tr>`;
        }).join('')}</tbody>
    `;
    tableWrapper.appendChild(table);
    container.appendChild(tableWrapper);
}

function renderLeague() {
    const dateStrip = document.getElementById('date-strip');
    dateStrip.className = 'date-strip hidden';
    if (!appState.activeLeagueId) {
        renderLeagueList();
    } else {
        renderLeagueDetail();
    }
}

function renderFavorites() {
    const container = document.getElementById('fixtures-container');
    const dateStrip = document.getElementById('date-strip');
    dateStrip.className = 'date-strip hidden';
    container.innerHTML = '<h2 class="tab-heading">Favorites</h2><p class="tab-description">Saved fixtures are kept only in this browser.</p>';
    const favorites = appState.allFixtures.filter(isFavorite).sort((left, right) => left.timeObj - right.timeObj);
    if (!favorites.length) {
        container.innerHTML += '<div class="no-fixtures">No favorite fixtures yet. Use Save on a Home fixture to track it here.</div>';
        return;
    }
    favorites.forEach(fixture => container.appendChild(createFixtureCard(fixture, 3, fixture.metric || 'xg')));
}

function renderActiveTab() {
    const tabs = [
        ['home-tab', 'home'],
        ['league-tab', 'league'],
        ['favorite-tab', 'favorite'],
    ];
    tabs.forEach(([id, tab]) => {
        const button = document.getElementById(id);
        if (!button) return;
        const selected = appState.activeTab === tab;
        button.className = `bottom-nav-item ${selected ? 'active' : ''}`;
        button.setAttribute('aria-selected', String(selected));
    });
    if (appState.activeTab === 'home') renderHome();
    if (appState.activeTab === 'league') renderLeague();
    if (appState.activeTab === 'favorite') renderFavorites();
}

async function init() {
    const container = document.getElementById('fixtures-container');
    const versionTag = document.getElementById('version-tag');
    const badgeAttribution = document.getElementById('badge-attribution');
    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Failed to fetch data');
        const data = await response.json();
        if (!data.leagues || data.leagues.length === 0) {
            container.innerHTML = '<div class="no-fixtures">No leagues found.</div>';
            return;
        }
        appState.fixtureData = data;
        appState.allFixtures = data.leagues.flatMap(league => (league.fixtures || []).map(fixture => ({
            ...fixture,
            leagueId: league.id,
            leagueName: league.name,
            metric: league.metric || 'xg',
            localDateStr: localDateString(fixture.date),
            timeObj: fixtureTimeObject(fixture),
        })));
        appState.activeDate = currentLocalDateString();

        try {
            const standingsResponse = await fetch('league_standings.json');
            if (standingsResponse.ok) {
                const standings = await standingsResponse.json();
                if (standings && Array.isArray(standings.leagues)) appState.standingsData = standings;
            }
        } catch (error) {
            appState.standingsData = { leagues: [] };
        }

        try {
            const badgeResponse = await fetch('team_badges.json');
            if (badgeResponse.ok) {
                const badgeData = await badgeResponse.json();
                if (badgeData && badgeData.badges) teamBadgeManifest = badgeData;
                if (badgeAttribution && badgeData && badgeData.source && badgeData.source.attribution) {
                    badgeAttribution.textContent = badgeData.source.attribution;
                }
            }
        } catch (error) {
            teamBadgeManifest = { badges: {} };
        }

        try {
            const versionResponse = await fetch('version.json');
            if (versionResponse.ok) {
                const versionData = await versionResponse.json();
                versionTag.textContent = `v${versionData.version}`;
            }
        } catch (error) {
            console.error('Failed to load version info', error);
        }

        [['home-tab', 'home'], ['league-tab', 'league'], ['favorite-tab', 'favorite']].forEach(([id, tab]) => {
            const button = document.getElementById(id);
            if (!button) return;
            button.addEventListener('click', () => {
                appState.activeTab = tab;
                renderActiveTab();
            });
        });
        renderActiveTab();
    } catch (error) {
        console.error(error);
        container.innerHTML = '<div class="no-fixtures">Error loading fixtures. Please try again later.</div>';
    }
}

function setupLogoClickHandlers() {
    document.body.addEventListener('click', event => {
        const badge = event.target && typeof event.target.closest === 'function' ? event.target.closest('.team-badge') : null;
        if (!badge) return;
        const teamName = badge.dataset.team;
        if (!teamName) return;
        let teamLogos = {};
        try {
            teamLogos = JSON.parse(localStorage.getItem('team_logos') || '{}');
        } catch (error) {
            teamLogos = {};
        }
        const currentLogoUrl = teamLogos[teamName] || '';
        const newLogoUrl = prompt(`Enter custom logo URL for ${teamName} (leave blank to remove):`, currentLogoUrl);
        if (newLogoUrl === null) return;
        const trimmedLogoUrl = newLogoUrl.trim();
        if (trimmedLogoUrl) teamLogos[teamName] = trimmedLogoUrl;
        else delete teamLogos[teamName];
        try {
            localStorage.setItem('team_logos', JSON.stringify(teamLogos));
        } catch (error) {
            return;
        }
        renderActiveTab();
    });
}

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
