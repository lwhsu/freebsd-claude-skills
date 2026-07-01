# GitHub API Reference

All endpoints are unauthenticated (60 req/hour limit). Set `GH_TOKEN` for 5000 req/hour.

## Fetch PR metadata

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/pulls/<N>'
```

Key fields:
- `title` — PR title
- `state` — `open` or `closed`
- `merged` — boolean
- `body` — description text
- `user.login` — submitter's GitHub login
- `html_url` — canonical URL
- `diff_url` — `.diff` URL
- `patch_url` — `.patch` URL

## Fetch PR comments (issue comments)

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/issues/<N>/comments'
```

Returns array of `{user: {login}, body, created_at}`.

## Fetch PR review comments (inline code comments)

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/pulls/<N>/comments'
```

## Fetch PR commits

```sh
fetch -qo - 'https://api.github.com/repos/freebsd/freebsd-ports/pulls/<N>/commits'
```

Returns array of commit objects. Extract author from:
- `commit.author.name`
- `commit.author.email`

## Fetch GitHub user profile

```sh
fetch -qo - 'https://api.github.com/users/<login>'
```

Key fields: `name`, `email` (may be `null` if not public).

## Parse JSON with Python

```sh
fetch -qo - '<url>' | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['field'])"
```

For arrays:
```sh
fetch -qo - '<url>' | python3 -c "import json,sys; d=json.load(sys.stdin); [print(item['field']) for item in d]"
```

## Fetch the diff

```sh
fetch -qo /tmp/pr<N>.diff 'https://github.com/freebsd/freebsd-ports/pull/<N>.diff'
```

Or stream it:
```sh
fetch -qo - 'https://github.com/freebsd/freebsd-ports/pull/<N>.diff'
```
