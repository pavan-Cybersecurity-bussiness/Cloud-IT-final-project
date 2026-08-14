# CampusSwap — Cloud IT Final Project

CampusSwap is a student marketplace for the HTW Berlin community. Students can browse listings, post items, contact sellers, and manage their listings.

For the Cloud IT module, the original CampusSwap frontend was kept, but the localStorage-based backend was replaced with a small microservice backend and cloud deployment setup. The same concept is also used separately for the Web Application module as a frontend-only version.

This repository is the Cloud IT version. The interface is mostly the same, but the frontend now communicates with three backend services through an API gateway.

## Architecture

```text
Browser (CampusSwap UI)
        |
        v
  API Gateway (Flask)
        |
        +--> auth-service        (SQLite) — accounts and JWTs
        +--> listings-service    (SQLite) — listings, search, moderation,
        |                                      favourites and image uploads
        +--> messaging-service   (SQLite) — buyer/seller enquiries

listings-service --> Azure Blob Storage (listing photos)
Azure Blob Storage --> Azure Function (thumbnail generation)
```

Each backend service has its own database. A service does not access another service's database directly.

The frontend also does not communicate with the individual backend services. All API requests go through the Flask gateway, which acts as the single public entry point.

All four backend components are Dockerized. In both Docker Compose and Kubernetes, only the gateway is exposed externally.

### Why Azure?

The project uses Azure for the cloud components. Blob Storage is used for listing images, Azure Functions handles thumbnail generation, and Azure App Service is used for hosting.

Using one cloud provider keeps the deployment simpler and also matches the project requirement to choose a cloud platform rather than mixing several providers.

### Kubernetes and hosting

Kubernetes and cloud hosting are treated as two separate parts of the project.

The Kubernetes manifests can be deployed to Minikube to demonstrate container orchestration. The running pods, deployments and logs can then be used as evidence for the orchestration requirement.

For the hosted version, the same Docker images can be deployed to Azure App Service. This gives the project a public live deployment without requiring the Kubernetes environment to be the production host.

## Repository layout

```text
backend/
  gateway/             Flask reverse proxy and public API entry point
  auth-service/        accounts and JWT handling
  listings-service/    listings, search, moderation, favourites and images
  messaging-service/   buyer/seller enquiries

docker-compose.yml     local development setup
k8s/                   Kubernetes manifests for Minikube or AKS
azure-function/        Blob-triggered thumbnail generator
frontend/              CampusSwap frontend
```

## Navigation

The application has five main pages. Every page is reachable from `index.html` with one click.

Some links are hidden until a user logs in. This is intentional because those pages are only available to members or moderators.

If someone tries to open a protected page directly while logged out, the frontend redirects them to `login.html` or `index.html` instead of displaying a broken page.

| Page | Available from `index.html` as | Link/action |
|---|---|---|
| `index.html` | Everyone | Starting page |
| `login.html` | Everyone | "Log in" in the header |
| `listing.html` | Everyone | Click a listing card |
| `create-listing.html` | Members | "Post an item" after logging in |
| `dashboard.html` | Members and Moderators | "My listings" after logging in |

A visitor can therefore browse the marketplace, open a listing and log in without needing an account first. Once logged in, the additional member pages become available.

## Requirements traceability

| Brief requirement | Implementation | How to verify |
|---|---|---|
| Full-stack application with 5+ pages | `frontend/*.html` — index, login, dashboard, create/edit listing and listing detail | Open the application and navigate through the pages |
| Microservice architecture | `backend/{auth,listings,messaging}-service` plus `backend/gateway` and `frontend` | Run `docker compose ps` and check the four independent containers |
| Cloud-based image storage | `backend/listings-service/image_storage.py` uploads to Azure Blob Storage when `AZURE_STORAGE_CONNECTION_STRING` is configured | Upload a listing image and check the Azure Storage container |
| REST API | `frontend/js/api.js` communicates with Flask routes through the gateway | Use the browser Network tab while using the application |
| Docker containers | One Dockerfile for each backend component | Run `docker compose build` |
| Container orchestration | `k8s/*.yaml` contains Deployments and Services for all four components | Run `kubectl get pods -n campusswap` and `kubectl get deployments -n campusswap` |
| Cloud hosting | Azure App Service | Open the deployed application from a separate network |
| Serverless component | `azure-function/ThumbnailGenerator` is triggered by new Blob uploads | Upload an image and check the `listing-thumbnails` container |

