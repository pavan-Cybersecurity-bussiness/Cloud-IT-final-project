# CampusSwap — Cloud IT final project

A student marketplace for the HTW Berlin community (browse, post, message,
moderate) rebuilt as a microservice backend behind the original CampusSwap
front end, for the Cloud IT module's full-stack + cloud deployment brief.

The same CampusSwap concept is also submitted separately for the Web
Application module as a front-end-only, localStorage-backed build. This
repository is the Cloud IT version: the UI is the same, but it now talks to
three real backend microservices instead of the browser's local storage.

## Architecture

```
Browser (CampusSwap UI)
        |
        v
  API gateway  (Flask, the only public entry point)
        |
        +--> auth-service       (own SQLite DB)  — accounts, JWT issuance
        +--> listings-service   (own SQLite DB)  — CRUD, search, moderation,
        |                                          favorites, image upload
        +--> messaging-service  (own SQLite DB)  — buyer/seller inquiries

  listings-service --> Azure Blob Storage (listing photos)
  Azure Blob Storage --(upload trigger)--> Azure Function (thumbnail generator)
```

Each service owns its own database — no service reaches into another
service's tables directly — and the frontend never talks to a backend
service directly, only ever to the gateway. All four services are
independently Dockerized; the gateway is the only one exposed to the
outside world in both docker-compose and Kubernetes.

**Single cloud provider.** Everything — Blob Storage, the serverless
function, and hosting — runs on Azure. The brief requires picking one cloud
service; mixing providers would be the first thing a strict grading pass
would catch, so this was a deliberate, not incidental, choice.

**Orchestration and hosting are treated as two separate requirements.**
Container orchestration is demonstrated with Kubernetes manifests deployed
to Minikube (`kubectl get pods`, deployment YAML, and pod logs are your
evidence for that line item). Hosting the live site is a separate line item
satisfied by deploying the same Docker images to Azure App Service. They
don't have to be the same infrastructure, and keeping them separate is what
makes Minikube a safe choice under a tight deadline rather than a shortcut —
see the brief: "Kubernetes **or** any cloud service" for orchestration, and
a plain live URL for hosting.

## Repository layout

```
backend/
  gateway/             Flask reverse proxy — the only public service
  auth-service/        accounts + JWT
  listings-service/    listings CRUD, search, moderation, favorites, images
  messaging-service/   buyer/seller inquiries
docker-compose.yml     local dev: all four services networked together
k8s/                   Kubernetes manifests for Minikube (or AKS)
azure-function/        Blob-triggered thumbnail generator
frontend/              the CampusSwap UI (adapted to call the gateway)
```

## Requirements traceability

| Brief requirement | Where it's implemented | How to verify |
|---|---|---|
| Full-stack app, 5+ pages | `frontend/*.html` — index (browse), login, dashboard (4 tabs), create/edit listing, listing detail | Click through all five in a browser |
| Microservice architecture, frontend + backend | `backend/{auth,listings,messaging}-service` (each with its own DB) + `backend/gateway` + `frontend/` | `docker compose ps` shows 4 independent containers; each has its own Dockerfile |
| Images in cloud-based storage | `backend/listings-service/image_storage.py` uploads to Azure Blob Storage when `AZURE_STORAGE_CONNECTION_STRING` is set | Upload a listing photo, check the Azure Storage container in the portal |
| REST API, frontend ↔ backend | `frontend/js/api.js` (fetch calls) ↔ Flask routes in each service, proxied by `backend/gateway/app.py` | Browser dev tools → Network tab while using the site |
| Docker containers | One `Dockerfile` per service (4 total) | `docker compose build` |
| Container orchestration | `k8s/*.yaml` — Deployments + Services for all 4 components, deployed to Minikube | `kubectl get pods -n campusswap`, `kubectl get deployments -n campusswap` |
| Hosted on a cloud service | Azure App Service (see Deploying to Azure below) | The live URL, checked from a browser on a different network |
| At least one serverless component | `azure-function/ThumbnailGenerator` — Blob-triggered, resizes uploads | Upload a listing photo, check `listing-thumbnails` container for the resized copy |

## Running locally (docker-compose)

```bash
cd campusswap-cloud
docker compose up --build
```

This starts all four services; the gateway is reachable at
`http://localhost:8080`. Open `frontend/index.html` directly in a browser
(or serve the `frontend/` folder with any static file server — e.g.
`npx serve frontend`). `frontend/js/config.js` already points at
`http://localhost:8080/api`.

Without `AZURE_STORAGE_CONNECTION_STRING` set, `listings-service` falls
back to storing uploaded photos on its own local disk and serves them back
out through the gateway — the app is fully functional with zero cloud
credentials configured, which is what made it possible to test every
endpoint (including image upload) before ever touching an Azure account.

To point it at real Azure Blob Storage instead, create a `.env` file next
to `docker-compose.yml`:

```
AZURE_STORAGE_CONNECTION_STRING=<your connection string>
```

and uncomment the corresponding line in `docker-compose.yml` under
`listings-service`.

## Deploying to Minikube

