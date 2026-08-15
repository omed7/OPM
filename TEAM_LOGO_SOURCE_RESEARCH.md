# Team Logo Source Research

**Date:** 2026-08-15
**Author:** Manus AI
**Status:** Recommendation only — no provider, API key, public asset, workflow, deployment, or data contract has been changed.

> **Working legal analysis, not formal legal advice.** Club crests can involve trademark and other third-party rights. A qualified lawyer should review any decision that is consequential for the public service.

## Decision context

OPM currently renders a deterministic initials badge and allows an individual visitor to enter an arbitrary image URL into browser-local storage. It has **no automated, reviewed, or provenance-controlled team-logo source**. The requested next phase is to show club badges without changing `public/data.json`, adding a new production data provider silently, or assuming that an image API grants trademark rights.

The preferred delivery model is a **separate, provider-attributed badge manifest** keyed by `league_id` and reviewed provider-team ID. The frontend should retain its initials badge as a fail-closed fallback whenever the mapping, asset, or provider image is unavailable. This preserves the existing fixture artifact contract while avoiding ambiguous name-only matching across leagues.

## Provider findings

| Option | Published rights position | Technical fit | Coverage / operating model | Assessment |
|---|---|---|---|---|
| **TheSportsDB paid API** | Its terms say paid users may use its custom artwork in projects with source attribution, require trademarked logos to remain unmodified, and state that third-party content needs owner permission or another legal basis. [1] | The team-list response supplies a per-team `strBadge` URL; the documentation defines a 512×512 team-badge asset. [2] [3] | Paid tiers advertise full premium JSON and higher limits; exact coverage of OPM’s 25 supported leagues must be tested before adoption. [4] | **Preferred candidate, but only after written confirmation from TheSportsDB covering public OPM display of team badges and required attribution.** |
| **API-Football / API-Sports** | It provides logos for identification, but explicitly says it does **not** grant a licence to publish supplied data or images and places authorisation responsibility on the user. [5] | It documents a team-logo URL and team IDs. [6] | Technically straightforward; sourcing could be mapped by provider team ID. | **Reject as an unauthorised default.** Its published terms are not sufficient for OPM’s public logo display. |
| **Sportmonks** | Its documentation exposes an `image_path` for team records. [7] The public material reviewed did not establish that the standard API subscription grants OPM rights to display and cache club marks. | Strong technical fit, including stable provider team IDs and image URLs. [7] | Published FAQ material describes paid plans and broader competition coverage, but that does not answer the crest-rights question. [8] | **Only consider after receiving written commercial confirmation that expressly covers public team-logo display for OPM’s chosen competitions.** |
| **Live Score API** | Its terms describe logos as non-commercial, informative use only, say they are share-alike, and also state that teams retain rights and additional use requires explicit permission. [9] | Provider supplies team data, but the reviewed documentation does not establish a better mapping or coverage advantage for OPM. | Requires a subscription after a trial. [9] | **Do not use as the permanent source.** The non-commercial limitation and rights language are too restrictive/ambiguous for a durable public site. |
| **Direct club sites, search results, or random GitHub logo packs** | No common licence, provenance, update process, or club-by-club approval exists. | Fast to prototype but fragile and difficult to audit. | Would require manual curation across every active club and season. | **Reject.** Do not scrape, hotlink, or vendor these assets without documented rights. |
| **Existing browser-local custom URLs** | The site cannot verify provenance or permissions for an arbitrary visitor-provided URL. | Already implemented, but it is per-browser and not public coverage. | No catalogue, review, update, or failure policy. | **Keep only as an optional private override, or remove it in the implementation PR; it is not a product logo source.** |

## Recommendation

OPM should use **TheSportsDB as the candidate for a controlled badge manifest only if the provider confirms in writing that its paid plan permits OPM to display the returned `strBadge` images on its public website for the selected leagues, and specifies the required attribution and whether remote delivery or caching is permitted**. The provider’s published terms are more directly useful than the alternatives reviewed: they allow paid-project artwork use, require attribution, and explain the treatment of trademarked logos. They still leave third-party-rights responsibility with the user, so the written confirmation is the essential gate. [1]

Until that confirmation is obtained, the safe product decision is to retain initials badges. OPM should **not** adopt API-Football merely because its endpoint exposes an image URL; its own terms say no publication licence is granted. [5] It should also not create a repository of copied club crests, because doing so would add redistribution risk and an ongoing asset-maintenance burden.

## Proposed implementation, after approval

| Component | Proposed behaviour | Contract / risk control |
|---|---|---|
| Provider configuration | Store the paid provider credential only in an approved secret store; use a bounded build-time synchronisation path, not client-side API credentials. | Requires separate approval for an external API, secret, and scheduled update path. |
| Source manifest | Generate `public/team_badges.json`, mapping `(league_id, normalised_team_name)` to provider team ID and remote `badge_url`, with `updated_at` and source metadata. | Leaves `public/data.json` unchanged; provider ID prevents ambiguous name-only matching. |
| Asset delivery | Render remote badge URLs from the approved provider CDN. Do **not** vendor or re-host crests unless the written provider response explicitly permits it. | Avoids unauthorised redistribution and keeps image updates with the provider. |
| Frontend fallback | Load the badge manifest alongside fixture data. If a mapping is absent, URL fails, or the image cannot load, show the existing generated initials badge. | No blank/broken team badge and no fixture-rendering failure. |
| Attribution | Add the exact provider credit/link required by the written confirmation. | Meets provider terms; no implied club sponsorship or endorsement. |
| Matching and review | Build a league-scoped mapping report for every active fixture team, resolve aliases manually, and fail closed for uncertain matches. | Prevents wrong-club badges, particularly for generic club names. |
| Tests | Add deterministic tests for mapping success, missing badges, duplicate team names across leagues, image failures, and manifest/schema validation. | Verifies the public seam independently of a live provider. |

## Approval gate

Before implementation, the following decisions are needed:

1. **Authorise provider outreach/subscription:** approve contacting TheSportsDB and, if satisfactory, obtaining a paid API key. The written confirmation should specifically cover public OPM display, the selected competitions, attribution text, and remote versus cached delivery.
2. **Choose the asset policy:** approve **remote provider-hosted URLs only** unless the provider expressly authorises local caching/re-hosting.
3. **Approve the technical scope:** a separate manifest, build-time provider synchronisation, frontend fallback, and removal or restriction of the current arbitrary-URL prompt are recommended. This preserves `public/data.json` but introduces a new external API, secret, and scheduled data dependency.
4. **Approve the final commercial interpretation:** if OPM will carry advertising, paid access, sponsorship, or other commercial use, obtain a legal review and explicit provider confirmation before publishing logos.

## References

[1]: https://www.thesportsdb.com/docs_terms_of_use.php "TheSportsDB Terms of Service"
[2]: https://www.thesportsdb.com/docs_api_guide "TheSportsDB API Documentation"
[3]: https://www.thesportsdb.com/docs_artwork "TheSportsDB Artwork Types"
[4]: https://www.thesportsdb.com/pricing "TheSportsDB Pricing"
[5]: https://www.api-football.com/terms "API-Football Terms of Use"
[6]: https://www.api-football.com/documentation-v3 "API-Football Documentation"
[7]: https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/teams-players-coaches-and-referees/teams "Sportmonks Football API: Teams"
[8]: https://www.sportmonks.com/faq/ "Sportmonks FAQ and Pricing Information"
[9]: https://live-score-api.com/index/terms "Live Score API Terms and Conditions"
