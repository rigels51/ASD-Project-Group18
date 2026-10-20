# Release 2 cloud deployment evidence (read by the agentic-loop Cloud Deployment Review)

## After each cloud deployment (whoever ran it)

1. Copy `deployment.example.json` to `deployment.json` and replace every value with the real one:
   the platform, the commit that was deployed, the `cloud-deployment.yml` run URL and its conclusion,
   and the public URL of every frontend and backend.
2. Keep `"ai_profile": "baseline"` and `"ai_enabled": []` for the required deployment
   (AI-Mode, MCP, RAG and Multi-Agent disabled). For bonus marks, list the backends whose AI
   routes are switched on in the cloud, e.g. `"ai_enabled": ["timetable-backend"]`.
3. Commit `deployment.json`.

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
