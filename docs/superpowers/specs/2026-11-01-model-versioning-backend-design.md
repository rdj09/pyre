# Panel Workbench Model Versioning & SQLite Backend Design

**Date:** 2026-11-01
**Status:** Approved
**Scope:** A SQLite-backed persistence and versioning layer for the Panel treaty pricing workbench (`app/`) — save/load/copy/delete pricing models, mark versions final vs. optional, a catalog dashboard, and a version-comparison view.
**Backward compatibility:** Fully additive. No changes to any existing public `pyre` signature.

---

## Intent and why

The workbench currently has no persistence at all — close the browser tab
and everything (loaded claims/exposures, contract config, layers, pricing
results) is gone. The user's actual workflows all involve coming back to
work later or building on prior work:

1. **Save-and-resume** — stop partway through configuring a contract, come
   back and finish later.
2. **Edit an old model** — reopen a saved model, update it with new
   claims/exposures data, re-run.
3. **Renewal copy** — clone last year's model wholesale, swap in this
   year's data, keep the two linked.
4. **Movement analysis** — diff two linked versions, both their inputs
   (what changed in the contract/claims/exposures) and their outputs
   (what moved in the results).
5. **Cross-pricing pattern awareness** (long-term, non-goal for this
   piece — see below) — once many pricings are stored, look across all
   of them for recurring manual adjustments or errors.

This is third of four follow-up subsystems identified after the Freyja
branding work (report export — shipped; **this one**; xlwings
integration — not started). It is independent of the other two: no
shared files, no shared design decisions.

## Goals

- Save a pricing model — claims, exposures, contract metadata, layers,
  and (if computed) results — to a local SQLite database, at any point,
  complete or partial.
- Load a saved model back into the workbench exactly as it was.
- Copy a saved model into a new, independent version that remembers what
  it was copied from.
- Delete a saved version.
- Mark any version as "final" or leave it "optional" — a plain flag, not
  enforced-unique; several optional siblings and one or more finals can
  coexist under the same parent.
- A catalog/dashboard view: counts of saved versions and the contract
  details sitting against them.
- A comparison view: pick two or more saved versions and see what
  differs, in both inputs and results.
- Recompute a loaded version's results on demand (pricing logic in
  `pyre` can change; a saved version's cached results can go stale).

## Non-goals / anti-goals for this piece

- **Cross-pricing pattern mining or auto-suggested corrections.** The
  relational results table this design adds is what would make that
  possible later; building the mining/suggestion logic itself is out of
  scope here. Building it anyway, unasked, would be scope creep this
  spec explicitly rejects.
- **xlwings / live Excel integration.** Separate subsystem, not touched.
- **Multi-user concurrency, auth, or a networked database.** This is a
  local, single-user SQLite file, matching how the workbench already
  runs (`panel serve` / `python run_app.py` on one machine).
- **Claim-level or exposure-level diffing in the comparison view.**
  Comparing claims/exposures row-by-row between two versions is a
  plausible future want, but nothing in the brainstorming conversation
  asked for it — v1's input diff covers contract/layer fields (the
  "structures and terms and conditions" the user explicitly described
  wanting to compare) plus claims/exposures summarized as counts and
  totals.
- **A trash/undo for deletes.** Delete is a real delete. If this turns
  out to be too risky in practice, a soft-delete is a small, isolated
  follow-up — not building it speculatively now.

## Constraints

- `src/pyre` stays dependency-free — this entire subsystem lives under
  `app/`, never under `src/pyre/`, matching the existing convention that
  keeps the core package free of `panel`/`pandas`/`openpyxl`.
- No new third-party dependencies — `sqlite3` and `pickle` are both
  stdlib.
- Must not change `WorkbenchState`'s existing behavior for the current
  (non-persisted) in-memory session — persistence is additive.

---

## Decisions made during brainstorming (the "how," already decided)

### Storage split: relational metadata + results, pickled inputs

Three kinds of data, stored two different ways:

1. **Version/lineage metadata** (label, parent link, final flag,
   timestamps, denormalized contract identity fields for display) —
   plain relational columns. This is exactly what the catalog dashboard
   and comparison picker need to list/filter/group, and it's cheap and
   small.
2. **Pricing results** (`by_layer_year` / `exposures_by_year`) — plain
   relational rows, one table each, reusing the exact row shapes
   `summarize_by_layer_year`/`summarize_exposures_by_year` already
   produce (`src/pyre/models/Experience/experience_preparer.py`, shipped
   in the report-export work). Relational because this is precisely the
   data a dashboard or future cross-pricing query would aggregate —
   a pickled blob would make it invisible to SQL.
3. **Full input object graph** (`Claims`, `Exposures`,
   `RIContractMetadata` + `list[RILayer]`) — **pickled** into a single
   `BLOB` column per version. This is the user's own suggestion, applied
   where it actually pays for itself: the inputs just need to come back
   out exactly as they went in, with zero hand-written
   serialize/deserialize mapping code for every nested dataclass. Not
   used for results or metadata, which need to be queryable.

