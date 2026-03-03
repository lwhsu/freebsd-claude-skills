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

### 3. Run poudriere

```sh
sudo poudriere bulk -tr -b latest -NN -C -j <jail> <category/portname>[@all]
```

Where `<jail>` is the poudriere jail name (check with `poudriere jail -l`).

Flags:
- `-t` — run port tests
- `-r` — remove packages not listed
- `-b latest` — use latest package set for dependencies
- `-NN` — no-op on non-matching packages (build only what's specified)
- `-C` — clean before build

### 4. Analyze results

On **success**: proceed to commit.

On **failure**: check the build logs. Common log location:

```
/usr/local/poudriere/data/logs/bulk/<jail>-default/<timestamp>/logs/errors/
```

Common failures:
- `check-plist`: missing or extra files in pkg-plist
- `stage-qa`: staging issues
- Patch apply failures: patches need rebasing
- Dependency issues: missing `BUILD_DEPENDS` or `LIB_DEPENDS`

### 5. PHP flavor failures

If some PHP flavors fail but others succeed, add `IGNORE_WITH_PHP` to the Makefile:

```make
IGNORE_WITH_PHP=	82 83
```

Then rebuild to verify the remaining flavors pass.

## Tips

- Poudriere covers `stage`, `check-plist`, and `package` — no need to run these manually.
- Build logs are the primary debugging tool — always read them on failure before attempting fixes.
