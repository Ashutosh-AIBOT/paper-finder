---
title: Research Paper API
emoji: 📚
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Research Paper Search API

Search 20 free academic paper sources in one query. Auto-ranked by boom score (citations / age).

## Setup (Required)

Add this secret in HuggingFace Space → Settings → Variables and Secrets:

```
DATABASE_URL = postgres://avnadmin:YOUR_PASSWORD@pg-1e9e4eea-apnibatz02-1878.e.aivencloud.com:26258/defaultdb?sslmode=require
```

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Health check |
| `GET /search?topic=transformer` | Search all sources |
| `GET /search?topic=transformer&sector=ai` | Filter by sector |
| `GET /search?topic=transformer&limit=20` | Control result count |
| `GET /apis` | List all APIs in DB |
| `GET /sectors` | List available sectors |
| `GET /docs` | Swagger UI |

## Sectors
`ai` · `biology` · `physics` · `cs` · `multidisciplinary` · `social` · `chemistry`

## Add More APIs (No Code Change)
```sql
INSERT INTO apis (id, name, sector, url, protocol, auth, priority, status)
VALUES ('newapi', 'New Source', 'ai', 'https://api.example.com/search', 'rest', 'none', 8, 'active');
```
