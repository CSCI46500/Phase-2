import { useState } from 'react';
import { useHealthCheck } from '../hooks/useHealthCheck';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import './HealthDashboard.css';

type ComponentStatus = 'healthy' | 'degraded' | 'down' | 'unknown';

type HealthMetric = {
  name: string;
  status: ComponentStatus;
  responseTime?: number;
  message?: string;
  lastChecked?: string;
};

const HealthDashboard: React.FC = () => {
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [refreshInterval, setRefreshInterval] = useState<number>(30);
  const { data, loading, error, refetch, lastUpdated } = useHealthCheck(
    autoRefresh ? refreshInterval * 1000 : null
  );

  const getStatusColor = (status: ComponentStatus): string => {
    switch (status) {
      case 'healthy':
        return 'status-healthy';
      case 'degraded':
        return 'status-degraded';
      case 'down':
        return 'status-down';
      default:
        return 'status-unknown';
    }
  };

  const getStatusIcon = (status: ComponentStatus): string => {
    switch (status) {
      case 'healthy':
        return '✓';
      case 'degraded':
        return '⚠';
      case 'down':
        return '✗';
      default:
        return '?';
    }
  };

  const formatResponseTime = (ms?: number): string => {
    if (ms === undefined) return 'N/A';
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getOverallStatus = (): ComponentStatus => {
    if (!data || !data.components) return 'unknown';

    const statuses = Object.values(data.components).map((c: unknown) => (c as { status: string }).status);
    if (statuses.every((s) => s === 'healthy')) return 'healthy';
    if (statuses.some((s) => s === 'down')) return 'down';
    if (statuses.some((s) => s === 'degraded')) return 'degraded';
    return 'unknown';
  };

  const getHealthMetrics = (): HealthMetric[] => {
    if (!data || !data.components) return [];

    return Object.entries(data.components).map(([name, component]: [string, unknown]) => {
      const comp = component as { status?: string; response_time?: number; message?: string; last_checked?: string };
      return {
        name: name.charAt(0).toUpperCase() + name.slice(1),
        status: comp.status || 'unknown',
        responseTime: comp.response_time,
        message: comp.message,
        lastChecked: comp.last_checked,
      };
    });
  };

  const overallStatus = getOverallStatus();
  const metrics = getHealthMetrics();
  const uptime = data?.uptime;

  // Chart data preparation
  const getResponseTimeChartData = () => {
    return metrics
      .filter((m) => m.responseTime !== undefined)
      .map((m) => ({
        name: m.name,
        responseTime: m.responseTime,
        status: m.status,
      }));
  };

  const getStatusDistributionData = () => {
    const statusCounts: Record<string, number> = {};
    metrics.forEach((m) => {
      statusCounts[m.status] = (statusCounts[m.status] || 0) + 1;
    });

    return Object.entries(statusCounts).map(([status, count]) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1),
      value: count,
      status: status as ComponentStatus,
    }));
  };

  const getStatusChartColor = (status: ComponentStatus): string => {
    switch (status) {
      case 'healthy':
        return '#4ebb7e';
      case 'degraded':
        return '#ffc107';
      case 'down':
        return '#ef5350';
      default:
        return '#9e9e9e';
    }
  };

  const responseTimeData = getResponseTimeChartData();
  const statusDistributionData = getStatusDistributionData();

  return (
    <div className="health-dashboard">
      <div className="dashboard-header">
        <h2 id="health-heading">System Health Dashboard</h2>

        <div className="dashboard-controls">
          <div className="auto-refresh-control">
            <label htmlFor="auto-refresh">
              <input
                id="auto-refresh"
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                aria-label="Enable auto-refresh"
              />
              <span>Auto-refresh</span>
            </label>
          </div>

          {autoRefresh && (
            <div className="refresh-interval-control">
              <label htmlFor="refresh-interval" className="visually-hidden">
                Refresh interval in seconds
              </label>
              <select
                id="refresh-interval"
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                aria-label="Select refresh interval"
              >
                <option value={10}>10s</option>
                <option value={30}>30s</option>
                <option value={60}>1m</option>
                <option value={300}>5m</option>
              </select>
            </div>
          )}

          <button
            onClick={() => refetch()}
            disabled={loading}
            className="btn-secondary refresh-button"
            aria-label={loading ? 'Refreshing health status' : 'Refresh health status'}
          >
            {loading ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>

      {lastUpdated && (
        <p className="last-updated" role="status" aria-live="polite">
          Last updated: {new Date(lastUpdated).toLocaleString()}
        </p>
      )}

      {error && (
        <div className="error-message" role="alert" aria-live="assertive">
          <h3>Unable to fetch health status</h3>
          <p>{error.message}</p>
        </div>
      )}

      {data && !loading && (
        <div className="health-content">
          {/* Overall Status Card */}
          <section
            className={`overall-status ${getStatusColor(overallStatus)}`}
            aria-labelledby="overall-status-heading"
          >
            <div className="status-icon" aria-hidden="true">
              {getStatusIcon(overallStatus)}
            </div>
            <div className="status-info">
              <h3 id="overall-status-heading">Overall System Status</h3>
              <p className="status-text">{overallStatus.toUpperCase()}</p>
              {uptime !== undefined && (
                <p className="uptime-text" aria-label={`System uptime: ${uptime} seconds`}>
                  Uptime: {Math.floor(uptime / 3600)}h {Math.floor((uptime % 3600) / 60)}m
                </p>
              )}
            </div>
          </section>

          {/* Charts Section */}
          {metrics.length > 0 && (
            <div className="charts-section">
              {/* Response Time Chart */}
              {responseTimeData.length > 0 && (
                <div className="chart-card">
                  <h3>Response Time by Component</h3>
                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={responseTimeData}
                        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis
                          dataKey="name"
                          stroke="#888"
                          style={{ fontSize: '0.85rem' }}
                        />
                        <YAxis
                          stroke="#888"
                          style={{ fontSize: '0.85rem' }}
                          label={{ value: 'ms', angle: -90, position: 'insideLeft' }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1e1e1e',
                            border: '1px solid #333',
                            borderRadius: '8px',
                            color: '#fff',
                          }}
                          formatter={(value: number) => [`${value.toFixed(2)} ms`, 'Response Time']}
                        />
                        <Legend />
                        <Bar
                          dataKey="responseTime"
                          fill="#0066cc"
                          radius={[8, 8, 0, 0]}
                          name="Response Time (ms)"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Status Distribution Chart */}
              {statusDistributionData.length > 0 && (
                <div className="chart-card">
                  <h3>Component Status Distribution</h3>
                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={statusDistributionData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent }) =>
                            `${name}: ${(percent * 100).toFixed(0)}%`
                          }
                          outerRadius={100}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {statusDistributionData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={getStatusChartColor(entry.status)}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1e1e1e',
                            border: '1px solid #333',
                            borderRadius: '8px',
                            color: '#fff',
                          }}
                        />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Component Metrics */}
          <section className="metrics-section" aria-labelledby="metrics-heading">
            <h3 id="metrics-heading">Component Health Metrics</h3>

            <div className="metrics-grid" role="list">
              {metrics.map((metric) => (
                <div
                  key={metric.name}
                  className={`metric-card ${getStatusColor(metric.status)}`}
                  role="listitem"
                >
                  <div className="metric-header">
                    <span className="metric-icon" aria-hidden="true">
                      {getStatusIcon(metric.status)}
                    </span>
                    <h4>{metric.name}</h4>
                  </div>

                  <div className="metric-body">
                    <div className="metric-status">
                      <span className="metric-label">Status:</span>
                      <span className={`metric-value ${getStatusColor(metric.status)}`}>
                        {metric.status.toUpperCase()}
                      </span>
                    </div>

                    {metric.responseTime !== undefined && (
                      <div className="metric-response-time">
                        <span className="metric-label">Response Time:</span>
                        <span className="metric-value">
                          {formatResponseTime(metric.responseTime)}
                        </span>
                      </div>
                    )}

                    {metric.responseTime !== undefined && (
                      <div className="response-time-bar">
                        <div
                          className="response-time-fill"
                          style={{
                            width: `${Math.min((metric.responseTime / 1000) * 100, 100)}%`,
                          }}
                          role="progressbar"
                          aria-valuenow={metric.responseTime}
                          aria-valuemin={0}
                          aria-valuemax={1000}
                          aria-label={`Response time: ${formatResponseTime(metric.responseTime)}`}
                        />
                      </div>
                    )}

                    {metric.message && (
                      <p className="metric-message">{metric.message}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* System Information */}
          {data.version && (
            <section className="system-info" aria-labelledby="system-info-heading">
              <h3 id="system-info-heading">System Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">API Version:</span>
                  <span className="info-value">{data.version}</span>
                </div>
                {data.environment && (
                  <div className="info-item">
                    <span className="info-label">Environment:</span>
                    <span className="info-value">{data.environment}</span>
                  </div>
                )}
                {data.timestamp && (
                  <div className="info-item">
                    <span className="info-label">Server Time:</span>
                    <span className="info-value">
                      {new Date(data.timestamp).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      )}

      {loading && !data && (
        <div className="spinner" role="status" aria-live="polite" aria-busy="true">
          <div className="spinner-icon" aria-hidden="true"></div>
          <span>Loading health status...</span>
        </div>
      )}
    </div>
  );
};

export default HealthDashboard;
