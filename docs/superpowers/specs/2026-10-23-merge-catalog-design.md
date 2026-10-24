# Merge the CadQuery Catalog into PyTools

Date: 2026-10-23. Status: draft for review.

## Goal

One site, one repo, one database. PyTools (`raubcamaioni.com/tools`, repo `RaubCamaioni/PyTools`) absorbs the
CadQuery Catalog (`raubcamaioni.com/catalog`, repo `RaubCamaioni/cadquery-catalog`). Every entry is a tool (a
script). A tool whose entrypoint returns a CadQuery object is a **model**: it gets the catalog's display (3D viewer,
STL/STEP downloads, preview thumbnail). `?kind=model` filters any listing to models only and shows them as the
catalog's card grid. The catalog's metadata (tags, categories, description) and its create/edit dialog apply to all
tools. `/catalog` goes away.

Success: `raubcamaioni.com/tools/?kind=model` shows the 130 repo models as the catalog shows them today; the 245
existing tools still run unchanged; every tool can carry tags, categories and a description; the catalog service,
image and repo are retired.

## Decisions (from the user)

- PyTools is the surviving repo and app. The catalog's features are ported into it in stages (approach A), each
  release live on its own.
- One sandbox image (PyTools' image, which already includes `cadquery>=2.3.0`).
- One category tree for all scripts, two levels, no "Models" top level: a model is filed like any other tool.
- The kind filter is a query parameter, `?kind=model`, not a path. Stored kinds: `script`, `model`.
- `/tools` stays PyTools' text list; model rows get a small thumbnail. `?kind=model` shows the card grid.
- One database. The catalog's database is not imported: the 130 repo models are added as new tools, as if uploaded
  today, under the owner's account (the only real account). Votes, runs and ids start fresh.
- No `/catalog` redirects and no id mapping: the `/catalog` location is removed; old links 404.

## Model detection

- The sandbox's `--inspect` report gains the entrypoint's declared return annotation (as written, e.g.
  `cq.Workplane`). sandboxcore's `Signature` carries it (`returns: str | None`); a sandboxcore minor release.
- A tool is a model when the annotation names a CadQuery type (`Workplane`, `Shape`, `Solid`, `Compound`,
  `Assembly`, bare or `cq.`/`cadquery.` qualified) **and** a build with default arguments succeeds at create or code
  update. All parameters must have defaults; `Path = None` counts as a default (the demo build).
- A script that declares a CadQuery return but fails its build is refused (400, the build error shown), as the
  catalog does today. Nothing is stored.
- `Tool.kind` (`script` | `model`) is set on every create and code update. The successful default build is stored
  with the tool (`preview.svg`, `model.stl`, `model.step`, `meta.json`) as the catalog stores it, under the data
  directory, and deleted with the tool.

## Runtime

- The catalog's `sandbox/src/sandbox/export.py` moves into PyTools' sandbox package. The result step checks the
  entrypoint's return value: a CadQuery object is exported (STL, STEP, preview, meta) and the run's result is the
  catalog's model result dict. Any other value is serialised as today.
- So a plain script that happens to return a shape still displays as a model for that run; it is only listed as a
  model if it declares the return type and passes the upload build.
- The catalog's import-time trims (`sandbox/stubs/` for vtk/ezdxf, the pinned CadQuery version lookup) move into
  PyTools' `Containerfile.sandbox`. Converter imports are unaffected (libraries load on import).

## Pages and URLs

All under `ROOT_PATH=/tools`; tool pages stay `/tools/tool/{id}`.

- **Script page:** today's PyTools page, with the description above the code and tags/categories shown.
- **Model page:** the catalog's model page: viewer showing the stored default build, the parameter panel with
  rebuild, STL/STEP downloads, size/volume readout, the code viewable, the same metadata.
- **Listings:** `/tools/` and `/tools/c/{cat}[/{sub}]`, with `search`, paging and `kind`. Without `kind`: the text
  list, model rows with a small thumbnail. With `kind=model`: the card grid of models only. The category bar shows
  only categories that have tools in the current view (with counts). A header switch `[all] [models]` toggles
  `kind`, keeping category and search. Every link inside a listing (categories, search, paging) keeps `kind`.
- **Profile:** the catalog's `[create]` / `[edit]` dialog (file, description, tags, categories) replaces PyTools'
  upload input and per-tool update button, for all tools.

## Metadata

- The catalog's `app/metadata/` registry moves as is: kinds Tags, Categories, Description; tables renamed
  `ToolTag`, `ToolCategory`, `ToolDescription`. The editors (`meta-editors.js`, entry row with `[+]`, chip box,
  dropdowns) come with it.
- PyTools' `Tool.tags` JSON column is copied into `ToolTag` once (the catalog's `copy_json_tags` with its
  `DoneMigration` marker), then the column is dropped.
