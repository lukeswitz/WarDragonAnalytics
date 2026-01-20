.PHONY: help setup start stop restart logs clean backup restore status health

# Default target
help:
	@echo "WarDragon Analytics - Docker Compose Management"
	@echo ""
	@echo "Available targets:"
	@echo "  setup       - Initial setup (copy .env.example, create directories)"
	@echo "  start       - Start all services"
	@echo "  stop        - Stop all services"
	@echo "  restart     - Restart all services"
	@echo "  logs        - Tail logs from all services"
	@echo "  status      - Show service status"
	@echo "  health      - Check health of all services"
	@echo "  clean       - Remove containers and volumes (WARNING: deletes data!)"
	@echo "  backup      - Backup database to backups/ directory"
	@echo "  restore     - Restore database from backup (set BACKUP_FILE=path)"
	@echo "  shell-db    - Open psql shell to TimescaleDB"
	@echo "  shell-collector - Open shell in collector container"
	@echo "  shell-web   - Open shell in web container"
	@echo ""
	@echo "Service-specific logs:"
	@echo "  logs-collector  - Tail collector logs"
	@echo "  logs-web        - Tail web logs"
	@echo "  logs-grafana    - Tail Grafana logs"
	@echo "  logs-db         - Tail TimescaleDB logs"

setup:
	@echo "Setting up WarDragon Analytics..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file - EDIT THIS FILE with your passwords!"; \
	else \
		echo ".env already exists, skipping..."; \
	fi
	@mkdir -p volumes/timescale-data volumes/grafana-data logs/collector config
	@chmod 700 volumes/timescale-data volumes/grafana-data
	@echo "Created directories"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env and set strong passwords"
	@echo "2. Edit config/kits.yaml to define your WarDragon kits"
	@echo "3. Run 'make start' to start services"

start:
	@echo "Starting WarDragon Analytics..."
	docker-compose up -d
	@echo "Services starting... Run 'make status' to check status"
	@echo "Web UI will be available at http://localhost:8080"
	@echo "Grafana will be available at http://localhost:3000"

stop:
	@echo "Stopping WarDragon Analytics..."
	docker-compose down

restart:
	@echo "Restarting WarDragon Analytics..."
	docker-compose restart

logs:
	docker-compose logs -f

logs-collector:
	docker-compose logs -f collector

logs-web:
	docker-compose logs -f web

logs-grafana:
	docker-compose logs -f grafana

logs-db:
	docker-compose logs -f timescaledb

status:
	@echo "Service Status:"
	@docker-compose ps

health:
	@echo "Checking service health..."
	@echo ""
	@echo "TimescaleDB:"
	@docker exec wardragon-timescaledb pg_isready -U wardragon || echo "  UNHEALTHY"
	@echo ""
	@echo "Web API:"
	@curl -sf http://localhost:8080/health > /dev/null && echo "  HEALTHY" || echo "  UNHEALTHY"
	@echo ""
	@echo "Grafana:"
	@curl -sf http://localhost:3000/api/health > /dev/null && echo "  HEALTHY" || echo "  UNHEALTHY"
	@echo ""
	@echo "Docker Compose Status:"
	@docker-compose ps

clean:
	@echo "WARNING: This will remove all containers and volumes (including data)!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose down -v; \
		echo "Containers and volumes removed"; \
	else \
		echo "Cancelled"; \
	fi

backup:
	@mkdir -p backups
	@BACKUP_FILE=backups/wardragon_backup_$$(date +%Y%m%d_%H%M%S).sql.gz; \
	echo "Backing up database to $$BACKUP_FILE..."; \
	docker exec wardragon-timescaledb pg_dump -U wardragon wardragon | gzip > $$BACKUP_FILE; \
	echo "Backup complete: $$BACKUP_FILE"

restore:
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "ERROR: BACKUP_FILE not specified"; \
		echo "Usage: make restore BACKUP_FILE=backups/wardragon_backup_20260119.sql.gz"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "ERROR: Backup file not found: $(BACKUP_FILE)"; \
		exit 1; \
	fi
	@echo "Restoring database from $(BACKUP_FILE)..."
	@if echo "$(BACKUP_FILE)" | grep -q ".gz$$"; then \
		gunzip -c $(BACKUP_FILE) | docker exec -i wardragon-timescaledb psql -U wardragon wardragon; \
	else \
		docker exec -i wardragon-timescaledb psql -U wardragon wardragon < $(BACKUP_FILE); \
	fi
	@echo "Restore complete"

shell-db:
	docker exec -it wardragon-timescaledb psql -U wardragon wardragon

shell-collector:
	docker exec -it wardragon-collector /bin/bash

shell-web:
	docker exec -it wardragon-web /bin/bash

pull:
	@echo "Pulling latest images..."
	docker-compose pull

build:
	@echo "Building application containers..."
	docker-compose build

update: pull build restart
	@echo "Update complete"

# Development targets
dev-setup:
	@if [ ! -f docker-compose.override.yml ]; then \
		cp docker-compose.override.yml.example docker-compose.override.yml; \
		echo "Created docker-compose.override.yml for development"; \
	fi
	@make setup

dev-start:
	@echo "Starting in development mode..."
	@docker-compose up

# Show database stats
db-stats:
	@echo "Database Statistics:"
	@docker exec wardragon-timescaledb psql -U wardragon wardragon -c "\
		SELECT \
			schemaname, \
			tablename, \
			pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size \
		FROM pg_tables \
		WHERE schemaname = 'public' \
		ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Show recent drone detections
db-drones:
	@echo "Recent Drone Detections (last 10):"
	@docker exec wardragon-timescaledb psql -U wardragon wardragon -c "\
		SELECT time, kit_id, drone_id, lat, lon, alt, rid_make, rid_model \
		FROM drones \
		ORDER BY time DESC \
		LIMIT 10;" 2>/dev/null || echo "Table 'drones' does not exist yet"

# Show kit status
db-kits:
	@echo "Configured Kits Status:"
	@docker exec wardragon-timescaledb psql -U wardragon wardragon -c "\
		SELECT kit_id, name, status, last_seen, api_url \
		FROM kits \
		ORDER BY last_seen DESC;" 2>/dev/null || echo "Table 'kits' does not exist yet"
