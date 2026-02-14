#!/usr/bin/make
# Medicaid Whistleblower Analytics - Makefile
# One-command control for the entire stack

# Colors for terminal output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.PHONY: help
help:
	@echo "$(BLUE)╔════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║   Medicaid Whistleblower Analytics - Control Center    ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Available commands:$(NC)"
	@echo ""
	@echo "$(GREEN)┌── Development Commands ──────────────────────────────┐$(NC)"
	@echo "│  make up        $(NC)- Start all services in background"
	@echo "│  make down      $(NC)- Stop all services"
	@echo "│  make restart   $(NC)- Restart all services"
	@echo "│  make logs      $(NC)- Follow all logs"
	@echo "│  make logs-backend  $(NC)- Follow backend logs only"
	@echo "│  make logs-frontend $(NC)- Follow frontend logs only"
	@echo "│  make status    $(NC)- Show container status"
	@echo "$(GREEN)└──────────────────────────────────────────────────────┘$(NC)"
	@echo ""
	@echo "$(YELLOW)┌── Database Commands ──────────────────────────────────┐$(NC)"
	@echo "│  make psql      $(NC)- Open PostgreSQL CLI"
	@echo "│  make db-backup $(NC)- Backup database to file"
	@echo "│  make db-restore$(NC)- Restore database from backup"
	@echo "│  make db-reset  $(NC)- Reset database (delete all data)"
	@echo "│  make adminer   $(NC)- Start Adminer UI (port 8080)"
	@echo "$(YELLOW)└──────────────────────────────────────────────────────┘$(NC)"
	@echo ""
	@echo "$(RED)┌── Analysis Commands ───────────────────────────────────┐$(NC)"
	@echo "│  make sweep     $(NC)- Run NYC elderly care sweep"
	@echo "│  make provider id=123 $(NC)- Analyze specific provider"
	@echo "│  make export    $(NC)- Export all high-risk cases"
	@echo "│  make reports   $(NC)- Generate all reports"
	@echo "$(RED)└──────────────────────────────────────────────────────┘$(NC)"
	@echo ""
	@echo "$(BLUE)┌── Data Commands ───────────────────────────────────────┐$(NC)"
	@echo "│  make load-data $(NC)- Load Medicaid dataset"
	@echo "│  make sample    $(NC)- Load sample (100k rows) for testing"
	@echo "│  make validate  $(NC)- Validate dataset"
	@echo "$(BLUE)└──────────────────────────────────────────────────────┘$(NC)"
	@echo ""
	@echo "$(GREEN)┌── Maintenance ────────────────────────────────────────┐$(NC)"
	@echo "│  make clean     $(NC)- Remove containers and volumes"
	@echo "│  make prune     $(NC)- Docker system prune"
	@echo "│  make shell     $(NC)- Open backend shell"
	@echo "│  make test      $(NC)- Run all tests"
	@echo "│  make coverage  $(NC)- Run tests with coverage"
	@echo "$(GREEN)└──────────────────────────────────────────────────────┘$(NC)"
	@echo ""
	@echo "$(YELLOW)Example: make provider id=12345$(NC)"

# ---------------------------------------------------------------------------
# Development Commands
# ---------------------------------------------------------------------------

up:
	@echo "$(GREEN)🚀 Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Services started. View logs with 'make logs'$(NC)"

down:
	@echo "$(YELLOW}🛑 Stopping all services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ Services stopped.$(NC)"

restart: down up

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

status:
	@echo "$(BLUE)📊 Container Status:$(NC)"
	docker-compose ps

# ---------------------------------------------------------------------------
# Database Commands
# ---------------------------------------------------------------------------

psql:
	@echo "$(BLUE)🐘 Connecting to PostgreSQL...$(NC)"
	docker-compose exec postgres psql -U analyst medicaid_db

db-backup:
	@echo "$(BLUE)💾 Creating database backup...$(NC)"
	mkdir -p ./backups
	docker-compose exec -T postgres pg_dump -U analyst medicaid_db > ./backups/backup_`date +%Y%m%d_%H%M%S`.sql
	@echo "$(GREEN)✅ Backup saved to ./backups/$(NC)"

