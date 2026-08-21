# Skills

Agent skills I use every day, organized by category. Small, composable, and battle-tested — every rule in them was paid for by a real failure or a real review round, not written speculatively.

The design skill has a live demo: [jackieqin.com](https://jackieqin.com) is built entirely in the 宣纸 language that `xuanzhi-design` teaches.

## Installation

**Claude Code** (as a plugin — updates when this repo does):

```
/plugin marketplace add Jackie-Qin/skills
/plugin install qin-skills
```

**Any agent** (copies editable skill files into your project via [skills.sh](https://skills.sh)):

```bash
npx skills@latest add Jackie-Qin/skills
```

Or just copy any `skills/<category>/<name>/` folder into your agent's skills directory — each skill is self-contained markdown.

## Skills

### productivity

Worktree-based parallel sessions: run many agent sessions on one repo without them stepping on each other, then clean up without losing work. The three skills form one lifecycle.

| Skill | What it does |
| --- | --- |
| [wt-start](./skills/productivity/wt-start/SKILL.md) | Start a task in a fresh worktree based exactly on `origin/main`. Never touches a dirty primary checkout; restores gitignored config the app needs. |
| [wt-close](./skills/productivity/wt-close/SKILL.md) | Close one worktree — only after its PR is proven `MERGED` or abandonment is explicitly authorized. Refuses dirty state; handles the squash-merge `-d`/`-D` dance safely. |
| [main-update](./skills/productivity/main-update/SKILL.md) | The batch sweep. Fast-forwards `main`, removes every merged/stale worktree, deletes gone branches, and cleans the two kinds of remote cruft `git fetch --prune` can never reach — orphaned `pr/*` tracking refs and merged `origin/*` branches auto-delete missed. Asks before touching anything that might be work. |

The shared philosophy: **evidence authorizes destruction.** A `MERGED` PR record, an ancestor-of-main proof, or an explicit user choice — never a guess. When in doubt these skills stop, ask, or report; they never force, never rebase pushed branches, never auto-PR.

**Optional [macos-dev-sandbox](https://github.com/Jackie-Qin/macos-dev-sandbox) integration.** A separate MIT tool of mine for least-authority build isolation on macOS. When its `dev-sandbox` CLI is on `PATH`, `wt-start` seeds a new worktree's Swift-package checkouts from a warm sibling sandbox via APFS copy-on-write, `wt-close` retires that worktree's sandbox state (isolated DerivedData, SPM clones, xcresults, owned simulator clone) before removal, and `main-update` does the same per swept worktree plus a prune backstop for orphaned sandboxes. Every call is gated on `command -v dev-sandbox` and no-ops silently when it's missing — none of the three skills require it.

### ui

| Skill | What it does |
| --- | --- |
| [xuanzhi-design](./skills/ui/xuanzhi-design/SKILL.md) | The 宣纸 (xuan / rice paper) design language: warm paper grounds, subtractive ink, one cinnabar accent, deckled sheets, seal chops, hanging-scroll page structure. Includes deep references on [building paper that reads as paper](./skills/ui/xuanzhi-design/paper.md) and [cutting seals that aren't fake](./skills/ui/xuanzhi-design/seals.md). |
| [zhuanke-seal](./skills/ui/zhuanke-seal/SKILL.md) | Cut a real-looking Chinese seal (印章) from any text: pick text, style (朱文/白文), glyph source (verified public-domain 说文 小篆, or your own seal font), layout, and color. Ships the full pipeline — Commons glyph fetcher with license verification, 篆刻-faithful composition (屈曲填满, 疏密匀称), stone-erosion carving, potrace to a color-agnostic SVG. |

More categories (ux, engineering) will appear as skills graduate from private use.

## Layout

```
skills/
  productivity/
    wt-start/SKILL.md
    wt-close/SKILL.md
    main-update/SKILL.md
  ui/
    xuanzhi-design/
      SKILL.md
      paper.md
      seals.md
    zhuanke-seal/
      SKILL.md
      scripts/
        fetch_glyph.py
        cut_seal.py
```

Each skill is a folder with a `SKILL.md` (frontmatter: `name`, `description`) plus optional reference files the skill links to. This is the standard agent-skills format — it works in Claude Code, and the markdown is portable to any agent that reads skills.

## License

MIT — see [LICENSE](./LICENSE). Hack on them, adapt them, make them your own.
