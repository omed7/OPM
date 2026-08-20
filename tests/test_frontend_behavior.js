const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const scriptPath = path.join(__dirname, '..', 'public', 'script.js');
const scriptSource = fs.readFileSync(scriptPath, 'utf8');

class ClassList {
    constructor() {
        this.values = new Set();
    }

    add(value) {
        this.values.add(value);
    }

    contains(value) {
        return this.values.has(value);
    }

    remove(value) {
        this.values.delete(value);
    }
}

class Element {
    constructor(tagName) {
        this.tagName = tagName;
        this.children = [];
        this.className = '';
        this.classList = new ClassList();
        this._innerHTML = '';
        this.textContent = '';
        this.listeners = {};
        this.style = {};
        this.attributes = {};
        this.id = '';
        this.dataset = {};
    }

    get innerHTML() {
        return this._innerHTML;
    }

    set innerHTML(value) {
        this._innerHTML = value;
        this.children = [];
    }

    appendChild(child) {
        this.children.push(child);
        return child;
    }

    addEventListener(eventName, listener) {
        this.listeners[eventName] = listener;
    }

    setAttribute(name, value) {
        this.attributes[name] = String(value);
        if (name === 'id') this.id = String(value);
    }

    getAttribute(name) {
        return this.attributes[name] || null;
    }

    click() {
        if (this.listeners.click) this.listeners.click({ target: this });
    }
}

class FakeDate extends Date {
    constructor(value) {
        super(value === undefined ? '2026-08-16T12:00:00Z' : value);
    }
}

function createStorage(initialValues = {}) {
    const values = new Map(Object.entries(initialValues));
    return {
        getItem(key) {
            return values.has(key) ? values.get(key) : null;
        },
        setItem(key, value) {
            values.set(key, String(value));
        },
    };
}

function response(ok, payload) {
    return { ok, json: async () => payload };
}

async function boot({
    data,
    dataOk = true,
    standings = { leagues: [] },
    standingsOk = true,
    badges = { badges: {} },
    badgesOk = true,
    version = 'test-version',
    initialStorage = {},
}) {
    const elements = {
        'fixtures-container': new Element('main'),
        'version-tag': new Element('p'),
        'date-strip': new Element('div'),
        'theme-toggle': new Element('button'),
        'badge-attribution': new Element('p'),
        'home-tab': new Element('button'),
        'league-tab': new Element('button'),
        'favorite-tab': new Element('button'),
    };
    const storage = createStorage(initialStorage);
    const errors = [];
    let readyHandler;
    const document = {
        body: new Element('body'),
        documentElement: {
            attributes: {},
            setAttribute(name, value) {
                this.attributes[name] = value;
            },
            getAttribute(name) {
                return this.attributes[name] || null;
            },
        },
        getElementById(id) {
            return elements[id] || null;
        },
        createElement(tagName) {
            return new Element(tagName);
        },
        querySelectorAll() {
            return [];
        },
        addEventListener(eventName, listener) {
            if (eventName === 'DOMContentLoaded') readyHandler = listener;
        },
    };
    const context = {
        Date: FakeDate,
        console: { error(error) { errors.push(String(error)); } },
        document,
        fetch: async url => {
            if (url === 'data.json') return response(dataOk, data);
            if (url === 'league_standings.json') return response(standingsOk, standings);
            if (url === 'team_badges.json') return response(badgesOk, badges);
            if (url === 'version.json') return response(true, { version });
            throw new Error(`Unexpected fetch: ${url}`);
        },
        localStorage: storage,
        prompt: () => null,
        setImmediate,
    };
    vm.runInNewContext(scriptSource, context, { filename: scriptPath });
    readyHandler();
    for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve));
    return { document, elements, storage, errors };
}

function predictionFixture() {
    return {
        home_team: 'Home FC',
        away_team: 'Away FC',
        date: '2026-08-16',
        kickoff_time: '21:30',
        home_expected_xg: 1.7,
        away_expected_xg: 1.2,
        combined_expected_xg: 2.9,
        home_expected_goals: 1.5,
        away_expected_goals: 1.0,
        combined_expected_goals: 2.5,
        home_last_4_matches: [{ opponent: 'H1', xg_for: 2, xg_against: 1, goals_for: 2, goals_against: 1 }],
        away_last_4_matches: [{ opponent: 'A1', xg_for: 1, xg_against: 2, goals_for: 1, goals_against: 2 }],
    };
}

