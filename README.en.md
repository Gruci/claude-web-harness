<div align="center">

# claude-web-harness

**It asks first. It writes the design. Break a rule and it stops.**

FastAPI · PostgreSQL · React &nbsp;·&nbsp; Harness v2.3.0

[한국어](README.md) · [English](README.en.md)

</div>

An AI forgets when the conversation ends. The next session's AI has no idea what was agreed and rewrites things its own way. That piles up into code nobody can read.

Writing "please do it this way" in a document does not hold. People and AIs alike skip rules that live only in prose.

So this harness does not ask. It extracts a design first, then measures whether the rules were kept. Break one and nothing goes through.

This repository is that distribution copy. Drop it into any project and the install below is all you need.

## How it runs

Say "build me a dashboard" and the AI does not start coding.

**It asks.** Which screen, what data, how far to go.

**It reads.** The relevant code, directly. Not just filenames. Where the data comes from and where it goes.

**It writes.** A design document, saved as a file. Exact paths, real code fragments, what could break. If it contains "implement later" or "similar to the above," it is not a design document. For screen work it must show both the desktop and the phone layout.

**It stops.** Until you read it and approve. Not one line of code has been touched yet.

**It builds.** To the approved design. Every save triggers a check, and a violation blocks on the spot.

**It cleans up.** Updates the related documents, clears the working files. When it tries to end the conversation the full check runs again. One violation left and the conversation does not end.

You speak twice. Answering the questions, and approving the design.

## Install

```bash
# 1. Clone and re-initialize as a new repo. Without git, no checks run.
git clone https://github.com/Gruci/claude-web-harness.git my-project
cd my-project
rm -rf .git && git init && git add -A && git commit -m "init"

# 2. Install script. Records current issues in existing code as already-known.
python harness_install.py

# 3. Permissions and the GitHub remote.
python setup_global_permissions.py
gh repo create my-project --private --source . --push

# 4. Run.
claude
```

To add it onto an existing project, copy the files instead of cloning and merge only the hooks in `.claude/settings.json`.

**Existing code will not blow up all at once.** The install script records what is already there. That list only shrinks. Any new file must pass everything from the start.

**git and the remote are not optional.** The checks run against the list of files git manages. Without git no checking is possible, so the harness does not pass you; it blocks and tells you to run git init. Without a remote your code lives on one machine only, so the conversation cannot end until one is connected.

You click exactly two things. Trusting a new folder, and agreeing to danger mode the first time on that machine. Those are Claude Code's own safeguards and the harness cannot remove them.

## Usage

Ask in plain language. Nothing to memorize.

```
build me a dashboard page
fix this bug
add an API
```

If a request needs both the server and the screen, both workers run at once and the data they hand each other is checked for a match.

## How the harness grows

The gates were not designed up front. One was added each time something went wrong.

When something goes wrong, the incident goes into `dev/LESSONS.md` first: what happened and what it cost. A rule on its own gets waved through next session as "surely this one is an exception." A rule with a price tag attached does not.

Then you ask whether a machine can check it. If it can, it becomes a gate, and from then on the rule is a block rather than a request. If it cannot, you write "prose only" and say why. Write neither and a check catches you, because that is an incident recorded with the decision postponed.

So the list of prose-only entries is the list of candidates for the next gate.

The longer a project runs, the more the harness fits that project's actual failures. It fills up with what bit you, not with someone else's best practices.

## What is inside

**28 gates.** Checks that run on save and when the conversation ends. 400 lines per file, naming, no code outside the declared folders, no colour literals in screen files, no fixed widths that break phones, whether paths written in documents actually exist, even which model handles which task. All on from the start. Tuning happens in one place, `harness_config.py`.

**Hooks.** Scripts that fire at set moments. Right after a save, just before the conversation ends, at session start. They live in `.claude/hooks/`, and `.claude/settings.json` decides what runs when.

**Agents.** Workers dedicated to one area. Server, screen, verification. Each reads its own rulebook before working. They live in `.claude/agents/`.

**Skills.** Bundled sequences for common work. "Build a feature" turns on the whole sequence from interview to cleanup. They live in `.claude/skills/`.

**Documents.** Where the rules and this project's own knowledge accumulate. The AI reads `CLAUDE.md` automatically every session. The full map is `HARNESS.md`, the server rules `DEVGUIDE.md`, the screen rules `DESIGN_GUIDE.md`.

