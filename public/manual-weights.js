(() => {
    const TOTAL_BASIS_POINTS = 10000;
    const STORAGE_PREFIX = 'opm:manual-fixture-weights:v1:';

    function fixtureKey(fixture) {
        return [
            fixture.leagueId,
            fixture.home_team,
            fixture.away_team,
            String(fixture.date || '').slice(0, 10),
        ].map(value => encodeURIComponent(String(value || ''))).join('|');
    }

    function historyKey(match) {
        return [match.opponent, String(match.date || '').slice(0, 10), match.venue].join('|');
    }

    function historySignature(matches) {
        return matches.map(historyKey).join('||');
    }

    function historyKeys(fixture) {
        const homeKey = Object.keys(fixture).find(key => key.startsWith('home_last_') && key.endsWith('_matches'));
        const awayKey = Object.keys(fixture).find(key => key.startsWith('away_last_') && key.endsWith('_matches'));
        return {
            home: homeKey,
            away: awayKey,
            homeMatches: fixture[homeKey] || [],
            awayMatches: fixture[awayKey] || [],
        };
    }

    function evenlyDistributedWeights(length) {
        if (!length) return [];
        const base = Math.floor(TOTAL_BASIS_POINTS / length);
        let remainder = TOTAL_BASIS_POINTS % length;
        return Array.from({ length }, () => {
            const value = base + (remainder > 0 ? 1 : 0);
            remainder = Math.max(0, remainder - 1);
            return value;
        });
    }

    function validWeights(weights, length) {
        return Array.isArray(weights)
            && weights.length === length
            && weights.every(Number.isInteger)
            && weights.every(weight => weight >= 0 && weight <= TOTAL_BASIS_POINTS)
            && weights.reduce((total, weight) => total + weight, 0) === TOTAL_BASIS_POINTS;
    }

    function readFixtureStorage(fixture) {
        const histories = historyKeys(fixture);
        try {
            const stored = JSON.parse(localStorage.getItem(STORAGE_PREFIX + fixtureKey(fixture)) || 'null');
            if (!stored || stored.version !== 1) return null;
            if (stored.home_history !== historySignature(histories.homeMatches)) return null;
            if (stored.away_history !== historySignature(histories.awayMatches)) return null;
            if (!validWeights(stored.home_weights, histories.homeMatches.length)) return null;
            if (!validWeights(stored.away_weights, histories.awayMatches.length)) return null;
            return stored;
        } catch (_) {
            return null;
        }
    }

    function writeFixtureStorage(fixture, values) {
        const histories = historyKeys(fixture);
        const record = {
            version: 1,
            saved_at: new Date().toISOString(),
            home_history: historySignature(histories.homeMatches),
            away_history: historySignature(histories.awayMatches),
            home_weights: values.homeWeights,
            away_weights: values.awayWeights,
            home_pinned: values.homePinned,
            away_pinned: values.awayPinned,
        };
        localStorage.setItem(STORAGE_PREFIX + fixtureKey(fixture), JSON.stringify(record));
    }

    function selectedRows(matches, weights, pinned) {
        const resolvedWeights = validWeights(weights, matches.length)
            ? weights
            : evenlyDistributedWeights(matches.length);
        return matches.map((match, index) => ({
            match,
            weight_bps: resolvedWeights[index],
            pinned: Array.isArray(pinned) && pinned[index] === true,
        }));
    }

    function average(rows, field) {
        return rows.reduce((total, row) => total + (Number(row.match[field]) * row.weight_bps), 0) / TOTAL_BASIS_POINTS;
    }

    function metricExpectation(homeRows, awayRows, metric) {
        const fields = metric === 'xg' ? ['xg_for', 'xg_against'] : ['goals_for', 'goals_against'];
        const rows = [...homeRows, ...awayRows];
        if (!rows.every(row => fields.every(field => Number.isFinite(Number(row.match[field]))))) return null;
        const homeFor = average(homeRows, fields[0]);
        const homeAgainst = average(homeRows, fields[1]);
        const awayFor = average(awayRows, fields[0]);
        const awayAgainst = average(awayRows, fields[1]);
        return {
            home_expected: (homeFor + awayAgainst) / 2,
            away_expected: (awayFor + homeAgainst) / 2,
            combined_expected: (homeFor + awayAgainst + awayFor + homeAgainst) / 2,
        };
    }

    function previewForWeights(fixture, homeWeights, awayWeights, homePinned = [], awayPinned = []) {
        const histories = historyKeys(fixture);
        const homeRows = selectedRows(histories.homeMatches, homeWeights, homePinned);
        const awayRows = selectedRows(histories.awayMatches, awayWeights, awayPinned);
        const xg = metricExpectation(homeRows, awayRows, 'xg');
        const goals = metricExpectation(homeRows, awayRows, 'goals');
        return {
            home_expected_xg: xg.home_expected,
            away_expected_xg: xg.away_expected,
            combined_expected_xg: xg.combined_expected,
            home_expected_goals: goals ? goals.home_expected : null,
            away_expected_goals: goals ? goals.away_expected : null,
            combined_expected_goals: goals ? goals.combined_expected : null,
            homeRows,
            awayRows,
        };
    }

    function fixturePreview(fixture, stored = readFixtureStorage(fixture)) {
        return previewForWeights(
            fixture,
            stored && stored.home_weights,
            stored && stored.away_weights,
            stored && stored.home_pinned,
            stored && stored.away_pinned,
        );
    }

    function displayPrediction(fixture) {
        if (fixture.status === 'FINISHED') return null;
        const stored = readFixtureStorage(fixture);
        if (!stored) return null;
        return fixturePreview(fixture, stored);
    }

    function percentage(value) {
        return (value / 100).toFixed(2);
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
    }

    function editorRows(team, side, rows) {
        return rows.map((row, index) => `
            <label class="manual-weight-row">
                <span>${escapeHtml(row.match.date)} · ${escapeHtml(row.match.venue)} · ${escapeHtml(row.match.opponent)}</span>
                <input class="manual-weight-input" type="number" min="0" max="100" step="0.01" value="${percentage(row.weight_bps)}" data-manual-side="${side}" data-manual-index="${index}" data-manual-pinned="${row.pinned ? 'true' : 'false'}" aria-label="Manual percentage for ${escapeHtml(team)} versus ${escapeHtml(row.match.opponent)}">
                <small>${row.pinned ? 'Pinned for this fixture' : 'Shares this fixture’s remainder'}</small>
            </label>
        `).join('');
    }

    function fixtureEditorHtml(fixture) {
        if (fixture.status === 'FINISHED') return '';
        try {
            const preview = fixturePreview(fixture);
            return `
                <section class="manual-weights-panel" aria-label="Manual match weights">
                    <div class="manual-weights-heading"><div><p class="eyebrow">Private Safari adjustment</p><h3>Manual match weights</h3></div><span class="manual-preview-value">Manual xG: ${preview.home_expected_xg.toFixed(2)} – ${preview.away_expected_xg.toFixed(2)}${preview.home_expected_goals === null ? '' : `<br>Goals: ${preview.home_expected_goals.toFixed(2)} – ${preview.away_expected_goals.toFixed(2)}`}</span></div>
                    <p class="manual-weights-copy">This adjustment applies only to this fixture and is saved privately in Safari. Future fixtures start at equal weights.</p>
                    <div class="manual-weights-columns">
                        <div><strong>${escapeHtml(fixture.home_team)}</strong>${editorRows(fixture.home_team, 'home', preview.homeRows)}</div>
                        <div><strong>${escapeHtml(fixture.away_team)}</strong>${editorRows(fixture.away_team, 'away', preview.awayRows)}</div>
                    </div>
                    <p class="manual-weights-error" hidden role="alert"></p>
                    <div class="manual-weights-actions"><button class="secondary-button manual-weights-reset" type="button">Reset to 25%</button><button class="primary-button manual-weights-save" type="button">Save in Safari</button></div>
                </section>
            `;
        } catch (error) {
            return `<section class="manual-weights-panel"><p class="manual-weights-error">${escapeHtml(error.message)}</p></section>`;
        }
    }

    function inputsForSide(root, side) {
        return Array.from(root.querySelectorAll(`.manual-weight-input[data-manual-side="${side}"]`));
    }

    function setError(root, message) {
        const target = root.querySelector('.manual-weights-error');
        if (!target) return;
        target.textContent = message;
        target.hidden = !message;
    }

    function previewSummaryHtml(preview) {
        const goals = preview.home_expected_goals === null
            ? ''
            : `<br>Goals: ${preview.home_expected_goals.toFixed(2)} – ${preview.away_expected_goals.toFixed(2)}`;
        return `Manual xG: ${preview.home_expected_xg.toFixed(2)} – ${preview.away_expected_xg.toFixed(2)}${goals}`;
    }

    function updateEditorPreview(root, fixture) {
        const home = valuesFromEditor(root, 'home');
        const away = valuesFromEditor(root, 'away');
        const preview = previewForWeights(fixture, home.weights, away.weights, home.pinned, away.pinned);
        const target = root.querySelector('.manual-preview-value');
        if (target) target.innerHTML = previewSummaryHtml(preview);
    }

    function redistribute(sideInputs, changedInput) {
        changedInput.dataset.manualPinned = 'true';
        const pinned = sideInputs.filter(input => input.dataset.manualPinned === 'true');
        const pinnedTotal = pinned.reduce((total, input) => total + Math.round(Number(input.value) * 100), 0);
        if (!Number.isFinite(pinnedTotal) || pinnedTotal > TOTAL_BASIS_POINTS) {
            throw new Error('Pinned percentages cannot exceed 100.00%.');
        }
        const unpinned = sideInputs.filter(input => input.dataset.manualPinned !== 'true');
        if (!unpinned.length) {
            if (pinnedTotal !== TOTAL_BASIS_POINTS) throw new Error('All pinned rows must total 100.00%.');
            return;
        }
        const remaining = TOTAL_BASIS_POINTS - pinnedTotal;
        const base = Math.floor(remaining / unpinned.length);
        let remainder = remaining % unpinned.length;
        unpinned.forEach(input => {
            const weight = base + (remainder > 0 ? 1 : 0);
            remainder = Math.max(0, remainder - 1);
            input.value = percentage(weight);
        });
    }

    function valuesFromEditor(root, side) {
        const inputs = inputsForSide(root, side);
        const weights = inputs.map(input => {
            const percentageValue = Number(input.value);
            if (!Number.isFinite(percentageValue) || percentageValue < 0 || percentageValue > 100) {
                throw new Error('Each percentage must be between 0.00 and 100.00.');
            }
            return Math.round(percentageValue * 100);
        });
        if (!validWeights(weights, inputs.length)) throw new Error('Each team’s weights must total exactly 100.00%.');
        return {
            weights,
            pinned: inputs.map(input => input.dataset.manualPinned === 'true'),
        };
    }

    function bindEditor(card, fixture, render) {
        const root = card.querySelector('.manual-weights-panel');
        if (!root || root.dataset.manualBound === 'true') return;
        root.dataset.manualBound = 'true';
        root.addEventListener('input', event => {
            const input = event.target;
            if (!input || !input.classList.contains('manual-weight-input')) return;
            try {
                redistribute(inputsForSide(root, input.dataset.manualSide), input);
                updateEditorPreview(root, fixture);
                setError(root, '');
            } catch (error) {
                setError(root, error.message || 'Invalid percentage.');
            }
        });
        root.addEventListener('click', event => {
            const target = event.target && typeof event.target.closest === 'function'
                ? event.target.closest('.manual-weights-save, .manual-weights-reset')
                : null;
            if (!target) return;
            if (typeof event.preventDefault === 'function') event.preventDefault();
            try {
                if (target.classList.contains('manual-weights-reset')) {
                    localStorage.removeItem(STORAGE_PREFIX + fixtureKey(fixture));
                    render();
                    return;
                }
                const home = valuesFromEditor(root, 'home');
                const away = valuesFromEditor(root, 'away');
                writeFixtureStorage(fixture, {
                    homeWeights: home.weights,
                    awayWeights: away.weights,
                    homePinned: home.pinned,
                    awayPinned: away.pinned,
                });
                render();
            } catch (error) {
                setError(root, error.message || 'Safari could not save this adjustment.');
            }
        });
    }

    window.OPMManualWeights = {
        fixtureEditorHtml,
        bindEditor,
        fixtureKey,
        readFixtureStorage,
        writeFixtureStorage,
        selectedRows,
        fixturePreview,
        previewForWeights,
        displayPrediction,
        evenlyDistributedWeights,
    };
})();