db-restore:
	@echo "$(YELLOW)⚠️  Restoring database...$(NC)"
	@if [ -z "$(file)" ]; then \
		echo "$(RED)❌ Usage: make db-restore file=backup.sql$(NC)"; \
		exit 1; \
	fi
	cat $(file) | docker-compose exec -T postgres psql -U analyst medicaid_db
	@echo "$(GREEN)✅ Database restored from $(file)$(NC)"

db-reset:
	@echo "$(RED)⚠️  WARNING: This will delete ALL data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "\n$(YELLOW)Resetting database...$(NC)"; \
		docker-compose down -v; \
		docker-compose up -d postgres; \
		sleep 5; \
		docker-compose run --rm backend alembic upgrade head; \
		echo "$(GREEN)✅ Database reset complete$(NC)"; \
	else \
		echo "\n$(GREEN)Cancelled$(NC)"; \
	fi

adminer:
	@echo "$(BLUE)🌐 Starting Adminer on http://localhost:8080$(NC)"
	docker-compose --profile dev up -d adminer
	@echo "$(GREEN)✅ Adminer started. Login with: analyst / your_password / medicaid_db$(NC)"

# ---------------------------------------------------------------------------
# Analysis Commands
# ---------------------------------------------------------------------------

sweep:
	@echo "$(BLUE)🔍 Running NYC elderly care sweep...$(NC)"
	docker-compose exec backend python scripts/run_analysis.py --sweep --min-risk 70 --output /app/exports/sweep_`date +%Y%m%d_%H%M%S`.csv
	@echo "$(GREEN)✅ Sweep complete. Check ./exports/$(NC)"

provider:
	@if [ -z "$(id)" ]; then \
		echo "$(RED)❌ Usage: make provider id=12345$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🔍 Analyzing provider $(id)...$(NC)"
	docker-compose exec backend python scripts/run_analysis.py --provider $(id) --verbose --output-dir /app/exports

export:
	@echo "$(BLUE)📦 Exporting all high-risk cases...$(NC)"
	docker-compose exec backend python scripts/export_cases.py --all --format both --output /app/exports
	@echo "$(GREEN)✅ Exports saved to ./exports/$(NC)"

reports:
	@echo "$(BLUE)📊 Generating all reports...$(NC)"
	docker-compose exec backend python scripts/generate_reports.py --all --output /app/exports
	@echo "$(GREEN)✅ Reports saved to ./exports/$(NC)"

# ---------------------------------------------------------------------------
# Data Commands
# ---------------------------------------------------------------------------

load-data:
	@echo "$(BLUE)📥 Loading Medicaid dataset...$(NC)"
	docker-compose exec backend python scripts/load_data.py --chunksize 50000
	@echo "$(GREEN)✅ Data loading complete$(NC)"

sample:
	@echo "$(BLUE)📥 Loading sample (100k rows) for testing...$(NC)"
	docker-compose exec backend python scripts/load_data.py --sample 100000 --chunksize 10000
	@echo "$(GREEN)✅ Sample data loaded$(NC)"

validate:
	@echo "$(BLUE)✅ Validating dataset...$(NC)"
	docker-compose exec backend python scripts/validate_data.py --file /app/data/medicaid_claims.zip --quick

# ---------------------------------------------------------------------------
# Maintenance Commands
# ---------------------------------------------------------------------------

clean:
	@echo "$(RED)🧹 Removing containers and volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✅ Clean complete$(NC)"

prune:
	@echo "$(RED)🧹 Docker system prune...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✅ Prune complete$(NC)"

shell:
	@echo "$(BLUE)🐚 Opening backend shell...$(NC)"
	docker-compose exec backend /bin/bash

test:
	@echo "$(BLUE)🧪 Running all tests...$(NC)"
	docker-compose exec backend pytest tests/ -v

coverage:
	@echo "$(BLUE)📊 Running tests with coverage...$(NC)"
	docker-compose exec backend pytest tests/ --cov=app --cov-report=term --cov-report=html:/app/exports/coverage
	@echo "$(GREEN)✅ Coverage report saved to ./exports/coverage/$(NC)"

# ---------------------------------------------------------------------------
# Quick commands
# ---------------------------------------------------------------------------

all: up sweep export reports
	@echo "$(GREEN)🎯 Full analysis complete!$(NC)"

dev: up adminer
	@echo "$(GREEN)🎯 Development environment ready!$(NC)"

# ---------------------------------------------------------------------------
# Help (default target)
# ---------------------------------------------------------------------------

.DEFAULT_GOAL := help
