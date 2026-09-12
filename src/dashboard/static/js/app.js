/* ═══════════════════════════════════════════════════════════
   SIpi Incendios — Frontend Unified Dashboard Application
   ===========================================================
   - CONAF-Style Hotspots Monitoring Engine (Loaded by default)
   - Real-time Filter by Region and Fire Severity
   - Interactive Hotspot Inspection & Click-to-Evaluate
   - Clean Esri Dark Canvas & Satellite tiles (no watermark)
   - Live XGBoost Fire Risk Prediction & Gauge Animation
   - Regla 30-30-30 CONAF Live Evaluator & Action Protocol
   - Real Spatial Context (MapBiomas 2022, GeoNames, NASA SRTM)
   - Real-Time SHAP Local Feature Impact & Plain Spanish Diagnostic
   - 7-Day Meteorological Fire Risk Forecast (Open-Meteo) with 1-click evaluation
   - "What-If" Climate Scenario Simulator
   - Model Metrics & Diagnostics Gallery with Lightbox
   - Macrozone Zoom Bar & GPS Geolocation
   - Methodological Guide & Technical Glossary Modal
   ═══════════════════════════════════════════════════════════ */

// ── State Management ───────────────────────────────────────────
let map;
let marker;
let baseLayers = {};
let currentBaseLayer;
let hotspotsLayerGroup;
let historicalHotspotsData = null;
let currentCoords = { lat: -36.8270, lon: -73.0503 }; // Default: Concepción
let lastPredictionResult = null;
let predictionHistory = JSON.parse(localStorage.getItem('sipi_history') || '[]');
let simDebounceTimer = null;
let currentShapFactors = [];
let activeRegionalData = [];

// ── App Initialization ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    initNavScroll();
    initHeaderActions();
    initMap();
    initMacroZoomButtons();
    initPlaceSearch();
    initForm();
    initPresets();
    initDatePresets();
    initSimulator();
    initForecastControls();
    initHotspotFilters();
    initSHAPViewToggle();
    initRegionalFilters();
    loadRegionalSummary();
    loadModelInfo();
    loadEvaluationPlots();
    renderHistory();
    setDefaultDate();

    // 1. Load and display all CONAF / VIIRS hotspots immediately on startup
    await loadHistoricalHotspots();

    // 2. Auto-run initial prediction for immediate visual feedback
    await handlePredict();
    loadForecast(currentCoords.lat, currentCoords.lon);
    runSimulation();
});

// ── 1. Navigation & Smooth Scroll ──────────────────────────────
function initNavScroll() {
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const targetEl = document.querySelector(targetId);
            if (targetEl) {
                const headerOffset = 90;
                const elementPosition = targetEl.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Scrollspy to highlight active link
    window.addEventListener('scroll', () => {
        const sections = document.querySelectorAll('.section-container');
        let currentSectionId = '';
        const scrollPosition = window.pageYOffset + 140;

        sections.forEach(sec => {
            const top = sec.offsetTop;
            const height = sec.offsetHeight;
            if (scrollPosition >= top && scrollPosition < top + height) {
                currentSectionId = '#' + sec.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentSectionId) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    });
}

// ── 1.1 Header Actions & Modal ─────────────────────────────────
function initHeaderActions() {
    // GPS Geolocation
    const btnGps = document.getElementById('btn-hdr-gps');
    if (btnGps) {
        btnGps.addEventListener('click', () => {
            if (!navigator.geolocation) {
                showToast('Geolocalización no soportada por el navegador.');
                return;
            }

            btnGps.classList.add('loading');
            navigator.geolocation.getCurrentPosition(
                async (pos) => {
                    btnGps.classList.remove('loading');
                    let lat = pos.coords.latitude;
                    let lon = pos.coords.longitude;

                    // Validate if within Chile continental roughly
                    if (lat < -56.0 || lat > -17.0 || lon < -76.0 || lon > -66.0) {
                        showToast('Tu ubicación GPS está fuera de Chile continental. Usando Concepción como referencia.');
                        lat = -36.8270;
                        lon = -73.0503;
                    } else {
                        showToast(`📍 Ubicación GPS detectada: ${lat.toFixed(4)}, ${lon.toFixed(4)}`);
                    }

                    document.getElementById('input-lat').value = lat.toFixed(4);
                    document.getElementById('input-lon').value = lon.toFixed(4);
                    currentCoords = { lat, lon };

                    placeMarker(lat, lon);
                    map.flyTo([lat, lon], 9, { duration: 1.0 });

                    await handlePredict();
                    loadForecast(lat, lon);
                    runSimulation();
                },
                (err) => {
                    btnGps.classList.remove('loading');
                    showToast('No se pudo obtener la ubicación GPS (permiso denegado).');
                },
                { timeout: 10000 }
            );
        });
    }

    // Guide Modal
    const btnHelp = document.getElementById('btn-hdr-help');
    const guideModal = document.getElementById('guide-modal');
    const btnCloseGuide = document.getElementById('btn-close-guide');
    const guideOverlay = document.getElementById('guide-overlay');

    if (btnHelp && guideModal) {
        btnHelp.addEventListener('click', () => {
            guideModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });

        const closeGuide = () => {
            guideModal.style.display = 'none';
            document.body.style.overflow = '';
        };

        btnCloseGuide?.addEventListener('click', closeGuide);
        guideOverlay?.addEventListener('click', closeGuide);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && guideModal.style.display === 'flex') {
                closeGuide();
            }
        });
    }

    // System Report Modal
    const btnReport = document.getElementById('btn-hdr-report');
    const reportModal = document.getElementById('report-modal');
    const btnCloseReport = document.getElementById('btn-close-report');
    const reportOverlay = document.getElementById('report-overlay');
    const btnReportPrint = document.getElementById('btn-report-print');

    if (btnReport && reportModal) {
        btnReport.addEventListener('click', () => {
            reportModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });

        const closeReport = () => {
            reportModal.style.display = 'none';
            document.body.style.overflow = '';
        };

        btnCloseReport?.addEventListener('click', closeReport);
        reportOverlay?.addEventListener('click', closeReport);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && reportModal.style.display === 'flex') {
                closeReport();
            }
        });

        btnReportPrint?.addEventListener('click', () => {
            window.print();
        });

        // Report Internal Section Navigation
        document.querySelectorAll('.btn-rep-nav').forEach(tabBtn => {
            tabBtn.addEventListener('click', () => {
                const repKey = tabBtn.getAttribute('data-rep');
                const targetSec = document.getElementById(`rep-sec-${repKey}`);
                if (targetSec) {
                    targetSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    document.querySelectorAll('.btn-rep-nav').forEach(b => b.classList.remove('active'));
                    tabBtn.classList.add('active');
                }
            });
        });
    }
}

