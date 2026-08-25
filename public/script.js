const FAVORITES_STORAGE_KEY = 'opm:favorites:v1';

let teamBadgeManifest = { badges: {} };

function manualWeightsModule() {
    return typeof window !== 'undefined' ? window.OPMManualWeights : null;
}
let logoDialogState = { teamName: null, trigger: null };
let appState = {
    fixtureData: null,
    standingsData: { leagues: [] },
    allFixtures: [],
    activeDate: null,
    activeSearchQuery: '',
    activeTab: 'home',
    activeLeagueId: null,
    activeSeasonId: null,
    activeView: 'overall',
    activeSort: 'combined',
    activeSortDirection: 'asc',
    homeStatusFilter: 'all',
    homeForecastFilter: 'all',
    homeFiltersOpen: false,
};

const STANDINGS_SORT_OPTIONS = [
    ['combined', 'Combined PA'],
    ['xg', 'xG PA'],
    ['goals', 'Goals PA'],
    ['matches', 'Matches played'],
    ['name', 'Team name'],
];

const HOME_STATUS_FILTERS = [
    ['all', 'All'],
    ['upcoming', 'Upcoming'],
    ['finished', 'Finished'],
];

const HOME_FORECAST_FILTERS = [
    ['all', 'All forecasts'],
    ['available', 'Available'],
    ['unavailable', 'Unavailable'],
];

