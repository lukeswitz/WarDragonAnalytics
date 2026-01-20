# Test Data Generator - Data Flow

## Overview

```
┌──────────────────────────────────────────────────────────────┐
│              test_data_generator.py                          │
│  Simulates real-world WarDragon kit data over time          │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ Generates
                            ▼
        ┌───────────────────────────────────────┐
        │                                       │
        │  Time Simulation (e.g., 2 hours)      │
        │  - Start: Now - 2h                    │
        │  - End: Now                           │
        │  - Interval: 5 seconds                │
        │                                       │
        └───────────────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
      ┌────────┐      ┌──────────┐    ┌───────────┐
      │ Kits   │      │ Drones   │    │ Signals   │
      │ (1-5)  │      │ (10-100) │    │ (random)  │
      └────────┘      └──────────┘    └───────────┘
           │                │                │
           │                │                │
           ▼                ▼                ▼
    ┌──────────┐    ┌──────────────┐  ┌────────────┐
    │ Kit Base │    │ Flight Paths │  │ FPV Freqs  │
    │ Location │    │ - Waypoints  │  │ - 5.8 GHz  │
    │ GPS      │    │ - Speed      │  │ - DJI      │
    └──────────┘    │ - Altitude   │  └────────────┘
                    │ - Heading    │
                    └──────────────┘
                            │
           ┌────────────────┴────────────────┐
           ▼                                 ▼
    ┌─────────────┐                  ┌──────────────┐
    │ Output Mode │                  │ Output Mode  │
    │    SQL      │                  │   Database   │
    └─────────────┘                  └──────────────┘
           │                                 │
           ▼                                 ▼
    ┌─────────────┐                  ┌──────────────┐
    │ INSERT      │                  │ TimescaleDB  │
    │ statements  │                  │ - drones     │
    │ (stdout)    │                  │ - signals    │
    └─────────────┘                  │ - health     │
                                     │ - kits       │
                                     └──────────────┘
```

## Data Generation Process

### Phase 1: Initialization

```
1. Parse CLI arguments (--mode, --duration, --kits, --drones)
2. Calculate time range (end_time = now, start_time = now - duration)
3. Select kit locations from predefined GPS coordinates
4. Generate kit records and insert/print
```

### Phase 2: Drone Track Creation

```
For each kit:
  For each drone (random count around --drones):
    1. Generate drone metadata:
       - Serial number (e.g., DJI485729)
       - MAC address (random)
       - Operator ID (FAA format)
       - Make/Model (DJI Mini 3 Pro, etc.)
       - UA type (Helicopter/Multirotor, etc.)

    2. Generate flight plan:
       - Random start time within duration
       - Flight duration: 5-45 minutes
       - Pilot location (within 5km of kit)
       - Home point (same as pilot)
       - 3-8 GPS waypoints
       - Max speed: 5-20 m/s
       - Max altitude: 30-120 m

    3. Store as DroneTrack object
```

### Phase 3: Time Progression Loop

```
current_time = start_time

while current_time <= end_time:
    # Every 5 seconds (drone update rate)
    For each drone track:
        if current_time in [track.start_time, track.end_time]:
            position = interpolate_waypoint(current_time)
            if position:
                generate_drone_record(position)
                add_to_batch()

    # Probabilistic signal generation
    For each kit:
        if random() < signal_probability:
            generate_fpv_signal()
            add_to_batch()

    # Every 30 seconds (health update rate)
    if current_time % 30s == 0:
        For each kit:
            generate_health_record()
            add_to_batch()

    # Batch insert/print when batch_size reached
    if batch_size >= 1000:
        insert_or_print_batch()
        clear_batch()

    current_time += 5 seconds
```

## Data Volume Estimates

### Small Test (15 minutes, 1 kit, 3 drones)
```
Kits:          1
Drone records: ~540    (3 drones × 180 intervals)
Signal records: ~162   (30% × 540 intervals)
Health records: 30     (1 kit × 30 intervals)
Total:         ~732 records
```

### Standard Test (2 hours, 3 kits, 15 drones)
```
Kits:          3
Drone records: ~45,000  (45 drones × 1,440 intervals × ~70% active)
Signal records: ~6,500  (30% × 3 kits × 1,440 intervals)
Health records: 720     (3 kits × 240 intervals)
Total:         ~52,220 records
```

### Large Test (4 hours, 5 kits, 20 drones)
```
Kits:          5
Drone records: ~120,000 (100 drones × 2,880 intervals × ~70% active)
Signal records: ~21,600 (30% × 5 kits × 2,880 intervals)
Health records: 2,400   (5 kits × 480 intervals)
Total:         ~144,000 records
```

