# Bugzilla CLI Reference

The `bugzilla` CLI is provided by `devel/py-python-bugzilla`.

## Querying tickets

```sh
# Basic info
bugzilla query --bug_id <N> --outputformat '%{id} %{status} %{summary}'

# Full details with comments
bugzilla query --bug_id <N> --outputformat '%{id} %{status} %{summary}\n%{comments}'

# Specific fields
bugzilla query --bug_id <N> --outputformat '%{assigned_to}'
bugzilla query --bug_id <N> --outputformat '%{component}'
```

Available format fields include: `id`, `status`, `summary`, `component`, `assigned_to`, `creator`, `comments`, `attachments`.

## Fetching attachments

```sh
cd /tmp && bugzilla attach --get <ATTACHMENT_ID>
```

Downloads the attachment to the current working directory. Use `/tmp` to avoid polluting the ports tree.

When multiple attachments exist, check `is_obsolete` — only use the non-obsolete (latest) one.

## Modifying tickets

```sh
# Close as fixed
bugzilla modify <N> --close FIXED

# Assign to someone
bugzilla modify <N> -a <email>

# Add a comment
bugzilla modify <N> --comment "ports <commit-hash>"
```

For already-committed tickets: assign to committer + close FIXED. The commit hook auto-adds the hash comment, so no need to comment the hash separately.

## REST API fallback

If the CLI returns empty comments, use the REST API:

```sh
# Get comments
curl -s 'https://bugs.freebsd.org/bugzilla/rest/bug/<N>/comment'

# Get bug details including reporter info
curl -s 'https://bugs.freebsd.org/bugzilla/rest/bug/<N>'
```

Reporter info is at `.bugs[0].creator_detail.{real_name,email}` in the JSON response.

## Getting attachment details

Use the REST API to check attachment metadata:

```sh
curl -s 'https://bugs.freebsd.org/bugzilla/rest/bug/<N>/attachment'
```

Check `is_obsolete` field to find the latest non-obsolete attachment.
