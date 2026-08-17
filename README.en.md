<div align="center">

# claude-web-harness

**Design first · Machine enforced · Stack agnostic**

Harness v3.0.1

[한국어](README.md) · [English](README.en.md)

</div>

`claude-web-harness` is an automated validation tool that prevents context loss and code quality degradation during developer–AI collaboration. It enforces an agreed design up front and maintains code consistency through checks that run at save time.

The language under inspection is set by a single configuration line (`LANG`). Extensions, idiom patterns, and external tooling follow from it, so adding a language never requires editing the checker itself. Checks that cannot run are never treated as passing — they are reported with a reason.

## Table of contents

1. [Overview](#1-overview)
2. [Quick start](#2-quick-start)
3. [Daily workflow](#3-daily-workflow)
4. [Validation rules](#4-validation-rules)
5. [Project structure and configuration](#5-project-structure-and-configuration)
6. [Maintenance and scaling](#6-maintenance-and-scaling)
7. [FAQ](#7-faq)

---

## 1. Overview

When an AI session ends, previously agreed conventions and coding style are lost. The next session generates code on its own judgment without that context, and the accumulated divergence eventually breaks the consistency of the codebase.

Recording rules in documents alone provides no enforcement. Conventions written as prose are easy to bypass, for both people and AI. This harness implements rules as **blocks**, not requests.

### 1.1 Design principles

| Principle | Implementation |
|:--|:--|
| **Design first** | A design document is written to a file and approved before any code. No source changes occur before approval |
| **Save-time validation** | Static checks run immediately after a file is saved; violations block the change and require a fix |
| **Exit-time revalidation** | The full check re-runs when the conversation tries to end. Unresolved violations prevent the session from closing |
| **Stack agnostic** | The checking logic has no knowledge of the project. Project-specific values are isolated in a single configuration file |
| **Unverified reported as unverified** | A check that cannot run — because of language or missing configuration — is reported as `[SKIP]` with a reason, never as a pass |

### 1.2 Check statuses

Results are reported in six grades. Splitting "could not run" into three distinct reasons is the core design element of this tool — the action required differs in each case.

| Grade | Meaning | Session exit |
|:--|:--|:--:|
| `[OK]` | Check ran, no violations | Allowed |
| `[SKIP]` | Not performed — required configuration is missing | Allowed |
| `[N/A]` | The rule does not hold in this language | Allowed |
| `[TOOL]` | External tooling absent, so the check cannot run | Allowed |
| `[FAIL]` | Violation detected | Blocked |
| `[REPORT]` | Soft signal with false-positive potential. Not counted in totals | Allowed |

> **`[SKIP]` is not a pass.** It means the check is inactive due to missing configuration. Previous-generation tooling treated this state as a pass, so a single mismatched folder name left eight checks inert while returning a green signal.

---

## 2. Quick start

### 2.1 Installation

```bash
# 1. Clone and enter the repository
git clone https://github.com/WooriGrunda/claude-web-harness.git my-project
cd my-project

# 2. Reset git history and make the initial commit
rm -rf .git && git init && git add -A && git commit -m "init"

# 3. Launch Claude Code
claude
```

Then instruct the session:

```
set up the harness
```

The onboarding procedure identifies the project type, generates the configuration file, connects the remote repository, and reviews any inactive checks.

### 2.2 Project type selection

One of four types is selected during setup. Only the checks relevant to that type are activated.

| Type | Target | Preset applied |
|:--|:--|:--|
| Screen-based service | Applications used in a browser — login, dashboards, interaction | `web_fastapi_react` |
| API-only service | Backend that exchanges data with no screens | `api_fastapi` |
| Batch / automation | Scheduled work such as scraping, aggregation, report generation | `batch_python` |
| Undecided | Pre-decision stage. Installs the most common configuration; unused checks stay inactive | `web_fastapi_react` |

No prior knowledge of stack names is required. Onboarding asks about the shape of the deliverable; selecting the stack and explaining the rationale is the tool's responsibility.

### 2.3 Manual installation

To install without going through a session:

```bash
python -X utf8 harness_install.py --list                      # List presets and their purpose
python -X utf8 harness_install.py --preset web_fastapi_react  # Generate the configuration file
# After adjusting folder names in harness_profile.py to match the real structure
python -X utf8 harness_install.py                             # Register existing violations and verify
python -X utf8 setup_global_permissions.py                    # Merge global permissions
```

### 2.4 Prerequisites

| Item | Required | Reason |
|:--|:--:|:--|
| Git repository | Yes | The check target list is collected via `git ls-files`. Without it the target set is empty and every check is inert |
| GitHub remote | Yes | Session exit is blocked while unset. With `gh` authenticated, a private repository is created automatically |
| Python | Yes | Runtime for the checker |
| Node.js | Optional | Needed only for the UI quality tooling |

---

## 3. Daily workflow

Feature additions and changes proceed through five stages. The developer is involved at two points: **answering questions** and **approving the design**.

```
[1. Ask & analyze] → [2. Write design] → [3. Await approval] → [4. Build & check] → [5. Clean & revalidate]
                                                 ▲
                                        developer involvement
```

| Stage | Activity | Source changes |
|:--:|:--|:--:|
| 1 | Asks which screen, which data, and how far to take the work. Reads the relevant code directly to analyze data flow and module dependencies | None |
| 2 | Writes the design to a file: exact paths, real code snippets, expected blast radius | None |
| 3 | Waits for developer review and approval | None |
| 4 | Implements per the approved design. Checks run on every save | Yes |
| 5 | Updates related documents and files away working artifacts. Re-runs the full check at exit | Yes |

### 3.1 Design document requirements

An artifact missing any of the following is not accepted as a design, and stage 2 is rejected.

- Exact file paths with a single-responsibility statement per file
- Real code snippets (pseudocode is not accepted)
- Breaking changes and trade-offs stated explicitly
- For screen work, a responsive layout table covering both desktop and mobile
- No unresolved placeholders such as `TBD`, "implement later", or "similar to the above"

---

## 4. Validation rules

Thirty-two checks run at file save time. On detection, the change is blocked and a fix is requested. The full list and the rationale for each are defined in `HARNESS.md`.

### 4.1 Representative rules

| Violation | Reason and remedy |
|:--|:--|
| Data-modifying SQL in a read-only layer | Layer responsibility violation. Move write operations to the write layer |
| Hard-coded color literal in screen code (`#ff8800`) | Restricted to the color source file or CSS variables |
| Fixed pixel width (`width: 420px`) | Mobile viewport support. Replace with `max-width`, `%`, or `clamp` |
| Single file exceeding 400 lines | Single responsibility lost. Split by feature |
| API keys or credentials hard-coded in source | Route through the settings module. If already committed, key rotation is required |
| File path stated in a document does not exist | Document–code synchronization. Remove stale references after deletion or rename |
| Missing type hints on public functions | Module interface specification |
| Agent definition inconsistent with the model policy table | Prevents model routing drift |

### 4.2 Reviewing inactive checks

Checks not performed due to missing configuration are reported with their reason.

```
[SKIP] 브라우저 API 직접 호출 — 설정에 브라우저 API 래퍼를 안 적었음
[SKIP] DDL 저장 타입 잘림 — 설정에 schema 폴더를 안 적었음
```

If the check is relevant to the project, populate the corresponding entry in `harness_profile.py` to activate it. If it is genuinely inapplicable — UI checks in a service with no screens, for example — leave it inactive; the inactive state continues to be reported on every run.

### 4.3 Execution points

| Point | Scope | On violation |
|:--|:--|:--|
| Immediately after file save | That file | Change blocked, fix requested |
| Attempted session exit | Full | Session exit blocked |
| Manual run (`python -X utf8 -m kernel.runner`) | Full | Exit code 1 |

---

## 5. Project structure and configuration

### 5.1 Directory layout

```
project-root/
├── harness_profile.py      # Project configuration source (folder names, vocabulary, exemptions)
├── harness_install.py      # Setup and existing-violation registration script
├── CLAUDE.md               # AI behavior rules. Stack-agnostic skeleton, auto-loaded each session
├── PROJECT.md              # Service domain, vocabulary, layer structure
├── HARNESS.md              # Full map of checks, hooks, agents, and skills
├── DEVGUIDE.md             # Server development rules (paired with dev/)
├── DESIGN_GUIDE.md         # Screen design rules (paired with design/)
├── EDITING.md              # Work board preventing concurrent-session conflicts
├── kernel/                 # Checking engine. No knowledge of the project
├── profiles/               # Configuration presets by project type
├── harness_gates/          # Checks specific to this repository (optional)
├── tests/                  # Regression fixtures and expected output for the checker itself
└── .claude/                # 14 hooks, 6 agents, 10 skills, session configuration
```

### 5.2 Layer structure

```
User
 └─ Claude Code session
     ├─ Skills (work procedures)
     ├─ Agents (domain specialists)
     └─ Hooks (automation)
         └─ kernel/ (checking logic — project agnostic)
             └─ harness_profile.py (project-specific values)
```

Lower layers enforce upper ones. The checking logic holds only the **shape** of a rule; the target that rule applies to is designated by the configuration file. For example, the judgment "no write SQL in a read-only layer" lives in `kernel/`, while that layer's actual path is defined in `harness_profile.py`.

### 5.3 Configuration

When porting to another project, `harness_profile.py` is in principle the only file to modify.

```python
# harness_profile.py — language under inspection (one line brings extensions, idioms, tooling)
LANG = "go"                       # kernel/langs/go.py

# Layer path definitions
# Keys are roles the checker knows; values are this project's real paths.
# A value of None puts every check that uses that role into [SKIP].

LAYERS: dict[str, str | None] = {
    "read":      "db/reads",      # Read-only. Target of the write-SQL check
    "write":     "db/writes",     # Mutations only
    "db":        "db",            # Target of the connection-scope check
    "web":       "api",           # Example of changing the default "web"
    "routes":    "api/routes",    # Update alongside the parent path
    "ui":        "frontend/src",  # None disables 7 screen-related checks
    "tests":     "tests",
    "schema":    "db/schema",
    "shared":    "utils",
    "batch":     "batches",
}
```

Principal configuration entries:

| Entry | Purpose |
|:--|:--|
| `STAGE` | Project maturity: `greenfield` / `growing` / `mature` |
| `LAYERS` | Real path per role. Undeclared roles disable their checks |
| `FILES` · `SYMBOLS` | Framework-specific names such as the settings module and connection helper |
| `SCOPE` | Excluded paths: vendored copies, build output, fixtures |
| `VOCAB` | Forbidden abbreviations and screen-facing terminology |
| `ALLOWLIST` | Permanent file-level exemptions |
| `DOC_SYNC` | Pairs of values duplicated between documents and code |
| `AGENT_MODEL_POLICY` | Fixed model and effort per role |
| `MAINTENANCE` | Trigger thresholds for routine reviews |
| `LOCAL_GATES` | Repository-specific checks to enable |

> Mismatches between configuration and the real structure are detected by the placement check. Creating application code in an undeclared folder is blocked at save time, and the setup script reports out-of-scope code folders once.

### 5.4 Model role delegation

Model tiers are separated by the nature of the work. This assignment is itself a check: if the policy table and agent definitions disagree, the session will not close.

| Model | Responsibility | Assignment criterion |
|:--|:--|:--|
| **Opus** | Architecture, judgment, review | High-cost-to-reverse decisions. Never downgraded |
| **Fable** | Full implementation of an approved design | Judgment complete, volume remaining. Halts and returns the design if it contains unresolved items |
| **Sonnet** | Multi-file reading and cross-checking | Narrow judgment, high throughput. Returns summaries only |

---

## 6. Maintenance and scaling

### 6.1 Adopting into an existing project

Introducing the harness to a legacy codebase can surface a large number of violations on the first run. Left unaddressed, this leads to disabling the checks entirely, so the setup script **registers violations present at adoption time as exempt**.

| Target | Handling |
|:--|:--|
| Violations already present at adoption | Registered per `(check, file)` and excluded |
| When a registered file is later modified | Fix the violation and delete its entry |
| Newly created files | Must pass every check with no exceptions |

The registry is monotonically decreasing. Completed items are harvested with:

```bash
python -X utf8 harness_install.py --dry-run   # Preview what would be registered
python -X utf8 harness_install.py --prune     # Remove entries that are now fixed
```

Commit the generated registry. The state must be shared across sessions and machines for the monotonic decrease to hold.

### 6.2 Adding a check

When an incident or mistake occurs, add a rule through the following procedure.

| Stage | Activity | Artifact |
|:--:|:--|:--|
| 1 | Record the incident and what it cost. A bare rule invites the next session to treat it as an exception; a recorded cost does not | `dev/LESSONS.md` |
| 2 | Determine whether it is machine-detectable | — |
| 3 | If detectable, implement it as a check. General rules go in `kernel/`, repository-specific ones in `harness_gates/` | Check module |
| 4 | If not detectable, record `prose only` with the reason | `dev/LESSONS.md` |

Recording neither stage 3 nor stage 4 is itself caught by a check, because that is the state of having logged a problem and deferred the judgment. As a result, the prose-only list is the queue of checks to implement next.

### 6.3 Routine reviews

As a project grows, document–code divergence, over-engineering, and deferred work accumulate. The tool measures thresholds from the repository itself and decides when a review is due; no command input is required.

| Review | Measurement |
|:--|:--|
| Document–code divergence | Commits or days since last run |
| Over-engineering and complexity | Commits or days since last run |
| Deferred work | Count of remaining markers in source |
| Screen usability | Number of changed screen files |
| User-perspective review | Number of changed screen files |

When a threshold is exceeded it is reported at session start and runs automatically once current work completes. All reviews produce reports and change no source, so they require no approval. Projects with no screen layer are excluded from the two screen-related reviews.

Thresholds are adjusted in the `MAINTENANCE` entry of `harness_profile.py`.

### 6.4 Validating the checker itself

To prevent a check from being silently disabled during checker maintenance, the repository holds a fixture with exactly one violation planted per check, plus the expected output of checking it.

```bash
python -X utf8 tests/run_golden.py          # Compare against the full-configuration baseline
python -X utf8 tests/run_golden.py --bare   # Compare against the no-configuration baseline
```

Differences between the current output and the baseline are reported line by line. This comparison is the acceptance criterion for any checker refactor.

---

## 7. FAQ

**Can I use this with a language other than Python?**
Yes. Write `LANG = "go"` in the configuration and the extensions, idiom patterns, list of rules that do not apply to that language, and the external tooling to delegate to all follow from it. `python`, `go`, and `typescript` ship with the harness; any other language needs a `profiles/lang/<name>.py` declaring four items — `EXT`, `PATTERNS`, `NOT_APPLICABLE`, `LINTERS`.

Checks that require syntax analysis are delegated to that language's standard tooling: `go vet` and `staticcheck` for Go, `ruff` for Python, `tsc` and `eslint` for TypeScript. When a tool is absent the check is marked `[TOOL]` rather than passing, and the install command is printed alongside.

Measured on a Go project (the regression fixture ships in the repository at `tests/fixtures/goproj`):

| Category | Count |
|:--|:--:|
| Actually performed | 9 |
| `[N/A]` — rule does not hold in Go | 3 |
| `[TOOL]` — activates once tooling is installed | 4 |
| `[SKIP]` — configuration incomplete | 16 |

Installation state can be inspected with `python -X utf8 harness_install.py --doctor`.

**Can I install without having decided on a stack?**
Yes. Onboarding asks about the shape of the deliverable, not technology names. Selecting "undecided" installs the most common configuration, and checks for unused areas remain inactive.

**What if the nature of the project changes after installation?**
Modify the corresponding entry in `harness_profile.py`. Adding screens to a project that started without them means filling in `LAYERS["ui"]`, after which seven screen-related checks begin collecting targets. Two of them — screen terminology and the browser API wrapper — require additional configuration.

**Can a specific check be disabled if it does not suit the project?**
Emptying the corresponding configuration entry moves it to `[SKIP]`. Note that the inactive state is printed with its reason on every run; no setting suppresses that output.

**What does the developer need to write?**
Nothing at installation. Folder names and framework function names are handled by the onboarding procedure. The only information unique to the developer is domain knowledge for the service, recorded in `PROJECT.md` — what it deals with, what vocabulary it uses, which value ranges are meaningful. That accumulates during development rather than being written up front.

**Do I need to create the GitHub repository beforehand?**
If `gh` is authenticated, a private repository is created and pushed automatically, named after the directory. Public repositories are difficult to reverse, so they are created only on explicit request. The repository address is requested only when authentication is absent.

**Is preparation needed for a future mobile app?**

<details>
<summary>App-portability rules for projects that include screens</summary>

Development assumes the web. However, what carries over to an app and what does not is known in advance, so portable parts are separated from the start.

| Rule | On porting |
|:--|:--|
| Calculation and data shaping live outside screen files | Logic moves as is |
| Colors, spacing, and font sizes referenced only from source files | Values reused as is |
| Browser-only features go through a single wrapper | Only that file is replaced |
| Navigation code confined to the page layer | Minimal replacement surface |

When an app becomes necessary, only the screen layer is reimplemented; server, logic, and design values carry over. Nothing is lost if the app is never built — the separation is sound structure on its own.

Screens are approved only when desktop and mobile layouts are settled together at the design stage.

</details>

---

## Changelog

| Version | Changes |
|:--|:--|
| **v3.0.1** | Reworked hook stdin reading to no longer depend on EOF. Windows Claude Code does not send EOF to the `UserPromptSubmit` hook's stdin, so `json.load(sys.stdin)` blocked waiting for EOF and was killed by the 10s hook timeout (output discarded). Every hook now reads through a shared reader (`.claude/hooks/_hookio.py`) that returns as soon as a complete JSON object parses, without waiting for EOF. As a side effect, stdin is now decoded as UTF-8 explicitly, removing potential corruption of non-ASCII payloads under the previous cp949 default decode. Each hook's fail-open / fail-closed policy and the gate decision logic are unchanged. |
| **v3.0.0** | Initial public release. |

---

## License and author

Daehyun Kim · [LinkedIn](https://www.linkedin.com/in/daehyun-kim-b00365176/)

MIT License
