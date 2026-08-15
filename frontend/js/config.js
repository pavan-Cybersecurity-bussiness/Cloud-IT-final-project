// config.js — points the frontend at the deployed gateway, and carries a
// read-only SAS token so <img> tags can load private blob storage photos
// without the storage account needing public access enabled.
const API_BASE = 'https://campusswap-gateway.azurewebsites.net/api';
const AZURE_BLOB_SAS = 'se=2027-12-31&sp=r&sv=2026-04-06&sr=c&sig=5MAm4HxYfrYgPDfrTBH7NGFvFnCeaG8WKCVV%2BjqRazI%3D';
