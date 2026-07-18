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
                btn.textContent = league.name;
                btn.addEventListener('click', () => {
                    if (activeLeagueId === league.id) return;
                    activeLeagueId = league.id;

                    // Update active class on buttons
                    tabContainer.querySelectorAll('.tab-button').forEach(b => {
                        b.classList.toggle('active', b.textContent === league.name);
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

            // Copy and sort chronologically per league
            const sortedFixtures = [...league.fixtures].sort((a, b) => new Date(a.date) - new Date(b.date));

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

document.addEventListener('DOMContentLoaded', init);