// ── 2. Leaflet Map & Clean Layers ──────────────────────────────
function initMap() {
    // Center on central Chile fire corridor
    map = L.map('map', {
        center: [-36.8, -72.0],
        zoom: 7,
        zoomControl: true,
        attributionControl: true,
    });

    // Live mousemove coordinates badge display
    map.on('mousemove', (e) => {
        const coordsBadge = document.getElementById('map-coords-badge');
        if (coordsBadge) {
            coordsBadge.textContent = `📍 Coordenadas: ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
        }
    });

    // Base Tile Layers
    baseLayers.dark = L.tileLayer('https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri, HERE, Garmin, USGS',
        maxZoom: 16
    });

    baseLayers.satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri, Maxar, Earthstar Geographics',
        maxZoom: 18
    });

    baseLayers.voyager = L.tileLayer('https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> · OSM',
        subdomains: 'abcd',
        maxZoom: 19
    });

    // Default layer
    currentBaseLayer = baseLayers.dark;
    currentBaseLayer.addTo(map);

    // Layer switch buttons
    document.querySelectorAll('.btn-layer').forEach(btn => {
        btn.addEventListener('click', () => {
            const layerKey = btn.getAttribute('data-layer');
            if (baseLayers[layerKey] && currentBaseLayer !== baseLayers[layerKey]) {
                map.removeLayer(currentBaseLayer);
                currentBaseLayer = baseLayers[layerKey];
                currentBaseLayer.addTo(map);

                document.querySelectorAll('.btn-layer').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            }
        });
    });

    // Hotspot cluster group
    hotspotsLayerGroup = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 45,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        iconCreateFunction: function(cluster) {
            const count = cluster.getChildCount();
            let cClass = 'marker-cluster-small';
            if (count > 50) cClass = 'marker-cluster-large';
            else if (count > 15) cClass = 'marker-cluster-medium';

            return new L.DivIcon({
                html: `<div><span>${count}</span></div>`,
                className: 'marker-cluster ' + cClass,
                iconSize: new L.Point(36, 36)
            });
        }
    });
    map.addLayer(hotspotsLayerGroup);

    // Hotspots toggle
    const toggleHotspots = document.getElementById('toggle-hotspots');
    if (toggleHotspots) {
        toggleHotspots.addEventListener('change', (e) => {
            if (e.target.checked) {
                map.addLayer(hotspotsLayerGroup);
            } else {
                map.removeLayer(hotspotsLayerGroup);
            }
        });
    }

    // Click on map to evaluate point
    map.on('click', async (e) => {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;

        if (lat < -56.0 || lat > -17.0 || lng < -76.0 || lng > -66.0) {
            showToast('Haz click dentro del territorio de Chile continental.');
            return;
        }

        currentCoords = { lat, lon: lng };
        document.getElementById('input-lat').value = lat.toFixed(4);
        document.getElementById('input-lon').value = lng.toFixed(4);

        document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));

        placeMarker(lat, lng);
        await handlePredict();
        loadForecast(lat, lng);
        runSimulation();
    });

    // Initial default marker
    placeMarker(currentCoords.lat, currentCoords.lon);

    // Responsive map sizing
    window.addEventListener('resize', () => {
        if (map) map.invalidateSize();
    });
    setTimeout(() => {
        if (map) map.invalidateSize();
    }, 250);
}

// ── 2.1 Macrozone Quick Zoom Buttons ───────────────────────────
function initMacroZoomButtons() {
    document.querySelectorAll('.btn-macro').forEach(btn => {
        btn.addEventListener('click', () => {
            const macro = btn.getAttribute('data-macro');
            document.querySelectorAll('.btn-macro').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (macro === 'all') {
                map.fitBounds([[-33.0, -74.0], [-42.0, -70.0]], { duration: 0.8 });
            } else if (macro === 'centro') {
                map.flyTo([-33.45, -71.2], 8, { duration: 0.8 });
            } else if (macro === 'centrosur') {
                map.flyTo([-36.6, -72.3], 8, { duration: 0.8 });
            } else if (macro === 'sur') {
                map.flyTo([-39.5, -72.6], 8, { duration: 0.8 });
            } else if (macro === 'austral') {
                map.flyTo([-46.5, -73.5], 6, { duration: 0.8 });
            }
        });
    });
}

function placeMarker(lat, lng, popupContent = null) {
    if (marker) {
        map.removeLayer(marker);
    }

    const fireIcon = L.divIcon({
        className: 'fire-marker',
        html: `<div style="
            width: 34px; height: 34px;
            background: radial-gradient(circle, #FFD54F 15%, #E65100 65%, rgba(183, 28, 28, 0.4) 80%, transparent 85%);
            border-radius: 50%;
            box-shadow: 0 0 24px rgba(230, 81, 0, 0.95);
            animation: markerGlow 1.8s ease-in-out infinite;
        "></div>
        <style>
            @keyframes markerGlow {
                0%, 100% { transform: scale(1); opacity: 0.95; }
                50% { transform: scale(1.3); opacity: 1; }
            }
        </style>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
    });

    marker = L.marker([lat, lng], { icon: fireIcon, zIndexOffset: 1000 }).addTo(map);

    if (popupContent) {
        marker.bindPopup(popupContent, {
            className: 'dark-popup',
            maxWidth: 320,
        }).openPopup();
    }
}

// ── 3. CONAF Hotspots Monitoring Engine ────────────────────────
function initHotspotFilters() {
    document.getElementById('filter-region')?.addEventListener('change', () => renderHotspots());
    document.getElementById('filter-severity')?.addEventListener('change', () => renderHotspots());
}

async function loadHistoricalHotspots() {
    if (!historicalHotspotsData) {
        try {
            const resp = await fetch('/api/historical-hotspots');
            const data = await resp.json();
            historicalHotspotsData = data.hotspots || [];
        } catch (err) {
            console.error('Error cargando focos de incendios:', err);
            return;
        }
    }

    renderHotspots();

    // Smooth fit bounds to central/southern active zone on startup
    map.fitBounds([
        [-33.2, -73.8],
        [-40.2, -70.8]
    ], { padding: [20, 20] });
}

function renderHotspots() {
    if (!historicalHotspotsData) return;

    hotspotsLayerGroup.clearLayers();

    const selectedRegion = document.getElementById('filter-region')?.value || 'all';
    const selectedSeverity = document.getElementById('filter-severity')?.value || 'all';

    let visibleCount = 0;

    historicalHotspotsData.forEach(h => {
        // Filter by Region
        if (selectedRegion !== 'all') {
            const regStr = (h.region || '') + ' ' + (h.comuna || '');
            if (!regStr.toLowerCase().includes(selectedRegion.toLowerCase())) {
                return;
            }
        }

        // Filter by Severity
        if (selectedSeverity === 'mega' && h.ha < 500) return;
        if (selectedSeverity === 'medium' && (h.ha < 50 || h.ha >= 500)) return;
        if (selectedSeverity === 'small' && h.ha >= 50) return;

        visibleCount++;

        // Determine styling & colors based on CONAF alert levels
        let fillColor = '#FFEA00';
        let strokeColor = 'rgba(255,255,255,0.85)';
        let radius = 4;

        if (h.type === 'VIIRS Satélite') {
            fillColor = '#E040FB';
            radius = Math.min(8, Math.max(4, Math.log10(h.ha + 1) * 2.2));
        } else if (h.ha >= 500) {
            fillColor = '#FF1744'; // Megaincendio / Alerta Roja
            radius = Math.min(10, Math.max(6, Math.log10(h.ha + 1) * 2.5));
        } else if (h.ha >= 50) {
            fillColor = '#FF9100'; // Alerta Amarilla
            radius = Math.min(7, Math.max(4.5, Math.log10(h.ha + 1) * 2));
        } else {
            fillColor = '#FFEA00'; // Foco Menor
            radius = 3.5;
        }

        const circle = L.circleMarker([h.lat, h.lon], {
            radius: radius,
            fillColor: fillColor,
            color: strokeColor,
            weight: 1,
            opacity: 0.85,
            fillOpacity: 0.75
        });

        // Hover tooltip
        circle.bindTooltip(`
            <div style="font-family: Inter, sans-serif; font-size: 0.8rem; line-height: 1.3;">
                <strong style="color:${fillColor};">🔥 ${h.name || 'Incendio Forestal'}</strong><br>
                📍 ${h.comuna || 'Chile'} · <strong>${h.ha.toLocaleString()} ha</strong><br>
                <span style="color:#AAA; font-size: 0.72rem;">${h.fecha || ''} · ${h.alerta || ''}</span>
            </div>
        `, { sticky: true });

        // Click popup
        circle.on('click', (e) => {
            L.DomEvent.stopPropagation(e);
            
            const popupHtml = `
                <div style="font-family: Inter, sans-serif; padding: 4px; max-width: 260px;">
                    <div style="font-size: 0.95rem; font-weight: 800; color: ${fillColor}; line-height: 1.2;">
                        ${h.name || 'Incendio Forestal'}
                    </div>
                    <div style="font-size: 0.78rem; font-weight: 700; color: #FFF; margin: 4px 0;">
                        ${h.comuna} · ${h.region}
                    </div>
                    <div style="font-size: 0.75rem; color: #BBB; border-top: 1px solid rgba(255,255,255,0.12); padding-top: 6px; margin-top: 6px;">
                        📅 <strong>Fecha:</strong> ${h.fecha}<br>
                        🔥 <strong>Superficie Quemada:</strong> ${h.ha.toLocaleString()} ha<br>
                        ⚠️ <strong>Alerta:</strong> <span style="color:${fillColor}; font-weight:700;">${h.alerta}</span><br>
                        🔍 <strong>Causa:</strong> ${h.causa}
                    </div>
                    <button class="btn-popup-inspect" onclick="inspectHotspot(${h.lat}, ${h.lon}, '${h.fecha}')">
                        🎯 Evaluar Riesgo en este Punto
                    </button>
                </div>
            `;

            circle.bindPopup(popupHtml).openPopup();
        });

        hotspotsLayerGroup.addLayer(circle);
    });

    const badge = document.getElementById('hotspots-count-badge');
    if (badge) {
        badge.textContent = `${visibleCount.toLocaleString()} Focos`;
    }
}

// Inspect a specific hotspot and run live ML prediction
window.inspectHotspot = async function(lat, lon, fecha) {
    currentCoords = { lat, lon };
    document.getElementById('input-lat').value = lat.toFixed(4);
    document.getElementById('input-lon').value = lon.toFixed(4);
    if (fecha && fecha.length === 10) {
        document.getElementById('input-date').value = fecha;
    }

    placeMarker(lat, lon);
    map.flyTo([lat, lon], 9, { duration: 0.8 });

    await handlePredict();
    loadForecast(lat, lon);
    runSimulation();

    // Smooth scroll to results
    document.getElementById('result-container')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
};

// ── 4. Form & Presets ──────────────────────────────────────────
function initForm() {
    const form = document.getElementById('predict-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handlePredict();
        loadForecast(currentCoords.lat, currentCoords.lon);
        runSimulation();
    });
}

function initPresets() {
    document.querySelectorAll('.btn-preset').forEach(btn => {
        btn.addEventListener('click', async () => {
            const lat = parseFloat(btn.getAttribute('data-lat'));
            const lon = parseFloat(btn.getAttribute('data-lon'));
            currentCoords = { lat, lon };

            document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            document.getElementById('input-lat').value = lat.toFixed(4);
            document.getElementById('input-lon').value = lon.toFixed(4);
            placeMarker(lat, lon);
            map.flyTo([lat, lon], 8, { duration: 0.8 });

            await handlePredict();
            loadForecast(lat, lon);
            runSimulation();
        });
    });
}

function initDatePresets() {
    const inputDate = document.getElementById('input-date');
    if (!inputDate) return;

    inputDate.addEventListener('change', () => {
        updateDateModeBadge(inputDate.value);
    });

    document.querySelectorAll('.btn-date-preset').forEach(btn => {
        btn.addEventListener('click', async () => {
            const mode = btn.getAttribute('data-mode');
            const fixedDate = btn.getAttribute('data-date');
            const now = new Date();
            let targetDate = new Date();

            if (fixedDate) {
                inputDate.value = fixedDate;
            } else if (mode === 'today') {
                inputDate.value = now.toISOString().split('T')[0];
            } else if (mode === 'yesterday') {
                targetDate.setDate(now.getDate() - 1);
                inputDate.value = targetDate.toISOString().split('T')[0];
            } else if (mode === 'past7') {
                targetDate.setDate(now.getDate() - 7);
                inputDate.value = targetDate.toISOString().split('T')[0];
            } else if (mode === 'future7') {
                targetDate.setDate(now.getDate() + 7);
                inputDate.value = targetDate.toISOString().split('T')[0];
            }

            updateDateModeBadge(inputDate.value);
            await handlePredict();
            loadForecast(currentCoords.lat, currentCoords.lon);
            runSimulation();
        });
    });
}

function updateDateModeBadge(dateStr) {
    const badge = document.getElementById('date-mode-badge');
    if (!badge || !dateStr) return;

    const target = new Date(dateStr + 'T12:00:00');
    const now = new Date();
    const diffDays = Math.round((target - now) / (1000 * 60 * 60 * 24));

    if (diffDays < -14) {
        badge.textContent = `⏪ Archivo Histórico (${dateStr.slice(0, 4)})`;
        badge.style.background = 'rgba(255, 143, 0, 0.15)';
        badge.style.color = '#FFB74D';
        badge.style.borderColor = 'rgba(255, 143, 0, 0.4)';
    } else if (diffDays > 14) {
        badge.textContent = `📅 Futuro (Climatología ERA5)`;
        badge.style.background = 'rgba(33, 150, 243, 0.15)';
        badge.style.color = '#64B5F6';
        badge.style.borderColor = 'rgba(33, 150, 243, 0.4)';
    } else {
        badge.textContent = `📍 Tiempo Real / Pronóstico`;
        badge.style.background = 'rgba(0, 230, 118, 0.15)';
        badge.style.color = '#00E676';
        badge.style.borderColor = 'rgba(0, 230, 118, 0.4)';
    }
}

function setDefaultDate() {
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    document.getElementById('input-date').value = dateStr;
    document.getElementById('input-lat').value = currentCoords.lat.toFixed(4);
    document.getElementById('input-lon').value = currentCoords.lon.toFixed(4);
    updateDateModeBadge(dateStr);
}

async function handlePredict() {
    const lat = parseFloat(document.getElementById('input-lat').value);
    const lon = parseFloat(document.getElementById('input-lon').value);
    const fecha = document.getElementById('input-date').value;

    if (isNaN(lat) || isNaN(lon) || !fecha) {
        showToast('Completa todos los campos');
        return;
    }

    currentCoords = { lat, lon };
    updateDateModeBadge(fecha);

    // UI Loading state
    const btn = document.getElementById('btn-predict');
    const btnText = btn.querySelector('.btn-text');
    const btnLoading = btn.querySelector('.btn-loading');
    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline';

    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lon, fecha }),
        });

        const data = await response.json();

        if (!response.ok) {
            showToast(data.error || 'Error en la predicción');
            return;
        }

        lastPredictionResult = data;
        displayResult(data);
        placeMarker(lat, lon, buildPopupContent(data));
        addToHistory(data);

        // Update forecast headers
        document.getElementById('forecast-coords-display').textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
        document.getElementById('forecast-landcover-display').textContent = data.spatial_info.land_cover_name;

    } catch (err) {
        showToast('Error de conexión con el servidor');
        console.error(err);
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

// ── 5. Results Display & SHAP ──────────────────────────────────
function displayResult(data) {
    const container = document.getElementById('result-container');
    container.style.display = 'block';

    const probability = data.probability;
    const sp = data.spatial_info;
    const ws = data.weather_summary;

    // 0. Update Header Telemetry Strip
    const hdrPlace = document.getElementById('hdr-active-place');
    if (hdrPlace) hdrPlace.textContent = `${sp.nearest_town} (Lat ${data.location.lat.toFixed(2)}, Lon ${data.location.lon.toFixed(2)})`;
    const hdrDate = document.getElementById('hdr-active-date');
    if (hdrDate) hdrDate.textContent = data.fecha;
    const hdrRisk = document.getElementById('hdr-active-risk');
    if (hdrRisk) {
        hdrRisk.textContent = `${(probability * 100).toFixed(1)}% ${data.risk_level}`;
        hdrRisk.style.color = data.risk_color;
        hdrRisk.style.background = hexToRGBA(data.risk_color, 0.2);
        hdrRisk.style.borderColor = hexToRGBA(data.risk_color, 0.45);
    }

    // 1. Gauge Needle Animation
    const angle = -90 + (probability * 180);
    const needle = document.getElementById('gauge-needle');
    needle.setAttribute('transform', `rotate(${angle}, 100, 100)`);

    // 2. Gauge Value & Label
    const gaugeValue = document.getElementById('gauge-value');
    gaugeValue.textContent = `${(probability * 100).toFixed(1)}%`;
    gaugeValue.style.color = data.risk_color;

    const riskLabel = document.getElementById('risk-label');
    riskLabel.textContent = `Riesgo ${data.risk_level}`;
    riskLabel.style.color = data.risk_color;
    riskLabel.style.background = hexToRGBA(data.risk_color, 0.15);
    riskLabel.style.border = `1px solid ${hexToRGBA(data.risk_color, 0.4)}`;

    document.getElementById('risk-description').textContent = data.risk_description || '';

    // 3. Regla 30-30-30 CONAF Evaluator
    evaluate303030(ws);

    // 4. Action Protocol Guidance
    updateActionProtocol(probability, ws);

    // 5. Data Provenance & API Transparency
    if (data.data_provenance) {
        const prov = data.data_provenance;
        const provSource = document.getElementById('prov-weather-source');
        if (provSource) provSource.textContent = prov.source_name;
        
        const provLatency = document.getElementById('prov-latency');
        if (provLatency) provLatency.textContent = `${prov.latency_ms} ms`;
        
        const provHttp = document.getElementById('prov-http-status');
        if (provHttp) provHttp.textContent = `${prov.http_status} OK`;
        
        const provSamples = document.getElementById('prov-hourly-samples');
        if (provSamples) provSamples.textContent = `${prov.hourly_samples} hrs (${prov.start_window} a ${prov.end_window})`;
        
        const provLink = document.getElementById('prov-api-link');
        if (provLink) {
            provLink.href = prov.api_url;
            provLink.textContent = prov.api_url;
        }
        
        const provBadge = document.getElementById('prov-status-badge');
        if (provBadge) {
            if (prov.is_fallback) {
                provBadge.textContent = '🔵 Climatología ERA5 2023';
                provBadge.style.color = '#64B5F6';
                provBadge.style.background = 'rgba(33, 150, 243, 0.15)';
            } else if (prov.source_type === 'historical_archive') {
                provBadge.textContent = '🟢 ERA5 Histórico Real';
                provBadge.style.color = '#00E676';
                provBadge.style.background = 'rgba(0, 230, 118, 0.15)';
            } else {
                provBadge.textContent = '🟢 Pronóstico Oficial ECMWF';
                provBadge.style.color = '#00E676';
                provBadge.style.background = 'rgba(0, 230, 118, 0.15)';
            }
        }
    }

    // 6. Real Spatial Information & Slope Meter
    document.getElementById('sp-landcover').textContent = sp.land_cover_name;
    document.getElementById('sp-town').textContent = `${sp.nearest_town} (${sp.dist_nearest_town_km} km)`;
    document.getElementById('sp-elevation').textContent = `${sp.elevation_m} m`;
    document.getElementById('sp-slope').textContent = `${sp.slope_deg}°`;

    // Fuel Risk Badge
    const fuelBadge = document.getElementById('sp-fuel-badge');
    if (fuelBadge) {
        const coverLower = (sp.land_cover_name || '').toLowerCase();
        if (coverLower.includes('plantación') || coverLower.includes('pino') || coverLower.includes('eucalipto')) {
            fuelBadge.textContent = '🔥 Combustible Forestal Altamente Inflamable';
            fuelBadge.style.color = '#FF5252';
            fuelBadge.style.background = 'rgba(255, 23, 68, 0.15)';
            fuelBadge.style.borderColor = 'rgba(255, 23, 68, 0.4)';
        } else if (coverLower.includes('matorral') || coverLower.includes('pastizal') || coverLower.includes('pradera')) {
            fuelBadge.textContent = '🌾 Combustible Fino de Propagación Rápida';
            fuelBadge.style.color = '#FFB74D';
            fuelBadge.style.background = 'rgba(255, 143, 0, 0.15)';
            fuelBadge.style.borderColor = 'rgba(255, 143, 0, 0.4)';
        } else if (coverLower.includes('nativo')) {
            fuelBadge.textContent = '🌲 Bosque Nativo (Mayor Retención de Humedad)';
            fuelBadge.style.color = '#81C784';
            fuelBadge.style.background = 'rgba(76, 175, 80, 0.15)';
            fuelBadge.style.borderColor = 'rgba(76, 175, 80, 0.4)';
        } else {
            fuelBadge.textContent = '💧 Cobertura de Baja Propagación';
            fuelBadge.style.color = '#64B5F6';
            fuelBadge.style.background = 'rgba(33, 150, 243, 0.15)';
            fuelBadge.style.borderColor = 'rgba(33, 150, 243, 0.4)';
        }
    }

    // Slope meter
    const slopeFill = document.getElementById('slope-meter-fill');
    const slopeCurrent = document.getElementById('slope-meter-current');
    if (slopeFill && slopeCurrent) {
        const slopePct = Math.min(100, Math.max(4, (sp.slope_deg / 45) * 100));
        slopeFill.style.width = `${slopePct}%`;
        
        let slopeCategory = 'Plano (Escurrimiento mínimo)';
        if (sp.slope_deg > 25) slopeCategory = 'Ladera Crítica (Propagación Ascendente 2.5x)';
        else if (sp.slope_deg > 12) slopeCategory = 'Colina Moderada (Acelera Fuego)';
        slopeCurrent.textContent = `Pendiente: ${sp.slope_deg}° — ${slopeCategory}`;
    }

    // 7. Weather Summary & Status Badges
    document.getElementById('w-temp').textContent = `${ws.temp_max}°C`;
    document.getElementById('w-humidity').textContent = `${ws.humidity_min}%`;
    document.getElementById('w-precip').textContent = `${ws.precip_total} mm`;
    document.getElementById('w-wind').textContent = `${ws.wind_max} km/h`;

    // Weather threshold tags
    updateWeatherStatusBadges(ws);

    // 8. Past 7-Day Evolution Breakdown
    const pastGrid = document.getElementById('past-days-grid');
    if (pastGrid && data.past_7_days && data.past_7_days.length > 0) {
        pastGrid.innerHTML = data.past_7_days.map(d => `
            <div class="past-day-mini-card">
                <span class="day-lbl">${d.date.slice(5)}</span>
                <span class="day-temp">🌡️ ${d.temp_max}°C</span>
                <span class="day-hum">💧 ${d.humidity_min}%</span>
                <span class="day-rain">🌧️ ${d.precip}mm</span>
            </div>
        `).join('');
    }

    // 9. Render SHAP Waterfall Bars & Narrative
    currentShapFactors = data.shap_factors || [];
    renderSHAPBars('shap-bars', currentShapFactors);
    renderSHAPNarrative(currentShapFactors, data.risk_level, probability);

    // 10. Update Export Action Links
    updateExportLinks(data.location.lat, data.location.lon, data.fecha);
}

// ── 5.0 Regla 30-30-30 Evaluator ───────────────────────────────
function evaluate303030(ws) {
    const fTemp = document.getElementById('factor-temp');
    const fHum = document.getElementById('factor-hum');
    const fWind = document.getElementById('factor-wind');
    const badge = document.getElementById('rule-30-badge');

    if (!fTemp || !fHum || !fWind || !badge) return;

    const isTemp = ws.temp_max >= 30.0;
    const isHum = ws.humidity_min <= 30.0;
    const isWind = ws.wind_max >= 30.0;

    fTemp.classList.toggle('active-risk', isTemp);
    fHum.classList.toggle('active-risk', isHum);
    fWind.classList.toggle('active-risk', isWind);

    // Update dynamic meter progress bars
    const meterTempFill = document.getElementById('meter-temp-fill');
    const meterTempVal = document.getElementById('meter-temp-val');
    if (meterTempFill && meterTempVal) {
        const tempPct = Math.min(100, Math.max(0, (ws.temp_max / 42) * 100));
        meterTempFill.style.width = `${tempPct}%`;
        meterTempFill.classList.toggle('critical', isTemp);
        meterTempVal.textContent = `${ws.temp_max}°C`;
    }

    const meterHumFill = document.getElementById('meter-hum-fill');
    const meterHumVal = document.getElementById('meter-hum-val');
    if (meterHumFill && meterHumVal) {
        // Lower humidity = higher danger bar
        const humDangerPct = Math.min(100, Math.max(0, ((100 - ws.humidity_min) / 100) * 100));
        meterHumFill.style.width = `${humDangerPct}%`;
        meterHumFill.classList.toggle('critical', isHum);
        meterHumVal.textContent = `${ws.humidity_min}%`;
    }

    const meterWindFill = document.getElementById('meter-wind-fill');
    const meterWindVal = document.getElementById('meter-wind-val');
    if (meterWindFill && meterWindVal) {
        const windPct = Math.min(100, Math.max(0, (ws.wind_max / 65) * 100));
        meterWindFill.style.width = `${windPct}%`;
        meterWindFill.classList.toggle('critical', isWind);
        meterWindVal.textContent = `${ws.wind_max} km/h`;
    }

    let activeCount = (isTemp ? 1 : 0) + (isHum ? 1 : 0) + (isWind ? 1 : 0);

    if (activeCount === 3) {
        badge.textContent = '🚨 Condición 30-30-30 Cumplida (Peligro Extremo)';
        badge.style.background = 'rgba(255, 23, 68, 0.25)';
        badge.style.color = '#FF1744';
        badge.style.borderColor = 'rgba(255, 23, 68, 0.6)';
    } else if (activeCount === 2) {
        badge.textContent = '⚠️ 2/3 Condiciones de Riesgo Activas';
        badge.style.background = 'rgba(255, 143, 0, 0.2)';
        badge.style.color = '#FF9100';
        badge.style.borderColor = 'rgba(255, 143, 0, 0.5)';
    } else if (activeCount === 1) {
        badge.textContent = '⚡ 1 Condición de Riesgo Activa';
        badge.style.background = 'rgba(255, 213, 79, 0.15)';
        badge.style.color = '#FFD54F';
        badge.style.borderColor = 'rgba(255, 213, 79, 0.35)';
    } else {
        badge.textContent = '🟢 Condiciones Normales (Fuera de Alerta)';
        badge.style.background = 'rgba(0, 230, 118, 0.15)';
        badge.style.color = '#00E676';
        badge.style.borderColor = 'rgba(0, 230, 118, 0.35)';
    }
}

function updateWeatherStatusBadges(ws) {
    const sTemp = document.getElementById('w-temp-status');
    const sHum = document.getElementById('w-hum-status');
    const sPrecip = document.getElementById('w-precip-status');
    const sWind = document.getElementById('w-wind-status');

    if (sTemp) {
        if (ws.temp_max >= 33) { sTemp.textContent = 'Ola de Calor'; sTemp.className = 'weather-threshold critical'; }
        else if (ws.temp_max >= 30) { sTemp.textContent = 'Calor Intenso'; sTemp.className = 'weather-threshold warning'; }
        else { sTemp.textContent = 'Moderado'; sTemp.className = 'weather-threshold'; }
    }

    if (sHum) {
        if (ws.humidity_min <= 20) { sHum.textContent = 'Sequedad Extrema'; sHum.className = 'weather-threshold critical'; }
        else if (ws.humidity_min <= 30) { sHum.textContent = 'Baja Humedad'; sHum.className = 'weather-threshold warning'; }
        else { sHum.textContent = 'Humedo'; sHum.className = 'weather-threshold'; }
    }

    if (sPrecip) {
        if (ws.precip_total === 0) { sPrecip.textContent = '0 mm (Seco)'; sPrecip.className = 'weather-threshold warning'; }
        else if (ws.precip_total >= 10) { sPrecip.textContent = 'Lluvia Significativa'; sPrecip.className = 'weather-threshold'; }
        else { sPrecip.textContent = 'Lluvia Débil'; sPrecip.className = 'weather-threshold'; }
    }

    if (sWind) {
        if (ws.wind_max >= 35) { sWind.textContent = 'Viento Crítico'; sWind.className = 'weather-threshold critical'; }
        else if (ws.wind_max >= 25) { sWind.textContent = 'Viento Fuerte'; sWind.className = 'weather-threshold warning'; }
        else { sWind.textContent = 'Brisa Normal'; sWind.className = 'weather-threshold'; }
    }
}

function updateActionProtocol(prob, ws) {
    const textEl = document.getElementById('protocol-text');
    const boxEl = document.getElementById('protocol-box');
    if (!textEl || !boxEl) return;

    if (prob >= 0.75) {
        boxEl.style.borderLeftColor = '#FF1744';
        textEl.innerHTML = `<strong>ALERTA ROJA INSTITUCIONAL (SENAPRED / CONAF):</strong> Riesgo extremo de ignición explosiva y propagación descontrolada. Suspender inmediatamente faenas agrícolas, forestales y uso de maquinaria. Disposición al 100% de brigadas y aeronaves de combate.`;
    } else if (prob >= 0.50) {
        boxEl.style.borderLeftColor = '#FF9100';
        textEl.innerHTML = `<strong>ALERTA AMARILLA POR AMENAZA DE INCENDIO:</strong> Alistamiento prioritario de brigadas CONAF y Bomberos. Prohibición estricta de quemas agrícolas. Reforzar patrullajes preventivos en interfaz urbano-forestal.`;
    } else if (prob >= 0.25) {
        boxEl.style.borderLeftColor = '#FFD54F';
        textEl.innerHTML = `<strong>ALERTA TEMPRANA PREVENTIVA:</strong> Monitoreo activo de torres de detección y satélites. Difusión de medidas de autocuidado a la población y prohibición de fogatas en áreas silvestres.`;
    } else {
        boxEl.style.borderLeftColor = '#00E676';
        textEl.innerHTML = `<strong>CONDICIONES DE VIGILANCIA NORMAL:</strong> Baja probabilidad de ignición. Mantener medidas de precaución estándar y canales de alerta temprana operativos.`;
    }
}

// ── 5.1 SHAP Narrative Generator & Toggles ─────────────────────
function initSHAPViewToggle() {
    const btnBars = document.getElementById('btn-shap-bars');
    const btnText = document.getElementById('btn-shap-text');
    const barsView = document.getElementById('shap-bars');
    const textView = document.getElementById('shap-narrative');

    if (btnBars && btnText && barsView && textView) {
        btnBars.addEventListener('click', () => {
            btnBars.classList.add('active');
            btnText.classList.remove('active');
            barsView.style.display = 'flex';
            textView.style.display = 'none';
        });

        btnText.addEventListener('click', () => {
            btnText.classList.add('active');
            btnBars.classList.remove('active');
            barsView.style.display = 'none';
            textView.style.display = 'block';
        });
    }
}

function renderSHAPNarrative(factors, riskLevel, prob) {
    const content = document.getElementById('narrative-content');
    if (!content || !factors || factors.length === 0) return;

    const topPositives = factors.filter(f => f.impact > 0).slice(0, 3);
    const topNegatives = factors.filter(f => f.impact < 0).slice(0, 2);

    let html = `<ul>`;

    if (topPositives.length > 0) {
        topPositives.forEach(f => {
            html += `
                <li class="narrative-item positive">
                    <span class="narrative-icon">🔥</span>
                    <div><strong>${f.label}:</strong> Con valor de <em>${f.value}</em>, impulsó al alza la probabilidad en <strong>+${(Math.abs(f.impact) * 10).toFixed(1)} pts de riesgo</strong>.</div>
                </li>
            `;
        });
    }

    if (topNegatives.length > 0) {
        topNegatives.forEach(f => {
            html += `
                <li class="narrative-item negative">
                    <span class="narrative-icon">🛡️</span>
                    <div><strong>${f.label}:</strong> Con valor de <em>${f.value}</em>, actuó como factor protector conteniendo el riesgo en <strong>-${(Math.abs(f.impact) * 10).toFixed(1)} pts</strong>.</div>
                </li>
            `;
        });
    }

    html += `</ul>`;
    content.innerHTML = html;
}

function updateExportLinks(lat, lon, fecha) {
    const btnDossier = document.getElementById('btn-export-dossier');
    const btnJson = document.getElementById('btn-export-json');
    const btnCsv = document.getElementById('btn-export-csv');

    if (btnDossier) btnDossier.href = `/api/export-report?lat=${lat}&lon=${lon}&fecha=${fecha}&format=html`;
    if (btnJson) btnJson.href = `/api/export-report?lat=${lat}&lon=${lon}&fecha=${fecha}&format=json`;
    if (btnCsv) btnCsv.href = `/api/export-report?lat=${lat}&lon=${lon}&fecha=${fecha}&format=csv`;
}

// ── 5.2 Place Search on Map ────────────────────────────────────
function initPlaceSearch() {
    const input = document.getElementById('map-place-search');
    const clearBtn = document.getElementById('btn-clear-search');
    const dropdown = document.getElementById('search-results-dropdown');
    if (!input || !dropdown) return;

    let searchTimer = null;

    input.addEventListener('input', () => {
        const query = input.value.trim();
        if (query.length > 0) {
            if (clearBtn) clearBtn.style.display = 'block';
        } else {
            if (clearBtn) clearBtn.style.display = 'none';
            dropdown.style.display = 'none';
            return;
        }

        clearTimeout(searchTimer);
        searchTimer = setTimeout(async () => {
            if (query.length < 2) return;
            try {
                const resp = await fetch(`/api/search-places?q=${encodeURIComponent(query)}`);
                const data = await resp.json();
                if (data.results && data.results.length > 0) {
                    dropdown.innerHTML = data.results.map(p => `
                        <div class="search-result-item" data-lat="${p.lat}" data-lon="${p.lon}" data-name="${p.name}">
                            <div>
                                <div class="place-name">${p.name}</div>
                                <div class="place-coords">📍 ${p.lat}, ${p.lon}</div>
                            </div>
                            <span style="font-size:0.7rem;color:var(--fire-orange);font-weight:700;">Evaluar ➜</span>
                        </div>
                    `).join('');
                    dropdown.style.display = 'block';

                    dropdown.querySelectorAll('.search-result-item').forEach(item => {
                        item.addEventListener('click', async () => {
                            const lat = parseFloat(item.getAttribute('data-lat'));
                            const lon = parseFloat(item.getAttribute('data-lon'));
                            const name = item.getAttribute('data-name');

                            document.getElementById('input-lat').value = lat.toFixed(4);
                            document.getElementById('input-lon').value = lon.toFixed(4);
                            currentCoords = { lat, lon };
                            input.value = name;
                            dropdown.style.display = 'none';

                            placeMarker(lat, lon);
                            map.flyTo([lat, lon], 10, { duration: 1.0 });

                            await handlePredict();
                            loadForecast(lat, lon);
                            runSimulation();
                        });
                    });
                } else {
                    dropdown.innerHTML = '<div style="padding:10px 14px;font-size:0.78rem;color:var(--text-muted);">No se encontraron lugares con ese nombre.</div>';
                    dropdown.style.display = 'block';
                }
            } catch (err) {
                console.error(err);
            }
        }, 250);
    });

    clearBtn?.addEventListener('click', () => {
        input.value = '';
        clearBtn.style.display = 'none';
        dropdown.style.display = 'none';
    });

    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

// ── 5.3 Regional Summary & Filters ─────────────────────────────
function initRegionalFilters() {
    document.querySelectorAll('.btn-reg-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const filter = tab.getAttribute('data-filter');
            document.querySelectorAll('.btn-reg-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderFilteredRegionalCards(filter);
        });
    });
}

