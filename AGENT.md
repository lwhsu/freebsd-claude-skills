# AGENT.md

Claude Code skills for FreeBSD development (ports, src, doc). Each skill is a
directory under `skills/<name>/` containing `SKILL.md` and optionally
`references/` for detail files loaded on demand.

## Adding or renaming a skill — update ALL of these in ONE commit

1. `skills/<name>/SKILL.md` — the skill itself.
2. `README.md` — both the **Skills table** (alphabetical) and the **Usage** list.
3. `.claude-plugin/marketplace.json` — `skills` array (alphabetical).

History shows forgetting 2 or 3 causes follow-up fix commits. Check all three
before committing.

## Conventions

- `SKILL.md` < 500 lines; procedural workflow only. Detailed knowledge goes in
  `references/*.md`, read only when needed (saves tokens).
- Frontmatter: `description` ("... This skill should be used when ..."),
  `user_invocable: true`, optional `arguments`.
- The FreeBSD upstream git remote is always named `freebsd` in these skills.
- Never hardcode system paths; discover with `make -V` etc. at runtime.
- Skills never push to the upstream `freebsd` remote; that is left to the user.
- Test: `sh setup.sh` (symlinks into `~/.claude/skills/`), restart Claude Code.

## Commit style

Plain subject lines like `skills/<name>: <change>` or `README, marketplace: ...`.
See `git log` for examples.
