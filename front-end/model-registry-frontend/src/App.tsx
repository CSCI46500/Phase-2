import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import IngestPackage from './components/IngestPackage';
import SearchArtifacts from './components/SearchArtifacts';
import './App.css';

const App: React.FC = () => {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <h1 className="logo">Model Registry</h1>
            <ul className="nav-links">
              <li>
                <NavLink 
                  to="/" 
                  className={({ isActive }) => isActive ? 'active' : ''}
                >
                  Search
                </NavLink>
              </li>
              <li>
                <NavLink 
                  to="/ingest"
                  className={({ isActive }) => isActive ? 'active' : ''}
                >
                  Ingest
                </NavLink>
              </li>
            </ul>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<SearchArtifacts />} />
            <Route path="/ingest" element={<IngestPackage />} />
          </Routes>
        </main>

        <footer className="footer">
          <p>Trustworthy Model Registry - Phase 2 Project</p>
        </footer>
      </div>
    </Router>
  );
};

export default App;