function goalsOnlyFinishedFixture() {
    return {
        home_team: 'Goals Home',
        away_team: 'Goals Away',
        date: '2026-08-16',
        kickoff_time: '18:00',
        status: 'FINISHED',
        home_goals: 2,
        away_goals: 1,
        home_xg: null,
        away_xg: null,
        home_expected_goals: 1.4,
        away_expected_goals: 0.9,
    };
}

function standingsFixture() {
    const unavailable = { xg: null, goals: null, xg_goals: null };
    return {
        schema_version: 1,
        leagues: [{
            id: 'premier_league',
            name: 'Premier League',
            seasons: [
                {
                    id: '2026-07-01',
                    label: '2026/27',
                    prediction_provenance: 'reconstructed_historical',
                    teams: [{
                        name: 'Home FC',
                        matches_played: 1,
                        views: {
                            overall: {
                                xg: { total: 0.4, average: 0.4, eligible_matches: 1 },
                                goals: { total: 1.5, average: 1.5, eligible_matches: 1 },
                                xg_goals: { total: 0.95, average: 0.95 },
                            },
                            for: {
                                xg: { total: -0.1, average: -0.1, eligible_matches: 1 },
                                goals: { total: 0.5, average: 0.5, eligible_matches: 1 },
                                xg_goals: { total: 0.2, average: 0.2 },
                            },
                            against: {
                                xg: { total: 0.5, average: 0.5, eligible_matches: 1 },
                                goals: { total: 1.0, average: 1.0, eligible_matches: 1 },
                                xg_goals: { total: 0.75, average: 0.75 },
                            },
                        },
                    }],
                },
                {
                    id: '2025-07-01',
                    label: '2025/26',
                    prediction_provenance: 'unavailable',
                    teams: [{ name: 'Historic FC', matches_played: 20, views: { overall: unavailable, for: unavailable, against: unavailable } }],
                },
            ],
        }],
    };
}

function homeCard(elements) {
    const section = elements['fixtures-container'].children[0];
    return section.children[1].children[0];
}

async function testHomeDefaultsToCompactFixtureDetailsAndFavorites() {
    const app = await boot({
        data: { leagues: [{ id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [predictionFixture()] }] },
    });
    const { elements, storage, document, errors } = app;
    const card = homeCard(elements);

    assert.strictEqual(elements['home-tab'].getAttribute('aria-selected'), 'true');
    assert.strictEqual(elements['date-strip'].children.length, 7);
    assert.match(card.innerHTML, /UTC\+03:00 · 21:30/);
    assert.doesNotMatch(card.innerHTML, /Predicted xG/);
    assert.doesNotMatch(card.innerHTML, /1\.70/);

    card.click();
    assert.match(card.innerHTML, /Predicted xG/);
    assert.match(card.innerHTML, /1\.70 - 1\.20/);

    card.listeners.click({
        target: { closest: selector => (selector === '.favorite-toggle' ? {} : null) },
        preventDefault() {},
        stopPropagation() {},
    });
    assert.match(storage.getItem('opm:favorites:v1'), /Home FC/);

    elements['favorite-tab'].click();
    assert.strictEqual(elements['favorite-tab'].getAttribute('aria-selected'), 'true');
    assert.strictEqual(elements['fixtures-container'].children.length, 1);
    assert.match(elements['fixtures-container'].children[0].innerHTML, /Home FC/);

    assert.strictEqual(document.documentElement.getAttribute('data-theme'), 'light');
    elements['theme-toggle'].click();
    assert.strictEqual(document.documentElement.getAttribute('data-theme'), 'dark');
    assert.strictEqual(storage.getItem('theme'), 'dark');
    assert.deepStrictEqual(errors, []);
}