## Layers

```text
Human
 └─ Claude Code session
     ├─ Skills
     ├─ Agents
     └─ Hooks
         └─ static_check.py
             └─ harness_config.py
```

Each layer enforces the one above it. A human can break a rule and a hook still stops it, and one settings file decides what the hooks stop. That is also why porting to another project means editing one file, `harness_config.py`.

## Cost

Models come in tiers. Deep but expensive, or fast and cheap. Judgment goes up, labour goes down, and only summaries come back.

**Opus** designs, judges, reviews. The more complex the service, the harder the design. This seat is never downgraded.

**Fable** implements an approved design end to end. Judgment is done; what is left is hands.

**Sonnet** splits up reading and comparing dozens of files and sends only the summary back.

A gate guards this assignment too. Quietly swap in a cheaper model and the conversation will not end. And when Fable takes a big job, it does not fill in blanks itself. It stops and hands the decision back.

## Mobile and apps

A screen is approved only after the desktop and phone layouts are fixed together at design time. Asking for mobile after the fact is a rebuild; deciding it at design time is just design. The common causes of broken phone layouts are blocked the moment you save, and nothing is called done before it survives 390px.

Development today is 100% web. But what carries over to an app and what gets thrown away is already known, so the parts that carry over are separated from the start.

| Rule | When moving to an app |
|:--|:--|
| Calculation and data shaping live outside screen files | Logic moves as-is |
| Colours, spacing, font sizes live in a constants file | Values reused as-is |
| Browser-only features go through a single file | Replace that one file |
| Navigation code lives only at the page level | Minimal replacement scope |

When an app is needed you rebuild the screens only. The server, the logic, and the design values come along. Never building an app costs nothing either. The separation is good structure on its own.

## Occasional commands

Ignore these day to day. Roughly monthly, they only produce reports and never touch code.

| Command | What it does |
|:--|:--|
| `MD 감사해줘` ("audit the docs") | Find where documents disagree with the code |
| `/lazy-audit` | Find needlessly complex code |
| `/lazy-debt` | Collect the spots marked "simple for now, improve later" |
| `/impeccable critique` | Screen usability |
| `/impeccable audit` | Accessibility, load speed, behaviour per screen size |
| `검수 돌려줘` ("run a review") | Whether the metrics and wording make sense to a real user |

## Files

| File | Role |
|:--|:--|
| `CLAUDE.md` | AI behaviour rules. Read automatically every session |
| `HARNESS.md` | Full map of hooks, agents, skills, gates |
| `DEVGUIDE.md` | Server rules → `dev/` |
| `DESIGN_GUIDE.md` | Screen design rules → `design/` |
| `EDITING.md` | Work board. Keeps parallel sessions from colliding |
| `harness_config.py` | Single point for project settings |
| `harness_install.py` | Install script |
| `static_check.py` | The checker core |
| `.claude/` | Hooks, agents, skills, settings |
| `AGENTS.md` · `.agents/` · `.codex/` | For a different tool (Codex). Claude does not read these |

## FAQ

**My stack is different.** Edit the stack line at the top of `CLAUDE.md` together with `harness_config.py`. If it differs a lot, adjust the affected checks too.

**I want to rename folders.** Go ahead. They are set at the top of `harness_config.py`. If your repo uses `api/`, change `WEB_PREFIX` to `"api/"` and the sub-paths (`routes`, `static`) follow, because they are derived. Only touch the parent.

If the declaration and the repo disagree, a gate catches it. Put app code in an undeclared folder and the save is blocked, and the install script points out undeclared code folders once up front.

**A check does not fit us.** Turn it off in `ENABLED` in `harness_config.py`. Limits like the line count live in the same file.

**What do I fill in on a new project?** The stack line, the layer folder names, brand colours, and the reviewer's personality. All of it lives in `harness_config.py` and a few lines of docs, and you set it once. Keeping to it afterwards is the gates' job. Beyond that, what a person fills in is knowledge about the field this service belongs to: what it deals with, what terms it uses, which numbers matter. And that is not filled in up front either; it accumulates in the documents as you build.

## Author

Daehyun Kim · [LinkedIn](https://www.linkedin.com/in/daehyun-kim-b00365176/)

MIT License