- `tags/suggest` lists tags in use on public tools.

## Category tree

One `server/src/app/categories.yaml`. Slugs are permanent once released.

| Top level (slug) | Subcategories (slug) |
|---|---|
| Converters (`converters`) | Images (`images`), Documents & PDF (`documents`), Media (`media`), Data formats (`data`), Units (`units`), 3D files (`3d`) |
| Text (`text`) | Encoding (`encoding`), Formatting (`formatting`), Generators (`generators`) |
| Developer (`developer`) | Code (`code`), Web (`web`), Regex & cron (`patterns`) |
| Security (`security`) | Hashing (`hashing`), Passwords (`passwords`), Encryption (`encryption`) |
| Utilities (`utilities`) | Time & date (`time`), QR & barcodes (`codes`), Calculators (`calculators`) |
| Home, Office & Desk, Workshop, Hardware & Electronics, Outdoor & Garage, Hobbies | the catalog's subcategories and slugs, unchanged |
| Miscellaneous (`misc`) | none; the fallback, alone |

Rules unchanged from the catalog: up to 3 categories, the first is primary, `misc` stands alone, none or unknown
falls back to `misc`.

## Repo content and filing

- The catalog's `models/` (130 scripts) moves to `tools/models/`. The 245 existing tools are filed too.
- One manifest, `tools/catalog.yaml`: for each repo tool, its file, categories, tags and description. Drafted by
  Claude, reviewed by the user in the PR.
- `pytools-admin apply-manifest <yaml> [--apply]` (the catalog's command, dry run by default, backup to
  `/data/backups` before writing) gains one ability: an entry whose tool does not exist on the site (matched by
  name and owner) is created from its file through the normal upload path (including the model build), then made
  public and given its metadata. Existing tools only get their metadata compared and updated.
- A repo test fails when a repo tool has no manifest entry.

## Releases

Each is a `v<semver>` tag matching `server/pyproject.toml`, checked in a browser against the local dev server
before tagging and confirmed live after.

1. **v0.4.0, runtime:** sandboxcore with `returns`; `export.py` and the stubs in the sandbox image; a returned
   CadQuery object displays as a model on the run result. (The unreleased sandboxcore switch from #14 ships here;
   sandbox image first, then the app.)
2. **v0.5.0, metadata:** registry, tables and JSON-tag copy, category tree, create/edit dialog, browse by category,
   `apply-manifest`, `tools/catalog.yaml` filing the existing tools, applied live.
3. **v0.6.0, models:** `Tool.kind`, the upload build and stored default build, model page, thumbnails,
   `?kind=model` card grid, `[all] [models]` switch; `tools/models/` added and created live through
   `apply-manifest --apply`.
4. **Retire the catalog:** remove the `/catalog` nginx location; stop and disable `catalog.service` and
   `catalog-update.timer`; keep its data directory and a final backup until the user has checked `?kind=model`
   live, then delete them; archive `RaubCamaioni/cadquery-catalog`; the user deletes the catalog's GitHub OAuth
   app. No app release.

## Testing

- PyTools' suite plus the catalog's tests ported: metadata (tags, categories, description, routes), tag migration,
  categories, browse, manifest, admin CLI, upload build, model routes.
- New: return-annotation detection (each CadQuery type name, qualified and bare, a non-CadQuery annotation, none);
  a declared model failing its build is refused and not stored; a converter runs unchanged in the merged image;
  `kind` is kept by every listing link; `apply-manifest` creates missing tools and is idempotent on re-run.
- Before v0.4.0 ships: a model build and a heavy converter run inside PyTools' memory cap (2 GB) on the server.

## Out of scope

Carrying over catalog votes, runs or ids; redirects from `/catalog`; new export formats (3MF, glTF); per-kind
sandbox images; more metadata kinds (variations, printer profiles) beyond keeping the registry open to them.
