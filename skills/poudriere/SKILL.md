---
description: "Run a poudriere test build for a FreeBSD port. This skill should be used when the user asks to test, build, or verify a port, or after modifying a port and before committing."
user_invocable: true
arguments: "<category/portname>"
---

# Poudriere Test Build

Run a poudriere test build for a FreeBSD port.

## Inputs

- `category/portname` — the port to test (e.g., `devel/py-foo`)

## Procedure

### 1. Verify the branch

**Critical**: Poudriere mounts the working tree. Running from `main` won't see changes on a feature branch.

```sh
git branch --show-current
```

If not on the feature branch with the changes, switch to it first.

### 2. Detect flavors

Check if the port has flavors that require testing all variants:

```sh
cd <ports-tree>/<category>/<portname>
make -V FLAVORS
make -V USES
```

Rules:
- If `USES` contains `php:` → **always** use `@all` to test all PHP flavors
- If `FLAVORS` is non-empty → use `@all` to test all flavors
- Otherwise → use the bare port name

### 3. Sync changes to steropes

The hermes user on steropes has no GitHub SSH key, so `git fetch aitna` won't work.
**Preferred workflow for iterative fixes**: SCP changed files directly.

```sh
scp -i ~/cyclopes/hermes.id_ed25519 /path/to/Makefile \
    hermes@steropes.centralus.cloudapp.azure.com:/pithos/hermes/freebsd-ports/<category>/<port>/Makefile
```

For a full tree sync, push branch to aitna from local and use HTTPS remote on steropes, or SCP all changed files.

### 4. Run poudriere (on steropes, via SSH)

Run in background so SSH disconnect doesn't kill the build:

```sh
ssh -i ~/cyclopes/hermes.id_ed25519 hermes@steropes.centralus.cloudapp.azure.com \
  "nohup sudo poudriere bulk -tr -b latest -NN -C -j 15_0_amd64 <category/portname> \
   > /tmp/poudriere-bulk.log 2>&1 &"
```

Flags:
- `-t` — run port tests
- `-r` — remove packages not listed
- `-b latest` — use pre-built binary packages for deps (avoids rebuilding lang/rust which takes 30+ min and can OOM)
- `-NN` — no-op on non-matching packages (build only what's specified)
- `-C` — clean before build

### 5. Monitor progress

**While running:**
```sh
ssh ... "sudo poudriere status -b -j 15_0_amd64"
```
Shows phase (lib-depends → build → stage), CPU%, MEM%, elapsed time.

**After completion:**
```sh
ssh ... "sudo poudriere status -f -j 15_0_amd64 | tail -3"
```
Check `BUILT` and `FAIL` columns.

For long builds (e.g. Rust ports ~12-14 min), use `ScheduleWakeup` at 270s intervals to poll.

### 6. Analyze results

On **success** (BUILT=1, FAIL=0): proceed to commit.

On **failure**: check the build log:

```sh
ssh ... "tail -60 /usr/local/poudriere/data/logs/bulk/15_0_amd64-default/latest/logs/<pkgname>.log"
```

Get clean error list:
```sh
ssh ... "grep -E '^error(\[|:)' .../logs/<pkgname>.log | head -20"
```

Common failures:
- `check-plist`: missing or extra files in pkg-plist
- `stage-qa`: staging issues
- Patch apply failures: patches need rebasing
- Dependency issues: missing `BUILD_DEPENDS` or `LIB_DEPENDS`
- Rust/Cargo-specific: see section below

Fix → SCP updated Makefile → restart build. Repeat until BUILT=1.

### 7. PHP flavor failures

If some PHP flavors fail but others succeed, add `IGNORE_WITH_PHP` to the Makefile:

```make
IGNORE_WITH_PHP=	82 83
```

Then rebuild to verify the remaining flavors pass.

## Rust/Cargo Port Specifics

### OOM during lang/rust build
Use `-b latest` to fetch pre-built rust binary. Without it, poudriere rebuilds rust from source, which requires 26+ GiB for the linker step and OOMs on 32GB VMs. The 64GB steropes config handles it, but `-b latest` is always faster.

### USE_GITHUB + USES=cargo ordering bug
`cargo-extract` (priority 600) runs before USE_GITHUB renames the source dir (priority 700). If `CARGO_VENDOR_DIR` defaults to `${WRKSRC}/cargo-crates`, extraction fails because WRKSRC doesn't exist yet.

**Fix**: Always set `CARGO_VENDOR_DIR= ${WRKDIR}/cargo-crates` in Cargo ports that also use USE_GITHUB.

### Binary install paths
Cargo places build artifacts in `${WRKDIR}/target/release/`, **not** `${WRKSRC}/target/release/`. Use `${WRKDIR}/target/release/` in `do-install`.

### Makefile.crates
Put `CARGO_CRATES=` in a separate `Makefile.crates` file. `USES=cargo` auto-includes it when present. Keeps the main Makefile readable.

### Tauri app FreeBSD portability
Several Tauri vendor crates gate GTK/Linux platform code on `target_os = "linux"` only. FreeBSD needs the same code paths. Fix with a `post-patch` loop:

```makefile
_FREEBSD_PATCH_CRATES= \
    ${CARGO_VENDOR_DIR}/muda-0.17.1 \
    ${CARGO_VENDOR_DIR}/tauri-plugin-updater-2.10.0 \
    ${CARGO_VENDOR_DIR}/tauri-plugin-single-instance-2.4.0 \
    ${CARGO_VENDOR_DIR}/tauri-utils-2.8.3

post-patch:
	@for d in ${_FREEBSD_PATCH_CRATES}; do \
		${FIND} $$d \( -name '*.rs' -o -name 'Cargo.toml' \) \
			-exec ${REINPLACE_CMD} \
			's|target_os = "linux"|any(target_os = "linux", target_os = "freebsd")|g' {} + ; \
	done
```

Discover affected crates from errors like `use of unresolved module platform_impl` or `no field X on type Y`. Add the crate to `_FREEBSD_PATCH_CRATES` and rebuild.

## Tips

- Poudriere covers `stage`, `check-plist`, and `package` — no need to run these manually.
- Build logs are the primary debugging tool — always read them on failure before attempting fixes.
- Stop steropes after a successful build: `~/cyclopes/steropes-stop.sh`
