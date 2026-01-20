#!/usr/bin/env python3
"""
WarDragon Analytics Collector Service

Polls DragonSync APIs from configured WarDragon kits and stores data in TimescaleDB.

Features:
- Async polling of multiple kits every 5 seconds
- Fetches /drones, /signals, /status endpoints
- Normalizes data and writes to TimescaleDB
- Tracks kit health (online/offline/stale)
- Exponential backoff for offline kits
- Connection pooling and retry logic
- Graceful shutdown on SIGTERM/SIGINT
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import os

import httpx
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://wardragon:wardragon@localhost:5432/wardragon')
KITS_CONFIG = os.getenv('KITS_CONFIG', '/config/kits.yaml')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))  # seconds
STATUS_POLL_INTERVAL = int(os.getenv('STATUS_POLL_INTERVAL', '30'))  # seconds
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))  # seconds
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
INITIAL_BACKOFF = float(os.getenv('INITIAL_BACKOFF', '5.0'))  # seconds
MAX_BACKOFF = float(os.getenv('MAX_BACKOFF', '300.0'))  # 5 minutes
STALE_THRESHOLD = int(os.getenv('STALE_THRESHOLD', '60'))  # seconds

# Global shutdown event
shutdown_event = asyncio.Event()


class KitHealth:
    """Tracks health status and backoff for a kit"""

    def __init__(self, kit_id: str):
        self.kit_id = kit_id
        self.status = 'unknown'  # unknown, online, offline, stale, error
        self.last_seen: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.consecutive_failures = 0
        self.backoff_delay = INITIAL_BACKOFF
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    def mark_success(self):
        """Mark successful poll"""
        self.status = 'online'
        self.last_seen = datetime.now(timezone.utc)
        self.consecutive_failures = 0
        self.backoff_delay = INITIAL_BACKOFF
        self.total_requests += 1
        self.successful_requests += 1
        self.last_error = None

    def mark_failure(self, error: str):
        """Mark failed poll and calculate backoff"""
        self.status = 'offline'
        self.last_error = error
        self.consecutive_failures += 1
        self.total_requests += 1
        self.failed_requests += 1

        # Exponential backoff: delay = min(initial * 2^failures, max)
        self.backoff_delay = min(
            INITIAL_BACKOFF * (2 ** self.consecutive_failures),
            MAX_BACKOFF
        )
        logger.warning(
            f"Kit {self.kit_id} failed (attempt {self.consecutive_failures}). "
            f"Next retry in {self.backoff_delay:.1f}s. Error: {error}"
        )

    def mark_stale(self):
        """Mark as stale if no data received recently"""
        if self.last_seen:
            age = (datetime.now(timezone.utc) - self.last_seen).total_seconds()
            if age > STALE_THRESHOLD:
                self.status = 'stale'
                logger.warning(f"Kit {self.kit_id} marked stale (last seen {age:.0f}s ago)")

    def get_next_poll_delay(self) -> float:
        """Get delay until next poll attempt"""
        if self.status == 'online':
            return 0.0  # Poll immediately
        return self.backoff_delay

    def get_stats(self) -> Dict[str, Any]:
        """Get health statistics"""
        success_rate = (
            (self.successful_requests / self.total_requests * 100)
            if self.total_requests > 0 else 0.0
        )
        return {
            'status': self.status,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'consecutive_failures': self.consecutive_failures,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': f"{success_rate:.1f}%",
            'next_retry_delay': self.backoff_delay,
            'last_error': self.last_error
        }


class DatabaseWriter:
    """Handles database connections and writes"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self._connect()

    def _connect(self):
        """Create database engine with connection pooling"""
        try:
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,   # Recycle connections after 1 hour
                echo=False
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise

    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def insert_drones(self, kit_id: str, drones: List[Dict]) -> int:
        """Insert drone records into database"""
        if not drones:
            return 0

        inserted = 0
        try:
            with self.engine.connect() as conn:
                for drone in drones:
                    try:
                        query = text("""
                            INSERT INTO drones (
                                time, kit_id, drone_id, lat, lon, alt, speed, heading,
                                pilot_lat, pilot_lon, home_lat, home_lon,
                                mac, rssi, freq, ua_type, operator_id, caa_id,
                                rid_make, rid_model, rid_source, track_type
                            ) VALUES (
                                :time, :kit_id, :drone_id, :lat, :lon, :alt, :speed, :heading,
                                :pilot_lat, :pilot_lon, :home_lat, :home_lon,
                                :mac, :rssi, :freq, :ua_type, :operator_id, :caa_id,
                                :rid_make, :rid_model, :rid_source, :track_type
                            )
                            ON CONFLICT (time, kit_id, drone_id) DO UPDATE SET
                                lat = EXCLUDED.lat,
                                lon = EXCLUDED.lon,
                                alt = EXCLUDED.alt,
                                speed = EXCLUDED.speed,
                                heading = EXCLUDED.heading
                        """)

                        # Normalize timestamp
                        timestamp = self._parse_timestamp(drone.get('timestamp'))

                        # Determine track type
                        track_type = drone.get('track_type', 'drone')
                        if drone.get('icao'):
                            track_type = 'aircraft'

                        conn.execute(query, {
                            'time': timestamp,
                            'kit_id': kit_id,
                            'drone_id': drone.get('drone_id') or drone.get('icao') or drone.get('mac', 'unknown'),
                            'lat': self._safe_float(drone.get('lat')),
                            'lon': self._safe_float(drone.get('lon')),
                            'alt': self._safe_float(drone.get('alt') or drone.get('altitude')),
                            'speed': self._safe_float(drone.get('speed')),
                            'heading': self._safe_float(drone.get('heading')),
                            'pilot_lat': self._safe_float(drone.get('pilot_lat')),
                            'pilot_lon': self._safe_float(drone.get('pilot_lon')),
                            'home_lat': self._safe_float(drone.get('home_lat')),
                            'home_lon': self._safe_float(drone.get('home_lon')),
                            'mac': drone.get('mac'),
                            'rssi': self._safe_int(drone.get('rssi')),
                            'freq': self._safe_float(drone.get('freq')),
                            'ua_type': drone.get('ua_type'),
                            'operator_id': drone.get('operator_id'),
                            'caa_id': drone.get('caa_id'),
                            'rid_make': drone.get('rid_make') or drone.get('make'),
                            'rid_model': drone.get('rid_model') or drone.get('model'),
                            'rid_source': drone.get('rid_source') or drone.get('source'),
                            'track_type': track_type
                        })
                        conn.commit()
                        inserted += 1
                    except SQLAlchemyError as e:
                        logger.error(f"Failed to insert drone record: {e}")
                        conn.rollback()
                        continue

            if inserted > 0:
                logger.debug(f"Inserted {inserted} drone records for kit {kit_id}")
            return inserted
        except Exception as e:
            logger.error(f"Failed to insert drones for kit {kit_id}: {e}")
            return 0

    async def insert_signals(self, kit_id: str, signals: List[Dict]) -> int:
        """Insert signal records into database"""
        if not signals:
            return 0

        inserted = 0
        try:
            with self.engine.connect() as conn:
                for signal in signals:
                    try:
                        query = text("""
                            INSERT INTO signals (
                                time, kit_id, freq_mhz, power_dbm, bandwidth_mhz,
                                lat, lon, alt, detection_type
                            ) VALUES (
                                :time, :kit_id, :freq_mhz, :power_dbm, :bandwidth_mhz,
                                :lat, :lon, :alt, :detection_type
                            )
                            ON CONFLICT (time, kit_id, freq_mhz) DO UPDATE SET
                                power_dbm = EXCLUDED.power_dbm
                        """)

                        timestamp = self._parse_timestamp(signal.get('timestamp'))

                        # Determine detection type
                        freq = self._safe_float(signal.get('freq_mhz') or signal.get('freq'))
                        detection_type = signal.get('type', 'analog')
                        if freq and 5600 <= freq <= 5900:
                            detection_type = signal.get('type', 'analog')

                        conn.execute(query, {
                            'time': timestamp,
                            'kit_id': kit_id,
                            'freq_mhz': freq,
                            'power_dbm': self._safe_float(signal.get('power_dbm') or signal.get('power')),
                            'bandwidth_mhz': self._safe_float(signal.get('bandwidth_mhz') or signal.get('bandwidth')),
                            'lat': self._safe_float(signal.get('lat')),
                            'lon': self._safe_float(signal.get('lon')),
                            'alt': self._safe_float(signal.get('alt')),
                            'detection_type': detection_type
                        })
                        conn.commit()
                        inserted += 1
                    except SQLAlchemyError as e:
                        logger.error(f"Failed to insert signal record: {e}")
                        conn.rollback()
                        continue

            if inserted > 0:
                logger.debug(f"Inserted {inserted} signal records for kit {kit_id}")
            return inserted
        except Exception as e:
            logger.error(f"Failed to insert signals for kit {kit_id}: {e}")
            return 0

    async def insert_health(self, kit_id: str, status: Dict) -> bool:
        """Insert system health record into database"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO system_health (
                        time, kit_id, lat, lon, alt,
                        cpu_percent, memory_percent, disk_percent,
                        uptime_hours, temp_cpu, temp_gpu
                    ) VALUES (
                        :time, :kit_id, :lat, :lon, :alt,
                        :cpu_percent, :memory_percent, :disk_percent,
                        :uptime_hours, :temp_cpu, :temp_gpu
                    )
                    ON CONFLICT (time, kit_id) DO UPDATE SET
                        cpu_percent = EXCLUDED.cpu_percent,
                        memory_percent = EXCLUDED.memory_percent,
                        disk_percent = EXCLUDED.disk_percent
                """)

                timestamp = self._parse_timestamp(status.get('timestamp'))

                # Extract GPS data
                gps = status.get('gps', {})

                # Extract system metrics
                cpu = status.get('cpu', {})
                memory = status.get('memory', {})
                disk = status.get('disk', {})
                temps = status.get('temps', {})

                conn.execute(query, {
                    'time': timestamp,
                    'kit_id': kit_id,
                    'lat': self._safe_float(gps.get('lat')),
                    'lon': self._safe_float(gps.get('lon')),
                    'alt': self._safe_float(gps.get('alt')),
                    'cpu_percent': self._safe_float(cpu.get('percent')),
                    'memory_percent': self._safe_float(memory.get('percent')),
                    'disk_percent': self._safe_float(disk.get('percent')),
                    'uptime_hours': self._safe_float(status.get('uptime_hours')),
                    'temp_cpu': self._safe_float(temps.get('cpu')),
                    'temp_gpu': self._safe_float(temps.get('gpu'))
                })
                conn.commit()

                logger.debug(f"Inserted health record for kit {kit_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to insert health for kit {kit_id}: {e}")
            return False

    async def update_kit_status(self, kit_id: str, status: str, last_seen: datetime):
        """Update kit status in kits table"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO kits (kit_id, status, last_seen)
                    VALUES (:kit_id, :status, :last_seen)
                    ON CONFLICT (kit_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_seen = EXCLUDED.last_seen
                """)
                conn.execute(query, {
                    'kit_id': kit_id,
                    'status': status,
                    'last_seen': last_seen
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update kit status: {e}")

    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp from various formats"""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                pass
        # Default to current time
        return datetime.now(timezone.utc)

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def close(self):
        """Close database connection pool"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection pool closed")


class KitCollector:
    """Handles polling and data collection for a single kit"""

    def __init__(self, kit_config: Dict, db: DatabaseWriter, client: httpx.AsyncClient):
        self.kit_id = kit_config['id']
        self.name = kit_config.get('name', self.kit_id)
        self.api_url = kit_config['api_url'].rstrip('/')
        self.location = kit_config.get('location', 'Unknown')
        self.enabled = kit_config.get('enabled', True)

        self.db = db
        self.client = client
        self.health = KitHealth(self.kit_id)

        logger.info(f"Initialized collector for kit {self.kit_id} ({self.name}) at {self.api_url}")

    async def fetch_json(self, endpoint: str, retry: int = 0) -> Optional[Dict]:
        """Fetch JSON data from kit endpoint with retry logic"""
        url = f"{self.api_url}{endpoint}"

        try:
            response = await self.client.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            error = f"Timeout fetching {endpoint}"
            if retry < MAX_RETRIES:
                logger.debug(f"Kit {self.kit_id}: {error}, retrying ({retry + 1}/{MAX_RETRIES})")
                await asyncio.sleep(1 * (retry + 1))  # Linear backoff for retries
                return await self.fetch_json(endpoint, retry + 1)
            logger.error(f"Kit {self.kit_id}: {error} after {MAX_RETRIES} retries")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Kit {self.kit_id}: HTTP {e.response.status_code} fetching {endpoint}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Kit {self.kit_id}: Request error fetching {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Kit {self.kit_id}: Unexpected error fetching {endpoint}: {e}")
            return None

    async def poll_drones(self) -> bool:
        """Poll /drones endpoint and store data"""
        data = await self.fetch_json('/drones')
        if data is None:
            return False

        # Handle both {drones: [...]} and [...] formats
        drones = data if isinstance(data, list) else data.get('drones', [])

        if drones:
            inserted = await self.db.insert_drones(self.kit_id, drones)
            logger.info(f"Kit {self.kit_id}: Collected {len(drones)} drones, inserted {inserted}")

        return True

    async def poll_signals(self) -> bool:
        """Poll /signals endpoint and store data"""
        data = await self.fetch_json('/signals')
        if data is None:
            return False

        # Handle both {signals: [...]} and [...] formats
        signals = data if isinstance(data, list) else data.get('signals', [])

        if signals:
            inserted = await self.db.insert_signals(self.kit_id, signals)
            logger.info(f"Kit {self.kit_id}: Collected {len(signals)} signals, inserted {inserted}")

        return True

    async def poll_status(self) -> bool:
        """Poll /status endpoint and store data"""
        data = await self.fetch_json('/status')
        if data is None:
            return False

        success = await self.db.insert_health(self.kit_id, data)
        if success:
            logger.info(f"Kit {self.kit_id}: Collected system status")

        return True

    async def poll_all_endpoints(self) -> bool:
        """Poll all endpoints for this kit"""
        # Poll drones and signals endpoints
        results = await asyncio.gather(
            self.poll_drones(),
            self.poll_signals(),
            return_exceptions=True
        )

        # Check if any succeeded
        success = any(r is True for r in results)

        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                endpoint = ['/drones', '/signals'][i]
                logger.error(f"Kit {self.kit_id}: Exception polling {endpoint}: {result}")

        return success

    async def run(self):
        """Main polling loop for this kit"""
        logger.info(f"Starting collector for kit {self.kit_id}")

        status_poll_counter = 0
        status_interval_cycles = STATUS_POLL_INTERVAL // POLL_INTERVAL

        while not shutdown_event.is_set():
            if not self.enabled:
                await asyncio.sleep(POLL_INTERVAL)
                continue

            try:
                # Poll drones and signals
                success = await self.poll_all_endpoints()

                # Poll status less frequently
                status_poll_counter += 1
                if status_poll_counter >= status_interval_cycles:
                    status_success = await self.poll_status()
                    success = success or status_success
                    status_poll_counter = 0

                # Update health status
                if success:
                    self.health.mark_success()
                    await self.db.update_kit_status(
                        self.kit_id,
                        self.health.status,
                        self.health.last_seen
                    )
                else:
                    self.health.mark_failure("Failed to fetch data from any endpoint")
                    await self.db.update_kit_status(
                        self.kit_id,
                        self.health.status,
                        datetime.now(timezone.utc)
                    )

                # Calculate next poll delay
                if success:
                    delay = POLL_INTERVAL
                else:
                    # Use exponential backoff for failed kits
                    delay = self.health.get_next_poll_delay()
                    logger.info(f"Kit {self.kit_id}: Backing off for {delay:.1f}s")

                # Wait for next poll or shutdown
                try:
                    await asyncio.wait_for(
                        shutdown_event.wait(),
                        timeout=delay
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue polling

            except Exception as e:
                logger.error(f"Kit {self.kit_id}: Unexpected error in polling loop: {e}", exc_info=True)
                self.health.mark_failure(str(e))
                await asyncio.sleep(POLL_INTERVAL)

        logger.info(f"Stopped collector for kit {self.kit_id}")


class CollectorService:
    """Main collector service that manages all kit collectors"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.kits = []
        self.db = None
        self.client = None
        self.tasks = []
        self.health_stats = {}

    def load_config(self) -> List[Dict]:
        """Load kits configuration from YAML file"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            kits = config.get('kits', [])
            logger.info(f"Loaded {len(kits)} kits from configuration")

            # Validate configuration
            for kit in kits:
                if 'id' not in kit:
                    raise ValueError("Kit configuration missing 'id' field")
                if 'api_url' not in kit:
                    raise ValueError(f"Kit {kit['id']} missing 'api_url' field")

            return kits
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    async def start(self):
        """Start the collector service"""
        logger.info("Starting WarDragon Analytics Collector Service")
        logger.info(f"Poll interval: {POLL_INTERVAL}s")
        logger.info(f"Status poll interval: {STATUS_POLL_INTERVAL}s")
        logger.info(f"Request timeout: {REQUEST_TIMEOUT}s")

        # Load configuration
        kit_configs = self.load_config()

        # Initialize database
        logger.info("Initializing database connection...")
        self.db = DatabaseWriter(DATABASE_URL)

        if not self.db.test_connection():
            logger.error("Database connection test failed. Exiting.")
            sys.exit(1)

        # Initialize HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
            follow_redirects=True
        )
        logger.info("HTTP client initialized with connection pooling")

        # Create kit collectors
        enabled_kits = [k for k in kit_configs if k.get('enabled', True)]
        logger.info(f"Starting collectors for {len(enabled_kits)} enabled kits")

        for kit_config in enabled_kits:
            collector = KitCollector(kit_config, self.db, self.client)
            self.kits.append(collector)
            self.health_stats[kit_config['id']] = collector.health

        # Start collector tasks
        for kit in self.kits:
            task = asyncio.create_task(kit.run())
            self.tasks.append(task)

        logger.info(f"Collector service started with {len(self.tasks)} active collectors")

        # Start health monitoring task
        health_task = asyncio.create_task(self.monitor_health())
        self.tasks.append(health_task)

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Wait for all tasks to complete
        logger.info("Waiting for collector tasks to complete...")
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("All collector tasks completed")

    async def monitor_health(self):
        """Periodically log health statistics for all kits"""
        while not shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # Log every minute

                if shutdown_event.is_set():
                    break

                logger.info("=== Kit Health Status ===")
                for kit_id, health in self.health_stats.items():
                    health.mark_stale()
                    stats = health.get_stats()
                    logger.info(
                        f"Kit {kit_id}: {stats['status']} | "
                        f"Success rate: {stats['success_rate']} | "
                        f"Requests: {stats['total_requests']} "
                        f"(OK: {stats['successful_requests']}, Failed: {stats['failed_requests']})"
                    )
                    if stats['last_error']:
                        logger.info(f"  Last error: {stats['last_error']}")
                logger.info("=" * 40)

            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")

    async def shutdown(self):
        """Gracefully shutdown the service"""
        logger.info("Initiating graceful shutdown...")
        shutdown_event.set()

        # Close HTTP client
        if self.client:
            await self.client.aclose()
            logger.info("HTTP client closed")

        # Close database connection
        if self.db:
            self.db.close()

        logger.info("Shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received signal {sig_name}, initiating shutdown...")
    shutdown_event.set()


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and run service
    service = CollectorService(KITS_CONFIG)

    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Collector service stopped")


if __name__ == '__main__':
    main()