## Database Schema Mapping

### Kits Table
```python
{
    "kit_id": "kit-001",
    "name": "Test Kit 1",
    "location": "San Francisco, CA",
    "api_url": "http://192.168.1.100:8088",
    "last_seen": "2026-01-19T23:00:00+00:00",
    "status": "online",
    "created_at": "2026-01-19T21:00:00+00:00"
}
```

### Drones Table (Hypertable)
```python
{
    "time": "2026-01-19T21:15:23+00:00",
    "kit_id": "kit-001",
    "drone_id": "DJI485729",
    "lat": 37.775234,
    "lon": -122.421567,
    "alt": 87.5,
    "speed": 12.3,
    "heading": 245.7,
    "pilot_lat": 37.776890,
    "pilot_lon": -122.419876,
    "home_lat": 37.776890,
    "home_lon": -122.419876,
    "mac": "a4:c2:f4:8a:3d:2f",
    "rssi": -67,
    "freq": 5800.0,
    "ua_type": "Helicopter/Multirotor",
    "operator_id": "FAA1234567890123",
    "caa_id": "",
    "rid_make": "DJI",
    "rid_model": "Mini 3 Pro",
    "rid_source": "wifi",
    "track_type": "drone"
}
```

### Signals Table (Hypertable)
```python
{
    "time": "2026-01-19T21:15:25+00:00",
    "kit_id": "kit-001",
    "freq_mhz": 5740.0,
    "power_dbm": -58.4,
    "bandwidth_mhz": 8.0,
    "lat": 37.774900,
    "lon": -122.419400,
    "alt": 15.2,
    "detection_type": "analog"
}
```

### System Health Table (Hypertable)
```python
{
    "time": "2026-01-19T21:15:30+00:00",
    "kit_id": "kit-001",
    "lat": 37.774901,
    "lon": -122.419402,
    "alt": 15.2,
    "cpu_percent": 42.3,
    "memory_percent": 58.7,
    "disk_percent": 34.2,
    "uptime_hours": 0.26,
    "temp_cpu": 52.1,
    "temp_gpu": 45.8
}
```

## Batch Insert Performance

```
Batch Size: 1,000 records
Method: psycopg2.extras.execute_batch()

Typical performance:
- 1,000 drone records: ~100ms
- 10,000 drone records: ~800ms
- 50,000 total records: ~4 seconds
```

## Conflict Handling

All INSERT statements use `ON CONFLICT DO NOTHING` to prevent duplicates:

```sql
-- Primary key: (time, kit_id, drone_id)
INSERT INTO drones (...) VALUES (...)
ON CONFLICT (time, kit_id, drone_id) DO NOTHING;

-- Primary key: (time, kit_id, freq_mhz)
INSERT INTO signals (...) VALUES (...)
ON CONFLICT (time, kit_id, freq_mhz) DO NOTHING;

-- Primary key: (time, kit_id)
INSERT INTO system_health (...) VALUES (...)
ON CONFLICT (time, kit_id) DO NOTHING;

-- Primary key: kit_id
INSERT INTO kits (...) VALUES (...)
ON CONFLICT (kit_id) DO UPDATE SET last_seen = EXCLUDED.last_seen;
```

## Realistic Data Patterns

### Drone Flight Simulation
```
1. Generate waypoints:
   WP1 (37.775, -122.420, 45m)
   WP2 (37.777, -122.418, 78m)
   WP3 (37.779, -122.422, 92m)
   WP4 (37.776, -122.419, 50m)

2. For each time interval:
   - Calculate progress: elapsed / total_flight_time
   - Determine current segment: floor(progress × num_waypoints)
   - Interpolate position: linear between WP_n and WP_n+1
   - Calculate heading: bearing from WP_n to WP_n+1
   - Add noise: speed ±20%, altitude ±5m

3. Result: Smooth flight path with realistic turns
```

### FPV Signal Randomization
```
- Frequency: Select from predefined bands (A, B, E, F, R, DJI)
- Power: Random between -85 dBm (weak) and -45 dBm (strong)
- Type: 70% analog, 30% DJI digital
- Rate: 30% probability per 5s interval (configurable)
```

### System Health Variation
```
Base values (set per kit):
- CPU: 30% ± 15%
- Memory: 50% ± 10%
- Disk: 40% + slow growth
- Temp CPU: 50°C ± 10°C
- Temp GPU: 45°C ± 8°C

Per update:
- Add random variation within ranges
- Clamp to [0, 100] for percentages
- Simulate gradual disk usage increase
```
