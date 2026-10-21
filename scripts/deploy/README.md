# Release 2 cloud deployment - Azure Container Apps

`deploy_azure.py` deploys the **integrated** application (all 16 Compose services) to one Azure
Container Apps environment. The same script runs from a laptop and from
`.github/workflows/cloud-deployment.yml`.

**Baseline cloud profile:** frontends, backends and databases only. AI-Mode, MCP, RAG and the
Multi-Agent server are not deployed, and every backend runs with `MCP_ENABLED`, `RAG_ENABLED` and
`MULTI_AGENT_ENABLED` set to `false`.

| Compose | Azure |
|---|---|
| one service | one Container App with the same name, 1 replica (SQLite lives in the container) |
| frontends, backends | public HTTPS ingress, `https://<app>.<environment-domain>` |
| databases | HTTPS ingress, called by their backend at `https://<app>.<environment-domain>` (see Known limitation) |
| `http://localhost:<port>` in frontend HTML/JS | rewritten in a build copy to the cloud URL (repo files untouched) |
| images | built for `linux/amd64` with Docker, pushed to Azure Container Registry |

## First deployment (from your laptop)

Prerequisites: Azure for Students subscription, Docker Desktop running, Azure CLI (`brew install azure-cli`).

```bash
az login
az account show -o table                            # check the right subscription is selected
python3 scripts/deploy/deploy_azure.py plan         # dry run: prints every command, changes nothing
python3 scripts/deploy/deploy_azure.py deploy       # ~15-25 min the first time (16 image builds)
```

At the end it smoke-tests every public app and writes `docs/release-2/cloud/deployment.json`,
which the agentic-loop Cloud Deployment Review reads:

```bash
python -m agentic_loop.main --mode cloud
```

Useful options:

```bash
python3 scripts/deploy/deploy_azure.py deploy --only timetable-backend timetable-frontend   # redeploy two apps
python3 scripts/deploy/deploy_azure.py status                                               # apps + URLs
az containerapp logs show -g asd-group18-rg -n timetable-backend --tail 50                  # app logs
```

Settings (environment variables): `AZ_RESOURCE_GROUP` (default `asd-group18-rg`), `AZ_LOCATION`
(`australiaeast`), `AZ_CONTAINERAPP_ENV` (`asd-group18-env`), `AZ_ACR_NAME` (default derived from the
subscription id). If your subscription restricts regions, set `AZ_LOCATION` to an allowed one.

## Automatic deployment (GitHub Actions)

`cloud-deployment.yml` runs when any student CI workflow finishes successfully on `main`, or by hand
(**Actions -> Cloud Deployment - Azure Container Apps -> Run workflow**). Its `ci-gate` job checks that
the latest run of **every** student workflow on `main` is green before deploying.

One-time setup, by the subscription owner, after the first laptop deployment. It uses a
**user-assigned managed identity** with a GitHub OIDC federated credential: GitHub Actions gets a
short-lived token for this repository's `main` branch only, and no password is stored anywhere.
(A service principal from `az ad sp create-for-rbac` is not an option: UTS does not let students
register applications in its directory - "Insufficient privileges".)

```bash
RG=asd-group18-rg
az provider register -n Microsoft.ManagedIdentity --wait
az identity create -g $RG -n asd-group18-github -o none
az identity federated-credential create -g $RG --identity-name asd-group18-github --name github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:rigels51/ASD-Project-Group18:ref:refs/heads/main --audiences api://AzureADTokenExchange
az role assignment create --assignee-object-id "$(az identity show -g $RG -n asd-group18-github --query principalId -o tsv)" \
  --assignee-principal-type ServicePrincipal --role Contributor \
  --scope "$(az group show -n $RG --query id -o tsv)"
az identity show -g $RG -n asd-group18-github --query "{AZURE_CLIENT_ID:clientId, AZURE_TENANT_ID:tenantId}" -o table
az account show --query "{AZURE_SUBSCRIPTION_ID:id}" -o table
```

Add the three values as repository secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and
`AZURE_SUBSCRIPTION_ID` (GitHub -> Settings -> Secrets and variables -> Actions; needs repo admin).
The identity can only manage the `asd-group18-rg` resource group, and only workflow runs on `main`
can use it.

## Known limitation - database APIs are publicly reachable

Azure now creates Consumption environments as **express** environments. They reject `allowInsecure`,
redirect plain `http://<app>` calls to `https://<app>.internal.<domain>`, and the environment
certificate does not cover that internal name (`CERTIFICATE_VERIFY_FAILED: Hostname mismatch`).
The only certificate-valid address is the public one, so each database gets HTTPS ingress and its
backend calls it there. Traffic is encrypted, but the database APIs can be reached from the internet.
Restricting them (IP allow-list to the environment's outbound IP, or a shared API key) is the
cloud endpoint-security bonus item.

## Cost and teardown

16 apps x 0.25 vCPU / 0.5 GiB, always on, plus a Basic registry - a few US$ per day against the
Azure for Students credit. Set a budget alert in the portal (Cost Management -> Budgets).
After marking, delete everything:

```bash
python3 scripts/deploy/deploy_azure.py destroy --yes
```

## Tests (offline)

```bash
python3 -m unittest scripts.deploy.test_deploy_azure -v
```
