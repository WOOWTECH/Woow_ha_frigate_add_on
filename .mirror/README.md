# `.mirror/` — mirror operations

Everything here is WOOWTECH-added, not from upstream. Do not delete these
files or the automation will break.

## Files

- **`config.env`** — sourced by workflows. Holds `UPSTREAM_URL`,
  `UPSTREAM_BRANCH`, `MIRROR_IMAGE_PREFIX` and `KEEP_SUBDIRS`.
- **`patch-image.py`** — rewrites `image:` fields in every add-on config so
  HAOS pulls from `ghcr.io/woowtech/ha-mirror-*` instead of upstream ghcr.
  Also emits `image-map.json`.
- **`image-map.json`** — machine-readable list of `(upstream image, arches,
  version, mirror image)` tuples. Consumed by `.github/workflows/image-mirror.yml`.
- **`last-sync.yaml`** — timestamp + upstream commit of the last successful
  mirror-sync run.
- **`<add-on dir>/upgrade-check/`, `<add-on dir>/upgrade-notes.yaml`**
  (optional) — upgrade comparison hooks/settings and declared breaking
  changes for that add-on. mirror-sync copies them into `<add-on dir>/` on
  every rebuild, so they survive the nightly sync.

## Release gating (pipeline #91)

The App Store ships only formal Releases of this repository (`v<version>`;
the first, `v0.18.2`, was created from `main` without a comparison, pipeline
#172). `mirror-sync` runs sync → image copy (`image-mirror`, which has no
schedule of its own) → the Store's upgrade comparison → Release, and the
add-on gets its Release only when it passes the comparison. If it fails, the
run fails and the step summary says which category and why. For an intended
upstream breaking change, add the declaration (with the migration) to
`.mirror/<add-on dir>/upgrade-notes.yaml`, commit it to `main`, and run
`mirror-sync` by hand: it checks the same version again and, when it passes,
creates the Release with the declaration in its notes.

## `KEEP_SUBDIRS` — why this mirror prunes

Upstream (`blakeblackshear/frigate-hass-addons`) publishes more add-ons than we
republish. `mirror-sync` therefore rebuilds `main` from upstream and then
drops every top-level path not listed in `KEEP_SUBDIRS`:

```
KEEP_SUBDIRS="frigate LICENSE"
```

The `upstream` branch is a **complete, unpruned** mirror of
`blakeblackshear/frigate-hass-addons`, so nothing is lost — if we later decide to
republish another add-on, add its directory to `KEEP_SUBDIRS` and re-run the
workflow. If a listed path disappears upstream (rename/removal), mirror-sync
fails loudly instead of publishing an empty store.

The Music Assistant and Matter Hub mirrors do not set `KEEP_SUBDIRS`; their
upstreams are single-product stores where the whole tree is wanted.

## Image naming

Sanitizer: `lowercase; '/' → '-'; '.' → '-'`

| Upstream image | Mirror image |
|----------------|--------------|
| `ghcr.io/blakeblackshear/frigate` | `ghcr.io/woowtech/ha-mirror-ghcr-io-blakeblackshear-frigate` |

For an `image:` ending in `/{arch}`, HAOS Supervisor substitutes the arch and
appends `:<version>`; `image-mirror.yml` copies each arch separately. For a
plain image (a multi-arch OCI index), one `skopeo copy --all` carries every
arch.

## Verifying a sync

```bash
gh run list --workflow mirror-sync  --limit 3
gh run list --workflow image-mirror --limit 3
cat .mirror/last-sync.yaml
```

Both workflows can be run manually from the Actions tab (`Run workflow`).
`image-mirror` normally runs only inside `mirror-sync`.
