# OSVERSION-Conditional Knobs in Ports

When a port needs different `CONFIGURE_ARGS` / `MAKE_ENV` / patches
depending on the **host FreeBSD release** — usually to work around a
kernel- or libc-level regression in older releases that newer releases
have fixed.

## When to use

- A new upstream release relies on a kernel or libc feature that only
  works on a newer FreeBSD branch (e.g. SVE signal-context handling,
  new `sigaltstack(2)` semantics, new `elf_aux_info(3)` aux vector
  entries).
- The fix landed in a specific releng branch (e.g. `releng/15.1`) and
  must be MFCed before older supported releases get it.
- You want the port to keep building on the older releases until
  EoL without sacrificing the newer release's correctness.

If the workaround needs to be at runtime (not just build-time), prefer
patching the source so the binary detects the kernel at startup. Use
this `OSVERSION` conditional only when build-time selection is enough.

## Pattern

`OSVERSION` is defined by `bsd.port.pre.mk`, so any conditional that
references it must appear **after** that include. The convention is to
put it inside the existing per-arch block:

```make
.include <bsd.port.pre.mk>

.if ${ARCH} == aarch64
CONFIGURE_ARGS+=	--disable-dtrace
# 15.0/aarch64 kernel mishandles SVE signal-context alignment, which
# corrupts JIT signal frames on Neoverse N2 once HotSpot turns on the
# SVE codepath via elf_aux_info(3).  Fixed in releng/15.1.
.if ${OSVERSION} < 1501000
MAKE_ENV+=	JAVA_TOOL_OPTIONS=-XX:UseSVE=0
.endif
.endif
```

OSVERSION format: `MMmmppp` (e.g. `1501000` = 15.1, `1500000` = 15.0).
Look up exact values in `sys/sys/param.h` (`__FreeBSD_version`).

## Verification

Test both branches of the conditional **without running poudriere**:

```sh
cd <ports-tree>/<category>/<portname>
# Should print the new MAKE_ENV addition:
make -V MAKE_ENV ARCH=aarch64 OSVERSION=1500000 | tr ' ' '\n' | grep <key>
# Should NOT print it:
make -V MAKE_ENV ARCH=aarch64 OSVERSION=1501000 | tr ' ' '\n' | grep <key>
```

This catches typos and inverted comparisons (`<` vs `>`) in seconds.
Then run a full poudriere build against a jail of the older release
to confirm the workaround actually fires in practice.

## Documentation

Always add a short comment explaining **why** the workaround exists,
including the upstream commit or PR that introduced the dependency and
the FreeBSD branch that contains the fix.  Future maintainers will
delete the conditional once the older release reaches EoL; the
comment is what tells them it is safe to do so.

## Caveats

- `OSVERSION` reflects the **build host**, not the runtime host.  A
  package built on a 15.0 builder will still get the workaround
  baked in even if the user runs it on 15.1.  If that matters,
  document it in `pkg-message`.
- Conversely, a package built on a 15.1 builder will **not** include
  the workaround, so users on 15.0 may need to set the env-var
  themselves.  Decide which side the workaround should protect, or
  patch the source for runtime detection.
- Do not bump `PORTREVISION` just for adding a build-host-only
  workaround that does not change the resulting package binary;
  rebuild it next time the port version bumps naturally.
