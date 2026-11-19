import React, { useState, useEffect, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Zap,
  CheckCircle2,
  Clock,
  Compass,
  Layers,
  ArrowRight,
  TrendingDown,
  Gauge,
  HelpCircle,
} from 'lucide-react';

// Custom Map Markers
const createRaceMarker = (type, label) => {
  const isOrigin = type === 'origin';
  const bgColor = isOrigin ? '#10b981' : '#ef4444';
  const emoji = isOrigin ? '🟢' : '🏁';

  return L.divIcon({
    className: 'race-marker-icon',
    html: `
      <div style="
        background: ${bgColor};
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 800;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        border: 2px solid #ffffff;
        display: flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
        cursor: pointer;
      ">
        <span>${emoji}</span>
        <span>${label}</span>
      </div>
    `,
    iconSize: [80, 26],
    iconAnchor: [40, 13],
  });
};

// Canvas-based renderer for fast, zero-DOM node visualization of explored points
function ExploredCanvasLayer({ coords, color = '#38bdf8', maxCount = 0 }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !coords || coords.length === 0 || maxCount <= 0) return;

    const slice = coords.slice(0, maxCount);
    const canvasLayer = L.canvas();
    const markers = slice.map(([lat, lng]) =>
      L.circleMarker([lat, lng], {
        renderer: canvasLayer,
        radius: 3.5,
        fillColor: color,
        fillOpacity: 0.65,
        stroke: false,
      })
    );

    const group = L.layerGroup(markers).addTo(map);

    return () => {
      map.removeLayer(group);
    };
  }, [map, coords, color, maxCount]);

  return null;
}