Trade-off, stated plainly: pickle ties a saved blob to the exact class
shape at save time. If a `pyre` dataclass's fields change later, old
blobs may fail to unpickle. Mitigation for this round: store the
installed `pyre.__about__.__version__` alongside each blob so a failed
load can at least say *why* ("saved under pyre 0.0.1, this is 0.0.3") —
no migration tooling is being built now. This is a deliberate, named
risk, not an oversight.

### Versioning is a tree, not a line

Every saved version optionally points at the version it was copied from
(`parent_id`). Multiple versions can share a parent — the different
structures/T&Cs tried against the same base. `is_final` is a plain
boolean with no uniqueness constraint: several optional siblings and one
or more finals can coexist.

### Saving is an explicit action

A "Save Version" action, separate from "Run pricing." The user decides
when something is worth checkpointing; nothing is saved automatically on
every run. Saving a version with no results at all is valid (the
save-and-resume case) — `claims`/`exposures`/`contract_metadata` can all
be `None` and `layers` can be empty.

### Copy duplicates the full blob

Copying a version writes a new row with a new pickled blob (a full copy
of the parent's inputs) and `parent_id` set to the original. No
reference-sharing or deduplication — storage is cheap, correctness is
simple, and it avoids any risk of one version's "copy" accidentally
mutating another's stored data.

### Delete is a real delete

Removes the version row and its associated results rows. No trash, no
recovery (see Non-goals).

### Results are cached, not recomputed on every view

Loading a version for viewing or comparison reads its cached results
rows directly — no recomputation. A separate, explicit "Recalculate"
action rebuilds `ExperienceModelData` from the version's pickled inputs,
re-runs `run_pricing`, and lets the user choose to overwrite this
version's cached results or save the fresh results as a new version.

### Load drops back into the fully editable forms

Loading a version repopulates `app/pages/contract_config.py` and
`app/pages/data_loading.py`'s tabs with the saved values, fully
editable from there — the user keeps working on it exactly as if
they'd built it live this session, rather than landing on a read-only
snapshot they'd have to Copy before touching.

This requires retrofitting both pages, which today build every widget
from hardcoded literal defaults (`date.today()`, `"C-0001"`, an empty
`layer_rows` list, etc.) with no path for `state` to seed them. Each
widget's initial value needs to fall back to the corresponding field on
`state` (`state.contract_metadata`, `state.layers`,
`state.claims`/`state.exposures`) when already populated, instead of
the current literal. "Load" itself then becomes: set those `state`
fields from the unpickled `ModelSnapshot`, then rebuild and swap in the
three main tabs (`build_contract_config_page(state)`,
`build_data_loading_page(state)`, `build_results_page(state)`) so the
now-state-seeded widgets render. This is the one piece of this design
that modifies existing page behavior rather than only adding new files —
flagged explicitly so the implementation plan scopes it as its own task
with its own tests, not a one-line aside inside a bigger task.

### Exporting a loaded-but-not-recalculated version (builder's call)

`results.py`'s existing "Export to Excel" button needs a live
`ExperienceModelData` object, which a cached-results load never
produces (by design — Load doesn't recompute). Rather than disabling
export until Recalculate, a loaded version's "Export to Excel" writes
directly from its **cached** `pricing_results_by_layer_year`/
`pricing_results_exposures_by_year` rows via `write_table` (the same
primitive `write_experience_rating_results` already uses), bypassing
`ExperienceModelData` entirely. The live "Run pricing" page keeps using
the existing `ExperienceModelData`-based export unchanged.

### SQLite connection lifecycle (builder's call)

One connection opened and closed per repository call (a context-managed
`sqlite3.connect(path)` per function in `app/db.py`), not a long-lived
module-level connection. `panel serve` can host multiple browser
sessions in one process, each with its own `WorkbenchState`; `sqlite3`
connections aren't safely shared across threads, and per-call
open/close sidesteps that with no meaningful performance cost for an
occasional-click save/load/compare workload. `PRAGMA foreign_keys = ON`
is set on every connection open.

### Catalog grouping (builder's call)

The dashboard groups and counts by the denormalized `contract_id`
column, not by walking `parent_id` lineage to a root ancestor. "High
level summary of counts... against contract details" reads as a direct
catalog of saved versions grouped by the contract identity actually
displayed, not a reconstructed deal-level rollup across renewals (which
would also be ambiguous the moment a copy changes its `contract_id`).
Lineage stays available for the Compare view's parent/child navigation,
just not for dashboard grouping.

### Storage location

A new `data/` directory at the repo root (gitignored), containing
`data/workbench.db`. Not under `app/` (keeps a runtime data artifact out
of the source tree) and not inside `src/pyre/` (same dependency-free
rule as everything else in this design).

---

## What's left to the builder

### Schema (concrete, in `app/db.py` or an `app/db/` package — single file is fine for this size)

```sql
CREATE TABLE pricing_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    parent_id INTEGER REFERENCES pricing_versions(id),
    is_final INTEGER NOT NULL DEFAULT 0,          -- 0/1
    created_at TEXT NOT NULL,                      -- ISO 8601
    updated_at TEXT NOT NULL,
    pyre_version TEXT NOT NULL,
    contract_id TEXT,                              -- denormalized, nullable (draft saves)
    cedent_name TEXT,
    contract_description TEXT,
    inception_date TEXT,
    expiration_date TEXT,
    inputs_blob BLOB NOT NULL                      -- pickled ModelSnapshot
);

CREATE TABLE pricing_results_by_layer_year (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    layer_id INTEGER NOT NULL,
    layer_name TEXT NOT NULL,
    modelling_year INTEGER NOT NULL,
    ceded_paid REAL NOT NULL,
    ceded_incurred REAL NOT NULL,
    claim_count INTEGER NOT NULL,
    earned_premium REAL NOT NULL,
    loss_ratio REAL                                -- nullable, matches summarize_by_layer_year
);

CREATE TABLE pricing_results_exposures_by_year (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL REFERENCES pricing_versions(id) ON DELETE CASCADE,
    modelling_year INTEGER NOT NULL,
    written REAL NOT NULL,
    earned REAL NOT NULL
);
```

`PRAGMA foreign_keys = ON` must be set per-connection for the `ON DELETE
CASCADE` to actually fire (SQLite default is off).

### `ModelSnapshot` (the pickled payload)

A small plain dataclass, defined in `app/db.py`, **not** reusing
`WorkbenchState` directly (that class also carries `results`, which are
pandas DataFrames headed for the relational tables instead, and pickling
them twice is wasteful):

```python
@dataclass
class ModelSnapshot:
    claims: Claims | None
    exposures: Exposures | None
    contract_metadata: RIContractMetadata | None
    layers: list[RILayer]
```

### Repository functions (`app/db.py`)

- `init_db(path: Path) -> None` — create tables if absent, enable foreign keys.
- `save_version(conn, state: WorkbenchState, label: str, parent_id: int | None, is_final: bool) -> int`
- `save_results(conn, version_id: int, results: PricingResults) -> None` — called after a run, or by Recalculate.
- `load_version(conn, version_id: int) -> tuple[ModelSnapshot, PricingResults | None]`
- `list_versions(conn, *, final_only: bool = False) -> list[VersionSummary]` — `VersionSummary` is a small dataclass with the denormalized display columns plus result counts, never unpickling the blob.
- `copy_version(conn, version_id: int, new_label: str) -> int`
- `delete_version(conn, version_id: int) -> None`
- `set_final(conn, version_id: int, is_final: bool) -> None`
- `diff_versions(conn, version_id_a: int, version_id_b: int) -> VersionDiff` — `VersionDiff` holds: per-layer field changes (attachment/limit/type/etc., unpickling both blobs), claims/exposures count+total deltas, and a joined-by-(layer_id, modelling_year) results comparison with a delta column (straight SQL, no unpickling needed for this half).

### Panel UI

- New tab in `app/main.py`'s `pn.Tabs`: **"Saved Models"**
  (`app/pages/model_library.py`) — the catalog/dashboard (counts +
  contract details, per Goals), a table of versions with Load / Copy /
  Delete / Mark Final actions, and the entry point for "Save Version"
  (label field + optional parent selection, defaulting to "no parent").
- New tab: **"Compare"** (`app/pages/compare.py`) — pick two or more
  saved versions from a multi-select, show the input diff and the
  joined results diff.
- `app/pages/results.py` gains a "Save Version" button next to "Export
  to Excel," and (once a version is loaded) a "Recalculate" button.
- `app/state.py`'s `WorkbenchState` gains an optional `loaded_version_id`
  field so the UI knows whether "Save" should create a new row or is
  really "Save As" vs. updating the currently-loaded one — exact UX
  (always-new-version vs. overwrite-in-place) is left to the
  implementation plan to pin down with concrete steps, since it's a
  mechanical detail, not a new design decision.

### Testing

Unit-testable without a running Panel server, same convention as
`app/service.py` — `app/db.py` has no `import panel`. Cover: save
draft (no claims/no contract) and reload it unchanged; save a version
with results and reload the results rows; copy preserves parent link
and produces an independent blob (mutate the copy's claims after
loading, confirm the original is unaffected); delete removes result
rows via cascade; `diff_versions` on two hand-built versions with a
known layer-limit change and a known loss-ratio change produces the
expected diff; `pyre_version` is recorded and surfaces on a
deliberately-corrupted blob instead of a raw `pickle` traceback.

### Out of scope, explicitly, for the implementation plan to not drift into

See Non-goals above — cross-pricing mining, xlwings, claim-level diffing,
soft-delete/trash, multi-user/networked access.
