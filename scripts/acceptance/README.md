# Local acceptance of content review and learning

`run_local.py` starts owned loopback services on available ports, creates a temporary SQLite database, generates temporary fixture credentials, runs the browser workflow and stops its services. It never uses the configured project database, publishes anything, or recruits participants. The database is removed after the run; logs, result JSON and screenshot remain in the chosen output directory.

Requirements: the project's backend dependencies in a Python environment, installed frontend dependencies, Playwright available to Node, and an existing compatible Chromium browser. Reuse working dependencies. Example on this host:

```sh
/Users/mac/.codex/skill-envs/learnflow-review/bin/python scripts/acceptance/run_local.py \
  --python /Users/mac/.codex/skill-envs/learnflow-review/bin/python \
  --node /Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  --node-path /Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
  --chrome '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --output /tmp/learnflow-content-acceptance
```

The workflow creates two teacher items through the UI, confirms that pending items cannot be delivered, approves one and rejects the other through the admin UI, checks persisted decisions and answer masking, then verifies `/student/learn` correct/wrong grading, visible tutorial, retry, a failed submission and task-load failure recovery without an unhandled Promise rejection. It forces only the next-task request's topic to the fixture topic; selection, approval and grading are performed by the actual backend. This isolates content selection while preserving the real UI and service path.

This is technical acceptance using fictional accounts. It does not measure learning benefits, model calibration, security of every endpoint or production deployment readiness. See the separately recorded `/learn` and four-role homepage checks for those covered routes. The runner assumes the existing seed fixture email identities and a POSIX host; it is not a production startup script.

`verify_k12_import.py --output /tmp/k12-import-check` independently imports every current numeric/no-image compatible XES item into a disposable database twice, verifies that all remain unapproved and that the second import does not duplicate them, records source hashes and removes the database. Run it with the backend Python environment. This checks importer behavior, not mathematical rendering, item accuracy or calibrated difficulty.

## Formula syntax and display

Run `node scripts/acceptance/audit_math_render.cjs results/k12/math_render_audit_20261008.json` after installing the frontend's locked dependencies. It checks delimited formula parsing against the full numeric-format subset and records warnings, source-content review flags and source hashes. The browser workflow also checks fraction markup in both ordinary learning routes and horizontal layout on a 390px viewport. Formula rendering does not reconstruct tables already flattened in source metadata or support the bank's image/multiple-answer items.

KaTeX is pinned in the frontend lockfile. Text remains escaped by React, unsupported expressions retain their source, external-content commands are disabled, and macros are not shared across formulas. Configuration follows [KaTeX API](https://katex.org/docs/api.html) and [options](https://katex.org/docs/options.html).

## Due reviews

Use the same `run_local.py` command with `--scenario reviews`. The runner inserts one explicitly fictional, overdue review in its own temporary database after startup, so this checks scheduling behavior without waiting a day or modifying the project database. The browser follows the student homepage link, checks formula rendering, injects a failed submission, retries with a real answer, reads feedback/explanation, rejects a second submission and confirms the due count and persisted attempt count. A fixed scheduling rule is not an independently fitted forgetting curve or evidence of learning benefit.
