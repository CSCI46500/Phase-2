import { useState, FormEvent, ChangeEvent } from 'react';
import { modelRegistryAPI } from '../services/api';
import type { IngestResponse, ApiError } from '../types';

const IngestPackage: React.FC = () => {
  const [modelId, setModelId] = useState<string>('');
  const [version, setVersion] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      // Authenticate first with default admin credentials
      // In production, this should be handled through a proper login flow
      try {
        await modelRegistryAPI.authenticate(
          'ece30861defaultadminuser',
          'correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages'
        );
      } catch (authErr) {
        throw new Error('Failed to authenticate with the API. Please check your credentials.');
      }

      // Extract model ID from URL if a full URL is provided
      let extractedModelId = modelId;
      if (modelId.includes('huggingface.co/')) {
        const match = modelId.match(/huggingface\.co\/(.+?)(?:\?|$)/);
        if (match) {
          extractedModelId = match[1];
        }
      }

      const result = await modelRegistryAPI.ingestPackage(
        extractedModelId,
        version || undefined,
        description || undefined
      );
      setResponse(result);
      setModelId(''); // Clear input on success
      setVersion('');
      setDescription('');
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  };

  const handleModelIdChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setModelId(e.target.value);
  };

  const handleVersionChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setVersion(e.target.value);
  };

  const handleDescriptionChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setDescription(e.target.value);
  };

  return (
    <div className="ingest-container">
      <h2 id="ingest-heading">Ingest Model Package</h2>

      <form onSubmit={handleSubmit} aria-labelledby="ingest-heading">
        <div className="form-group">
          <label htmlFor="modelId">
            HuggingFace Model ID or URL: <span aria-label="required" className="required-indicator">*</span>
          </label>
          <input
            type="text"
            id="modelId"
            value={modelId}
            onChange={handleModelIdChange}
            placeholder="username/model-name or https://huggingface.co/username/model-name"
            disabled={loading}
            required
            aria-required="true"
            aria-describedby="modelId-help"
            aria-invalid={error ? 'true' : 'false'}
          />
          <small id="modelId-help">
            Example: bert-base-uncased or https://huggingface.co/bert-base-uncased
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="version">Version (optional):</label>
          <input
            type="text"
            id="version"
            value={version}
            onChange={handleVersionChange}
            placeholder="1.0.0"
            disabled={loading}
            aria-describedby="version-help"
          />
          <small id="version-help">
            Specify a version number for this model package
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="description">Description (optional):</label>
          <input
            type="text"
            id="description"
            value={description}
            onChange={handleDescriptionChange}
            placeholder="Model description"
            disabled={loading}
            aria-describedby="description-help"
          />
          <small id="description-help">
            Provide a brief description of the model
          </small>
        </div>

        <button
          type="submit"
          disabled={loading || !modelId.trim()}
          aria-label={loading ? 'Ingesting model package...' : 'Ingest model package'}
          aria-busy={loading}
        >
          {loading ? 'Ingesting...' : 'Ingest Package'}
        </button>
      </form>

      {loading && (
        <div
          className="spinner"
          role="status"
          aria-live="polite"
          aria-busy="true"
        >
          <div className="spinner-icon" aria-hidden="true"></div>
          <p>Processing model... This may take a minute.</p>
        </div>
      )}

      {error && (
        <div
          className="error-message"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        >
          <h3><span aria-label="Error" role="img">❌</span> Error</h3>
          <p id="error-description">{error.message}</p>
          {error.code && <p className="error-code">Error Code: {error.code}</p>}
          <p id="error-suggestion">
            Please verify the model ID and try again. Ensure the model exists on HuggingFace.
          </p>
        </div>
      )}

      {response && (
        <div
          className="success-message"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          <h3><span aria-label="Success" role="img">✅</span> Success!</h3>
          <div className="response-details">
            <div className="info-row">
              <span className="label">Model ID:</span>
              <span className="value">
                {response.id || <><span aria-label="Warning" role="img">⚠️</span> Pending (not implemented)</>}
              </span>
            </div>
            <div className="info-row">
              <span className="label">Name:</span>
              <span className="value">{response.name}</span>
            </div>
            <div className="info-row">
              <span className="label">Overall Score:</span>
              <span
                className={`value score ${response.score >= 0.5 ? 'pass' : 'fail'}`}
                aria-label={`Overall score: ${response.score.toFixed(2)} out of 1.0, ${response.score >= 0.5 ? 'passing' : 'failing'}`}
              >
                {response.score.toFixed(2)}
              </span>
            </div>

            <h4><span aria-label="Metrics" role="img">📊</span> Metrics:</h4>
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
              <h4><span aria-label="Implementation Status" role="img">🔧</span> Implementation Status:</h4>
              <ul>
                <li className="implemented"><span aria-label="Completed" role="img">✓</span> Model successfully ingested and validated</li>
                <li className="implemented"><span aria-label="Completed" role="img">✓</span> Metrics calculated and stored</li>
                <li className="implemented"><span aria-label="Completed" role="img">✓</span> Score validation (≥0.5 required)</li>
                <li className="missing"><span aria-label="Not implemented" role="img">✗</span> Unique ID generation not yet implemented</li>
                <li className="missing"><span aria-label="Not implemented" role="img">✗</span> Lineage graph parsing incomplete</li>
                <li className="missing"><span aria-label="Not implemented" role="img">✗</span> Reproducibility metric (demo code execution)</li>
                <li className="missing"><span aria-label="Not implemented" role="img">✗</span> Reviewedness metric (GitHub PR analysis)</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IngestPackage;
