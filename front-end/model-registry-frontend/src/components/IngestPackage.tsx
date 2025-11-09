import { useState, FormEvent, ChangeEvent } from 'react';
import { modelRegistryAPI } from '../services/api';
import type { IngestResponse, ApiError } from '../types';

const IngestPackage: React.FC = () => {
  const [modelUrl, setModelUrl] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const result = await modelRegistryAPI.ingestPackage(modelUrl);
      setResponse(result);
      setModelUrl(''); // Clear input on success
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setModelUrl(e.target.value);
  };

  return (
    <div className="ingest-container">
      <h2>Ingest Model Package</h2>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="modelUrl">HuggingFace Model URL:</label>
          <input
            type="text"
            id="modelUrl"
            value={modelUrl}
            onChange={handleInputChange}
            placeholder="https://huggingface.co/username/model-name"
            disabled={loading}
            required
          />
        </div>
        
        <button type="submit" disabled={loading || !modelUrl.trim()}>
          {loading ? 'Ingesting...' : 'Ingest Package'}
        </button>
      </form>

      {loading && (
        <div className="spinner">
          <div className="spinner-icon"></div>
          <p>Processing model... This may take a minute.</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <h3>❌ Error</h3>
          <p>{error.message}</p>
          {error.code && <p className="error-code">Error Code: {error.code}</p>}
        </div>
      )}

      {response && (
        <div className="success-message">
          <h3>✅ Success!</h3>
          <div className="response-details">
            <div className="info-row">
              <span className="label">Model ID:</span>
              <span className="value">{response.id || '⚠️ Pending (not implemented)'}</span>
            </div>
            <div className="info-row">
              <span className="label">Name:</span>
              <span className="value">{response.name}</span>
            </div>
            <div className="info-row">
              <span className="label">Overall Score:</span>
              <span className={`value score ${response.score >= 0.5 ? 'pass' : 'fail'}`}>
                {response.score.toFixed(2)}
              </span>
            </div>
            
            <h4>📊 Metrics:</h4>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-name">Ramp-up:</span>
                <span className="metric-value">{response.metrics.rampUp.toFixed(2)}</span>
              </div>
              <div className="metric-item">
                <span className="metric-name">Correctness:</span>
                <span className="metric-value">{response.metrics.correctness.toFixed(2)}</span>
              </div>
              <div className="metric-item">
                <span className="metric-name">Bus Factor:</span>
                <span className="metric-value">{response.metrics.busFactor.toFixed(2)}</span>
              </div>
              <div className="metric-item">
                <span className="metric-name">Responsive Maintainer:</span>
                <span className="metric-value">
                  {response.metrics.responsiveMaintainer.toFixed(2)}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-name">License:</span>
                <span className="metric-value">{response.metrics.license.toFixed(2)}</span>
              </div>
            </div>

            <div className="implementation-notes">
              <h4>🔧 Implementation Status:</h4>
              <ul>
                <li className="implemented">✓ Model successfully ingested and validated</li>
                <li className="implemented">✓ Metrics calculated and stored</li>
                <li className="implemented">✓ Score validation (≥0.5 required)</li>
                <li className="missing">✗ Unique ID generation not yet implemented</li>
                <li className="missing">✗ Lineage graph parsing incomplete</li>
                <li className="missing">✗ Reproducibility metric (demo code execution)</li>
                <li className="missing">✗ Reviewedness metric (GitHub PR analysis)</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IngestPackage;
