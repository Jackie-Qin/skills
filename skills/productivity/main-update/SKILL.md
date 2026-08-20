---
name: main-update
description: Fast-forward primary `main` and sweep stale state — removes worktrees whose PR is MERGED and whose tree is clean, removes worktrees that are ancestors of main with clean trees, deletes local branches whose upstream is `gone` and which are merged into main. Also sweeps remote-side cruft `git fetch --prune` can't reach: deletes orphaned remote-tracking refs owned by no configured remote (e.g. `pr/*`, `pull/*` left by `gh pr checkout`), push-deletes `origin/*` branches whose PR is MERGED (auto-delete-on-merge misses), and reports — never auto-deletes — branches with CLOSED or no PR. Surfaces "halfway work" worktrees (no PR but real WIP, or un-PR'd commits) via a per-candidate question with Open PR / Sweep / Leave options, with a supersession check for untracked files that overlap with main-tracked paths. Stashes/pops the primary checkout around the pull. Refuses to destroy anything dirty without explicit user authorization; refuses to force-push, rebase remote-pushed branches, or push-delete any remote branch not proven MERGED; refuses to auto-PR. Retires each swept worktree's dev-sandbox state and prunes stale/orphaned sandboxes as a disk backstop. Use when asked to "update main", "sync main", "clean up worktrees", "clean up branches", or after a batch of PRs has merged.
argument-hint: "[--keep <branch1,branch2,...>] [--dry-run]"
---

# Update Main + Sweep Merged Worktrees

Bulk version of `wt-close`. One pass over every worktree, every local branch, and every remote-tracking ref:

1. **Fast-forward** primary `main` to `origin/main`.
2. **Sweep merged worktrees** — any worktree whose branch has a `MERGED` PR and whose working tree is clean.
3. **Sweep ancestor-of-main worktrees** — any worktree whose branch has zero unique commits ahead of `origin/main` and a clean tree (the "stale main snapshot" case; no work to lose).
4. **Halfway-work review** — for worktrees with no PR but real uncommitted state OR un-PR'd commits, ask the user per candidate (Open PR / Sweep / Leave). Includes a supersession check that compares untracked files against tracked-on-main paths.
5. **Delete stale local branches** — any local branch whose upstream is `gone` and which is reachable from (or squash-merged into) `main`.
6. **Sweep orphaned remote-tracking refs** — local `refs/remotes/<x>/…` refs owned by no configured remote (e.g. `pr/*`, `pull/*`, `pr919` left by `gh pr checkout` / manual `fetch pull/N/head`). `git fetch --prune` only reconciles `origin/*`, so it never reaches these. Local-only delete; zero server impact.
7. **Push-delete merged `origin/*` branches** — branches whose PR is MERGED (work is already on `main`; auto-delete-on-merge simply missed them). Branches with a CLOSED PR (rejected) or no PR (possible teammate WIP / live automation) are reported, never auto-deleted.
8. **Preserve everything else** — open PRs, dirty trees outside the review path, branches in the keep-list, bot-managed branches (`dependabot/*`, release-automation branches), tags, the primary checkout itself.

The skill is intentionally conservative: when in doubt, it asks (in halfway-work review) or leaves state alone and reports.

## Arguments

Raw arguments: $ARGUMENTS

- **`--keep <branch1,branch2,...>`** — comma-separated branch names to skip even if they look mergeable. Names match the branch, not the worktree path.
- **`--dry-run`** — print the plan, do not execute. Recommended for the first run after a long break.
- **No argument** — sweep everything that qualifies.

## Step 1 — Inventory

Run in parallel:

```bash
git worktree list
git branch -vv
git status --short
git fetch origin --prune
git remote                                                  # configured remotes (usually just `origin`)
git for-each-ref --format='%(refname)' refs/remotes/        # every remote-tracking ref, incl. orphans
```

Record the **primary checkout path** (first row of `git worktree list`). If that row is tagged `(bare)` **and no row is tagged `[main]`**, the primary is a bare worktree-host: `main` exists only as a ref, there is no working tree to stash, and Steps 3–4 take the ref-level path below. Otherwise the primary is the non-bare row checked out on `main`.

