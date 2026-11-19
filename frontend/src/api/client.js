/**
 * API Client for Emergency Ambulance Route Optimization System.
 * Relative '/api' paths ensure seamless operation in single-service containerized deployments.
 */

const API_BASE = '/api';

export async function fetchGraphInfo() {
  const res = await fetch(`${API_BASE}/graph/info`);
  if (!res.ok) throw new Error('Failed to fetch graph info');
  return res.json();
}

export async function fetchHospitals() {
  const res = await fetch(`${API_BASE}/hospitals`);
  if (!res.ok) throw new Error('Failed to fetch hospitals');
  return res.json();
}

export async function fetchStations() {
  const res = await fetch(`${API_BASE}/stations`);
  if (!res.ok) throw new Error('Failed to fetch ambulance stations');
  return res.json();
}

export async function computeRoute(lat, lng, hospitalId = null, timeOfDay = 'off_peak') {
  const res = await fetch(`${API_BASE}/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat,
      lng,
      hospital_id: hospitalId,
      time_of_day: timeOfDay,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to compute route');
  }
  return res.json();
}

export async function computeCritical(routeNodes, baseTimeSec, source = null, target = null) {
  const res = await fetch(`${API_BASE}/critical`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      route_nodes: routeNodes,
      base_time_sec: baseTimeSec,
      source,
      target,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to compute resilience analysis');
  }
  return res.json();
}

export async function fetchBackupRoutes(source, target, primaryPath = null, baseTimeSec = null) {
  const res = await fetch(`${API_BASE}/backup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source,
      target,
      primary_path: primaryPath,
      base_time_sec: baseTimeSec,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to compute backup routes');
  }
  return res.json();
}

export async function blockRoad(u, v, incidentLat = null, incidentLng = null, originalTimeSec = null) {
  const res = await fetch(`${API_BASE}/block`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      u,
      v,
      incident_lat: incidentLat,
      incident_lng: incidentLng,
      original_time_sec: originalTimeSec,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to block road segment');
  }
  return res.json();
}

export async function unblockRoad(u, v, incidentLat = null, incidentLng = null) {
  const res = await fetch(`${API_BASE}/unblock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      u,
      v,
      incident_lat: incidentLat,
      incident_lng: incidentLng,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to unblock road segment');
  }
  return res.json();
}

export async function restoreRoads(incidentLat = null, incidentLng = null) {
  const res = await fetch(`${API_BASE}/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      incident_lat: incidentLat,
      incident_lng: incidentLng,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to restore road network');
  }
  return res.json();
}

export async function fetchCoverage(mode = 'current', k = 4, algorithm = 'p_median') {
  const url = `${API_BASE}/coverage?mode=${encodeURIComponent(mode)}&k=${k}&algorithm=${encodeURIComponent(algorithm)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch coverage data');
  }
  return res.json();
}

export async function suggestPlacement(k = 4, algorithm = 'p_median') {
  const res = await fetch(`${API_BASE}/placement/suggest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ k, algorithm }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to compute suggested station placement');
  }
  return res.json();
}

export async function assignAmbulances(accidents, objective = 'min_sum') {
  const res = await fetch(`${API_BASE}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ accidents, objective }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to compute multi-ambulance assignment');
  }
  return res.json();
}

export async function fetchTrafficConfig() {
  const res = await fetch(`${API_BASE}/traffic/config`);
  if (!res.ok) throw new Error('Failed to fetch traffic config');
  return res.json();
}

export async function scoreHospitals(lat, lng, traumaRequirement = 'general', hospitalStatuses = null, timeOfDay = 'off_peak') {
  const res = await fetch(`${API_BASE}/hospitals/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat,
      lng,
      trauma_requirement: traumaRequirement,
      hospital_statuses: hospitalStatuses,
      time_of_day: timeOfDay,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to score candidate hospitals');
  }
  return res.json();
}

export async function compareTrafficRoutes(lat = null, lng = null, hospitalId = null) {
  const res = await fetch(`${API_BASE}/route/compare-traffic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat,
      lng,
      hospital_id: hospitalId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to compare off-peak vs peak routes');
  }
  return res.json();
}

export async function runAlgorithmRace({
  source = null,
  target = null,
  originLat = null,
  originLng = null,
  destinationLat = null,
  destinationLng = null,
  timeOfDay = 'off_peak',
  sampleLimit = 1200,
} = {}) {
  const res = await fetch(`${API_BASE}/race`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source,
      target,
      origin_lat: originLat,
      origin_lng: originLng,
      destination_lat: destinationLat,
      destination_lng: destinationLng,
      time_of_day: timeOfDay,
      sample_limit: sampleLimit,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to execute Dijkstra vs A* algorithm race');
  }
  return res.json();
}



