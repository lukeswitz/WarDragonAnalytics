// WarDragon Analytics - Tactical Operations JavaScript

// Global variables
let map;
let markers = [];
let lines = [];
let currentData = [];
let patternData = {
    repeated: [],
    coordinated: [],
    pilotReuse: [],
    anomalies: [],
    multiKit: []
};
let refreshTimer;
let alertRefreshTimer;
let kits = [];
let watchlist = [];
let alerts = [];
let activeFilters = {
    showUnusual: false,
    showRepeated: false,
    showCoordinated: false,
    geoPolygon: null
};
let drawnItems;

// Kit color mapping
const KIT_COLORS = [
    '#ff4444', '#4444ff', '#44ff44', '#ffff44', '#ff44ff', '#44ffff',
    '#ff8844', '#8844ff', '#44ff88', '#ff4488', '#88ff44', '#4488ff'
];

// Pattern colors
const PATTERN_COLORS = {
    coordinated: '#ffaa00',
    pilotReuse: '#4444ff',
    normal: '#4444ff',
    unusual: '#ff4444'
};

// Initialize map
function initMap() {
    map = L.map('map').setView([34.05, -118.24], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Initialize drawn items layer for geographic filtering
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    // Add drawing controls
    const drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
            polygon: {
                allowIntersection: false,
                showArea: true,
                shapeOptions: {
                    color: '#00ff00'
                }
            },
            polyline: false,
            rectangle: true,
            circle: false,
            marker: false,
            circlemarker: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: true
        }
    });
    map.addControl(drawControl);

    // Handle drawn shapes
    map.on(L.Draw.Event.CREATED, function (event) {
        const layer = event.layer;
        drawnItems.clearLayers();
        drawnItems.addLayer(layer);

        // Store polygon for filtering
        if (event.layerType === 'polygon' || event.layerType === 'rectangle') {
            activeFilters.geoPolygon = layer.toGeoJSON().geometry.coordinates[0];
            applyFilters();
        }
    });

    map.on(L.Draw.Event.DELETED, function () {
        activeFilters.geoPolygon = null;
        applyFilters();
    });
}

// Create custom marker icon
function createMarkerIcon(color, trackType, options = {}) {
    const { isWatchlist = false, isAnomaly = false, multiKitCount = 0, isCoordinated = false } = options;

    let iconHtml = trackType === 'aircraft'
        ? `<svg width="30" height="30" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" fill="${color}"/></svg>`
        : `<svg width="30" height="30" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="8" fill="${color}" stroke="#000" stroke-width="1"/></svg>`;

    // Add badges for special markers
    let badges = '';
    if (isWatchlist) {
        badges += '<div class="marker-badge watchlist">⭐</div>';
    }
    if (isAnomaly) {
        badges += '<div class="marker-badge anomaly">⚠</div>';
    }
    if (multiKitCount > 1) {
        badges += `<div class="marker-badge multi-kit">${multiKitCount}</div>`;
    }
    if (isCoordinated) {
        badges += '<div class="marker-badge coordinated">↔</div>';
    }

    const fullHtml = `
        <div class="marker-wrapper">
            ${iconHtml}
            ${badges}
        </div>
    `;

    return L.divIcon({
        html: fullHtml,
        className: 'marker-icon',
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -15]
    });
}

// Add CSS for marker badges
const style = document.createElement('style');
style.textContent = `
    .marker-wrapper { position: relative; }
    .marker-badge {
        position: absolute;
        top: -5px;
        right: -5px;
        background: #ff4444;
        color: white;
        border-radius: 50%;
        width: 16px;
        height: 16px;
        font-size: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        border: 2px solid #1a1a1a;
    }
    .marker-badge.watchlist { background: #00ff00; color: #1a1a1a; }
    .marker-badge.multi-kit { background: #4444ff; }
    .marker-badge.coordinated { background: #ffaa00; }
`;
document.head.appendChild(style);

// Format time
function formatTime(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}

// Format coordinate
function formatCoord(value, decimals = 6) {
    return value != null ? value.toFixed(decimals) : 'N/A';
}