```bash
minikube start
eval $(minikube docker-env)   # build straight into Minikube's own Docker daemon

docker build -t campusswap/auth-service:latest      backend/auth-service
docker build -t campusswap/listings-service:latest  backend/listings-service
docker build -t campusswap/messaging-service:latest backend/messaging-service
docker build -t campusswap/gateway:latest            backend/gateway

kubectl apply -f k8s/00-namespace.yaml

# Create the real secret (do NOT commit actual values — see
# k8s/01-secret-template.yaml for the exact command)
kubectl create secret generic campusswap-secrets \
  --namespace campusswap \
  --from-literal=JWT_SECRET=$(openssl rand -hex 32) \
  --from-literal=AZURE_STORAGE_CONNECTION_STRING=""

kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/03-auth-service.yaml
kubectl apply -f k8s/04-listings-service.yaml
kubectl apply -f k8s/05-messaging-service.yaml
kubectl apply -f k8s/06-gateway.yaml

kubectl get pods -n campusswap
minikube service gateway -n campusswap --url
```

Whatever URL the last command prints, update `k8s/02-configmap.yaml`'s
`PUBLIC_GATEWAY_URL` and `frontend/js/config.js`'s `API_BASE` to match, then
re-apply the ConfigMap and restart the listings-service pod:

```bash
kubectl apply -f k8s/02-configmap.yaml
kubectl rollout restart deployment/listings-service -n campusswap
```

**Screenshot/log evidence to keep for the submission:** `kubectl get pods
-n campusswap` (showing all 4 Running), `kubectl get deployments -n
campusswap`, and `kubectl logs deployment/gateway -n campusswap`.

## Deploying to Azure

These steps need your own Azure account and the `az` CLI logged in
(`az login`) — run them yourself rather than from a shared environment,
since they touch your subscription and credentials.

**1. Storage account + containers (image storage + Function trigger):**
```bash
az group create --name campusswap-rg --location germanywestcentral
az storage account create --name campusswapstorage --resource-group campusswap-rg --sku Standard_LRS
az storage container create --name listing-images --account-name campusswapstorage
az storage container create --name listing-thumbnails --account-name campusswapstorage
az storage account show-connection-string --name campusswapstorage --resource-group campusswap-rg
```
Use that connection string as `AZURE_STORAGE_CONNECTION_STRING` wherever
it's needed below.

**2. Container registry + push images:**
```bash
az acr create --name campusswapacr --resource-group campusswap-rg --sku Basic
az acr login --name campusswapacr
docker tag campusswap/gateway:latest campusswapacr.azurecr.io/gateway:latest
docker push campusswapacr.azurecr.io/gateway:latest
# repeat tag+push for auth-service, listings-service, messaging-service
```

**3. App Service (Web App for Containers) per backend service, plus the
static frontend** — either four `az webapp create --deployment-container-image-name ...`
calls (one per service, each with its own `az webapp config appsettings set`
for `JWT_SECRET` / `PUBLIC_GATEWAY_URL` / `AZURE_STORAGE_CONNECTION_STRING`),
or Azure Static Web Apps for `frontend/` if you'd rather not manage a
container for static files. Point `frontend/js/config.js`'s `API_BASE` at
the gateway's App Service URL once it's live.

**4. Function App (serverless component):**
```bash
az functionapp create \
  --name campusswap-thumbnails \
  --resource-group campusswap-rg \
  --storage-account campusswapstorage \
  --consumption-plan-location germanywestcentral \
  --runtime python --runtime-version 3.11 --functions-version 4

func azure functionapp publish campusswap-thumbnails
```
(`func` is the Azure Functions Core Tools CLI — install it if it isn't
already on your machine.)

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `JWT_SECRET` | auth, listings, messaging | Shared signing key for session tokens — same value in all three |
| `AUTH_DB_PATH` / `LISTINGS_DB_PATH` / `MESSAGING_DB_PATH` | respective service | SQLite file path |
| `AZURE_STORAGE_CONNECTION_STRING` | listings-service | When set, uploads go to Azure Blob Storage; when unset, local disk |
| `AZURE_BLOB_CONTAINER` | listings-service | Blob container name (default `listing-images`) |
| `PUBLIC_GATEWAY_URL` | listings-service | Base URL stamped onto locally-stored image links |
| `AUTH_SERVICE_URL` / `LISTINGS_SERVICE_URL` / `MESSAGING_SERVICE_URL` | gateway | Where to proxy each `/api/<service>` prefix |

## Design decisions worth knowing before you're asked about them

- **No real passwords.** The original front end was explicit about this
  ("Front-end demo — no password, just picking who you are for this
  session") — the Auth service preserves that behavior on purpose rather
  than bolting on a password field that wouldn't match the rest of the
  demo's intent. What changed is that identity now lives in a real
  database behind a REST API instead of being invented client-side.
- **SQLite per service, not a shared managed database.** Keeps each
  service genuinely independent and needs zero provisioning to run
  locally. The trade-off: since each pod's SQLite file lives on its own
  volume, none of the three data-owning services can be scaled beyond 1
  replica without moving to a shared database — noted directly in the k8s
  manifests via `replicas: 1`.
- **Messaging denormalizes listing title and seller name onto each
  inquiry** at creation time instead of messaging-service calling back
  into listings-service to look them up. Keeps the two services
  independent (messaging still works if listings-service is down) at the
  cost of a stale title if a listing is later renamed.
- **CORS is fully open on the gateway.** Fine for a class project with a
  static frontend hosted anywhere; a real deployment would restrict it to
  the frontend's actual origin.
- **Local-disk image fallback.** `image_storage.py` uses Azure Blob
  Storage when `AZURE_STORAGE_CONNECTION_STRING` is set, and local disk
  otherwise — meaning every endpoint, including image upload, was fully
  testable before ever touching an Azure account.
