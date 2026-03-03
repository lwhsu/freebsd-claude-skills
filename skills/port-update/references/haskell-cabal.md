# Haskell (Cabal) Port Tips

## GHC version selection

- Check which GHC version the port needs (look at `base` bounds in `.cabal` file)
- `lang/ghc` provides the latest GHC; older versions have suffixed ports (e.g., `lang/ghc98`)
- GHC bundled libraries (base, containers, bytestring, etc.) set upper bounds for many packages

## USE_CABAL dependency resolution

Cannot use `cabal-install` on the host to resolve dependencies. Use poudriere iteratively:

1. Build → check the log
2. Add missing packages to `USE_CABAL`
3. Rebuild → repeat until successful

Reference working Haskell ports (e.g., `devel/hs-hlint`, `textproc/hs-pandoc`) for known-good package versions and revisions.

Stackage LTS gives a starting point but may not match the exact GHC patchlevel.

## Hackage revisions (`_N` suffix)

Revisions fix version bounds without changing source code — critical for GHC compatibility.

Format in `USE_CABAL`: `package-version_N` (e.g., `aeson-2.2.3.0_4` = revision 4)

Many packages need revisions to relax `base`, `containers`, `bytestring` upper bounds for newer GHC. Check existing Haskell ports for correct revision numbers — they're already tested.

When a package has no revision and has tight bounds, check Hackage:
```
https://hackage.haskell.org/package/PKG-VER/revisions/
```

## Common GHC compatibility issues

- `foldl'` added to Prelude in GHC 9.10, causing "Ambiguous occurrence" errors in older packages — use newer package versions
- `Code` kind change breaks th-compat < 0.1.5
- unix package API changes break unix-compat < 0.7
- `allow-newer: all` can cause unexpected dependency resolution

## Dependency gotchas

- `libyaml` needs `libyaml-clib` in `USE_CABAL` (all other Haskell ports include both)
- `vector-0.13.2.0_1` has a public sub-library (`benchmarks-O2`) that depends on `tasty` — must include `tasty` and `unbounded-delays` in `USE_CABAL`
- `stringsearch-0.3.6.6` has `+base4` flag with `containers < 0.6` — needs revision `_2`
- `bitwise-1.0.0.1` has extremely tight `base < 4.12` — needs revision `_11`

## FreeBSD-specific notes

- `execvpe(3)` is available in FreeBSD 15+/16+ libc — rawfilepath's `__hsunix_execvpe` patch may no longer be needed
- The ports framework applies ALL files matching `files/patch-*` — renaming to `.bak` is NOT enough to disable a patch; must `rm` the file
