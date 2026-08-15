# Team Logo Source Research

**Date:** 2026-08-15
**Author:** Manus AI
**Status:** Recommendation only — no provider, API key, public asset, workflow, deployment, or data contract has been changed.

> **Working legal analysis, not formal legal advice.** Club crests can involve trademark and other third-party rights. A qualified lawyer should review any decision that is consequential for the public service.

## Decision context

OPM renders deterministic initials badges and allows an individual visitor to enter an arbitrary image URL into browser-local storage. It has no automated, reviewed, or provenance-controlled team-logo source. The requested phase is to show club badges without changing `public/data.json`, adding a production data provider silently, or treating access to an image URL as a trademark licence.

A durable implementation needs a league-scoped, reviewed mapping from the fixture team to a specific asset record. The frontend must retain its initials badge as a fail-closed fallback whenever a mapping, image, or licence assertion is absent. This preserves the public fixture-data contract and prevents an ambiguous name from receiving the wrong club badge.

## Commercial and community-source comparison

| Option | Rights and provenance position | Technical and coverage fit | Assessment for OPM |
|---|---|---|---|
| **TheSportsDB paid API** | Its terms permit paid users to use its custom artwork with source attribution, require trademarked logos to remain unmodified, and require users to have an appropriate basis for third-party content. [1] | It exposes a `strBadge` URL per team and documents a 512×512 team-badge asset. [2] [3] Exact OPM-league coverage must be tested. | **Preferred managed candidate, conditional on written confirmation** of public display rights, attribution, selected-competition coverage, and remote-versus-cached delivery. |
| **API-Football / API-Sports** | It says that logos are for identification, but explicitly does not grant a licence to publish supplied data or visual assets. [5] | It documents team identifiers and a logo URL. [6] | **Reject as a default source.** Technical availability is not a sufficient public-use right. |
| **Sportmonks** | Its team records expose `image_path`, but the published material reviewed does not establish that a standard subscription grants public display and caching rights for club crests. [7] | Strong team-ID and image-path model; paid coverage is broad. [7] [8] | **Consider only with a written commercial confirmation** that expressly covers OPM’s public display use. |
| **Live Score API** | Its terms limit crest use to non-commercial, informative contexts, use inconsistent share-alike/reserved-rights language, and say further use requires permission from the respective team. [9] | Provides team data, but no material coverage or rights advantage was identified. | **Reject for the durable public product.** |
| **Leo4815162342/football-logos** | A large community collection advertising more than 4,000 SVG/PNG logos, but its repository metadata reports no licence and the repository does not state the origin or reuse terms of its club marks. [10] | Recent activity and broad apparent coverage. | **Discovery-only; do not use, hotlink, or vendor the assets.** |
| **FCLOGO/fclogo.top** | The archived project carries an MIT licence for its website repository and describes community SVG/PNG logos. Neither the repository nor the code licence establishes a sublicense for third-party club crests. [11] | 747 commits and a contributor workflow, but GitHub marks it archived and its named successor returned 404 during review. [11] [12] | **Reject as a production source.** A code licence cannot be assumed to license team marks. |
| **luukhopman/football-logos** | The season-organised PNG collection has no licence file and is explicitly tagged `scraped`. [13] | Recent July 2026 activity; covers top 25 European leagues only, not OPM’s full international set. [13] | **Discovery-only; do not use, hotlink, or vendor the assets.** |
| **Wikimedia Commons plus Wikidata** | Commons requires a clear per-file free copyright licence and source information, but warns that reusers remain responsible for complying with licences and other restrictions such as trademarks. [14] Wikidata’s P154 is a Commons-media-file link, not a guarantee that a specific team’s asset is complete, current, or reference-backed. [15] | Community-maintained and auditable one file at a time. A representative LAFC crest has a public-domain copyright conclusion while retaining a separate trademark notice. [16] | **Viable only as a curated partial supplement.** It cannot promise every OPM team and requires an individual review record for every asset. |
| **Direct club sites, search results, or arbitrary visitor URLs** | No common licence, provenance record, or auditable update process exists. | Fast to prototype but fragile and impossible to cover safely at product scale. | **Reject as an automated source.** Retain the current initials badge as fallback. |

## Open-source conclusion

