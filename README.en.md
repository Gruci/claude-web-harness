<div align="center">

# claude-web-harness

**A guardrail that keeps AI from wrecking your code**

Harness v3.1.0

[한국어](README.md) · [English](README.en.md)

</div>

## Three-line summary

1. When you build with an AI like Claude Code, every new session forgets yesterday's agreements, and the code starts drifting.
2. This tool turns those agreements into **automatic checks** instead of documents — break one, and the save itself is blocked.
3. After install, one sentence ("set up the harness") finishes configuration; from then on the checks run without you thinking about them.

## What is this?

Think of the automatic brakes that stop a car even when a novice driver makes a mistake. This tool is a guardrail for development: the moment the AI writes code that breaks a rule, the save stops and the AI has to fix it.

Talk to an AI long enough and the code tangles. Today's session doesn't know yesterday's agreements, "this is probably fine" piles up, and one day nobody can read the codebase. Writing rules down doesn't stop this — a document is a request, not enforcement. This harness implements rules as **blocking**.

### Before / after

| | Without it | With it |
|:--|:--|:--|
| When the session changes | Yesterday's agreements are forgotten | The same rules are enforced regardless of session |
| When a rule is broken | Nothing happens — a human finds out later | The save is blocked instantly and the AI fixes it |
| Order of work | Implementation starts immediately | No source is touched until you approve a design document |
| "It's done" | May be just words | The session cannot end until every check passes |
| When a check can't run | It silently looks like a pass | It is reported as not-run, with the reason |

### Don't know development? You need this most

A developer notices when the AI writes something strange. If you can't read code, you have no choice but to trust "it's done." Projects built purely on that trust tend to follow one path:

1. The first days feel like magic — features appear as fast as you can describe them.
2. As code piles up, the AI starts tripping over its own work. Fixing one feature breaks another that used to work.
3. One day "add this feature" stops working at all, and rebuilding from scratch becomes faster than repairing. The time and money spent don't come back.

This tool exists to keep stage 2 from ever arriving. It gives you the effect of a code-literate person reviewing every change — done by automatic checks instead. The AI's "it's done" only counts when the checks pass, and until they pass, the session will not end. **You don't need to read the code for the code to stay sound.**

### Use it when

- **You don't know development**, you're building a service with AI, and you worry it might suddenly stop working one day
- You're starting a project **from scratch** with Claude Code and worry the code will drift
- You've already **watched consistency collapse** while collaborating with an AI
- You want "design first, implement after approval" enforced **by a system, not by asking nicely**

It attaches to web services with screens, API-only servers, and batch jobs alike. Languages beyond Python (Go, TypeScript) are supported with a single configuration line.

---

## Start in five minutes

### Step 1 — Get it

```bash
git clone https://github.com/Gruci/claude-web-harness.git my-project
cd my-project
rm -rf .git && git init && git add -A && git commit -m "init"
```

### Step 2 — Install inside Claude Code

```bash
claude
```

Once the session opens, say:

```
set up the harness
```

Onboarding asks a few questions — at the level of "what do you want to build?", not technology names. Answer whether your service has screens, is API-only, or runs on a schedule, and it handles configuration, GitHub connection, and check activation on its own. It's fine if you haven't chosen a stack — recommending one, with reasons, is the tool's job.

### Step 3 — Just develop

```
build me a login feature
```

The AI no longer jumps straight to code. It first writes up a design document showing what it will build and how, and only starts implementing after you approve. During implementation, checks run on every file save, and the AI fixes violations itself. When the session ends, the full check suite runs again — unresolved violations keep the session open.

That's all there is. Everything below is reference material for when you need it.

---

## harness_profile.py — the only file you'll ever edit

Onboarding generates it automatically, so you don't need to open it at first. Later, when the project structure changes, this one file is all you touch.

Why does it exist? The check logic itself knows nothing about your project. It only knows the **shape** of a rule — "a read-only folder must not modify data" — and this file tells it which folder that is. So porting to another project means swapping this file, never editing the checker.

```python
# harness_profile.py — language under inspection (one line brings extensions, idioms, tooling)
LANG = "go"                       # kernel/langs/go.py

# Project shape (one line settles which checks simply do not apply)
# In a service with no screens, screen checks are "not applicable" — not "misconfigured".
ARCH = "backend_only"             # web_layered / backend_only / headless

# Layer path definitions
# Keys are roles the checker knows; values are this project's real paths.
# A value of None puts every check that uses that role into [SKIP].

LAYERS: dict[str, str | None] = {
    "read":      "db/reads",      # Read-only. The write-SQL check watches this
    "write":     "db/writes",     # Mutations only
    "db":        "db",            # Watched by the connection-scope check
    "web":       "api",           # Example of changing the default "web"
    "routes":    "api/routes",    # Update alongside the parent path
    "ui":        "frontend/src",  # None rests the seven screen-related checks
    "tests":     "tests",
    "schema":    "db/schema",
    "shared":    "utils",
    "batch":     "batches",
}
```