async function loadRegionalSummary() {
    const grid = document.getElementById('regional-cards-grid');
    if (!grid) return;

    try {
        const resp = await fetch('/api/regional-risk-summary');
        const data = await resp.json();
        activeRegionalData = data.regions || [];

        renderFilteredRegionalCards('all');

    } catch (err) {
        console.error('Error loading regional summary:', err);
    }
}

function renderFilteredRegionalCards(filter) {
    const grid = document.getElementById('regional-cards-grid');
    if (!grid || activeRegionalData.length === 0) return;

    let filtered = activeRegionalData;

    if (filter === 'centro') {
        filtered = activeRegionalData.filter(r => r.macrozone.toLowerCase().includes('centro') && !r.macrozone.toLowerCase().includes('sur'));
    } else if (filter === 'centrosur') {
        filtered = activeRegionalData.filter(r => r.macrozone.toLowerCase().includes('centro-sur') || r.name.includes('Maule') || r.name.includes('Biobío') || r.name.includes('Ñuble'));
    } else if (filter === 'sur') {
        filtered = activeRegionalData.filter(r => r.macrozone.toLowerCase().includes('sur') && !r.macrozone.toLowerCase().includes('austral'));
    } else if (filter === 'austral') {
        filtered = activeRegionalData.filter(r => r.macrozone.toLowerCase().includes('austral') || r.name.includes('Aysén') || r.name.includes('Magallanes'));
    }

    grid.innerHTML = filtered.map(r => `
        <div class="regional-card">
            <div class="regional-card-header">
                <div class="reg-title-box">
                    <h4>${r.name}</h4>
                    <span class="reg-macrozone">${r.macrozone}</span>
                </div>
                <span class="reg-vuln-badge" style="background:${hexToRGBA(r.vulnerability_color, 0.15)};color:${r.vulnerability_color};border:1px solid ${hexToRGBA(r.vulnerability_color, 0.4)};">
                    ${r.vulnerability_level}
                </span>
            </div>
            <ul class="reg-stats-list">
                <li><span>🔥 Focos Históricos:</span> <strong>${r.historical_hotspots} focos</strong></li>
                <li><span>🌿 Combustible Dominante:</span> <strong>${r.main_fuel}</strong></li>
            </ul>
            <button type="button" class="btn-eval-region" onclick="evaluateRegionTarget(${r.lat}, ${r.lon}, '${r.name}')">
                📍 Evaluar Riesgo en ${r.name}
            </button>
        </div>
    `).join('');
}