## Running locally with Docker Compose

From the project directory:

```bash
cd campusswap-cloud
docker compose up --build
```

This starts the four backend services. The gateway is available at:

```text
http://localhost:8080
```

The frontend can be opened directly from `frontend/index.html`, or served with a simple static file server such as:

```bash
npx serve frontend
```

`frontend/js/config.js` already points to:

```text
http://localhost:8080/api
```

### Running without Azure

Azure credentials are not required for local development.

If `AZURE_STORAGE_CONNECTION_STRING` is not set, the listings service stores uploaded images on its local disk and serves them through the gateway.

This makes the application fully usable locally, including image uploads, without having to configure an Azure account first.

### Using Azure Blob Storage locally

To use real Azure Blob Storage, create a `.env` file next to `docker-compose.yml`:

```text
AZURE_STORAGE_CONNECTION_STRING=<your connection string>
```

Then enable the corresponding environment variable in `docker-compose.yml` for the listings service.

## Deploying to Minikube

Start Minikube and use its Docker environment:

```bash
minikube start
eval $(minikube docker-env)
```

Build the four images:

```bash
docker build -t campusswap/auth-service:latest backend/auth-service
docker build -t campusswap/listings-service:latest backend/listings-service
docker build -t campusswap/messaging-service:latest backend/messaging-service
docker build -t campusswap/gateway:latest backend/gateway
```

Create the namespace:

```bash
kubectl apply -f k8s/00-namespace.yaml
```

Create the required secret. Actual secrets should not be committed to the repository:

```bash
kubectl create secret generic campusswap-secrets \
  --namespace campusswap \
  --from-literal=JWT_SECRET=$(openssl rand -hex 32) \
  --from-literal=AZURE_STORAGE_CONNECTION_STRING=""
```

Apply the ConfigMap and deployments:

```bash
kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/03-auth-service.yaml
kubectl apply -f k8s/04-listings-service.yaml
kubectl apply -f k8s/05-messaging-service.yaml
kubectl apply -f k8s/06-gateway.yaml
```

Check the pods:

```bash
kubectl get pods -n campusswap
```

The gateway can be exposed with:

```bash
minikube service gateway -n campusswap --url
```

If the returned URL is different from the one currently configured, update `PUBLIC_GATEWAY_URL` in `k8s/02-configmap.yaml` and `API_BASE` in `frontend/js/config.js`.

Then apply the ConfigMap again and restart the listings service:

```bash
kubectl apply -f k8s/02-configmap.yaml
kubectl rollout restart deployment/listings-service -n campusswap
```

### Evidence for the Kubernetes requirement

Useful screenshots/logs for the submission are:

```bash
kubectl get pods -n campusswap
kubectl get deployments -n campusswap
kubectl logs deployment/gateway -n campusswap
```

The first command should show the four application components running.

## Deploying to Azure

The Azure deployment requires your own Azure account and the Azure CLI. Run `az login` locally before creating the resources.

### 1. Storage account and containers

Create the resource group and storage account:

```bash
az group create --name campusswap-rg --location germanywestcentral

az storage account create \
  --name campusswapstorage \
  --resource-group campusswap-rg \
  --sku Standard_LRS
```

Create the two containers:

```bash
az storage container create \
  --name listing-images \
  --account-name campusswapstorage

az storage container create \
  --name listing-thumbnails \
  --account-name campusswapstorage
```

Get the storage connection string:

```bash
az storage account show-connection-string \
  --name campusswapstorage \
  --resource-group campusswap-rg
```

