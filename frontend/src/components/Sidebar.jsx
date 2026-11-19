import React, { useState } from 'react';
import {
  Clock,
  Navigation,
  Activity,
  Layers,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Building2,
  Ambulance,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  GitFork,
  HelpCircle,
  Ban,
  RefreshCw,
  GitMerge,
  Split,
  MapPin,
  Sparkles,
  Sliders,
  Compass,
  Crosshair,
  TrendingUp,
  BarChart2,
  CheckCircle2,
  Trophy,
  Award,
  Stethoscope,
  Zap,
} from 'lucide-react';

export default function Sidebar({
  routeData,
  criticalData,
  backupData,
  blockedRoads = [],
  addedDelayMin = 0.0,
  accidentLocation,
  loading,
  criticalLoading,
  backupLoading,
  blockLoading,
  error,
  // Mode Switcher Props: 'single' | 'triage' | 'multi'
  activeMode = 'single',
  onModeChange,
  // Prompt 7 Props: Hospital Scoring & Smart Triage
  hospitals = [],
  traumaRequirement = 'general',
  onToggleTraumaRequirement,
  hospitalStatuses = {},
  onUpdateHospitalStatus,
  onPresetHospitalStatuses,
  scoredHospitalsData = null,
  scoringLoading = false,
  onScoreHospitals,
  // Traffic Comparison Props
  trafficComparisonData = null,
  trafficComparisonActive = false,
  onCloseTrafficComparison,
  // Prompt 5 props: Station Placement & Isochrone Coverage
  coverageData,
  baselineCoverage,
  coverageLoading,
  suggestedStations = [],
  kAmbulances = 4,
  setKAmbulances,
  placementAlgorithm = 'p_median',
  setPlacementAlgorithm,
  coverageMode = 'current',
  onSuggestPlacement,
  onToggleCoverageMode,
  showCoverageHeatmap = true,
  onToggleCoverageHeatmap,
  // Prompt 6 Props: Multi-Accident Assignment
  assignmentData = null,
  assignmentLoading = false,
  multiAccidents = [],
  assignmentObjective = 'min_sum',
  onToggleAssignmentObjective,
  onClearAccidents,
  onRemoveAccident,
  // Prompt 8 Props: Algorithm Race (Dijkstra vs A*)
  raceData = null,
  raceLoading = false,
  onRunRace,
  onBlockRoad,
  onUnblockRoad,
  onRestoreRoads,
}) {
  const [showVertexList, setShowVertexList] = useState(false);
  const [showSoftBridgeList, setShowSoftBridgeList] = useState(true);
  const [showBackupList, setShowBackupList] = useState(true);
  const [showPlacementSection, setShowPlacementSection] = useState(false);
  const [showSuggestedStationsList, setShowSuggestedStationsList] = useState(true);

  const props = routeData?.properties;
  const critProps = criticalData?.properties;
  const backupPlans = backupData?.properties?.plans || [];

  const covProps = coverageData?.properties;
  const bands = covProps?.bands;
  const baselineComp = covProps?.baseline_comparison;
  const isSuggested = covProps?.mode === 'suggested';

  return (
    <aside style={styles.sidebar}>
      {/* Header section of sidebar */}
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={18} color="#38bdf8" />
          <h2 style={{ fontSize: '15px', fontWeight: '700', color: '#f8fafc' }}>
            Dispatch Telemetry & Resilience
          </h2>
        </div>
        {(loading || criticalLoading || backupLoading || blockLoading || scoringLoading) && (
          <span style={styles.loadingBadge}>
            {blockLoading
              ? 'Rerouting...'
              : loading
              ? 'Routing...'
              : criticalLoading
              ? 'Analyzing Resilience...'
              : scoringLoading
              ? 'Scoring Hospitals...'
              : 'Computing Backups...'}
          </span>
        )}
      </div>

      <div style={styles.scrollableContent}>
        {error && (
          <div style={styles.errorAlert}>
            <AlertCircle size={16} color="#ef4444" style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* 4-Way Operation Mode Switcher: Single Route vs Smart Triage vs Multi-Accident Fleet vs Algorithm Race */}
        <div style={styles.operationModeContainer}>
          <button
            onClick={() => onModeChange && onModeChange('single')}
            style={{
              ...styles.operationModeBtn,
              backgroundColor: activeMode === 'single' ? '#0284c7' : '#1e293b',
              color: activeMode === 'single' ? '#ffffff' : '#94a3b8',
              border: activeMode === 'single' ? '1px solid #38bdf8' : '1px solid #334155',
            }}
          >
            <Navigation size={12} style={{ marginRight: '4px' }} />
            Single Route
          </button>
          <button
            onClick={() => onModeChange && onModeChange('triage')}
            style={{
              ...styles.operationModeBtn,
              backgroundColor: activeMode === 'triage' ? '#10b981' : '#1e293b',
              color: activeMode === 'triage' ? '#ffffff' : '#94a3b8',
              border: activeMode === 'triage' ? '1px solid #34d399' : '1px solid #334155',
            }}
          >
            <Stethoscope size={12} style={{ marginRight: '4px' }} />
            Smart Triage
          </button>
          <button
            onClick={() => onModeChange && onModeChange('multi')}
            style={{
              ...styles.operationModeBtn,
              backgroundColor: activeMode === 'multi' ? '#db2777' : '#1e293b',
              color: activeMode === 'multi' ? '#ffffff' : '#94a3b8',
              border: activeMode === 'multi' ? '1px solid #f472b6' : '1px solid #334155',
            }}
          >
            <Ambulance size={12} style={{ marginRight: '4px' }} />
            Fleet ({multiAccidents.length}/5)
          </button>
          <button
            onClick={() => onModeChange && onModeChange('race')}
            style={{
              ...styles.operationModeBtn,
              backgroundColor: activeMode === 'race' ? '#8b5cf6' : '#1e293b',
              color: activeMode === 'race' ? '#ffffff' : '#94a3b8',
              border: activeMode === 'race' ? '1px solid #a78bfa' : '1px solid #334155',
            }}
          >
            <Zap size={12} style={{ marginRight: '4px' }} />
            Race (A*)
          </button>
        </div>

        {/* Peak vs Off-Peak Route Divergence Alert Banner */}
        {trafficComparisonActive && trafficComparisonData && (
          <div style={styles.trafficDivergenceCard}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Zap size={16} color="#f97316" />
                <span style={{ fontSize: '12px', fontWeight: '800', color: '#fed7aa', letterSpacing: '0.03em' }}>
                  PEAK VS OFF-PEAK ROUTE DIVERGENCE
                </span>
              </div>
              <button
                onClick={onCloseTrafficComparison}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '12px' }}
              >
                ✕ Close
              </button>
            </div>

            <p style={{ fontSize: '11px', color: '#ffedd5', lineHeight: '1.45', marginBottom: '8px' }}>
              {trafficComparisonData.properties?.explanation}
            </p>

            <div style={styles.divergenceMetricsGrid}>
              <div style={{ ...styles.metricItem, borderLeft: '3px solid #0284c7' }}>
                <div style={styles.metricLabel}>Off-Peak Route (Arterial)</div>
                <div style={{ fontSize: '15px', fontWeight: '800', color: '#38bdf8', fontFamily: 'JetBrains Mono' }}>
                  {trafficComparisonData.properties?.off_peak?.travel_time_min} min
                </div>
                <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>
                  During peak: {trafficComparisonData.properties?.off_peak?.time_if_driven_at_peak_min} min
                </div>
              </div>

              <div style={{ ...styles.metricItem, borderLeft: '3px solid #f97316' }}>
                <div style={styles.metricLabel}>Peak Detour (Bypass)</div>
                <div style={{ fontSize: '15px', fontWeight: '800', color: '#fb923c', fontFamily: 'JetBrains Mono' }}>
                  {trafficComparisonData.properties?.peak?.travel_time_min} min
                </div>
                <div style={{ fontSize: '10px', color: '#34d399', fontWeight: '700', marginTop: '2px' }}>
                  Saves -{trafficComparisonData.properties?.peak_bypass_savings_min} min vs arterial!
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Prompt 7 Flagship: Smart Triage & Hospital Facility Scoring Panel */}
        {activeMode === 'triage' && (
          <div style={styles.triageCard}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Stethoscope size={18} color="#10b981" />
                <span style={{ fontSize: '13px', fontWeight: '800', color: '#f8fafc', letterSpacing: '0.04em' }}>
                  SMART TRIAGE & FACILITY SCORING
                </span>
              </div>
              <span style={{ ...styles.blockedPill, backgroundColor: '#059669' }}>
                Score = T + P_tr + P_ld
              </span>
            </div>

            <p style={{ fontSize: '11px', color: '#cbd5e1', lineHeight: '1.4', marginBottom: '10px' }}>
              Multi-criteria facility selection balances driving time, clinical trauma capabilities (Level-1 vs Level-2), and ER operational queue status (Normal/Busy/Full).
            </p>

            {/* Trauma Requirement Selector */}
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px', fontWeight: '700' }}>
                CLINICAL TRAUMA SEVERITY:
              </div>
              <div style={styles.modeToggleContainer}>
                <button
                  onClick={() => onToggleTraumaRequirement && onToggleTraumaRequirement('general')}
                  style={{
                    ...styles.modeToggleBtn,
                    backgroundColor: traumaRequirement === 'general' ? '#0284c7' : '#0f172a',
                    color: traumaRequirement === 'general' ? '#ffffff' : '#94a3b8',
                    border: traumaRequirement === 'general' ? '1px solid #38bdf8' : '1px solid #334155',
                  }}
                  title="General Emergency: All trauma facilities qualified (P_trauma = 0 min)"
                >
                  🩺 General Emergency (P_tr=0m)
                </button>
                <button
                  onClick={() => onToggleTraumaRequirement && onToggleTraumaRequirement('major_trauma')}
                  style={{
                    ...styles.modeToggleBtn,
                    backgroundColor: traumaRequirement === 'major_trauma' ? '#dc2626' : '#0f172a',
                    color: traumaRequirement === 'major_trauma' ? '#ffffff' : '#94a3b8',
                    border: traumaRequirement === 'major_trauma' ? '1px solid #ef4444' : '1px solid #334155',
                  }}
                  title="Major Trauma: Level-1 trauma center required. Non-L1 incurs +15 min transfer penalty"
                >
                  🚨 Major Trauma (L1 Req, +15m)
                </button>
              </div>
            </div>

            {/* Hospital Status Management with Presets */}
            <div style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: '700' }}>
                  HOSPITAL CAPACITY PRESETS:
                </span>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button onClick={() => onPresetHospitalStatuses && onPresetHospitalStatuses('all_normal')} style={styles.presetMiniBtn}>
                    All Normal
                  </button>
                  <button onClick={() => onPresetHospitalStatuses && onPresetHospitalStatuses('bowring_busy')} style={{ ...styles.presetMiniBtn, color: '#f59e0b' }}>
                    Bowring Busy
                  </button>
                  <button onClick={() => onPresetHospitalStatuses && onPresetHospitalStatuses('mass_casualty')} style={{ ...styles.presetMiniBtn, color: '#ef4444' }}>
                    Mass Casualty
                  </button>
                </div>
              </div>
            </div>

            {/* Why Winner Beat Nearest Callout Box */}
            {scoredHospitalsData?.properties?.winner && (
              <div style={styles.winnerCalloutBox}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Trophy size={16} color="#fbbf24" />
                    <span style={{ fontSize: '12px', fontWeight: '800', color: '#fbbf24' }}>
                      WINNER: {scoredHospitalsData.properties.winner.short_name} ({scoredHospitalsData.properties.winner.score_min}m)
                    </span>
                  </div>
                  {scoredHospitalsData.properties.nearest && scoredHospitalsData.properties.nearest.id !== scoredHospitalsData.properties.winner.id ? (
                    <span style={{ fontSize: '10px', color: '#fca5a5', fontWeight: '700' }}>
                      Nearest: {scoredHospitalsData.properties.nearest.short_name} ({scoredHospitalsData.properties.nearest.score_min}m)
                    </span>
                  ) : (
                    <span style={{ fontSize: '10px', color: '#34d399', fontWeight: '700' }}>
                      Optimal on all criteria
                    </span>
                  )}
                </div>

                <p style={{ fontSize: '11px', color: '#f1f5f9', lineHeight: '1.45', margin: '4px 0 0 0' }}>
                  {scoredHospitalsData.properties.winner_explanation}
                </p>
              </div>
            )}

            {/* Ranked Hospital Table */}
            {scoredHospitalsData?.properties?.ranked_hospitals && (
              <div style={{ marginTop: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: '800', color: '#e2e8f0', letterSpacing: '0.04em' }}>
                    CANDIDATE HOSPITAL RANKING TABLE
                  </span>
                  <span style={{ fontSize: '10px', color: '#94a3b8' }}>
                    P_load: Normal=0m · Busy=+8m · Full=+30m
                  </span>
                </div>

                <div style={styles.tableWrapper}>
                  <table style={styles.assignmentTable}>
                    <thead>
                      <tr>
                        <th style={styles.th}>Rank</th>
                        <th style={styles.th}>Hospital</th>
                        <th style={styles.th}>Status Toggle</th>
                        <th style={styles.th}>Travel (T)</th>
                        <th style={styles.th}>P_trauma</th>
                        <th style={styles.th}>P_load</th>
                        <th style={{ ...styles.th, color: '#38bdf8' }}>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scoredHospitalsData.properties.ranked_hospitals.map((h, idx) => {
                        const isWin = h.is_winner;
                        const isNear = h.is_nearest;
                        return (
                          <tr
                            key={h.id}
                            style={{
                              backgroundColor: isWin
                                ? 'rgba(16, 185, 129, 0.15)'
                                : idx % 2 === 0
                                ? 'rgba(30, 41, 59, 0.4)'
                                : 'transparent',
                            }}
                          >
                            <td style={styles.td}>
                              {isWin ? (
                                <span style={{ fontWeight: '800', color: '#fbbf24' }}>🥇 #1</span>
                              ) : (
                                <span style={{ color: '#94a3b8' }}>#{h.rank}</span>
                              )}
                            </td>
                            <td style={styles.td}>
                              <div style={{ fontWeight: '700', color: isWin ? '#34d399' : '#f8fafc' }}>
                                {h.short_name}
                              </div>
                              <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
                                <span
                                  style={{
                                    fontSize: '9px',
                                    fontWeight: '700',
                                    color: h.trauma_level === 'Level-1' ? '#60a5fa' : '#c084fc',
                                  }}
                                >
                                  {h.trauma_level}
                                </span>
                                {isNear && (
                                  <span style={{ fontSize: '9px', color: '#f59e0b', fontWeight: '700' }}>
                                    · 📍 Nearest ({h.distance_km}km)
                                  </span>
                                )}
                              </div>
                            </td>
                            <td style={styles.td}>
                              <div style={{ display: 'flex', gap: '2px' }}>
                                {['normal', 'busy', 'full'].map((st) => {
                                  const active = (hospitalStatuses[h.id] || h.status) === st;
                                  let bg = '#0f172a';
                                  let col = '#64748b';
                                  if (active) {
                                    if (st === 'normal') {
                                      bg = '#059669';
                                      col = '#ffffff';
                                    } else if (st === 'busy') {
                                      bg = '#d97706';
                                      col = '#ffffff';
                                    } else {
                                      bg = '#dc2626';
                                      col = '#ffffff';
                                    }
                                  }
                                  return (
                                    <button
                                      key={st}
                                      onClick={() => onUpdateHospitalStatus && onUpdateHospitalStatus(h.id, st)}
                                      style={{
                                        padding: '2px 5px',
                                        fontSize: '9px',
                                        fontWeight: active ? '700' : '500',
                                        backgroundColor: bg,
                                        color: col,
                                        border: '1px solid ' + (active ? col : '#334155'),
                                        borderRadius: '3px',
                                        cursor: 'pointer',
                                      }}
                                    >
                                      {st[0].toUpperCase()}
                                    </button>
                                  );
                                })}
                              </div>
                            </td>
                            <td style={{ ...styles.td, fontFamily: 'JetBrains Mono', color: '#f1f5f9' }}>
                              {h.travel_time_min}m
                            </td>
                            <td
                              style={{
                                ...styles.td,
                                fontFamily: 'JetBrains Mono',
                                color: h.p_trauma_min > 0 ? '#ef4444' : '#64748b',
                                fontWeight: h.p_trauma_min > 0 ? '700' : '400',
                              }}
                            >
                              +{h.p_trauma_min}m
                            </td>
                            <td
                              style={{
                                ...styles.td,
                                fontFamily: 'JetBrains Mono',
                                color: h.p_load_min > 0 ? '#f59e0b' : '#64748b',
                                fontWeight: h.p_load_min > 0 ? '700' : '400',
                              }}
                            >
                              +{h.p_load_min}m
                            </td>
                            <td
                              style={{
                                ...styles.td,
                                fontFamily: 'JetBrains Mono',
                                fontWeight: '800',
                                color: isWin ? '#34d399' : '#38bdf8',
                                fontSize: '12px',
                              }}
                            >
                              {h.score_min}m
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {!accidentLocation && (
              <div style={styles.assignmentEmptyPrompt}>
                <span style={{ fontSize: '24px', marginBottom: '6px' }}>📍</span>
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#f8fafc' }}>
                  No Incident Placed Yet
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                  Click anywhere on the Bengaluru map to evaluate candidate hospital triage scores
                </div>
              </div>
            )}
          </div>
        )}

        {/* Prompt 6 Flagship: Multi-Accident Assignment Panel */}
        {activeMode === 'multi' && (
          <div style={styles.assignmentCard}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Ambulance size={18} color="#ec4899" />
                <span style={{ fontSize: '13px', fontWeight: '800', color: '#f8fafc', letterSpacing: '0.04em' }}>
                  MULTI-ACCIDENT FLEET DISPATCH
                </span>
              </div>
              <span style={{ ...styles.blockedPill, backgroundColor: '#db2777' }}>
                {multiAccidents.length} / 5 Sites
              </span>
            </div>

            <p style={{ fontSize: '11px', color: '#cbd5e1', lineHeight: '1.4', marginBottom: '10px' }}>
              Click on the map to place up to 5 emergency incidents across Bengaluru. 1-to-1 ambulance matching solves Min-Sum (Hungarian) or Minimax Bottleneck.
            </p>

            {/* Objective Switcher Toggle (Prompt 6: Min-Sum vs Bottleneck) */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px', fontWeight: '600' }}>
                DISPATCH OBJECTIVE:
              </div>
              <div style={styles.modeToggleContainer}>
                <button
                  onClick={() => onToggleAssignmentObjective && onToggleAssignmentObjective('min_sum')}
                  style={{
                    ...styles.modeToggleBtn,
                    backgroundColor: assignmentObjective === 'min_sum' ? '#059669' : '#0f172a',
                    color: assignmentObjective === 'min_sum' ? '#ffffff' : '#94a3b8',
                    border: assignmentObjective === 'min_sum' ? '1px solid #10b981' : '1px solid #334155',
                  }}
                  title="Min-Sum: Minimizes sum of all response times (Hungarian Algorithm)"
                >
                  Min-Sum (Total Time)
                </button>
                <button
                  onClick={() => onToggleAssignmentObjective && onToggleAssignmentObjective('bottleneck')}
                  style={{
                    ...styles.modeToggleBtn,
                    backgroundColor: assignmentObjective === 'bottleneck' ? '#d97706' : '#0f172a',
                    color: assignmentObjective === 'bottleneck' ? '#ffffff' : '#94a3b8',
                    border: assignmentObjective === 'bottleneck' ? '1px solid #f59e0b' : '1px solid #334155',
                  }}
                  title="Bottleneck: Minimizes the maximum worst-case response time (Minimax BAP)"
                >
                  Bottleneck (Worst-Case)
                </button>
              </div>
            </div>

            {/* Action Bar */}
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
              <button
                onClick={onClearAccidents}
                disabled={multiAccidents.length === 0}
                style={{
                  ...styles.clearAccidentsBtn,
                  opacity: multiAccidents.length === 0 ? 0.4 : 1,
                  cursor: multiAccidents.length === 0 ? 'not-allowed' : 'pointer',
                }}
              >
                Clear Accidents ({multiAccidents.length})
              </button>
            </div>

            {/* Assignment Results Telemetry */}
            {assignmentData?.properties?.assignments && (
              <>
                <div style={styles.metricGrid}>
                  <div style={styles.metricItem}>
                    <div style={styles.metricLabel}>Total Fleet Time</div>
                    <div style={{ fontSize: '18px', fontWeight: '800', color: '#10b981', fontFamily: 'JetBrains Mono' }}>
                      {assignmentData.properties.total_time_min} <span style={{ fontSize: '11px', color: '#94a3b8' }}>min</span>
                    </div>
                    <div style={styles.metricSub}>({assignmentData.properties.total_time_sec}s total)</div>
                  </div>

                  <div style={styles.metricItem}>
                    <div style={styles.metricLabel}>Worst-Case Time</div>
                    <div style={{ fontSize: '18px', fontWeight: '800', color: '#f59e0b', fontFamily: 'JetBrains Mono' }}>
                      {assignmentData.properties.max_time_min} <span style={{ fontSize: '11px', color: '#94a3b8' }}>min</span>
                    </div>
                    <div style={styles.metricSub}>({assignmentData.properties.max_time_sec}s max delay)</div>
                  </div>

                  <div style={styles.metricItem}>
                    <div style={styles.metricLabel}>Mean Response</div>
                    <div style={{ fontSize: '18px', fontWeight: '800', color: '#38bdf8', fontFamily: 'JetBrains Mono' }}>
                      {assignmentData.properties.mean_time_min} <span style={{ fontSize: '11px', color: '#94a3b8' }}>min</span>
                    </div>
                    <div style={styles.metricSub}>({assignmentData.properties.num_assigned} units dispatched)</div>
                  </div>
                </div>

                {/* Assignment Table (Prompt 6) */}
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '11px', fontWeight: '800', color: '#e2e8f0', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    1-TO-1 FLEET ASSIGNMENT TABLE
                  </div>
                  <div style={styles.tableWrapper}>
                    <table style={styles.assignmentTable}>
                      <thead>
                        <tr>
                          <th style={styles.th}>Route</th>
                          <th style={styles.th}>Accident</th>
                          <th style={styles.th}>Dispatched Ambulance</th>
                          <th style={styles.th}>Base Station</th>
                          <th style={styles.th}>Time</th>
                          <th style={styles.th}>Distance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {assignmentData.properties.assignments.map((a) => (
                          <tr key={a.ambulance_id}>
                            <td style={styles.td}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span
                                  style={{
                                    display: 'inline-block',
                                    width: '10px',
                                    height: '10px',
                                    borderRadius: '50%',
                                    backgroundColor: a.color,
                                  }}
                                />
                                {a.is_bottleneck && (
                                  <span style={{ fontSize: '9px', fontWeight: '800', color: '#f59e0b' }}>
                                    ⚠️ MAX
                                  </span>
                                )}
                              </div>
                            </td>
                            <td style={styles.td}>
                              <span style={{ fontWeight: '700', color: '#f8fafc' }}>
                                #{a.accident_index}
                              </span>
                            </td>
                            <td style={styles.td}>
                              <span style={{ fontWeight: '600', color: '#cbd5e1' }}>
                                {a.ambulance_name}
                              </span>
                            </td>
                            <td style={styles.td}>
                              <span style={{ color: '#94a3b8' }}>{a.station_name}</span>
                            </td>
                            <td style={{ ...styles.td, fontFamily: 'JetBrains Mono', color: '#f1f5f9' }}>
                              {a.travel_time_min} min ({a.travel_time_sec}s)
                            </td>
                            <td style={{ ...styles.td, fontFamily: 'JetBrains Mono', color: '#cbd5e1' }}>
                              {a.distance_km} km
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}

            {multiAccidents.length === 0 && (
              <div style={styles.assignmentEmptyPrompt}>
                <span style={{ fontSize: '24px', marginBottom: '6px' }}>📍</span>
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#f8fafc' }}>
                  No Incidents Placed Yet
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                  Click anywhere on the Bengaluru map to place Accident #1 (up to 5 accidents)
                </div>
              </div>
            )}
          </div>
        )}

        {/* Prompt 8 Flagship: Algorithm Race Panel (Dijkstra vs A*) */}
        {activeMode === 'race' && (
          <div style={styles.raceCard}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Zap size={18} color="#a78bfa" />
                <span style={{ fontSize: '13px', fontWeight: '800', color: '#f8fafc', letterSpacing: '0.04em' }}>
                  ALGORITHM RACE (DIJKSTRA VS A*)
                </span>
              </div>
              <span style={{ ...styles.blockedPill, backgroundColor: '#7c3aed' }}>
                Admissible A*
              </span>
            </div>

            <p style={{ fontSize: '11px', color: '#cbd5e1', lineHeight: '1.45', marginBottom: '10px' }}>
              Compare Dijkstra uniform-cost search against A* directed search using the admissible Haversine heuristic <code style={{ color: '#a78bfa' }}>h(u) = d_haversine / v_max</code>. Guaranteed to return identical shortest path costs while pruning unpromising road branches.
            </p>

            {/* Presets */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px', fontWeight: '700' }}>
                SELECT EMERGENCY CORRIDOR:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <button
                  onClick={() => onRunRace && onRunRace('preset_majestic_manipal')}
                  disabled={raceLoading}
                  style={styles.racePresetBtn}
                >
                  📍 Majestic Station ➔ Manipal Hospital
                </button>
                <button
                  onClick={() => onRunRace && onRunRace('preset_koramangala_kc')}
                  disabled={raceLoading}
                  style={styles.racePresetBtn}
                >
                  📍 Koramangala Station ➔ KC General
                </button>
                <button
                  onClick={() => onRunRace && onRunRace('preset_jayanagar_bowring')}
                  disabled={raceLoading}
                  style={styles.racePresetBtn}
                >
                  📍 Jayanagar Station ➔ Bowring Hospital
                </button>
              </div>
            </div>

            {/* Quick Status / Verification Badge */}
            {raceData && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 8px',
                    borderRadius: '6px',
                    backgroundColor: raceData.properties?.costs_equal ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                    border: `1px solid ${raceData.properties?.costs_equal ? '#10b981' : '#ef4444'}`,
                  }}
                >
                  <CheckCircle2 size={14} color={raceData.properties?.costs_equal ? '#10b981' : '#ef4444'} />
                  <span style={{ fontSize: '11px', fontWeight: '800', color: raceData.properties?.costs_equal ? '#10b981' : '#ef4444' }}>
                    {raceData.properties?.costs_equal
                      ? `Costs Strictly Equal (Δ = ${raceData.properties?.cost_diff_sec?.toFixed(3)}s)`
                      : `Discrepancy: Δ = ${raceData.properties?.cost_diff_sec?.toFixed(3)}s`}
                  </span>
                </div>

                <div style={styles.raceMetricGrid}>
                  <div style={styles.raceMetricBox}>
                    <div style={styles.metricLabel}>Dijkstra Nodes</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#38bdf8', fontFamily: 'JetBrains Mono' }}>
                      {raceData.properties?.dijkstra?.nodes_expanded?.toLocaleString()}
                    </div>
                  </div>
                  <div style={styles.raceMetricBox}>
                    <div style={styles.metricLabel}>A* Nodes</div>
                    <div style={{ fontSize: '14px', fontWeight: '800', color: '#10b981', fontFamily: 'JetBrains Mono' }}>
                      {raceData.properties?.astar?.nodes_expanded?.toLocaleString()}
                    </div>
                  </div>
                  <div style={{ ...styles.raceMetricBox, gridColumn: 'span 2' }}>
                    <div style={styles.metricLabel}>Node Pruning Gain</div>
                    <div style={{ fontSize: '13px', fontWeight: '800', color: '#34d399', fontFamily: 'JetBrains Mono' }}>
                      📉 {raceData.properties?.node_reduction_pct}% fewer nodes explored
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Prompt 4: Active Road Blockages & Live Re-routing Alert Card */}
        {blockedRoads.length > 0 && (
          <div style={styles.blockageCard}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Ban size={16} color="#ef4444" />
                <span style={{ fontSize: '12px', fontWeight: '800', color: '#fca5a5' }}>
                  ROAD CLOSURE DETOUR ACTIVE
                </span>
              </div>
              <span style={styles.blockedPill}>{blockedRoads.length} Blocked</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', margin: '4px 0' }}>
              <span style={{ fontSize: '26px', fontWeight: '800', color: '#ef4444', fontFamily: 'JetBrains Mono' }}>
                +{addedDelayMin}
              </span>
              <span style={{ fontSize: '12px', color: '#fca5a5', fontWeight: '600' }}>min added detour delay</span>
            </div>

            <p style={{ fontSize: '11px', color: '#fed7aa', marginBottom: '10px', lineHeight: '1.4' }}>
              Dijkstra dynamically re-routed the ambulance around the blocked segment. Network resilience has been updated.
            </p>

            {/* List of blocked roads */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '10px' }}>
              {blockedRoads.map((br, idx) => (
                <div key={idx} style={styles.blockedRoadItem}>
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '240px' }}>
                    <div style={{ fontSize: '11px', fontWeight: '700', color: '#f8fafc' }}>
                      {br.name || 'Road Segment'}
                    </div>
                    <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                      Nodes: {br.u} → {br.v}
                    </div>
                  </div>
                  <button
                    onClick={() => onUnblockRoad && onUnblockRoad(br.u, br.v)}
                    style={styles.unblockBtn}
                    title="Re-open this road segment"
                  >
                    Unblock
                  </button>
                </div>
              ))}
            </div>

            <button onClick={onRestoreRoads} style={styles.restoreNetworkBtn}>
              <RefreshCw size={13} style={{ marginRight: '6px' }} />
              Restore All Blocked Roads
            </button>
          </div>
        )}

        {/* Prompt 5 Flagship: Station Placement & Isochrone Coverage Optimization */}
        <div style={styles.coverageCard}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Compass size={17} color="#a855f7" />
              <span style={{ fontSize: '12px', fontWeight: '800', color: '#e2e8f0', letterSpacing: '0.04em' }}>
                STATION PLACEMENT & COVERAGE
              </span>
            </div>
            <button
              onClick={() => setShowPlacementSection(!showPlacementSection)}
              style={styles.iconMiniBtn}
            >
              {showPlacementSection ? <ChevronDown size={14} color="#94a3b8" /> : <ChevronRight size={14} color="#94a3b8" />}
            </button>
          </div>

          {showPlacementSection && (
            <>
              {/* Mode Toggle Buttons: Current Baseline vs Proposed Optimal */}
              <div style={styles.modeToggleContainer}>
                <button
                  onClick={() => onToggleCoverageMode && onToggleCoverageMode('current')}
                  style={{
                    ...styles.modeToggleBtn,
                    backgroundColor: !isSuggested ? '#2563eb' : '#1e293b',
                    color: !isSuggested ? '#ffffff' : '#94a3b8',
                    border: !isSuggested ? '1px solid #3b82f6' : '1px solid #334155',
                  }}
                >
                  Current 4 Bases
                </button>
                <button
                  onClick={() => onToggleCoverageMode && onToggleCoverageMode('suggested')}
                  disabled={!isSuggested && suggestedStations.length === 0}
                  style={{
                    ...styles.modeToggleBtn,
                    backgroundColor: isSuggested ? '#7c3aed' : '#1e293b',
                    color: isSuggested ? '#ffffff' : '#94a3b8',
                    border: isSuggested ? '1px solid #a855f7' : '1px solid #334155',
                    opacity: !isSuggested && suggestedStations.length === 0 ? 0.4 : 1,
                  }}
                >
                  Proposed ({kAmbulances} Bases)
                </button>
              </div>

              {/* Isochrone Coverage Breakdown in 4 Bands */}
              {bands && (
                <div style={{ marginTop: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: '#cbd5e1' }}>
                      Demand Coverage ({covProps?.total_demand_points || 433} points)
                    </span>
                    <span style={{ fontSize: '11px', color: '#38bdf8', fontFamily: 'JetBrains Mono' }}>
                      Mean: {covProps?.mean_time_min}m · Max: {covProps?.max_time_min}m
                    </span>
                  </div>

                  {/* Segmented Multi-Color Progress Bar */}
                  <div style={styles.segmentedProgressBar}>
                    <div
                      style={{
                        width: `${bands.under_8_min?.pct || 0}%`,
                        backgroundColor: '#10b981',
                        height: '100%',
                      }}
                      title={`< 8 min: ${bands.under_8_min?.pct}% (${bands.under_8_min?.count})`}
                    />
                    <div
                      style={{
                        width: `${bands.between_8_and_15?.pct || 0}%`,
                        backgroundColor: '#f59e0b',
                        height: '100%',
                      }}
                      title={`8 - 15 min: ${bands.between_8_and_15?.pct}% (${bands.between_8_and_15?.count})`}
                    />
                    <div
                      style={{
                        width: `${bands.between_15_and_30?.pct || 0}%`,
                        backgroundColor: '#ef4444',
                        height: '100%',
                      }}
                      title={`15 - 30 min: ${bands.between_15_and_30?.pct}% (${bands.between_15_and_30?.count})`}
                    />
                    <div
                      style={{
                        width: `${bands.over_30_min?.pct || 0}%`,
                        backgroundColor: '#475569',
                        height: '100%',
                      }}
                      title={`> 30 min: ${bands.over_30_min?.pct}% (${bands.over_30_min?.count})`}
                    />
                  </div>

                  {/* Band Legend */}
                  <div style={styles.bandsGrid}>
                    <div style={styles.bandItem}>
                      <div style={{ ...styles.colorDot, backgroundColor: '#10b981' }} />
                      <span style={styles.bandLabel}>&lt; 8m (Golden Hour):</span>
                      <strong style={{ color: '#10b981', fontFamily: 'JetBrains Mono' }}>
                        {bands.under_8_min?.pct}%
                      </strong>
                    </div>

                    <div style={styles.bandItem}>
                      <div style={{ ...styles.colorDot, backgroundColor: '#f59e0b' }} />
                      <span style={styles.bandLabel}>8 - 15 min:</span>
                      <strong style={{ color: '#f59e0b', fontFamily: 'JetBrains Mono' }}>
                        {bands.between_8_and_15?.pct}%
                      </strong>
                    </div>

                    <div style={styles.bandItem}>
                      <div style={{ ...styles.colorDot, backgroundColor: '#ef4444' }} />
                      <span style={styles.bandLabel}>15 - 30 min:</span>
                      <strong style={{ color: '#ef4444', fontFamily: 'JetBrains Mono' }}>
                        {bands.between_15_and_30?.pct}%
                      </strong>
                    </div>

                    <div style={styles.bandItem}>
                      <div style={{ ...styles.colorDot, backgroundColor: '#475569' }} />
                      <span style={styles.bandLabel}>&gt; 30 min:</span>
                      <strong style={{ color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                        {bands.over_30_min?.pct}%
                      </strong>
                    </div>
                  </div>

                  {/* Before / After Comparison Card */}
                  {isSuggested && baselineComp && (
                    <div style={styles.comparisonCard}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                        <CheckCircle2 size={15} color="#10b981" />
                        <span style={{ fontSize: '11px', fontWeight: '800', color: '#10b981' }}>
                          BEFORE / AFTER PLACEMENT COMPARISON
                        </span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#cbd5e1', lineHeight: '1.4' }}>
                        Mean response reduced from <strong>{baselineComp.baseline_mean_time_min}m</strong> to{' '}
                        <strong style={{ color: '#38bdf8' }}>{covProps?.mean_time_min}m</strong> ({' '}
                        <span style={{ color: '#10b981', fontWeight: '700' }}>
                          {baselineComp.mean_time_reduction_min >= 0
                            ? `-${baselineComp.mean_time_reduction_min} min`
                            : `+${Math.abs(baselineComp.mean_time_reduction_min)} min`}
                        </span>{' '}
                        · {baselineComp.mean_time_improvement_pct}%).
                      </div>
                      <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '3px' }}>
                        Golden-hour &lt;8 min coverage improved from{' '}
                        <strong>{baselineComp.baseline_under_8_pct}%</strong> to{' '}
                        <strong style={{ color: '#10b981' }}>{bands.under_8_min?.pct}%</strong> (+
                        {baselineComp.under_8_coverage_gain_pct}% gain).
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Station Location Suggestion Controls */}
              <div style={{ marginTop: '12px', borderTop: '1px solid #334155', paddingTop: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: '700', color: '#f8fafc' }}>
                    Number of Stations (k):
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      onClick={() => setKAmbulances(Math.max(1, kAmbulances - 1))}
                      style={styles.counterBtn}
                    >
                      -
                    </button>
                    <span style={{ fontSize: '14px', fontWeight: '800', color: '#38bdf8', fontFamily: 'JetBrains Mono' }}>
                      {kAmbulances}
                    </span>
                    <button
                      onClick={() => setKAmbulances(Math.min(10, kAmbulances + 1))}
                      style={styles.counterBtn}
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* Algorithm Choice */}
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>
                    DISCRETE FACILITY LOCATION ALGORITHM:
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '4px' }}>
                    <button
                      onClick={() => setPlacementAlgorithm('p_median')}
                      style={{
                        ...styles.algoPillBtn,
                        backgroundColor: placementAlgorithm === 'p_median' ? '#7c3aed' : '#0f172a',
                        color: placementAlgorithm === 'p_median' ? '#ffffff' : '#94a3b8',
                        borderColor: placementAlgorithm === 'p_median' ? '#a855f7' : '#334155',
                      }}
                      title="p-Median: Minimizes average travel time across all demand points (Teitz-Bart Swap Heuristic)"
                    >
                      p-Median (Swap)
                    </button>
                    <button
                      onClick={() => setPlacementAlgorithm('k_center')}
                      style={{
                        ...styles.algoPillBtn,
                        backgroundColor: placementAlgorithm === 'k_center' ? '#7c3aed' : '#0f172a',
                        color: placementAlgorithm === 'k_center' ? '#ffffff' : '#94a3b8',
                        borderColor: placementAlgorithm === 'k_center' ? '#a855f7' : '#334155',
                      }}
                      title="k-Center: Minimizes the maximum bottleneck distance / worst-case radius"
                    >
                      k-Center (Worst)
                    </button>
                    <button
                      onClick={() => setPlacementAlgorithm('1_center')}
                      style={{
                        ...styles.algoPillBtn,
                        backgroundColor: placementAlgorithm === '1_center' ? '#7c3aed' : '#0f172a',
                        color: placementAlgorithm === '1_center' ? '#ffffff' : '#94a3b8',
                        borderColor: placementAlgorithm === '1_center' ? '#a855f7' : '#334155',
                      }}
                      title="1-Center: Computes graph center minimizing vertex eccentricity"
                    >
                      1-Center
                    </button>
                  </div>
                </div>

                <button
                  onClick={() => onSuggestPlacement && onSuggestPlacement(kAmbulances, placementAlgorithm)}
                  disabled={coverageLoading}
                  style={styles.suggestBtn}
                >
                  <Sparkles size={14} style={{ marginRight: '6px' }} />
                  Suggest Station Locations
                </button>
              </div>

              {/* List of Suggested Candidate Stations */}
              {suggestedStations.length > 0 && (
                <div style={{ marginTop: '10px' }}>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: '#c084fc', marginBottom: '6px' }}>
                    Optimal Selected Candidate Junctions:
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {suggestedStations.map((stn, idx) => (
                      <div key={idx} style={styles.suggestedStationRow}>
                        <div style={{ fontSize: '11px', color: '#f8fafc', fontWeight: '600' }}>
                          ⚡ Station #{idx + 1} (Node {stn.node_id})
                        </div>
                        <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                          {stn.lat.toFixed(4)}, {stn.lng.toFixed(4)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Primary Route Telemetry & Emergency Destination Card */}
        {routeData && (activeMode === 'single' || activeMode === 'triage') && (
          <div style={styles.telemetryCard}>
            <div style={styles.cardHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Navigation size={16} color="#38bdf8" />
                <span style={styles.cardTitle}>PRIMARY ROUTE (PLAN A)</span>
              </div>
              <span style={styles.badgeSuccess}>Optimal Dijkstra</span>
            </div>

            {/* Quick Metrics Grid */}
            <div style={styles.metricGrid}>
              <div style={styles.metricItem}>
                <div style={styles.metricLabel}>Total Time</div>
                <div style={styles.metricValue}>
                  {props?.total_time_min} <span style={{ fontSize: '11px', color: '#94a3b8' }}>min</span>
                </div>
                <div style={styles.metricSub}>({props?.total_time_sec}s)</div>
              </div>

              <div style={styles.metricItem}>
                <div style={styles.metricLabel}>Total Distance</div>
                <div style={styles.metricValue}>
                  {props?.total_distance_km} <span style={{ fontSize: '11px', color: '#94a3b8' }}>km</span>
                </div>
                <div style={styles.metricSub}>({props?.total_distance_m}m)</div>
              </div>

              <div style={styles.metricItem}>
                <div style={styles.metricLabel}>Nodes Settled</div>
                <div style={{ ...styles.metricValue, color: '#38bdf8' }}>
                  {props?.nodes_expanded?.toLocaleString()}
                </div>
                <div style={styles.metricSub}>Heap extractions</div>
              </div>
            </div>

            {/* Leg Breakdown */}
            <div style={styles.legSection}>
              {/* Leg 1: Station to Accident */}
              <div style={styles.legCard}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ ...styles.legIcon, backgroundColor: 'rgba(245, 158, 11, 0.2)' }}>
                    <Ambulance size={14} color="#f59e0b" />
                  </div>
                  <div>
                    <div style={styles.legTitle}>Leg 1: Station Dispatch</div>
                    <div style={styles.legSubtitle}>
                      {props?.station?.name || 'Nearest Ambulance Post'}
                    </div>
                  </div>
                </div>
                <div style={styles.legMetrics}>
                  <div style={styles.legMetricMain}>{props?.dispatch_time_min} min</div>
                  <div style={styles.legMetricSub}>{props?.dispatch_distance_km} km</div>
                </div>
              </div>

              {/* Leg 2: Accident to Hospital */}
              <div style={styles.legCard}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ ...styles.legIcon, backgroundColor: 'rgba(16, 185, 129, 0.2)' }}>
                    <Building2 size={14} color="#10b981" />
                  </div>
                  <div>
                    <div style={styles.legTitle}>Leg 2: Hospital Transport</div>
                    <div style={styles.legSubtitle}>
                      {props?.hospital?.name || 'Destination Hospital'}
                    </div>
                  </div>
                </div>
                <div style={styles.legMetrics}>
                  <div style={{ ...styles.legMetricMain, color: '#10b981' }}>
                    {props?.transport_time_min} min
                  </div>
                  <div style={styles.legMetricSub}>{props?.transport_distance_km} km</div>
                </div>
              </div>
            </div>

            {/* Turn order vertices inspection */}
            {props?.turn_order_vertices && (
              <div style={{ marginTop: '12px' }}>
                <button
                  onClick={() => setShowVertexList(!showVertexList)}
                  style={styles.toggleBtn}
                >
                  <Layers size={14} style={{ marginRight: '6px' }} />
                  <span>
                    Turn-Order Vertices ({props.turn_order_vertices.length} junctions)
                  </span>
                  {showVertexList ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>

                {showVertexList && (
                  <div style={styles.vertexBox}>
                    <div style={styles.vertexList}>
                      {props.turn_order_vertices.map((v, i) => (
                        <span key={i} style={styles.vertexPill}>
                          {i === 0
                            ? `Station [${v}]`
                            : i === props.turn_order_vertices.length - 1
                            ? `Hospital [${v}]`
                            : v}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Prompt 3 Flagship: Critical Infrastructure & Graph Resilience Telemetry */}
        {criticalData && critProps && (activeMode === 'single' || activeMode === 'triage') && (
          <div style={styles.resilienceCard}>
            <div style={styles.cardHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldAlert size={16} color="#ef4444" />
                <span style={styles.cardTitle}>NETWORK RESILIENCE SCORE</span>
              </div>
              <span
                style={{
                  ...styles.resilienceBadge,
                  backgroundColor: critProps.badge?.bg_color || critProps.rating_color || '#10b981',
                  color: critProps.badge?.text_color || '#ffffff',
                }}
              >
                {critProps.badge?.label || critProps.rating || 'Resilient'} ({critProps.resilience_score}/100)
              </span>
            </div>

            {/* Score Explanation Callout */}
            <p style={styles.explanationText}>{critProps.explanation}</p>

            {/* Mathematical Formula Component Breakdown */}
            <div style={styles.formulaGrid}>
              <div style={styles.formulaItem}>
                <div style={styles.formulaLabel}>Menger Connectivity</div>
                <div style={styles.formulaValue}>λ = {critProps.components?.lambda_connectivity ?? 1}</div>
                <div style={styles.formulaSub}>
                  L = {critProps.components?.L_score ?? 0} (w: 40%)
                </div>
              </div>

              <div style={styles.formulaItem}>
                <div style={styles.formulaLabel}>Max Detour Ratio</div>
                <div style={styles.formulaValue}>ρ = {critProps.components?.rho_max_detour ?? 1.0}x</div>
                <div style={styles.formulaSub}>
                  D = {critProps.components?.D_score ?? 0} (w: 40%)
                </div>
              </div>

              <div style={styles.formulaItem}>
                <div style={styles.formulaLabel}>Bridge Proportion</div>
                <div style={styles.formulaValue}>
                  {critProps.components?.bridge_length_meters > 0
                    ? `${(
                        (critProps.components.bridge_length_meters /
                          (props?.total_distance_m || 1)) *
                        100
                      ).toFixed(1)}%`
                    : '0%'}
                </div>
                <div style={styles.formulaSub}>
                  C = {critProps.components?.C_score ?? 1.0} (w: 20%)
                </div>
              </div>
            </div>

            {/* Cut Elements Summary */}
            <div style={styles.cutSummary}>
              <div style={styles.cutItem}>
                <span style={styles.cutIconStrict}>■</span>
                <span style={styles.cutText}>Strict Bridges:</span>
                <strong>{critProps.counts?.strict_bridges ?? 0}</strong>
              </div>
              <div style={styles.cutItem}>
                <span style={styles.cutIconSoft}>■</span>
                <span style={styles.cutText}>Soft Bridges (ρ ≥ 1.5):</span>
                <strong>{critProps.counts?.soft_bridges ?? 0}</strong>
              </div>
              <div style={styles.cutItem}>
                <span style={styles.cutIconAP}>●</span>
                <span style={styles.cutText}>Articulation Points:</span>
                <strong>{critProps.counts?.articulation_points ?? 0}</strong>
              </div>
            </div>

            {/* Interactive Soft Bridges List */}
            {critProps.soft_bridges && critProps.soft_bridges.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <button
                  onClick={() => setShowSoftBridgeList(!showSoftBridgeList)}
                  style={styles.toggleBtn}
                >
                  <AlertTriangle size={14} color="#f59e0b" style={{ marginRight: '6px' }} />
                  <span>
                    Soft Bridges & Detour Ratios ({critProps.soft_bridges.length})
                  </span>
                  {showSoftBridgeList ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>

                {showSoftBridgeList && (
                  <div style={styles.softBridgeContainer}>
                    {critProps.soft_bridges.map((sb, idx) => (
                      <div key={idx} style={styles.softBridgeItem}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                          <span style={styles.softBridgeRoad}>
                            {sb.road_name || 'Road Segment'}
                          </span>
                          <span
                            style={{
                              ...styles.detourPill,
                              color: sb.is_disconnected ? '#ef4444' : '#f59e0b',
                            }}
                          >
                            {sb.is_disconnected ? 'DISCONNECTED' : `${sb.detour_ratio}x detour`}
                          </span>
                        </div>
                        <div style={styles.softBridgeMeta}>
                          Edge: ({sb.u} → {sb.v}) · Detour: {sb.detour_time_sec}s (+{sb.detour_delay_sec}s)
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Prompt 4 Flagship: Alternate Emergency Routing (Plan B & Plan C) */}
        {backupData && backupPlans.length > 0 && (activeMode === 'single' || activeMode === 'triage') && (
          <div style={styles.backupCard}>
            <div style={styles.cardHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <GitFork size={16} color="#10b981" />
                <span style={styles.cardTitle}>ALTERNATE BACKUP PLANS (YEN'S K=3)</span>
              </div>
              <span style={styles.badgeSuccess}>K-Shortest Paths</span>
            </div>

            <p style={styles.backupIntroText}>
              Precomputed redundant paths guarantee continuous medical transport in the event of primary road closure or severe congestion.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {backupPlans.map((plan) => (
                <div
                  key={plan.plan_id}
                  style={{
                    ...styles.planCard,
                    borderColor: plan.color,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          width: '12px',
                          height: '12px',
                          borderRadius: '50%',
                          backgroundColor: plan.color,
                          display: 'inline-block',
                        }}
                      />
                      <span style={{ fontSize: '13px', fontWeight: '800', color: '#f8fafc' }}>
                        {plan.name}
                      </span>
                      {plan.is_edge_disjoint && (
                        <span style={styles.disjointBadge}>Edge-Disjoint</span>
                      )}
                    </div>
                    <span style={{ fontSize: '13px', fontWeight: '800', color: plan.color, fontFamily: 'JetBrains Mono' }}>
                      {plan.travel_time_min} min
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '6px' }}>
                    <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                      {plan.distance_km} km · {plan.hops} junctions
                    </span>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        color: plan.time_diff_min === 0 ? '#10b981' : '#f59e0b',
                        fontFamily: 'JetBrains Mono',
                      }}
                    >
                      {plan.time_diff_min === 0 ? 'Baseline (Plan A)' : `+${plan.time_diff_min} min vs Plan A`}
                    </span>
                  </div>

                  {/* Sample street trajectory */}
                  {plan.streets && plan.streets.length > 0 && (
                    <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      Corridor: {plan.streets.slice(0, 3).join(' → ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state prompt if no accident placed */}
        {!accidentLocation && activeMode === 'single' && (
          <div style={styles.emptyPrompt}>
            <span style={{ fontSize: '28px', marginBottom: '8px' }}>🚑</span>
            <div style={{ fontSize: '13px', fontWeight: '700', color: '#f8fafc' }}>
              No Emergency Incident Placed
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px', lineHeight: '1.4' }}>
              Click anywhere along the central Bengaluru corridor to simulate an accident, dispatch the nearest ambulance, and analyze bridge cut resilience.
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: '440px',
    height: '100%',
    backgroundColor: '#0f172a',
    borderRight: '1px solid #1e293b',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    zIndex: 900,
  },
  header: {
    padding: '14px 18px',
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  scrollableContent: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  loadingBadge: {
    fontSize: '11px',
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    fontWeight: '600',
  },
  errorAlert: {
    padding: '10px 12px',
    borderRadius: '6px',
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  operationModeContainer: {
    display: 'flex',
    gap: '6px',
    marginBottom: '8px',
  },
  operationModeBtn: {
    flex: 1,
    padding: '8px 6px',
    borderRadius: '8px',
    fontSize: '11px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.15s ease',
  },
  trafficDivergenceCard: {
    backgroundColor: 'rgba(249, 115, 22, 0.12)',
    borderRadius: '10px',
    border: '1.5px solid #f97316',
    padding: '12px 14px',
    boxShadow: '0 4px 12px rgba(249, 115, 22, 0.2)',
  },
  divergenceMetricsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
    marginTop: '6px',
  },
  triageCard: {
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1.5px solid #10b981',
    padding: '14px 16px',
    boxShadow: '0 4px 14px rgba(16, 185, 129, 0.2)',
  },
  winnerCalloutBox: {
    backgroundColor: 'rgba(251, 191, 36, 0.1)',
    borderRadius: '8px',
    border: '1px solid #fbbf24',
    padding: '10px 12px',
    marginBottom: '10px',
  },
  presetMiniBtn: {
    padding: '2px 7px',
    borderRadius: '4px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#94a3b8',
    fontSize: '10px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  assignmentCard: {
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1.5px solid #db2777',
    padding: '14px 16px',
    boxShadow: '0 4px 14px rgba(219, 39, 119, 0.2)',
  },
  raceCard: {
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1.5px solid #8b5cf6',
    padding: '14px 16px',
    boxShadow: '0 4px 14px rgba(139, 92, 246, 0.2)',
  },
  racePresetBtn: {
    backgroundColor: '#334155',
    color: '#e2e8f0',
    border: '1px solid #475569',
    borderRadius: '6px',
    padding: '6px 10px',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.15s ease',
  },
  raceMetricGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '6px',
  },
  raceMetricBox: {
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    padding: '6px 8px',
    border: '1px solid #334155',
  },
  clearAccidentsBtn: {
    padding: '5px 12px',
    borderRadius: '6px',
    backgroundColor: '#334155',
    color: '#f8fafc',
    border: '1px solid #475569',
    fontSize: '11px',
    fontWeight: '600',
  },
  tableWrapper: {
    overflowX: 'auto',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#0f172a',
  },
  assignmentTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '11px',
  },
  th: {
    backgroundColor: '#1e293b',
    color: '#94a3b8',
    fontWeight: '700',
    padding: '6px 8px',
    textAlign: 'left',
    fontSize: '10px',
    borderBottom: '1px solid #334155',
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '6px 8px',
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
    verticalAlign: 'middle',
    whiteSpace: 'nowrap',
  },
  assignmentEmptyPrompt: {
    padding: '24px 16px',
    textAlign: 'center',
    backgroundColor: '#0f172a',
    borderRadius: '8px',
    border: '1px dashed #475569',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: '10px',
  },
  blockageCard: {
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    border: '1.5px solid #ef4444',
    padding: '12px 14px',
    boxShadow: '0 4px 12px rgba(239, 68, 68, 0.25)',
  },
  blockedPill: {
    fontSize: '10px',
    fontWeight: '700',
    color: '#ffffff',
    backgroundColor: '#ef4444',
    padding: '2px 8px',
    borderRadius: '12px',
  },
  blockedRoadItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '6px 10px',
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    border: '1px solid #334155',
  },
  unblockBtn: {
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    fontSize: '10px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  restoreNetworkBtn: {
    width: '100%',
    padding: '8px 12px',
    borderRadius: '6px',
    backgroundColor: '#334155',
    border: '1px solid #475569',
    color: '#f8fafc',
    fontSize: '11px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  coverageCard: {
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    border: '1px solid #334155',
    padding: '12px 14px',
  },
  iconMiniBtn: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: '2px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modeToggleContainer: {
    display: 'flex',
    gap: '6px',
  },
  modeToggleBtn: {
    flex: 1,
    padding: '6px 8px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  segmentedProgressBar: {
    height: '10px',
    borderRadius: '5px',
    overflow: 'hidden',
    display: 'flex',
    backgroundColor: '#0f172a',
    marginTop: '6px',
  },
  bandsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '6px',
    marginTop: '8px',
  },
  bandItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '11px',
  },
  colorDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  bandLabel: {
    color: '#cbd5e1',
  },
  comparisonCard: {
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    borderRadius: '8px',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    padding: '10px 12px',
    marginTop: '10px',
  },
  counterBtn: {
    width: '24px',
    height: '24px',
    borderRadius: '4px',
    backgroundColor: '#334155',
    color: '#ffffff',
    border: 'none',
    fontWeight: '800',
    fontSize: '14px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  algoPillBtn: {
    padding: '5px 4px',
    borderRadius: '6px',
    border: '1px solid',
    fontSize: '10px',
    fontWeight: '700',
    cursor: 'pointer',
    textAlign: 'center',
  },
  suggestBtn: {
    width: '100%',
    padding: '8px 12px',
    borderRadius: '6px',
    background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
    border: 'none',
    color: 'white',
    fontWeight: '700',
    fontSize: '12px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(168, 85, 247, 0.35)',
    transition: 'all 0.15s ease',
  },
  suggestedStationRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '4px 6px',
    backgroundColor: '#0f172a',
    borderRadius: '4px',
  },
  telemetryCard: {
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    border: '1px solid #334155',
    padding: '12px 14px',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '10px',
  },
  cardTitle: {
    fontSize: '12px',
    fontWeight: '800',
    color: '#e2e8f0',
    letterSpacing: '0.04em',
  },
  badgeSuccess: {
    fontSize: '10px',
    fontWeight: '700',
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    padding: '2px 8px',
    borderRadius: '4px',
    border: '1px solid rgba(16, 185, 129, 0.3)',
  },
  metricGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '8px',
    marginBottom: '12px',
  },
  metricItem: {
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    padding: '8px 10px',
    border: '1px solid #334155',
  },
  metricLabel: {
    fontSize: '10px',
    color: '#94a3b8',
    marginBottom: '2px',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  },
  metricValue: {
    fontSize: '17px',
    fontWeight: '800',
    color: '#f8fafc',
    fontFamily: 'JetBrains Mono, monospace',
  },
  metricSub: {
    fontSize: '10px',
    color: '#64748b',
    marginTop: '1px',
    fontFamily: 'JetBrains Mono, monospace',
  },
  legSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  legCard: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 10px',
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    border: '1px solid #334155',
  },
  legIcon: {
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  legTitle: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  legSubtitle: {
    fontSize: '10px',
    color: '#94a3b8',
  },
  legMetrics: {
    textAlign: 'right',
  },
  legMetricMain: {
    fontSize: '12px',
    fontWeight: '800',
    color: '#f59e0b',
    fontFamily: 'JetBrains Mono, monospace',
  },
  legMetricSub: {
    fontSize: '10px',
    color: '#64748b',
    fontFamily: 'JetBrains Mono, monospace',
  },
  toggleBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '6px 8px',
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    border: '1px solid #334155',
    color: '#94a3b8',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  vertexBox: {
    marginTop: '6px',
    padding: '8px',
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    border: '1px solid #334155',
    maxHeight: '140px',
    overflowY: 'auto',
  },
  vertexList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
  },
  vertexPill: {
    fontSize: '9px',
    padding: '2px 5px',
    borderRadius: '3px',
    backgroundColor: '#1e293b',
    color: '#94a3b8',
    fontFamily: 'JetBrains Mono, monospace',
    border: '1px solid #334155',
  },
  resilienceCard: {
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    border: '1.5px solid #ef4444',
    padding: '12px 14px',
    boxShadow: '0 4px 12px rgba(239, 68, 68, 0.15)',
  },
  resilienceBadge: {
    fontSize: '11px',
    fontWeight: '800',
    padding: '3px 10px',
    borderRadius: '6px',
    letterSpacing: '0.04em',
  },
  explanationText: {
    fontSize: '11px',
    color: '#cbd5e1',
    lineHeight: '1.4',
    marginBottom: '10px',
  },
  formulaGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '6px',
    marginBottom: '10px',
  },
  formulaItem: {
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    padding: '6px 8px',
    border: '1px solid #334155',
    textAlign: 'center',
  },
  formulaLabel: {
    fontSize: '9px',
    color: '#94a3b8',
    marginBottom: '2px',
  },
  formulaValue: {
    fontSize: '13px',
    fontWeight: '800',
    color: '#f8fafc',
    fontFamily: 'JetBrains Mono, monospace',
  },
  formulaSub: {
    fontSize: '9px',
    color: '#64748b',
    marginTop: '2px',
  },
  cutSummary: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 10px',
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    border: '1px solid #334155',
    fontSize: '11px',
  },
  cutItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    color: '#cbd5e1',
  },
  cutIconStrict: {
    color: '#ef4444',
    fontSize: '14px',
  },
  cutIconSoft: {
    color: '#f59e0b',
    fontSize: '14px',
  },
  cutIconAP: {
    color: '#38bdf8',
    fontSize: '14px',
  },
  cutText: {
    color: '#94a3b8',
  },
  softBridgeContainer: {
    marginTop: '6px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    maxHeight: '160px',
    overflowY: 'auto',
  },
  softBridgeItem: {
    padding: '6px 8px',
    backgroundColor: '#0f172a',
    borderRadius: '4px',
    border: '1px solid #334155',
  },
  softBridgeRoad: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  detourPill: {
    fontSize: '10px',
    fontWeight: '800',
    fontFamily: 'JetBrains Mono, monospace',
  },
  softBridgeMeta: {
    fontSize: '10px',
    color: '#94a3b8',
    marginTop: '2px',
  },
  backupCard: {
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    border: '1px solid #10b981',
    padding: '12px 14px',
    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.1)',
  },
  backupIntroText: {
    fontSize: '11px',
    color: '#cbd5e1',
    lineHeight: '1.4',
    marginBottom: '10px',
  },
  planCard: {
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    border: '1px solid',
    padding: '8px 10px',
  },
  disjointBadge: {
    fontSize: '9px',
    fontWeight: '700',
    color: '#a855f7',
    backgroundColor: 'rgba(168, 85, 247, 0.15)',
    padding: '1px 5px',
    borderRadius: '3px',
    border: '1px solid rgba(168, 85, 247, 0.3)',
  },
  emptyPrompt: {
    padding: '30px 16px',
    textAlign: 'center',
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    border: '1px dashed #334155',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
};
