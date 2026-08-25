const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const scriptPath = path.join(__dirname, '..', 'public', 'script.js');
const scriptSource = fs.readFileSync(scriptPath, 'utf8');
const manualWeightsPath = path.join(__dirname, '..', 'public', 'manual-weights.js');
const manualWeightsSource = fs.readFileSync(manualWeightsPath, 'utf8');

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
        this.value = '';
        this.hidden = false;
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

    querySelector() {
        return null;
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

class FakeGmtPlusThreeDate extends Date {
    constructor(value) {
        const instant = value === undefined ? '2026-08-23T12:00:00Z' : value;
        super(new Date(instant).getTime() + (3 * 60 * 60 * 1000));
    }

    getFullYear() { return this.getUTCFullYear(); }
    getMonth() { return this.getUTCMonth(); }
    getDate() { return this.getUTCDate(); }
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
    DateImpl = FakeDate,
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
        'logo-dialog': new Element('div'),
        'logo-dialog-team': new Element('strong'),
        'logo-url': new Element('input'),
        'logo-dialog-error': new Element('p'),
        'logo-form': new Element('form'),
        'logo-dialog-close': new Element('button'),
        'logo-dialog-cancel': new Element('button'),
        'logo-remove': new Element('button'),
    };
    elements['logo-dialog'].hidden = true;
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
        addEventListener(eventName, listener) {
            if (eventName === 'DOMContentLoaded') readyHandler = listener;
        },
    };
    const manualWindow = {};
    vm.runInNewContext(manualWeightsSource, {
        window: manualWindow,
        localStorage: storage,
        console,
        Math,
        Number,
        String,
        Map,
        Array,
        Error,
        JSON,
        Date: DateImpl,
        encodeURIComponent,
        Object,
    }, { filename: manualWeightsPath });
    const context = {
        Date: DateImpl,
        URL,
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
        window: manualWindow,
        setImmediate,
    };
    vm.runInNewContext(scriptSource, context, { filename: scriptPath });
    readyHandler();
    for (let index = 0; index < 8; index += 1) await new Promise(resolve => setImmediate(resolve));
    return { document, elements, storage, errors, context };
}

function predictionFixture(overrides = {}) {
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
        ...overrides,
    };
}

