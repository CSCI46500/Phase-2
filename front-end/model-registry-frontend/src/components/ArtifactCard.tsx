import { useState } from 'react';
import ScoreBadge from './ScoreBadge';
import type { Artifact } from '../types';

interface ArtifactCardProps {
  artifact: Artifact;
}

const ArtifactCard: React.FC<ArtifactCardProps> = ({ artifact }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const handleDownload = (): void => {
    // Placeholder for download functionality
    console.log(`Downloading artifact: ${artifact.id}`);
    alert(`Download functionality coming soon for ${artifact.name}`);
  };

  const toggleExpanded = (): void => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="artifact-card">
      <div className="card-header">
        <h3>{artifact.name}</h3>
        {artifact.version && (
          <span className="version-badge">v{artifact.version}</span>
        )}
      </div>
      
      <p className="artifact-description">{artifact.description}</p>
      
      <div className="artifact-scores">
        <ScoreBadge label="Overall" score={artifact.score} isPrimary />
        <ScoreBadge label="Ramp-up" score={artifact.metrics.rampUp} />
        <ScoreBadge label="Correctness" score={artifact.metrics.correctness} />
        <ScoreBadge label="Bus Factor" score={artifact.metrics.busFactor} />
      </div>

      {isExpanded && (
        <div className="expanded-metrics">
          <h4>Additional Metrics:</h4>
          <div className="metrics-list">
            <div className="metric-row">
              <span>Responsive Maintainer:</span>
              <span>{artifact.metrics.responsiveMaintainer.toFixed(2)}</span>
            </div>
            <div className="metric-row">
              <span>License:</span>
              <span>{artifact.metrics.license.toFixed(2)}</span>
            </div>
            {artifact.metrics.reviewedness !== undefined && (
              <div className="metric-row">
                <span>Reviewedness:</span>
                <span>{artifact.metrics.reviewedness.toFixed(2)}</span>
              </div>
            )}
            {artifact.metrics.reproducibility !== undefined && (
              <div className="metric-row">
                <span>Reproducibility:</span>
                <span>{artifact.metrics.reproducibility.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="artifact-meta">
        <span className="meta-item">ID: {artifact.id}</span>
        {artifact.author && <span className="meta-item">By: {artifact.author}</span>}
        <span className="meta-item">
          Updated: {new Date(artifact.updatedAt).toLocaleDateString()}
        </span>
      </div>

      <div className="card-actions">
        <button className="btn-secondary" onClick={toggleExpanded}>
          {isExpanded ? 'Show Less' : 'Show More'}
        </button>
        <button className="btn-primary" onClick={handleDownload}>
          Download
        </button>
      </div>
    </div>
  );
};

export default ArtifactCard;
