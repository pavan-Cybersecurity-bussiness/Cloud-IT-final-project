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

Single cloud provider. Everything — Blob Storage, the serverless
function, and hosting — runs on Azure. The brief requires picking one cloud
service;

**Orchestration and hosting are treated as two separate requirements.**
Container orchestration is demonstrated with Kubernetes manifests deployed
to Minikube `kubectl get pods`, deployment YAML.

Hosting the live site is satisfied by deploying the same Docker images to Azure App Service. They
don't have to be the same infrastructure

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

## Navigation map (all 5 pages, one click away)

Every page is reachable in exactly one click from `index.html` — two of them
just don't appear in the header until you're logged in, which is
intentional role-based navigation ,  Reaching a gated page directly by URL while logged out
redirects you to `login.html` or `index.html` instead of showing a broken
page.

 Page -- Reachable from `index.html` as... | Link/action |

`index.html` -— (the starting page) | — |
 `login.html` -- Anyone (Visitor) | "Log in" in the header |
`listing.html` -- Anyone (Visitor) | Click any listing card |
`create-listing.html` -- Members only | "Post an item" in the header (hidden until logged in as a Member) |
`dashboard.html` -- Members and Moderators | "My listings" in the header (hidden until logged in) |

So a Visitor's first look at the homepage shows 3 of the 5 pages
immediately (browse, log in, view a listing); logging in as a Member
reveals the other 2. All 5 are one click away from `index.html` at every
point — which two you can see just depends on whether you're logged in,
exactly like any real marketplace site.
## Live deployment
- Site: https://campusswap-frontend.azurewebsites.net
- API gateway: https://campusswap-gateway.azurewebsites.net

## Container orchestration evidence (Minikube)

`kubectl get pods -n campusswap` showing all four services running:

<img width="468" height="173" alt="image" src="https://github.com/user-attachments/assets/1f73348a-4e86-49ae-bab9-c81c949d21b2" />

The formal submission should continue from the Minikube evidence section and replace the remaining informal/project-notes wording with examiner-oriented documentation.

## Requirements Traceability

| Module Requirement                              | Implementation                                                                                                  | Verification                                                                 |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Full-stack application with at least five pages | `frontend/` containing `index.html`, `login.html`, `listing.html`, `create-listing.html`, and `dashboard.html`  | Navigation and functionality verified through the web interface              |
| Microservice architecture                       | `auth-service`, `listings-service`, `messaging-service`, and `gateway`                                          | Four independent Docker containers and service-specific Dockerfiles          |
| Independent service databases                   | SQLite database maintained independently by each backend service                                                | Database paths and service configurations                                    |
| REST API communication                          | Frontend requests through `frontend/js/api.js`; requests are routed by the Flask gateway                        | Browser Network tab and gateway/service endpoints                            |
| API gateway                                     | Flask gateway provides the single public backend entry point                                                    | Gateway routes `/api/auth`, `/api/listings`, and `/api/messaging`            |
| Containerisation                                | Individual Dockerfiles for all four backend components                                                          | `docker compose build`                                                       |
| Container orchestration                         | Kubernetes Deployments and Services defined under `k8s/`                                                        | `kubectl get pods -n campusswap` and `kubectl get deployments -n campusswap` |
| Cloud-based image storage                       | Azure Blob Storage used by `listings-service` when configured                                                   | Uploaded images verified in the Azure Storage container                      |
| Serverless component                            | Azure Function triggered by Blob Storage uploads                                                                | Generated thumbnails verified in the `listing-thumbnails` container          |
| Cloud hosting                                   | Azure App Service used for deployment of the application components                                             | Application accessed through the deployed Azure URLs                         |
| Role-based functionality                        | Visitor, Member, and Moderator access levels implemented in the frontend and backend                            | Authentication state and protected routes                                    |
| Listing management                              | Creation, editing, deletion, search, favourites, moderation, and image upload implemented by `listings-service` | Functional testing through the application                                   |
| Messaging                                       | Buyer/seller inquiries implemented by `messaging-service`                                                       | Inquiry creation and retrieval through the application                       |

## Local Deployment

The complete backend can be executed locally using Docker Compose:

```bash
cd campusswap-cloud
docker compose up --build
```

The four backend services are deployed as separate containers and communicate through the Docker Compose network. The API gateway is available on port `8080`.

The frontend is configured to communicate with the gateway through:

```text
http://localhost:8080/api
```

The frontend may be served using any static HTTP server.

When Azure Blob Storage credentials are not configured, `listings-service` uses local filesystem storage for uploaded images. This provides a local execution mode without requiring Azure credentials while preserving the same application interface.

When `AZURE_STORAGE_CONNECTION_STRING` is configured, uploaded listing images are stored in Azure Blob Storage.

## Kubernetes Deployment

Kubernetes deployment is defined through the manifests located in `k8s/`.

The deployment consists of:

* `auth-service`
* `listings-service`
* `messaging-service`
* `gateway`

