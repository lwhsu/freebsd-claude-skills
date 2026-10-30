# Fix sorting prompt

Sent to one subagent after verification, to rank the FIX and DESIGN items
for the report: `fixes.py` writes their summary to `{run}/fix-proposals/items.md`.
Fill in the `{...}` fields.  It does not redo the review; it sorts the
results and checks the top picks against the code.

---

You are helping finish a review of the TODO/FIXME/XXX comments in the
FreeBSD src tree at {src}.  Two reviewers (an in-depth triage, then an
independent verification) have already looked at every item below; your
job is to sort and rank their results for a report, not to redo the
review.

Input: {run}/fix-proposals/items.md, one `## <id> <verdict> <path>:<line>
status=... effort=... risk=...` header per item followed by `zh:`
(Traditional Chinese summary), `why:` (rationale) and `fix:` (proposed
fix) lines, some cut short.  Verdict FIX means the comment marks a real
defect or missing piece with a concrete fix (status verified = the second
reviewer agreed, disputed = it did not); DESIGN means it needs a
maintainer decision.  Full records, including the complete text and the
proposed patch, are in {ledger} (one JSON object per line, key "id"; use
`grep '"id": "<id>"'` rather than loading the whole file).

Do this:
1. Give every item a category, one of: memory-safety (use-after-free,
   overflow, out-of-bounds, uninitialized), locking (missing lock, race,
   lock order), error-handling (unchecked error, wrong errno, leak on error
   path), resource-leak, logic (wrong result, wrong constant, wrong
   condition), security (privilege, information leak, input validation),
   interface (man page or documented behaviour disagrees with code, wrong
   API contract), dead-code (unbuilt or unreachable code that should be
   retired), missing-feature (an unimplemented case the comment asks for),
   performance, cleanup (a correct but awkward construct to simplify).
   Pick the one that best describes the consequence.
2. Give every item a severity: high (a user can hit a crash, panic, memory
   corruption, data loss or a security problem on a supported platform),
   medium (wrong behaviour or a wrong result that a user can observe, or a
   latent bug that needs unusual conditions), low (no user-visible effect
   today: dead code, cleanup, documentation, an unimplemented corner case).
3. Group items that one change would resolve (duplicated comments, one
   directory to retire, one function to fix in several places) into
   clusters with a short name.
4. Pick the 15 to 20 most important items (high first, then medium items
   with broad reach).  For each pick, check the claim against the code
   yourself: read it at the reviewed commit with `git -C {src} show
   {head}:<path>` (the working tree may hold uncommitted edits that shift
   line numbers; do not use it, and do not modify the src tree).  Drop a
   pick whose described bug is not present in that code, and say so.  Do
   not run `git log -S`/`-G` or any history search without a path.

Write two files in {run}/:
- fix-categories.jsonl: one JSON object per item, for every item:
  {"id", "category", "severity", "cluster" (name or ""), "title_zh" (one
  line, at most 40 Chinese characters, Taiwan-style Traditional Chinese,
  saying what is wrong)}.  Write it with a short Python script using
  json.dumps(..., ensure_ascii=False).
- fix-highlights.md, in Taiwan-style Traditional Chinese (code
  identifiers, paths and commit hashes as they are): counts per category
  and per severity; the clusters with their item ids and what the single
  change would be; then the picks, each as a short paragraph: id,
  path:line, what is wrong and what a user would see, the proposed fix in
  one or two sentences, effort/risk, and what you confirmed in the code.
  End with the picks you dropped and why.

When done, reply with one line: `<n> items categorized, <k> highlights`.