window.evaluateRegionTarget = async function(lat, lon, name) {
    document.getElementById('input-lat').value = lat.toFixed(4);
    document.getElementById('input-lon').value = lon.toFixed(4);
    currentCoords = { lat, lon };

    placeMarker(lat, lon);
    map.flyTo([lat, lon], 8, { duration: 1.0 });

    await handlePredict();
    loadForecast(lat, lon);
    runSimulation();

    document.getElementById('section-map-predict').scrollIntoView({ behavior: 'smooth' });
};

function renderSHAPBars(containerId, factors) {
    const container = document.getElementById(containerId);
    if (!container || !factors || factors.length === 0) {
        if (container) container.innerHTML = '<p style="color:var(--text-muted);font-size:0.8rem;">No hay datos SHAP disponibles.</p>';
        return;
    }

    const maxImpact = Math.max(...factors.map(f => Math.abs(f.impact)), 0.1);

    container.innerHTML = factors.map(f => {
        const isPos = f.impact > 0;
        const widthPercent = Math.min(100, Math.max(8, (Math.abs(f.impact) / maxImpact) * 100));
        const dirClass = isPos ? 'positive' : 'negative';
        const sign = isPos ? '+' : '';

        return `
            <div class="shap-bar-item">
                <div class="shap-bar-header">
                    <span class="shap-bar-title">${f.label} <small style="color:var(--text-muted);">(${f.value})</small></span>
                    <span class="shap-bar-val ${dirClass}">${sign}${f.impact.toFixed(3)}</span>
                </div>
                <div class="shap-bar-track">
                    <div class="shap-bar-fill ${dirClass}" style="width: ${widthPercent}%;"></div>
                </div>
            </div>
        `;
    }).join('');
}

