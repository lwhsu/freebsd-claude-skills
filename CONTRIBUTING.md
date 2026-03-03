# Contributing

## Structure

Each skill lives in `skills/<name>/` with:

- `SKILL.md` — The skill definition (< 500 lines). Loaded by Claude Code when invoked.
- `references/` — Optional detailed reference files that the skill reads as needed.

## Guidelines

- Keep `SKILL.md` focused on the procedural workflow (what to do, in what order).
- Put detailed technical knowledge in `references/` files.
- Do not hardcode system-specific paths; use `make -V` to discover values at runtime.
- Each skill should be self-contained but may suggest other skills for related tasks.
- Test changes by running `sh setup.sh` and starting a new Claude Code session.

## Skill frontmatter

Each `SKILL.md` starts with YAML frontmatter:

```yaml
---
description: "Short description. This skill should be used when..."
---
```

The `description` field is used by Claude Code for auto-discovery.
