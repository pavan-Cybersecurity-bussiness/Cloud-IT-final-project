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

kubernets(minicubes)
<img width="1280" height="1024" alt="image" src="https://github.com/user-attachments/assets/e399cf16-7b46-4f88-ac41-a4df4c79604d" />
