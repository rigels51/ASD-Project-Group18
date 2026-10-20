# Release 2 testing evidence (read by the agentic-loop Testing Review)

Every student puts two files here. One person then runs the Testing Review for the whole group.

| File | What it proves | How to make it |
|---|---|---|
| `student-<n>-precommit.txt` | Pre-commit security scans (Ruff security rules, detect-secrets, pip-audit) ran on **your** code | `python3 scripts/capture_test_evidence.py precommit --student <n>` |
| `student-<n>-ci.md` | Your `student-x.yml` ran green on GitHub and tested **2 endpoint functions** of your backend | `python3 scripts/capture_test_evidence.py ci --student <n> --endpoints "GET /x; POST /x"` |

## 1. One-time setup (each student)

```bash
python3 -m pip install pre-commit
pre-commit install            # from the repo root - scans now run on every `git commit`
```

To check that the hooks run, make any commit. You'll see three lines: `Ruff security rules`, `detect-secrets` and `pip-audit`. Take a screenshot of them for the report.

## 2. Pre-commit evidence

```bash
python3 scripts/capture_test_evidence.py precommit --student <n>
```

This scans every tracked file in your `student-<n>/` folder.

* **Ruff findings** (`S201` debug=True, `S608` SQL string building, `S113` no timeout, and so on): either fix them, or document why they are safe with `# noqa: S608 - <reason>` on that line.
* **pip-audit vulnerabilities:** raise the version pins in your `requirements.txt` to the "Fix Versions" shown, then re-run your tests.
* **detect-secrets:** never commit real keys. If a hit is a false positive, run `detect-secrets audit .secrets.baseline` and mark it as not a secret.

Re-run until all three hooks show `Passed` (or every remaining finding is documented), then commit the file.

## 3. CI evidence (after your `student-x.yml` run is green on GitHub)

The capture needs the GitHub CLI. On a Mac, run `brew install gh && gh auth login` once. Then:

```bash
python3 scripts/capture_test_evidence.py ci --student <n> --endpoints "GET /assessments; POST /assessments"
```

Without `gh`, copy the details from the Actions page instead:

```bash
python3 scripts/capture_test_evidence.py ci --student <n> --run-url <actions run url> \
  --conclusion success --passed 7 --failed 0 --endpoints "GET /assessments; POST /assessments"
```

## 4. Testing Review (one person, after everyone's files are in)

```bash
python3 -m agentic_loop.main --mode testing
# -> docs/release-2/agentic-loop/testing-validation.md
```

Students who haven't added evidence yet show up as `MISSING`, so you can run it at any time.

| Student | Workflow | Endpoints (fill in) |
|---|---|---|
| 1 Rigel | `RigelRivamonte.yml` | |
| 2 Jeriko | `JerikoArceo.yml` | |
| 3 Lazizbek | `student-3.yml` | |
| 4 Yi | `YiZhang.yml` | |
| 5 Vu | `student-5.yml` | `GET /assessments` (get_assessments_route), `POST /assessments` (create_assessment_route) |
