# Patch Rebasing Procedure

When existing patches in `files/` fail to apply after a version bump.

## Steps

### 1. Extract clean source

```sh
cd <ports-tree>/<category>/<portname>
make extract BATCH=yes
```

### 2. Create `.orig` backup files

For each file that needs patching, create an `.orig` copy:

```sh
command cp -f <WRKSRC>/<path/to/file> <WRKSRC>/<path/to/file>.orig
```

Use `command cp -f` to bypass any interactive alias on `cp`.

Identify which files need patching by reading the existing patch files in `files/` — each patch header shows the target file path.

### 3. Edit the target files

Apply the intended changes manually to each target file. Refer to the old patch to understand what the change does, then apply the equivalent change to the new source.

### 4. Regenerate patches

```sh
make makepatch
```

This generates new patch files from the diff between `.orig` and modified files.

### 5. Verify

```sh
make clean
make patch BATCH=yes
```

Confirm all patches apply cleanly.

## Important notes

- **Never edit patch files directly** — always use the `.orig` → edit → `makepatch` workflow.
- If `make clean` destroys the work directory, you must redo steps 1-2 for **all** patches before running `make makepatch`.
- If upstream already includes a patch's changes, just delete the patch file from `files/`.
- Watch for new upstream features that install Linux-specific files (e.g., systemd units) — may need new patches to remove them on FreeBSD.
- The ports framework applies ALL files matching `files/patch-*` — renaming to `.bak` or `.orig` is NOT enough to disable a patch; must `rm` the file.