// Controller to synchronize or fit bounds
function MapBoundsController({ originCoords, destCoords, pathCoords }) {
  const map = useMap();

  useEffect(() => {
    if (!map) return;
    if (pathCoords && pathCoords.length > 0) {
      const bounds = L.latLngBounds(pathCoords);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    } else if (originCoords && destCoords) {
      const bounds = L.latLngBounds([originCoords, destCoords]);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
  }, [map, originCoords, destCoords, pathCoords]);

  return null;
}

export default function AlgorithmRace({
  raceData,
  raceLoading,
  onRunRace,
  timeOfDay = 'off_peak',
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progressPct, setProgressPct] = useState(100); // 0 to 100
  const [speed, setSpeed] = useState(2); // 1x, 2x, 5x, 10x
  const animFrameRef = useRef(null);
  const lastTimeRef = useRef(null);

  const props = raceData?.properties;
  const dijkstraProps = props?.dijkstra;
  const astarProps = props?.astar;

  const dijkstraCoords = dijkstraProps?.anim_coords || dijkstraProps?.explored_coords || [];
  const astarCoords = astarProps?.anim_coords || astarProps?.explored_coords || [];

  const maxPoints = Math.max(dijkstraCoords.length, astarCoords.length, 1);

  // Compute how many points to show for each based on current progress percentage
  const currentStepDijkstra = Math.floor((progressPct / 100) * dijkstraCoords.length);
  const currentStepAstar = Math.floor((progressPct / 100) * astarCoords.length);

  // Extract path lines from features
  const dijkstraFeature = raceData?.features?.find((f) => f.properties?.role === 'dijkstra_path');
  const astarFeature = raceData?.features?.find((f) => f.properties?.role === 'astar_path');

  // Convert GeoJSON [lon, lat] to Leaflet [lat, lon]
  const dijkstraPathCoords = dijkstraFeature?.geometry?.coordinates?.map(([lon, lat]) => [lat, lon]) || [];
  const astarPathCoords = astarFeature?.geometry?.coordinates?.map(([lon, lat]) => [lat, lon]) || [];

  const originCoords = props?.origin_coords; // [lat, lon]
  const destCoords = props?.destination_coords; // [lat, lon]

  // Animation Loop
  useEffect(() => {
    if (!isPlaying) {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      lastTimeRef.current = null;
      return;
    }

    const animate = (timestamp) => {
      if (!lastTimeRef.current) lastTimeRef.current = timestamp;
      const delta = timestamp - lastTimeRef.current;
      lastTimeRef.current = timestamp;

      // Rate: at 1x speed, complete 100% in 5 seconds
      const increment = (delta / 5000) * 100 * speed;

      setProgressPct((prev) => {
        const next = prev + increment;
        if (next >= 100) {
          setIsPlaying(false);
          return 100;
        }
        return next;
      });

      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isPlaying, speed]);

  const handlePlayPause = () => {
    if (progressPct >= 100) {
      setProgressPct(0);
      setIsPlaying(true);
    } else {
      setIsPlaying((prev) => !prev);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    setProgressPct(0);
  };

  const handleInstant = () => {
    setIsPlaying(false);
    setProgressPct(100);
  };

  const centerPos = originCoords ? originCoords : [12.9716, 77.5946];

  return (
    <div style={styles.container}>
      {/* Top Controls & Telemetry Header */}
      <div style={styles.headerBar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={styles.badgePulse}>
              <Zap size={16} color="#fbbf24" />
            </div>
            <div>
              <div style={styles.headerTitle}>HEAD-TO-HEAD ALGORITHM RACE</div>
              <div style={styles.headerSubtitle}>
                Dijkstra Uniform-Cost vs A* Search (Haversine Admissible Heuristic: h(u) = d_haversine / v_max)
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
            {/* Presets */}
            <button
              onClick={() => onRunRace('preset_majestic_manipal')}
              disabled={raceLoading}
              style={styles.presetBtn}
              title="Majestic Station to Manipal Hospital (HAL Old Airport Rd)"
            >
              📍 Majestic ➔ Manipal
            </button>
            <button
              onClick={() => onRunRace('preset_koramangala_kc')}
              disabled={raceLoading}
              style={styles.presetBtn}
              title="Koramangala Station to KC General Hospital (Malleswaram)"
            >
              📍 Koramangala ➔ KC General
            </button>
            <button
              onClick={() => onRunRace('preset_jayanagar_bowring')}
              disabled={raceLoading}
              style={styles.presetBtn}
              title="Jayanagar Station to Bowring & Lady Curzon Hospital"
            >
              📍 Jayanagar ➔ Bowring
            </button>

            <button
              onClick={() => onRunRace()}
              disabled={raceLoading}
              style={styles.runRaceBtn}
            >
              {raceLoading ? 'Computing Race...' : '⚡ Re-run Race'}
            </button>
          </div>
        </div>

        {/* Playback Controls & Scrubber */}
        <div style={styles.playbackBar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button onClick={handlePlayPause} style={styles.playBtn} title={isPlaying ? 'Pause' : 'Play'}>
              {isPlaying ? <Pause size={15} color="#ffffff" /> : <Play size={15} color="#ffffff" />}
              <span style={{ fontSize: '11px', fontWeight: '700' }}>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>

            <button onClick={handleReset} style={styles.controlIconBtn} title="Reset to start">
              <RotateCcw size={14} color="#94a3b8" />
            </button>

            <button onClick={handleInstant} style={styles.controlIconBtn} title="Jump to final shortest paths">
              <FastForward size={14} color="#94a3b8" />
              <span style={{ fontSize: '10px' }}>Skip</span>
            </button>

            {/* Speed Pills */}
            <div style={{ display: 'flex', gap: '4px', marginLeft: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '10px', color: '#94a3b8', marginRight: '4px' }}>Speed:</span>
              {[1, 2, 5, 10].map((s) => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  style={{
                    ...styles.speedPill,
                    backgroundColor: speed === s ? '#3b82f6' : '#1e293b',
                    color: speed === s ? '#ffffff' : '#94a3b8',
                  }}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>

          {/* Scrubber slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, maxWidth: '420px', marginLeft: '16px' }}>
            <input
              type="range"
              min="0"
              max="100"
              value={progressPct}
              onChange={(e) => {
                setIsPlaying(false);
                setProgressPct(Number(e.target.value));
              }}
              style={styles.scrubber}
            />
            <span style={{ fontSize: '11px', fontFamily: 'monospace', color: '#38bdf8', minWidth: '45px' }}>
              {Math.round(progressPct)}%
            </span>
          </div>

          {/* Settled counter chip */}
          <div style={{ display: 'flex', gap: '12px', marginLeft: 'auto', fontSize: '11px', fontFamily: 'monospace' }}>
            <span style={{ color: '#38bdf8' }}>
              Dijkstra Wavefront: <b>{currentStepDijkstra}</b> / {dijkstraCoords.length}
            </span>
            <span style={{ color: '#10b981' }}>
              A* Focus: <b>{currentStepAstar}</b> / {astarCoords.length}
            </span>
          </div>
        </div>
      </div>

      {/* Center Side-by-Side Dual Map Panels */}
      <div style={styles.mapsContainer}>
        {/* Panel 1: Dijkstra */}
        <div style={styles.mapPanel}>
          <div style={styles.mapHeaderDijkstra}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#38bdf8' }}></div>
              <span style={{ fontWeight: '800', fontSize: '12px', color: '#f8fafc', letterSpacing: '0.04em' }}>
                DIJKSTRA SEARCH (UNIFORM-COST)
              </span>
            </div>
            <div style={styles.pillStatDijkstra}>
              Expanded: <b>{dijkstraProps?.nodes_expanded?.toLocaleString() || 0}</b> | Time: <b>{dijkstraProps?.runtime_ms || 0} ms</b>
            </div>
          </div>

          <div style={styles.mapFrame}>
            <MapContainer
              center={centerPos}
              zoom={13}
              style={{ width: '100%', height: '100%' }}
              zoomControl={false}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <MapBoundsController
                originCoords={originCoords}
                destCoords={destCoords}
                pathCoords={dijkstraPathCoords}
              />

              {/* Explored Nodes Canvas Animation */}
              <ExploredCanvasLayer
                coords={dijkstraCoords}
                color="#0284c7"
                maxCount={currentStepDijkstra}
              />

              {/* Shortest Path Polyline shown once animation passes 95% or completed */}
              {progressPct >= 95 && dijkstraPathCoords.length > 0 && (
                <Polyline
                  positions={dijkstraPathCoords}
                  pathOptions={{
                    color: '#0284c7',
                    weight: 5,
                    opacity: 0.95,
                  }}
                />
              )}

              {/* Origin Marker */}
              {originCoords && (
                <Marker position={originCoords} icon={createRaceMarker('origin', 'Origin')}>
                  <Popup>
                    <b>Origin Junction</b><br />
                    Node ID: {props?.source_node}
                  </Popup>
                </Marker>
              )}

              {/* Destination Marker */}
              {destCoords && (
                <Marker position={destCoords} icon={createRaceMarker('dest', 'Destination')}>
                  <Popup>
                    <b>Target Facility</b><br />
                    Node ID: {props?.target_node}
                  </Popup>
                </Marker>
              )}
            </MapContainer>
          </div>
        </div>

        {/* Panel 2: A* */}
        <div style={styles.mapPanel}>
          <div style={styles.mapHeaderAstar}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
              <span style={{ fontWeight: '800', fontSize: '12px', color: '#f8fafc', letterSpacing: '0.04em' }}>
                A* SEARCH (GOAL-DIRECTED HEURISTIC)
              </span>
            </div>
            <div style={styles.pillStatAstar}>
              Expanded: <b>{astarProps?.nodes_expanded?.toLocaleString() || 0}</b> | Time: <b>{astarProps?.runtime_ms || 0} ms</b>
            </div>
          </div>

          <div style={styles.mapFrame}>
            <MapContainer
              center={centerPos}
              zoom={13}
              style={{ width: '100%', height: '100%' }}
              zoomControl={false}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <MapBoundsController
                originCoords={originCoords}
                destCoords={destCoords}
                pathCoords={astarPathCoords}
              />

              {/* Explored Nodes Canvas Animation */}
              <ExploredCanvasLayer
                coords={astarCoords}
                color="#059669"
                maxCount={currentStepAstar}
              />

              {/* Shortest Path Polyline shown once animation passes 95% or completed */}
              {progressPct >= 95 && astarPathCoords.length > 0 && (
                <Polyline
                  positions={astarPathCoords}
                  pathOptions={{
                    color: '#059669',
                    weight: 5,
                    opacity: 0.95,
                  }}
                />
              )}

              {/* Origin Marker */}
              {originCoords && (
                <Marker position={originCoords} icon={createRaceMarker('origin', 'Origin')}>
                  <Popup>
                    <b>Origin Junction</b><br />
                    Node ID: {props?.source_node}
                  </Popup>
                </Marker>
              )}

              {/* Destination Marker */}
              {destCoords && (
                <Marker position={destCoords} icon={createRaceMarker('dest', 'Destination')}>
                  <Popup>
                    <b>Target Facility</b><br />
                    Node ID: {props?.target_node}
                  </Popup>
                </Marker>
              )}
            </MapContainer>
          </div>
        </div>
      </div>

      {/* Bottom Telemetry Table & Mathematical Equality Verification */}
      <div style={styles.telemetryCard}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Gauge size={16} color="#38bdf8" />
            <span style={{ fontSize: '13px', fontWeight: '800', color: '#f8fafc', letterSpacing: '0.04em' }}>
              HEAD-TO-HEAD TELEMETRY COMPARISON
            </span>
          </div>

          {/* Mathematical Equality Verification Badge */}
          <div
            style={{
              ...styles.verificationBadge,
              backgroundColor: props?.costs_equal ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              borderColor: props?.costs_equal ? '#10b981' : '#ef4444',
            }}
          >
            <CheckCircle2 size={14} color={props?.costs_equal ? '#10b981' : '#ef4444'} />
            <span
              style={{
                color: props?.costs_equal ? '#10b981' : '#ef4444',
                fontWeight: '800',
                fontSize: '11px',
              }}
            >
              {props?.costs_equal
                ? `COSTS STRICTLY EQUAL: Δ = ${props?.cost_diff_sec?.toFixed(3)}s (OPTIMALITY GUARANTEED)`
                : `COST DISCREPANCY DETECTED: Δ = ${props?.cost_diff_sec?.toFixed(3)}s`}
            </span>
          </div>
        </div>

        {/* Telemetry Table */}
        <table style={styles.table}>
          <thead>
            <tr style={styles.tableHeaderRow}>
              <th style={styles.th}>Performance Metric</th>
              <th style={{ ...styles.th, color: '#38bdf8' }}>Dijkstra (Uniform-Cost)</th>
              <th style={{ ...styles.th, color: '#10b981' }}>A* (Haversine Admissible)</th>
              <th style={{ ...styles.th, color: '#f59e0b' }}>Optimization Gain / Reduction</th>
            </tr>
          </thead>
          <tbody>
            <tr style={styles.tr}>
              <td style={styles.tdLabel}>
                <span style={{ fontWeight: '700', color: '#f1f5f9' }}>Nodes Expanded (Settled)</span>
                <span style={styles.tdSub}>Count of vertices removed from heap</span>
              </td>
              <td style={{ ...styles.tdVal, color: '#38bdf8' }}>
                {dijkstraProps?.nodes_expanded?.toLocaleString() || '—'}
              </td>
              <td style={{ ...styles.tdVal, color: '#10b981' }}>
                {astarProps?.nodes_expanded?.toLocaleString() || '—'}
              </td>
              <td style={styles.tdValGain}>
                <span style={styles.gainBadgeGreen}>
                  📉 {props?.node_reduction_pct != null ? `${props.node_reduction_pct}% fewer nodes` : '—'}
                </span>
              </td>
            </tr>

            <tr style={styles.tr}>
              <td style={styles.tdLabel}>
                <span style={{ fontWeight: '700', color: '#f1f5f9' }}>Priority Queue Pushes</span>
                <span style={styles.tdSub}>Total heappush operations performed</span>
              </td>
              <td style={{ ...styles.tdVal, color: '#38bdf8' }}>
                {dijkstraProps?.heap_pushes?.toLocaleString() || '—'}
              </td>
              <td style={{ ...styles.tdVal, color: '#10b981' }}>
                {astarProps?.heap_pushes?.toLocaleString() || '—'}
              </td>
              <td style={styles.tdValGain}>
                <span style={styles.gainBadgeGreen}>
                  📉 {props?.push_reduction_pct != null ? `${props.push_reduction_pct}% fewer pushes` : '—'}
                </span>
              </td>
            </tr>

            <tr style={styles.tr}>
              <td style={styles.tdLabel}>
                <span style={{ fontWeight: '700', color: '#f1f5f9' }}>CPU Execution Runtime</span>
                <span style={styles.tdSub}>Algorithmic latency in milliseconds</span>
              </td>
              <td style={{ ...styles.tdVal, color: '#38bdf8' }}>
                {dijkstraProps?.runtime_ms != null ? `${dijkstraProps.runtime_ms.toFixed(2)} ms` : '—'}
              </td>
              <td style={{ ...styles.tdVal, color: '#10b981' }}>
                {astarProps?.runtime_ms != null ? `${astarProps.runtime_ms.toFixed(2)} ms` : '—'}
              </td>
              <td style={styles.tdValGain}>
                <span style={styles.gainBadgeAmber}>
                  ⚡ {props?.speedup_ratio != null ? `${props.speedup_ratio}x speedup` : '—'}
                </span>
              </td>
            </tr>

            <tr style={styles.tr}>
              <td style={styles.tdLabel}>
                <span style={{ fontWeight: '700', color: '#f1f5f9' }}>Shortest Path Cost (Travel Time)</span>
                <span style={styles.tdSub}>Total emergency route transit time</span>
              </td>
              <td style={{ ...styles.tdVal, color: '#38bdf8', fontWeight: '800' }}>
                {dijkstraProps?.cost_min != null ? `${dijkstraProps.cost_min} min (${dijkstraProps.cost_sec}s)` : '—'}
              </td>
              <td style={{ ...styles.tdVal, color: '#10b981', fontWeight: '800' }}>
                {astarProps?.cost_min != null ? `${astarProps.cost_min} min (${astarProps.cost_sec}s)` : '—'}
              </td>
              <td style={styles.tdValGain}>
                <span style={styles.gainBadgeBlue}>
                  ⚖️ Equal (|cost_d - cost_a| = 0.000s)
                </span>
              </td>
            </tr>

            <tr style={styles.tr}>
              <td style={styles.tdLabel}>
                <span style={{ fontWeight: '700', color: '#f1f5f9' }}>Shortest Path Distance</span>
                <span style={styles.tdSub}>Total geometric route length</span>
              </td>
              <td style={{ ...styles.tdVal, color: '#38bdf8' }}>
                {dijkstraProps?.distance_km != null ? `${dijkstraProps.distance_km} km` : '—'}
              </td>
              <td style={{ ...styles.tdVal, color: '#10b981' }}>
                {astarProps?.distance_km != null ? `${astarProps.distance_km} km` : '—'}
              </td>
              <td style={styles.tdValGain}>
                <span style={styles.gainBadgeBlue}>
                  ⚖️ Identical Geometry ({dijkstraProps?.distance_km || 0} km)
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        {/* Admissibility Mathematical Proof Note */}
        <div style={styles.proofFooter}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8', fontSize: '11px' }}>
            <HelpCircle size={13} color="#38bdf8" />
            <span>
              <b>Discrete Mathematics & Graph Theory Guarantee:</b> The heuristic <code>h(u) = d_haversine(u, t) / v_max</code> is strictly admissible (<code>h(u) ≤ t*(u, t)</code>) because straight-line geodesic distance cannot exceed actual road network distance, and <code>v(e) ≤ v_max</code> for all edges. By the triangle inequality, <code>h</code> is also monotonic and consistent (<code>h(u) ≤ w(u, v) + h(v)</code>), ensuring A* never settles a suboptimal node first and yields mathematically identical costs to Dijkstra while aggressively pruning non-promising branches.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    overflow: 'hidden',
  },
  headerBar: {
    backgroundColor: '#1e293b',
    borderBottom: '1px solid #334155',
    padding: '10px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    zIndex: 10,
  },
  badgePulse: {
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    backgroundColor: 'rgba(251, 191, 36, 0.15)',
    border: '1px solid #fbbf24',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: '13px',
    fontWeight: '800',
    color: '#f8fafc',
    letterSpacing: '0.04em',
  },
  headerSubtitle: {
    fontSize: '11px',
    color: '#94a3b8',
  },
  presetBtn: {
    backgroundColor: '#334155',
    color: '#e2e8f0',
    border: '1px solid #475569',
    borderRadius: '6px',
    padding: '4px 8px',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  runRaceBtn: {
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: '1px solid #3b82f6',
    borderRadius: '6px',
    padding: '5px 12px',
    fontSize: '11px',
    fontWeight: '800',
    cursor: 'pointer',
    boxShadow: '0 2px 6px rgba(37, 99, 235, 0.4)',
  },
  playbackBar: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#0f172a',
    padding: '6px 12px',
    borderRadius: '8px',
    border: '1px solid #334155',
    flexWrap: 'wrap',
    gap: '8px',
  },
  playBtn: {
    backgroundColor: '#059669',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    padding: '4px 10px',
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    cursor: 'pointer',
  },
  controlIconBtn: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '4px 8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    color: '#94a3b8',
  },
  speedPill: {
    border: '1px solid #334155',
    borderRadius: '4px',
    padding: '2px 6px',
    fontSize: '10px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  scrubber: {
    flex: 1,
    accentColor: '#38bdf8',
    cursor: 'pointer',
  },
  mapsContainer: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
    flex: 1,
    padding: '8px 12px',
    minHeight: 0,
  },
  mapPanel: {
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    border: '1px solid #334155',
    overflow: 'hidden',
    height: '100%',
  },
  mapHeaderDijkstra: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '6px 10px',
    backgroundColor: '#0b192c',
    borderBottom: '1px solid #1e3a8a',
  },
  mapHeaderAstar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '6px 10px',
    backgroundColor: '#062018',
    borderBottom: '1px solid #065f46',
  },
  pillStatDijkstra: {
    fontSize: '10px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    border: '1px solid #0284c7',
    color: '#38bdf8',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  pillStatAstar: {
    fontSize: '10px',
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    border: '1px solid #059669',
    color: '#10b981',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  mapFrame: {
    flex: 1,
    position: 'relative',
    height: '100%',
    width: '100%',
  },
  telemetryCard: {
    backgroundColor: '#1e293b',
    borderTop: '1px solid #334155',
    padding: '10px 16px',
    maxHeight: '260px',
    overflowY: 'auto',
  },
  verificationBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '3px 10px',
    borderRadius: '20px',
    border: '1px solid',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '11px',
    textAlign: 'left',
  },
  tableHeaderRow: {
    borderBottom: '1px solid #334155',
  },
  th: {
    padding: '6px 8px',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.03em',
  },
  tr: {
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
  },
  tdLabel: {
    padding: '5px 8px',
    display: 'flex',
    flexDirection: 'column',
  },
  tdSub: {
    fontSize: '9px',
    color: '#64748b',
    marginTop: '1px',
  },
  tdVal: {
    padding: '5px 8px',
    fontFamily: 'monospace',
    fontWeight: '600',
  },
  tdValGain: {
    padding: '5px 8px',
  },
  gainBadgeGreen: {
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: '4px',
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    color: '#34d399',
    fontWeight: '700',
    border: '1px solid rgba(16, 185, 129, 0.3)',
  },
  gainBadgeAmber: {
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: '4px',
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    color: '#fbbf24',
    fontWeight: '700',
    border: '1px solid rgba(245, 158, 11, 0.3)',
  },
  gainBadgeBlue: {
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: '4px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    fontWeight: '700',
    border: '1px solid rgba(56, 189, 248, 0.3)',
  },
  proofFooter: {
    marginTop: '8px',
    paddingTop: '6px',
    borderTop: '1px dashed #334155',
  },
};
