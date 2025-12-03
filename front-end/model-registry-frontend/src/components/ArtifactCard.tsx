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
        <ScoreBadge label="License" score={artifact.metrics.license} />
        <ScoreBadge label="Ramp-up" score={artifact.metrics.rampUp} />
        <ScoreBadge label="Bus Factor" score={artifact.metrics.busFactor} />
      </div>

      {isExpanded && (
        <div
          id={`expanded-metrics-${artifact.id}`}
          className="expanded-metrics"
          role="region"
          aria-labelledby={`expanded-heading-${artifact.id}`}
        >
          <h4 id={`expanded-heading-${artifact.id}`}>All Metrics:</h4>
          <dl className="metrics-list">
            {/* Phase 1 Metrics */}
            <div className="metric-row">
              <dt>Correctness:</dt>
              <dd>{artifact.metrics.correctness.toFixed(2)}</dd>
            </div>
            <div className="metric-row">
              <dt>Responsive Maintainer:</dt>
              <dd>{artifact.metrics.responsiveMaintainer.toFixed(2)}</dd>
            </div>

            {/* Phase 2 Metrics */}
            {artifact.metrics.codeQuality !== undefined && (
              <div className="metric-row">
                <dt>Code Quality:</dt>
                <dd>{artifact.metrics.codeQuality.toFixed(2)}</dd>
              </div>
            )}
            {artifact.metrics.datasetQuality !== undefined && (
              <div className="metric-row">
                <dt>Dataset Quality:</dt>
                <dd>{artifact.metrics.datasetQuality.toFixed(2)}</dd>
              </div>
            )}
            {artifact.metrics.datasetAndCodeScore !== undefined && (
              <div className="metric-row">
                <dt>Dataset & Code Score:</dt>
                <dd>{artifact.metrics.datasetAndCodeScore.toFixed(2)}</dd>
              </div>
            )}
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
            {artifact.metrics.performanceClaims !== undefined && (
              <div className="metric-row">
                <dt>Performance Claims:</dt>
                <dd>{artifact.metrics.performanceClaims.toFixed(2)}</dd>
              </div>
            )}
            {artifact.metrics.treeScore !== undefined && (
              <div className="metric-row">
                <dt>Tree Score:</dt>
                <dd>{artifact.metrics.treeScore.toFixed(2)}</dd>
              </div>
            )}
            {artifact.metrics.sizeScore !== undefined && (
              <div className="metric-row">
                <dt>Size Score:</dt>
                <dd>
                  {typeof artifact.metrics.sizeScore === 'number'
                    ? artifact.metrics.sizeScore.toFixed(2)
                    : `AWS: ${artifact.metrics.sizeScore?.aws_server?.toFixed(2) || 'N/A'}, Desktop: ${artifact.metrics.sizeScore?.desktop_pc?.toFixed(2) || 'N/A'}`
                  }
                </dd>
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