Each component is represented by a Kubernetes Deployment and Service. The namespace used for the application is `campusswap`.

The deployment sequence is:

```bash
minikube start
eval $(minikube docker-env)

docker build -t campusswap/auth-service:latest backend/auth-service
docker build -t campusswap/listings-service:latest backend/listings-service
docker build -t campusswap/messaging-service:latest backend/messaging-service
docker build -t campusswap/gateway:latest backend/gateway

kubectl apply -f k8s/00-namespace.yaml

kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/03-auth-service.yaml
kubectl apply -f k8s/04-listings-service.yaml
kubectl apply -f k8s/05-messaging-service.yaml
kubectl apply -f k8s/06-gateway.yaml
```

The resulting workloads can be verified using:

```bash
kubectl get pods -n campusswap
kubectl get deployments -n campusswap
```

The submitted Minikube evidence demonstrates that all four application services are deployed and running within the `campusswap` namespace.

## Kubernetes Configuration

The Kubernetes configuration separates application configuration from container images.

Secrets are used for sensitive configuration, including:

* `JWT_SECRET`
* `AZURE_STORAGE_CONNECTION_STRING`

The ConfigMap contains non-sensitive application configuration, including service URLs and the public gateway URL.

The gateway provides the externally accessible application interface, while the remaining backend services operate as internal services.

The data-owning services use one replica because SQLite databases are stored within the individual service volumes. Increasing the number of replicas without changing the database architecture would result in independent SQLite databases and therefore would not provide shared persistent state.

## Azure Deployment

Azure provides the cloud infrastructure used by the project. The following Azure services are used:

| Azure Service            | Purpose                                            |
| ------------------------ | -------------------------------------------------- |
| Azure Blob Storage       | Storage of listing images and generated thumbnails |
| Azure Functions          | Serverless thumbnail generation                    |
| Azure Container Registry | Storage of Docker images                           |
| Azure App Service        | Hosting of containerised application components    |

The application is deployed using Docker images stored in Azure Container Registry.

The Docker images are tagged for the Azure Container Registry using:

```bash
docker tag campusswap/gateway:latest campusswapacr.azurecr.io/gateway:latest
docker push campusswapacr.azurecr.io/gateway:latest
```

The same process is applied to the authentication, listings, and messaging services.

The live application is available at:

```text
https://campusswap-frontend.azurewebsites.net
```

The API gateway is available at:

```text
https://campusswap-gateway.azurewebsites.net
```

## Azure Blob Storage

Azure Blob Storage is used for persistent cloud storage of listing images.

Two containers are used:

```text
listing-images
listing-thumbnails
```

The `listing-images` container stores uploaded listing images. The `listing-thumbnails` container stores resized versions generated by the serverless processing component.

The listings service accesses Azure Blob Storage using the `AZURE_STORAGE_CONNECTION_STRING` environment variable.

The storage implementation is encapsulated in:

```text
backend/listings-service/image_storage.py
```

This separates image-storage functionality from the main listing-management logic.

## Serverless Processing

The project implements a serverless image-processing component using Azure Functions.

The function is located under:

```text
azure-function/ThumbnailGenerator
```

The function is triggered by an image upload to Azure Blob Storage.

The processing flow is:

```text
User uploads listing image
        |
        v
listings-service
        |
        v
Azure Blob Storage
        |
        v
Blob trigger
        |
        v
Azure Function
        |
        v
Thumbnail generation
        |
        v
listing-thumbnails container
```

The function therefore operates independently of the main application containers and demonstrates event-driven serverless processing.

## Environment Configuration

The application uses environment variables to separate configuration from application code.

| Variable                          | Component                           | Purpose                                        |
| --------------------------------- | ----------------------------------- | ---------------------------------------------- |
| `JWT_SECRET`                      | Authentication, listings, messaging | JWT signing and verification                   |
| `AUTH_DB_PATH`                    | Authentication service              | SQLite database location                       |
| `LISTINGS_DB_PATH`                | Listings service                    | SQLite database location                       |
| `MESSAGING_DB_PATH`               | Messaging service                   | SQLite database location                       |
| `AZURE_STORAGE_CONNECTION_STRING` | Listings service                    | Azure Blob Storage authentication              |
| `AZURE_BLOB_CONTAINER`            | Listings service                    | Listing image container                        |
| `PUBLIC_GATEWAY_URL`              | Listings service                    | Public base URL for locally stored image links |
| `AUTH_SERVICE_URL`                | Gateway                             | Authentication service endpoint                |
| `LISTINGS_SERVICE_URL`            | Gateway                             | Listings service endpoint                      |
| `MESSAGING_SERVICE_URL`           | Gateway                             | Messaging service endpoint                     |

Sensitive values are provided through environment configuration and Kubernetes Secrets rather than being committed to the repository.

## Security and Access Control

Authentication is implemented through the authentication microservice.

The authentication service maintains account information in its own SQLite database and issues JSON Web Tokens (JWTs).