function goalsOnlyFinishedFixture(overrides = {}) {
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
        ...overrides,
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

function sortableStandingsFixture() {
    const metric = average => (average === null ? null : { total: average, average, eligible_matches: 1 });
    const views = (xg, goals, combined) => ({
        overall: { xg: metric(xg), goals: metric(goals), xg_goals: metric(combined) },
        for: { xg: metric(xg), goals: metric(goals), xg_goals: metric(combined) },
        against: { xg: metric(xg), goals: metric(goals), xg_goals: metric(combined) },
    });
    return {
        leagues: [{
            id: 'premier_league',
            name: 'Premier League',
            seasons: [{
                id: '2026-07-01',
                label: '2026/27',
                prediction_provenance: 'stored_pre_match',
                teams: [
                    { name: 'Atletico FC', matches_played: 4, views: views(0.9, 0.1, 0.4) },
                    { name: 'Bravo FC', matches_played: 3, views: views(0.4, 0.5, 0.1) },
                    { name: 'Deportivo La Coruna', matches_played: 1, views: views(null, null, null) },
                ],
            }],
        }],
    };
}

function homeToolbar(elements) {
    return elements['fixtures-container'].children[0];
}

function homeSection(elements) {
    return elements['fixtures-container'].children[1];
}

function homeCard(elements) {
    const section = homeSection(elements);
    return section.children[1].children[0];
}

function renderedLeagueTable(container) {
    const wrapper = container.children.find(child => child.className === 'standings-table-wrapper');
    return wrapper.children[0];
}

function renderedSortControls(container) {
    return container.children.find(child => child.className === 'standings-sort-controls');
}

function activateCardControl(card, selector) {
    card.listeners.click({
        target: { closest: value => (value === selector ? {} : null) },
        preventDefault() {},
        stopPropagation() {},
    });
}

async function testHomeSearchDetailsAndFavorites() {
    const app = await boot({
        data: {
            leagues: [
                { id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [predictionFixture()] },
                { id: 'la_liga', name: 'La Liga', metric: 'xg', fixtures: [predictionFixture({ home_team: 'Madrid FC', away_team: 'City FC', kickoff_time: '18:30' })] },
            ],
        },
    });
    const { elements, storage, document, errors } = app;
    let card = homeCard(elements);

    assert.strictEqual(elements['home-tab'].getAttribute('aria-selected'), 'true');
    assert.strictEqual(elements['date-strip'].children.length, 7);
    const todayButton = elements['date-strip'].children[3];
    assert.match(todayButton.innerHTML, /Today/);
    assert.doesNotMatch(todayButton.innerHTML, /day-num/);
    assert.match(todayButton.getAttribute('aria-label'), /^Today,/);
    assert.match(homeToolbar(elements).children[0].innerHTML, /2 matches/);
    assert.match(card.innerHTML, /UTC\+03:00 · 21:30/);
    assert.match(card.innerHTML, /View details/);
    assert.doesNotMatch(card.innerHTML, /Predicted xG/);

    activateCardControl(card, '.fixture-details-toggle');
    assert.match(card.innerHTML, /Predicted xG/);
    assert.match(card.innerHTML, /1\.70 - 1\.20/);
    assert.match(card.innerHTML, /Hide details/);

    activateCardControl(card, '.favorite-toggle');
    assert.match(storage.getItem('opm:favorites:v1'), /Home FC/);

    let search = homeToolbar(elements).children[1].children[1];
    search.listeners.input({ target: { value: 'Madrid' } });
    assert.match(homeToolbar(elements).children[0].innerHTML, /1 of 2 matches/);
    assert.match(homeCard(elements).innerHTML, /Madrid FC/);

    search = homeToolbar(elements).children[1].children[1];
    search.listeners.input({ target: { value: 'Unknown Club' } });
    assert.match(elements['fixtures-container'].children[1].innerHTML, /No fixtures matching this search/);

    search = homeToolbar(elements).children[1].children[1];
    search.listeners.input({ target: { value: '' } });
    assert.match(homeCard(elements).innerHTML, /Home FC/);

    elements['favorite-tab'].click();
    assert.strictEqual(elements['favorite-tab'].getAttribute('aria-selected'), 'true');
    assert.strictEqual(elements['fixtures-container'].children.length, 1);
    assert.match(elements['fixtures-container'].children[0].children[0].innerHTML, /Home FC/);

    assert.strictEqual(document.documentElement.getAttribute('data-theme'), 'light');
    elements['theme-toggle'].click();
    assert.strictEqual(document.documentElement.getAttribute('data-theme'), 'dark');
    assert.strictEqual(elements['theme-toggle'].getAttribute('aria-pressed'), 'true');
    assert.strictEqual(storage.getItem('theme'), 'dark');
    assert.deepStrictEqual(errors, []);
}

async function testUnavailableUpcomingFixtureStillRendersManualEditor() {
    const history = (prefix, xgFor, xgAgainst) => Array.from({ length: 4 }, (_, index) => ({
        opponent: `${prefix}${index + 1}`,
        date: `2026-08-${String(12 - index).padStart(2, '0')}`,
        venue: index % 2 ? 'away' : 'home',
        xg_for: xgFor + index / 10,
        xg_against: xgAgainst + index / 10,
        goals_for: 1,
        goals_against: 1,
    }));
    const unavailable = predictionFixture({
        home_expected_xg: null,
        away_expected_xg: null,
        combined_expected_xg: null,
        home_expected_goals: null,
        away_expected_goals: null,
        combined_expected_goals: null,
        home_last_4_matches: history('Home history ', 0.8, 1.1),
        away_last_4_matches: history('Away history ', 0.7, 1.2),
    });
    const app = await boot({
        data: { leagues: [{ id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [unavailable] }] },
    });
    const card = homeCard(app.elements);
    activateCardControl(card, '.fixture-details-toggle');
    assert.match(card.innerHTML, /Manual match weights/);
    assert.match(card.innerHTML, /Manual xG:/);
    assert.deepStrictEqual(app.errors, []);
}

async function testXgOnlyForecastStaysAvailableOnHome() {
    const xgOnly = predictionFixture({
        home_expected_goals: null,
        away_expected_goals: null,
        combined_expected_goals: null,
    });
    const app = await boot({
        data: { leagues: [{ id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [xgOnly] }] },
    });
    const card = homeCard(app.elements);
    assert.match(card.innerHTML, /xG forecast available/);
    assert.doesNotMatch(card.innerHTML, /Forecast unavailable/);
    activateCardControl(card, '.fixture-details-toggle');
    assert.match(card.innerHTML, /Predicted xG/);
    assert.match(card.innerHTML, /1\.70 - 1\.20/);
    assert.doesNotMatch(card.innerHTML, /No qualifying pre-match forecast/);
    assert.deepStrictEqual(app.errors, []);
}

async function testFixtureIntelligenceFiltersAvailabilityAndFreshness() {
    const app = await boot({
        data: {
            meta: { generated_at: '2026-08-16T08:30:00Z' },
            leagues: [
                { id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [predictionFixture({ status: 'SCHEDULED' })] },
                { id: 'la_liga', name: 'La Liga', metric: 'xg', fixtures: [predictionFixture({
                    home_team: 'Finished FC',
                    away_team: 'Result FC',
                    status: 'FINISHED',
                    home_goals: 2,
                    away_goals: 1,
                    combined_expected_xg: null,
                    combined_expected_goals: null,
                })] },
            ],
        },
    });
    const { elements, errors } = app;
    assert.strictEqual(homeToolbar(elements).children[0].children[0].textContent, 'Data updated 2026-08-16 08:30:00 UTC');
    assert.match(homeCard(elements).innerHTML, /Forecast available/);

    let filters = homeToolbar(elements).children[2];
    let statusControls = filters.children[0].children[1];
    statusControls.children[1].click();
    assert.match(homeCard(elements).innerHTML, /Home FC/);

    filters = homeToolbar(elements).children[2];
    statusControls = filters.children[0].children[1];
    statusControls.children[2].click();
    assert.match(homeCard(elements).innerHTML, /Finished FC/);
    assert.match(homeCard(elements).innerHTML, /Forecast unavailable/);

    filters = homeToolbar(elements).children[2];
    const forecastControls = filters.children[1].children[1];
    forecastControls.children[1].click();
    const emptyState = elements['fixtures-container'].children[1];
    assert.match(emptyState.innerHTML, /No finished available forecast fixtures/);
    assert.strictEqual(emptyState.children[0].textContent, 'Clear filters');
    emptyState.children[0].click();
    assert.match(homeCard(elements).innerHTML, /Home FC/);
    assert.match(homeToolbar(elements).children[0].innerHTML, /2 matches/);
    assert.deepStrictEqual(errors, []);
}

async function testCompletedTimestampUsesViewerLocalDateWithDateOnlyFallback() {
    const app = await boot({
        DateImpl: FakeGmtPlusThreeDate,
        data: {
            leagues: [{
                id: 'mls',
                name: 'Major League Soccer',
                metric: 'xg',
                fixtures: [
                    goalsOnlyFinishedFixture({
                        home_team: 'Late UTC FC',
                        away_team: 'Local Today FC',
                        date: '2026-08-22',
                        kickoff_at: '2026-08-22T23:30:00Z',
                    }),
                    goalsOnlyFinishedFixture({
                        home_team: 'Legacy FC',
                        away_team: 'Date Only FC',
                        date: '2026-08-22',
                    }),
                ],
            }],
        },
    });

    assert.strictEqual(app.context.fixtureLocalDateString({
        date: '2026-08-22', status: 'FINISHED', kickoff_at: '2026-08-22T23:30:00Z',
    }), '2026-08-23');
    assert.strictEqual(app.context.fixtureLocalDateString({
        date: '2026-08-22', status: 'FINISHED',
    }), '2026-08-22');
    assert.match(homeToolbar(app.elements).children[0].innerHTML, /1 match/);
    assert.match(homeCard(app.elements).innerHTML, /Late UTC FC/);
    assert.doesNotMatch(homeCard(app.elements).innerHTML, /Legacy FC/);
    assert.deepStrictEqual(app.errors, []);
}

async function testHomeRendersEverySameLeagueFixtureOnTheSelectedDate() {
    const fixtures = Array.from({ length: 13 }, (_, index) => predictionFixture({
        home_team: `MLS Home ${index + 1}`,
        away_team: `MLS Away ${index + 1}`,
        date: '2026-08-16',
        status: 'FINISHED',
        home_goals: index % 4,
        away_goals: (index + 1) % 4,
    }));
    const app = await boot({
        data: { leagues: [{ id: 'mls', name: 'Major League Soccer', metric: 'xg', fixtures }] },
    });
    const section = homeSection(app.elements);

    assert.match(homeToolbar(app.elements).children[0].innerHTML, /13 matches/);
    assert.match(section.children[0].innerHTML, /Major League Soccer/);
    assert.match(section.children[0].innerHTML, />13<\/span>/);
    assert.strictEqual(section.children[1].children.length, 13);
    assert.deepStrictEqual(app.errors, []);
}

async function testEmptyDateOffersPreviousAndNextAvailableDates() {
    const app = await boot({
        data: {
            leagues: [{
                id: 'mls',
                name: 'Major League Soccer',
                metric: 'xg',
                fixtures: [
                    predictionFixture({ home_team: 'Previous Date FC', away_team: 'Away FC', date: '2026-08-15' }),
                    predictionFixture({ home_team: 'Next Date FC', away_team: 'Away FC', date: '2026-08-17' }),
                ],
            }],
        },
    });
    const emptyState = app.elements['fixtures-container'].children[1];

    assert.match(emptyState.innerHTML, /No fixtures on this date/);
    const dateActions = emptyState.children[0];
    assert.strictEqual(dateActions.children.length, 2);
    assert.match(dateActions.children[0].textContent, /Previous available/);
    assert.match(dateActions.children[1].textContent, /Next available/);

    dateActions.children[1].click();
    assert.match(homeToolbar(app.elements).children[0].innerHTML, /1 match/);
    assert.match(homeCard(app.elements).innerHTML, /Next Date FC/);
    assert.deepStrictEqual(app.errors, []);
}

async function testGoalsOnlyFinishedFixtureExplainsMissingXg() {
    const app = await boot({
        data: { leagues: [{ id: 'admiral-bundesliga', name: 'Admiral Bundesliga', metric: 'goals', fixtures: [goalsOnlyFinishedFixture()] }] },
    });
    const card = homeCard(app.elements);

    activateCardControl(card, '.fixture-details-toggle');
    assert.match(card.innerHTML, /FT score/);
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
    const currentTable = renderedLeagueTable(container);
    assert.strictEqual(seasonSelector.children[0].textContent, '2026/27');
    assert.match(currentTable.innerHTML, /\+0\.40 \/ \+0\.40/);
    assert.match(currentTable.innerHTML, /\+0\.95 \/ \+0\.95/);
    assert.match(container.children[2].textContent, /Reconstructed historical prediction/);

    controls.children[1].click();
    const forTable = renderedLeagueTable(elements['fixtures-container']);
    assert.match(forTable.innerHTML, /-0\.10 \/ -0\.10/);
    assert.match(forTable.innerHTML, /\+0\.20 \/ \+0\.20/);

    const refreshedSelector = elements['fixtures-container'].children[1];
    refreshedSelector.children[0].click();
    refreshedSelector.children[1].children[1].click();
    const historicContainer = elements['fixtures-container'];
    const historicTable = renderedLeagueTable(historicContainer);
    assert.strictEqual(historicContainer.children[1].children[0].textContent, '2025/26');
    assert.match(historicTable.innerHTML, /Historic FC/);
    assert.match(historicTable.innerHTML, /—/);
    const unavailableNote = historicContainer.children.find(child => child.className === 'season-unavailable-note');
    assert.match(unavailableNote.textContent, /Prediction accuracy is unavailable/);
    assert.deepStrictEqual(errors, []);
}

async function testLeagueCrestsAndSorting() {
    const app = await boot({
        data: { leagues: [{ id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [predictionFixture()] }] },
        standings: sortableStandingsFixture(),
        badges: {
            badges: {
                premier_league: {
                    'Atlético FC': { badge_url: 'https://example.com/atletico.png' },
                },
            },
        },
    });
    app.elements['league-tab'].click();
    app.elements['fixtures-container'].children[0].children[0].click();

    let container = app.elements['fixtures-container'];
    let tableHtml = renderedLeagueTable(container).innerHTML;
    assert.match(tableHtml, /https:\/\/example\.com\/atletico\.png/);
    assert.match(tableHtml, /Deportivo La Coruna/);
    assert.match(tableHtml, />DC<\/span>/);
    assert.ok(tableHtml.indexOf('Bravo FC') < tableHtml.indexOf('Atletico FC'));

    let sortControls = renderedSortControls(container);
    sortControls.children[1].listeners.change({ target: { value: 'goals' } });
    container = app.elements['fixtures-container'];
    tableHtml = renderedLeagueTable(container).innerHTML;
    assert.ok(tableHtml.indexOf('Atletico FC') < tableHtml.indexOf('Bravo FC'));

    sortControls = renderedSortControls(container);
    sortControls.children[1].listeners.change({ target: { value: 'matches' } });
    container = app.elements['fixtures-container'];
    tableHtml = renderedLeagueTable(container).innerHTML;
    assert.ok(tableHtml.indexOf('Deportivo La Coruna') < tableHtml.indexOf('Bravo FC'));

    sortControls = renderedSortControls(container);
    sortControls.children[2].click();
    container = app.elements['fixtures-container'];
    tableHtml = renderedLeagueTable(container).innerHTML;
    assert.ok(tableHtml.indexOf('Atletico FC') < tableHtml.indexOf('Bravo FC'));

    sortControls = renderedSortControls(container);
    sortControls.children[1].listeners.change({ target: { value: 'name' } });
    container = app.elements['fixtures-container'];
    tableHtml = renderedLeagueTable(container).innerHTML;
    assert.ok(tableHtml.indexOf('Deportivo La Coruna') < tableHtml.indexOf('Bravo FC'));
    assert.deepStrictEqual(app.errors, []);
}

async function testLocalCrestDialogRetainsBrowserOnlyStorage() {
    const app = await boot({
        data: { leagues: [{ id: 'premier_league', name: 'Premier League', metric: 'xg', fixtures: [predictionFixture()] }] },
    });
    const trigger = new Element('button');
    app.context.showLogoDialog('Home FC', trigger);
    assert.strictEqual(app.elements['logo-dialog'].hidden, false);
    assert.strictEqual(app.elements['logo-dialog-team'].textContent, 'Home FC');

    app.elements['logo-url'].value = 'https://example.com/home-fc.png';
    app.elements['logo-form'].listeners.submit({ preventDefault() {} });
    assert.match(app.storage.getItem('team_logos'), /home-fc\.png/);
    assert.strictEqual(app.elements['logo-dialog'].hidden, true);

    app.context.showLogoDialog('Home FC', trigger);
    app.elements['logo-url'].value = 'not a URL';
    app.elements['logo-form'].listeners.submit({ preventDefault() {} });
    assert.strictEqual(app.elements['logo-dialog-error'].hidden, false);
    assert.match(app.elements['logo-dialog-error'].textContent, /valid http or https/);
    assert.deepStrictEqual(app.errors, []);
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
    assert.match(cardHtml, /data-team="Away FC"[^>]*>AF<\/button>/);
    assert.strictEqual(app.elements['badge-attribution'].textContent, 'Team badges: TheSportsDB');
    assert.deepStrictEqual(app.errors, []);
}

async function testEmptyArtifactAndDataLoadError() {
    const empty = await boot({ data: { leagues: [] } });
    assert.match(empty.elements['fixtures-container'].innerHTML, /No leagues found/);
    assert.deepStrictEqual(empty.errors, []);

    const failed = await boot({ data: {}, dataOk: false });
    assert.match(failed.elements['fixtures-container'].innerHTML, /Fixture data could not load/);
    assert.strictEqual(failed.errors.length, 1);
    assert.match(failed.errors[0], /Failed to fetch data/);
}

(async () => {
    await testHomeSearchDetailsAndFavorites();
    await testUnavailableUpcomingFixtureStillRendersManualEditor();
    await testXgOnlyForecastStaysAvailableOnHome();
    await testFixtureIntelligenceFiltersAvailabilityAndFreshness();
    await testCompletedTimestampUsesViewerLocalDateWithDateOnlyFallback();
    await testHomeRendersEverySameLeagueFixtureOnTheSelectedDate();
    await testEmptyDateOffersPreviousAndNextAvailableDates();
    await testGoalsOnlyFinishedFixtureExplainsMissingXg();
    await testLeagueSeasonNavigationAndPaModes();
    await testLeagueCrestsAndSorting();
    await testLocalCrestDialogRetainsBrowserOnlyStorage();
    await testBadgeManifestAttributionAndFallback();
    await testEmptyArtifactAndDataLoadError();
    console.log('Frontend behavior tests passed.');
})().catch(error => {
    console.error(error);
    process.exit(1);
});
