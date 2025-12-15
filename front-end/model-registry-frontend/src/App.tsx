import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import IngestPackage from './components/IngestPackage';
import SearchArtifacts from './components/SearchArtifacts';
import HealthDashboard from './components/HealthDashboard';
import { modelRegistryAPI } from './services/api';
import './App.css';

const App: React.FC = () => {
  // Authenticate on app load
  useEffect(() => {
    const authenticate = async () => {
      try {
        await modelRegistryAPI.authenticate(
          'ece30861defaultadminuser',
          'correcthorsebatterystaple123(!__+@**(A\'";DROP TABLE packages;'
        );
        console.log('Authentication successful');
      } catch (error) {
        console.error('Failed to authenticate:', error);
      }
    };
    authenticate();
  }, []);

  return (
    <Router>
      <div className="app">
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        <nav className="navbar" aria-label="Main navigation" role="navigation">
          <div className="nav-container">
            <h1 className="logo">
              <Link to="/" aria-label="Model Registry home">
                Model Registry
              </Link>
            </h1>
            <ul className="nav-links" role="list">
              <li>
                <NavLink
                  to="/"
                  className={({ isActive }) => isActive ? 'active' : ''}
                  aria-label="Search artifacts"
                >
                  Search
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/ingest"
                  className={({ isActive }) => isActive ? 'active' : ''}
                  aria-label="Ingest new model package"
                >
                  Ingest
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/health"
                  className={({ isActive }) => isActive ? 'active' : ''}
                  aria-label="System health dashboard"
                >
                  Health
                </NavLink>
              </li>
            </ul>
          </div>
        </nav>

        <main id="main-content" className="main-content" tabIndex={-1} role="main">
          <Routes>
            <Route path="/" element={<SearchArtifacts />} />
            <Route path="/ingest" element={<IngestPackage />} />
            <Route path="/health" element={<HealthDashboard />} />
          </Routes>
        </main>

        <footer className="footer" role="contentinfo">
          <p>Trustworthy Model Registry - Phase 2 Project</p>
        </footer>
      </div>
    </Router>
  );
};

export default App;
