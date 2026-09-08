# Investment Fund Management Platform

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)
![Solidity](https://img.shields.io/badge/Solidity-0.8.19-363636?style=flat-square&logo=solidity&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)

A distributed backend for managing investment-fund assets and buy/sell orders. The platform combines role-based Flask services, relational and document storage, Redis-backed workflows, and smart-contract voting for investment decisions.

## Why this project

Investment decisions often involve multiple actors, temporary state, authorization rules, and an auditable approval process. This project models that workflow as a small distributed system:

- employees search the portfolio and submit buy or sell orders;
- directors review pending orders and start a voting process;
- an Ethereum smart contract records approvals, rejections, and director vetoes;
- a background worker applies approved decisions to the portfolio and removes completed workflow state.

The result is a practical demonstration of service separation, polyglot persistence, asynchronous processing, role-based security, and blockchain integration.

## Architecture

```mermaid
flowchart LR
    Client[API client] --> Auth[Auth Service<br/>:5000]
    Client --> Employee[Employee Service<br/>:5001]
    Client --> Director[Director Service<br/>:5002]

    Auth --> SQL[(Relational DB)]
    Employee --> Mongo[(MongoDB)]
    Employee --> Redis[(Redis)]
    Director --> Mongo
    Director --> Redis
    Director --> Chain[Ganache / Ethereum]

    Checker[Blockchain Checker] --> Chain
    Checker --> Redis
    Checker --> Mongo
```

### Components

| Component | Responsibility | Main dependencies |
|---|---|---|
| Auth Service | Registration, login, password hashing, JWT issuance, and user roles | Flask, SQLAlchemy, Flask-JWT-Extended |
| Employee Service | Portfolio search and creation of buy/sell orders | Flask, MongoDB, Redis |
| Director Service | Pending-order review, reports, contract deployment, and voting transaction generation | Flask, MongoDB, Redis, Web3.py |
| Blockchain Checker | Polls voting contracts and applies finalized decisions | MongoDB, Redis, Web3.py |
| `InvestmentVoting` | Majority voting with approved, rejected, and vetoed outcomes | Solidity, Ethereum/Ganache |

## Core workflow

1. A user registers and authenticates through the Auth Service.
2. The Auth Service returns a JWT containing the user's role.
3. An employee creates a buy or sell order, which is stored temporarily in Redis.
4. A director reviews pending orders and starts a decision with an odd number of voter addresses.
5. The Director Service deploys an `InvestmentVoting` contract and returns encoded transactions for approval, rejection, and veto actions.
6. The Blockchain Checker monitors the contract status.
7. Approved orders are applied idempotently to MongoDB; rejected or vetoed orders are discarded.
8. Completed orders and contract references are removed from Redis.

## Engineering highlights

- Clear separation between authentication, employee, director, and background-processing responsibilities
- JWT authentication with role-based route protection
- Password hashing through Werkzeug
- Flexible asset search with MongoDB filters and aggregation pipelines
- Redis-backed temporary order and contract state
- Solidity smart contract with voter allowlists, duplicate-vote protection, majority decisions, and director veto
- Idempotent processing of finalized buy and sell orders
- Health endpoints for service and dependency checks
- Docker Compose environment for MongoDB, Redis, and a deterministic local Ethereum chain
- Configurable infrastructure through environment variables

## Technology stack

| Area | Technologies |
|---|---|
| API and application layer | Python 3.12, Flask |
| Authentication | Flask-JWT-Extended, Werkzeug password hashing |
| Relational persistence | Flask-SQLAlchemy, SQLite by default, configurable through `DATABASE_URL` |
| Portfolio persistence | MongoDB, PyMongo |
| Workflow state | Redis |
| Blockchain | Solidity, Web3.py, Ganache |
| Development environment | Docker, Docker Compose |

## API overview

All protected endpoints expect a bearer token:

```http
Authorization: Bearer <access-token>
```

### Auth Service - port `5000`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/register` | Register an employee account |
| `POST` | `/login` | Authenticate and receive an access token |
| `POST` | `/delete` | Delete the authenticated account |
| `GET` | `/health` | Service health check |

### Employee Service - port `5001`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/search` | Search assets by name, category, dates, and custom fields |
| `POST` | `/create_buy_order` | Submit a pending asset-purchase order |
| `POST` | `/create_sell_order` | Submit a pending asset-sale order |
| `GET` | `/health` | MongoDB and Redis health check |

### Director Service - port `5002`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/pending_orders` | List orders awaiting a decision |
| `GET` | `/report` | Aggregate spending and earnings by asset category |
| `POST` | `/decision` | Deploy a voting contract for a pending order |
| `GET` | `/health` | MongoDB and Redis health check |

## Getting started

### Prerequisites

- Python 3.12+
- Docker with Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/markomijanovic/investment-fund-management-platform.git
cd investment-fund-management-platform
```

### 2. Create a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure the environment

Create a `.env` file in the project root:

```dotenv
JWT_SECRET_KEY=replace-with-a-long-random-secret

# DATABASE_URL is optional; SQLite defaults to instance/db.sqlite3

MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=change-this-password
MONGO_DATABASE=investment_fund
MONGO_URI=mongodb://admin:change-this-password@localhost:27017/?authSource=admin

REDIS_PASSWORD=change-this-password
REDIS_URI=redis://:change-this-password@localhost:6379/0

BLOCKCHAIN_URL=http://127.0.0.1:8545
```

The values above are intended only for local development. Use secret management and dedicated credentials in any deployed environment.

### 4. Start infrastructure services

```bash
docker compose -f compose.local.yaml up -d
```

This starts:

- MongoDB on `localhost:27017`
- Redis on `localhost:6379`
- Ganache on `localhost:8545`

### 5. Initialize the authentication database

```bash
mkdir -p instance
python -m services.auth.init_db
```

The initializer creates the schema and a local director fixture. Replace development fixtures before using the application outside a controlled local environment.

### 6. Run the application components

Start each process in a separate terminal with the virtual environment activated:

```bash
python -m services.auth.app
```

```bash
python -m services.employee.app
```

```bash
python -m services.director.app
```

```bash
python -m services.blockchain_checker.main
```

The checker runs continuously by default. To execute a single polling cycle:

```bash
CHECKER_RUN_ONCE=true python -m services.blockchain_checker.main
```

## Example authentication request

Register a local employee:

```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{
    "forename": "Jane",
    "surname": "Doe",
    "email": "jane@example.com",
    "password": "change-me-123"
  }'
```

Log in and obtain an access token:

```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "password": "change-me-123"
  }'
```

## Smart-contract test

With Ganache running, execute the contract integration test:

```bash
python blockchain/test_contract.py
```

The test deploys contracts, verifies majority approval, checks late-voting protection, and validates the director-only veto path.

## Project structure

```text
.
├── blockchain/
│   ├── build/                       # Compiled ABI and bytecode
│   ├── contracts/InvestmentVoting.sol
│   └── test_contract.py
├── services/
│   ├── auth/                        # Users, login, JWTs, relational DB
│   ├── employee/                    # Asset search and order creation
│   ├── director/                    # Reports and voting decisions
│   ├── blockchain_checker/          # Finalized-order processor
│   └── common/                      # Shared authorization helpers
├── compose.local.yaml               # MongoDB, Redis, and Ganache
├── Dockerfile
└── requirements.txt
```

## Current scope

This repository is an academic and portfolio backend project. It focuses on the service layer, persistence, workflow orchestration, and blockchain decision logic. A production deployment would additionally require hardened secrets, TLS, centralized logging, migrations, rate limiting, automated API tests, and a production WSGI server.

## Author

Developed and maintained by [Marko Mijanović](https://github.com/markomijanovic).
