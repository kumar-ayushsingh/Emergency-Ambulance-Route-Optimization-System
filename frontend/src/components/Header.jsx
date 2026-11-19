import React from 'react';
import { Link } from 'react-router-dom';
import {
  Siren,
  Activity,
  ShieldCheck,
  RotateCcw,
  RefreshCw,
  Sun,
  Moon,
  Car,
  Clock,
  Zap,
  Home,
} from 'lucide-react';

export default function Header({
  graphInfo,
  onReset,
  onRestore,
  blockedCount = 0,
  loading,
  // Time-of-Day Traffic Controls
  timeOfDay = 'off_peak',
  timeHour = 12,
  onTimeChange,
  onTriggerTrafficComparison,
  trafficComparisonActive = false,
}) {
  const PERIODS = [
    { id: 'night', label: 'Night', mult: '0.8x', hour: 2, icon: Moon, color: '#a855f7' },
    { id: 'off_peak', label: 'Off-Peak', mult: '1.0x', hour: 12, icon: Sun, color: '#38bdf8' },
    { id: 'morning_peak', label: 'Morning Peak', mult: '1.6x', hour: 9, icon: Car, color: '#f59e0b' },
    { id: 'evening_peak', label: 'Evening Peak', mult: '1.8x', hour: 18, icon: Car, color: '#ef4444' },
  ];

  const currentPeriod = PERIODS.find((p) => p.id === timeOfDay) || PERIODS[1];

  const formatHour = (h) => {
    const pad = (n) => String(n).padStart(2, '0');
    const ampm = h >= 12 ? 'PM' : 'AM';
    const displayH = h % 12 === 0 ? 12 : h % 12;
    return `${pad(displayH)}:00 ${ampm}`;
  };

  const handleSliderChange = (e) => {
    const h = parseInt(e.target.value, 10);
    // Map hour to period:
    // 23:00 - 06:00 -> night
    // 08:30 - 11:00 -> morning_peak
    // 17:00 - 20:30 -> evening_peak
    // otherwise -> off_peak
    let period = 'off_peak';
    if (h >= 23 || h < 6) {
      period = 'night';
    } else if (h >= 8 && h <= 11) {
      period = 'morning_peak';
    } else if (h >= 17 && h <= 20) {
      period = 'evening_peak';
    } else {
      period = 'off_peak';
    }

    if (onTimeChange) {
      onTimeChange(period, h);
    }
  };

  const handlePeriodClick = (p) => {
    if (onTimeChange) {
      onTimeChange(p.id, p.hour);
    }
  };

  return (
    <header style={styles.header}>
      <div style={styles.brandContainer}>
        <div style={styles.iconBadge}>
          <Siren size={22} color="#ef4444" />
        </div>
        <div>
          <h1 style={styles.title}>Emergency Ambulance Route Optimization System</h1>
          <p style={styles.subtitle}>
            Bengaluru Emergency Corridor · Discrete Mathematics (Module 4: Graph Theory)
          </p>
        </div>
      </div>

      {/* Center: Time-of-Day Traffic Congestion Slider & Controls */}
      <div style={styles.trafficSection}>
        <div style={styles.trafficHeaderRow}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Clock size={13} color="#38bdf8" />
            <span style={{ fontSize: '11px', fontWeight: '700', color: '#94a3b8' }}>
              TIME-OF-DAY TRAFFIC MODEL:
            </span>
            <span style={{ ...styles.timeBadge, backgroundColor: currentPeriod.color + '22', color: currentPeriod.color }}>
              {formatHour(timeHour)} ({currentPeriod.label} · {currentPeriod.mult})
            </span>
          </div>

          <button
            onClick={onTriggerTrafficComparison}
            disabled={loading}
            style={{
              ...styles.divergenceBtn,
              backgroundColor: trafficComparisonActive ? '#f97316' : '#1e293b',
              borderColor: trafficComparisonActive ? '#ea580c' : '#475569',
              color: trafficComparisonActive ? '#ffffff' : '#f97316',
            }}
            title="Demonstrate route divergence where peak arterial congestion causes optimal path to detour via bypass streets"
          >
            <Zap size={13} style={{ marginRight: '4px' }} />
            {trafficComparisonActive ? 'Peak Divergence Active' : 'Compare Off-Peak vs Peak'}
          </button>
        </div>

        <div style={styles.trafficControlsRow}>
          {/* Quick preset buttons */}
          <div style={styles.periodPillGroup}>
            {PERIODS.map((p) => {
              const active = p.id === timeOfDay;
              const Icon = p.icon;
              return (
                <button
                  key={p.id}
                  onClick={() => handlePeriodClick(p)}
                  disabled={loading}
                  style={{
                    ...styles.periodBtn,
                    backgroundColor: active ? p.color : '#0f172a',
                    color: active ? '#ffffff' : '#94a3b8',
                    borderColor: active ? p.color : '#334155',
                    fontWeight: active ? '700' : '500',
                  }}
                >
                  <Icon size={11} style={{ marginRight: '4px' }} />
                  {p.label} <span style={{ opacity: 0.85, fontSize: '10px' }}>({p.mult})</span>
                </button>
              );
            })}
          </div>

          {/* 24h Slider */}
          <div style={styles.sliderWrapper}>
            <input
              type="range"
              min="0"
              max="23"
              step="1"
              value={timeHour}
              onChange={handleSliderChange}
              disabled={loading}
              style={styles.timeSlider}
              title={`Drag to simulate hour of day: ${formatHour(timeHour)}`}
            />
          </div>
        </div>
      </div>

      {/* Right section: Graph topology metrics and resets */}
      <div style={styles.rightSection}>
        {graphInfo && (
          <div style={styles.graphStats}>
            <div style={styles.statPill}>
              <span style={styles.statLabel}>|V|:</span>
              <span style={styles.statValue}>{graphInfo.vertices?.toLocaleString()}</span>
            </div>
            <div style={styles.statPill}>
              <span style={styles.statLabel}>|E|:</span>
              <span style={styles.statValue}>{graphInfo.directed_edges?.toLocaleString()}</span>
            </div>
            <div style={{ ...styles.statPill, borderColor: '#10b981', background: 'rgba(16, 185, 129, 0.1)' }}>
              <ShieldCheck size={14} color="#10b981" style={{ marginRight: 4 }} />
              <span style={{ ...styles.statValue, color: '#10b981' }}>Handshake Lemma Verified</span>
            </div>
          </div>
        )}

        {blockedCount > 0 && (
          <button
            onClick={onRestore}
            disabled={loading}
            style={styles.restoreBtn}
            title="Restore all blocked roads"
          >
            <RefreshCw size={13} style={{ marginRight: 5 }} />
            Restore ({blockedCount})
          </button>
        )}

        <button
          onClick={onReset}
          disabled={loading}
          style={styles.resetBtn}
          title="Clear current accident and route"
        >
          <RotateCcw size={14} style={{ marginRight: 5 }} />
          Reset
        </button>

        <Link
          to="/"
          style={styles.homeLinkBtn}
          title="Return to Landing Page"
        >
          <Home size={13} style={{ marginRight: 5 }} />
          Home
        </Link>
      </div>
    </header>
  );
}