function buildPopupContent(data) {
    return `
        <div style="text-align:center; padding: 4px; font-family: Inter, sans-serif;">
            <div style="font-size: 1.4rem; font-weight: 800; color: ${data.risk_color};">
                ${(data.probability * 100).toFixed(1)}%
            </div>
            <div style="font-size: 0.85rem; font-weight: 800; color: ${data.risk_color};
                        text-transform: uppercase; letter-spacing: 0.08em; margin: 4px 0;">
                Riesgo ${data.risk_level}
            </div>
            <div style="font-size: 0.75rem; color: #B0B0D0; margin: 6px 0;">
                ${data.spatial_info.land_cover_name}<br>
                ${data.fecha} · Elev. ${data.spatial_info.elevation_m}m
            </div>
            <div style="font-size: 0.72rem; color: #8888AA; border-top: 1px solid rgba(120,120,180,0.25); padding-top: 6px;">
                🌡️ ${data.weather_summary.temp_max}°C &nbsp;
                💧 ${data.weather_summary.humidity_min}% &nbsp;
                💨 ${data.weather_summary.wind_max}km/h
            </div>
        </div>
    `;
}

// ── 6. 7-Day Forecast ──────────────────────────────────────────
function initForecastControls() {
    const btn = document.getElementById('btn-refresh-forecast');
    if (btn) {
        btn.addEventListener('click', () => {
            loadForecast(currentCoords.lat, currentCoords.lon);
        });
    }
}