If a folder name differs from reality, just change it. When configuration and actual structure disagree, the placement check catches it — there is no path where a renamed folder leaves checks silently idling.

Principal configuration entries:

| Entry | Purpose |
|:--|:--|
| `STAGE` | Project maturity: `greenfield` / `growing` / `mature` |
| `LANG` | Server language. Extensions, idioms, and external tooling follow from it |
| `ARCH` | Project shape. Checks that cannot hold in a project without screens or a web server report `[N/A]` |
| `LAYERS` | Real path per role. Unset roles rest their checks |
| `FILES` · `SYMBOLS` | Framework-specific names such as the settings module and connection helper |
| `SCOPE` | Paths excluded from checking: vendored copies, build output, fixtures |
| `VOCAB` | Forbidden abbreviations and internal terms that must not reach the screen |
| `ALLOWLIST` | Permanent file-level exemptions |
| `DOC_SYNC` | Pairs of values duplicated between documents and code, kept in sync |
| `AGENT_MODEL_POLICY` | Pinned AI model per role |
| `MAINTENANCE` | Thresholds that trigger routine reviews |
| `LOCAL_GATES` | Checks specific to this repository |

---

## How daily development flows

A feature request goes through five stages. You step in at exactly two points: **answering questions** and **approving the design**.

```
[1. Ask & analyze] → [2. Write design] → [3. Await approval] → [4. Implement & check] → [5. Clean up & re-verify]
                                               ▲
                                        where you step in
```

| Stage | What happens | Source changes |
|:--:|:--|:--:|
| 1 | It asks which screens, which data, what scope — and reads the related code to trace data flow | None |
| 2 | It writes the design as a file: exact paths, real code snippets, expected blast radius | None |
| 3 | It waits for your review and approval | None |
| 4 | It implements per the approved design. Checks run on every save | Yes |
| 5 | It updates related documents and cleans up. The full suite runs again at session end | Yes |

A design containing `TBD`, "implement later", or "similar to the above" is not accepted as a design and is sent back. Work that needs a visual draft gets a mockup file under `docs/tasks/mockup/` first, approved before implementation; when the work is done, research, plan, and mockup files are archived together under `docs/tasks/archive/`.

---

## FAQ

**Does it work outside Python?**
Yes. Write `LANG = "go"` and the extensions, idioms, the list of rules that don't hold in that language, and the external tools to delegate to all follow. `python`, `go`, and `typescript` ship built in; any other language needs a `profiles/lang/<name>.py` declaring four items (`EXT`·`PATTERNS`·`NOT_APPLICABLE`·`LINTERS`). Checks that need real parsing are delegated to that language's standard tools — `go vet`·`staticcheck` for Go, `ruff` for Python, `tsc`·`eslint` for TypeScript. A missing tool shows as `[TOOL]` with its install command, never as a pass.

**Can I install before choosing a stack?**
Yes. Onboarding asks about the shape of what you're building, not technology names. Choose "undecided" and the most common configuration is installed, with checks for unused areas resting.

**My service has no screens, yet screen checks keep showing "configuration incomplete".**
Declare `ARCH = "backend_only"` (server only) or `ARCH = "headless"` (no web, no screens). Those checks then report `[N/A]` (nothing to configure in this project shape) instead of `[SKIP]` (configuration left empty). What was lost and what never existed stay distinguishable.

**What if the project's nature changes after install?**
Edit the matching entry in `harness_profile.py`. Adding screens to a project that started without them means switching `ARCH` to `web_layered` and filling in `LAYERS["ui"]`, after which the seven screen-related checks begin collecting targets.

**Can I turn off a check that doesn't fit my project?**
Empty its configuration entry and it moves to `[SKIP]`. The resting state is printed with its reason on every run, though — no setting hides that, on purpose.

**What do I have to write myself?**
At install time, nothing. Folder names and framework function names are handled by onboarding. What only you know is your service's domain knowledge, which accumulates in `PROJECT.md` as development progresses.

**Do I need to create a GitHub repository in advance?**
With `gh` authenticated, a private repository is created and pushed automatically. Public repositories are hard to undo, so one is created only on explicit request. You're asked for a repository address only when authentication is missing.

**Planning to expand to a mobile app later?**

<details>
<summary>App-portability rules for projects with screens</summary>

Current development targets the web. But so that what's reusable is separated from what's disposable ahead of time:

