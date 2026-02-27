# Irrigation Decision Engine

A microservice that analyzes soil and environmental data to calculate crop water stress and provide irrigation recommendations.

## Tech Stack

- **Backend:** FastAPI (Python 3.11)
- **Database:** PostgreSQL 15
- **ORM:** SQLAlchemy
- **Containerization:** Docker & Docker Compose

## How to Run (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Start the project

```bash
docker compose up --build
```

This starts two containers:

| Container         | Description             | Port |
|-------------------|-------------------------|------|
| `irrigation-app`  | FastAPI application     | 8000 |
| `irrigation-db`   | PostgreSQL 15 database  | 5433 |

### Verify it works

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

## API Endpoints

### Crops
| Method | Endpoint           | Description                          |
|--------|--------------------|--------------------------------------|
| POST   | `/crops`           | Register a new crop                  |
| GET    | `/crops`           | List all crops                       |
| GET    | `/crops/{crop_id}` | Get a specific crop                  |

### Sensor Data
| Method | Endpoint                   | Description                          |
|--------|----------------------------|--------------------------------------|
| POST   | `/sensor-data`             | Submit new sensor readings           |
| GET    | `/sensor-data`             | List sensor readings                 |
| GET    | `/sensor-data/{sensor_id}` | Get specific sensor data             |

### Irrigation Decisions
| Method | Endpoint                              | Description                          |
|--------|---------------------------------------|--------------------------------------|
| POST   | `/decisions/evaluate/{sensor_data_id}`| Analyze data and generate decision   |
| GET    | `/decisions`                          | List irrigation decisions            |
| PATCH  | `/decisions/{decision_id}`            | Update decision status               |

## Database Schema

The application uses three main tables:

- **crops** — Crop information with moisture and temperature thresholds
- **sensor_data** — Environmental and soil sensor readings
- **irrigation_decisions** — Generated irrigation recommendations with stress analysis

## Project Structure

```
├── app/
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py
│   ├── interfaces/
│   │   ├── __init__.py
│   │   └── api.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── irrigation_service.py
│   ├── __init__.py
│   └── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Team

| Name              | GitHub                                              |
|-------------------|------------------------------------------------------|
| Nazanin Niazi     | [@NazaninNiazi11](https://github.com/NazaninNiazi11) |
| Shada Daab        | [@shadatr](https://github.com/shadatr)               |
| Özge Zelal Küçük  | [@ozge-devops](https://github.com/ozge-devops)       |

## Course

Special Topics in Software Development
