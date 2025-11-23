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

  const handleKeyDown = (e: React.KeyboardEvent): void => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleExpanded();
    }
  };

  return (
    <article className="artifact-card" role="listitem" aria-labelledby={`artifact-${artifact.id}-name`}>
      <div className="card-header">
        <h3 id={`artifact-${artifact.id}-name`}>{artifact.name}</h3>
        {artifact.version && (
          <span className="version-badge" aria-label={`Version ${artifact.version}`}>
            v{artifact.version}
          </span>
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
        <div
          id={`expanded-metrics-${artifact.id}`}
          className="expanded-metrics"
          role="region"
          aria-labelledby={`expanded-heading-${artifact.id}`}
        >
          <h4 id={`expanded-heading-${artifact.id}`}>Additional Metrics:</h4>
          <dl className="metrics-list">
            <div className="metric-row">
              <dt>Responsive Maintainer:</dt>
              <dd>{artifact.metrics.responsiveMaintainer.toFixed(2)}</dd>
            </div>
            <div className="metric-row">
              <dt>License:</dt>
              <dd>{artifact.metrics.license.toFixed(2)}</dd>
            </div>
            {artifact.metrics.reviewedness !== undefined && (
              <div className="metric-row">
                <dt>Reviewedness:</dt>
                <dd>{artifact.metrics.reviewedness.toFixed(2)}</dd>
              </div>
            )}
            {artifact.metrics.reproducibility !== undefined && (
              <div className="metric-row">
                <dt>Reproducibility:</dt>
                <dd>{artifact.metrics.reproducibility.toFixed(2)}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      <div className="artifact-meta" aria-label="Artifact metadata">
        <span className="meta-item" aria-label={`Artifact ID: ${artifact.id}`}>
          ID: {artifact.id}
        </span>
        {artifact.author && (
          <span className="meta-item" aria-label={`Author: ${artifact.author}`}>
            By: {artifact.author}
          </span>
        )}
        <span className="meta-item" aria-label={`Last updated: ${new Date(artifact.updatedAt).toLocaleDateString()}`}>
          Updated: {new Date(artifact.updatedAt).toLocaleDateString()}
        </span>
      </div>

      <div className="card-actions">
        <button
          className="btn-secondary"
          onClick={toggleExpanded}
          onKeyDown={handleKeyDown}
          aria-expanded={isExpanded}
          aria-controls={`expanded-metrics-${artifact.id}`}
          aria-label={`${isExpanded ? 'Hide' : 'Show'} additional metrics for ${artifact.name}`}
        >
          {isExpanded ? 'Show Less' : 'Show More'}
        </button>
        <button
          className="btn-primary"
          onClick={handleDownload}
          aria-label={`Download ${artifact.name} package`}
        >
          Download
        </button>
      </div>
    </article>
  );
};

export default ArtifactCard;