Use the returned connection string as `AZURE_STORAGE_CONNECTION_STRING` where required.

### 2. Container registry

Create an Azure Container Registry:

```bash
az acr create \
  --name campusswapacr \
  --resource-group campusswap-rg \
  --sku Basic

az acr login --name campusswapacr
```

Tag and push the gateway image:

```bash
docker tag campusswap/gateway:latest campusswapacr.azurecr.io/gateway:latest
docker push campusswapacr.azurecr.io/gateway:latest
```

Repeat the tagging and push process for:

- `auth-service`
- `listings-service`
- `messaging-service`

### 3. App Service

The backend services can be deployed as separate Web Apps for Containers. Each service gets its own App Service configuration.

The relevant application settings include:

- `JWT_SECRET`
- `PUBLIC_GATEWAY_URL`
- `AZURE_STORAGE_CONNECTION_STRING`

The frontend can either be hosted separately with Azure Static Web Apps or served using a container.

Once the gateway is live, update `frontend/js/config.js` so that `API_BASE` points to the gateway's App Service URL.

### 4. Azure Function

The thumbnail generator is implemented as an Azure Function triggered by Blob uploads.

Create the Function App with:

```bash
az functionapp create \
  --name campusswap-thumbnails \
  --resource-group campusswap-rg \
  --storage-account campusswapstorage \
  --consumption-plan-location germanywestcentral \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4
```

Publish the function:

```bash
func azure functionapp publish campusswap-thumbnails
```

`func` is provided by the Azure Functions Core Tools.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `JWT_SECRET` | auth, listings, messaging | Shared signing key used for JWTs |
| `AUTH_DB_PATH` | auth-service | SQLite database path |
| `LISTINGS_DB_PATH` | listings-service | SQLite database path |
| `MESSAGING_DB_PATH` | messaging-service | SQLite database path |
| `AZURE_STORAGE_CONNECTION_STRING` | listings-service | Enables Azure Blob Storage for uploads |
| `AZURE_BLOB_CONTAINER` | listings-service | Name of the image container, defaulting to `listing-images` |
| `PUBLIC_GATEWAY_URL` | listings-service | Base URL used for locally stored image links |
| `AUTH_SERVICE_URL` | gateway | Address of the auth service |
| `LISTINGS_SERVICE_URL` | gateway | Address of the listings service |
| `MESSAGING_SERVICE_URL` | gateway | Address of the messaging service |

## Design decisions

### Authentication

The project does not use real passwords.

The original frontend was designed as a demonstration where a user simply selected their identity for the session. The Auth service keeps that behaviour instead of introducing a password system that would not fit the original application.

The main difference is where the identity is stored. In the original version it was handled in the frontend. In this version it is stored in the auth service's database and exposed through a REST API, with JWTs used for authenticated requests.

### One SQLite database per service

Each service has its own SQLite database. This keeps the services independent and makes the project easy to run locally without setting up a separate database server.

There is a trade-off. SQLite is not suitable for scaling these services horizontally in the current setup because each pod has its own database volume. The Kubernetes manifests therefore use one replica for each data-owning service.

Moving to a shared database or another persistent database solution would be the next step if the application needed to scale beyond this project setup.

### Messaging data

The messaging service stores the listing title and seller name when an enquiry is created.

This means the messaging service does not need to call the listings service just to display basic information about an enquiry. The services remain independent, and messaging can continue working even if the listings service is temporarily unavailable.

The downside is that the stored title can become outdated if the listing is renamed later.

### CORS

CORS is currently open on the gateway so that the static frontend can be hosted separately from the backend.

For a real production deployment, the allowed origin should be restricted to the actual frontend domain.

### Image storage fallback

The listings service uses Azure Blob Storage when `AZURE_STORAGE_CONNECTION_STRING` is configured.

If it is not configured, images are stored locally instead.

This fallback was useful during development because the complete application, including image uploads, could be tested before configuring the Azure resources.
