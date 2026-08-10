<div align="center">

# claude-web-harness

**It asks first. It writes the design first. It blocks you when you break it.**

Harness v3.0.0 · Works with any stack

[한국어](README.md) · [English](README.en.md)

</div>

AI forgets when the conversation ends. The next session's AI doesn't know what was agreed and writes in its own style. Stack enough of that up and nobody can read the code.

Writing "please do it this way" in a document isn't enough. Rules that live only in prose are easy to skip past — for people and for AI.

So this harness doesn't ask nicely. It gets the design out of you first, and a machine measures whether you kept to it. Break it and nothing passes.

## Getting started

```bash
git clone https://github.com/WooriGrunda/claude-web-harness.git my-project
cd my-project
rm -rf .git && git init && git add -A && git commit -m "init"
claude
```

Then say **"set up the harness"**.

It asks one thing during setup: what you're building.

> - Something people use in a browser — they log in, look at screens, press buttons
> - Something other programs call — no screens, just data
> - Something that runs on a schedule — scraping, aggregation, report generation
> - Not sure yet

Answer that and the rest is handled. It picks the tech for you and tells you why, fills in the settings, creates a private GitHub repo and pushes, and finally tells you in plain words what will be blocked from now on.

**You don't need to know any tech names.** It won't ask "FastAPI or Django". "Not sure yet" is a fine answer — it installs the most common setup, and whatever you don't use simply switches itself off.

There are exactly two things you click yourself: the prompt asking whether you trust the new folder, and the one-time consent prompt on that machine. Those are Claude Code's own safeguards; the harness can't remove them.

## What a day looks like

Say "build me a dashboard" and it doesn't start coding.

**It asks.** Which screen this goes on, what data it uses, how far to take it.

**It reads.** It opens the relevant code. Not just filenames — it follows where the data comes from and where it goes.

**It writes.** The design goes into a file. Exact paths, real code snippets, what could break. Blanks like "implement later" or "similar to the above" mean it isn't a design yet. For screens, both the desktop and phone layouts have to be there.

**It stops.** Until you read it and approve. Not one line of code is touched before that.

**It builds.** Following the approved design. Checks run on every save, and violations are blocked on the spot.

**It cleans up.** Related documents get updated and working files are filed away. When it tries to end the conversation, the full check runs again. If anything is left, the conversation doesn't end.

Across one feature you speak twice: answering the questions, and approving the design. Everything between is on its own.

## What gets blocked

Checks run the moment a file is saved. For example:

| Write this | And this happens |
|:--|:--|
| Code that deletes data in a read-only folder | Blocked on the spot |
| A color literal `#ff8800` in a screen file | Colors come from one designated place |
| A fixed width `width: 420px` that breaks phones | Use something that adapts to screen size |
| A file over 400 lines | Split it by feature |
| An API key pasted into code | Route it through settings |
| A file path in a document that doesn't exist | Fix the document |

There are thirty of these. They all run once more when you try to end the conversation, and if a single one fails, the conversation doesn't end.

### Checks that aren't running say so

This is the most important part of the harness.

If a check hasn't been told what it needs, it does not count as passing. It prints this instead:

```
[SKIP] 브라우저 API 직접 호출 — 설정에 브라우저 API 래퍼를 안 적었음
```

That means "this check is currently looking at nothing." It is not a pass.

The previous generation treated that as a pass. So one mismatched folder name left eight checks doing nothing while showing green. **Believing you're protected when you aren't is the most dangerous state of all.**

## Adding it to a project that already has code

Drop this onto an existing codebase and the first run can produce hundreds of findings. At that point people just switch the checks off entirely. That's the usual way tools like this die.

So during setup, **whatever is already broken gets recorded as "was already like this"** and passes. That list never grows. Next time you touch one of those files, fix it and delete its line. Files you create from now on have to pass everything from the start.

If you're copying files instead of cloning, take `kernel/`, `profiles/`, `.claude/`, and `harness_install.py`, then merge just the `hooks` section of `.claude/settings.json`.

## Change anything that doesn't fit

Folder names, which checks are on, the line limit. All of it lives in one file, `harness_profile.py`. It's also the only file you change when moving to another project.

If your project uses an `api/` folder, write `"web": "api"`. If there are no screens, leave the screen entries empty and six screen checks switch off. Decide later to add screens and writing that one line switches them back on.

If the settings and the real folders disagree, the checks catch it. Create code in an undeclared folder and the save is blocked; setup also points it out once. And if something still slips through, the disabled check shows up as `[SKIP]` above.

## Routine maintenance

As a project grows, documents drift from the code, code gets more complicated than it needs to be, and things marked "improve this later" pile up.

**There are no commands to memorize.** The harness keeps count and, when the time comes, tells you at the start of a session and runs the pass itself once your current work is done. Five of them: documents versus code, needlessly complex code, deferred items, screen usability, and whether the metrics and wording make sense to a real user.