`--prune` deletes remote-tracking refs whose remote branch is gone. After pruning, `git branch -vv` will show `[origin/<branch>: gone]` for every local branch whose remote was deleted (typically: PR merged + branch auto-deleted by GitHub).

**`--prune` has two blind spots this skill closes (Step 2C → Step 6.5):**
- It only reconciles refs under `refs/remotes/origin/*` (origin's fetch refspec). Refs under a *different* first segment — `refs/remotes/pr/*`, `refs/remotes/pull/*`, `refs/remotes/pr919` left behind by `gh pr checkout` or a manual `git fetch origin pull/N/head:…` — are owned by no configured remote, so prune never considers them. They clutter `git branch -r` forever at zero server cost.
- It never deletes branches *on the server*. A branch whose PR was CLOSED-without-merge (GitHub auto-deletes only on **merge**, never on close) or merged via a path that bypassed auto-delete-on-merge lingers on `origin` indefinitely.

## Step 2 — Classify

Build two lists.

**A. Worktrees** (excluding the primary checkout, any path under `.claude/worktrees/`, and any path outside the project's worktree pattern — e.g., `/private/tmp/...`, anywhere not co-located with the primary checkout). For each worktree, gather four signals:

```bash
gh pr list --head <branch> --state all --json number,state,mergedAt --jq '.[0]'
git -C <worktree-path> status --short
git -C <worktree-path> rev-list --left-right --count origin/main...HEAD   # "<behind> <ahead>"
git -C <worktree-path> status -sb | head -1                                # tracked-vs-pushed signal
```

Classify:
| PR state | Ahead of main | Tree state | Action |
|---|---|---|---|
| MERGED | any | clean | **sweep** |
| MERGED | any | dirty | skip + report (dirty merged worktree is suspicious — could be post-merge edits) |
| OPEN | any | any | skip (work in progress) |
| CLOSED | any | any | skip + report (rejected — user may want the diff back) |
| no PR | 0 commits | clean | **sweep** (no work to lose — branch is just an old main snapshot, ancestor of `origin/main`) |
| no PR | 0 commits | dirty | **halfway work** — go to Step 2.5 |
| no PR | ≥1, already pushed (`origin/<branch>` exists) | clean | **ready-to-PR** — go to Step 2.5 |
| no PR | ≥1, unpushed (no remote ref) | any | **halfway work** — go to Step 2.5 |

The "ahead=0 + clean" case is a free win a naive sweep misses — verify with `git merge-base --is-ancestor <branch-tip> origin/main` and you can `-d` safely after `git worktree remove`.

If `--keep <list>` includes the branch, force-skip and report.

**B. Local branches without a worktree** (i.e., branches in `git branch -vv` whose row does not contain a worktree path). For each:

| Upstream | Merged into main | Action |
|---|---|---|
| `gone` | yes (`git branch --merged main` lists it) | **delete with `-d`** |
| `gone` | no, but PR is MERGED | **delete with `-D`** after showing last 5 commits |
| `gone` | no, no merged PR | skip + report (could be lost work) |
| present | any | skip |

The squash-merge case is the common one for `-D`: commit SHAs differ from main's tip, so `-d` refuses, but the PR record proves the changes landed.

**C. Remote-tracking refs** (`git branch -r`). Split into two populations.

**C1 — Orphaned refs (no configured remote owns them).** For each ref under `refs/remotes/`, take the first path segment as the owning remote; if `git remote` doesn't list it, the ref is an orphan:

```bash
for ref in $(git for-each-ref --format='%(refname)' refs/remotes/ | sed 's#refs/remotes/##'); do
  [ "$ref" = "origin/HEAD" ] && continue
  remote="${ref%%/*}"                                  # `pr/838`→`pr`, `pr919`→`pr919`, `origin/foo`→`origin`
  git remote | grep -qx "$remote" || echo "ORPHAN: $ref"
done
```

Every `ORPHAN:` line is a Step 6.5 local-delete candidate — no server call, no data at risk (the underlying PR is long closed/merged; this is just a stale local checkout pointer).

**C2 — Real `origin/*` branches.** Classify each by PR state. **Do NOT bulk-fetch with `gh pr list --limit N` then grep** — on a repo with hundreds of PRs the list truncates and a merged branch then mis-classifies as "no PR". Query per-branch; that is authoritative:

```bash
for b in $(git branch -r | grep -E '^\s*origin/' | grep -vE 'origin/(HEAD|main$)' | sed 's#.*origin/##'); do
  state=$(gh pr list --head "$b" --state all --json state --jq '.[0].state // "NO-PR"')
  printf '%s\t%s\n' "$state" "$b"
done
```

| PR state | Action |
|---|---|
| MERGED | **push-delete** in Step 6.5 (work is on `main`; this just finishes the auto-delete-on-merge job) |
| CLOSED | **report only** — rejected diff; the branch is its only copy, the user may want it back. Never auto-delete. |
| OPEN | skip (live PR) |
| NO-PR | **report only** — could be a teammate's not-yet-PR'd WIP or live automation (bot/agent branch prefixes). Never auto-delete. |

Exclusions — **never push-delete even when MERGED**: `dependabot/*` (Dependabot manages its own branch lifecycle) and release-automation branches (release provenance). Report them instead. Honor `--keep <list>` here too.

## Step 2.5 — Halfway-work review (per candidate)

For every worktree flagged "halfway work" or "ready-to-PR" in Step 2A, run a per-candidate review *before* touching primary main. Do this even under `--dry-run` (the question is read-only; the action is what gets dry-run'd).

For each candidate, gather:

```bash
git -C <worktree-path> diff --stat $(git -C <worktree-path> merge-base origin/main HEAD)..HEAD   # committed work
git -C <worktree-path> diff --stat                                                                # uncommitted tracked
git -C <worktree-path> status --short                                                             # full incl. untracked
git -C <worktree-path> log -1 --format='%h %s' 2>/dev/null                                        # last commit msg
```

**Supersession check** — for any **untracked** file in the worktree, check whether the same path is *tracked on `origin/main`*:

```bash
for f in $(git -C <wt> ls-files --others --exclude-standard); do
  git -C <wt> cat-file -e "origin/main:$f" 2>/dev/null && \
    echo "SUPERSEDED-CANDIDATE: $f also exists on main; diff before treating as WIP"
done
```

If any path is flagged, diff the worktree's untracked content against `git show origin/main:<path>`. If main's version is meaningfully different, this is a "you already shipped a divergent version" case — a stale draft of work that later landed through another branch. Surface that in the prompt below so the user can choose "sweep" with full context.

Then ask the user (one question per candidate, or one batched question if there are 2+ similar candidates):

| Header | Question shape |
|---|---|
| Branch name | "`<branch>` has <diffstat> uncommitted + <N> commits ahead of main. Last commit: `<msg>`. Disposition?" |
| Options | `[Open PR]` `[Sweep — discard work]` `[Leave as-is]` |

If a supersession candidate exists, name it in the question — e.g., "`docs/plan.md` also exists on main with different content; this worktree may be superseded draft work."

**For `[Open PR]`:**
- If branch tip is unpushed: stash within the worktree if needed, fast-forward branch to `origin/main` (only when ahead=0 — i.e., the branch is an ancestor of main, in which case `git reset --hard origin/main` is non-destructive), un-stash, commit with a Conventional Commits message following the repo's commit conventions (including any standard trailers), `git push -u origin <branch>`, then `gh pr create`.
- If branch tip is already pushed: do NOT rebase or force-push. Just `gh pr create --head <branch>`. The merge tool / merger handles rebase concerns.
- Hand-write the PR body (don't auto-derive from commit message alone — the body is where the *why* lives).

**For `[Sweep — discard work]`:** the user has explicitly authorized losing the dirty state. `--force` on `git worktree remove` is permitted *only* under this branch of the flow. Then `git branch -d` (or `-D` for non-ancestor branches with PR=MERGED proof, none here).

**For `[Leave as-is]`:** record in skipped report; do not touch.

After the review, the surviving candidates are: still-OPEN-PR worktrees (untouched), still-MERGED-PR worktrees (sweep in Step 5), and any user-authorized sweeps from the review (do those alongside Step 5).

## Step 3 — Stash primary if needed

First detect whether the primary is a **bare** repo (a worktree host with no working tree of its own):

```bash
git rev-parse --is-bare-repository      # "true" → skip this whole step
```

**If bare: skip Step 3.** A bare repo has no working tree or index — `git status` / `git stash` error with "fatal: this operation must be run in a work tree" and would halt the run before the sweep. Record "primary is bare" so Step 4 takes the ref-level path and Step 7 is a no-op.

Otherwise, from the primary checkout (verify with `pwd`):

```bash
git status --short
```

If anything is modified or untracked, stash with `-u`:

```bash
git stash push -u -m "main-update auto-stash $(date +%s)"
```

Record the stash ref so Step 7 can pop it deterministically. **If the stash command fails**, stop the entire run and report — never fast-forward over un-stashed changes.

## Step 4 — Fast-forward main

**If the primary is bare** (Step 3 detected it): there is no working tree to `checkout`/`pull` into. Advance the `main` ref directly — `git fetch` into a branch ref is fast-forward-only by default, so this keeps the "diverged main = STOP" guarantee:

```bash
git fetch origin main:main      # ff-only; updates refs/heads/main to origin/main
```

If it prints `(non-fast-forward)` / `[rejected]`, STOP — local `main` diverged and needs human eyes. (A bare repo *permits* fetching into HEAD's branch precisely because nothing is checked out; the identical command is *refused* in a non-bare primary, which is why the two paths differ.)

**Otherwise (non-bare primary):**

```bash
git checkout main          # no-op if already on main
git pull --ff-only origin main
```

If `--ff-only` refuses (local main diverged from origin), STOP. Do not proceed with the sweep — divergent main is a problem that needs human eyes. Pop the stash before exiting (non-bare path only; the bare path never stashed).

## Step 5 — Sweep merged worktrees

For each worktree in the sweep list (Step 2A), first retire its dev-sandbox state (isolated DerivedData / SPM clones / owned simulator clone; no-op when absent):

```bash
command -v dev-sandbox >/dev/null && dev-sandbox ios cleanup --repo <worktree-path>
git worktree remove <worktree-path>
```

If `ios cleanup` refuses (active build / open files), report it and continue — the orphaned sandbox is caught by the Step 6.7 prune backstop.

If `git worktree remove` refuses (e.g., uncommitted change appeared between Step 2 and Step 5), skip that worktree and continue with the rest. **Never pass `--force`.**

Then delete the local branch:

```bash
git branch -d <branch>            # try safe delete first
git branch -D <branch>            # only if -d refuses AND PR is MERGED (proven in Step 2)
```

Print `git log --oneline -5 <branch>` before any `-D` so the report shows what's being force-deleted.

## Step 6 — Delete stale no-worktree branches

For each branch in the delete list (Step 2B):

```bash
git branch -d <branch>            # for the merged-into-main case
git branch -D <branch>            # for the squash-merged-PR case (after showing commit list)
```

Same `-D` safeguard as Step 5: print last 5 commits before force-deleting.

## Step 6.5 — Remote-side sweep

Runs after Step 4 confirmed `main` is healthy. Two parts; the first is local, the second touches the server.

**Orphaned remote-tracking refs (C1) — always safe, local-only:**

```bash
git branch -rd pr/838 pr/884 pr919 pull/1679 …   # every ORPHAN: ref from Step 2C1
```

`git branch -rd` only removes the local pointer under `refs/remotes/` — no network, nothing on origin changes (equivalent: `git update-ref -d refs/remotes/<ref>`). No `-D`/force needed; these refs have no merge semantics.

**Merged `origin/*` branches (C2 = MERGED) — server mutation, gated:**

Re-confirm MERGED immediately before each delete — PR state can change between Step 2 and here — then delete:

```bash
for b in <C2-MERGED branches>; do
  state=$(gh pr list --head "$b" --state all --json state --jq '.[0].state')
  [ "$state" = "MERGED" ] && git push origin --delete "$b" || echo "SKIP $b (state=$state)"
done
```

Never `git push origin --delete` a branch whose PR is CLOSED, OPEN, or absent, and never one matching `dependabot/*` or a release-automation pattern. **This is the same authorization tier as the force-push prohibition** — a remote branch you can't prove is merged may be a teammate's work. CLOSED-PR and no-PR branches are **not** deleted here; they go to the Step 8 report so the user decides.

**Pre-push hook note:** `git push origin --delete` fires the repo's pre-push hook. A hook that runs preflight/CI needs a working tree and so **fails in a bare primary** (`fatal: this operation must be run in a work tree`). Do **not** reach for `--no-verify` or a raw API call to get around it — both are guardrail circumvention. The robust fixes, in order: (1) make the hook skip delete-only pushes (detect the all-zero `<local-oid>` on stdin and `exit 0` before any working-tree command); (2) run the deletion from a regular worktree whose on-disk hook is current. Never disable the hook to force the delete.

## Step 6.7 — Sandbox prune backstop

If `dev-sandbox` is installed, reclaim sandboxes and simulator clones whose owner worktree is gone or idle (each ~18 GB when built):

```bash
dev-sandbox ios prune --max-idle-days 7          # dry-run listing; always run this first
dev-sandbox ios prune --max-idle-days 7 --live   # skip under --dry-run
```

Prune has its own hard guards (exact-UDID, shutdown state, lease, process/open-file rechecks) and refuses anything untrusted; never widen it with manual `simctl delete` or `rm -rf` on sandbox roots.

## Step 7 — Pop the stash

If Step 3 stashed:

```bash
git stash pop                     # by default pops the most recent; use the recorded ref if other sessions could have stashed
```

If `pop` reports merge conflicts, STOP and report. The stashed changes are safe (`git stash list` still shows them) — the user resolves manually. Do not `git stash drop` automatically on conflict.

## Step 8 — Report

```bash
git worktree list
git branch -vv
git branch -r                        # confirm orphaned refs gone + remaining origin branches
pwd
git log --oneline -1
git stash list                       # full stash inventory
# stash-bloat: count stashes older than 30 days
git stash list --format='%cr %gd %gs' | awk '/months ago|years ago/ || ($1+0 >= 30 && /days ago/)'
# local-only tags (present locally, absent on origin) — report only, never auto-delete.
# NB: options MUST precede the remote — `git ls-remote --tags origin --refs` parses the trailing
# `--refs` as a ref *pattern*, matches nothing, and returns empty (→ every real tag mis-flagged
# local-only). Use `--refs --tags origin`, and fail-closed if the remote read comes back empty.
remote_tags=$(git ls-remote --refs --tags origin | sed 's#.*refs/tags/##' | sort)
if [ -n "$remote_tags" ]; then
  comm -23 <(git tag | sort) <(printf '%s\n' "$remote_tags")
else
  echo "⚠️  could not read remote tags — skip local-only-tag report (do NOT claim all tags local-only)"
fi
```

Format:

```
✅ Main updated: <old-sha> → <new-sha> (<N> commits).
🧹 Removed N worktrees:
  - <path> (<branch>, PR #<n>)
  ...
✨ PRs opened from halfway-work review:
  - PR #<n>: <title> (<branch>)
  ...
🗑  Deleted N local branches:
  - <branch> (PR #<n>, force-delete: yes/no, reason)
  ...
🧽 Cleaned N orphaned remote-tracking refs (local-only): pr/838, pull/1679, …
☁️  Push-deleted N merged origin branches:
  - origin/<branch> (PR #<n>, MERGED)
  ...
📋 Remote branches left for your review (NOT deleted):
  - CLOSED (N): <branch> (PR #<n>, closed <date>) …      ← rejected diffs; branch is the only copy
  - no PR (N): <branch> …                                 ← possible teammate WIP / automation
  - bot-managed (N): <branch> …                           ← excluded by policy
🏷  Tags: N local-only tag(s) not on origin — report only; delete manually if intended.
🧯 Sandboxes: cleaned N worktree sandboxes; prune retired M stale/orphaned (freed ~X GB) or "dev-sandbox not installed".
⏭  Skipped:
  - <branch>: <reason>
  ...
📦 Stash bloat: N stashes older than 30 days. Oldest: <date>. Worth a separate stash-inspection pass.
📍 pwd: <primary-checkout>
```

If the stash-pop produced conflicts, surface that prominently at the top.

The stash-bloat line is informational — don't auto-cleanup. Stash inspection deserves its own pass (too easy to lose work).

## Important constraints

- **`git worktree remove --force` is allowed *only* when the user has explicitly chosen `[Sweep — discard work]` in Step 2.5's halfway-work prompt.** Outside that path, dirty state = another session's work. Skip and report.
- **Never force-push, never rebase remote-pushed branches as part of the sweep.** If a halfway-work candidate's branch is already on origin, `gh pr create --head <branch>` from the existing pushed ref. Rebase concerns are the merger's problem, not the sweeper's. (Learned the hard way: rebasing an already-pushed branch mid-sweep gets you correctly blocked; the right move is opening the PR from the pushed ref as-is and letting the squash-merge handle drift.)
- **`git push origin --delete <branch>` is allowed *only* for branches proven MERGED** (Step 2C2), never for `dependabot/*` or release-automation branches, and never for CLOSED-PR or no-PR branches. This is the same authorization tier as the force-push prohibition above: deleting a CLOSED-PR branch destroys the only copy of a rejected diff, and a no-PR branch may be a teammate's not-yet-PR'd work or live automation. Reconfirm `MERGED` immediately before each delete (Step 6.5) — state can change mid-run.
- **Orphaned remote-tracking refs (`git branch -rd`) are always safe to sweep** — they're local pointers under `refs/remotes/<x>/` that no configured remote owns; deleting one makes no network call and changes nothing on the server.
- **Never delete tags.** Report local-only tags (in `git tag`, absent from `git ls-remote --tags origin`) so the user decides — release tags are provenance markers, and a local-only `*-test` tag may still be intentional.
- **Never auto-PR.** Step 2.5 must ask before opening any PR. Branch name + commit message alone is insufficient signal — an "auto-PR" path can ship a directional reversal of something already shipped, because a stale draft looks identical to fresh work until a human reads the diff.
- **Never `git branch -D` without a Step-5/6 commit-list print AND a MERGED PR record.** Force-delete without one of those is data loss. Branch-tip-is-ancestor-of-main is its own proof and qualifies for `-d` (no force needed).
- **Never `git pull` with anything but `--ff-only`.** Diverged main is a stop condition.
- **Bare primary → ref-level fast-forward.** When `git rev-parse --is-bare-repository` is `true`, skip the Step 3 stash (no working tree) and advance main with `git fetch origin main:main` (itself ff-only) instead of `checkout`+`pull`. Never `checkout`/`stash`/`status` in a bare repo — they error with "must be run in a work tree" and halt the run before the remote sweep (which itself works fine bare: `git branch -rd` and `git push origin --delete` need no working tree).
- **Never `git stash drop` automatically.** If pop conflicts, leave the stash for the user.
- **Always use `--prune` on the fetch.** Without it, `[gone]` upstream markers are stale and the classification is wrong.
- **Respect `--keep`.** If the user names a branch, do not touch it even if it qualifies.
- **Skip worktrees outside the project's worktree pattern**:
  - `.claude/worktrees/*` (agent harness sessions — often have unpushed local commits)
  - external paths like `/private/tmp/*`, `/var/folders/*`, anywhere not co-located with the primary checkout (one-off detached experiments)
  - the user can override with explicit naming, but default to skip + report.

## Relationship to other skills

- **`wt-close`** — single-worktree version. Use that when targeting one branch; use this skill when sweeping after a batch.
- **`wt-start`** — creates the worktrees this skill removes.