async function loadForecast(lat, lon) {
    const grid = document.getElementById('forecast-grid');
    grid.innerHTML = '<div class="loading-placeholder"><span class="spinner"></span> Obteniendo pronóstico meteorológico a 7 días...</div>';

    document.getElementById('forecast-coords-display').textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;

    try {
        const resp = await fetch('/api/forecast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lon })
        });
        const data = await resp.json();

        if (!resp.ok) {
            grid.innerHTML = `<div class="loading-placeholder" style="color:#FF5252;">${data.error || 'Error obteniendo pronóstico'}</div>`;
            return;
        }

        if (data.location && data.location.land_cover_name) {
            document.getElementById('forecast-landcover-display').textContent = data.location.land_cover_name;
        }

        const days = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

        // Find peak risk day
        let maxProb = -1;
        let peakDay = null;
        data.forecast.forEach(item => {
            if (item.probability > maxProb) {
                maxProb = item.probability;
                peakDay = item;
            }
        });

        const peakBadge = document.getElementById('forecast-peak-badge');
        if (peakBadge && peakDay) {
            peakBadge.textContent = `Pico Semanal: ${peakDay.date} (${(maxProb * 100).toFixed(0)}% Riesgo ${peakDay.risk_level})`;
            peakBadge.style.color = peakDay.risk_color;
            peakBadge.style.background = hexToRGBA(peakDay.risk_color, 0.2);
            peakBadge.style.borderColor = hexToRGBA(peakDay.risk_color, 0.5);
        }

        grid.innerHTML = data.forecast.map(item => {
            const dateObj = new Date(item.date + 'T12:00:00');
            const dayName = days[dateObj.getDay()];
            const probPct = (item.probability * 100).toFixed(0);
            const isPeak = item.date === peakDay?.date && maxProb > 0.3;

            return `
                <div class="forecast-card ${isPeak ? 'peak-card' : ''}" style="border-top: 3px solid ${item.risk_color};" onclick="evaluateForecastDay('${item.date}')" title="Click para evaluar este día">
                    <div class="forecast-card-day">${dayName}</div>
                    <div class="forecast-card-date">${item.date}</div>
                    <div class="forecast-card-prob" style="color: ${item.risk_color};">${probPct}%</div>
                    <div class="forecast-card-badge" style="color: ${item.risk_color}; background: ${hexToRGBA(item.risk_color, 0.15)};">
                        ${item.risk_level}
                    </div>
                    <div class="forecast-card-metrics">
                        <div class="forecast-metric-row"><span>🌡️ Temp:</span><strong>${item.temp_max}°C</strong></div>
                        <div class="forecast-metric-row"><span>💧 Hum:</span><strong>${item.humidity_min}%</strong></div>
                        <div class="forecast-metric-row"><span>💨 Viento:</span><strong>${item.wind_max} km/h</strong></div>
                        <div class="forecast-metric-row"><span>🌧️ Lluvia:</span><strong>${item.precip_total} mm</strong></div>
                    </div>
                    <span class="forecast-click-hint">Click para evaluar ➜</span>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error('Error cargando pronóstico:', err);
        grid.innerHTML = '<div class="loading-placeholder" style="color:#FF5252;">Error de conexión con el servidor.</div>';
    }
}

window.evaluateForecastDay = async function(fecha) {
    document.getElementById('input-date').value = fecha;
    updateDateModeBadge(fecha);
    await handlePredict();
    runSimulation();
    document.getElementById('section-map-predict').scrollIntoView({ behavior: 'smooth' });
    showToast(`📅 Evaluando pronóstico para el ${fecha}`);
};

// ── 7. What-If Scenario Simulator ──────────────────────────────
function initSimulator() {
    const sliders = [
        { id: 'sim-temp', badge: 'badge-temp', unit: '°C', prefix: '+' },
        { id: 'sim-humidity', badge: 'badge-humidity', unit: '%', prefix: '+' },
        { id: 'sim-wind', badge: 'badge-wind', unit: ' km/h', prefix: '+' },
        { id: 'sim-slope', badge: 'badge-slope', unit: '°', prefix: '' },
    ];

    sliders.forEach(s => {
        const input = document.getElementById(s.id);
        const badge = document.getElementById(s.badge);
        if (input && badge) {
            input.addEventListener('input', () => {
                const val = parseFloat(input.value);
                badge.textContent = `${val > 0 ? s.prefix : ''}${val}${s.unit}`;
                triggerDebouncedSimulation();
            });
        }
    });

    const selectCover = document.getElementById('sim-landcover');
    if (selectCover) {
        selectCover.addEventListener('change', () => triggerDebouncedSimulation());
    }

    document.querySelectorAll('.btn-scenario').forEach(btn => {
        btn.addEventListener('click', () => {
            const temp = parseFloat(btn.getAttribute('data-temp') || 0);
            const hum = parseFloat(btn.getAttribute('data-hum') || 0);
            const wind = parseFloat(btn.getAttribute('data-wind') || 0);
            const cover = btn.getAttribute('data-cover') || '';

            setSimulatorValues(temp, hum, wind, cover);
            runSimulation();
        });
    });

    document.getElementById('btn-reset-scenario')?.addEventListener('click', () => {
        setSimulatorValues(0, 0, 0, '');
        runSimulation();
    });
}

function setSimulatorValues(temp, hum, wind, cover = '') {
    const sTemp = document.getElementById('sim-temp');
    const sHum = document.getElementById('sim-humidity');
    const sWind = document.getElementById('sim-wind');
    const sCover = document.getElementById('sim-landcover');

    if (sTemp) { sTemp.value = temp; document.getElementById('badge-temp').textContent = `${temp >= 0 ? '+' : ''}${temp}°C`; }
    if (sHum) { sHum.value = hum; document.getElementById('badge-humidity').textContent = `${hum >= 0 ? '+' : ''}${hum}%`; }
    if (sWind) { sWind.value = wind; document.getElementById('badge-wind').textContent = `${wind >= 0 ? '+' : ''}${wind} km/h`; }
    if (sCover) { sCover.value = cover; }
}

function triggerDebouncedSimulation() {
    clearTimeout(simDebounceTimer);
    simDebounceTimer = setTimeout(() => {
        runSimulation();
    }, 250);
}

async function runSimulation() {
    const deltaTemp = parseFloat(document.getElementById('sim-temp')?.value || 0);
    const deltaHum = parseFloat(document.getElementById('sim-humidity')?.value || 0);
    const deltaWind = parseFloat(document.getElementById('sim-wind')?.value || 0);
    const coverOverride = document.getElementById('sim-landcover')?.value || null;
    const slopeVal = document.getElementById('sim-slope')?.value || null;

    try {
        const resp = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: currentCoords.lat,
                lon: currentCoords.lon,
                delta_temp: deltaTemp,
                delta_humidity: deltaHum,
                delta_wind: deltaWind,
                override_land_cover: coverOverride ? parseInt(coverOverride) : null,
                override_slope: slopeVal ? parseFloat(slopeVal) : null
            })
        });

        const data = await resp.json();
        if (!resp.ok) return;

        // Render Baseline Card
        const b = data.baseline;
        document.getElementById('comp-base-prob').textContent = `${(b.probability * 100).toFixed(1)}%`;
        document.getElementById('comp-base-prob').style.color = b.risk_color;
        const bRisk = document.getElementById('comp-base-risk');
        bRisk.textContent = b.risk_level;
        bRisk.style.color = b.risk_color;
        bRisk.style.background = hexToRGBA(b.risk_color, 0.15);
        document.getElementById('comp-base-details').innerHTML = `
            <li>🌡️ Temp. Máx: <span>${b.temp_max}°C</span></li>
            <li>💧 Humedad Mín: <span>${b.humidity_min}%</span></li>
            <li>💨 Viento Máx: <span>${b.wind_max} km/h</span></li>
            <li>🌿 Cobertura: <span>${b.land_cover_name}</span></li>
            <li>📐 Pendiente: <span>${b.slope_deg}°</span></li>
        `;

        // Render Simulated Card
        const s = data.simulated;
        document.getElementById('comp-sim-prob').textContent = `${(s.probability * 100).toFixed(1)}%`;
        document.getElementById('comp-sim-prob').style.color = s.risk_color;
        const sRisk = document.getElementById('comp-sim-risk');
        sRisk.textContent = s.risk_level;
        sRisk.style.color = s.risk_color;
        sRisk.style.background = hexToRGBA(s.risk_color, 0.15);
        document.getElementById('comp-sim-details').innerHTML = `
            <li>🌡️ Temp. Máx: <span>${s.temp_max}°C</span></li>
            <li>💧 Humedad Mín: <span>${s.humidity_min}%</span></li>
            <li>💨 Viento Máx: <span>${s.wind_max} km/h</span></li>
            <li>🌿 Cobertura: <span>${s.land_cover_name}</span></li>
            <li>📐 Pendiente: <span>${s.slope_deg}°</span></li>
        `;

        // Render Delta Badge
        const delta = data.delta_probability;
        const deltaBadge = document.getElementById('comp-delta-badge');
        const sign = delta > 0 ? '+' : '';
        deltaBadge.textContent = `${sign}${(delta * 100).toFixed(1)}%`;
        if (delta > 0.05) {
            deltaBadge.style.color = '#FF5252';
            deltaBadge.style.background = 'rgba(255, 82, 82, 0.15)';
        } else if (delta < -0.05) {
            deltaBadge.style.color = '#69F0AE';
            deltaBadge.style.background = 'rgba(105, 240, 174, 0.15)';
        } else {
            deltaBadge.style.color = '#FFD54F';
            deltaBadge.style.background = 'rgba(255, 213, 79, 0.15)';
        }

        // Render Simulated SHAP
        renderSHAPBars('sim-shap-bars', data.shap_factors);

    } catch (err) {
        console.error('Error running simulation:', err);
    }
}

// ── 8. Model Info & Diagnostics Gallery ─────────────────────────
async function loadModelInfo() {
    try {
        const resp = await fetch('/api/model-info');
        const info = await resp.json();

        const status = document.getElementById('model-status');
        status.classList.add('active');
        status.querySelector('.status-text').textContent =
            `XGBoost V${info.version} · ${info.n_features} features`;

        const metrics = info.metrics || {};
        const grid = document.getElementById('metrics-grid');

        const metricCards = [
            { value: (metrics.roc_auc || 0).toFixed(4), label: 'ROC-AUC', sub: 'Capacidad discriminativa global' },
            { value: (metrics.f1_score || 0).toFixed(4), label: 'F1 Score', sub: 'Equilibrio precisión y recall' },
            { value: (metrics.accuracy || 0).toFixed(4), label: 'Accuracy', sub: 'Exactitud global en test' },
            { value: (metrics.average_precision || metrics.roc_auc || 0).toFixed(4), label: 'Avg. Precision', sub: 'Área bajo PR curve' },
            { value: info.train_samples?.toLocaleString() || '—', label: 'Muestras Train', sub: info.train_years || '2002-2018' },
            { value: info.test_samples?.toLocaleString() || '—', label: 'Muestras Test', sub: info.test_years || '2019-2020' },
            { value: info.n_features || '—', label: 'Variables / Features', sub: 'Satélite + Clima + Topo' },
        ];

        if (metrics.brier_score !== undefined) {
            metricCards.push({
                value: metrics.brier_score.toFixed(4),
                label: 'Brier Score',
                sub: 'Calibración probabilística (↓ mejor)'
            });
        }

        grid.innerHTML = metricCards.map(m => `
            <div class="metric-card">
                <div class="metric-value">${m.value}</div>
                <div class="metric-label">${m.label}</div>
                <div class="metric-sublabel">${m.sub}</div>
            </div>
        `).join('');

    } catch (err) {
        console.error('Error loading model info:', err);
        const status = document.getElementById('model-status');
        status.querySelector('.status-text').textContent = 'Error de conexión';
    }
}

async function loadEvaluationPlots() {
    try {
        const resp = await fetch('/api/evaluation-plots');
        const data = await resp.json();
        const grid = document.getElementById('gallery-grid');

        if (!data.plots || data.plots.length === 0) {
            grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; color:var(--text-muted);">No hay gráficos disponibles.</div>';
            return;
        }

        grid.innerHTML = data.plots.map(plot => `
            <div class="gallery-card" onclick="openLightbox('${plot.url}', '${plot.title}')">
                <img src="${plot.url}" alt="${plot.title}" loading="lazy">
                <div class="gallery-card-info">
                    <h4>${plot.title}</h4>
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error('Error loading plots:', err);
    }
}

// ── 9. Lightbox Modal ──────────────────────────────────────────
function openLightbox(src, caption) {
    const lightbox = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    const cap = document.getElementById('lightbox-caption');

    img.src = src;
    cap.textContent = caption;
    lightbox.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    lightbox.style.display = 'none';
    document.body.style.overflow = '';
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('lightbox-overlay')?.addEventListener('click', closeLightbox);
    document.getElementById('lightbox-close')?.addEventListener('click', closeLightbox);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeLightbox();
    });
});

