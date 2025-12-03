import { useState, useEffect, useCallback } from 'react';
import { modelRegistryAPI } from '../services/api';
import type { LogEntry, LogLevel, ApiError } from '../types';
import './LogViewer.css';

const LogViewer: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [total, setTotal] = useState<number>(0);

  // Filter states
  const [selectedLevel, setSelectedLevel] = useState<LogLevel | ''>('');
  const [searchText, setSearchText] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [limit] = useState<number>(50);

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(10);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const offset = (currentPage - 1) * limit;
      const response = await modelRegistryAPI.getLogs(
        selectedLevel || undefined,
        sourceFilter || undefined,
        startDate || undefined,
        endDate || undefined,
        searchText || undefined,
        offset,
        limit
      );

      setLogs(response.logs);
      setTotal(response.total);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err as ApiError);
      console.error('Failed to fetch logs:', err);
    } finally {
      setLoading(false);
    }
  }, [currentPage, limit, selectedLevel, sourceFilter, startDate, endDate, searchText]);

  // Initial fetch and filter changes
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchLogs();
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchLogs]);

  const handleFilterChange = () => {
    setCurrentPage(1); // Reset to first page when filters change
  };

  const handleClearFilters = () => {
    setSelectedLevel('');
    setSearchText('');
    setSourceFilter('');
    setStartDate('');
    setEndDate('');
    setCurrentPage(1);
  };

  const getLogLevelClass = (level: LogLevel): string => {
    return `log-level-${level.toLowerCase()}`;
  };

  const getLogLevelIcon = (level: LogLevel): string => {
    switch (level) {
      case 'DEBUG':
        return '🔍';
      case 'INFO':
        return 'ℹ️';
      case 'WARNING':
        return '⚠️';
      case 'ERROR':
        return '❌';
      case 'CRITICAL':
        return '🔥';
      default:
        return '📝';
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const totalPages = Math.ceil(total / limit);
  const hasActiveFilters = selectedLevel || searchText || sourceFilter || startDate || endDate;

  return (
    <div className="log-viewer">
      <div className="log-viewer-header">
        <h2>System Logs</h2>

        <div className="auto-refresh-controls">
          <label>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Auto-refresh</span>
          </label>

          {autoRefresh && (
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
            >
              <option value={5}>5s</option>
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>1m</option>
            </select>
          )}

          <button onClick={fetchLogs} disabled={loading} className="btn-secondary">
            {loading ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>

      {lastUpdated && (
        <p className="last-updated">
          Last updated: {lastUpdated.toLocaleString()}
        </p>
      )}

      <div className="log-filters">
        <div className="filter-group">
          <label htmlFor="log-level-filter">Log Level:</label>
          <select
            id="log-level-filter"
            value={selectedLevel}
            onChange={(e) => {
              setSelectedLevel(e.target.value as LogLevel | '');
              handleFilterChange();
            }}
          >
            <option value="">All Levels</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="search-filter">Search:</label>
          <input
            id="search-filter"
            type="text"
            placeholder="Search logs..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onBlur={handleFilterChange}
            onKeyDown={(e) => e.key === 'Enter' && handleFilterChange()}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="source-filter">Source:</label>
          <input
            id="source-filter"
            type="text"
            placeholder="Filter by source..."
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            onBlur={handleFilterChange}
            onKeyDown={(e) => e.key === 'Enter' && handleFilterChange()}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="start-date-filter">Start Date:</label>
          <input
            id="start-date-filter"
            type="datetime-local"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              handleFilterChange();
            }}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="end-date-filter">End Date:</label>
          <input
            id="end-date-filter"
            type="datetime-local"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              handleFilterChange();
            }}
          />
        </div>

        {hasActiveFilters && (
          <button onClick={handleClearFilters} className="btn-clear-filters">
            Clear Filters
          </button>
        )}
      </div>

      {error && (
        <div className="error-message" role="alert">
          <h3>Failed to load logs</h3>
          <p>{error.message}</p>
        </div>
      )}

      <div className="log-stats">
        <p>
          Showing {logs.length} of {total} logs
          {hasActiveFilters && ' (filtered)'}
        </p>
      </div>

      {loading && logs.length === 0 ? (
        <div className="spinner">
          <div className="spinner-icon"></div>
          <span>Loading logs...</span>
        </div>
      ) : logs.length === 0 ? (
        <div className="no-logs">
          <p>No logs found</p>
          {hasActiveFilters && (
            <button onClick={handleClearFilters} className="btn-secondary">
              Clear filters to see all logs
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="logs-container">
            <div className="logs-table">
              <div className="logs-table-header">
                <div className="log-col-level">Level</div>
                <div className="log-col-timestamp">Timestamp</div>
                <div className="log-col-source">Source</div>
                <div className="log-col-message">Message</div>
              </div>

              <div className="logs-table-body">
                {logs.map((log) => (
                  <div
                    key={log.id}
                    className={`log-entry ${getLogLevelClass(log.level)}`}
                  >
                    <div className="log-col-level">
                      <span className="log-level-badge">
                        <span className="log-icon" aria-hidden="true">
                          {getLogLevelIcon(log.level)}
                        </span>
                        <span className="log-level-text">{log.level}</span>
                      </span>
                    </div>

                    <div className="log-col-timestamp">
                      {formatTimestamp(log.timestamp)}
                    </div>

                    <div className="log-col-source">
                      {log.source || 'N/A'}
                    </div>

                    <div className="log-col-message">
                      <div className="log-message-text">{log.message}</div>
                      {log.user && (
                        <div className="log-metadata">
                          <span className="metadata-label">User:</span>
                          <span className="metadata-value">{log.user}</span>
                        </div>
                      )}
                      {log.metadata && Object.keys(log.metadata).length > 0 && (
                        <details className="log-metadata-details">
                          <summary>Additional Details</summary>
                          <pre className="metadata-json">
                            {JSON.stringify(log.metadata, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage === 1 || loading}
                className="btn-secondary"
              >
                Previous
              </button>

              <span className="page-info">
                Page {currentPage} of {totalPages}
              </span>

              <button
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages || loading}
                className="btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default LogViewer;
