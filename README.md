# Irrigation Decision Engine

A microservice that analyzes soil and environmental data to calculate crop water stress and provide irrigation recommendations.

## How to Run (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Start the project

```bash
docker compose up --build
```

This starts two containers:

| Container        | Description              | Port  |
|------------------|--------------------------|-------|
| `irrigation-app` | FastAPI application      | 8000  |
| `irrigation-db`  | PostgreSQL 15 database   | 5433  |

### Verify it works

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs
