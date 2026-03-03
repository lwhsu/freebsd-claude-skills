# Python Port Update Patterns

## Step-by-step workflow

1. **Read current port files**: Makefile, distinfo, pkg-descr, and any patches in `files/`
2. **Check upstream changes**: Compare pyproject.toml (or setup.py/setup.cfg) between old and new versions for:
   - `[build-system] requires` — setuptools version bumps
   - `license` field format — PEP 639 vs legacy
   - `requires-python` — minimum Python version changes
   - New/removed dependencies
3. **Update Makefile**: Change `DISTVERSION` to the new version
4. **Regenerate distinfo**: Run `make makesum`
5. **Update patches**: Adjust any existing patches in `files/` for the new source
6. **Test with poudriere** using the `/poudriere` skill

## Extracting upstream source for inspection

When `make extract` fails (e.g., permissions), extract directly from the tarball:
```sh
tar xf <distfiles-dir>/<distfile>.tar.gz -C /tmp <path/to/file>
```

## Poudriere setuptools version caveat

Poudriere's `latest` package repo may ship an older setuptools (e.g., 63.x). This causes two common build failures with modern Python projects:

### PEP 639 license format (setuptools >= 77)

**Symptom**: Build error like:
```
configuration error: `project.license` must be valid exactly by one definition
GIVEN VALUE: "MIT"
OFFENDING RULE: 'oneOf'
```

**Cause**: Upstream uses PEP 639 string format `license = "MIT"` which requires setuptools >= 77.

**Fix**: Patch pyproject.toml to use legacy format:
```diff
-license = "MIT"
+license = {text = "MIT"}
```

### setuptools version requirement too high

**Symptom**: Build error like:
```
ERROR Missing dependencies:
    setuptools>=77
```

**Cause**: `[build-system] requires = ["setuptools>=77"]` but poudriere only has 63.x.

**Fix**: Patch pyproject.toml to lower the requirement to match what the port actually needs (e.g., `>=61` if that's what the previous version used). This is safe when we've already patched out the features requiring the newer setuptools (like PEP 639 license).

### Combined patch example

When both issues are present, combine fixes into a single patch file (`files/patch-pyproject.toml`):
```diff
--- pyproject.toml.orig	2025-08-24 12:54:06 UTC
+++ pyproject.toml
@@ -9,7 +9,7 @@
 requires-python = ">=3.8"
 readme = "README.md"
-license = "MIT"
+license = {text = "MIT"}
 keywords = ["MySQL"]
@@ -33,7 +33,7 @@
 [build-system]
-requires = ["setuptools>=77"]
+requires = ["setuptools>=61"]
 build-backend = "setuptools.build_meta"
```

## Patch file conventions

- Timestamp in `--- file.orig` header should match the actual file modification time from the tarball
- Context lines must match the actual source exactly
- If updating an existing patch, verify context lines still match by comparing against the new source

## Port naming patch

Many Python packages use mixed-case names on PyPI (e.g., `PyMySQL`) but FreeBSD ports use lowercase `PORTNAME`. If the port has a patch changing `name = "PyMySQL"` to `name = "pymysql"` in pyproject.toml, this patch typically needs to be carried forward across version bumps.
