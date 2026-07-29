# Music Assistant Yoto Provider Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build and verify a read-only Yoto music provider for Music Assistant 2.9.9 that independently authenticates, imports cards and ordered tracks, browses/searches them, and resolves a fresh signed stream only at playback time.

**Architecture:** The standalone repository contains a directly loadable `yoto/` provider directory plus isolated unit/contract tests. A small adapter owns `yoto-api==4.3.2`, refresh-token persistence, catalogue refresh, and error translation; pure mapping helpers convert Yoto cards/chapters/tracks into Music Assistant albums/tracks without retaining signed URLs outside the short-lived Yoto client response. An isolated checkout of Music Assistant tag `2.9.9` loads the provider via a reversible symlink/copy in its provider directory and uses its own storage and port.

**Tech Stack:** Python 3.14, Music Assistant 2.9.9 / `music-assistant-models==1.1.129.post1`, `yoto-api==4.3.2`, aiohttp, pytest, pytest-asyncio, Ruff, mypy, uv.

---

### Task 1: Standalone project and provider manifest

**Objective:** Create an installable/testable repository and a manifest discoverable by Music Assistant 2.9.9.

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `yoto/manifest.json`
- Create: `yoto/__init__.py`
- Test: `tests/test_manifest.py`

**TDD:** First validate required manifest fields, exact pinned dependency, provider domain/type, and absence of embedded secrets; observe failure, then add the minimum manifest and setup entry point. Run `uv run pytest tests/test_manifest.py -v` and commit.

### Task 2: Stable catalogue model and identifiers

**Objective:** Preserve card/chapter/track order with stable reversible provider IDs and no signed URLs in stored catalogue records.

**Files:**
- Create: `yoto/catalogue.py`
- Test: `tests/test_catalogue.py`
- Create: `tests/fixtures/library.json`
- Create: `tests/fixtures/card_detail.json`

**TDD:** Add one vertical test at a time for library parsing, chapter/track order, metadata, ID encoding/decoding, missing values, malformed responses, and URL exclusion. Run each focused test RED then GREEN, full file, then commit.

### Task 3: Independent Yoto authentication and refresh persistence

**Objective:** Implement browser Authorization Code + PKCE with a user-supplied client ID, a secure refresh-token field, automatic refresh, and persistence of rotated refresh tokens.

**Files:**
- Create: `yoto/client.py`
- Modify: `yoto/__init__.py`
- Test: `tests/test_auth.py`

**TDD:** Test config schema and unofficial warning, browser event URL, successful token capture, absent session/client ID errors, refresh before API use, rotated-token callback, invalid refresh token translation, and secret-safe repr/logging. Use fake sessions/clients only. Run focused and full tests, then commit.

### Task 4: Music Assistant album/track mapping

**Objective:** Represent each card as an album and every playable Yoto track as an ordered Music Assistant track with author, artwork, duration, availability, and stable provider mappings.

**Files:**
- Create: `yoto/provider.py`
- Modify: `yoto/__init__.py`
- Test: `tests/test_mapping.py`

**TDD:** Add tests for album metadata/artwork, author fallback, flattened chapter/track ordering, track/disc numbers, durations, stable IDs, item lookups, removed/missing cards, and provider contract types. Run focused and full tests, then commit.

### Task 5: Library synchronisation, search, and browse

**Objective:** Import all cards and tracks, search card/track/author/series text, and browse all cards plus Yoto library groups.

**Files:**
- Modify: `yoto/provider.py`
- Test: `tests/test_provider.py`

**TDD:** Test library generators, refresh behaviour, case-insensitive search (including `Moshi` fixture), media-type filtering/limits, browse root/all-cards/groups/group contents, stale group/card handling, and clean API failure translation. Run focused and full tests, then commit.

### Task 6: Fresh and secret-safe stream resolution

**Objective:** Resolve a new signed URL immediately before playback without persisting, caching, logging, displaying, or exposing it in media metadata.

**Files:**
- Modify: `yoto/client.py`
- Modify: `yoto/provider.py`
- Test: `tests/test_streams.py`

**TDD:** Test that every call refetches card details, returns an HTTP `StreamDetails` with correct audio metadata/duration, rejects unsupported media types/missing URLs, excludes the signed URL from catalogue/config/repr/log records, and redacts errors containing URL query strings. Run focused and full tests, then commit.

### Task 7: Automated quality and Music Assistant 2.9.9 contract checks

**Objective:** Make all checks pass against the exact 2.9.9 API.

**Files:**
- Create: `tests/conftest.py`
- Create: `scripts/check.sh`
- Create: `.github/workflows/ci.yml`
- Modify code/tests as required by checks.

**Verification:** Run `ruff format --check`, `ruff check`, `mypy`, fixture secret scans, manifest parse/import against the checked-out 2.9.9 server, and complete pytest suite. Review failures with regression tests before fixes, then commit.

### Task 8: Isolated Music Assistant 2.9.9 runtime

**Objective:** Prove provider discovery, setup flow, provider load, and library sync without touching production.

**Files:**
- Create: `scripts/install-isolated.sh`
- Create: `scripts/remove-isolated.sh`
- Create: `docs/isolated-verification.md`

**Verification:** Use `/home/dave/work/music-assistant-yoto-reference/server` at tag `2.9.9`, a reversible symlink to `yoto/`, dedicated storage `/home/dave/work/music-assistant-yoto-isolated-data`, and a non-production port. Confirm manifest discovery and config entries with automated API/contract probes. For real sync, pause only for Yoto browser authorization, then verify card/track counts and `Moshi` results. Never access or alter production add-on files.

### Task 9: Documentation, security review, and upstream assessment

**Objective:** Document private installation/upgrade/rollback/limitations and assess policy-compliant upstream submission.

**Files:**
- Create: `README.md`
- Create: `docs/installation.md`
- Create: `docs/security.md`
- Create: `docs/upstream-assessment.md`
- Create: `docs/tag-player-future.md`

**Verification:** Confirm docs give reversible install/upgrade/rollback steps, identify private API/terms and story-as-album limitations, state that signed URLs must never be copied/logged, constrain Tag Player/NFC to a future UID→imported-item mapping, and cite Music Assistant contribution/AI policy sources. Do not submit a PR or change production. Commit.

### Task 10: Approved live playback and production deployment gate

**Objective:** After account verification, perform only explicitly approved live-speaker and production actions.

**Pre-flight gate:** Ask Mark to choose a Sonos and approve one audible test. Verify Music Assistant reports actual playing state and correct card/track metadata, then stop playback if requested.

**Production gate:** Present the exact deployment method, required custom image/add-on changes, backup/rollback commands, expected downtime, and validation checklist. Obtain explicit approval before changing or restarting `d5369777_music_assistant`. Never overwrite the stock add-on unrecoverably.