No reviewed GitHub badge collection is a safe source for OPM’s public team logos. An MIT, GPL, or similar licence attached to a software repository generally governs the contributor’s repository content; it is not evidence that the contributor owns or can sublicense the underlying club trademarks and crest artwork. The two most technically useful collections reviewed either lack an asset licence or identify the artwork as scraped. FCLOGO adds an MIT code licence but is archived and still does not state a separate rights grant for individual club marks. [10] [11] [13]

Wikimedia Commons is the strongest community-driven alternative because each approved file has a description page with a licence, source, and author record. However, that makes it a **per-file curation workflow**, not a complete badge feed. The safe open-source policy would permit only a file that has been individually reviewed for a public-domain or compatible free copyright status, contains required attribution in a manifest, and has its trademark note recorded. A missing or uncertain file must fall back to initials. Commons cannot meet the product requirement that every current and future team always has a logo without accepted gaps or a separate licensed source. [14] [16]

## Recommendation

OPM should keep its current initials fallback and choose one of two deliberate paths. The first and recommended path is a managed source such as TheSportsDB, but only after the provider confirms in writing that its paid plan permits OPM’s public display of the returned badge images for the selected competitions, specifies required attribution, and confirms whether remote delivery and caching are allowed. [1]

The second path is a **Wikimedia Commons curated subset**. It would publish a separate manifest only for team crests whose individual Commons file pages have been reviewed and logged. It should never claim universal coverage, should keep provider-origin and licence metadata, and should show initials wherever a badge cannot be established confidently. This is licensing-safer than community logo packs, but it is not a complete solution to the user requirement for every team to have a crest.

## Proposed implementation, after approval

| Component | Proposed behaviour | Contract and risk control |
|---|---|---|
| Source manifest | Add `public/team_badges.json`, mapping `(league_id, normalised_team_name)` to a reviewed source record, exact remote `badge_url`, required attribution, licence/source URL, and `updated_at`. | Leaves `public/data.json` unchanged and prevents ambiguous name-only matches. |
| Managed-source delivery | Use the provider’s remote image URL only when its written terms permit it; do not vendor or re-host crests without explicit permission. | Avoids unauthorised redistribution and keeps provider updates current. |
| Commons delivery | Include only individually reviewed Commons files with a compatible copyright licence and recorded trademark note; use the original or thumbnail URL in the manifest. | Makes each community asset auditable and avoids relying on collection-level assertions. |
| Frontend fallback | If a manifest mapping is absent, an image fails, or a record is withdrawn, render the existing generated initials badge. | Prevents broken cards and fails closed on rights or availability uncertainty. |
| Attribution | Render the exact provider credit/link or Commons attribution required by each record. | Meets source terms and avoids implied club sponsorship or endorsement. |
| Matching and review | Generate a league-scoped report for every active fixture team, resolve aliases manually, and reject uncertain matches. | Prevents wrong-club badges and records the basis for each choice. |
| Tests | Add deterministic tests for approved mapping success, missing/withdrawn badges, duplicate names across leagues, image failure, attribution, and manifest-schema validation. | Tests the public seam without depending on a live provider. |

## Approval gate

Before implementation, choose one of these scopes:

1. **Managed-source outreach:** authorise contacting TheSportsDB and, if the written answer is satisfactory, obtaining a paid API key. The confirmation must cover public display, selected competitions, attribution, and caching.
2. **Commons subset pilot:** authorise a research-only mapping pilot for the teams in the active `public/data.json`, with no asset re-hosting and initials retained for all uncertain or absent records.
3. **Combined product model:** authorise the managed source as primary after written clearance and Commons only as a documented fallback where the provider has no badge.
4. **No logo-source change:** retain initials badges until a provider agreement or legal review is available.

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
[10]: https://github.com/Leo4815162342/football-logos "Leo4815162342 football-logos repository"
[11]: https://github.com/FCLOGO/fclogo.top "FCLOGO archived repository"
[12]: https://github.com/FCLOGO/fclogo-next "FCLOGO named successor URL"
[13]: https://github.com/luukhopman/football-logos "luukhopman football-logos repository"
[14]: https://commons.wikimedia.org/wiki/Commons:Licensing "Wikimedia Commons Licensing Policy"
[15]: https://www.wikidata.org/wiki/Property:P154 "Wikidata Property P154: logo image"
[16]: https://commons.wikimedia.org/wiki/File:Los_Angeles_Football_Club.svg "Representative Commons football crest file"
