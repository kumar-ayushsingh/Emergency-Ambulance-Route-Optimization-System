import React, { useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';
import {
  ShieldAlert,
  AlertTriangle,
  GitCommit,
  Layers,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  X,
  Eye,
  EyeOff,
  Activity,
} from 'lucide-react';

// Create custom SVG markers using L.divIcon
const createHospitalIcon = (traumaLevel, status = 'normal', rank = null, isWinner = false) => {
  const isLevel1 = traumaLevel === 'Level-1';
  const bgColor = isWinner ? '#059669' : isLevel1 ? '#ef4444' : '#3b82f6';
  const borderColor = isWinner ? '#fbbf24' : '#ffffff';
  const statusColor = status === 'normal' ? '#10b981' : status === 'busy' ? '#f59e0b' : '#ef4444';

  return L.divIcon({
    className: 'custom-hospital-marker',
    html: `
      <div style="
        position: relative;
        background-color: ${bgColor};
        width: 34px;
        height: 34px;
        border-radius: 8px;
        border: 2.5px solid ${borderColor};
        box-shadow: 0 4px 12px rgba(0,0,0,0.6);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 800;
        font-size: 13px;
        cursor: pointer;
      ">
        <span style="line-height: 1;">${isWinner ? '🏆' : 'H'}</span>
        <span style="font-size: 8px; font-weight: 700; opacity: 0.95;">${isLevel1 ? 'L1' : 'L2'}</span>
        
        <!-- Status indicator dot -->
        <span style="
          position: absolute;
          top: -3px;
          right: -3px;
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background-color: ${statusColor};
          border: 1.5px solid #ffffff;
        "></span>

        ${
          rank
            ? `
          <span style="
            position: absolute;
            bottom: -5px;
            left: 50%;
            transform: translateX(-50%);
            background-color: ${isWinner ? '#fbbf24' : '#1e293b'};
            color: ${isWinner ? '#0f172a' : '#f8fafc'};
            font-size: 8px;
            font-weight: 900;
            padding: 0 3px;
            border-radius: 3px;
            border: 1px solid #334155;
            white-space: nowrap;
          ">#${rank}</span>
        `
            : ''
        }
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  });
};

const createStationIcon = () => {
  return L.divIcon({
    className: 'custom-station-marker',
    html: `
      <div style="
        background-color: #f59e0b;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 2px solid #ffffff;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #0f172a;
        font-weight: 800;
        font-size: 14px;
        cursor: pointer;
      ">
        🚑
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
};

const createAccidentIcon = () => {
  return L.divIcon({
    className: 'custom-accident-marker',
    html: `
      <div style="
        position: relative;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      ">
        <div style="
          position: absolute;
          width: 36px;
          height: 36px;
          background: rgba(239, 68, 68, 0.4);
          border-radius: 50%;
          animation: pulse 1.5s infinite;
        "></div>
        <div style="
          background-color: #ef4444;
          width: 26px;
          height: 26px;
          border-radius: 50%;
          border: 2px solid #ffffff;
          box-shadow: 0 0 15px rgba(239, 68, 68, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
        ">
          ⚠️
        </div>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20],
  });
};

const createBlockedRoadIcon = () => {
  return L.divIcon({
    className: 'custom-blocked-road-marker',
    html: `
      <div style="
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background-color: #dc2626;
        border: 2px solid #ffffff;
        box-shadow: 0 2px 8px rgba(220, 38, 38, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-weight: 900;
        font-size: 14px;
        cursor: pointer;
      ">
        ✕
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
};

const createArticulationPointIcon = () => {
  return L.divIcon({
    className: 'custom-ap-marker',
    html: `
      <div style="
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background-color: #f59e0b;
        border: 2px solid #ffffff;
        box-shadow: 0 0 8px rgba(245, 158, 11, 0.9);
        cursor: pointer;
      "></div>
    `,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -8],
  });
};

const createSuggestedStationIcon = (index) => {
  return L.divIcon({
    className: 'custom-suggested-station-marker',
    html: `
      <div style="
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
        border: 2px solid #ffffff;
        box-shadow: 0 4px 12px rgba(168, 85, 247, 0.7);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-weight: 900;
        font-size: 11px;
        cursor: pointer;
      ">
        <span style="font-size: 10px; line-height: 1;">⚡</span>
        <span style="font-size: 8px; font-weight: 800;">#${index}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
};

const createNumberedAccidentIcon = (index, color = '#ef4444') => {
  return L.divIcon({
    className: 'custom-numbered-accident-marker',
    html: `
      <div style="
        position: relative;
        width: 34px;
        height: 34px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      ">
        <div style="
          position: absolute;
          width: 34px;
          height: 34px;
          background: ${color}44;
          border-radius: 50%;
          animation: pulse 1.5s infinite;
        "></div>
        <div style="
          background-color: ${color};
          width: 26px;
          height: 26px;
          border-radius: 50%;
          border: 2px solid #ffffff;
          box-shadow: 0 0 12px ${color}aa;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          font-weight: 900;
          color: white;
          font-family: JetBrains Mono, monospace;
        ">
          ${index}
        </div>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  });
};

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: (e) => {
      if (onMapClick) {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

export default function MapView({
  hospitals,
  stations,
  accidentLocation,
  routeData,
  criticalData,
  backupData,
  blockedRoads = [],
  blockedFeatures = [],
  // Prompt 7 Props: Hospital Scoring & Route Divergence
  scoredHospitalsData = null,
  hospitalStatuses = {},
  trafficComparisonData = null,
  trafficComparisonActive = false,
  // Prompt 5 Props:
  coverageData = null,
  suggestedStations = [],
  showCoverageHeatmap = true,
  onToggleCoverageHeatmap,
  // Prompt 6 Props: Multi-Accident Assignment
  assignmentData = null,
  multiAccidents = [],
  assignmentMode = false,
  onRemoveAccident,
  onMapClick,
  onBlockRoad,
  onUnblockRoad,
  onRestoreRoads,
  // Loading & Error Props
  loadingMessage = null,
  error = null,
  onClearError = null,
}) {
  const center = [12.965, 77.600];

  // Layer Visibility Toggles
  const [showPrimaryRoute, setShowPrimaryRoute] = useState(true);
  const [showPlanB, setShowPlanB] = useState(true);
  const [showPlanC, setShowPlanC] = useState(true);
  const [showStrictBridges, setShowStrictBridges] = useState(true);
  const [showSoftBridges, setShowSoftBridges] = useState(true);
  const [showAPs, setShowAPs] = useState(true);
  const [showHospitals, setShowHospitals] = useState(true);
  const [showStations, setShowStations] = useState(true);
  const [isLegendExpanded, setIsLegendExpanded] = useState(true);

  // Extract route lines from GeoJSON features
  const dispatchFeature = routeData?.features?.find(
    (f) => f.geometry.type === 'LineString' && f.properties.leg === 'dispatch'
  );
  const transportFeature = routeData?.features?.find(
    (f) => f.geometry.type === 'LineString' && f.properties.leg === 'transport'
  );

  const dispatchPositions =
    dispatchFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];

  const transportPositions =
    transportFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];

  // Extract Prompt 7 Scoring Routes (Winner and Nearest)
  const winnerRouteFeature = scoredHospitalsData?.features?.find(
    (f) => f.geometry.type === 'LineString' && f.properties.role === 'winner_route'
  );
  const nearestRouteFeature = scoredHospitalsData?.features?.find(
    (f) => f.geometry.type === 'LineString' && f.properties.role === 'nearest_route'
  );

  const winnerPositions =
    winnerRouteFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];
  const nearestPositions =
    nearestRouteFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];

  // Extract Traffic Comparison Routes (Off-Peak vs Peak Divergence)
  const offPeakRouteFeature = trafficComparisonData?.features?.find(
    (f) => f.geometry.type === 'LineString' && f.properties.role === 'off_peak_route'
  );
  const peakRouteFeature = trafficComparisonData?.features?.find(
    (f) => f.geometry.type === 'LineString' && f.properties.role === 'peak_route'
  );

  const offPeakPositions =
    offPeakRouteFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];
  const peakPositions =
    peakRouteFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];

  // Extract critical features from criticalData GeoJSON
  const strictBridges =
    criticalData?.features?.filter((f) => f.properties.type === 'strict_bridge') || [];

  const softBridges =
    criticalData?.features?.filter((f) => f.properties.type === 'soft_bridge') || [];

  const articulationPoints =
    criticalData?.features?.filter((f) => f.properties.type === 'articulation_point') || [];

  // Extract Backup Routes (Plan B, Plan C)
  const backupPlans = backupData?.features || [];
  const planBFeature = backupPlans.find((f) => f.properties?.plan_name?.includes('Plan B'));
  const planCFeature = backupPlans.find((f) => f.properties?.plan_name?.includes('Plan C'));

  const planBPositions = planBFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];
  const planCPositions = planCFeature?.geometry.coordinates.map(([lng, lat]) => [lat, lng]) || [];

  // Extract Blocked Features
  const blockedLineFeatures =
    blockedFeatures.filter((f) => f.properties?.type === 'blocked_edge');
  const blockedMarkerFeatures =
    blockedFeatures.filter((f) => f.properties?.type === 'blocked_marker');

  // Extract Coverage Features (Prompt 5)
  const coveragePoints =
    coverageData?.features?.filter((f) => f.properties?.type === 'coverage_point') || [];

  const suggestedStationFeatures =
    coverageData?.features?.filter((f) => f.properties?.type === 'suggested_station') || [];

  // Extract Multi-Accident Assignment Features (Prompt 6)
  const assignmentRoutes =
    assignmentData?.features?.filter((f) => f.properties?.type === 'assigned_route') || [];

  const assignedAccidents =
    assignmentData?.features?.filter((f) => f.properties?.type === 'assigned_accident') || [];

  // Map of scored hospitals for badge lookup
  const scoredMap = {};
  if (scoredHospitalsData?.properties?.ranked_hospitals) {
    scoredHospitalsData.properties.ranked_hospitals.forEach((h) => {
      scoredMap[h.id] = h;
    });
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <MapContainer
        center={center}
        zoom={13}
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapClickHandler onMapClick={onMapClick} />

        {/* Prompt 5: Isochrone Coverage Heat Map Layer */}
        {showCoverageHeatmap &&
          coveragePoints.map((pt, idx) => {
            const [lng, lat] = pt.geometry.coordinates;
            const p = pt.properties;
            return (
              <CircleMarker
                key={`cov-${p.node_id || idx}`}
                center={[lat, lng]}
                radius={6}
                pathOptions={{
                  fillColor: p.color,
                  fillOpacity: 0.8,
                  color: '#0f172a',
                  weight: 0.8,
                }}
              >
                <Popup>
                  <div style={{ color: '#f8fafc', fontSize: '12px' }}>
                    <div style={{ fontWeight: '800', color: p.color, fontSize: '13px', marginBottom: '4px' }}>
                      {p.band_label}
                    </div>
                    <div>
                      Nearest Station Time: <strong style={{ color: '#f8fafc' }}>{p.time_min} min</strong> ({p.time_sec}s)
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '3px' }}>
                      Demand Grid Node ID: {p.node_id}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

        {/* Prompt 5: Suggested Optimal Station Locations */}
        {suggestedStationFeatures.map((stn, idx) => {
          const [lng, lat] = stn.geometry.coordinates;
          const p = stn.properties;
          return (
            <Marker
              key={`sugg-${p.node_id || idx}`}
              position={[lat, lng]}
              icon={createSuggestedStationIcon(idx + 1)}
            >
              <Popup>
                <div style={{ color: '#f8fafc', fontSize: '12px' }}>
                  <div style={{ fontWeight: '800', color: '#c084fc', fontSize: '13px', marginBottom: '4px' }}>
                    ⚡ {p.name || `Proposed Station #${idx + 1}`}
                  </div>
                  <div>Node ID: <strong style={{ color: '#f8fafc' }}>{p.node_id}</strong></div>
                  <div>Algorithm: <span style={{ color: '#a855f7', fontWeight: '700' }}>{p.algorithm}</span></div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                    Coordinates: {lat.toFixed(4)}, {lng.toFixed(4)}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Hospital Markers */}
        {showHospitals &&
          hospitals.map((h) => {
            const coords = [h.geometry.coordinates[1], h.geometry.coordinates[0]];
            const props = h.properties;
            const currentStatus = hospitalStatuses[props.id] || props.status || 'normal';
            const scoredInfo = scoredMap[props.id];
            const isWinner = scoredInfo?.is_winner || false;
            const rank = scoredInfo?.rank;

            return (
              <Marker
                key={props.id}
                position={coords}
                icon={createHospitalIcon(props.trauma_level, currentStatus, rank, isWinner)}
              >
              <Popup>
                <div style={{ color: '#f8fafc' }}>
                  <div style={{ fontWeight: '700', fontSize: '14px', marginBottom: '4px' }}>
                    {props.name} {isWinner && '🏆'}
                  </div>
                  <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: '700',
                        backgroundColor: props.trauma_level === 'Level-1' ? '#ef4444' : '#3b82f6',
                        color: 'white',
                      }}
                    >
                      {props.trauma_level} Trauma
                    </span>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: '700',
                        backgroundColor:
                          currentStatus === 'normal'
                            ? '#10b981'
                            : currentStatus === 'busy'
                            ? '#f59e0b'
                            : '#ef4444',
                        color: 'white',
                      }}
                    >
                      Status: {currentStatus.toUpperCase()}
                    </span>
                  </div>

                  {scoredInfo && (
                    <div
                      style={{
                        backgroundColor: 'rgba(16, 185, 129, 0.15)',
                        border: '1px solid #10b981',
                        borderRadius: '4px',
                        padding: '6px 8px',
                        marginBottom: '6px',
                        fontSize: '11px',
                      }}
                    >
                      <div>
                        Triage Score: <strong>{scoredInfo.score_min} min</strong> (Rank #{scoredInfo.rank})
                      </div>
                      <div style={{ color: '#cbd5e1' }}>
                        Road Time: {scoredInfo.travel_time_min}m | P_tr: +{scoredInfo.p_trauma_min}m | P_ld: +{scoredInfo.p_load_min}m
                      </div>
                    </div>
                  )}

                  <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                    <div><strong>Available Beds:</strong> {props.beds_available}</div>
                    <div><strong>ICU Capacity:</strong> {props.total_icu_beds} beds</div>
                    <div><strong>Specialties:</strong> {props.specialties?.join(', ')}</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                      {props.address}
                    </div>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Ambulance Station Markers */}
        {showStations &&
          stations.map((s) => {
            const coords = [s.geometry.coordinates[1], s.geometry.coordinates[0]];
            const props = s.properties;
            return (
              <Marker key={props.id} position={coords} icon={createStationIcon()}>
              <Popup>
                <div style={{ color: '#f8fafc' }}>
                  <div style={{ fontWeight: '700', fontSize: '14px', marginBottom: '4px' }}>
                    {props.name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                    <div><strong>Available Ambulances:</strong> {props.ambulances_available} units</div>
                    <div><strong>ALS / BLS Units:</strong> {props.als_ambulances} ALS / {props.bls_ambulances} BLS</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                      {props.address}
                    </div>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Single Accident Marker */}
        {accidentLocation && !assignmentMode && (
          <Marker
            position={[accidentLocation.lat, accidentLocation.lng]}
            icon={createAccidentIcon()}
          >
            <Popup>
              <div style={{ color: '#f8fafc' }}>
                <strong style={{ color: '#ef4444' }}>⚠️ Incident Location</strong>
                <div style={{ fontSize: '12px', marginTop: '4px' }}>
                  Lat: {accidentLocation.lat.toFixed(5)}, Lng: {accidentLocation.lng.toFixed(5)}
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Multi-Accident Markers */}
        {assignmentMode &&
          multiAccidents.map((acc, idx) => {
            const assignedProps = assignedAccidents.find(
              (f) => f.properties.accident_index === acc.index
            )?.properties;
            const palette = ['#10b981', '#f59e0b', '#3b82f6', '#ec4899', '#8b5cf6'];
            const markerColor = assignedProps?.color || palette[idx % palette.length];
            return (
              <Marker
                key={`multi-acc-${acc.id || idx}`}
                position={[acc.lat, acc.lng]}
                icon={createNumberedAccidentIcon(acc.index, markerColor)}
              >
                <Popup>
                  <div style={{ color: '#f8fafc', fontSize: '12px' }}>
                    <div style={{ fontWeight: '800', color: markerColor, fontSize: '14px', marginBottom: '4px' }}>
                      🚨 Incident Site #{acc.index}
                    </div>
                    {assignedProps ? (
                      <div>
                        <div>Assigned: <strong style={{ color: markerColor }}>{assignedProps.assigned_ambulance}</strong></div>
                        <div>Response Time: <strong style={{ color: '#f8fafc' }}>{assignedProps.travel_time_min} min</strong> ({assignedProps.travel_time_sec}s)</div>
                      </div>
                    ) : (
                      <div style={{ color: '#94a3b8' }}>Awaiting fleet assignment optimization...</div>
                    )}
                    {onRemoveAccident && (
                      <button
                        onClick={() => onRemoveAccident(acc.id || acc.index)}
                        style={{
                          marginTop: '8px',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          backgroundColor: '#dc2626',
                          border: 'none',
                          color: 'white',
                          fontWeight: '700',
                          fontSize: '10px',
                          cursor: 'pointer',
                          width: '100%',
                        }}
                      >
                        Remove This Accident
                      </button>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}

        {/* Prompt 6: Multi-Ambulance Assignment Routes */}
        {assignmentRoutes.map((rf, idx) => {
          const coords = rf.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
          const p = rf.properties;
          return (
            <Polyline
              key={`assign-route-${idx}`}
              positions={coords}
              pathOptions={{
                color: p.color,
                weight: 6,
                opacity: 0.95,
              }}
            >
              <Popup>
                <div style={{ color: '#f8fafc', fontSize: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: p.color }} />
                    <strong style={{ color: p.color, fontSize: '13px' }}>
                      {p.ambulance_name}
                    </strong>
                  </div>
                  <div>Base: <strong>{p.station_name}</strong></div>
                  <div>Assigned Incident: <strong>Accident #{p.accident_index}</strong></div>
                  <div style={{ marginTop: '4px', borderTop: '1px solid #334155', paddingTop: '4px' }}>
                    <div>Travel Time: <strong style={{ color: '#f8fafc' }}>{p.travel_time_min} min</strong> ({p.travel_time_sec}s)</div>
                    <div>Distance: {p.distance_km} km</div>
                  </div>
                  {p.is_bottleneck && (
                    <div style={{ marginTop: '4px', color: '#f59e0b', fontWeight: '800', fontSize: '11px' }}>
                      ⚠️ Worst-Case Bottleneck Route
                    </div>
                  )}
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {/* Prompt 7: Winner Hospital Route (LineString, Emerald Green) */}
        {winnerPositions.length > 0 && !trafficComparisonActive && (
          <Polyline
            positions={winnerPositions}
            pathOptions={{
              color: '#10b981',
              weight: 6,
              opacity: 0.95,
            }}
          >
            <Popup>
              <div style={{ color: '#f8fafc' }}>
                <div style={{ color: '#10b981', fontWeight: '800', fontSize: '13px' }}>
                  🏆 WINNER HOSPITAL ROUTE
                </div>
                <div>{winnerRouteFeature?.properties?.short_name}</div>
                <div>Triage Score: <strong>{winnerRouteFeature?.properties?.score_min} min</strong></div>
                <div>Travel Time: {winnerRouteFeature?.properties?.travel_time_min} min ({winnerRouteFeature?.properties?.distance_km} km)</div>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Prompt 7: Nearest Hospital Route (LineString, Amber Dashed, if Winner != Nearest) */}
        {nearestPositions.length > 0 && !trafficComparisonActive && (
          <Polyline
            positions={nearestPositions}
            pathOptions={{
              color: '#f59e0b',
              weight: 4,
              opacity: 0.85,
              dashArray: '6, 8',
            }}
          >
            <Popup>
              <div style={{ color: '#f8fafc' }}>
                <div style={{ color: '#f59e0b', fontWeight: '800', fontSize: '13px' }}>
                  📍 NEAREST HOSPITAL ROUTE
                </div>
                <div>{nearestRouteFeature?.properties?.short_name}</div>
                <div>Road Travel Time: {nearestRouteFeature?.properties?.travel_time_min} min ({nearestRouteFeature?.properties?.distance_km} km)</div>
                <div>Triage Score: <strong>{nearestRouteFeature?.properties?.score_min} min</strong></div>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Traffic Comparison: Off-Peak Route (Cyan / Sky Blue) */}
        {trafficComparisonActive && offPeakPositions.length > 0 && (
          <Polyline
            positions={offPeakPositions}
            pathOptions={{
              color: '#0284c7',
              weight: 6,
              opacity: 0.95,
            }}
          >
            <Popup>
              <div style={{ color: '#f8fafc' }}>
                <div style={{ color: '#38bdf8', fontWeight: '800', fontSize: '13px' }}>
                  ☀️ OFF-PEAK OPTIMAL ROUTE (DIRECT ARTERIAL)
                </div>
                <div>Travel Time (Off-Peak): <strong>{offPeakRouteFeature?.properties?.travel_time_min} min</strong></div>
                <div>Time if driven at Peak: <span style={{ color: '#ef4444', fontWeight: '700' }}>{offPeakRouteFeature?.properties?.time_if_driven_at_peak_min} min</span></div>
                <div>Distance: {offPeakRouteFeature?.properties?.distance_km} km</div>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Traffic Comparison: Peak Route (Vibrant Orange Detour) */}
        {trafficComparisonActive && peakPositions.length > 0 && (
          <Polyline
            positions={peakPositions}
            pathOptions={{
              color: '#f97316',
              weight: 6,
              opacity: 0.95,
            }}
          >
            <Popup>
              <div style={{ color: '#f8fafc' }}>
                <div style={{ color: '#fb923c', fontWeight: '800', fontSize: '13px' }}>
                  🚦 EVENING PEAK ROUTE (CONGESTION BYPASS)
                </div>
                <div>Travel Time (Peak Detour): <strong>{peakRouteFeature?.properties?.travel_time_min} min</strong></div>
                <div>Distance: {peakRouteFeature?.properties?.distance_km} km</div>
                <div style={{ color: '#34d399', fontWeight: '700', marginTop: '4px' }}>
                  Bypasses congested arterial corridor, saving time!
                </div>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Standard Route Leg 1: Station to Accident (Dispatch) */}
        {showPrimaryRoute && !winnerPositions.length && !trafficComparisonActive && dispatchPositions.length > 0 && (
          <Polyline
            positions={dispatchPositions}
            pathOptions={{
              color: '#f59e0b',
              weight: 5,
              opacity: 0.8,
              dashArray: '8, 8',
            }}
          >
            <Popup>
              <div style={{ color: '#f8fafc' }}>
                <strong>Leg 1: Ambulance Dispatch</strong>
                <div>Time: {dispatchFeature?.properties.time_min} mins</div>
                <div>Distance: {dispatchFeature?.properties.distance_km} km</div>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Standard Route Leg 2: Accident to Hospital (Transport) */}
        {showPrimaryRoute && !winnerPositions.length && !trafficComparisonActive && transportPositions.length > 0 && (
          <Polyline
            positions={transportPositions}
            pathOptions={{
              color: '#38bdf8',
              weight: 5,
              opacity: 0.85,
            }}
          >
            <Popup>
              <div style={{ color: '#f8fafc' }}>
                <strong>Leg 2: Hospital Transport</strong>
                <div>Time: {transportFeature?.properties.time_min} mins</div>
                <div>Distance: {transportFeature?.properties.distance_km} km</div>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Plan B Backup Route (VIOLET) */}
        {showPlanB && planBPositions.length > 0 && !trafficComparisonActive && (
          <Polyline
            positions={planBPositions}
            pathOptions={{
              color: '#a855f7',
              weight: 5,
              opacity: 0.9,
              dashArray: '8, 8',
            }}
          />
        )}

        {/* Plan C Backup Route (TEAL) */}
        {showPlanC && planCPositions.length > 0 && !trafficComparisonActive && (
          <Polyline
            positions={planCPositions}
            pathOptions={{
              color: '#06b6d4',
              weight: 5,
              opacity: 0.9,
              dashArray: '4, 6',
            }}
          />
        )}

        {/* Blocked Road Polylines */}
        {blockedLineFeatures.map((bf, idx) => {
          const coords = bf.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
          return (
            <Polyline
              key={`blocked-line-${idx}`}
              positions={coords}
              pathOptions={{
                color: '#7f1d1d',
                weight: 10,
                opacity: 0.95,
                dashArray: '6, 6',
              }}
            />
          );
        })}

        {/* Blocked Road Cross Markers */}
        {blockedMarkerFeatures.map((bm, idx) => {
          const [lng, lat] = bm.geometry.coordinates;
          const { u, v, road_name } = bm.properties;
          return (
            <Marker
              key={`blocked-marker-${idx}`}
              position={[lat, lng]}
              icon={createBlockedRoadIcon()}
            >
              <Popup>
                <div style={{ color: '#f8fafc' }}>
                  <div style={{ color: '#ef4444', fontWeight: '800', fontSize: '13px' }}>
                    ⛔ ROAD CLOSED (BLOCKED)
                  </div>
                  <div style={{ fontWeight: '600', marginTop: '2px' }}>{road_name}</div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                    Segment: {u} → {v}
                  </div>
                  <button
                    onClick={() => onUnblockRoad && onUnblockRoad(u, v)}
                    style={{
                      marginTop: '8px',
                      padding: '5px 12px',
                      borderRadius: '4px',
                      backgroundColor: '#10b981',
                      border: 'none',
                      color: 'white',
                      fontWeight: '700',
                      fontSize: '11px',
                      cursor: 'pointer',
                      width: '100%',
                    }}
                  >
                    🔓 Re-open Road (Unblock)
                  </button>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Strict Bridges on Route (RED) */}
        {showStrictBridges &&
          strictBridges.map((b, idx) => {
            const coords = b.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
            return (
              <Polyline
                key={`strict-bridge-${idx}`}
                positions={coords}
                pathOptions={{
                  color: '#dc2626',
                  weight: 9,
                  opacity: 1.0,
                }}
              />
            );
          })}

        {/* Soft Bridges on Route (ORANGE) */}
        {showSoftBridges &&
          softBridges.map((sb, idx) => {
            const coords = sb.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
            return (
              <Polyline
                key={`soft-bridge-${idx}`}
                positions={coords}
                pathOptions={{
                  color: '#f97316',
                  weight: 8,
                  opacity: 0.95,
                }}
              />
            );
          })}

        {/* Articulation Points (Amber Dots) */}
        {showAPs &&
          articulationPoints.map((ap, idx) => {
            const [lng, lat] = ap.geometry.coordinates;
            return (
              <Marker
                key={`ap-${idx}`}
                position={[lat, lng]}
                icon={createArticulationPointIcon()}
              />
            );
          })}
      </MapContainer>

      {/* Floating Instructions Banner */}
      {!accidentLocation && !assignmentMode && (
        <div style={styles.floatingBanner}>
          <span style={{ marginRight: '8px' }}>📍</span>
          Click on the Bengaluru street map to place an emergency incident and calculate routes.
        </div>
      )}

      {/* Traffic Comparison Floating HUD */}
      {trafficComparisonActive && trafficComparisonData && (
        <div style={styles.trafficHUD}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '16px' }}>⚡</span>
            <strong style={{ color: '#fed7aa', fontSize: '12px' }}>
              PEAK VS OFF-PEAK ROUTE DIVERGENCE DEMO
            </strong>
          </div>
          <div style={{ display: 'flex', gap: '12px', fontSize: '11px', marginTop: '4px' }}>
            <div>
              <span style={{ color: '#38bdf8', fontWeight: '700' }}>● Off-Peak Arterial:</span>{' '}
              {trafficComparisonData.properties?.off_peak?.travel_time_min}m (at peak: {trafficComparisonData.properties?.off_peak?.time_if_driven_at_peak_min}m)
            </div>
            <div>
              <span style={{ color: '#fb923c', fontWeight: '700' }}>● Peak Bypass:</span>{' '}
              {trafficComparisonData.properties?.peak?.travel_time_min}m (
              <span style={{ color: '#34d399', fontWeight: '800' }}>
                -{trafficComparisonData.properties?.peak_bypass_savings_min}m saved
              </span>
              )
            </div>
          </div>
        </div>
      )}

      {/* Floating Loading HUD */}
      {loadingMessage && (
        <div style={styles.floatingLoadingHud}>
          <RefreshCw size={15} color="#38bdf8" className="animate-spin" />
          <span style={{ fontSize: '12px', fontWeight: '700', color: '#f8fafc' }}>
            {loadingMessage}
          </span>
        </div>
      )}

      {/* Floating Error Alert Banner for Unreachable Routes / Disconnection */}
      {error && (
        <div style={styles.floatingErrorBanner}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} color="#ef4444" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '12px', fontWeight: '800', color: '#fca5a5', letterSpacing: '0.02em' }}>
                ROUTE UNREACHABLE / NETWORK DISCONNECTION
              </div>
              <div style={{ fontSize: '11px', color: '#fed7aa', marginTop: '2px' }}>
                {error}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            {onRestoreRoads && (
              <button onClick={onRestoreRoads} style={styles.errorBannerActionBtn}>
                Restore Blocked Roads
              </button>
            )}
            {onClearError && (
              <button onClick={onClearError} style={styles.errorBannerDismissBtn} title="Dismiss warning">
                ✕
              </button>
            )}
          </div>
        </div>
      )}

      {/* Collapsible Map Legend & Layer Visibility Toggles */}
      <div style={styles.legend}>
        <div
          onClick={() => setIsLegendExpanded(!isLegendExpanded)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            paddingBottom: isLegendExpanded ? '8px' : '0',
            borderBottom: isLegendExpanded ? '1px solid #334155' : 'none',
            userSelect: 'none',
          }}
          title={isLegendExpanded ? 'Collapse Layers & Legend' : 'Expand Layers & Legend'}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Layers size={14} color="#38bdf8" />
            <span style={{ fontSize: '11px', fontWeight: '800', color: '#f8fafc', letterSpacing: '0.04em' }}>
              LAYERS & LEGEND
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={styles.layerActiveCountPill}>
              {[showPrimaryRoute, showStrictBridges, showSoftBridges, showAPs, showPlanB, showPlanC, showHospitals, showStations].filter(Boolean).length} Active
            </span>
            {isLegendExpanded ? <ChevronDown size={14} color="#94a3b8" /> : <ChevronUp size={14} color="#94a3b8" />}
          </div>
        </div>

        {isLegendExpanded && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
            {/* Section 1: Layer Visibility Toggles */}
            <div>
              <div style={{ fontSize: '10px', fontWeight: '700', color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>
                Layer Toggles:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={showPrimaryRoute}
                    onChange={(e) => setShowPrimaryRoute(e.target.checked)}
                    style={{ accentColor: '#0284c7' }}
                  />
                  <span>Primary Route</span>
                </label>

                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={showStrictBridges}
                    onChange={(e) => setShowStrictBridges(e.target.checked)}
                    style={{ accentColor: '#dc2626' }}
                  />
                  <span>Strict Bridges</span>
                </label>

                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={showSoftBridges}
                    onChange={(e) => setShowSoftBridges(e.target.checked)}
                    style={{ accentColor: '#f97316' }}
                  />
                  <span>Soft Bridges</span>
                </label>

                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={showAPs}
                    onChange={(e) => setShowAPs(e.target.checked)}
                    style={{ accentColor: '#fbbf24' }}
                  />
                  <span>Articulation Pts</span>
                </label>

                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={showPlanB && showPlanC}
                    onChange={(e) => {
                      setShowPlanB(e.target.checked);
                      setShowPlanC(e.target.checked);
                    }}
                    style={{ accentColor: '#a855f7' }}
                  />
                  <span>Backup Plans</span>
                </label>

                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={showHospitals}
                    onChange={(e) => setShowHospitals(e.target.checked)}
                    style={{ accentColor: '#ef4444' }}
                  />
                  <span>Hospitals</span>
                </label>

                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={showStations}
                    onChange={(e) => setShowStations(e.target.checked)}
                    style={{ accentColor: '#f59e0b' }}
                  />
                  <span>Stations</span>
                </label>

                {onToggleCoverageHeatmap && (
                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={showCoverageHeatmap}
                      onChange={(e) => onToggleCoverageHeatmap(e.target.checked)}
                      style={{ accentColor: '#10b981' }}
                    />
                    <span>Coverage Bands</span>
                  </label>
                )}
              </div>
            </div>

            {/* Section 2: Visual Legend Guide */}
            <div style={{ borderTop: '1px solid #334155', paddingTop: '8px' }}>
              <div style={{ fontSize: '10px', fontWeight: '700', color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>
                Legend Key:
              </div>

              {trafficComparisonActive ? (
                <>
                  <div style={styles.legendItem}>
                    <div style={{ width: '16px', height: '4px', backgroundColor: '#0284c7', borderRadius: '2px' }} />
                    <span style={{ color: '#38bdf8', fontWeight: '700' }}>Off-Peak Route (Arterial)</span>
                  </div>
                  <div style={styles.legendItem}>
                    <div style={{ width: '16px', height: '4px', backgroundColor: '#f97316', borderRadius: '2px' }} />
                    <span style={{ color: '#fb923c', fontWeight: '700' }}>Peak Bypass Detour</span>
                  </div>
                </>
              ) : scoredHospitalsData ? (
                <>
                  <div style={styles.legendItem}>
                    <div style={{ width: '16px', height: '4px', backgroundColor: '#10b981', borderRadius: '2px' }} />
                    <span style={{ color: '#34d399', fontWeight: '700' }}>Winner Hospital Route</span>
                  </div>
                  {nearestPositions.length > 0 && (
                    <div style={styles.legendItem}>
                      <div style={{ width: '16px', height: '4px', backgroundColor: '#f59e0b', borderRadius: '2px', border: '1px dashed white' }} />
                      <span style={{ color: '#f59e0b', fontWeight: '700' }}>Nearest Facility (Sub-optimal)</span>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div style={styles.legendItem}>
                    <div style={{ width: '16px', height: '4px', backgroundColor: '#f59e0b', borderRadius: '2px', border: '1px dashed white' }} />
                    <span>Leg 1: Station Dispatch</span>
                  </div>
                  <div style={styles.legendItem}>
                    <div style={{ width: '16px', height: '4px', backgroundColor: '#38bdf8', borderRadius: '2px' }} />
                    <span>Leg 2: Hospital Transport</span>
                  </div>
                </>
              )}

              <div style={styles.legendItem}>
                <div style={{ width: '16px', height: '5px', backgroundColor: '#dc2626', borderRadius: '2px' }} />
                <span>Strict Bridge (Cut Edge)</span>
              </div>
              <div style={styles.legendItem}>
                <div style={{ width: '16px', height: '5px', backgroundColor: '#f97316', borderRadius: '2px' }} />
                <span>Soft Bridge (Detour ρ ≥ 1.5)</span>
              </div>
              <div style={styles.legendItem}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#fbbf24', border: '1px solid #d97706' }} />
                <span>Articulation Point (Cut Vertex)</span>
              </div>
              <div style={styles.legendItem}>
                <div style={{ width: '16px', height: '4px', backgroundColor: '#a855f7', borderRadius: '2px', border: '1px dashed #c084fc' }} />
                <span>Plan B & Plan C (Yen's K-Shortest)</span>
              </div>

              {blockedLineFeatures.length > 0 && (
                <div style={styles.legendItem}>
                  <div style={{ ...styles.legendBadge, backgroundColor: '#7f1d1d', border: '1px solid #ef4444' }}>❌</div>
                  <span style={{ color: '#fca5a5', fontWeight: '700' }}>
                    Closed Road ({blockedLineFeatures.length} Blocked)
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  floatingBanner: {
    position: 'absolute',
    top: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 999,
    backgroundColor: 'rgba(15, 23, 42, 0.92)',
    border: '1px solid #3b82f6',
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.6)',
    borderRadius: '10px',
    padding: '10px 20px',
    color: '#e2e8f0',
    fontSize: '13px',
    fontWeight: '500',
    display: 'flex',
    alignItems: 'center',
    backdropFilter: 'blur(8px)',
  },
  trafficHUD: {
    position: 'absolute',
    top: '16px',
    right: '20px',
    zIndex: 999,
    backgroundColor: 'rgba(15, 23, 42, 0.94)',
    border: '1.5px solid #f97316',
    boxShadow: '0 8px 24px rgba(249, 115, 22, 0.25)',
    borderRadius: '8px',
    padding: '8px 14px',
    color: '#f8fafc',
    backdropFilter: 'blur(8px)',
  },
  legend: {
    position: 'absolute',
    bottom: '24px',
    left: '24px',
    zIndex: 999,
    backgroundColor: 'rgba(15, 23, 42, 0.94)',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '12px 16px',
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.6)',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    fontSize: '12px',
    color: '#cbd5e1',
    backdropFilter: 'blur(8px)',
    maxWidth: '280px',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    userSelect: 'none',
    fontSize: '11px',
    color: '#e2e8f0',
  },
  legendBadge: {
    width: '20px',
    height: '20px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '10px',
    fontWeight: '800',
  },
};