async function testGoalsOnlyFinishedFixtureExplainsMissingXg() {
    const app = await boot({
        data: { leagues: [{ id: 'admiral-bundesliga', name: 'Admiral Bundesliga', metric: 'goals', fixtures: [goalsOnlyFinishedFixture()] }] },
    });
    const card = homeCard(app.elements);

    card.click();
    assert.match(card.innerHTML, /FT Score/);
    assert.match(card.innerHTML, /2 - 1/);
    assert.match(card.innerHTML, /Goals-only result/);
    assert.match(card.innerHTML, /xG unavailable/);
    assert.doesNotMatch(card.innerHTML, /Actual xG/);
    assert.deepStrictEqual(app.errors, []);
}

async function testLeagueSeasonNavigationAndPaModes() {
    const app = await boot({
        data: { leagues: [{ id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [predictionFixture()] }] },
        standings: standingsFixture(),
    });
    const { elements, errors } = app;

    elements['league-tab'].click();
    const directory = elements['fixtures-container'].children[0];
    assert.strictEqual(directory.children.length, 1);
    directory.children[0].click();

    const container = elements['fixtures-container'];
    const seasonSelector = container.children[1];
    const controls = container.children[3];
    const currentTable = container.children[4].children[0];
    assert.strictEqual(seasonSelector.children[0].textContent, '2026/27');
    assert.match(currentTable.innerHTML, /\+0\.40 \/ \+0\.40/);
    assert.match(currentTable.innerHTML, /\+0\.95 \/ \+0\.95/);
    assert.match(container.children[2].textContent, /Reconstructed historical prediction/);

    controls.children[1].click();
    const forTable = elements['fixtures-container'].children[4].children[0];
    assert.match(forTable.innerHTML, /-0\.10 \/ -0\.10/);
    assert.match(forTable.innerHTML, /\+0\.20 \/ \+0\.20/);

    const refreshedSelector = elements['fixtures-container'].children[1];
    refreshedSelector.children[0].click();
    refreshedSelector.children[1].children[1].click();
    const historicContainer = elements['fixtures-container'];
    const historicTable = historicContainer.children[5].children[0];
    assert.strictEqual(historicContainer.children[1].children[0].textContent, '2025/26');
    assert.match(historicTable.innerHTML, /Historic FC/);
    assert.match(historicTable.innerHTML, /—/);
    assert.match(historicContainer.children[4].textContent, /Prediction accuracy is unavailable/);
    assert.deepStrictEqual(errors, []);
}

async function testBadgeManifestAttributionAndFallback() {
    const app = await boot({
        data: { leagues: [{ id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [predictionFixture()] }] },
        badges: {
            source: { attribution: 'Team badges: TheSportsDB' },
            badges: { premier_league: { 'Home FC': { badge_url: 'https://r2.thesportsdb.com/images/home-fc.png' } } },
        },
    });
    const cardHtml = homeCard(app.elements).innerHTML;
    assert.match(cardHtml, /https:\/\/r2\.thesportsdb\.com\/images\/home-fc\.png/);
    assert.match(cardHtml, /data-team="Away FC"[^>]*>AF<\/div>/);
    assert.strictEqual(app.elements['badge-attribution'].textContent, 'Team badges: TheSportsDB');
    assert.deepStrictEqual(app.errors, []);
}

async function testEmptyArtifactAndDataLoadError() {
    const empty = await boot({ data: { leagues: [] } });
    assert.match(empty.elements['fixtures-container'].innerHTML, /No leagues found/);
    assert.deepStrictEqual(empty.errors, []);

    const failed = await boot({ data: {}, dataOk: false });
    assert.match(failed.elements['fixtures-container'].innerHTML, /Error loading fixtures/);
    assert.strictEqual(failed.errors.length, 1);
    assert.match(failed.errors[0], /Failed to fetch data/);
}

(async () => {
    await testHomeDefaultsToCompactFixtureDetailsAndFavorites();
    await testGoalsOnlyFinishedFixtureExplainsMissingXg();
    await testLeagueSeasonNavigationAndPaModes();
    await testBadgeManifestAttributionAndFallback();
    await testEmptyArtifactAndDataLoadError();
    console.log('Frontend behavior tests passed.');
})().catch(error => {
    console.error(error);
    process.exit(1);
});
