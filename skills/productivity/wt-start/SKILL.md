---
name: wt-start
description: Start an independent work session in a fresh Git worktree based exactly on origin/main. Protects dirty primary checkouts, verifies the remote base, and restores required gitignored config without depending on a workspace manager.
argument-hint: "<task-or-branch-name>"
---

# Worktree Start

Create one independent Git worktree for one task. Git is the only lifecycle manager.

## 1. Resolve the repository

From any checkout in the target repository:

```bash
CURRENT="$(git rev-parse --show-toplevel)"
ROOT="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
git -C "$ROOT" worktree list --porcelain
git -C "$ROOT" status --porcelain
git -C "$ROOT" fetch origin main --prune
EXPECTED="$(git -C "$ROOT" rev-parse origin/main)"
```

Confirm `ROOT` is the primary checkout shown by `git worktree list`. Stop on a bare or unusual custom layout rather than guessing.

A dirty primary checkout is an active-session signal, not a blocker. Never stash, commit, reset, clean, or discard it.

## 2. Choose branch and path

Use the requested task name as the branch only if `git check-ref-format --branch "$BRANCH"` accepts it and no local branch already has that name. Otherwise ask for a valid unique branch; do not silently reuse or rewrite one.

Choose the worktree root in this order:

1. A location required by the repository's nearest `AGENTS.md` or setup script.
2. Existing project-local `.worktrees/` or `worktrees/`, but only when `git check-ignore` proves the directory is ignored.
3. A sibling directory named `<repo>-worktrees/` next to the primary checkout.

```bash
WORKTREE_PATH="<absolute-selected-path>"
test ! -e "$WORKTREE_PATH"
git -C "$ROOT" check-ref-format --branch "$BRANCH"
test -z "$(git -C "$ROOT" branch --list "$BRANCH")"
```

If using a project-local directory, stop unless it is ignored. Never create a worktree inside a tracked path.

## 3. Create from the exact remote base

```bash
git -C "$ROOT" worktree add -b "$BRANCH" "$WORKTREE_PATH" origin/main
```

Do not run a worktree-creating setup script after this command. If the repository requires its own creator script, read that script first and use its documented interface *instead of* `git worktree add`, then verify the resulting checkout is based on the fetched `origin/main`.

## 4. Restore project-local setup

Read the nearest `AGENTS.md` and any `scripts/setup-worktree.sh` for post-create requirements such as hooks, ignored credentials, symlinks, or dependency installation. Apply only the post-create portions; do not create a second worktree.

The most common gap: gitignored config the app needs at runtime (`.env.local`, service credentials, generated config) exists in the primary checkout but not in a fresh worktree. Symlink from the primary rather than copying, so there is one source of truth:

```bash
src="$ROOT/<ignored-config-file>"
dst="$WORKTREE_PATH/<ignored-config-file>"
test -e "$dst" || { test -f "$src" && ln -s "$src" "$dst"; }
```

Also restore a repo-managed hooks path if the project uses one:

```bash
git -C "$ROOT" config core.hooksPath <hooks-dir>   # only if the repo documents it
```

For each repository, inspect its instructions instead of guessing paths.

## 5. Verify and report

```bash
ACTUAL="$(git -C "$WORKTREE_PATH" rev-parse HEAD)"
test "$ACTUAL" = "$EXPECTED"
test "$(git -C "$WORKTREE_PATH" branch --show-current)" = "$BRANCH"
test -z "$(git -C "$WORKTREE_PATH" status --porcelain)"
git -C "$ROOT" worktree list --porcelain
```

Report the absolute path, branch, short base SHA, and local setup result.

## Constraints

- Never auto-stash or mutate a dirty primary checkout.
- Never omit the explicit `origin/main` base.
- Never reuse an existing branch or path without explicit intent.
- Never run two worktree creators for one checkout.
- Never commit or push to `main` from the new worktree.

## Related skills

- `wt-close` removes the worktree after merge or explicit abandonment authorization.
- `main-update` performs conservative bulk cleanup after a batch of PRs merges.
