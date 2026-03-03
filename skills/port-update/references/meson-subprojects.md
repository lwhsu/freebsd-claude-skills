# Meson Subprojects in FreeBSD Ports

## wrap-git vs release tarballs

- `wrap-git` clones repos at build time — **fails in poudriere** (no network)
- `wrap-file` downloads tarballs — also fails in poudriere
- Release tarballs (`meson dist`) bundle all subprojects with `patch_directory` overlays already applied — best option for ports
- If no release tarball exists, use `GH_TUPLE` to fetch subproject source and `post-extract` to apply packagefiles overlay

## patch_directory mechanism

- Wrap files can specify `patch_directory = <name>` which copies files from `subprojects/packagefiles/<name>/` over the subproject source
- These overlay files typically replace upstream build files (e.g., adding meson.build to projects that only have Makefiles)
- When `subprojects/<name>/` directory already exists, meson skips the wrap file entirely — no clone, no patch_directory overlay
- If using `GH_TUPLE` to pre-extract subproject source, must manually copy packagefiles in `post-extract`

## Meson option types matter

- `required: get_option('foo')` where `foo` is a **boolean** option: use `true`/`false`
- `required: get_option('foo')` where `foo` is a **feature** option: use `enabled`/`disabled`/`auto`
- Check `meson_options.txt` to determine the type — passing the wrong type causes immediate configure failure

## Bundled dependencies on FreeBSD

Some bundled dependencies may need FreeBSD-specific patches. Common issues:

- Build systems that only handle Linux/Darwin/Windows — need FreeBSD code paths
- Libraries that use `-ldl` — on FreeBSD, `dlopen` is in libc, not libdl
- Platform detection relying on `#ifdef __linux__` — need `#ifdef __FreeBSD__` additions

## Skipping network-dependent tests/subprojects

For subprojects that use wrap-git (e.g., gtest), patch to make them conditional:

```meson
gtest_dep_check = dependency('gtest', required: false)
if gtest_dep_check.found()
    subdir('tests')
endif
```

## Release tarball advantages

Prefer release tarballs over `USE_GITHUB` when available:
- Include vendored subprojects with overlays already applied
- Include generated files (e.g., `git_version.h`), eliminating `post-patch` hacks
- Use `USES+=tar:xz` instead of `EXTRACT_SUFX=.tar.xz` (more idiomatic)