// Create popup content
function createPopup(track, options = {}) {
    const ridMake = track.rid_make || 'Unknown';
    const ridModel = track.rid_model || 'Unknown';
    const trackType = track.track_type || 'drone';
    const { isWatchlist = false, isAnomaly = false, anomalyTypes = [], multiKitCount = 0 } = options;

    let badges = '';
    if (isWatchlist) badges += '<span class="popup-badge watchlist">Watchlist</span> ';
    if (isAnomaly) badges += '<span class="popup-badge anomaly">Anomaly</span> ';
    if (multiKitCount > 1) badges += `<span class="popup-badge multi-kit">Seen by ${multiKitCount} kits</span> `;

    let anomalyInfo = '';
    if (anomalyTypes.length > 0) {
        anomalyInfo = `
            <div class="popup-row">
                <span class="popup-label">Anomalies:</span>
                <span class="popup-value">${anomalyTypes.join(', ')}</span>
            </div>
        `;
    }

    return `
        <div class="popup-title">${track.drone_id} ${badges}</div>
        <div class="popup-row">
            <span class="popup-label">Kit:</span>
            <span class="popup-value">${track.kit_id}</span>
        </div>
        <div class="popup-row">
            <span class="popup-label">Type:</span>
            <span class="popup-value">${trackType}</span>
        </div>
        <div class="popup-row">
            <span class="popup-label">RID:</span>
            <span class="popup-value">${ridMake} ${ridModel}</span>
        </div>
        <div class="popup-row">
            <span class="popup-label">Position:</span>
            <span class="popup-value">${formatCoord(track.lat)}, ${formatCoord(track.lon)}</span>
        </div>
        <div class="popup-row">
            <span class="popup-label">Altitude:</span>
            <span class="popup-value">${track.alt != null ? track.alt.toFixed(1) : 'N/A'} m</span>
        </div>
        <div class="popup-row">
            <span class="popup-label">Speed:</span>
            <span class="popup-value">${track.speed != null ? track.speed.toFixed(1) : 'N/A'} m/s</span>
        </div>
        <div class="popup-row">
            <span class="popup-label">RSSI:</span>
            <span class="popup-value">${track.rssi || 'N/A'} dBm</span>
        </div>
        <div class="popup-row">
            <span class="popup-label">Time:</span>
            <span class="popup-value">${formatTime(track.time)}</span>
        </div>
        ${anomalyInfo}
    `;
}

