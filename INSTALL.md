# Installing these skills in any agent harness

This repo is a **portable skill library**: 73 skill directories, each a
`<name>/SKILL.md` with YAML frontmatter (`name`, `description`, `version`) and
an RFC-style body, plus a root `AGENTS.md` router that maps task types to
skills. It works in any harness — opencode, Claude Code, Codex, Cursor,
aider, Windsurf, or a plain chat window.

Do not hand-install. Paste the prompt below into your coding agent and let it
do the wiring. Replace `<REPO_PATH>` with the absolute path where you cloned
this repo (e.g. `~/skills`).

---

## Paste this into your agent

```text
I am giving you an agent skill library at <REPO_PATH> (cloned from
github.com/BradMyrick/kodr-skills). Make it available to me in THIS harness.

WHAT THE LIBRARY IS
- <REPO_PATH>/AGENTS.md is a router: engineering principles plus a table that
  maps task types (rust, blockchain, dist, ai, cs, security, devops) to skill
  names.
- Each skill is a directory <REPO_PATH>/<skill-name>/SKILL.md with YAML
  frontmatter (name, description, version) and an RFC-style spec body.
- 73 skills total. The directory name equals the frontmatter name.

YOUR JOB — do these steps in order, narrating each one:

1. IDENTIFY your harness's mechanisms (state what they are before touching
   anything):
   a. Always-on instructions: how this harness loads persistent context
      (e.g. AGENTS.md at project root, CLAUDE.md, .cursor/rules,
      .codex/AGENTS.md, opencode.json "instructions", or equivalent).
   b. On-demand skills: whether this harness supports skill/plugin
      directories containing SKILL.md files that are loaded when needed
      (opencode, Claude Code, and agents.md-compatible harnesses do).

2. WIRE THE ROUTER (instructions layer):
   - If this harness auto-loads AGENTS.md from the project root, copy or
     symlink <REPO_PATH>/AGENTS.md content into the location this harness
     uses. If an instruction file already exists, APPEND the router section
     to it — never overwrite existing content.
   - If this harness has no instruction mechanism, say so and skip; the
     fallback in step 4 covers it.

3. WIRE THE SKILLS (on-demand layer):
   - If this harness supports skill directories, point its config at
     <REPO_PATH> (or copy/symlink the skill directories into the harness's
     skills location — prefer a symlink so updates via git pull propagate).
   - Exclude no skills; all 73 are meant to be available.

4. FALLBACK (only if step 3 found no skill mechanism): paste the full
   content of <REPO_PATH>/AGENTS.md into this harness's instruction file
   (or into our conversation if none exists) and follow its routing rule:
   when a task matches a router line, read that <skill-name>/SKILL.md from
   <REPO_PATH> before designing or implementing.

5. VERIFY before reporting done:
   - List or count the skills now visible to the harness (expect 73).
   - Demonstrate routing: load the SKILL.md for `rust-testing` (or ask me
     for a task that triggers a router match) and quote its first heading.

HARD RULES
- Never delete, overwrite, or truncate any existing config or instruction
  file. Append or merge only, and save a timestamped backup (.bak-<date>)
  beside every file you modify.
- Do not modify anything inside <REPO_PATH>; it is a read-only library.
- Do not invent harness features. If something is unsupported, say so and
  use the fallback instead of pretending.
- Report every file you created, modified, or backed up, with paths.

Begin with step 1 now.
```

---

## Notes for humans

- **Updating**: if you symlinked, `git pull` inside the clone is the whole
  update. If you copied, re-run the same prompt with "resync my skills from
  <REPO_PATH>".
- **opencode users**: no prompt needed — add the repo to `opencode.json`:

  ```json
  {
    "$schema": "https://opencode.ai/config.json",
    "instructions": ["~/.skills/AGENTS.md"],
    "skills": { "paths": ["~/.skills"] }
  }
  ```

  (Adjust the path to your clone. The `skill` tool then loads skills
  on-demand, routed by frontmatter `description`.)
- **Skill format compatibility**: the `SKILL.md`-with-frontmatter format
  matches the cross-agent skills convention, so harnesses that support
  agent skills load these natively.