const LEAGUE_COUNTRIES = {
    'premier_league': { code: 'gb-eng', name: 'England' },
    'la_liga': { code: 'es', name: 'Spain' },
    'serie_a': { code: 'it', name: 'Italy' },
    'bundesliga': { code: 'de', name: 'Germany' },
    'ligue_1': { code: 'fr', name: 'France' },
    'admiral-bundesliga': { code: 'at', name: 'Austria' },
    'pro-league-belgium': { code: 'be', name: 'Belgium' },
    'serie-a-brazil': { code: 'br', name: 'Brazil' },
    'superliga-denmark': { code: 'dk', name: 'Denmark' },
    '2-bundesliga': { code: 'de', name: 'Germany' },
    'liga-mx': { code: 'mx', name: 'Mexico' },
    'eredivisie': { code: 'nl', name: 'Netherlands' },
    'eerste-divisie': { code: 'nl', name: 'Netherlands' },
    'eliteserien': { code: 'no', name: 'Norway' },
    'liga-portugal': { code: 'pt', name: 'Portugal' },
    'pro-league-saudi': { code: 'sa', name: 'Saudi Arabia' },
    'premiership': { code: 'gb-sct', name: 'Scotland' },
    'super-lig': { code: 'tr', name: 'Türkiye' },
    'mls': { code: 'us', name: 'United States' },
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

function hasCanonicalKickoffAt(fixture) {
    return fixture && fixture.status === 'FINISHED'
        && typeof fixture.kickoff_at === 'string'
        && /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\dZ$/.test(fixture.kickoff_at);
}

function fixtureLocalDateString(fixture) {
    if (hasCanonicalKickoffAt(fixture)) {
        const instant = new Date(fixture.kickoff_at);
        if (!Number.isNaN(instant.getTime())) {
            return `${instant.getFullYear()}-${String(instant.getMonth() + 1).padStart(2, '0')}-${String(instant.getDate()).padStart(2, '0')}`;
        }
    }
    return localDateString(fixture && fixture.date);
}

function currentLocalDateString() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function formatHomeDate(value) {
    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return value || 'Selected date';
    return date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
}

function fixtureTimeObject(fixture) {
    if (hasCanonicalKickoffAt(fixture)) {
        const instant = new Date(fixture.kickoff_at);
        if (!Number.isNaN(instant.getTime())) return instant;
    }
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
    if (favorites.has(key)) favorites.delete(key);
    else favorites.add(key);
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
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
}

function getColor(name) {
    let hash = 0;
    for (let index = 0; index < name.length; index += 1) {
        hash = name.charCodeAt(index) + ((hash << 5) - hash);
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

function normalizeTeamName(value) {
    return String(value || '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLocaleLowerCase()
        .replace(/[^a-z0-9]/g, '');
}

function getManifestTeamBadge(leagueId, teamName) {
    const leagueBadges = teamBadgeManifest.badges && teamBadgeManifest.badges[leagueId];
    if (!leagueBadges || !teamName) return null;
    const direct = leagueBadges[teamName];
    if (direct && direct.badge_url) return direct;

    const normalizedName = normalizeTeamName(teamName);
    const matches = Object.keys(leagueBadges)
        .filter(candidate => normalizeTeamName(candidate) === normalizedName);
    if (matches.length !== 1) return null;
    const normalizedBadge = leagueBadges[matches[0]];
    return normalizedBadge && normalizedBadge.badge_url ? normalizedBadge : null;
}

function getTeamBadgeUrl(leagueId, teamName) {
    const localLogoUrl = getTeamLogo(teamName);
    const manifestBadge = getManifestTeamBadge(leagueId, teamName);
    return localLogoUrl || (manifestBadge && manifestBadge.badge_url) || null;
}

function renderBadgeHtml(leagueId, teamName) {
    const initials = getInitials(teamName);
    const color = getColor(teamName);
    const logoUrl = getTeamBadgeUrl(leagueId, teamName);
    if (logoUrl) {
        return `<button class="team-badge" type="button" data-team="${teamName}" style="background-color: transparent;" title="Customize ${teamName} crest" aria-label="Customize ${teamName} crest"><img src="${logoUrl}" alt="${teamName} crest" onerror="this.remove(); this.parentElement.style.backgroundColor='${color}'; this.parentElement.textContent='${initials}';"></button>`;
    }
    return `<button class="team-badge" type="button" data-team="${teamName}" style="background-color: ${color}" title="Customize ${teamName} crest" aria-label="Customize ${teamName} crest">${initials}</button>`;
}

function renderStandingsTeamHtml(leagueId, teamName) {
    const initials = getInitials(teamName);
    const color = getColor(teamName);
    const logoUrl = getTeamBadgeUrl(leagueId, teamName);
    const crest = logoUrl
        ? `<span class="standings-team-crest" aria-hidden="true"><img src="${logoUrl}" alt="" onerror="this.remove(); this.parentElement.style.backgroundColor='${color}'; this.parentElement.textContent='${initials}';"></span>`
        : `<span class="standings-team-crest standings-team-initials" style="background-color: ${color}" aria-hidden="true">${initials}</span>`;
    return `<span class="standings-team">${crest}<span>${teamName}</span></span>`;
}

function fixtureHasPublishedForecast(fixture) {
    return ['home_expected_xg', 'away_expected_xg', 'combined_expected_xg']
        .every(field => typeof fixture[field] === 'number' && Number.isFinite(fixture[field]));
}

function fixtureHasPublishedGoalsForecast(fixture) {
    return ['home_expected_goals', 'away_expected_goals', 'combined_expected_goals']
        .every(field => typeof fixture[field] === 'number' && Number.isFinite(fixture[field]));
}

function fixtureForecastAvailability(fixture) {
    if (!fixtureHasPublishedForecast(fixture)) return 'unavailable';
    return fixtureHasPublishedGoalsForecast(fixture) ? 'full' : 'xg-only';
}

function safariDisplayPrediction(fixture) {
    const manualWeights = manualWeightsModule();
    if (!manualWeights) return null;
    return manualWeights.displayPrediction(fixture);
}

function manualEstimateHtml(fixture) {
    const manualWeights = manualWeightsModule();
    if (!manualWeights || !manualWeights.canCalculateXg(fixture)) return '';
    return `
        <p class="manual-estimate-note">A private Safari xG estimate is available from these selected histories. It does not change OPM’s published forecast, standings, or future fixtures.</p>
        ${manualWeights.fixtureEditorHtml(fixture)}
    `;
}

function renderForecastStatusHtml(fixture) {
    const manualPrediction = safariDisplayPrediction(fixture);
    const displayedForecast = manualPrediction || fixture;
    const availability = fixtureForecastAvailability(displayedForecast);
    const available = availability !== 'unavailable';
    const label = manualPrediction
        ? 'Private Safari forecast'
        : (availability === 'full' ? 'Forecast available' : (availability === 'xg-only' ? 'xG forecast available' : 'Forecast unavailable'));
    const statusClass = availability === 'xg-only' ? 'xg-only' : (available ? 'available' : 'unavailable');
    return `<span class="forecast-status ${statusClass}">${label}</span>`;
}

function homeForecastSummaryHtml(fixture) {
    if (fixture.status === 'FINISHED') return '';
    const manualPrediction = safariDisplayPrediction(fixture);
    const displayedForecast = manualPrediction || fixture;
    if (!fixtureHasPublishedForecast(displayedForecast)) return '';
    const source = manualPrediction ? 'Private Safari' : 'Published';
    return `
        <div class="home-forecast-summary ${manualPrediction ? 'private' : 'published'}" aria-label="${source} expected goals forecast">
            <span>${source} xG</span>
            <strong>${formatNumber(displayedForecast.home_expected_xg)} – ${formatNumber(displayedForecast.away_expected_xg)}</strong>
            <small>Total ${formatNumber(displayedForecast.combined_expected_xg)}</small>
        </div>
    `;
}

function fixtureDetailsHtml(fixture, scaleMax, metric) {
    const manualPrediction = safariDisplayPrediction(fixture);
    const displayFixture = manualPrediction ? { ...fixture, ...manualPrediction } : fixture;
    const forecastAvailable = fixtureHasPublishedForecast(displayFixture);
    if (fixture.status === 'FINISHED') {
        const goals = `${fixture.home_goals ?? '—'} - ${fixture.away_goals ?? '—'}`;
        const hasActualXg = [fixture.home_xg, fixture.away_xg]
            .every(value => typeof value === 'number' && Number.isFinite(value));
        const actualMetric = hasActualXg
            ? `<div><span>Actual xG</span><strong>${formatNumber(fixture.home_xg)} - ${formatNumber(fixture.away_xg)}</strong></div>`
            : '<div><span>Goals-only result</span><strong>xG unavailable</strong></div>';
        const predictionParts = [];
        if (fixture.home_expected_goals !== undefined && fixture.home_expected_goals !== null) {
            predictionParts.push(`Pred Goals: ${formatNumber(fixture.home_expected_goals)} - ${formatNumber(fixture.away_expected_goals)}`);
        }
        if (fixture.home_expected_xg !== undefined && fixture.home_expected_xg !== null) {
            predictionParts.push(`Pred xG: ${formatNumber(fixture.home_expected_xg)} - ${formatNumber(fixture.away_expected_xg)}`);
        }
        return `
            <div class="fixture-detail-result">
                <div><span>FT score</span><strong>${goals}</strong></div>
                ${actualMetric}
            </div>
            <div class="prediction-history">${forecastAvailable && predictionParts.length ? predictionParts.join(' · ') : 'No qualifying pre-match forecast is published in this artifact.'}</div>
        `;
    }

    if (!forecastAvailable) {
        return `
            <p class="forecast-unavailable-copy">No qualifying pre-match forecast is published in this artifact.</p>
            ${manualEstimateHtml(fixture)}
        `;
    }

    const displayMetric = metric === 'goals' && !fixtureHasPublishedGoalsForecast(displayFixture) ? 'xg' : metric;
    const homeExpected = displayFixture[`home_expected_${displayMetric}`];
    const awayExpected = displayFixture[`away_expected_${displayMetric}`];
    const combined = displayFixture[`combined_expected_${displayMetric}`];
    const safeScale = Math.max(scaleMax || 3, 0.1);
    const homePercent = typeof homeExpected === 'number' ? Math.max(0, Math.min(100, (homeExpected / safeScale) * 100)) : 0;
    const awayPercent = typeof awayExpected === 'number' ? Math.max(0, Math.min(100, (awayExpected / safeScale) * 100)) : 0;
    const homeHistoryKey = Object.keys(fixture).find(key => key.startsWith('home_last_') && key.endsWith('_matches'));
    const awayHistoryKey = Object.keys(fixture).find(key => key.startsWith('away_last_') && key.endsWith('_matches'));
    const historyHtml = records => (records || []).map(match => {
        const valueFor = match[`${displayMetric}_for`];
        const valueAgainst = match[`${displayMetric}_against`];
        return `<div class="history-item">${formatNumber(valueFor)} - ${formatNumber(valueAgainst)} vs ${match.opponent}</div>`;
    }).join('') || '<div class="history-item">No history available.</div>';
    const metricLabel = displayMetric === 'xg' ? 'xG' : 'Goals';

    return `
            <div class="fixture-detail-prediction">
            <div class="detail-metric-label">${manualPrediction ? 'Private Safari ' : 'Predicted '}${metricLabel}</div>
            <div class="detail-metric-value">${formatNumber(combined)}</div>
            <div class="detail-metric-split">${formatNumber(homeExpected)} - ${formatNumber(awayExpected)}</div>
        </div>
        <div class="xg-bars" aria-hidden="true">
            <div class="xg-bar-container home-bar-container"><div class="xg-bar" style="width: ${homePercent}%"></div></div>
            <div class="xg-bar-container away-bar-container"><div class="xg-bar" style="width: ${awayPercent}%"></div></div>
        </div>
        <div class="match-history">
            <div class="history-list home">${historyHtml(fixture[homeHistoryKey])}</div>
            <div class="history-list away">${historyHtml(fixture[awayHistoryKey])}</div>
        </div>
        ${manualWeightsModule() ? manualWeightsModule().fixtureEditorHtml(fixture) : ''}
    `;
}

function createFixtureCard(fixture, scaleMax, metric) {
    const card = document.createElement('article');
    let expanded = false;

    function renderCard() {
        const favorite = isFavorite(fixture);
        card.className = `fixture-card ${expanded ? 'expanded' : 'compact'}`;
        card.innerHTML = `
            <div class="fixture-summary">
                <div class="team">
                    ${renderBadgeHtml(fixture.leagueId, fixture.home_team)}
                    <div class="team-name">${fixture.home_team}</div>
                </div>
                <div class="fixture-time" aria-label="Kickoff ${formatSourceKickoff(fixture)}">
                    <span>${fixture.status === 'FINISHED' ? 'Final' : 'Kickoff'}</span>
                    <strong>${fixture.status === 'FINISHED' ? `${fixture.home_goals ?? '—'} - ${fixture.away_goals ?? '—'}` : formatSourceKickoff(fixture)}</strong>
                </div>
                <div class="team">
                    ${renderBadgeHtml(fixture.leagueId, fixture.away_team)}
                    <div class="team-name">${fixture.away_team}</div>
                </div>
            </div>
            ${homeForecastSummaryHtml(fixture)}
            <div class="fixture-card-actions">
                ${renderForecastStatusHtml(fixture)}
                <button class="favorite-toggle" type="button" aria-pressed="${favorite}" aria-label="${favorite ? 'Remove' : 'Add'} ${fixture.home_team} versus ${fixture.away_team} ${favorite ? 'from' : 'to'} favorites">${favorite ? 'Favorited' : 'Favorite'}</button>
                <button class="fixture-details-toggle" type="button" aria-expanded="${expanded}" aria-label="${expanded ? 'Hide' : 'Show'} details for ${fixture.home_team} versus ${fixture.away_team}">${expanded ? 'Hide details' : 'View details'} <span class="details-toggle-icon" aria-hidden="true">⌄</span></button>
            </div>
            <div class="fixture-details ${expanded ? '' : 'hidden'}">${expanded ? fixtureDetailsHtml(fixture, scaleMax, metric) : ''}</div>
        `;
        const manualWeights = manualWeightsModule();
        if (expanded && manualWeights) manualWeights.bindEditor(card, fixture, renderCard);
    }

    function toggleDetails() {
        expanded = !expanded;
        renderCard();
    }

    renderCard();
    card.addEventListener('click', event => {
        const target = event.target;
        if (!target || typeof target.closest !== 'function') return;
        if (target.closest('.favorite-toggle')) {
            if (typeof event.preventDefault === 'function') event.preventDefault();
            if (typeof event.stopPropagation === 'function') event.stopPropagation();
            toggleFavorite(fixture);
            return;
        }
        if (target.closest('.fixture-details-toggle')) {
            if (typeof event.preventDefault === 'function') event.preventDefault();
            if (typeof event.stopPropagation === 'function') event.stopPropagation();
            toggleDetails();
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
        const isToday = offset === 0;
        button.className = `date-button ${isToday ? 'today' : ''} ${dateString === appState.activeDate ? 'active' : ''}`;
        button.setAttribute('type', 'button');
        button.setAttribute('aria-pressed', String(dateString === appState.activeDate));
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const accessibleDate = date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
        button.setAttribute('aria-label', isToday ? `Today, ${accessibleDate}` : accessibleDate);
        button.innerHTML = isToday
            ? '<div class="day-name">Today</div>'
            : `<div class="day-name">${dayNames[date.getDay()]}</div><div class="day-num">${date.getDate()}</div>`;
        button.addEventListener('click', () => {
            appState.activeDate = dateString;
            appState.activeSearchQuery = '';
            renderActiveTab();
        });
        dateStrip.appendChild(button);
    }
}

function fixtureMatchesSearch(fixture, query) {
    const normalized = String(query || '').trim().toLocaleLowerCase();
    if (!normalized) return true;
    return [fixture.home_team, fixture.away_team, fixture.leagueName]
        .some(value => String(value || '').toLocaleLowerCase().includes(normalized));
}

function fixtureStatusGroup(fixture) {
    if (fixture.status === 'FINISHED') return 'finished';
    if (['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED'].includes(fixture.status)) return 'upcoming';
    return 'other';
}

function fixtureMatchesHomeFilters(fixture) {
    const statusMatches = appState.homeStatusFilter === 'all'
        || fixtureStatusGroup(fixture) === appState.homeStatusFilter;
    const forecastMatches = appState.homeForecastFilter === 'all'
        || (appState.homeForecastFilter === 'available') === fixtureHasPublishedForecast(fixture);
    return statusMatches && forecastMatches;
}

function hasActiveHomeConstraints() {
    return Boolean(appState.activeSearchQuery.trim())
        || appState.homeStatusFilter !== 'all'
        || appState.homeForecastFilter !== 'all';
}

function resetHomeConstraints() {
    appState.activeSearchQuery = '';
    appState.homeStatusFilter = 'all';
    appState.homeForecastFilter = 'all';
    appState.homeFiltersOpen = false;
    renderActiveTab();
}

function activeHomeFilterCount() {
    return [appState.homeStatusFilter, appState.homeForecastFilter]
        .filter(value => value !== 'all').length;
}

function formatArtifactFreshness(value) {
    const parsed = new Date(value || '');
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toISOString().replace('T', ' ').replace(/\.\d{3}Z$/, ' UTC');
}

function createFilterGroup(labelText, stateKey, options) {
    const group = document.createElement('div');
    group.className = 'fixture-filter-group';
    const label = document.createElement('span');
    label.className = 'fixture-filter-label';
    label.textContent = labelText;
    group.appendChild(label);
    const controls = document.createElement('div');
    controls.className = 'fixture-filter-controls';
    options.forEach(([value, text]) => {
        const button = document.createElement('button');
        const selected = appState[stateKey] === value;
        button.className = `fixture-filter-button ${selected ? 'active' : ''}`;
        button.setAttribute('type', 'button');
        button.setAttribute('aria-pressed', String(selected));
        button.textContent = text;
        button.addEventListener('click', () => {
            appState[stateKey] = value;
            renderActiveTab();
        });
        controls.appendChild(button);
    });
    group.appendChild(controls);
    return group;
}

function createHomeToolbar(totalCount, visibleCount) {
    const toolbar = document.createElement('section');
    toolbar.className = 'home-toolbar';
    const countText = hasActiveHomeConstraints()
        ? `${visibleCount} of ${totalCount} matches`
        : `${totalCount} ${totalCount === 1 ? 'match' : 'matches'}`;

    const copy = document.createElement('div');
    copy.className = 'home-toolbar-copy';
    copy.innerHTML = `<p class="eyebrow">Match centre</p><h2>${formatHomeDate(appState.activeDate)} <span class="fixture-count">${countText}</span></h2><p>Browse scheduled and completed fixtures by competition.</p>`;
    const freshness = formatArtifactFreshness(appState.fixtureData && appState.fixtureData.meta && appState.fixtureData.meta.generated_at);
    if (freshness) {
        const freshnessLine = document.createElement('p');
        freshnessLine.className = 'artifact-freshness';
        freshnessLine.textContent = `Data updated ${freshness}`;
        freshnessLine.setAttribute('aria-label', `Fixture data artifact generated at ${freshness}`);
        copy.appendChild(freshnessLine);
    }

    const searchField = document.createElement('div');
    searchField.className = 'home-search-field';
    const label = document.createElement('label');
    label.setAttribute('for', 'home-search');
    label.textContent = 'Find a fixture';
    const input = document.createElement('input');
    input.id = 'home-search';
    input.className = 'search-input';
    input.setAttribute('type', 'search');
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('placeholder', 'Team or league');
    input.value = appState.activeSearchQuery;
    const help = document.createElement('p');
    help.className = 'home-search-help';
    help.textContent = 'Searches the selected date only.';
    input.addEventListener('input', event => {
        appState.activeSearchQuery = event.target.value || '';
        renderActiveTab();
    });
    searchField.appendChild(label);
    searchField.appendChild(input);
    searchField.appendChild(help);
    const filters = document.createElement('div');
    filters.className = `fixture-filters ${appState.homeFiltersOpen ? 'mobile-open' : ''}`;
    filters.setAttribute('aria-label', 'Fixture filters');
    filters.appendChild(createFilterGroup('Status', 'homeStatusFilter', HOME_STATUS_FILTERS));
    filters.appendChild(createFilterGroup('Forecast', 'homeForecastFilter', HOME_FORECAST_FILTERS));

    const filterActions = document.createElement('div');
    filterActions.className = 'home-filter-actions';
    const filterToggle = document.createElement('button');
    const activeFilterCount = activeHomeFilterCount();
    filterToggle.className = 'home-filter-toggle';
    filterToggle.setAttribute('type', 'button');
    filterToggle.setAttribute('aria-expanded', String(appState.homeFiltersOpen));
    filterToggle.setAttribute('aria-controls', 'home-fixture-filters');
    filterToggle.textContent = activeFilterCount ? `Filters (${activeFilterCount})` : 'Filters';
    filterToggle.addEventListener('click', () => {
        appState.homeFiltersOpen = !appState.homeFiltersOpen;
        renderActiveTab();
    });
    filters.id = 'home-fixture-filters';
    filterActions.appendChild(filterToggle);
    if (hasActiveHomeConstraints()) {
        const clear = document.createElement('button');
        clear.className = 'home-filter-clear';
        clear.setAttribute('type', 'button');
        clear.textContent = 'Clear';
        clear.addEventListener('click', resetHomeConstraints);
        filterActions.appendChild(clear);
    }

    toolbar.appendChild(copy);
    toolbar.appendChild(searchField);
    toolbar.appendChild(filters);
    toolbar.appendChild(filterActions);
    return toolbar;
}

function availableDatesAroundActiveDate() {
    const dates = [...new Set(appState.allFixtures.map(fixture => fixture.localDateStr).filter(Boolean))]
        .sort();
    const previous = dates.filter(date => date < appState.activeDate).at(-1) || null;
    const next = dates.find(date => date > appState.activeDate) || null;
    return { previous, next };
}

function createAvailableDateAction(label, date) {
    const button = document.createElement('button');
    button.className = 'empty-state-reset';
    button.setAttribute('type', 'button');
    button.textContent = `${label}: ${formatHomeDate(date)}`;
    button.addEventListener('click', () => {
        appState.activeDate = date;
        appState.activeSearchQuery = '';
        renderActiveTab();
    });
    return button;
}

function createHomeEmptyState(hasFixturesOnDate) {
    const state = document.createElement('div');
    state.className = 'no-fixtures';
    if (!hasFixturesOnDate) {
        state.innerHTML = '<div><strong>No fixtures on this date.</strong>Select an available date to view matches.</div>';
        const { previous, next } = availableDatesAroundActiveDate();
        if (previous || next) {
            const actions = document.createElement('div');
            actions.className = 'empty-state-date-actions';
            if (previous) actions.appendChild(createAvailableDateAction('Previous available', previous));
            if (next) actions.appendChild(createAvailableDateAction('Next available', next));
            state.appendChild(actions);
        }
        return state;
    }
    const statusPhrase = appState.homeStatusFilter === 'all' ? '' : `${appState.homeStatusFilter} `;
    const forecastPhrase = appState.homeForecastFilter === 'all' ? '' : `${appState.homeForecastFilter} forecast `;
    const searchPhrase = appState.activeSearchQuery.trim() ? ' matching this search' : '';
    const message = `No ${statusPhrase}${forecastPhrase}fixtures${searchPhrase}.`.replace(/\\s+/g, ' ');
    state.innerHTML = `<div><strong>${message}</strong>Try another filter or clear the current constraints.</div>`;
    const reset = document.createElement('button');
    reset.className = 'empty-state-reset';
    reset.setAttribute('type', 'button');
    reset.textContent = 'Clear filters';
    reset.addEventListener('click', resetHomeConstraints);
    state.appendChild(reset);
    return state;
}

function renderHome() {
    const container = document.getElementById('fixtures-container');
    const dateStrip = document.getElementById('date-strip');
    dateStrip.className = 'date-strip';
    renderDateStrip();
    container.innerHTML = '';

    const fixturesOnDate = appState.allFixtures.filter(fixture => fixture.localDateStr === appState.activeDate);
    const visibleFixtures = fixturesOnDate
        .filter(fixture => fixtureMatchesSearch(fixture, appState.activeSearchQuery))
        .filter(fixtureMatchesHomeFilters);
    container.appendChild(createHomeToolbar(fixturesOnDate.length, visibleFixtures.length));

    if (fixturesOnDate.length === 0 || visibleFixtures.length === 0) {
        container.appendChild(createHomeEmptyState(fixturesOnDate.length > 0));
        return;
    }

    const grouped = {};
    visibleFixtures.forEach(fixture => {
        if (!grouped[fixture.leagueId]) grouped[fixture.leagueId] = { name: fixture.leagueName, fixtures: [] };
        grouped[fixture.leagueId].fixtures.push(fixture);
    });

    Object.entries(grouped).forEach(([leagueId, league]) => {
        const leagueFixtures = league.fixtures.sort((left, right) => left.timeObj - right.timeObj);
        const section = document.createElement('section');
        section.className = 'league-section';
        const storageKey = `league_expansion:${appState.activeDate}:${leagueId}`;
        const open = localStorage.getItem(storageKey) !== 'closed';
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

function standingSortValue(team, viewId, sortId) {
    if (sortId === 'name') return team.name || '';
    if (sortId === 'matches') return Number.isFinite(team.matches_played) ? team.matches_played : null;
    const metricId = { combined: 'xg_goals', xg: 'xg', goals: 'goals' }[sortId];
    const metric = team.views && team.views[viewId] && team.views[viewId][metricId];
    return metric && Number.isFinite(metric.average) ? Math.abs(metric.average) : null;
}

function sortStandingTeams(teams) {
    return [...teams].sort((left, right) => {
        const leftValue = standingSortValue(left, appState.activeView, appState.activeSort);
        const rightValue = standingSortValue(right, appState.activeView, appState.activeSort);
        if (appState.activeSort === 'name') {
            const comparison = leftValue.localeCompare(rightValue);
            return appState.activeSortDirection === 'asc' ? comparison : -comparison;
        }
        const leftMissing = leftValue === null;
        const rightMissing = rightValue === null;
        if (leftMissing || rightMissing) {
            if (leftMissing && rightMissing) return left.name.localeCompare(right.name);
            return leftMissing ? 1 : -1;
        }
        const comparison = leftValue - rightValue;
        if (comparison !== 0) return appState.activeSortDirection === 'asc' ? comparison : -comparison;
        return left.name.localeCompare(right.name);
    });
}

function sortDirectionLabel() {
    if (appState.activeSort === 'name') return appState.activeSortDirection === 'asc' ? 'A–Z' : 'Z–A';
    if (appState.activeSort === 'matches') return appState.activeSortDirection === 'asc' ? 'Fewest first' : 'Most first';
    return appState.activeSortDirection === 'asc' ? 'Closest to zero' : 'Largest magnitude';
}

function renderStandingsSortControls() {
    const controls = document.createElement('div');
    controls.className = 'standings-sort-controls';
    const label = document.createElement('label');
    label.setAttribute('for', 'standings-sort');
    label.textContent = 'Sort by';
    const select = document.createElement('select');
    select.id = 'standings-sort';
    select.className = 'standings-sort-select';
    select.setAttribute('aria-label', 'Sort League table by');
    STANDINGS_SORT_OPTIONS.forEach(([value, labelText]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = labelText;
        if (value === appState.activeSort) option.setAttribute('selected', 'selected');
        select.appendChild(option);
    });
    select.value = appState.activeSort;
    select.addEventListener('change', event => {
        appState.activeSort = event.target.value;
        renderActiveTab();
    });
    const direction = document.createElement('button');
    direction.className = 'sort-direction-button';
    direction.setAttribute('type', 'button');
    direction.setAttribute('aria-label', `Sort direction: ${sortDirectionLabel()}`);
    direction.textContent = sortDirectionLabel();
    direction.addEventListener('click', () => {
        appState.activeSortDirection = appState.activeSortDirection === 'asc' ? 'desc' : 'asc';
        renderActiveTab();
    });
    controls.appendChild(label);
    controls.appendChild(select);
    controls.appendChild(direction);
    return controls;
}

function renderLeagueList() {
    const container = document.getElementById('fixtures-container');
    container.innerHTML = '<p class="eyebrow">Accuracy explorer</p><h2 class="tab-heading">League prediction accuracy</h2><p class="tab-description">Choose a league to inspect signed actual-minus-predicted performance by retained season.</p>';
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
            appState.activeSort = 'combined';
            appState.activeSortDirection = 'asc';
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
    container.appendChild(renderStandingsSortControls());

    const hasPredictionAccuracy = selectedSeason.teams.some(team => team.views.overall.xg || team.views.overall.goals);
    if (!hasPredictionAccuracy) {
        const note = document.createElement('p');
        note.className = 'season-unavailable-note';
        note.textContent = 'Matches played is retained for this season. Prediction accuracy is unavailable because original pre-match predictions were not stored.';
        container.appendChild(note);
    }

    const teams = sortStandingTeams(selectedSeason.teams);
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'standings-table-wrapper';
    tableWrapper.setAttribute('tabindex', '0');
    tableWrapper.setAttribute('aria-label', `${title.textContent} prediction accuracy table`);
    const table = document.createElement('table');
    table.className = 'standings-table';
    table.innerHTML = `
        <thead><tr><th scope="col">Team</th><th scope="col">Matches</th><th scope="col">xG PA</th><th scope="col">Goals PA</th><th scope="col">Combined PA</th></tr></thead>
        <tbody>${teams.map(team => {
            const view = team.views[appState.activeView];
            return `<tr><th scope="row">${renderStandingsTeamHtml(appState.activeLeagueId, team.name)}</th><td>${team.matches_played}</td><td>${formatPa(view.xg)}</td><td>${formatPa(view.goals)}</td><td>${formatPa(view.xg_goals)}</td></tr>`;
        }).join('')}</tbody>
    `;
    tableWrapper.appendChild(table);
    container.appendChild(tableWrapper);
}

function renderLeague() {
    const dateStrip = document.getElementById('date-strip');
    dateStrip.className = 'date-strip hidden';
    if (!appState.activeLeagueId) renderLeagueList();
    else renderLeagueDetail();
}

function renderFavorites() {
    const container = document.getElementById('fixtures-container');
    const dateStrip = document.getElementById('date-strip');
    dateStrip.className = 'date-strip hidden';
    const favorites = appState.allFixtures.filter(isFavorite).sort((left, right) => left.timeObj - right.timeObj);
    container.innerHTML = `<div class="favorites-heading-row"><div><p class="eyebrow">Your match list</p><h2 class="tab-heading">Favorites</h2></div><span class="favorites-count">${favorites.length} saved</span></div><p class="tab-description">Saved fixtures are kept only in this browser.</p>`;
    if (!favorites.length) {
        container.innerHTML += '<div class="no-fixtures"><div><strong>No saved fixtures yet.</strong>Use Favorite on a Home fixture to keep it here.</div></div>';
        return;
    }
    const grid = document.createElement('div');
    grid.className = 'favorites-grid';
    favorites.forEach(fixture => grid.appendChild(createFixtureCard(fixture, 3, fixture.metric || 'xg')));
    container.appendChild(grid);
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
            localDateStr: fixtureLocalDateString(fixture),
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
        container.innerHTML = '<div class="no-fixtures"><div><strong>Fixture data could not load.</strong>Please refresh and try again.</div></div>';
    }
}

function readLocalTeamLogos() {
    try {
        const stored = JSON.parse(localStorage.getItem('team_logos') || '{}');
        return stored && typeof stored === 'object' ? stored : {};
    } catch (error) {
        return {};
    }
}

function hideLogoDialog() {
    const dialog = document.getElementById('logo-dialog');
    if (!dialog) return;
    dialog.hidden = true;
    dialog.setAttribute('aria-hidden', 'true');
    const error = document.getElementById('logo-dialog-error');
    if (error) error.hidden = true;
    const trigger = logoDialogState.trigger;
    logoDialogState = { teamName: null, trigger: null };
    if (trigger && typeof trigger.focus === 'function') trigger.focus();
}

function showLogoDialog(teamName, trigger) {
    const dialog = document.getElementById('logo-dialog');
    const teamLabel = document.getElementById('logo-dialog-team');
    const input = document.getElementById('logo-url');
    const error = document.getElementById('logo-dialog-error');
    if (!dialog || !teamLabel || !input) return;
    logoDialogState = { teamName, trigger };
    const teamLogos = readLocalTeamLogos();
    teamLabel.textContent = teamName;
    input.value = teamLogos[teamName] || '';
    if (error) error.hidden = true;
    dialog.hidden = false;
    dialog.setAttribute('aria-hidden', 'false');
    if (typeof input.focus === 'function') input.focus();
}

function saveLocalTeamLogo(teamName, value) {
    const teamLogos = readLocalTeamLogos();
    if (value) teamLogos[teamName] = value;
    else delete teamLogos[teamName];
    localStorage.setItem('team_logos', JSON.stringify(teamLogos));
}

function setupLogoDialog() {
    const dialog = document.getElementById('logo-dialog');
    const form = document.getElementById('logo-form');
    const input = document.getElementById('logo-url');
    const close = document.getElementById('logo-dialog-close');
    const cancel = document.getElementById('logo-dialog-cancel');
    const remove = document.getElementById('logo-remove');
    const error = document.getElementById('logo-dialog-error');
    if (!dialog || !form || !input) return;

    const closeDialog = () => hideLogoDialog();
    if (close) close.addEventListener('click', closeDialog);
    if (cancel) cancel.addEventListener('click', closeDialog);
    dialog.addEventListener('click', event => {
        const target = event.target;
        if (target && typeof target.closest === 'function' && target.closest('[data-logo-dialog-close="true"]')) closeDialog();
    });
    if (remove) remove.addEventListener('click', () => {
        if (!logoDialogState.teamName) return;
        try {
            saveLocalTeamLogo(logoDialogState.teamName, '');
            hideLogoDialog();
            renderActiveTab();
        } catch (storageError) {
            if (error) {
                error.textContent = 'Your browser could not save that preference.';
                error.hidden = false;
            }
        }
    });
    form.addEventListener('submit', event => {
        if (typeof event.preventDefault === 'function') event.preventDefault();
        if (!logoDialogState.teamName) return;
        const value = String(input.value || '').trim();
        if (value) {
            try {
                const url = new URL(value);
                if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Unsupported protocol');
            } catch (urlError) {
                if (error) {
                    error.textContent = 'Enter a valid http or https image URL.';
                    error.hidden = false;
                }
                return;
            }
        }
        try {
            saveLocalTeamLogo(logoDialogState.teamName, value);
            hideLogoDialog();
            renderActiveTab();
        } catch (storageError) {
            if (error) {
                error.textContent = 'Your browser could not save that preference.';
                error.hidden = false;
            }
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !dialog.hidden) hideLogoDialog();
    });
}

function setupLogoClickHandlers() {
    document.body.addEventListener('click', event => {
        const badge = event.target && typeof event.target.closest === 'function' ? event.target.closest('.team-badge') : null;
        if (!badge) return;
        if (typeof event.preventDefault === 'function') event.preventDefault();
        const teamName = badge.dataset.team;
        if (teamName) showLogoDialog(teamName, badge);
    });
}

function syncThemeButton() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) return;
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    toggleBtn.setAttribute('aria-pressed', String(dark));
    toggleBtn.setAttribute('aria-label', dark ? 'Enable light theme' : 'Enable dark theme');
    const icon = typeof toggleBtn.querySelector === 'function' ? toggleBtn.querySelector('.theme-toggle-icon') : null;
    if (icon) icon.textContent = dark ? '☼' : '◐';
}

function setupTheme() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) return;
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    syncThemeButton();
    toggleBtn.addEventListener('click', () => {
        const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        syncThemeButton();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    init();
    setupTheme();
    setupLogoDialog();
    setupLogoClickHandlers();
});