// ── 10. History & Utilities ────────────────────────────────────
function addToHistory(data) {
    const entry = {
        lat: data.location.lat,
        lon: data.location.lon,
        fecha: data.fecha,
        probability: data.probability,
        risk_level: data.risk_level,
        risk_color: data.risk_color,
        land_cover_name: data.spatial_info.land_cover_name,
        timestamp: Date.now(),
    };

    predictionHistory.unshift(entry);
    if (predictionHistory.length > 20) {
        predictionHistory = predictionHistory.slice(0, 20);
    }
    localStorage.setItem('sipi_history', JSON.stringify(predictionHistory));
    renderHistory();
}

function renderHistory() {
    const section = document.getElementById('history-section');
    const list = document.getElementById('history-list');

    if (!section || !list) return;

    if (predictionHistory.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    list.innerHTML = predictionHistory.map(entry => `
        <div class="history-item" onclick="replayPrediction(${entry.lat}, ${entry.lon}, '${entry.fecha}')">
            <span class="history-coords">${entry.lat.toFixed(3)}, ${entry.lon.toFixed(3)} · ${entry.fecha}</span>
            <span class="history-risk" style="color: ${entry.risk_color};
                  background: ${hexToRGBA(entry.risk_color, 0.15)};">
                ${(entry.probability * 100).toFixed(0)}% ${entry.risk_level}
            </span>
        </div>
    `).join('');

    document.getElementById('btn-clear-history')?.addEventListener('click', () => {
        predictionHistory = [];
        localStorage.removeItem('sipi_history');
        renderHistory();
    });
}

function replayPrediction(lat, lon, fecha) {
    document.getElementById('input-lat').value = lat.toFixed(4);
    document.getElementById('input-lon').value = lon.toFixed(4);
    document.getElementById('input-date').value = fecha;
    currentCoords = { lat, lon };
    placeMarker(lat, lon);
    handlePredict();
    loadForecast(lat, lon);
    runSimulation();
    document.getElementById('section-map-predict').scrollIntoView({ behavior: 'smooth' });
}

function hexToRGBA(hex, alpha) {
    if (!hex || hex.length < 7) return `rgba(230, 81, 0, ${alpha})`;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function showToast(message) {
    const existing = document.querySelector('.error-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
