# FreeBSD Claude Skills

Claude Code skills for FreeBSD development.

## Skills

| Skill | Description |
|-------|-------------|
| `port-bug` | Process Bugzilla tickets (triage, apply patches, close) |
| `port-commit` | Commit message formatting with FreeBSD trailers |
| `port-phab` | Process Phabricator reviews |
| `port-security` | Security advisory workflow (VuXML + port updates) |
| `port-update` | Version update workflow (bump, patch, test, commit) |
| `poudriere` | Test builds with poudriere |
| `src-mfc` | MFC commits from main to supported stable branches |

## Installation

```sh
sh setup.sh
```

This creates symlinks from `~/.claude/skills/` to the skills in this repo.
Restart Claude Code to pick up the new skills.

To remove:

```sh
sh setup.sh --remove
```

## Usage

In a Claude Code session within a FreeBSD ports or src tree:

- `/src-mfc abc1234` - MFC a commit from main to all supported stable branches
- `/src-mfc abc1234 def5678 -b 15` - MFC two commits (squashed) to stable/15 only
- `/port-update devel/py-foo 1.2.3` - Update a port to a new version
- `/port-bug 123456` - Process a Bugzilla ticket
- `/port-security` - Handle a security advisory
- `/port-phab D12345` - Apply a Phabricator review
- `/poudriere devel/py-foo` - Run a test build
- `/port-commit` - Format and create a commit

## License

BSD-2-Clause. See [LICENSE](LICENSE).