| Rule | At porting time |
|:--|:--|
| Keep computation and data shaping out of screen files | Logic moves as-is |
| Reference colors, spacing, and font sizes only from the canonical file | Values reused as-is |
| Route browser-only features through a single wrapper | Only that file is replaced |
| Keep navigation code in the page layer | Minimal replacement surface |

If an app happens, only the screen layer is rebuilt; server, logic, and design values carry over. If it never happens, nothing is lost — the separation is good structure in its own right.

</details>

---

## Details

From here on is how it works under the hood. None of it is required to use the tool.

### Design principles

| Principle | Implementation |
|:--|:--|
| **Design first** | A design document is written and approved before code. No source changes before approval |
| **Verify at save time** | Static checks run right after each file save; violations block the change and demand a fix |
| **Re-verify at exit** | The full suite reruns when the conversation ends. Unresolved violations keep the session open |
| **Stack-agnostic** | The decision logic knows nothing about the project. Project-specific values live in one configuration file |
| **Unverified is reported as unverified** | A check that can't run due to language or configuration prints `[SKIP]` with a reason, never a pass |

### The six check grades

Splitting "couldn't run" into three distinct reasons is the core of this tool — because what you should do differs for each.

| Grade | Meaning | Your move | Session exit |
|:--|:--|:--|:--:|
| `[OK]` | Ran, no violations | — | Allowed |
| `[SKIP]` | Didn't run — configuration missing | Fill in the config to activate | Allowed |
| `[N/A]` | The rule doesn't hold in this language or project shape | **None — this is not a loss** | Allowed |
| `[TOOL]` | Couldn't run — external tool missing | Install the tool to activate | Allowed |
| `[FAIL]` | Violation detected | Fix it | Blocked |
| `[REPORT]` | Soft signal, false positives possible | Judge for yourself | Allowed |

> **`[SKIP]` is not a pass.** A previous generation of tooling treated it as one — and a single mismatched folder name left eight checks idle while everything reported green.

### What gets caught

Thirty-odd checks run on every file save. The full list and rationale live in `HARNESS.md`. Representative examples:

| Caught | Why, and the fix |
|:--|:--|
| Data-modifying SQL in the read-only layer | Layer responsibility violation. Move mutations to the write layer |
| Hardcoded colors in screen code (`#ff8800`) | Route through the canonical color file or CSS variables |
| Fixed pixel widths (`width: 420px`) | Breaks mobile. Use `max-width`, `%`, `clamp` |
| A file over 400 lines | Lost single responsibility. Split by feature |
| API keys hardcoded in source | Route through the settings module; rotate the key if already committed |
| A documented file path that doesn't exist | Clean up references left after deletes and renames |
| Missing type hints on public functions | Specify the module boundary |
| Agent definition disagreeing with the model policy table | Keeps model assignment aligned with policy |

Checks run at three moments:

| When | Target | On violation |
|:--|:--|:--|
| Right after a file save | That file | Change blocked, fix demanded |
| Session exit attempt | Everything | Exit blocked |
| Manual run (`python -X utf8 -m kernel.runner`) | Everything | Exit code 1 |

### Project layout

```
project-root/
├── harness_profile.py      # Canonical per-project configuration (folders, vocabulary, exemptions)
├── harness_install.py      # Installer and legacy-violation registration
├── CLAUDE.md               # AI behavior rules, auto-loaded each session
├── PROJECT.md              # Service domain, vocabulary, layer structure
├── HARNESS.md              # Full map of checks, hooks, agents, skills
├── DEVGUIDE.md             # Server-side rules (with dev/)
├── DESIGN_GUIDE.md         # Screen design rules (with design/)
├── EDITING.md              # Task board preventing concurrent-session conflicts
├── kernel/                 # Check engine. Knows nothing about the project
│   ├── langs/              # Language packs — per-language declarations
│   └── archs/              # Architecture packs — per-project-shape declarations
├── profiles/               # Configuration presets per project type
├── harness_gates/          # Repository-specific checks (optional)
├── tests/                  # The checker's own regression protection
└── .claude/                # Hooks, agents, skills, session settings
```

The hierarchy is simple: hooks (automatic) call the check engine (`kernel/`), the engine knows only the **shape** of each rule, and `harness_profile.py` supplies the real folders and names. "No write SQL in the read-only layer" lives in `kernel/`; where that layer actually is, the configuration decides.

### Project-type presets

The four types offered at install. Only checks matching the type are activated.

| Type | For | Preset |
|:--|:--|:--|
| Screen-based service | Things used in a browser — logins, dashboards | `web_fastapi_react` |
| API-only service | A backend exchanging data with no screens | `api_fastapi` |
| Batch / automation | Collection, aggregation, reports on a schedule | `batch_python` |
| Undecided | Pre-decision. Installs the common configuration; unused checks rest automatically | `web_fastapi_react` |

