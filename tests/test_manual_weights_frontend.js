const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'public', 'manual-weights.js'), 'utf8');
const storage = new Map();
const localStorage = {
    getItem: key => storage.has(key) ? storage.get(key) : null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: key => storage.delete(key),
};
const window = {};
vm.runInNewContext(source, { window, localStorage, console, Math, Number, String, Map, Array, Error, JSON, Date, encodeURIComponent, Object });

const manualWeights = window.OPMManualWeights;
const homeMatches = [
    { opponent: 'A', date: '2026-08-22', venue: 'away', xg_for: 0.85, xg_against: 1.98, goals_for: 1, goals_against: 2 },
    { opponent: 'B', date: '2026-08-16', venue: 'home', xg_for: 0.89, xg_against: 0.85, goals_for: 1, goals_against: 1 },
    { opponent: 'C', date: '2026-08-08', venue: 'home', xg_for: 0.22, xg_against: 2.20, goals_for: 0, goals_against: 2 },
    { opponent: 'D', date: '2026-08-01', venue: 'away', xg_for: 0.73, xg_against: 4.11, goals_for: 1, goals_against: 4 },
];
const awayMatches = [
    { opponent: 'E', date: '2026-08-21', venue: 'away', xg_for: 0.66, xg_against: 1.14, goals_for: 1, goals_against: 1 },
    { opponent: 'F', date: '2026-08-14', venue: 'home', xg_for: 1.20, xg_against: 0.92, goals_for: 2, goals_against: 1 },
    { opponent: 'G', date: '2026-08-07', venue: 'home', xg_for: 0.91, xg_against: 1.35, goals_for: 1, goals_against: 2 },
    { opponent: 'H', date: '2026-07-31', venue: 'away', xg_for: 0.45, xg_against: 1.72, goals_for: 0, goals_against: 2 },
];

function fixture(date) {
    return {
        leagueId: 'test-league',
        home_team: 'Home FC',
        away_team: 'Away FC',
        date,
        home_last_4_matches: homeMatches,
        away_last_4_matches: awayMatches,
    };
}

const selectedFixture = fixture('2026-08-30');
let preview = manualWeights.fixturePreview(selectedFixture);
assert.deepStrictEqual(preview.homeRows.map(row => row.weight_bps), [2500, 2500, 2500, 2500]);
assert.deepStrictEqual(preview.awayRows.map(row => row.weight_bps), [2500, 2500, 2500, 2500]);

manualWeights.writeFixtureStorage(selectedFixture, {
    homeWeights: [0, 3334, 3333, 3333],
    awayWeights: [2500, 2500, 2500, 2500],
    homePinned: [true, false, false, false],
    awayPinned: [false, false, false, false],
});
preview = manualWeights.fixturePreview(selectedFixture);
assert.deepStrictEqual(preview.homeRows.map(row => row.weight_bps), [0, 3334, 3333, 3333]);
assert.strictEqual(preview.homeRows.reduce((total, row) => total + row.weight_bps, 0), 10000);
assert.notStrictEqual(preview.home_expected_goals, null);

const futureFixture = fixture('2026-09-06');
const futurePreview = manualWeights.fixturePreview(futureFixture);
assert.deepStrictEqual(futurePreview.homeRows.map(row => row.weight_bps), [2500, 2500, 2500, 2500]);
assert.notStrictEqual(manualWeights.fixtureKey(selectedFixture), manualWeights.fixtureKey(futureFixture));

console.log('Safari-only manual fixture weight tests passed.');
