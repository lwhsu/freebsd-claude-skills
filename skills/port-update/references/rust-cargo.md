# Rust/Cargo Port Tips

## Updating Makefile.crates

After bumping the version, regenerate the cargo crate list:

```sh
cd <ports-tree>/<category>/<portname>
make cargo-crates > Makefile.crates
```

Then clean and regenerate distinfo:

```sh
make clean
make makesum
```

## WRKSRC_SUBDIR gotcha

`make cargo-crates` looks for `Cargo.lock` under `WRKSRC` (which includes `WRKSRC_SUBDIR`). For workspace repos where `Cargo.lock` is at the repo root but `WRKSRC_SUBDIR` points to a subcrate, `make cargo-crates` will fail with "Cargo.lock not found".

**Workaround**: Run the awk script directly on the correct path:

```sh
/usr/bin/awk -f /usr/ports/Mk/Scripts/cargo-crates.awk \
    <work-dir>/<name>-<version>/Cargo.lock > Makefile.crates
```

Find the correct work directory path:

```sh
make -V WRKSRC
make -V WRKDIR
```

## Large distinfo files

The `distinfo` for cargo ports can be very large (hundreds of crate checksums). When reading, use the `limit` parameter to avoid overwhelming the context.

## Workflow summary

1. Bump `DISTVERSION` in Makefile, remove `PORTREVISION`
2. `make makesum` to fetch new source tarball
3. `make extract BATCH=yes` to get the source
4. `make cargo-crates > Makefile.crates` (or use the awk workaround)
5. `make clean && make makesum` to fetch all crates and regenerate distinfo
6. Test with poudriere