Measured on a Go project (regression fixture ships in the repository at `tests/fixtures/goproj`):

| Category | Count |
|:--|:--:|
| Actually performed | 9 |
| `[N/A]` — rule does not hold in this language or project shape | 12 |
| `[TOOL]` — activates once tooling is installed | 3 |
| `[SKIP]` — configuration incomplete | 9 |

Installation state can be inspected with `python -X utf8 harness_install.py --doctor`.

### Manual installation

To install without going through a session:

```bash
python -X utf8 harness_install.py --list                      # List presets
python -X utf8 harness_install.py --preset web_fastapi_react  # Generate configuration
# Adjust folder names in harness_profile.py to the real structure, then
python -X utf8 harness_install.py                             # Register legacy violations and verify
python -X utf8 setup_global_permissions.py                    # Merge global permissions
```

Prerequisites: a Git repository (required — targets are collected via `git ls-files`, so an uninitialized repo neuters every check), a GitHub remote (required — without one, session exit is blocked), Python (required), Node.js (optional — only for UI quality tooling).

### Adopting on an existing project

Legacy code can flood the first run with violations. Left alone, that pressure leads to disabling checks — so the installer **pre-registers violations that existed at adoption time** as exemptions.

| Target | Handling |
|:--|:--|
| Violations that existed at adoption | Registered per (check, file) and excluded |
| A registered file gets edited later | Fix the violation and remove the registration |
| Newly created files | Full checks, no exceptions |

The registration list only shrinks. Cleanup:

```bash
python -X utf8 harness_install.py --dry-run   # Preview registrations
python -X utf8 harness_install.py --prune     # Clear resolved entries
```

### How check rules grow

When an incident or mistake happens, rules grow by this procedure:

| Stage | Action | Artifact |
|:--:|:--|:--|
| 1 | Record what happened and what it cost — cost included, so the next session can't wave it off | `dev/LESSONS.md` |
| 2 | Judge whether it's mechanically detectable | — |
| 3 | If detectable, implement it as a check. Generic rules in `kernel/`, repository-specific ones in `harness_gates/` | Check module |
| 4 | If not, mark it "prose-only" with the reason | `dev/LESSONS.md` |

Doing neither 3 nor 4 is itself caught by a check — it means the judgment was deferred.

### Routine reviews — the tool tells you when

As a project grows, document drift, over-engineering, and unpaid debt accumulate. The tool measures thresholds from the repository itself, decides when reviews are due, and announces them at session start. They run after your current work finishes, produce reports only, and never touch source. Thresholds are tuned in `MAINTENANCE` in `harness_profile.py`.

### AI model division of labor

Model tiers are split by the nature of the work. The assignment itself is checked — if the policy table and the actual assignment disagree, the session won't end.

| Model | Handles | Criterion |
|:--|:--|:--|
| **Opus** | Architecture, judgment, review | Decisions that are expensive to reverse. Never downgraded |
| **Fable** | Full implementation of an approved design | Judgment is done; only volume remains |
| **Sonnet** | Bulk reading and comparison across many files | Narrow judgment, high throughput |

### The checker checks itself

To keep a checker refactor from silently killing a check, the repository carries fixtures with one planted violation per check, plus golden answer files of the expected output.

```bash
python -X utf8 tests/run_golden.py          # Compare against full configuration
python -X utf8 tests/run_golden.py --bare   # Compare against no configuration
```

Any line differing from the answer file is reported. Passing this comparison is the bar for checker refactoring.

---

## Changelog

| Version | Changes |
|:--|:--|
| **v3.1.0** | Introduced the project-shape setting (`ARCH`). In projects without screens or a web server, the corresponding checks are reported as `[N/A]` (not applicable to this project shape) instead of `[SKIP]` (configuration missing). The shape is declared in one line — `web_layered` (screens + server), `backend_only` (server only), or `headless` (no web, no screens) — and works the same way as the language setting (`LANG`). Undeclared, behavior is unchanged. |
| **v3.0.1** | Reworked hook stdin reading to no longer depend on EOF. Windows Claude Code does not send EOF to the `UserPromptSubmit` hook's stdin, so `json.load(sys.stdin)` blocked waiting for EOF and was killed by the 10s hook timeout (output discarded). Every hook now reads through a shared reader (`.claude/hooks/_hookio.py`) that returns as soon as a complete JSON object parses, without waiting for EOF. As a side effect, stdin is now decoded as UTF-8 explicitly, removing potential corruption of non-ASCII payloads under the previous cp949 default decode. Each hook's fail-open / fail-closed policy and the gate decision logic are unchanged. |
| **v3.0.0** | Initial public release. |

---

## License & author

Daehyun Kim · [LinkedIn](https://www.linkedin.com/in/daehyun-kim-b00365176/)

MIT License
