---
name: wt-close
description: Close one Git worktree only after its PR is proven merged or abandonment is explicitly authorized. Preserves dirty-state refusal, primary-main fast-forward checks, and conservative branch cleanup without depending on a workspace manager.
argument-hint: "[<branch-or-worktree-path>]"
---

# Close Worktree

Remove one Git worktree without losing unreviewed work. GitHub/Git evidence authorizes destruction; Git owns the lifecycle.

## 1. Resolve the target

```bash
CURRENT="$(git rev-parse --show-toplevel)"
ROOT="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
git -C "$ROOT" worktree list --porcelain
```

Resolve the argument as an exact worktree path or exact branch from `git worktree list --porcelain`. With no argument, use the current checkout only when it is non-primary. From the primary checkout, list every non-primary candidate and ask which one to close. If a selector matches more than one candidate, stop and ask; never choose the first row.

Record the worktree path, actual branch, and primary checkout path. If no target exists but a local branch remains, report regular-branch cleanup guidance and stop; this skill does not silently delete standalone branches.

## 2. Authorize removal

Unless a merge step in this same turn already proved the same PR merged:

```bash
gh pr list --head "$BRANCH" --state all --json number,state --jq '.[0]'
```

- `MERGED`: continue.
- `OPEN` or `CLOSED`: stop; do not remove the worktree.
- No PR: ask the user to confirm explicit abandonment before continuing.

## 3. Refuse dirty or live state

```bash
git -C "$WORKTREE_PATH" status --short
git -C "$WORKTREE_PATH" diff --check
```

If the worktree is dirty, stop and report the files. Never pass `--force` merely because the PR merged; uncommitted state may be newer work from another session.

If the current shell is inside the target, move to the primary checkout before removal.

## 4. Fast-forward primary main

First verify the primary checkout is clean:

```bash
git -C "$ROOT" status --porcelain
git -C "$ROOT" fetch origin main --prune
git -C "$ROOT" checkout main
git -C "$ROOT" pull --ff-only origin main
```

Stop on dirty state or divergence. Do not merge, rebase, reset, stash, or clean the primary checkout.

## 5. Remove the worktree and branch

```bash
git -C "$ROOT" worktree remove "$WORKTREE_PATH"
git -C "$ROOT" worktree prune
git -C "$ROOT" branch -d "$BRANCH"
```

Never use `git worktree remove --force` for ordinary cleanup.

For a squash-merged PR, `git branch -d` may refuse because the feature tip is not reachable from the squash commit. Before any force deletion:

```bash
git -C "$ROOT" log --oneline -5 "$BRANCH"
```

Show the commits and ask for confirmation. Only then may `git branch -D "$BRANCH"` be used.

## 6. Verify

```bash
test ! -e "$WORKTREE_PATH"
git -C "$ROOT" worktree list --porcelain
git -C "$ROOT" branch --list "$BRANCH"
pwd
```

Report the primary checkout path, `main` short SHA, removed path, and removed branch.

## Constraints

- Never remove a worktree for an open or merely closed PR.
- Never force-remove a dirty worktree.
- Never mutate a dirty or diverged primary checkout to make cleanup pass.
- Never delete a standalone branch as a side effect.
- Never clean build caches or artifacts here.

## Related skills

- `wt-start` creates the worktree.
- `main-update` performs conservative bulk cleanup after a batch of PRs merges.
