import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import MapView from '../components/Map';
import Sidebar from '../components/Sidebar';
import AlgorithmRace from '../components/AlgorithmRace';
import {
  fetchGraphInfo,
  fetchHospitals,
  fetchStations,
  computeRoute,
  computeCritical,
  fetchBackupRoutes,
  blockRoad,
  unblockRoad,
  restoreRoads,
  fetchCoverage,
  suggestPlacement,
  assignAmbulances,
  scoreHospitals,
  compareTrafficRoutes,
  runAlgorithmRace,
} from '../api/client';

export default function Simulator() {
  const [graphInfo, setGraphInfo] = useState(null);
  const [hospitals, setHospitals] = useState([]);
  const [stations, setStations] = useState([]);
  const [accidentLocation, setAccidentLocation] = useState(null);
  const [routeData, setRouteData] = useState(null);
  const [criticalData, setCriticalData] = useState(null);
  const [backupData, setBackupData] = useState(null);
  const [blockedRoads, setBlockedRoads] = useState([]);
  const [blockedFeatures, setBlockedFeatures] = useState([]);
  const [addedDelayMin, setAddedDelayMin] = useState(0.0);
  const [originalRouteTimeSec, setOriginalRouteTimeSec] = useState(null);

  // Time-of-Day Traffic State
  const [timeOfDay, setTimeOfDay] = useState('off_peak');
  const [timeHour, setTimeHour] = useState(12);

  // Mode Switcher State: 'single' | 'triage' | 'multi'
  const [activeMode, setActiveMode] = useState('single');

  // Prompt 7 State: Hospital Scoring & Smart Triage (score = travel_time + P_trauma + P_load)
  const [traumaRequirement, setTraumaRequirement] = useState('general');
  const [hospitalStatuses, setHospitalStatuses] = useState({
    victoria: 'normal',
    nimhans: 'busy',
    bowring: 'normal',
    st_johns: 'normal',
    manipal: 'busy',
    kc_general: 'normal',
    igich: 'normal',
  });
  const [scoredHospitalsData, setScoredHospitalsData] = useState(null);
  const [scoringLoading, setScoringLoading] = useState(false);

  // Peak vs Off-Peak Route Divergence Comparison
  const [trafficComparisonData, setTrafficComparisonData] = useState(null);
  const [trafficComparisonActive, setTrafficComparisonActive] = useState(false);
  const [trafficComparisonLoading, setTrafficComparisonLoading] = useState(false);

  // Prompt 5 State: Coverage Heat Map & Station Placement Optimization
  const [coverageData, setCoverageData] = useState(null);
  const [baselineCoverage, setBaselineCoverage] = useState(null);
  const [coverageLoading, setCoverageLoading] = useState(false);
  const [showCoverageHeatmap, setShowCoverageHeatmap] = useState(true);
  const [suggestedStations, setSuggestedStations] = useState([]);
  const [kAmbulances, setKAmbulances] = useState(4);
  const [placementAlgorithm, setPlacementAlgorithm] = useState('p_median');
  const [coverageMode, setCoverageMode] = useState('current');

  // Prompt 6 State: Multi-Accident Assignment (Up to 5 accidents)
  const [multiAccidents, setMultiAccidents] = useState([]);
  const [assignmentObjective, setAssignmentObjective] = useState('min_sum');
  const [assignmentData, setAssignmentData] = useState(null);
  const [assignmentLoading, setAssignmentLoading] = useState(false);

  // Prompt 8 State: Algorithm Race (Dijkstra vs A*)
  const [raceData, setRaceData] = useState(null);
  const [raceLoading, setRaceLoading] = useState(false);

  const [loading, setLoading] = useState(false);
  const [criticalLoading, setCriticalLoading] = useState(false);
  const [backupLoading, setBackupLoading] = useState(false);
  const [blockLoading, setBlockLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load initial graph topology, facilities, and baseline coverage
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [info, hospData, stnData, covData] = await Promise.all([
          fetchGraphInfo(),
          fetchHospitals(),
          fetchStations(),
          fetchCoverage('current'),
        ]);
        setGraphInfo(info);
        setHospitals(hospData.features || []);
        setStations(stnData.features || []);
        setCoverageData(covData);
        setBaselineCoverage(covData);

        // Initialize hospital status defaults from backend
        if (hospData.features) {
          const initStatuses = {};
          hospData.features.forEach((h) => {
            initStatuses[h.properties.id] = h.properties.status || 'normal';
          });
          setHospitalStatuses((prev) => ({ ...initStatuses, ...prev }));
        }
      } catch (err) {
        console.error('Failed to load initial data:', err);
        setError('Failed to connect to backend server. Make sure the API service is running and reachable.');
      }
    }
    loadInitialData();
  }, []);

  // Time-of-Day Change Handler
  const handleTimeChange = async (period, hour) => {
    setTimeOfDay(period);
    setTimeHour(hour);

    // Recompute current single emergency route under new traffic conditions
    if (accidentLocation && (activeMode === 'single' || activeMode === 'triage')) {
      try {
        const rData = await computeRoute(accidentLocation.lat, accidentLocation.lng, null, period);
        setRouteData(rData);

        // Recompute hospital scoring
        await runHospitalScoring(accidentLocation.lat, accidentLocation.lng, traumaRequirement, hospitalStatuses, period);
      } catch (e) {
        console.warn('Re-routing on time change error:', e);
      }
    }

    // Recompute multi-accident assignments if active
    if (multiAccidents.length > 0 && activeMode === 'multi') {
      await runMultiAssignment(multiAccidents, assignmentObjective);
    }
  };

  // Hospital Scoring Runner
  const runHospitalScoring = async (
    lat = accidentLocation?.lat,
    lng = accidentLocation?.lng,
    req = traumaRequirement,
    statuses = hospitalStatuses,
    period = timeOfDay
  ) => {
    if (lat === undefined || lng === undefined) return;
    setScoringLoading(true);
    try {
      const res = await scoreHospitals(lat, lng, req, statuses, period);
      setScoredHospitalsData(res);
    } catch (err) {
      console.error('Hospital scoring error:', err);
    } finally {
      setScoringLoading(false);
    }
  };

  // Hospital Status Update Toggle
  const handleUpdateHospitalStatus = async (hospitalId, newStatus) => {
    const updated = { ...hospitalStatuses, [hospitalId]: newStatus };
    setHospitalStatuses(updated);
    if (accidentLocation) {
      await runHospitalScoring(accidentLocation.lat, accidentLocation.lng, traumaRequirement, updated, timeOfDay);
    }
  };

  // Preset status handlers
  const handlePresetHospitalStatuses = async (presetType) => {
    let newStatuses = {};
    if (presetType === 'all_normal') {
      Object.keys(hospitalStatuses).forEach((k) => {
        newStatuses[k] = 'normal';
      });
    } else if (presetType === 'bowring_busy') {
      newStatuses = { ...hospitalStatuses, bowring: 'busy', victoria: 'normal', nimhans: 'normal' };
    } else if (presetType === 'mass_casualty') {
      newStatuses = {
        victoria: 'busy',
        nimhans: 'full',
        bowring: 'busy',
        st_johns: 'normal',
        manipal: 'full',
        kc_general: 'busy',
        igich: 'normal',
      };
    }
    setHospitalStatuses(newStatuses);
    if (accidentLocation) {
      await runHospitalScoring(accidentLocation.lat, accidentLocation.lng, traumaRequirement, newStatuses, timeOfDay);
    }
  };

  // Trauma Requirement Toggle
  const handleToggleTraumaRequirement = async (req) => {
    setTraumaRequirement(req);
    if (accidentLocation) {
      await runHospitalScoring(accidentLocation.lat, accidentLocation.lng, req, hospitalStatuses, timeOfDay);
    }
  };

  // Trigger Peak vs Off-Peak Route Divergence Example
  const handleTriggerTrafficComparison = async () => {
    if (trafficComparisonActive) {
      setTrafficComparisonActive(false);
      return;
    }
    setTrafficComparisonLoading(true);
    try {
      const res = await compareTrafficRoutes(accidentLocation?.lat, accidentLocation?.lng);
      setTrafficComparisonData(res);
      setTrafficComparisonActive(true);
    } catch (err) {
      console.error('Failed to compare peak vs off-peak routes:', err);
      setError(err.message || 'Failed to compare routes');
    } finally {
      setTrafficComparisonLoading(false);
    }
  };

  // Prompt 6 Multi-Accident Assignment Runner
  const runMultiAssignment = async (accidents, obj = assignmentObjective) => {
    if (!accidents || accidents.length === 0) {
      setAssignmentData(null);
      return;
    }
    setAssignmentLoading(true);
    setError(null);
    try {
      const res = await assignAmbulances(accidents, obj);
      setAssignmentData(res);
    } catch (err) {
      console.error('Multi-accident assignment error:', err);
      setError(err.message || 'Failed to compute fleet assignment');
    } finally {
      setAssignmentLoading(false);
    }
  };

  const handleToggleAssignmentObjective = async (obj) => {
    setAssignmentObjective(obj);
    if (multiAccidents.length > 0) {
      await runMultiAssignment(multiAccidents, obj);
    }
  };

  const handleClearAccidents = () => {
    setMultiAccidents([]);
    setAssignmentData(null);
    setError(null);
  };

  // Prompt 8 Algorithm Race Runner
  const handleRunRace = async (preset = 'preset_majestic_manipal') => {
    setRaceLoading(true);
    setError(null);
    try {
      let payload = { timeOfDay };
      if (preset === 'preset_majestic_manipal') {
        payload.originLat = 12.9767;
        payload.originLng = 77.5713;
        payload.destinationLat = 12.9583;
        payload.destinationLng = 77.6508;
      } else if (preset === 'preset_koramangala_kc') {
        payload.originLat = 12.9352;
        payload.originLng = 77.6245;
        payload.destinationLat = 13.0012;
        payload.destinationLng = 77.5702;
      } else if (preset === 'preset_jayanagar_bowring') {
        payload.originLat = 12.9250;
        payload.originLng = 77.5938;
        payload.destinationLat = 12.9835;
        payload.destinationLng = 77.6056;
      } else if (typeof preset === 'object' && preset !== null) {
        payload = { ...payload, ...preset };
      }
      const data = await runAlgorithmRace(payload);
      setRaceData(data);
    } catch (err) {
      console.error('Race execution error:', err);
      setError(err.message || 'Failed to run algorithm race');
    } finally {
      setRaceLoading(false);
    }
  };

  const handleRemoveAccident = async (idOrIndex) => {
    const filtered = multiAccidents.filter((a) => a.id !== idOrIndex && a.index !== idOrIndex);
    const reindexed = filtered.map((a, idx) => ({ ...a, index: idx + 1 }));
    setMultiAccidents(reindexed);
    if (reindexed.length > 0) {
      await runMultiAssignment(reindexed, assignmentObjective);
    } else {
      setAssignmentData(null);
    }
  };

  // Mode Switcher Handler: 'single' | 'triage' | 'multi' | 'race'
  const handleModeChange = (mode) => {
    setActiveMode(mode);
    setError(null);
    if (mode === 'race' && !raceData) {
      handleRunRace('preset_majestic_manipal');
    }
  };

  // Handle map click: dispatches single route, triggers hospital scoring, or adds to multi-accident fleet dispatch
  const handleMapClick = async (lat, lng) => {
    if (activeMode === 'multi') {
      if (multiAccidents.length >= 5) {
        setError('Maximum of 5 emergency accident sites reached. Clear or remove an incident to place another.');
        return;
      }
      setError(null);
      const nextIndex = multiAccidents.length + 1;
      const newAcc = { id: `acc-${Date.now()}-${nextIndex}`, index: nextIndex, lat, lng };
      const nextList = [...multiAccidents, newAcc];
      setMultiAccidents(nextList);
      await runMultiAssignment(nextList, assignmentObjective);
      return;
    }

    // Single Emergency or Smart Triage Mode:
    setAccidentLocation({ lat, lng });
    setLoading(true);
    setCriticalLoading(true);
    setBackupLoading(true);
    setError(null);
    setCriticalData(null);
    setBackupData(null);

    try {
      // Step 1: Core Dijkstra Routing with active time_of_day traffic
      const rData = await computeRoute(lat, lng, null, timeOfDay);
      setRouteData(rData);
      setLoading(false);

      const totalTimeSec = rData.properties.total_time_sec;
      if (blockedRoads.length === 0) {
        setOriginalRouteTimeSec(totalTimeSec);
        setAddedDelayMin(0.0);
      } else if (originalRouteTimeSec) {
        const delay = Math.max(0.0, (totalTimeSec - originalRouteTimeSec) / 60.0);
        setAddedDelayMin(Number(delay.toFixed(2)));
      }

      // Step 2: Critical Infrastructure & Resilience Analysis
      const turnOrder = rData.properties.turn_order_vertices;
      const source = turnOrder[0];
      const target = turnOrder[turnOrder.length - 1];

      const cData = await computeCritical(turnOrder, totalTimeSec, source, target);
      setCriticalData(cData);
      setCriticalLoading(false);

      // Step 3: Backup Routes (Yen's K=3 & Edge-Disjoint Paths)
      try {
        const bkData = await fetchBackupRoutes(source, target, turnOrder, totalTimeSec);
        setBackupData(bkData);
      } catch (bkErr) {
        console.warn('Backup route computation warning:', bkErr);
      }

      // Step 4: Run Multi-Criteria Hospital Scoring (Prompt 7)
      await runHospitalScoring(lat, lng, traumaRequirement, hospitalStatuses, timeOfDay);
    } catch (err) {
      console.error('Routing/Resilience error:', err);
      setError(err.message || 'Operation failed for selected location');
    } finally {
      setLoading(false);
      setCriticalLoading(false);
      setBackupLoading(false);
    }
  };

  // Block / close a specific road segment on the working graph
  const handleBlockRoad = async (u, v, roadName = null) => {
    setBlockLoading(true);
    setError(null);
    try {
      const lat = accidentLocation?.lat;
      const lng = accidentLocation?.lng;
      const bRes = await blockRoad(u, v, lat, lng, originalRouteTimeSec);

      const newBlockedItem = {
        u,
        v,
        name: roadName || bRes.properties?.blocked_edge?.name || `Segment (${u} → ${v})`,
      };
      setBlockedRoads((prev) => [...prev, newBlockedItem]);

      const bFeats =
        bRes.features?.filter(
          (f) => f.properties?.type === 'blocked_edge' || f.properties?.type === 'blocked_marker'
        ) || [];
      setBlockedFeatures(bFeats);

      if (bRes.properties?.added_delay_min !== undefined) {
        setAddedDelayMin(bRes.properties.added_delay_min);
      }

      if (bRes.properties?.re_routed && bRes.properties?.route_properties) {
        const newRoute = {
          type: 'FeatureCollection',
          properties: bRes.properties.route_properties,
          features: bRes.features.filter(
            (f) => f.properties?.type !== 'blocked_edge' && f.properties?.type !== 'blocked_marker'
          ),
        };
        setRouteData(newRoute);

        const turnOrder = newRoute.properties.turn_order_vertices;
        const totalTime = newRoute.properties.total_time_sec;
        const cData = await computeCritical(turnOrder, totalTime, turnOrder[0], turnOrder[turnOrder.length - 1]);
        setCriticalData(cData);

        try {
          const bkData = await fetchBackupRoutes(turnOrder[0], turnOrder[turnOrder.length - 1], turnOrder, totalTime);
          setBackupData(bkData);
        } catch (bkErr) {
          console.warn('Backup calculation warning after block:', bkErr);
        }
      }
    } catch (err) {
      console.error('Road block error:', err);
      setError(err.message || 'Failed to block road segment');
    } finally {
      setBlockLoading(false);
    }
  };

  // Unblock a specific road segment
  const handleUnblockRoad = async (u, v) => {
    setBlockLoading(true);
    setError(null);
    try {
      const lat = accidentLocation?.lat;
      const lng = accidentLocation?.lng;
      const ubRes = await unblockRoad(u, v, lat, lng);

      const remainingBlocked = blockedRoads.filter((br) => !(br.u === u && br.v === v));
      setBlockedRoads(remainingBlocked);

      const bFeats =
        ubRes.features?.filter(
          (f) => f.properties?.type === 'blocked_edge' || f.properties?.type === 'blocked_marker'
        ) || [];
      setBlockedFeatures(bFeats);

      if (remainingBlocked.length === 0) {
        setAddedDelayMin(0.0);
      }

      if (ubRes.properties?.re_routed && ubRes.properties?.route_properties) {
        const newRoute = {
          type: 'FeatureCollection',
          properties: ubRes.properties.route_properties,
          features: ubRes.features.filter(
            (f) => f.properties?.type !== 'blocked_edge' && f.properties?.type !== 'blocked_marker'
          ),
        };
        setRouteData(newRoute);
      }
    } catch (err) {
      console.error('Unblock road error:', err);
      setError(err.message || 'Failed to unblock road segment');
    } finally {
      setBlockLoading(false);
    }
  };

  // Restore entire network to original baseline
  const handleRestoreRoads = async () => {
    setBlockLoading(true);
    setError(null);
    try {
      const lat = accidentLocation?.lat;
      const lng = accidentLocation?.lng;
      const res = await restoreRoads(lat, lng);

      setBlockedRoads([]);
      setBlockedFeatures([]);
      setAddedDelayMin(0.0);

      if (res.properties?.re_routed && res.properties?.route_properties) {
        const restoredRoute = {
          type: 'FeatureCollection',
          properties: res.properties.route_properties,
          features: res.features.filter(
            (f) => f.properties?.type !== 'blocked_edge' && f.properties?.type !== 'blocked_marker'
          ),
        };
        setRouteData(restoredRoute);
      }
    } catch (err) {
      console.error('Restore network error:', err);
      setError(err.message || 'Failed to restore network');
    } finally {
      setBlockLoading(false);
    }
  };

  // Station Placement Optimization
  const handleSuggestPlacement = async (k = kAmbulances, algo = placementAlgorithm) => {
    setCoverageLoading(true);
    setError(null);
    try {
      const res = await suggestPlacement(k, algo);
      setCoverageData(res);
      setSuggestedStations(res.properties?.suggested_stations || []);
      setCoverageMode('suggested');
      setShowCoverageHeatmap(true);
    } catch (err) {
      console.error('Failed to optimize station placement:', err);
      setError(err.message || 'Failed to optimize station placement');
    } finally {
      setCoverageLoading(false);
    }
  };

  const handleToggleCoverageMode = async (mode) => {
    if (mode === 'current') {
      if (baselineCoverage) {
        setCoverageData(baselineCoverage);
        setCoverageMode('current');
      } else {
        setCoverageLoading(true);
        try {
          const res = await fetchCoverage('current');
          setCoverageData(res);
          setBaselineCoverage(res);
          setCoverageMode('current');
        } catch (e) {
          console.error(e);
        } finally {
          setCoverageLoading(false);
        }
      }
    } else if (mode === 'suggested') {
      await handleSuggestPlacement(kAmbulances, placementAlgorithm);
    }
  };

  // Reset simulation
  const handleReset = async () => {
    try {
      await restoreRoads();
    } catch (e) {
      console.warn('Restore during reset:', e);
    }
    setAccidentLocation(null);
    setRouteData(null);
    setCriticalData(null);
    setBackupData(null);
    setBlockedRoads([]);
    setBlockedFeatures([]);
    setAddedDelayMin(0.0);
    setOriginalRouteTimeSec(null);
    setError(null);
    setCoverageMode('current');
    if (baselineCoverage) {
      setCoverageData(baselineCoverage);
    }
    setMultiAccidents([]);
    setAssignmentData(null);
    setScoredHospitalsData(null);
    setTrafficComparisonActive(false);
    setTrafficComparisonData(null);
    setActiveMode('single');
  };

  const activeLoadingMessage =
    blockLoading
      ? 'Simulating road blockage & dynamic re-routing...'
      : criticalLoading
      ? 'Computing Tarjan low-link bridges & resilience score...'
      : backupLoading
      ? "Calculating Yen's K=3 shortest paths & edge-disjoint routes..."
      : coverageLoading
      ? 'Computing multi-source Dijkstra coverage isochrones...'
      : assignmentLoading
      ? 'Solving Hungarian fleet assignment...'
      : scoringLoading
      ? 'Scoring candidate hospitals with trauma and load penalties...'
      : loading
      ? 'Finding nearest ambulance and computing optimal emergency route...'
      : null;

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Header
        graphInfo={graphInfo}
        onReset={handleReset}
        onRestore={handleRestoreRoads}
        blockedCount={blockedRoads.length}
        loading={
          loading ||
          criticalLoading ||
          backupLoading ||
          blockLoading ||
          coverageLoading ||
          assignmentLoading ||
          scoringLoading ||
          trafficComparisonLoading
        }
        timeOfDay={timeOfDay}
        timeHour={timeHour}
        onTimeChange={handleTimeChange}
        onTriggerTrafficComparison={handleTriggerTrafficComparison}
        trafficComparisonActive={trafficComparisonActive}
      />

      <main style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar
          routeData={routeData}
          criticalData={criticalData}
          backupData={backupData}
          blockedRoads={blockedRoads}
          addedDelayMin={addedDelayMin}
          accidentLocation={accidentLocation}
          loading={loading}
          criticalLoading={criticalLoading}
          backupLoading={backupLoading}
          blockLoading={blockLoading}
          error={error}
          // Mode Switcher Props
          activeMode={activeMode}
          onModeChange={handleModeChange}
          // Prompt 7 Props: Hospital Scoring & Smart Triage
          hospitals={hospitals}
          traumaRequirement={traumaRequirement}
          onToggleTraumaRequirement={handleToggleTraumaRequirement}
          hospitalStatuses={hospitalStatuses}
          onUpdateHospitalStatus={handleUpdateHospitalStatus}
          onPresetHospitalStatuses={handlePresetHospitalStatuses}
          scoredHospitalsData={scoredHospitalsData}
          scoringLoading={scoringLoading}
          onScoreHospitals={() =>
            runHospitalScoring(
              accidentLocation?.lat,
              accidentLocation?.lng,
              traumaRequirement,
              hospitalStatuses,
              timeOfDay
            )
          }
          // Traffic Comparison Props
          trafficComparisonData={trafficComparisonData}
          trafficComparisonActive={trafficComparisonActive}
          onCloseTrafficComparison={() => setTrafficComparisonActive(false)}
          // Prompt 5 Props:
          coverageData={coverageData}
          baselineCoverage={baselineCoverage}
          coverageLoading={coverageLoading}
          suggestedStations={suggestedStations}
          kAmbulances={kAmbulances}
          setKAmbulances={setKAmbulances}
          placementAlgorithm={placementAlgorithm}
          setPlacementAlgorithm={setPlacementAlgorithm}
          coverageMode={coverageMode}
          onSuggestPlacement={handleSuggestPlacement}
          onToggleCoverageMode={handleToggleCoverageMode}
          showCoverageHeatmap={showCoverageHeatmap}
          onToggleCoverageHeatmap={setShowCoverageHeatmap}
          // Prompt 6 Props:
          assignmentData={assignmentData}
          assignmentLoading={assignmentLoading}
          multiAccidents={multiAccidents}
          assignmentObjective={assignmentObjective}
          onToggleAssignmentObjective={handleToggleAssignmentObjective}
          onClearAccidents={handleClearAccidents}
          onRemoveAccident={handleRemoveAccident}
          // Prompt 8 Props: Algorithm Race (Dijkstra vs A*)
          raceData={raceData}
          raceLoading={raceLoading}
          onRunRace={handleRunRace}
          onBlockRoad={handleBlockRoad}
          onUnblockRoad={handleUnblockRoad}
          onRestoreRoads={handleRestoreRoads}
        />

        <div style={{ flex: 1, height: '100%', position: 'relative' }}>
          {activeMode === 'race' ? (
            <AlgorithmRace
              raceData={raceData}
              raceLoading={raceLoading}
              onRunRace={handleRunRace}
              timeOfDay={timeOfDay}
            />
          ) : (
            <MapView
              hospitals={hospitals}
              stations={stations}
              accidentLocation={accidentLocation}
              routeData={routeData}
              criticalData={criticalData}
              backupData={backupData}
              blockedRoads={blockedRoads}
              blockedFeatures={blockedFeatures}
              // Prompt 7 Props: Hospital Scoring & Divergence Routes
              scoredHospitalsData={scoredHospitalsData}
              hospitalStatuses={hospitalStatuses}
              trafficComparisonData={trafficComparisonData}
              trafficComparisonActive={trafficComparisonActive}
              // Prompt 5 Props:
              coverageData={coverageData}
              suggestedStations={suggestedStations}
              showCoverageHeatmap={showCoverageHeatmap}
              onToggleCoverageHeatmap={setShowCoverageHeatmap}
              // Prompt 6 Props:
              assignmentData={assignmentData}
              multiAccidents={multiAccidents}
              assignmentMode={activeMode === 'multi'}
              onRemoveAccident={handleRemoveAccident}
              onMapClick={handleMapClick}
              onBlockRoad={handleBlockRoad}
              onUnblockRoad={handleUnblockRoad}
              onRestoreRoads={handleRestoreRoads}
              // Loading & Error Alerts
              loadingMessage={activeLoadingMessage}
              error={error}
              onClearError={() => setError(null)}
            />
          )}
        </div>
      </main>
    </div>
  );
}
