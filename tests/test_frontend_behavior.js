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
        if (this.listeners.click) {
            this.listeners.click({ target: this });
        }
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
    return {
        ok,
        json: async () => payload,
    };
}

async function boot({ data, dataOk = true, badges = { badges: {} }, badgesOk = true, version = 'test-version', initialStorage = {} }) {
    const elements = {
        'fixtures-container': new Element('main'),
        'version-tag': new Element('p'),
        'date-strip': new Element('div'),
        'theme-toggle': new Element('button'),
        'badge-attribution': new Element('p'),
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
            if (eventName === 'DOMContentLoaded') {
                readyHandler = listener;
            }
        },
    };

    const context = {
        Date: FakeDate,
        console: {
            error(error) {
                errors.push(String(error));
            },
        },
        document,
        fetch: async (url) => {
            if (url === 'data.json') {
                return response(dataOk, data);
            }
            if (url === 'team_badges.json') {
                return response(badgesOk, badges);
            }
            if (url === 'version.json') {
                return response(true, { version });
            }
            throw new Error(`Unexpected fetch: ${url}`);
        },
        localStorage: storage,
        prompt: () => null,
        setImmediate,
    };

    vm.runInNewContext(scriptSource, context, { filename: scriptPath });
    readyHandler();
    for (let i = 0; i < 6; i++) {
        await new Promise(resolve => setImmediate(resolve));
    }

    return { document, elements, storage, errors };
}

function predictionFixture() {
    return {
        home_team: 'Home FC',
        away_team: 'Away FC',
        date: '2026-08-16',
        home_expected_goals: 1.5,
        away_expected_goals: 1.0,
        combined_expected_goals: 2.5,
        home_last_4_matches: [{ opponent: 'H1', goals_for: 2, goals_against: 1 }],
        away_last_4_matches: [{ opponent: 'A1', goals_for: 1, goals_against: 2 }],
    };
}

function finishedFixture() {
    return {
        home_team: 'Past Home',
        away_team: 'Past Away',
        date: '2026-08-16',
        status: 'FINISHED',
        home_goals: 2,
        away_goals: 1,
        home_xg: 1.8,
        away_xg: 0.9,
        home_expected_xg: 1.4,
        away_expected_xg: 1.1,
        home_expected_goals: 1.5,
        away_expected_goals: 1.0,
    };
}

async function testPopulatedMetricFinishedNavigationAndTheme() {
    const app = await boot({
        data: {
            leagues: [
                {
                    id: 'test-league',
                    name: 'Test League',
                    metric: 'goals',
                    fixtures: [predictionFixture(), finishedFixture()],
                },
            ],
        },
    });
    const { document, elements, storage, errors } = app;

    assert.strictEqual(elements['version-tag'].textContent, 'vtest-version');
    assert.strictEqual(elements['date-strip'].children.length, 7);
    assert.strictEqual(elements['date-strip'].children[3].classList.contains('active'), true);
    assert.strictEqual(elements['fixtures-container'].children.length, 1);
    const leagueBody = elements['fixtures-container'].children[0].children[1];
    assert.strictEqual(leagueBody.children.length, 2);
    assert.match(leagueBody.children[0].innerHTML, /Goals Combined/);
    assert.match(leagueBody.children[0].innerHTML, /1\.50 - 1\.00/);
    assert.match(leagueBody.children[1].innerHTML, /FT Score/);
    assert.match(leagueBody.children[1].innerHTML, /Pred Goals: 1\.50 - 1\.00 \| Pred xG: 1\.40 - 1\.10/);

    elements['date-strip'].children[4].click();
    assert.match(elements['fixtures-container'].innerHTML, /No fixtures on this date/);
    assert.strictEqual(elements['date-strip'].children[4].classList.contains('active'), true);

    assert.strictEqual(document.documentElement.getAttribute('data-theme'), 'light');
    elements['theme-toggle'].click();
    assert.strictEqual(document.documentElement.getAttribute('data-theme'), 'dark');
    assert.strictEqual(storage.getItem('theme'), 'dark');
    assert.deepStrictEqual(errors, []);
}

async function testStaticBadgeManifestAttributionAndFallback() {
    const app = await boot({
        data: {
            leagues: [{
                id: 'premier_league',
                name: 'Premier League',
                metric: 'xg',
                fixtures: [predictionFixture()],
            }],
        },
        badges: {
            source: {
                name: 'TheSportsDB',
                url: 'https://www.thesportsdb.com/',
                attribution: 'Team badges: TheSportsDB',
            },
            badges: {
                premier_league: {
                    'Home FC': {
                        badge_url: 'https://r2.thesportsdb.com/images/home-fc.png',
                        source_url: 'https://www.thesportsdb.com/team/home-fc',
                    },
                },
            },
        },
    });
    const { elements, errors } = app;
    const cardHtml = elements['fixtures-container'].children[0].children[1].children[0].innerHTML;

    assert.match(cardHtml, /https:\/\/r2\.thesportsdb\.com\/images\/home-fc\.png/);
    assert.match(cardHtml, /alt="Home FC badge"/);
    assert.match(cardHtml, /data-team="Away FC"[^>]*>AF<\/div>/);
    assert.strictEqual(elements['badge-attribution'].textContent, 'Team badges: TheSportsDB');
    assert.deepStrictEqual(errors, []);
}

