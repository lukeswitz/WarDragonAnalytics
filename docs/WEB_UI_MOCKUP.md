# WarDragon Analytics Web UI Mockup

## Overview

The web UI provides interactive access to all collected data with two main interfaces:

1. **Operations View** (default) - Real-time map + data
2. **Kit Management** - Add/configure kits

---

## Operations View (Main Page)

```
┌────────────────────────────────────────────────────────────────────┐
│ WarDragon Analytics             [Kit: All ▼] [Refresh: 5s ▼]  👤 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐ │
│  │ FILTERS            │  │        LEAFLET MAP (ALL KITS)        │ │
│  │                    │  │                                      │ │
│  │ Time Range:        │  │   🔴 Kit Alpha (online, 12 drones)  │ │
│  │ ⚫ Last 1 hour     │  │   🔴 Kit Bravo (online, 8 drones)   │ │
│  │ ○ Last 24 hours   │  │   🟡 Kit Charlie (stale, 2 drones)  │ │
│  │ ○ Custom range    │  │                                      │ │
│  │                    │  │   [Zoom to fit all kits]            │ │
│  │ Kit Source:        │  │                                      │ │
│  │ ☑ Kit Alpha       │  │   Click drone → show track history   │ │
│  │ ☑ Kit Bravo       │  │   Click kit → zoom to kit location   │ │
│  │ ☑ Kit Charlie     │  │                                      │ │
│  │                    │  │   Layers:                            │ │
│  │ Track Type:        │  │   ☑ Drones  ☑ Aircraft  ☐ Signals  │ │
│  │ ☑ Drones          │  │                                      │ │
│  │ ☑ Aircraft        │  └──────────────────────────────────────┘ │
│  │ ☐ FPV Signals     │                                           │
│  │                    │  ┌──────────────────────────────────────┐ │
│  │ RID Make:          │  │ LIVE TRACKS TABLE                    │ │
│  │ [DJI      ▼]      │  │ Kit    | Drone ID  | Type | RID Make │ │
│  │                    │  │ Alpha  | drone-214 | RID  | DJI M30T │ │
│  │ Alert Types:       │  │ Alpha  | N123AB    | ADSB | Cessna  │ │
│  │ ☐ Geofence breach │  │ Bravo  | drone-891 | RID  | Autel    │ │
│  │ ☐ Watchlist match │  │ ...                                  │ │
│  │                    │  └──────────────────────────────────────┘ │
│  │ [Apply Filters]    │                                           │
│  │ [Export CSV]       │  [View in Grafana] [Export KML]          │
│  └────────────────────┘                                           │
└────────────────────────────────────────────────────────────────────┘
```

### Key Features

1. **Kit selector** (top right) - View all kits or filter to one
2. **Refresh interval** - Auto-refresh every N seconds
3. **Filters** (left sidebar):
   - Time range (last hour, 24h, custom)
   - Kit source (multi-select checkboxes)
   - Track type (drones, aircraft, signals)
   - RID make/model dropdown
   - Alert types (future)
4. **Map** (center):
   - Color-coded markers per kit
   - Click drone → popup with details + track history
   - Click kit icon → zoom to that kit's coverage area
   - Layer toggles (drones, aircraft, signals)
5. **Live table** (bottom):
   - Latest tracks from all kits
   - Sortable columns
   - Click row → zoom map to that track
6. **Export buttons**:
   - Export CSV (filtered results)
   - Export KML (Google Earth)
   - View in Grafana (opens Grafana dashboard)

---

## Kit Management Page

Access via: `/kits` or hamburger menu

