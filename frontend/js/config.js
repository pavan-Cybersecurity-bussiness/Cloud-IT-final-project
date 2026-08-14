// config.js — single place to point the frontend at the deployed gateway.
//
// Local development (docker-compose): http://localhost:8080
// Production: replace with the gateway's live URL (Azure App Service /
// Container Apps / whatever the gateway ends up hosted on).
const API_BASE = 'http://localhost:8080/api';