async function testUnavailableBadgeManifestFallsBackToInitials() {
    const app = await boot({
        data: {
            leagues: [{
                id: 'premier_league',
                name: 'Premier League',
                metric: 'xg',
                fixtures: [predictionFixture()],
            }],
        },
        badgesOk: false,
    });
    const { elements, errors } = app;
    const cardHtml = elements['fixtures-container'].children[0].children[1].children[0].innerHTML;

    assert.match(cardHtml, /data-team="Home FC"[^>]*>HF<\/div>/);
    assert.match(cardHtml, /data-team="Away FC"[^>]*>AF<\/div>/);
    assert.strictEqual(elements['badge-attribution'].textContent, '');
    assert.deepStrictEqual(errors, []);
}

async function testCollapsedLeagueSectionsFlagsAndPersistence() {
    const activeLeagues = [
        ['premier_league', 'Premier League'], ['la_liga', 'La Liga'], ['serie_a', 'Serie A'],
        ['bundesliga', 'Bundesliga'], ['ligue_1', 'Ligue 1'], ['superliga-argentina', 'Superliga'],
        ['admiral-bundesliga', 'Admiral Bundesliga'], ['pro-league-belgium', 'Pro League'],
        ['serie-a-brazil', 'Serie A Brazil'], ['superliga-denmark', 'Superliga Denmark'],
        ['league-one', 'League One'], ['2-bundesliga', '2. Bundesliga'],
        ['copa-libertadores', 'Copa Libertadores'], ['j-league', 'J-League'], ['liga-mx', 'Liga MX'],
        ['eredivisie', 'Eredivisie'], ['eerste-divisie', 'Eerste Divisie'], ['eliteserien', 'Eliteserien'],
        ['liga-portugal', 'Liga Portugal'], ['pro-league-saudi', 'Pro League Saudi'],
        ['premiership', 'Premiership'], ['allsvenskan', 'Allsvenskan'], ['super-lig', 'Super Lig'],
        ['mls', 'Major League Soccer'], ['veikkausliiga', 'Veikkausliiga'],
    ];
    const app = await boot({
        data: {
            leagues: activeLeagues.map(([id, name]) => ({
                id,
                name,
                metric: 'xg',
                fixtures: [predictionFixture()],
            })),
        },
    });
    const { elements, storage, errors } = app;
    const sections = elements['fixtures-container'].children;
    assert.strictEqual(sections.length, activeLeagues.length);

    sections.forEach((section, index) => {
        const header = section.children[0];
        const body = section.children[1];
        assert.strictEqual(section.className, 'league-section');
        assert.strictEqual(header.tagName, 'button');
        assert.strictEqual(header.getAttribute('aria-expanded'), 'false');
        assert.strictEqual(body.classList.contains('hidden'), true);
        const flagPath = header.innerHTML.match(/assets\/flags\/([a-z-]+\.svg)/)[1];
        assert.strictEqual(fs.existsSync(path.join(__dirname, '..', 'public', 'assets', 'flags', flagPath)), true);
        assert.doesNotMatch(header.innerHTML, /[\u{1F1E6}-\u{1F1FF}]/u);
        assert.match(header.innerHTML, /flag/);
        assert.match(header.innerHTML, new RegExp(activeLeagues[index][1]));
    });

    const firstHeader = sections[0].children[0];
    const firstBody = sections[0].children[1];
    firstHeader.click();
    assert.strictEqual(firstHeader.getAttribute('aria-expanded'), 'true');
    assert.strictEqual(firstBody.classList.contains('hidden'), false);
    assert.strictEqual(storage.getItem('league_expansion:2026-08-16:premier_league'), 'open');

    const restoredApp = await boot({
        data: {
            leagues: activeLeagues.map(([id, name]) => ({
                id,
                name,
                metric: 'xg',
                fixtures: [predictionFixture()],
            })),
        },
        initialStorage: { 'league_expansion:2026-08-16:premier_league': 'open' },
    });
    const restoredSection = restoredApp.elements['fixtures-container'].children[0];
    assert.strictEqual(restoredSection.children[0].getAttribute('aria-expanded'), 'true');
    assert.strictEqual(restoredSection.children[1].classList.contains('hidden'), false);
    assert.deepStrictEqual(errors, []);
}

async function testEmptyArtifact() {
    const { elements, errors } = await boot({ data: { leagues: [] } });
    assert.match(elements['fixtures-container'].innerHTML, /No leagues found/);
    assert.deepStrictEqual(errors, []);
}

async function testDataLoadError() {
    const { elements, errors } = await boot({ data: {}, dataOk: false });
    assert.match(elements['fixtures-container'].innerHTML, /Error loading fixtures/);
    assert.strictEqual(errors.length, 1);
    assert.match(errors[0], /Failed to fetch data/);
}

(async () => {
    await testPopulatedMetricFinishedNavigationAndTheme();
    await testStaticBadgeManifestAttributionAndFallback();
    await testUnavailableBadgeManifestFallsBackToInitials();
    await testCollapsedLeagueSectionsFlagsAndPersistence();
    await testEmptyArtifact();
    await testDataLoadError();
    console.log('Frontend behavior tests passed.');
})().catch(error => {
    console.error(error);
    process.exit(1);
});