const styles = {
  header: {
    height: '76px',
    backgroundColor: '#0b1120',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    zIndex: 1000,
    gap: '12px',
  },
  brandContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexShrink: 0,
  },
  iconBadge: {
    width: '38px',
    height: '38px',
    borderRadius: '10px',
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#f8fafc',
    letterSpacing: '-0.01em',
  },
  subtitle: {
    fontSize: '10px',
    color: '#94a3b8',
    marginTop: '1px',
  },
  trafficSection: {
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '6px 10px',
    gap: '5px',
    minWidth: '450px',
  },
  trafficHeaderRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  timeBadge: {
    fontSize: '10px',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '4px',
    border: '1px solid currentColor',
    fontFamily: 'JetBrains Mono, monospace',
  },
  divergenceBtn: {
    display: 'flex',
    alignItems: 'center',
    padding: '3px 8px',
    borderRadius: '5px',
    border: '1px solid',
    fontSize: '11px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  trafficControlsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  periodPillGroup: {
    display: 'flex',
    gap: '4px',
  },
  periodBtn: {
    display: 'flex',
    alignItems: 'center',
    padding: '3px 7px',
    borderRadius: '4px',
    border: '1px solid',
    fontSize: '10px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  sliderWrapper: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
  },
  timeSlider: {
    width: '100%',
    cursor: 'pointer',
    accentColor: '#38bdf8',
    height: '4px',
  },
  rightSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexShrink: 0,
  },
  graphStats: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  statPill: {
    display: 'flex',
    alignItems: 'center',
    padding: '4px 8px',
    borderRadius: '6px',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    fontSize: '11px',
  },
  statLabel: {
    color: '#94a3b8',
    marginRight: '4px',
    fontFamily: 'JetBrains Mono, monospace',
  },
  statValue: {
    color: '#f1f5f9',
    fontWeight: '600',
    fontFamily: 'JetBrains Mono, monospace',
  },
  restoreBtn: {
    display: 'flex',
    alignItems: 'center',
    padding: '5px 10px',
    borderRadius: '6px',
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    fontSize: '11px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  resetBtn: {
    display: 'flex',
    alignItems: 'center',
    padding: '5px 10px',
    borderRadius: '6px',
    backgroundColor: '#1e293b',
    border: '1px solid #475569',
    color: '#e2e8f0',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  homeLinkBtn: {
    display: 'flex',
    alignItems: 'center',
    padding: '5px 10px',
    borderRadius: '6px',
    backgroundColor: '#0284c7',
    border: '1px solid #38bdf8',
    color: '#ffffff',
    fontSize: '11px',
    fontWeight: '700',
    textDecoration: 'none',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
};