```
┌────────────────────────────────────────────────────────────────────┐
│ WarDragon Analytics > Kit Management                          👤 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  CONFIGURED KITS                                [+ Add Kit]        │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ Kit Alpha                                    🟢 ONLINE         ││
│  │ ID: kit-alpha                                                  ││
│  │ API: http://192.168.1.100:8088                                 ││
│  │ Location: Mobile Unit Alpha                                    ││
│  │ Last Seen: 2 seconds ago                                       ││
│  │ Status: 12 drones, 3 signals, GPS: 34.05°N 118.24°W           ││
│  │ [Edit] [Test Connection] [View Logs] [Disable]                ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ Kit Bravo                                    🟢 ONLINE         ││
│  │ ID: kit-bravo                                                  ││
│  │ API: http://192.168.1.101:8088                                 ││
│  │ Location: Mobile Unit Bravo                                    ││
│  │ Last Seen: 1 second ago                                        ││
│  │ Status: 8 drones, 1 signal, GPS: 34.06°N 118.25°W             ││
│  │ [Edit] [Test Connection] [View Logs] [Disable]                ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ Kit Charlie                                  🟡 STALE          ││
│  │ ID: kit-charlie                                                ││
│  │ API: http://10.0.0.50:8088                                     ││
│  │ Location: Fixed Site HQ                                        ││
│  │ Last Seen: 45 seconds ago (warning threshold: 30s)            ││
│  │ Status: 2 drones, 0 signals, GPS: 34.07°N 118.26°W            ││
│  │ [Edit] [Test Connection] [View Logs] [Disable]                ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ Kit Delta                                    🔴 OFFLINE        ││
│  │ ID: kit-delta                                                  ││
│  │ API: http://192.168.1.102:8088                                 ││
│  │ Location: Mobile Unit Delta                                    ││
│  │ Last Seen: 5 minutes ago                                       ││
│  │ Status: Connection timeout (retrying in 30s)                   ││
│  │ [Edit] [Test Connection] [View Logs] [Enable]                 ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Add Kit Modal

Click `[+ Add Kit]` button:

```
┌──────────────────────────────────┐
│ Add New Kit                      │
├──────────────────────────────────┤
│                                  │
│ Kit Name:                        │
│ [Mobile Unit Echo          ]     │
│                                  │
│ Kit ID (unique):                 │
│ [kit-echo                  ]     │
│                                  │
│ API URL:                         │
│ [http://192.168.1.103:8088 ]     │
│                                  │
│ Location (optional):             │
│ [Field Operations          ]     │
│                                  │
│ [Test Connection]                │
│ ✅ Connection successful!        │
│ Kit is online and responding.    │
│                                  │
│     [Cancel]     [Add Kit]       │
└──────────────────────────────────┘
```

When you click `[Add Kit]`:
1. Analytics sends test request to `/status` endpoint
2. If successful, adds kit to `kits` table in database
3. Collector service automatically starts polling it
4. Kit appears in kit list immediately

---

## How Data Flows to UI

```
User visits http://localhost:8080
          ↓
FastAPI serves HTML page with Leaflet map
          ↓
JavaScript polls /api/drones?time_range=1h&kit=all
          ↓
FastAPI queries TimescaleDB:
  SELECT * FROM drones
  WHERE time > NOW() - INTERVAL '1 hour'
  AND kit_id IN (enabled kits)
          ↓
Returns JSON:
{
  "drones": [
    {
      "kit_id": "kit-alpha",
      "drone_id": "drone-214",
      "lat": 34.05, "lon": -118.24,
      "alt": 120.5, "speed": 15.2,
      "rid_make": "DJI", "rid_model": "M30T",
      "time": "2026-01-19T23:45:00Z"
    },
    ...
  ]
}
          ↓
JavaScript renders markers on Leaflet map
Each kit color-coded: Alpha=red, Bravo=blue, Charlie=green
```

### Real-Time Updates

**Option A: Polling (Simple, Phase 1)**
```javascript
// Refresh every 5 seconds
setInterval(() => {
  fetch('/api/drones?time_range=1h&kit=all')
    .then(r => r.json())
    .then(data => updateMap(data))
}, 5000)
```

**Option B: WebSockets (Advanced, Phase 3)**
```javascript
// Real-time push updates
const ws = new WebSocket('ws://localhost:8080/ws')
ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  addDroneToMap(update)  // Instant update
}
```

---

## Data Relevance & Interactivity

### 1. Time-Based Filtering
- **Last 1 hour:** Show only recent tracks (live operations)
- **Last 24 hours:** Historical analysis (what happened today)
- **Custom range:** Specific incident investigation (Jan 19, 14:00-15:00)

### 2. Geographic Filtering
- Click map → draw geofence → filter to drones inside polygon
- Click kit icon → filter to only that kit's detections
- Zoom to area → auto-filter to visible bounds

### 3. RID Enrichment Display
- Filter dropdown shows all RID makes seen: `DJI (234) | Autel (45) | Parrot (12)`
- Click "DJI" → show only DJI drones across all kits
- Click drone → popup shows full RID data (make, model, operator, CAA ID)

### 4. Multi-Kit Correlation
**Example:** Same drone seen by multiple kits

```
Map shows:
- Drone "drone-214" at 34.05°N, 118.24°W
  - Detected by Kit Alpha (RSSI: -65dBm, 100m away)
  - Also detected by Kit Bravo (RSSI: -72dBm, 250m away)

