# Release 2 cloud deployment evidence (read by the agentic-loop Cloud Deployment Review)

## After each cloud deployment

`python3 scripts/deploy/deploy_azure.py deploy` (laptop) and `cloud-deployment.yml` (GitHub Actions)
write `deployment.json` here automatically: platform, deployed commit, run URL, conclusion and the
public URL of every frontend and backend. From GitHub Actions, download it from the run's
`deployment-record` artifact. Commit it so the review has evidence. See `scripts/deploy/README.md`.

`deployment.example.json` shows the format. The required deployment keeps `"ai_profile": "baseline"`
and `"ai_enabled": []`. For bonus marks, list the backends whose AI routes are switched on in the
cloud, e.g. `"ai_enabled": ["timetable-backend"]`.

## Run the review (one person, from the repository root, on the host)

```bash
python -m agentic_loop.main --mode cloud
```

It checks `cloud-deployment.yml` (gated on CI, Azure/AWS step, AI flags set to `false`), the scripts
in `scripts/deploy/`, the deployment record, and then probes the live deployment **read-only**:

| Probe | Pass when |
|---|---|
| each frontend URL | `200` |
| each backend read route (`/students`, `/staff`, `/timetable`, `/courses`, `/assessments`) | `200` |
| each AI route (RAG, MCP, Multi-Agent) | error response that says *disabled* (S2 answers 403, others 503) |

Results: `PASS`, `WARN` (works, but needs a fix - e.g. AI route unavailable without saying disabled),
`MISSING` (no evidence yet) or `FAIL`. Any `FAIL`/`MISSING` makes the loop recommend **Do not release**;
`WARN` only gives **Release with conditions**; all `PASS` gives **Release**.

In a terminal it then asks for the **human release decision**. Non-interactive:

```bash
python -m agentic_loop.main --mode cloud --decision "Release" --reviewer "<name>" --comment "<reason>"
```

A reason is required whenever the decision differs from the loop's recommendation.

Outputs:
* `docs/release-2/agentic-loop/cloud-validation.md` - the review / validation log (report evidence)
* `docs/release-2/agentic-loop/cloud-release-decisions.jsonl` - one line per human release decision
