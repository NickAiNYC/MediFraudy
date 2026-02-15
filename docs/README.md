# Elite Fraud Ring Visualization Engine

## Overview
This system detects and visualizes complex fraud patterns in Medicaid provider networks using graph theory and machine learning.

## Features
- **Community Detection**: Identifies isolated subgraphs indicative of fraud rings.
- **Kickback Cycle Detection**: Finds circular referral patterns (A -> B -> C -> A).
- **Interactive Visualization**: Force-directed graph with D3.js.
- **Risk Scoring**: Automated risk assessment for providers.

## Architecture
- **Backend**: FastAPI, NetworkX, SQLAlchemy
- **Frontend**: React, D3.js, TypeScript
- **Database**: PostgreSQL

## Installation
See [QUICKSTART.md](QUICKSTART.md) for setup instructions.

## Documentation
- [PERFORMANCE.md](PERFORMANCE.md): Performance tuning for large graphs.
- [PRODUCTION.md](PRODUCTION.md): Deployment guide.