Popup shows:
┌─────────────────────────────────┐
│ Drone: drone-214                │
│ RID: DJI Mavic 3              │
│ Operator: N/A                   │
│ CAA ID: GB-ABC123              │
│                                 │
│ Detected by 2 kits:            │
│ • Kit Alpha (100m, -65dBm)     │
│ • Kit Bravo (250m, -72dBm)     │
│                                 │
│ Track history: [View]          │
│ [Export this drone's data]     │
└─────────────────────────────────┘
```

### 5. Track History Playback

Click drone → click "View Track" → opens timeline:

```
┌────────────────────────────────────────────────┐
│ Track History: drone-214 (DJI Mavic 3)       │
├────────────────────────────────────────────────┤
│ [◀◀] [▶] [▶▶]  ●━━━━━━━━━━━○ 15:23:45        │
│                                                │
│ Showing: 15:18:00 - 15:24:00 (6 minutes)      │
│                                                │
│ Map shows:                                     │
│ • Blue line: full track path                  │
│ • Red dot: position at selected time          │
│ • Yellow dots: Kit coverage areas             │
│                                                │
│ Data at 15:23:45:                             │
│ Altitude: 120.5m                              │
│ Speed: 15.2 m/s                               │
│ Heading: 045° (NE)                            │
│ Detected by: Kit Alpha                        │
└────────────────────────────────────────────────┘
```

---

## Example Use Cases

### Use Case 1: Live Operations
**Scenario:** 3 kits deployed at event, monitoring for unauthorized drones

**UI State:**
- Time range: Last 1 hour
- All kits enabled
- Map shows real-time positions
- Auto-refresh every 5 seconds
- Alert banner shows "2 active detections"

**Interaction:**
1. Click drone marker → see RID details
2. Click "Track history" → see flight path
3. Click "Export KML" → send to Google Earth for analysis

### Use Case 2: Historical Investigation
**Scenario:** Incident occurred yesterday, need to find all drones detected

**UI State:**
- Time range: Custom (Yesterday 14:00-16:00)
- Kit: Kit Alpha (was at incident location)
- RID Make: All

**Interaction:**
1. Filter shows 8 drones detected in that window
2. Click each drone → review RID data
3. Export CSV with all 8 drones + timestamps
4. Send report to stakeholders

### Use Case 3: Multi-Kit Coverage Analysis
**Scenario:** Verify kits are providing overlapping coverage

**UI State:**
- Time range: Last 24 hours
- All kits enabled
- Layer: Show signals (not just drones)

**Interaction:**
1. Map shows coverage circles around each kit
2. See overlap areas where multiple kits detected same drone
3. Identify gaps in coverage
4. Adjust kit placement accordingly

---

## Summary

**How users interact with data:**
- **Add kits:** Via web UI (`/kits` page) or config file
- **View data:** Leaflet map + table, auto-refreshes every 5s
- **Filter data:** Time range, kit source, RID make, track type
- **Analyze:** Click tracks, view history, export CSV/KML
- **Multi-kit:** See which kits detected same drone, analyze overlap

**Data stays relevant:**
- Auto-refresh keeps map live
- Time-based filtering (1h for ops, 24h for analysis)
- Geographic filtering (zoom to area)
- RID enrichment helps identify specific drones
- Track history shows movement over time

Everything is interactive, real-time (with 5s polling), and aggregates data from all configured kits into a single unified view.
