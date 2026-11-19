import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Siren,
  Activity,
  ShieldAlert,
  GitFork,
  Ban,
  Crosshair,
  Layers,
  Ambulance,
  Stethoscope,
  Clock,
  Zap,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  Menu,
  X,
  Compass,
  CheckCircle2,
  AlertTriangle,
  MapPin,
  Cpu,
  BarChart2,
  ShieldCheck,
} from 'lucide-react';
import { PROJECT_CONFIG } from '../config';

const GithubIcon = ({ size = 16, style = {} }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    style={style}
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 30) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (id) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div style={styles.pageWrapper}>
      {/* 
        =======================================================================
        LIGHT STICKY NAVBAR
        =======================================================================
      */}
      <nav
        style={{
          ...styles.navbar,
          boxShadow: scrolled
            ? '0 4px 20px rgba(0, 0, 0, 0.08)'
            : '0 1px 3px rgba(0, 0, 0, 0.05)',
        }}
      >
        <div style={styles.navContainer}>
          {/* Brand Logo & Title */}
          <Link to="/" style={styles.navBrand}>
            <div style={styles.navBrandIcon}>
              <Siren size={20} color="#dc2626" />
            </div>
            <div style={styles.navBrandText}>
              <span style={styles.navBrandTitle}>EMS Bengaluru</span>
              <span style={styles.navBrandSubtitle}>Route Optimizer</span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <div className="nav-links-desktop" style={styles.navLinksDesktop}>
            <button
              onClick={() => scrollToSection('problem')}
              style={styles.navLink}
            >
              The Problem
            </button>
            <button
              onClick={() => scrollToSection('solution')}
              style={styles.navLink}
            >
              Our Solution
            </button>
            <button
              onClick={() => scrollToSection('features')}
              style={styles.navLink}
            >
              Features
            </button>
            <button
              onClick={() => scrollToSection('maths')}
              style={styles.navLink}
            >
              Graph Theory
            </button>
            <button
              onClick={() => scrollToSection('tech')}
              style={styles.navLink}
            >
              Tech Stack
            </button>
          </div>

          {/* CTA Button: Launch Simulator */}
          <div className="nav-cta-desktop" style={styles.navCtaDesktop}>
            <Link to="/app" style={styles.navCtaBtn}>
              <Ambulance size={16} style={{ marginRight: '6px' }} />
              <span>Launch Simulator</span>
            </Link>
          </div>

          {/* Mobile Hamburger Button */}
          <button
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={styles.mobileMenuToggle}
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={24} color="#0f172a" /> : <Menu size={24} color="#0f172a" />}
          </button>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div style={styles.mobileDropdown}>
            <button
              onClick={() => scrollToSection('problem')}
              style={styles.mobileNavLink}
            >
              The Problem
            </button>
            <button
              onClick={() => scrollToSection('solution')}
              style={styles.mobileNavLink}
            >
              Our Solution
            </button>
            <button
              onClick={() => scrollToSection('features')}
              style={styles.mobileNavLink}
            >
              Features
            </button>
            <button
              onClick={() => scrollToSection('maths')}
              style={styles.mobileNavLink}
            >
              Graph Theory
            </button>
            <button
              onClick={() => scrollToSection('tech')}
              style={styles.mobileNavLink}
            >
              Tech Stack
            </button>
            <div style={{ marginTop: '12px', padding: '0 8px' }}>
              <Link
                to="/app"
                style={{ ...styles.navCtaBtn, width: '100%', justifyContent: 'center' }}
                onClick={() => setMobileMenuOpen(false)}
              >
                <Ambulance size={16} style={{ marginRight: '6px' }} />
                <span>Launch Simulator</span>
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* 
        =======================================================================
        SECTION 1: HERO (With stylised non-interactive SVG map background)
        =======================================================================
      */}
      <section style={styles.heroSection}>
        {/* Stylised Non-Interactive SVG Vector Map Background */}
        <div style={styles.heroMapBackground}>
          <svg
            width="100%"
            height="100%"
            viewBox="0 0 1200 800"
            preserveAspectRatio="xMidYMid slice"
            xmlns="http://www.w3.org/2000/svg"
            style={{ opacity: 0.28 }}
          >
            <defs>
              <pattern
                id="hero-grid-pattern"
                width="60"
                height="60"
                patternUnits="userSpaceOnUse"
              >
                <path
                  d="M 60 0 L 0 0 0 60"
                  fill="none"
                  stroke="#334155"
                  strokeWidth="0.8"
                  strokeDasharray="2,4"
                />
              </pattern>
              <linearGradient id="route-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ef4444" stopOpacity="0.9" />
                <stop offset="50%" stopColor="#38bdf8" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#10b981" stopOpacity="0.9" />
              </linearGradient>
            </defs>

            {/* Background Grid Pattern */}
            <rect width="100%" height="100%" fill="url(#hero-grid-pattern)" />

            {/* Stylised Arterial Roads */}
            <path
              d="M -50 220 C 250 200, 420 380, 750 340 C 950 310, 1100 480, 1250 450"
              fill="none"
              stroke="#1e3a8a"
              strokeWidth="5"
            />
            <path
              d="M 150 -50 C 280 250, 360 480, 480 850"
              fill="none"
              stroke="#1e293b"
              strokeWidth="4"
            />
            <path
              d="M 850 -50 C 780 280, 890 520, 820 850"
              fill="none"
              stroke="#1e293b"
              strokeWidth="4"
            />
            <path
              d="M -50 560 C 300 590, 650 510, 1250 620"
              fill="none"
              stroke="#1e3a8a"
              strokeWidth="4"
            />

            {/* Secondary Street Network Web */}
            <path
              d="M 300 120 L 450 240 L 420 380 L 620 440 L 750 340 L 920 310 L 880 180 Z"
              fill="rgba(2, 132, 199, 0.03)"
              stroke="#0284c7"
              strokeWidth="1.5"
              strokeDasharray="4,4"
            />
            <path
              d="M 420 380 L 320 540 L 520 620 L 680 520 L 620 440 Z"
              fill="rgba(16, 185, 129, 0.03)"
              stroke="#10b981"
              strokeWidth="1.5"
              strokeDasharray="4,4"
            />

            {/* Primary Glowing Ambulance Route Polyline */}
            <path
              d="M 180 680 L 320 540 L 420 380 L 620 440 L 750 340 L 890 260"
              fill="none"
              stroke="url(#route-gradient)"
              strokeWidth="3.5"
            />

            {/* Alternative Backup Route Polyline (Detour around choke point) */}
            <path
              d="M 420 380 Q 480 280 620 250 Q 720 220 890 260"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2.5"
              strokeDasharray="6,6"
            />

            {/* Road Network Junction Nodes */}
            {[
              [180, 680, '#10b981', 'Ambulance Station'],
              [320, 540, '#38bdf8', 'Junction'],
              [420, 380, '#ef4444', 'Cut Edge / Bridge'],
              [620, 440, '#38bdf8', 'Junction'],
              [750, 340, '#38bdf8', 'Junction'],
              [890, 260, '#ef4444', 'Hospital Gate'],
              [480, 250, '#94a3b8', 'Bypass Node'],
              [680, 520, '#94a3b8', 'Detour Node'],
              [920, 480, '#94a3b8', 'Periphery Node'],
            ].map(([cx, cy, color, label], idx) => (
              <g key={idx}>
                <circle cx={cx} cy={cy} r="8" fill="none" stroke={color} strokeWidth="1.5" opacity="0.6" />
                <circle cx={cx} cy={cy} r="4" fill={color} />
              </g>
            ))}

            {/* Choke Point Severance Cross Marker */}
            <g transform="translate(420, 380)">
              <circle r="14" fill="rgba(239, 68, 68, 0.2)" stroke="#ef4444" strokeWidth="1.5" />
              <line x1="-6" y1="-6" x2="6" y2="6" stroke="#ef4444" strokeWidth="2.5" />
              <line x1="6" y1="-6" x2="-6" y2="6" stroke="#ef4444" strokeWidth="2.5" />
            </g>
          </svg>
        </div>

        {/* Hero Foreground Content */}
        <div style={styles.heroContentContainer}>
          <div style={styles.heroBadgeRow}>
            <span style={styles.heroAcademicPill}>
              {PROJECT_CONFIG.course} · {PROJECT_CONFIG.module}
            </span>
            <span style={styles.heroCityPill}>
              <MapPin size={12} style={{ marginRight: '4px' }} />
              {PROJECT_CONFIG.city}
            </span>
          </div>

          <h1 style={styles.heroTitle}>{PROJECT_CONFIG.title}</h1>

          <p style={styles.heroSubtitle}>{PROJECT_CONFIG.subtitle}</p>

          <p style={styles.heroDescription}>
            A mathematically rigorous emergency dispatch platform combining real-time shortest path search, Tarjan bridge detection, Yen's k-shortest detour planning, and Hungarian fleet assignment across Bengaluru's 24,242-junction drivable road network.
          </p>

          <div style={styles.heroActionsRow}>
            <Link to="/app" style={styles.heroPrimaryBtn}>
              <Ambulance size={18} style={{ marginRight: '8px' }} />
              <span>Launch Simulator</span>
              <ArrowRight size={16} style={{ marginLeft: '8px' }} />
            </Link>

            <button
              onClick={() => scrollToSection('problem')}
              style={styles.heroSecondaryBtn}
            >
              <span>How it works</span>
              <ChevronDown size={16} style={{ marginLeft: '6px' }} />
            </button>
          </div>

          {/* Key Metric Highlights Strip */}
          <div style={styles.heroStatsGrid}>
            <div style={styles.heroStatItem}>
              <span style={styles.heroStatNumber}>24,242</span>
              <span style={styles.heroStatLabel}>Vertices (Junctions)</span>
            </div>
            <div style={styles.heroStatItem}>
              <span style={styles.heroStatNumber}>62,501</span>
              <span style={styles.heroStatLabel}>Directed Road Edges</span>
            </div>
            <div style={styles.heroStatItem}>
              <span style={styles.heroStatNumber}>7 Hospitals</span>
              <span style={styles.heroStatLabel}>Level-1 & Level-2 Facilities</span>
            </div>
            <div style={styles.heroStatItem}>
              <span style={styles.heroStatNumber}>&lt; 1 ms</span>
              <span style={styles.heroStatLabel}>Optimal Cost Discrepancy</span>
            </div>
          </div>
        </div>
      </section>

      {/* 
        =======================================================================
        SECTION 2: THE PROBLEM
        =======================================================================
      */}
      <section id="problem" style={styles.sectionContainer}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionEyebrow}>THE CRITICAL CHALLENGE</span>
          <h2 style={styles.sectionTitle}>Emergency Dispatch in Dense Urban Networks</h2>
          <p style={styles.sectionDescription}>
            Bengaluru's unique geographic and infrastructural layout creates severe bottlenecks where traditional uncoordinated ambulance routing encounters catastrophic delays.
          </p>
        </div>

        <div style={styles.cardsGridThree}>
          {/* Problem Card 1 */}
          <div style={styles.problemCard}>
            <div style={{ ...styles.cardIconBox, backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
              <Clock size={24} />
            </div>
            <h3 style={styles.cardTitle}>Congested Hospital Corridors</h3>
            <p style={styles.cardText}>
              Arterial corridors servicing major tertiary trauma centers—such as Victoria Hospital in Chamrajpet and Bowring & Lady Curzon Hospital in Shivajinagar—experience severe diurnal peak congestion, dramatically increasing critical golden-hour transit times.
            </p>
          </div>

          {/* Problem Card 2 */}
          <div style={styles.problemCard}>
            <div style={{ ...styles.cardIconBox, backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>
              <ShieldAlert size={24} />
            </div>
            <h3 style={styles.cardTitle}>Single Points of Failure</h3>
            <p style={styles.cardText}>
              Railway underpasses, elevated flyovers, and lake-boundary causeways act as bridge edges in the road graph. When one is blocked by waterlogging, roadwork, or accidents, the primary route is severed, requiring substantial detours.
            </p>
          </div>

          {/* Problem Card 3 */}
          <div style={styles.problemCard}>
            <div style={{ ...styles.cardIconBox, backgroundColor: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
              <Stethoscope size={24} />
            </div>
            <h3 style={styles.cardTitle}>Uncoordinated Facility Overload</h3>
            <p style={styles.cardText}>
              Routing solely to the geometrically nearest hospital without accounting for trauma capability (Level-1 vs Level-2) or emergency ward occupancy causes secondary inter-facility transfers and patient treatment delays.
            </p>
          </div>
        </div>
      </section>

      {/* 
        =======================================================================
        SECTION 3: OUR SOLUTION (4-step flow diagram)
        =======================================================================
      */}
      <section id="solution" style={{ ...styles.sectionContainer, backgroundColor: '#0d1829' }}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionEyebrow}>ALGORITHMIC ARCHITECTURE</span>
          <h2 style={styles.sectionTitle}>Our Solution: 4-Step Graph Pipeline</h2>
          <p style={styles.sectionDescription}>
            An integrated discrete mathematical workflow connecting incident intake to resilient hospital transport.
          </p>
        </div>

        {/* 4-Step Diagram */}
        <div style={styles.solutionFlowContainer}>
          {[
            {
              step: '01',
              title: 'Place Incident',
              desc: 'Incident coordinates are geocoded and snapped to the nearest road junction node in the 24,242-vertex directed road graph.',
              icon: MapPin,
              accent: '#38bdf8',
            },
            {
              step: '02',
              title: 'Find Best Units',
              desc: 'Multi-source Dijkstra finds the nearest ambulance base, while facility scoring evaluates drive time, trauma capability, and hospital load.',
              icon: Ambulance,
              accent: '#10b981',
            },
            {
              step: '03',
              title: 'Check Resilience',
              desc: "Tarjan's low-link algorithm scans the undirected simple graph to identify strict bridges, articulation points, and compute the Resilience Score.",
              icon: ShieldCheck,
              accent: '#f59e0b',
            },
            {
              step: '04',
              title: 'Plan Backups',
              desc: "Yen's algorithm computes loopless Plan B and Plan C detours, while Menger-style max-flow calculates edge-disjoint alternate paths.",
              icon: GitFork,
              accent: '#ef4444',
            },
          ].map((item, index) => {
            const Icon = item.icon;
            return (
              <div key={index} style={styles.flowCard}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span style={{ ...styles.flowStepBadge, backgroundColor: item.accent }}>
                    Step {item.step}
                  </span>
                  <div style={{ ...styles.flowIconBox, color: item.accent }}>
                    <Icon size={20} />
                  </div>
                </div>
                <h4 style={styles.flowCardTitle}>{item.title}</h4>
                <p style={styles.flowCardText}>{item.desc}</p>
                {index < 3 && (
                  <div style={styles.flowConnectorArrow}>
                    <ArrowRight size={18} color="#475569" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* 
        =======================================================================
        SECTION 4: FEATURES GRID (9 cards with graph-theory tags)
        =======================================================================
      */}
      <section id="features" style={styles.sectionContainer}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionEyebrow}>SYSTEM CAPABILITIES</span>
          <h2 style={styles.sectionTitle}>Comprehensive Feature Suite</h2>
          <p style={styles.sectionDescription}>
            Nine production-tested modules combining graph theory, mathematical programming, and geospatial simulation.
          </p>
        </div>

        <div style={styles.featuresGrid}>
          {[
            {
              icon: ShieldAlert,
              title: 'Critical Road Detection & Resilience Score',
              desc: 'Detects cut edges and cut vertices along the ambulance route, rating vulnerability from Resilient to Fragile.',
              tag: 'Bridges & Articulation Points',
              accent: '#ef4444',
            },
            {
              icon: GitFork,
              title: 'Backup Routes',
              desc: 'Generates loopless Plan B, Plan C, and edge-disjoint alternate routes with real-time detour delay indicators.',
              tag: "Yen's K-Shortest & Menger",
              accent: '#38bdf8',
            },
            {
              icon: Ban,
              title: 'Blockage Simulation',
              desc: 'Allows users to click any road segment to simulate closure, triggering immediate dynamic Dijkstra re-routing.',
              tag: 'Dynamic Edge Deletion',
              accent: '#f59e0b',
            },
            {
              icon: Crosshair,
              title: 'Station Placement Optimization',
              desc: 'Evaluates graph eccentricity across 433 demand nodes to solve 1-center, greedy k-center, and swap p-median.',
              tag: 'Eccentricity & K-Center',
              accent: '#10b981',
            },
            {
              icon: Layers,
              title: 'Coverage Heat Map',
              desc: 'Runs multi-source Dijkstra from all stations to visualize 8-min, 15-min, and 30-min emergency response bands.',
              tag: 'Multi-Source Dijkstra',
              accent: '#a855f7',
            },
            {
              icon: Ambulance,
              title: 'Multi-Accident Assignment',
              desc: 'Solves 1-to-1 matching for up to 5 simultaneous incidents using Hungarian min-sum or minimax bottleneck.',
              tag: 'Hungarian Algorithm',
              accent: '#ec4899',
            },
            {
              icon: Stethoscope,
              title: 'Smart Hospital Choice',
              desc: 'Scores candidate facilities using drive time plus trauma level and live emergency ward congestion penalties.',
              tag: 'Multi-Criteria Scoring',
              accent: '#14b8a6',
            },
            {
              icon: Clock,
              title: 'Time-of-Day Traffic',
              desc: 'Applies diurnal congestion multipliers across road classes and medical corridors to reveal peak route divergence.',
              tag: 'Dynamic Edge Weights',
              accent: '#f97316',
            },
            {
              icon: Zap,
              title: 'Dijkstra vs A* Race',
              desc: 'Compares uniform-cost expansion against goal-directed search with an admissible speed-bounded heuristic.',
              tag: 'Admissible A* Search',
              accent: '#fbbf24',
            },
          ].map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <div key={idx} style={styles.featureCard}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ ...styles.cardIconBox, backgroundColor: `${feat.accent}20`, color: feat.accent }}>
                    <Icon size={20} />
                  </div>
                  <span style={styles.conceptTag}>{feat.tag}</span>
                </div>
                <h4 style={styles.featureTitle}>{feat.title}</h4>
                <p style={styles.featureDesc}>{feat.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* 
        =======================================================================
        SECTION 5: MATHS BEHIND IT (Compact Table)
        =======================================================================
      */}
      <section id="maths" style={{ ...styles.sectionContainer, backgroundColor: '#0d1829' }}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionEyebrow}>THEORETICAL FOUNDATIONS</span>
          <h2 style={styles.sectionTitle}>The Mathematics Behind the System</h2>
          <p style={styles.sectionDescription}>
            Every route calculation, facility score, and fleet allocation is grounded in discrete mathematics and graph theory.
          </p>
        </div>

        <div style={styles.tableCard}>
          <div style={styles.tableScrollWrapper}>
            <table style={styles.mathTable}>
              <thead>
                <tr style={styles.mathTableHeader}>
                  <th style={styles.mathTh}>Mathematical Concept</th>
                  <th style={styles.mathTh}>Formal Formulation</th>
                  <th style={styles.mathTh}>Application in System</th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    concept: "Dijkstra's Algorithm",
                    formula: 'd(v) = min_{(u, v) in E} { d(u) + w(u, v) } with binary min-heap',
                    use: 'Single-source emergency transit time minimization & coverage bands',
                  },
                  {
                    concept: 'A* Search & Admissibility',
                    formula: 'f(u) = g(u) + h(u), h(u) = d_haversine(u, t) / v_max <= t*(u, t)',
                    use: 'Goal-directed routing with 33%+ node pruning & identical costs',
                  },
                  {
                    concept: "Tarjan's Low-Link DFS",
                    formula: 'low[u] = min(disc[u], low[w], disc[v]) via iterative DFS stack',
                    use: 'O(V + E) detection of strict bridge roads and critical cut vertices',
                  },
                  {
                    concept: "Menger's Theorem & Max-Flow",
                    formula: 'lambda(s, t) = min s-t edge cut = max edge-disjoint paths',
                    use: 'Topological route robustness and resilience scoring metric L',
                  },
                  {
                    concept: "Yen's K-Shortest Paths",
                    formula: 'Iterative deviation from root path with temporary edge bans',
                    use: 'Generation of loopless alternative Plans B and C for detours',
                  },
                  {
                    concept: 'Graph Eccentricity & Center',
                    formula: 'ecc(u) = max_{v in D} d(u, v), C(G) = argmin_u ecc(u)',
                    use: 'Optimal 1-center location for single ambulance depot',
                  },
                  {
                    concept: 'K-Center & P-Median',
                    formula: 'K-Center: min max d(u, v) | P-Median: min sum d(u, v)',
                    use: 'Greedy minimax & swap-based average-time multi-station placement',
                  },
                  {
                    concept: 'Hungarian Algorithm',
                    formula: 'Primal-dual Kuhn-Munkres bipartite matching on cost matrix in O(n³)',
                    use: 'Optimal multi-incident ambulance fleet dispatch minimizing total time',
                  },
                  {
                    concept: 'Bottleneck Assignment',
                    formula: 'min_pi max_i c(i, pi(i)) via binary threshold search',
                    use: 'Minimizing the maximum single patient wait time across all incidents',
                  },
                  {
                    concept: "Euler's Handshake Lemma",
                    formula: 'sum_{v in V} deg(v) = 2 |E|, strictly verified on graph build',
                    use: 'Topological sanity verification of the 62,501-edge Bengaluru graph',
                  },
                ].map((row, idx) => (
                  <tr key={idx} style={styles.mathTr}>
                    <td style={styles.mathTdConcept}>
                      <span style={{ fontWeight: '700', color: '#f8fafc' }}>{row.concept}</span>
                    </td>
                    <td style={styles.mathTdFormula}>
                      <code style={styles.mathCode}>{row.formula}</code>
                    </td>
                    <td style={styles.mathTdUse}>{row.use}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 
        =======================================================================
        SECTION 6: TECH STACK STRIP
        =======================================================================
      */}
      <section id="tech" style={styles.sectionContainer}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionEyebrow}>SYSTEM ARCHITECTURE</span>
          <h2 style={styles.sectionTitle}>Built with Industry-Standard Open Technologies</h2>
          <p style={styles.sectionDescription}>
            Engineered for high-throughput discrete mathematical processing and responsive spatial rendering.
          </p>
        </div>

        <div style={styles.techStripGrid}>
          {[
            { name: 'Python', role: 'Algorithm & Optimization Engine', desc: 'Custom Dijkstra, A*, Tarjan, Yen & SciPy Hungarian solvers', badge: 'v3.12' },
            { name: 'NetworkX', role: 'Graph Data Structures', desc: 'Directed MultiDiGraph & Undirected simple topological modeling', badge: 'v3.3' },
            { name: 'OSMnx', role: 'Geospatial Road Ingestion', desc: 'OpenStreetMap drivable network extraction & edge attribute caching', badge: 'v1.9' },
            { name: 'FastAPI', role: 'REST API & GeoJSON Service', desc: 'Asynchronous backend delivering RFC 7946 standardized GeoJSON', badge: 'v0.115' },
            { name: 'React', role: 'Reactive Frontend Architecture', desc: 'Component-driven user interface with real-time state management', badge: 'v18.3' },
            { name: 'Leaflet', role: 'Interactive Geospatial Mapping', desc: 'Hardware-accelerated 60fps Canvas exploration rendering', badge: 'v1.9' },
          ].map((tech, idx) => (
            <div key={idx} style={styles.techCard}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={styles.techName}>{tech.name}</span>
                <span style={styles.techBadge}>{tech.badge}</span>
              </div>
              <div style={styles.techRole}>{tech.role}</div>
              <div style={styles.techDesc}>{tech.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 
        =======================================================================
        CALL TO ACTION BANNER (Before footer)
        =======================================================================
      */}
      <section style={styles.ctaBannerSection}>
        <div style={styles.ctaBannerCard}>
          <div style={{ maxWidth: '640px' }}>
            <h3 style={styles.ctaTitle}>Ready to Test Bengaluru's Emergency Route Network?</h3>
            <p style={styles.ctaText}>
              Launch the interactive simulator to place emergency incidents, inspect critical bridges, simulate road closures, and watch Dijkstra and A* race in real time.
            </p>
          </div>
          <Link to="/app" style={styles.ctaBannerBtn}>
            <Ambulance size={18} style={{ marginRight: '8px' }} />
            <span>Launch Simulator</span>
            <ArrowRight size={16} style={{ marginLeft: '8px' }} />
          </Link>
        </div>
      </section>

      {/* 
        =======================================================================
        SECTION 7: FOOTER
        =======================================================================
      */}
      <footer style={styles.footer}>
        <div style={styles.footerContainer}>
          <div style={styles.footerTopRow}>
            {/* Project Academic Header */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <Siren size={18} color="#dc2626" />
                <span style={styles.footerBrandTitle}>{PROJECT_CONFIG.title}</span>
              </div>
              <p style={styles.footerAcademicBadge}>
                {PROJECT_CONFIG.course} · {PROJECT_CONFIG.projectType} · {PROJECT_CONFIG.module}
              </p>
              <p style={styles.footerCityNote}>
                Study Area: Central Bengaluru Emergency Corridors (Jhelum / Chamrajpet / Shivajinagar / Malleswaram)
              </p>
            </div>

            {/* GitHub Repository Link */}
            <div>
              <a
                href={PROJECT_CONFIG.githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={styles.footerGithubBtn}
              >
                <GithubIcon size={16} style={{ marginRight: '8px' }} />
                <span>View on GitHub</span>
                <ExternalLink size={12} style={{ marginLeft: '6px' }} />
              </a>
            </div>
          </div>

          {/* Team Members Placeholders Grid */}
          <div style={styles.footerTeamSection}>
            <div style={styles.footerSectionHeader}>PROJECT TEAM & CONTRIBUTORS</div>
            <div style={styles.footerTeamGrid}>
              {PROJECT_CONFIG.teamMembers.map((member, idx) => (
                <div key={idx} style={styles.teamMemberCard}>
                  <div style={styles.teamMemberName}>{member.name}</div>
                  <div style={styles.teamMemberRole}>{member.role}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Copyright & Academic Notice */}
          <div style={styles.footerBottomRow}>
            <span>
              &copy; 2026 Emergency Ambulance Route Optimization System. Built for academic research and discrete mathematics demonstration.
            </span>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <Link to="/app" style={styles.footerLink}>Simulator</Link>
              <button onClick={() => scrollToSection('problem')} style={styles.footerLinkBtn}>The Problem</button>
              <button onClick={() => scrollToSection('maths')} style={styles.footerLinkBtn}>Mathematics</button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

// Inline Styles for Responsive, Clean, Deep Navy Emergency Services Theme
const styles = {
  pageWrapper: {
    minHeight: '100vh',
    width: '100%',
    backgroundColor: '#0a192f',
    color: '#f8fafc',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    display: 'flex',
    flexDirection: 'column',
    overflowX: 'hidden',
  },

  /* 
    ===========================================================================
    LIGHT STICKY NAVBAR
    ===========================================================================
  */
  navbar: {
    position: 'sticky',
    top: 0,
    zIndex: 1000,
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    transition: 'box-shadow 0.2s ease',
  },
  navContainer: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '12px 24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  navBrand: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    textDecoration: 'none',
  },
  navBrandIcon: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    backgroundColor: '#fee2e2',
    border: '1px solid #fca5a5',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  navBrandText: {
    display: 'flex',
    flexDirection: 'column',
  },
  navBrandTitle: {
    fontSize: '15px',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.02em',
    lineHeight: '1.2',
  },
  navBrandSubtitle: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#dc2626',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  navLinksDesktop: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
    '@media (max-width: 900px)': {
      display: 'none',
    },
  },
  navLink: {
    background: 'none',
    border: 'none',
    fontSize: '13px',
    fontWeight: '600',
    color: '#475569',
    cursor: 'pointer',
    padding: '6px 4px',
    transition: 'color 0.15s ease',
  },
  navCtaDesktop: {
    display: 'flex',
    alignItems: 'center',
  },
  navCtaBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '700',
    textDecoration: 'none',
    boxShadow: '0 2px 8px rgba(220, 38, 38, 0.25)',
    transition: 'all 0.15s ease',
  },
  mobileMenuToggle: {
    display: 'none',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '4px',
  },
  mobileDropdown: {
    backgroundColor: '#ffffff',
    borderTop: '1px solid #e2e8f0',
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  mobileNavLink: {
    background: 'none',
    border: 'none',
    textAlign: 'left',
    fontSize: '14px',
    fontWeight: '600',
    color: '#1e293b',
    padding: '8px 0',
    cursor: 'pointer',
  },

  /* 
    ===========================================================================
    HERO SECTION
    ===========================================================================
  */
  heroSection: {
    position: 'relative',
    backgroundColor: '#0a192f',
    padding: '70px 24px 80px',
    overflow: 'hidden',
    borderBottom: '1px solid #1e293b',
  },
  heroMapBackground: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: 1,
  },
  heroContentContainer: {
    position: 'relative',
    zIndex: 2,
    maxWidth: '1080px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  heroBadgeRow: {
    display: 'flex',
    gap: '10px',
    marginBottom: '18px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  heroAcademicPill: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    borderRadius: '20px',
    padding: '4px 12px',
    letterSpacing: '0.02em',
  },
  heroCityPill: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#f8fafc',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '20px',
    padding: '4px 12px',
    display: 'flex',
    alignItems: 'center',
  },
  heroTitle: {
    fontSize: 'clamp(28px, 5vw, 46px)',
    fontWeight: '900',
    color: '#ffffff',
    lineHeight: '1.15',
    marginBottom: '16px',
    maxWidth: '920px',
    letterSpacing: '-0.03em',
  },
  heroSubtitle: {
    fontSize: 'clamp(16px, 2.5vw, 20px)',
    fontWeight: '600',
    color: '#94a3b8',
    lineHeight: '1.4',
    marginBottom: '20px',
    maxWidth: '780px',
  },
  heroDescription: {
    fontSize: '14px',
    color: '#cbd5e1',
    lineHeight: '1.6',
    maxWidth: '720px',
    marginBottom: '32px',
  },
  heroActionsRow: {
    display: 'flex',
    gap: '14px',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginBottom: '50px',
  },
  heroPrimaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    padding: '12px 26px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '700',
    textDecoration: 'none',
    boxShadow: '0 4px 16px rgba(220, 38, 38, 0.4)',
    transition: 'all 0.15s ease',
  },
  heroSecondaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    padding: '12px 22px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '700',
    border: '1px solid #334155',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  heroStatsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '16px',
    width: '100%',
    maxWidth: '900px',
    padding: '16px 20px',
    backgroundColor: 'rgba(15, 23, 42, 0.75)',
    backdropFilter: 'blur(8px)',
    borderRadius: '12px',
    border: '1px solid #1e293b',
  },
  heroStatItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '2px',
  },
  heroStatNumber: {
    fontSize: '22px',
    fontWeight: '800',
    color: '#38bdf8',
    fontFamily: "'JetBrains Mono', monospace",
  },
  heroStatLabel: {
    fontSize: '11px',
    color: '#94a3b8',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },

  /* 
    ===========================================================================
    SHARED SECTION STYLES
    ===========================================================================
  */
  sectionContainer: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '70px 24px',
    width: '100%',
  },
  sectionHeader: {
    textAlign: 'center',
    maxWidth: '760px',
    margin: '0 auto 46px',
  },
  sectionEyebrow: {
    fontSize: '11px',
    fontWeight: '800',
    color: '#dc2626',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    display: 'inline-block',
    marginBottom: '8px',
  },
  sectionTitle: {
    fontSize: 'clamp(22px, 3.5vw, 32px)',
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: '-0.02em',
    marginBottom: '12px',
    lineHeight: '1.25',
  },
  sectionDescription: {
    fontSize: '14px',
    color: '#94a3b8',
    lineHeight: '1.6',
  },

  /* 
    ===========================================================================
    THE PROBLEM CARDS
    ===========================================================================
  */
  cardsGridThree: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '24px',
  },
  problemCard: {
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    border: '1px solid #1e293b',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
  },
  cardIconBox: {
    width: '46px',
    height: '46px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '16px',
  },
  cardTitle: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: '10px',
  },
  cardText: {
    fontSize: '13px',
    color: '#94a3b8',
    lineHeight: '1.6',
  },

  /* 
    ===========================================================================
    OUR SOLUTION 4-STEP FLOW
    ===========================================================================
  */
  solutionFlowContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '18px',
    position: 'relative',
  },
  flowCard: {
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    border: '1px solid #1e293b',
    padding: '20px',
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
  },
  flowStepBadge: {
    fontSize: '11px',
    fontWeight: '800',
    color: '#ffffff',
    padding: '3px 8px',
    borderRadius: '4px',
    letterSpacing: '0.04em',
  },
  flowIconBox: {
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  flowCardTitle: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: '8px',
  },
  flowCardText: {
    fontSize: '12px',
    color: '#94a3b8',
    lineHeight: '1.55',
  },
  flowConnectorArrow: {
    position: 'absolute',
    right: '-10px',
    top: '50%',
    transform: 'translateY(-50%)',
    display: 'none', // Shown via CSS breakpoints if desired
  },

  /* 
    ===========================================================================
    FEATURES GRID (9 Cards)
    ===========================================================================
  */
  featuresGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))',
    gap: '20px',
  },
  featureCard: {
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    border: '1px solid #1e293b',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
  },
  conceptTag: {
    fontSize: '10px',
    fontWeight: '700',
    color: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    borderRadius: '4px',
    padding: '2px 6px',
    letterSpacing: '0.02em',
  },
  featureTitle: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: '6px',
  },
  featureDesc: {
    fontSize: '12px',
    color: '#94a3b8',
    lineHeight: '1.55',
  },

  /* 
    ===========================================================================
    MATHS TABLE
    ===========================================================================
  */
  tableCard: {
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    border: '1px solid #1e293b',
    overflow: 'hidden',
  },
  tableScrollWrapper: {
    overflowX: 'auto',
  },
  mathTable: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
    fontSize: '12px',
  },
  mathTableHeader: {
    backgroundColor: '#1e293b',
    borderBottom: '1px solid #334155',
  },
  mathTh: {
    padding: '12px 16px',
    fontWeight: '700',
    color: '#f8fafc',
    letterSpacing: '0.02em',
    whiteSpace: 'nowrap',
  },
  mathTr: {
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
  },
  mathTdConcept: {
    padding: '12px 16px',
    whiteSpace: 'nowrap',
  },
  mathTdFormula: {
    padding: '12px 16px',
    color: '#cbd5e1',
  },
  mathCode: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    backgroundColor: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid #334155',
    padding: '2px 6px',
    borderRadius: '4px',
    color: '#38bdf8',
    display: 'inline-block',
  },
  mathTdUse: {
    padding: '12px 16px',
    color: '#94a3b8',
    lineHeight: '1.45',
  },

  /* 
    ===========================================================================
    TECH STACK STRIP
    ===========================================================================
  */
  techStripGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '16px',
  },
  techCard: {
    backgroundColor: '#0f172a',
    borderRadius: '10px',
    border: '1px solid #1e293b',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
  },
  techName: {
    fontSize: '14px',
    fontWeight: '800',
    color: '#f8fafc',
  },
  techBadge: {
    fontSize: '10px',
    fontWeight: '700',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderRadius: '4px',
    padding: '1px 5px',
    border: '1px solid rgba(16, 185, 129, 0.3)',
  },
  techRole: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#38bdf8',
    marginBottom: '4px',
  },
  techDesc: {
    fontSize: '11px',
    color: '#64748b',
    lineHeight: '1.4',
  },

  /* 
    ===========================================================================
    CTA BANNER
    ===========================================================================
  */
  ctaBannerSection: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px 60px',
    width: '100%',
  },
  ctaBannerCard: {
    backgroundColor: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
    border: '1.5px solid #dc2626',
    borderRadius: '16px',
    padding: '36px 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '24px',
    flexWrap: 'wrap',
    boxShadow: '0 8px 30px rgba(220, 38, 38, 0.15)',
  },
  ctaTitle: {
    fontSize: '20px',
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: '8px',
  },
  ctaText: {
    fontSize: '13px',
    color: '#94a3b8',
    lineHeight: '1.5',
  },
  ctaBannerBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    padding: '12px 24px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '700',
    textDecoration: 'none',
    boxShadow: '0 4px 14px rgba(220, 38, 38, 0.35)',
    whiteSpace: 'nowrap',
  },

  /* 
    ===========================================================================
    FOOTER
    ===========================================================================
  */
  footer: {
    backgroundColor: '#07101e',
    borderTop: '1px solid #1e293b',
    padding: '48px 24px 30px',
    marginTop: 'auto',
  },
  footerContainer: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '30px',
  },
  footerTopRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: '20px',
  },
  footerBrandTitle: {
    fontSize: '15px',
    fontWeight: '800',
    color: '#ffffff',
  },
  footerAcademicBadge: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#38bdf8',
    marginBottom: '4px',
  },
  footerCityNote: {
    fontSize: '11px',
    color: '#64748b',
  },
  footerGithubBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    padding: '8px 14px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    textDecoration: 'none',
    border: '1px solid #334155',
  },
  footerTeamSection: {
    borderTop: '1px solid #1e293b',
    paddingTop: '20px',
  },
  footerSectionHeader: {
    fontSize: '11px',
    fontWeight: '800',
    color: '#94a3b8',
    letterSpacing: '0.06em',
    marginBottom: '14px',
  },
  footerTeamGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '12px',
  },
  teamMemberCard: {
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    padding: '10px 14px',
    border: '1px solid #1e293b',
  },
  teamMemberName: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  teamMemberRole: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '2px',
  },
  footerBottomRow: {
    borderTop: '1px solid rgba(51, 65, 85, 0.5)',
    paddingTop: '20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '12px',
    fontSize: '11px',
    color: '#64748b',
  },
  footerLink: {
    color: '#38bdf8',
    textDecoration: 'none',
    fontWeight: '600',
  },
  footerLinkBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: '11px',
  },
};