They all produce reports and change no code. That's why they run without asking. Whether to act on the findings is a separate decision afterwards. Projects without screens never see the two screen-related ones.

Adjust the intervals in `harness_profile.py`.

## How checks accumulate

The checks weren't designed up front. Each one was added after something went wrong.

When something goes wrong, the account goes into `dev/LESSONS.md` first — what happened and what it cost. A rule on its own gets waved through by the next session as "surely this is an exception", but a rule with a price attached doesn't.

Then you ask whether a machine can check it. If it can, it becomes a check, and from that point the rule isn't a request but a wall. If it can't, you write down "prose only" and why. Write neither and a check catches you, because that's the state of having recorded a problem and deferred the judgment.

So the prose-only list is exactly the queue of checks to build next.

The longer a project runs, the more closely the checks fit the accidents that project actually had. Not somebody else's best practices — the things that happened to us.

## Which model does what

Models come in tiers: the ones that think deeply but cost more, and the fast cheap ones. Judgment goes up, labor goes down, and only summaries come back.

**Opus** designs, judges, and reviews. The more complex a service gets, the harder design becomes. This seat never gets downgraded.

**Fable** implements an approved design end to end. Use it when the judgment is done and what's left is labor. If the design has blanks, it doesn't fill them in — it stops and sends it back.

**Sonnet** takes on reading and cross-checking dozens of files and reports back a summary.

A check enforces this assignment too. Quietly swapping in a cheaper model means the conversation won't end.

## What's inside

| File | Role |
|:--|:--|
| `CLAUDE.md` | AI behavior rules. Read automatically every session |
| `PROJECT.md` | What this project is. Its domain, vocabulary, folder layout |
| `HARNESS.md` | Full map of checks, automation scripts, and specialist AIs |
| `DEVGUIDE.md` · `DESIGN_GUIDE.md` | Server rules → `dev/`, screen rules → `design/` |
| `EDITING.md` | Work board. Keeps parallel sessions off the same files |
| `harness_profile.py` | This project's folder names and vocabulary. The one settings file |
| `harness_install.py` | Setup script |
| `kernel/` | The checking logic. Knows nothing about your project |
| `profiles/` | Setting templates, chosen by what you're building |
| `tests/` | The mechanism that catches the checker itself breaking |
| `.claude/` | Automation scripts, specialist AIs, work procedures |
| `AGENTS.md` · `.agents/` · `.codex/` | For other AI tools (Codex). Claude doesn't read these |

The checking logic knows nothing about your project, and everything project-specific lives in one settings file. "You must not delete data in a read-only folder" is the checker's judgment; which folder that is comes from the settings. That's why the same checker fits any combination of technologies.

Rules that are true only for your project go into `harness_gates/`, not into the checker itself — so the checker never carries somebody else's circumstances around.

## Who checks the checker

`tests/` holds a fake project with exactly one violation planted per check, plus the expected output of checking it.

```bash
python -X utf8 tests/run_golden.py
```

That compares the current result against the expected one. If you're editing the checker and some check quietly weakens, that line shows up immediately.

## Common questions

**Do I really need git?** Yes. The checks use git's list of tracked files to decide what to look at. Without git there's nothing to check, so it blocks with "set up git first" rather than passing.

**Do I have to create the GitHub repo?** It creates it. As long as you're logged in with the `gh` command, it makes a private repository and pushes. The folder name becomes the repository name. Public repositories are hard to undo, so that's the one thing you have to say yourself. If you're not logged in, that's the only time it asks.

**What if what I'm building changes later?** Starting without screens and adding them later is one line of settings. The reverse is the same.

**So what do I actually fill in?** Nothing at setup. Folder names and a few framework function names are needed, and they all get filled in for you.

The only thing you know that it can't is **the knowledge of the field this service operates in**, and that goes in `PROJECT.md`. What it deals with, what vocabulary it uses, which numbers are meaningful. And even that isn't filled in up front — it accumulates as you build.

**Could I turn this into an app later?**

<details>
<summary>Things worth doing up front if your project has screens</summary>

Development here assumes the web. But what carries over to an app and what doesn't is already known, so the parts that carry over are separated from the start.

| Rule | When you move to an app |
|:--|:--|
| Calculation and data shaping live outside screen files | Logic moves as is |
| Colors, spacing, and font sizes only from designated files | Values reused as is |
| Browser-only features go through a single file | Replace that one file |
| Navigation code only at the page level | Minimal replacement surface |

When you need an app, you rebuild only the screens. Server, logic, and design values carry over. If you never build the app, you lose nothing — the separation is good structure on its own.

Screens are only approved once desktop and phone are settled together at the design stage. "Mobile too" after the fact is a rebuild; decided at design time it's just design.

</details>

## Author

Daehyun Kim · [LinkedIn](https://www.linkedin.com/in/daehyun-kim-b00365176/)

MIT License
