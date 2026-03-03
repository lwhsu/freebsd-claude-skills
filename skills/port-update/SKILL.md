---
description: "Update a FreeBSD port to a new version. This skill should be used when the user asks to update, bump, or upgrade a port, or when processing a version update from a bug ticket or Phabricator review."
user_invocable: true
arguments: "<category/portname> <new-version>"
---

# Port Update Workflow

Update a FreeBSD port to a new upstream version.

## Inputs

- `category/portname` — the port to update (e.g., `devel/py-foo`)
- `new-version` — the target version (e.g., `1.2.3`)

## Procedure

### 1. Prepare the branch

```sh
git checkout main
git pull
git checkout -b claude/update-<portname>-<new-version>
```

### 2. Read current port files

Read the Makefile, distinfo, pkg-descr, pkg-plist, and any patches in `files/`.

Identify the port type by inspecting the Makefile:
- **Python**: `USES=` contains `python`
- **Rust/Cargo**: `USES=` contains `cargo`
- **Haskell/Cabal**: has `USE_CABAL`
- **Meson**: `USES=` contains `meson`
- **Go**: `USES=` contains `go`

Use `make -V VARNAME` to query Makefile variables rather than parsing with grep.

### 3. Update the version

In the Makefile:
- Change `DISTVERSION` (or `PORTVERSION`) to the new version.
- **Remove the `PORTREVISION` line** if present — version bumps reset it.
- Do NOT remove `PORTREVISION` for changes that don't bump the version (patches, dependency changes, etc.) — instead, increment it.

### 4. Regenerate distinfo

```sh
cd <ports-tree>/<category>/<portname>
make makesum
```

This downloads the new distfile and regenerates `distinfo`.

**Caveats:**
- `make makesum` changes the working directory — use absolute paths for subsequent operations.
- May fail if build dependencies aren't installed on the host. If a trusted patch provides distinfo, write it directly instead.
- Distfile directories may be root-owned after poudriere runs — may need `sudo chown` first.

### 5. Test existing patches

```sh
make patch BATCH=yes
```

If patches fail to apply, rebase them. See `references/patch-rebase.md` for the procedure.

If upstream already includes a patch's changes, delete the patch file.

### 6. Port-type-specific checks

Consult the appropriate reference file for port-type-specific guidance:
- Python ports: `references/python-ports.md` (setuptools version issues, PEP 639)
- Rust/Cargo ports: `references/rust-cargo.md` (cargo-crates, Makefile.crates)
- Haskell/Cabal ports: `references/haskell-cabal.md` (USE_CABAL deps, GHC compat)
- Meson ports: `references/meson-subprojects.md` (bundled deps, wrap files)

### 7. Check for new files

After building, watch for:
- New translations in `po/` — add to `pkg-plist` under `%%NLS%%`
- Poudriere's `check-plist` stage catches orphaned/missing files — read the build log

### 8. Test with poudriere

Use the `/poudriere` skill to run a test build. **Must be on the feature branch** — poudriere mounts the working tree.

### 9. Commit

Use the `/port-commit` skill to create the commit with proper formatting:

```
category/portname: Update to X.Y.Z
```

### 10. Switch back

```sh
git checkout main
```

## Tips

- Prefer release tarballs (`MASTER_SITES` + `DISTNAME`) over `USE_GITHUB` when available. Release tarballs from `meson dist` include vendored subprojects and generated files.
- Use `USES+=tar:xz` instead of `EXTRACT_SUFX=.tar.xz`.
- Use `BINARY_ALIAS` for binary name mappings (e.g., `python3=${PYTHON_CMD}`).
- When bumping `PORTREVISION` (not version): increment the existing value by 1.