The JWT is used by the backend services to identify the authenticated user and enforce access restrictions.

The application defines three functional access levels:

* Visitor
* Member
* Moderator

Visitors can browse listings and access public listing information.

Members can create and manage listings and access their dashboard and messaging functionality.

Moderators have access to moderation functionality.

Protected frontend pages also perform authentication checks. Direct access to protected pages while unauthenticated results in redirection rather than unrestricted access.

## Authentication Design

The original CampusSwap frontend used a demonstration identity-selection mechanism rather than password-based authentication. The Cloud IT implementation preserves this behaviour while moving identity management to the backend.

Consequently, the project does not implement real password authentication.

The authentication service provides persistent user records and JWT issuance through a REST API. This maintains compatibility with the original application concept while introducing a dedicated authentication microservice.

## Microservice Independence

Each backend service has an independent responsibility and database.

```text
auth-service
    |
    +-- Authentication
    +-- User records
    +-- JWT issuance

listings-service
    |
    +-- Listings
    +-- Search
    +-- Favourites
    +-- Moderation
    +-- Images

messaging-service
    |
    +-- Buyer/seller inquiries
```

No service directly accesses another service's database.

The frontend does not communicate directly with the individual backend services. All backend requests are routed through the API gateway.

This structure provides clear service boundaries and prevents database-level coupling between services.

## Messaging Data Model

The messaging service stores the listing title and seller name associated with an inquiry at the time the inquiry is created.

This approach avoids requiring the messaging service to query the listings service for every inquiry.

The resulting trade-off is that the stored title may become outdated if the corresponding listing is subsequently renamed. The design prioritises service independence over maintaining a live cross-service reference.

## Image Storage Design

The image-storage implementation supports two execution modes.

When Azure Blob Storage is configured, listing images are uploaded to Azure.

When Azure credentials are not configured, images are stored on the local filesystem.

This design permits the complete application to be tested locally without requiring cloud credentials while allowing the same application to use Azure Blob Storage in the cloud deployment.

## CORS Configuration

CORS is configured on the API gateway to allow communication from the static frontend.

The current configuration is suitable for the submitted academic deployment, where the frontend and API are deployed as separate application components.

For a production deployment, the permitted origin would be restricted to the specific frontend domain rather than allowing unrestricted cross-origin access.

## Repository Structure

The final repository is organised as follows:

```text
campusswap-cloud/
│
├── backend/
│   ├── gateway/
│   ├── auth-service/
│   ├── listings-service/
│   └── messaging-service/
│
├── frontend/
│
├── k8s/
│   ├── 00-namespace.yaml
│   ├── 01-secret-template.yaml
│   ├── 02-configmap.yaml
│   ├── 03-auth-service.yaml
│   ├── 04-listings-service.yaml
│   ├── 05-messaging-service.yaml
│   └── 06-gateway.yaml
│
├── azure-function/
│   └── ThumbnailGenerator/
│
└── docker-compose.yml
```

The repository structure separates application code, frontend resources, container orchestration configuration, and serverless functionality.

## Deployment Evidence

The submission includes deployment evidence for the Kubernetes component.

The primary Kubernetes evidence is:

```bash
kubectl get pods -n campusswap
```

This output demonstrates the deployment status of the four backend components.

Additional verification can be performed using:

```bash
kubectl get deployments -n campusswap
kubectl logs deployment/gateway -n campusswap
```

The live Azure deployment provides independent evidence of cloud hosting through the deployed application and API gateway URLs.

## Summary of Implemented Cloud IT Requirements

List of requirement that had be implemented.

1. A full-stack web application with five main pages.
2. A microservice backend consisting of three domain services and an API gateway.
3. Independent SQLite databases for each data-owning service.
4. REST-based communication between the frontend, gateway, and backend services.
5. Docker containerisation of all backend services.
6. Kubernetes orchestration demonstrated through Minikube.
7. Azure App Service hosting.
8. Azure Container Registry for Docker image storage.
9. Azure Blob Storage for listing images.
10. Azure Functions for event-driven thumbnail generation.
11. Environment-based configuration and Kubernetes Secrets.
12. Authentication and JWT-based session management.
13. Role-based access control for Visitors, Members, and Moderators.
14. Listing creation, editing, searching, favourites, moderation, and image upload.
15. Buyer/seller messaging functionality.
16. Separation of frontend access from internal backend services through the API gateway.

The resulting architecture demonstrates containerisation, microservice separation, REST communication, orchestration, cloud storage, serverless processing, and cloud hosting within a single Azure-based deployment environment.

                         Browser
                            |
                            v
                   CampusSwap Frontend
                            |
                            v
                     API Gateway
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
         Auth Service  Listings Service  Messaging Service
              |             |             |
              v             v             v
          SQLite DB     SQLite DB      SQLite DB
                            |
                            v
                    Azure Blob Storage
                            |
                            v
                     Azure Function
                            |
                            v
                  Thumbnail Storage

thank you