// Update map markers
function updateMap(data) {
    // Clear existing markers and lines
    markers.forEach(marker => map.removeLayer(marker));
    lines.forEach(line => map.removeLayer(line));
    markers = [];
    lines = [];

    // Draw pattern connections first (so they're behind markers)
    drawPatternConnections();

    // Add markers for each track
    data.forEach((track, index) => {
        if (track.lat != null && track.lon != null) {
            const kitIndex = kits.findIndex(k => k.kit_id === track.kit_id);
            const color = KIT_COLORS[kitIndex % KIT_COLORS.length];

            // Check for special statuses
            const isWatchlist = watchlist.includes(track.drone_id);
            const anomaly = patternData.anomalies.find(a => a.drone_id === track.drone_id);
            const isAnomaly = !!anomaly;
            const anomalyTypes = anomaly ? anomaly.anomaly_types || [] : [];
            const multiKit = patternData.multiKit.find(m => m.drone_id === track.drone_id);
            const multiKitCount = multiKit ? multiKit.kit_count : 0;
            const isCoordinated = patternData.coordinated.some(g =>
                g.drone_ids && g.drone_ids.includes(track.drone_id)
            );

            const icon = createMarkerIcon(color, track.track_type, {
                isWatchlist,
                isAnomaly,
                multiKitCount,
                isCoordinated
            });

            const marker = L.marker([track.lat, track.lon], { icon })
                .bindPopup(createPopup(track, { isWatchlist, isAnomaly, anomalyTypes, multiKitCount }))
                .addTo(map);

            markers.push(marker);
        }
    });

    // Auto-fit bounds if markers exist
    if (markers.length > 0) {
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Draw pattern connections on map
function drawPatternConnections() {
    // Draw coordinated drone connections
    patternData.coordinated.forEach(group => {
        if (group.drone_ids && group.drone_ids.length > 1) {
            const drones = currentData.filter(d => group.drone_ids.includes(d.drone_id));
            if (drones.length > 1) {
                for (let i = 0; i < drones.length - 1; i++) {
                    for (let j = i + 1; j < drones.length; j++) {
                        if (drones[i].lat && drones[j].lat) {
                            const line = L.polyline(
                                [[drones[i].lat, drones[i].lon], [drones[j].lat, drones[j].lon]],
                                {
                                    color: PATTERN_COLORS.coordinated,
                                    weight: 2,
                                    dashArray: '5, 5',
                                    opacity: 0.7
                                }
                            ).addTo(map);
                            lines.push(line);
                        }
                    }
                }
            }
        }
    });

    // Draw pilot reuse connections
    patternData.pilotReuse.forEach(pilot => {
        if (pilot.pilot_lat && pilot.pilot_lon && pilot.drone_ids) {
            pilot.drone_ids.forEach(droneId => {
                const drone = currentData.find(d => d.drone_id === droneId);
                if (drone && drone.lat) {
                    const line = L.polyline(
                        [[pilot.pilot_lat, pilot.pilot_lon], [drone.lat, drone.lon]],
                        {
                            color: PATTERN_COLORS.pilotReuse,
                            weight: 2,
                            opacity: 0.6
                        }
                    ).addTo(map);
                    lines.push(line);
                }
            });
        }
    });
}

// Update table
function updateTable(data) {
    const tbody = document.getElementById('tracks-table');
    tbody.innerHTML = '';

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: #aaa;">No data available</td></tr>';
        return;
    }

    data.slice(0, 100).forEach(track => {
        const row = document.createElement('tr');
        row.className = 'track-row';

        // Add special row classes
        if (watchlist.includes(track.drone_id)) {
            row.classList.add('watchlist');
        }
        if (patternData.anomalies.some(a => a.drone_id === track.drone_id)) {
            row.classList.add('anomaly');
        }

        row.onclick = () => {
            if (track.lat != null && track.lon != null) {
                map.setView([track.lat, track.lon], 15);
                markers.forEach(marker => {
                    const pos = marker.getLatLng();
                    if (pos.lat === track.lat && pos.lng === track.lon) {
                        marker.openPopup();
                    }
                });
            }
        };

        row.innerHTML = `
            <td>${formatTime(track.time)}</td>
            <td>${track.kit_id}</td>
            <td>${track.drone_id}</td>
            <td>${track.track_type || 'drone'}</td>
            <td>${track.rid_make || 'N/A'}</td>
            <td>${track.rid_model || 'N/A'}</td>
            <td>${formatCoord(track.lat)}</td>
            <td>${formatCoord(track.lon)}</td>
            <td>${track.alt != null ? track.alt.toFixed(1) : 'N/A'}</td>
            <td>${track.speed != null ? track.speed.toFixed(1) : 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Update stats
function updateStats(data) {
    const drones = data.filter(d => d.track_type === 'drone' || !d.track_type);
    const aircraft = data.filter(d => d.track_type === 'aircraft');
    const uniqueKits = new Set(data.map(d => d.kit_id));

    document.getElementById('total-tracks').textContent = data.length;
    document.getElementById('total-drones').textContent = drones.length;
    document.getElementById('total-aircraft').textContent = aircraft.length;
    document.getElementById('active-kits').textContent = uniqueKits.size;
}

// Update threat summary cards
function updateThreatCards() {
    // Active threats (anomalies in last hour)
    const activeThreatsCount = patternData.anomalies.length;
    document.getElementById('active-threats').textContent = activeThreatsCount;

    // Repeated contacts
    const repeatedCount = patternData.repeated.length;
    document.getElementById('repeated-contacts').textContent = repeatedCount;

    // Multi-kit detections
    const multiKitCount = patternData.multiKit.length;
    document.getElementById('multi-kit-detections').textContent = multiKitCount;

    // Total anomalies by type
    const anomalyCount = patternData.anomalies.reduce((sum, a) =>
        sum + (a.anomaly_types ? a.anomaly_types.length : 0), 0
    );
    document.getElementById('anomalies-count').textContent = anomalyCount;

    // Update quick filter counts
    document.getElementById('unusual-count').textContent = activeThreatsCount;
    document.getElementById('repeated-count').textContent = repeatedCount;
    document.getElementById('coordinated-count').textContent = patternData.coordinated.length;
}

// Alert Management
function addAlert(type, title, message) {
    const alert = {
        id: Date.now(),
        type, // 'info', 'warning', 'critical'
        title,
        message,
        time: new Date().toISOString()
    };

    alerts.push(alert);
    saveAlerts();
    renderAlerts();
}

function dismissAlert(alertId) {
    alerts = alerts.filter(a => a.id !== alertId);
    saveAlerts();
    renderAlerts();
}

function clearAllAlerts() {
    alerts = [];
    saveAlerts();
    renderAlerts();
}

function renderAlerts() {
    const panel = document.getElementById('alert-panel');
    const list = document.getElementById('alerts-list');

    if (alerts.length === 0) {
        panel.classList.remove('has-alerts');
        return;
    }

    panel.classList.add('has-alerts');
    list.innerHTML = '';

    alerts.forEach(alert => {
        const alertEl = document.createElement('div');
        alertEl.className = `alert-item ${alert.type}`;
        alertEl.innerHTML = `
            <div class="alert-content">
                <div class="alert-title">${alert.title}</div>
                <div class="alert-message">${alert.message}</div>
            </div>
            <span class="alert-time">${formatTime(alert.time)}</span>
            <button class="alert-dismiss" onclick="dismissAlert(${alert.id})">×</button>
        `;
        list.appendChild(alertEl);
    });
}

function saveAlerts() {
    localStorage.setItem('wardragon_alerts', JSON.stringify(alerts));
}

function loadAlerts() {
    const saved = localStorage.getItem('wardragon_alerts');
    if (saved) {
        alerts = JSON.parse(saved);
        renderAlerts();
    }
}

// Check for new alerts based on pattern data
function checkForAlerts() {
    const now = new Date();

    // Check for new anomalies
    patternData.anomalies.forEach(anomaly => {
        const existingAlert = alerts.find(a =>
            a.message.includes(anomaly.drone_id) && a.type === 'critical'
        );
        if (!existingAlert) {
            const anomalyTypes = anomaly.anomaly_types ? anomaly.anomaly_types.join(', ') : 'Unknown';
            addAlert('critical', 'Anomaly Detected',
                `Drone ${anomaly.drone_id}: ${anomalyTypes}`);
        }
    });

    // Check for coordinated activity
    patternData.coordinated.forEach(group => {
        if (group.drone_ids && group.drone_ids.length > 2) {
            const existingAlert = alerts.find(a =>
                a.message.includes('coordinated') && a.message.includes(group.drone_ids[0])
            );
            if (!existingAlert) {
                addAlert('warning', 'Coordinated Activity',
                    `${group.drone_ids.length} drones detected in close proximity`);
            }
        }
    });

    // Check for watchlist matches
    const watchlistMatches = currentData.filter(d => watchlist.includes(d.drone_id));
    watchlistMatches.forEach(drone => {
        const existingAlert = alerts.find(a =>
            a.message.includes(drone.drone_id) && a.type === 'info'
        );
        if (!existingAlert) {
            addAlert('info', 'Watchlist Match',
                `Drone ${drone.drone_id} detected`);
        }
    });
}

// Watchlist Management
function addToWatchlist(droneId) {
    droneId = droneId.trim();
    if (droneId && !watchlist.includes(droneId)) {
        watchlist.push(droneId);
        saveWatchlist();
        renderWatchlist();
        applyFilters();
    }
}

function removeFromWatchlist(droneId) {
    watchlist = watchlist.filter(id => id !== droneId);
    saveWatchlist();
    renderWatchlist();
    applyFilters();
}

function renderWatchlist() {
    const container = document.getElementById('watchlist-items');
    container.innerHTML = '';

    watchlist.forEach(droneId => {
        const tag = document.createElement('div');
        tag.className = 'watchlist-tag';
        tag.innerHTML = `
            ${droneId}
            <span class="remove" onclick="removeFromWatchlist('${droneId}')">×</span>
        `;
        container.appendChild(tag);
    });
}

function saveWatchlist() {
    localStorage.setItem('wardragon_watchlist', JSON.stringify(watchlist));
}

function loadWatchlist() {
    const saved = localStorage.getItem('wardragon_watchlist');
    if (saved) {
        watchlist = JSON.parse(saved);
        renderWatchlist();
    }
}

// Fetch kits
async function fetchKits() {
    try {
        const response = await fetch('/api/kits');
        const data = await response.json();
        kits = data.kits || [];
        updateKitCheckboxes();
    } catch (error) {
        console.error('Failed to fetch kits:', error);
    }
}

// Update kit checkboxes
function updateKitCheckboxes() {
    const container = document.getElementById('kit-checkboxes');
    container.innerHTML = '<label><input type="checkbox" value="all" checked> All Kits</label>';

    kits.forEach(kit => {
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = kit.kit_id;
        checkbox.checked = true;

        const statusDot = kit.status === 'online' ? '🟢' : kit.status === 'stale' ? '🟡' : '🔴';

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(` ${statusDot} ${kit.name || kit.kit_id}`));
        container.appendChild(label);
    });
}

// Get selected filters
function getFilters() {
    const timeRange = document.getElementById('time-range').value;
    const ridMake = document.getElementById('rid-make').value;
    const showDrones = document.getElementById('show-drones').checked;
    const showAircraft = document.getElementById('show-aircraft').checked;

    const kitCheckboxes = document.querySelectorAll('#kit-checkboxes input[type="checkbox"]:checked');
    const selectedKits = Array.from(kitCheckboxes)
        .map(cb => cb.value)
        .filter(v => v !== 'all');

    const filters = { time_range: timeRange };
    if (selectedKits.length > 0) {
        filters.kit_id = selectedKits.join(',');
    }
    if (ridMake) {
        filters.rid_make = ridMake;
    }

    return { filters, showDrones, showAircraft };
}

// Apply active filters to data
function applyActiveFilters(data) {
    let filtered = [...data];

    // Show unusual filter
    if (activeFilters.showUnusual) {
        filtered = filtered.filter(d =>
            patternData.anomalies.some(a => a.drone_id === d.drone_id)
        );
    }

    // Show repeated filter
    if (activeFilters.showRepeated) {
        filtered = filtered.filter(d =>
            patternData.repeated.some(r => r.drone_id === d.drone_id)
        );
    }

    // Show coordinated filter
    if (activeFilters.showCoordinated) {
        const coordinatedDrones = patternData.coordinated.flatMap(g => g.drone_ids || []);
        filtered = filtered.filter(d => coordinatedDrones.includes(d.drone_id));
    }

    // Geographic polygon filter
    if (activeFilters.geoPolygon) {
        filtered = filtered.filter(d => {
            if (!d.lat || !d.lon) return false;
            return isPointInPolygon([d.lon, d.lat], activeFilters.geoPolygon);
        });
    }

    return filtered;
}

// Point in polygon check
function isPointInPolygon(point, polygon) {
    const [x, y] = point;
    let inside = false;

    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const [xi, yi] = polygon[i];
        const [xj, yj] = polygon[j];

        const intersect = ((yi > y) !== (yj > y)) &&
            (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }

    return inside;
}

// Fetch pattern data
async function fetchPatterns() {
    const { filters } = getFilters();

    try {
        // Fetch all pattern endpoints
        const endpoints = [
            'repeated-drones',
            'coordinated',
            'pilot-reuse',
            'anomalies',
            'multi-kit'
        ];

        const promises = endpoints.map(async (endpoint) => {
            try {
                const params = new URLSearchParams(filters);
                const response = await fetch(`/api/patterns/${endpoint}?${params}`);
                if (response.ok) {
                    return await response.json();
                }
                return null;
            } catch (error) {
                console.log(`Pattern API ${endpoint} not yet available`);
                return null;
            }
        });

        const results = await Promise.all(promises);

        // Update pattern data
        patternData.repeated = results[0]?.drones || [];
        patternData.coordinated = results[1]?.groups || [];
        patternData.pilotReuse = results[2]?.pilots || [];
        patternData.anomalies = results[3]?.anomalies || [];
        patternData.multiKit = results[4]?.drones || [];

        updateThreatCards();
        checkForAlerts();
    } catch (error) {
        console.error('Failed to fetch patterns:', error);
    }
}

// Fetch and update data
async function fetchData() {
    try {
        showLoading(true);

        const { filters, showDrones, showAircraft } = getFilters();
        const params = new URLSearchParams(filters);

        const response = await fetch(`/api/drones?${params}`);
        const data = await response.json();

        // Filter by track type
        let filteredData = data.drones || [];
        if (!showDrones && !showAircraft) {
            filteredData = [];
        } else if (!showDrones) {
            filteredData = filteredData.filter(d => d.track_type === 'aircraft');
        } else if (!showAircraft) {
            filteredData = filteredData.filter(d => d.track_type !== 'aircraft');
        }

        currentData = filteredData;

        // Fetch pattern data
        await fetchPatterns();

        // Apply active filters
        const displayData = applyActiveFilters(currentData);

        updateMap(displayData);
        updateTable(displayData);
        updateStats(currentData);

        document.getElementById('last-update').textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    } catch (error) {
        console.error('Failed to fetch data:', error);
        addAlert('critical', 'Data Fetch Error', 'Failed to retrieve drone data');
    } finally {
        showLoading(false);
    }
}

// Show/hide loading indicator
function showLoading(show) {
    let overlay = document.getElementById('loading-overlay');
    if (show && !overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <div>Loading data...</div>
            </div>
        `;
        document.querySelector('.map-container').appendChild(overlay);
    } else if (!show && overlay) {
        overlay.remove();
    }
}

// Apply filters
function applyFilters() {
    fetchData();
}

// Toggle quick filter
function toggleQuickFilter(filterName) {
    const btn = document.getElementById(`filter-${filterName}`);
    activeFilters[filterName] = !activeFilters[filterName];

    if (activeFilters[filterName]) {
        btn.classList.add('active');
    } else {
        btn.classList.remove('active');
    }

    const displayData = applyActiveFilters(currentData);
    updateMap(displayData);
    updateTable(displayData);
}

// Filter by threat card
function filterByThreatCard(cardType) {
    // Reset all quick filters
    activeFilters.showUnusual = false;
    activeFilters.showRepeated = false;
    activeFilters.showCoordinated = false;

    document.getElementById('filter-showUnusual').classList.remove('active');
    document.getElementById('filter-showRepeated').classList.remove('active');
    document.getElementById('filter-showCoordinated').classList.remove('active');

    // Activate the selected filter
    if (cardType === 'unusual') {
        activeFilters.showUnusual = true;
        document.getElementById('filter-showUnusual').classList.add('active');
    } else if (cardType === 'repeated') {
        activeFilters.showRepeated = true;
        document.getElementById('filter-showRepeated').classList.add('active');
    } else if (cardType === 'coordinated') {
        activeFilters.showCoordinated = true;
        document.getElementById('filter-showCoordinated').classList.add('active');
    }

    const displayData = applyActiveFilters(currentData);
    updateMap(displayData);
    updateTable(displayData);
}

// Export CSV
function exportCSV() {
    const { filters } = getFilters();
    const params = new URLSearchParams(filters);
    window.location.href = `/api/export/csv?${params}`;
}

// Toggle theme
function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const theme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    localStorage.setItem('wardragon_theme', theme);
}

function loadTheme() {
    const theme = localStorage.getItem('wardragon_theme');
    if (theme === 'light') {
        document.body.classList.add('light-theme');
    }
}

// Setup auto-refresh
function setupAutoRefresh() {
    const select = document.getElementById('refresh-interval');
    select.addEventListener('change', () => {
        const interval = parseInt(select.value);

        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }

        if (interval > 0) {
            refreshTimer = setInterval(fetchData, interval * 1000);
            document.getElementById('refresh-status').textContent = `Auto-refresh: ${interval}s`;
        } else {
            document.getElementById('refresh-status').textContent = 'Auto-refresh: Disabled';
        }
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    loadTheme();
    loadWatchlist();
    loadAlerts();

    initMap();
    setupAutoRefresh();

    await fetchKits();
    await fetchData();

    // Start auto-refresh (default 5s)
    refreshTimer = setInterval(fetchData, 5000);

    // Start alert check (every 5s)
    alertRefreshTimer = setInterval(checkForAlerts, 5000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshTimer) clearInterval(refreshTimer);
    if (alertRefreshTimer) clearInterval(alertRefreshTimer);
});
