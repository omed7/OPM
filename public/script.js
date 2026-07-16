async function init() {
    const container = document.getElementById('fixtures-container');
    const versionTag = document.getElementById('version-tag');

    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Failed to fetch data');
        const data = await response.json();

        // Update version tag
        if (data.meta) {
            const date = new Date(data.meta.generated_at).toLocaleString();
            versionTag.textContent = `Version: ${data.meta.version} | Generated at: ${date}`;
        }

        if (!data.fixtures || data.fixtures.length === 0) {
            container.innerHTML = '<div class="no-fixtures">No upcoming fixtures found.</div>';
            return;
        }

        // Sort chronologically
        data.fixtures.sort((a, b) => new Date(a.date) - new Date(b.date));

        // Find max xG for scale
        let maxSingleXG = 0;
        data.fixtures.forEach(f => {
            maxSingleXG = Math.max(maxSingleXG, f.home_expected_xg, f.away_expected_xg);
        });
        // Add a bit of buffer
        const scaleMax = Math.max(maxSingleXG * 1.1, 3.0);

        container.innerHTML = '';
        data.fixtures.forEach(fixture => {
            container.appendChild(createFixtureCard(fixture, scaleMax));
        });

    } catch (error) {
        console.error(error);
        container.innerHTML = '<div class="no-fixtures">Error loading fixtures. Please try again later.</div>';
    }
}

function createFixtureCard(fixture, scaleMax) {
    const card = document.createElement('div');
    card.className = 'fixture-card';

    const homeInitials = getInitials(fixture.home_team);
    const awayInitials = getInitials(fixture.away_team);
    const homeColor = getColor(fixture.home_team);
    const awayColor = getColor(fixture.away_team);

    const homeXGPercent = (fixture.home_expected_xg / scaleMax) * 100;
    const awayXGPercent = (fixture.away_expected_xg / scaleMax) * 100;

    const homeHistory = (fixture.home_last_4_matches || []).map(m =>
        `<div class="history-item">${m.xg_for.toFixed(2)} - ${m.xg_against.toFixed(2)} vs ${m.opponent}</div>`
    ).join('');

    const awayHistory = (fixture.away_last_4_matches || []).map(m =>
        `<div class="history-item">${m.xg_for.toFixed(2)} - ${m.xg_against.toFixed(2)} vs ${m.opponent}</div>`
    ).join('');

    card.innerHTML = `
        <div class="fixture-header">
            <div class="team">
                <div class="team-badge" style="background-color: ${homeColor}">${homeInitials}</div>
                <div class="team-name">${fixture.home_team}</div>
            </div>
            <div class="xg-center">
                <div class="combined-xg-label">XG Combined</div>
                <div class="combined-xg">${fixture.combined_expected_xg.toFixed(2)}</div>
                <div class="split-xg">${fixture.home_expected_xg.toFixed(2)} - ${fixture.away_expected_xg.toFixed(2)}</div>
            </div>
            <div class="team">
                <div class="team-badge" style="background-color: ${awayColor}">${awayInitials}</div>
                <div class="team-name">${fixture.away_team}</div>
            </div>
        </div>
        <div class="xg-bars">
            <div class="xg-bar-container" id="home-bar-container">
                <div class="xg-bar" style="width: ${homeXGPercent}%"></div>
            </div>
            <div class="xg-bar-container" id="away-bar-container">
                <div class="xg-bar" style="width: ${awayXGPercent}%"></div>
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
    // Simple hash to get a consistent color from team name
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
    const color = "00000".substring(0, 6 - c.length) + c;

    // Ensure it's not too light (for white text)
    // Actually, let's use a predefined set of colors or a better hash-to-HSL
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 60%, 40%)`;
}

document.addEventListener('DOMContentLoaded', init);
