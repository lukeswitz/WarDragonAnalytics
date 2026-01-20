# WarDragon Analytics - Documentation Index

Complete guide to all documentation for the WarDragon Analytics project.

## Quick Start

**New to WarDragon Analytics? Start here:**

1. Read [README.md](README.md) - Project overview
2. Read [DOCKER_COMPOSE_SUMMARY.md](DOCKER_COMPOSE_SUMMARY.md) - Complete deployment summary
3. Run `./quickstart.sh` - Automated setup
4. Read [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed deployment guide

## Documentation Overview

### 📋 Core Documentation

#### [README.md](README.md)
**Purpose:** Project overview and introduction
**Topics:** Features, architecture overview, quick start
**Audience:** Everyone
**When to read:** First document to read

#### [DOCKER_COMPOSE_SUMMARY.md](DOCKER_COMPOSE_SUMMARY.md)
**Purpose:** Complete Docker setup summary
**Topics:** All files created, architecture, quick start, common operations
**Audience:** DevOps, developers, system administrators
**When to read:** Before deploying for the first time
**Size:** 11.2 KB - Comprehensive overview

### 🚀 Deployment Documentation

#### [DEPLOYMENT.md](DEPLOYMENT.md)
**Purpose:** Step-by-step deployment guide
**Topics:**
- Quick start instructions
- Production deployment
- Security hardening
- Reverse proxy setup (nginx)
- Backup and restore
- Maintenance procedures
- Troubleshooting
- Performance tuning

**Audience:** System administrators, DevOps engineers
**When to read:** When deploying to any environment
**Size:** 9.8 KB

#### [QUICKSTART.md](QUICKSTART.md)
**Purpose:** Rapid deployment guide
**Topics:** Fast setup, minimal configuration
**Audience:** Developers, quick testing
**When to read:** When you want to get started quickly

### 🔒 Security Documentation

#### [SECURITY.md](SECURITY.md)
**Purpose:** Comprehensive security guidelines
**Topics:**
- Security checklist
- Network security
- Authentication and authorization
- Data security
- Access control
- Monitoring and auditing
- System hardening (OS, Docker, PostgreSQL, Grafana)
- Incident response procedures
- Compliance considerations
- Regular maintenance schedule

**Audience:** Security engineers, system administrators
**When to read:** Before production deployment, during security audits
**Size:** 9.1 KB
**⚠️ CRITICAL:** Review before production deployment

### 🐳 Docker Documentation

#### [DOCKER_SETUP.md](DOCKER_SETUP.md)
**Purpose:** Complete Docker configuration reference
**Topics:**
- Service architecture
- Network configuration
- Volume management
- Environment variables
- Troubleshooting
- Upgrade procedures
- Performance tuning
- Production checklist

**Audience:** Docker administrators, DevOps engineers
**When to read:** When working with Docker configuration
**Size:** 10.5 KB

### ✅ Verification Documentation

#### [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md)
**Purpose:** Setup verification and testing
**Topics:**
- File verification checklist
- Configuration verification
- Functional verification
- Security verification
- Production readiness checklist
- Automated verification scripts

**Audience:** QA, DevOps, system administrators
**When to read:** After deployment, before production
**Size:** 13.5 KB

### 🏗️ Architecture Documentation

#### [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
**Purpose:** System architecture and design
**Topics:**
- Data sources (DragonSync API)
- Architecture diagram
- Database schema (TimescaleDB)
- Component descriptions
- Deployment options
- API compatibility
- Performance targets

**Audience:** Developers, architects, technical leads
**When to read:** When understanding system design
**Size:** 15.6 KB (from earlier read)

## Configuration Files

### Docker Configuration

#### docker-compose.yml
**Purpose:** Main Docker Compose configuration
**Contains:** 4 services (timescaledb, collector, web, grafana)
**Size:** 5.2 KB

#### docker-compose.prod.yml
**Purpose:** Production-specific overrides
**Contains:** Resource limits, enhanced logging, restart policies
**Size:** 2.2 KB

#### docker-compose.override.yml.example
**Purpose:** Development environment template
**Contains:** Debug settings, hot reload, volume mounts
**Size:** 1.9 KB

### Environment Configuration

#### .env.example
**Purpose:** Environment variable template
**Contains:** All configurable parameters with documentation
**Size:** 3.5 KB
**Action required:** Copy to .env and update passwords

### Application Configuration

#### config/kits.yaml
**Purpose:** WarDragon kit definitions
**Contains:** Kit IDs, names, API URLs, enabled status
**Size:** 1.3 KB
**Action required:** Configure your actual kits

### Grafana Configuration

#### grafana/datasources/timescaledb.yaml
**Purpose:** Auto-provisioned TimescaleDB datasource
**Size:** 379 bytes

#### grafana/dashboards/dashboard-provider.yaml
**Purpose:** Dashboard auto-provisioning configuration
**Size:** 277 bytes

## Management Scripts

### Makefile
**Purpose:** Common operations and shortcuts
**Size:** 5.7 KB
**Run:** `make help` to see all commands

**Key commands:**
```bash
make setup          # Initial setup
make start          # Start services
make stop           # Stop services
make logs           # View logs
make backup         # Backup database
make health         # Health check
```

### quickstart.sh
**Purpose:** Automated setup and deployment
**Size:** 4.2 KB
**Run:** `./quickstart.sh`

**Features:**
- Checks prerequisites
- Generates passwords
- Creates directories
- Starts services
- Displays access information

### healthcheck.sh
**Purpose:** Comprehensive health monitoring
**Size:** 3.6 KB
**Run:** `./healthcheck.sh`

**Checks:**
- Service health
- Database connectivity
- Disk space
- Resource usage
- Database statistics

## Systemd Integration

### wardragon-analytics.service
**Purpose:** Systemd service unit for auto-start
**Size:** 1.6 KB

**Installation:**
```bash
sudo cp wardragon-analytics.service /etc/systemd/system/
sudo systemctl enable wardragon-analytics
sudo systemctl start wardragon-analytics
```

## Additional Scripts

Located in `scripts/` directory:

- **backup.sh** - Database backup automation
- **cleanup.sh** - Clean up old data and logs
- **fix-permissions.sh** - Fix volume permissions
- **logs.sh** - Log viewing helper
- **reset-db.sh** - Database reset (development)
- **start.sh** - Service startup helper
- **stop.sh** - Service shutdown helper

## Documentation by Use Case

### 🎯 I want to...

#### Deploy for the first time
1. [DOCKER_COMPOSE_SUMMARY.md](DOCKER_COMPOSE_SUMMARY.md) - Overview
2. [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment steps
3. Run `./quickstart.sh`
4. [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md) - Verify deployment

#### Deploy to production
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
2. [SECURITY.md](SECURITY.md) - Security hardening
3. [DOCKER_SETUP.md](DOCKER_SETUP.md) - Docker configuration
4. [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md) - Production checklist

#### Understand the architecture
1. [README.md](README.md) - Overview
2. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detailed architecture
3. [DOCKER_SETUP.md](DOCKER_SETUP.md) - Docker architecture

#### Troubleshoot issues
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Troubleshooting section
2. [DOCKER_SETUP.md](DOCKER_SETUP.md) - Troubleshooting guide
3. Run `./healthcheck.sh`
4. Run `make logs`

#### Secure the deployment
1. [SECURITY.md](SECURITY.md) - Complete security guide
2. [DEPLOYMENT.md](DEPLOYMENT.md) - Security hardening section
3. [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md) - Security verification

#### Configure Docker
1. [DOCKER_SETUP.md](DOCKER_SETUP.md) - Complete reference
2. [DOCKER_COMPOSE_SUMMARY.md](DOCKER_COMPOSE_SUMMARY.md) - Summary
3. `docker-compose.yml` - Configuration file
4. `.env.example` - Environment variables

#### Maintain and monitor
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Maintenance section
2. [SECURITY.md](SECURITY.md) - Monitoring section
3. Run `./healthcheck.sh` regularly
4. Run `make backup` regularly

## Documentation by Audience

### 👨‍💻 Developers
**Start here:**
1. [README.md](README.md)
2. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. [DOCKER_COMPOSE_SUMMARY.md](DOCKER_COMPOSE_SUMMARY.md)
4. `docker-compose.override.yml.example`

**Key files:**
- Application code: `app/`
- Database schema: `docs/ARCHITECTURE.md`
- API documentation: `app/README_*.md`

### 🔧 DevOps Engineers
**Start here:**
1. [DOCKER_COMPOSE_SUMMARY.md](DOCKER_COMPOSE_SUMMARY.md)
2. [DEPLOYMENT.md](DEPLOYMENT.md)
3. [DOCKER_SETUP.md](DOCKER_SETUP.md)

**Key files:**
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `Makefile`
- `wardragon-analytics.service`

### 🔒 Security Engineers
**Start here:**
1. [SECURITY.md](SECURITY.md)
2. [DEPLOYMENT.md](DEPLOYMENT.md) - Security sections
3. [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md) - Security verification

**Key concerns:**
- Network isolation
- Authentication
- Data encryption
- Audit logging
- Incident response

### 🏢 System Administrators
**Start here:**
1. [DEPLOYMENT.md](DEPLOYMENT.md)
2. [DOCKER_SETUP.md](DOCKER_SETUP.md)
3. [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md)

**Key tasks:**
- Deployment
- Backup/restore
- Monitoring
- Maintenance
- Troubleshooting

### 👨‍💼 Project Managers
**Start here:**
1. [README.md](README.md)
2. [DOCKER_COMPOSE_SUMMARY.md](DOCKER_COMPOSE_SUMMARY.md)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**Key information:**
- Project overview
- Features
- Architecture
- Deployment options

## File Size Summary

| File | Size | Type |
|------|------|------|
| SETUP_VERIFICATION.md | 13.5 KB | Documentation |
| DOCKER_SETUP.md | 10.5 KB | Documentation |
| DOCKER_COMPOSE_SUMMARY.md | 11.2 KB | Documentation |
| DEPLOYMENT.md | 9.8 KB | Documentation |
| SECURITY.md | 9.1 KB | Documentation |
| Makefile | 5.7 KB | Script |
| docker-compose.yml | 5.2 KB | Configuration |
| quickstart.sh | 4.2 KB | Script |
| healthcheck.sh | 3.6 KB | Script |
| .env.example | 3.5 KB | Configuration |
| docker-compose.prod.yml | 2.2 KB | Configuration |
| docker-compose.override.yml.example | 1.9 KB | Configuration |
| wardragon-analytics.service | 1.6 KB | Configuration |
| .gitignore | 1.4 KB | Configuration |
| config/kits.yaml | 1.3 KB | Configuration |

**Total:** ~75 KB of comprehensive documentation and configuration

## Documentation Standards

All documentation follows these standards:

✅ **Clear Structure** - Headings, sections, subsections
✅ **Code Examples** - Practical, runnable examples
✅ **Security Notes** - Warnings and best practices
✅ **Cross-References** - Links to related documentation
✅ **Step-by-Step** - Clear instructions with commands
✅ **Troubleshooting** - Common issues and solutions
✅ **Checklists** - Verification and validation

## Quick Reference Commands

```bash
# Initial Setup
./quickstart.sh

# Manual Setup
make setup
cp .env.example .env
# Edit .env with passwords
make start

# Health Check
./healthcheck.sh
make health

# View Logs
make logs
make logs-collector
make logs-web

# Backup/Restore
make backup
make restore BACKUP_FILE=backup.sql.gz

# Service Management
make start
make stop
make restart
make status

# Database Operations
make shell-db
make db-stats
make db-kits

# Cleanup
make clean  # WARNING: Deletes all data!
```

## Getting Help

### In-Application Help
```bash
make help              # Makefile commands
docker-compose --help  # Docker Compose help
```

### Documentation Search
```bash
# Search all documentation for a term
grep -r "search term" *.md docs/

# Find configuration examples
grep -r "example" config/
```

### Troubleshooting Steps
1. Run `./healthcheck.sh`
2. Check `make logs`
3. Review [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting
4. Check [DOCKER_SETUP.md](DOCKER_SETUP.md) troubleshooting
5. Verify configuration with [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md)

## Documentation Maintenance

### Updating Documentation
When making changes to the system, update:
1. Relevant .md files
2. Inline comments in configuration files
3. ARCHITECTURE.md if design changes
4. This index if new files are added

### Documentation Feedback
Documentation improvements are welcome. When proposing changes:
- Be specific about unclear sections
- Suggest improvements
- Provide examples
- Consider all audiences

## Version Information

This documentation set was created for WarDragon Analytics as of 2026-01-19.

**Docker Compose Version:** 3.8
**TimescaleDB Version:** PostgreSQL 15
**Grafana Version:** Latest
**Python Version:** 3.11+ (assumed)

## License

See [LICENSE](LICENSE) file for project license information.

## Contributing

See [README.md](README.md) for contribution guidelines.

---

**Navigation Tips:**
- Use Ctrl+F (Cmd+F on Mac) to search within documents
- Most documentation includes a table of contents
- Links are provided to jump between related documents
- All commands are copy-paste ready

**Remember:** Security is paramount. Always review [SECURITY.md](SECURITY.md) before production deployment!
