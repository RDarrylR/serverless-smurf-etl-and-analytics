import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import './App.css';

function FileDetailsModal({ file, onClose }) {
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>File Details</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <table className="details-table">
            <tbody>
              <tr>
                <td>File Name:</td>
                <td>{file.name}</td>
              </tr>
              <tr>
                <td>S3 Key:</td>
                <td><code>{file.key}</code></td>
              </tr>
              <tr>
                <td>Status:</td>
                <td><span className={`status-badge ${file.status}`}>{file.status}</span></td>
              </tr>
              {file.partitions && (
                <>
                  <tr>
                    <td>Store ID:</td>
                    <td>{file.partitions.store_id}</td>
                  </tr>
                  <tr>
                    <td>Date:</td>
                    <td>{file.partitions.year}-{file.partitions.month}-{file.partitions.day}</td>
                  </tr>
                </>
              )}
              <tr>
                <td>Last Modified:</td>
                <td>{new Date(file.last_modified).toLocaleString()}</td>
              </tr>
              <tr>
                <td>File Size:</td>
                <td>{formatBytes(file.size)}</td>
              </tr>
              {file.error && (
                <tr>
                  <td>Validation Error:</td>
                  <td className="error-text">{file.error}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Color palette for charts
const PAYMENT_COLORS = { cash: '#4CAF50', credit: '#2196F3', debit: '#FF9800', gift_card: '#9C27B0' };

// Color palette for store lines
const STORE_COLORS = [
  '#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8',
  '#82ca9d', '#ffc658', '#ff7300', '#a4de6c', '#d0ed57', '#8dd1e1'
];

// Analytics Dashboard Component
function AnalyticsDashboard({ apiBaseUrl }) {
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = selectedDate
        ? `${apiBaseUrl}/analytics?date=${selectedDate}`
        : `${apiBaseUrl}/analytics`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch analytics');
      const data = await response.json();
      setAnalyticsData(data);
      if (!selectedDate && data.date) {
        setSelectedDate(data.date);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch analytics on mount and when date changes
  useEffect(() => {
    fetchAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  if (loading) {
    return <div className="analytics-loading">Loading analytics data...</div>;
  }

  if (error) {
    return <div className="analytics-error">Error: {error}</div>;
  }

  if (!analyticsData) {
    return <div className="analytics-empty">No analytics data available</div>;
  }

  const { kpis, stores, top_products, anomalies, trends, recommendations, available_dates } = analyticsData;

  // Prepare payment breakdown data for pie chart
  const paymentData = kpis?.payment_breakdown ? [
    { name: 'Cash', value: kpis.payment_breakdown.cash },
    { name: 'Credit', value: kpis.payment_breakdown.credit },
    { name: 'Debit', value: kpis.payment_breakdown.debit },
    { name: 'Gift Card', value: kpis.payment_breakdown.gift_card }
  ] : [];

  // Prepare store data for bar chart
  const storeChartData = stores?.map(store => ({
    name: store.store_id,
    sales: store.total_sales,
    transactions: store.transaction_count
  })) || [];

  return (
    <div className="analytics-dashboard">
      {/* Date Selector */}
      <div className="date-selector">
        <label>Select Date: </label>
        <select
          value={selectedDate || ''}
          onChange={(e) => setSelectedDate(e.target.value)}
        >
          {available_dates?.map(date => (
            <option key={date} value={date}>{date}</option>
          ))}
        </select>
        <button onClick={fetchAnalytics} className="refresh-button">Refresh</button>
      </div>

      {/* KPI Cards */}
      <div className="kpi-container">
        <div className="kpi-card">
          <div className="kpi-value">{formatCurrency(kpis?.total_sales || 0)}</div>
          <div className="kpi-label">Total Sales</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{kpis?.total_transactions || 0}</div>
          <div className="kpi-label">Transactions</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{formatCurrency(kpis?.avg_transaction || 0)}</div>
          <div className="kpi-label">Avg Transaction</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{kpis?.store_count || 0}</div>
          <div className="kpi-label">Active Stores</div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="charts-row">
        {/* Sales by Store Bar Chart */}
        <div className="chart-container">
          <h3>Sales by Store</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={storeChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip formatter={(value) => formatCurrency(value)} />
              <Legend />
              <Bar dataKey="sales" fill="#0088FE" name="Sales ($)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Payment Methods Pie Chart */}
        <div className="chart-container">
          <h3>Payment Methods</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={paymentData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {paymentData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={Object.values(PAYMENT_COLORS)[index % 4]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatCurrency(value)} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Products Table */}
      <div className="analytics-section">
        <h3>Top Products</h3>
        <table className="analytics-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Product</th>
              <th>SKU</th>
              <th>Units Sold</th>
              <th>Revenue</th>
            </tr>
          </thead>
          <tbody>
            {top_products?.slice(0, 10).map((product, index) => (
              <tr key={product.sku}>
                <td>{index + 1}</td>
                <td>{product.name}</td>
                <td><code>{product.sku}</code></td>
                <td>{product.units_sold}</td>
                <td>{formatCurrency(product.revenue)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* AI Insights Section */}
      <div className="insights-container">
        {/* Anomalies */}
        <div className="insight-section">
          <h3>Detected Anomalies ({anomalies?.length || 0})</h3>
          {anomalies?.length > 0 ? (
            <div className="insight-cards">
              {anomalies.map((anomaly, index) => (
                <div key={index} className={`insight-card anomaly severity-${anomaly.severity}`}>
                  <div className="insight-header">
                    <span className={`severity-badge ${anomaly.severity}`}>{anomaly.severity}</span>
                    <span className="insight-store">Store: {anomaly.store_id}</span>
                  </div>
                  <div className="insight-title">{anomaly.title}</div>
                  <div className="insight-description">{anomaly.description}</div>
                  {anomaly.deviation_percent && (
                    <div className="insight-metric">Deviation: {anomaly.deviation_percent}%</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="no-insights">No anomalies detected</div>
          )}
        </div>

        {/* Trends */}
        <div className="insight-section">
          <h3>Identified Trends ({trends?.length || 0})</h3>
          {trends?.length > 0 ? (
            <div className="insight-cards">
              {trends.map((trend, index) => (
                <div key={index} className="insight-card trend">
                  <div className="insight-header">
                    <span className="trend-type">{trend.trend_type}</span>
                    <span className="significance">{trend.significance}</span>
                  </div>
                  <div className="insight-title">{trend.title}</div>
                  <div className="insight-description">{trend.description}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-insights">No trends identified</div>
          )}
        </div>

        {/* Recommendations */}
        <div className="insight-section">
          <h3>Action Recommendations ({recommendations?.length || 0})</h3>
          {recommendations?.length > 0 ? (
            <div className="insight-cards">
              {recommendations.map((rec, index) => (
                <div key={index} className={`insight-card recommendation priority-${rec.priority}`}>
                  <div className="insight-header">
                    <span className={`priority-badge ${rec.priority}`}>{rec.priority} priority</span>
                    <span className="rec-category">{rec.category}</span>
                  </div>
                  <div className="insight-title">{rec.title}</div>
                  <div className="insight-description">{rec.description}</div>
                  {rec.expected_impact && (
                    <div className="insight-impact">Expected Impact: {rec.expected_impact}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="no-insights">No recommendations available</div>
          )}
        </div>
      </div>
    </div>
  );
}

// Trends Dashboard Component
function TrendsDashboard({ apiBaseUrl }) {
  const [trendsData, setTrendsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);
  const [selectedStores, setSelectedStores] = useState([]);

  const fetchTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/trends?days=${days}`);
      if (!response.ok) throw new Error('Failed to fetch trends');
      const data = await response.json();
      setTrendsData(data);
      // Select all stores by default
      if (selectedStores.length === 0 && data.stores) {
        setSelectedStores(data.stores);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrends();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  const toggleStore = (storeId) => {
    setSelectedStores(prev =>
      prev.includes(storeId)
        ? prev.filter(s => s !== storeId)
        : [...prev, storeId]
    );
  };

  const selectAllStores = () => {
    if (trendsData?.stores) {
      setSelectedStores(trendsData.stores);
    }
  };

  const clearAllStores = () => {
    setSelectedStores([]);
  };

  if (loading) {
    return <div className="analytics-loading">Loading trends data...</div>;
  }

  if (error) {
    return <div className="analytics-error">Error: {error}</div>;
  }

  if (!trendsData) {
    return <div className="analytics-empty">No trends data available</div>;
  }

  const { stores, time_series, store_summaries, product_trends, available_dates } = trendsData;

  return (
    <div className="analytics-dashboard">
      {/* Controls */}
      <div className="trends-controls">
        <div className="date-selector">
          <label>Days of Data: </label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <span className="data-info">
            ({available_dates?.length || 0} days available)
          </span>
          <button onClick={fetchTrends} className="refresh-button">Refresh</button>
        </div>

        {/* Store Filter */}
        <div className="store-filter">
          <label>Filter Stores: </label>
          <div className="store-filter-buttons">
            <button onClick={selectAllStores} className="filter-btn">Select All</button>
            <button onClick={clearAllStores} className="filter-btn">Clear All</button>
          </div>
          <div className="store-checkboxes">
            {stores?.map((storeId, index) => (
              <label key={storeId} className="store-checkbox">
                <input
                  type="checkbox"
                  checked={selectedStores.includes(storeId)}
                  onChange={() => toggleStore(storeId)}
                />
                <span
                  className="store-color-dot"
                  style={{ backgroundColor: STORE_COLORS[index % STORE_COLORS.length] }}
                />
                Store {storeId}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Total Sales Over Time Chart */}
      <div className="chart-container full-width">
        <h3>Total Sales Over Time</h3>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={time_series}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis tickFormatter={(value) => `$${(value/1000).toFixed(0)}k`} />
            <Tooltip formatter={(value) => formatCurrency(value)} />
            <Legend />
            <Line
              type="monotone"
              dataKey="total_sales"
              stroke="#2196F3"
              strokeWidth={3}
              name="Total Sales"
              dot={{ fill: '#2196F3' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Sales by Store Over Time */}
      <div className="chart-container full-width">
        <h3>Sales by Store Over Time</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={time_series}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis tickFormatter={(value) => `$${value}`} />
            <Tooltip formatter={(value) => formatCurrency(value)} />
            <Legend />
            {stores?.filter(s => selectedStores.includes(s)).map((storeId, index) => (
              <Line
                key={storeId}
                type="monotone"
                dataKey={`${storeId}_sales`}
                stroke={STORE_COLORS[stores.indexOf(storeId) % STORE_COLORS.length]}
                strokeWidth={2}
                name={`Store ${storeId}`}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Store Performance Summary */}
      <div className="analytics-section">
        <h3>Store Performance Summary</h3>
        <table className="analytics-table">
          <thead>
            <tr>
              <th>Store ID</th>
              <th>Total Sales</th>
              <th>Transactions</th>
              <th>Avg Daily Sales</th>
              <th>Days with Data</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {store_summaries?.map((store, index) => (
              <tr key={store.store_id}>
                <td>
                  <span
                    className="store-color-dot"
                    style={{ backgroundColor: STORE_COLORS[stores.indexOf(store.store_id) % STORE_COLORS.length] }}
                  />
                  {store.store_id}
                </td>
                <td>{formatCurrency(store.total_sales)}</td>
                <td>{store.total_transactions}</td>
                <td>{formatCurrency(store.avg_daily_sales)}</td>
                <td>{store.days_with_data}</td>
                <td className={store.trend_percent >= 0 ? 'trend-up' : 'trend-down'}>
                  {store.trend_percent >= 0 ? '+' : ''}{store.trend_percent}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Product Trends */}
      {product_trends && product_trends.length > 0 && (
        <div className="analytics-section">
          <h3>Top Selling Products</h3>
          <table className="analytics-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Product</th>
                <th>SKU</th>
                <th>Total Units</th>
                <th>Total Revenue</th>
                <th>Avg Daily Units</th>
                <th>Days Sold</th>
                <th>Trend</th>
                <th>Sales History</th>
              </tr>
            </thead>
            <tbody>
              {product_trends.map((product, index) => (
                <tr key={product.sku}>
                  <td>{index + 1}</td>
                  <td>{product.name}</td>
                  <td><code>{product.sku}</code></td>
                  <td>{product.total_units_sold}</td>
                  <td>{formatCurrency(product.total_revenue)}</td>
                  <td>{product.avg_daily_units}</td>
                  <td>{product.days_sold}</td>
                  <td className={
                    product.trend_direction === 'increasing' ? 'trend-up' :
                    product.trend_direction === 'decreasing' ? 'trend-down' : ''
                  }>
                    {product.trend_direction === 'increasing' && '↑'}
                    {product.trend_direction === 'decreasing' && '↓'}
                    {product.trend_direction === 'stable' && '→'}
                    {product.trend_direction !== 'insufficient_data' && ` ${product.trend_percent >= 0 ? '+' : ''}${product.trend_percent}%`}
                    {product.trend_direction === 'insufficient_data' && '-'}
                  </td>
                  <td className="sparkline-cell">
                    <ResponsiveContainer width={120} height={30}>
                      <LineChart data={product.daily_history}>
                        <Line
                          type="monotone"
                          dataKey="units_sold"
                          stroke={product.trend_direction === 'increasing' ? '#4CAF50' :
                                  product.trend_direction === 'decreasing' ? '#f44336' : '#2196F3'}
                          strokeWidth={1.5}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Transactions Over Time */}
      <div className="chart-container full-width">
        <h3>Transactions Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={time_series}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="total_transactions" fill="#82ca9d" name="Total Transactions" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function App() {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [processedFiles, setProcessedFiles] = useState([]);
  const [rejectedFiles, setRejectedFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('analytics');

  const API_BASE_URL = process.env.REACT_APP_API_URL || '';
  const GENERATE_UPLOAD_URL = `${API_BASE_URL}/generate-upload-url`;
  const GENERATE_DOWNLOAD_URL = `${API_BASE_URL}/generate-download-url`;
  const LIST_FILES_URL = `${API_BASE_URL}/files`;

  // Fetch files from S3 on component mount
  useEffect(() => {
    fetchFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchFiles = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(LIST_FILES_URL);
      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }
      const data = await response.json();

      // Separate files by status
      const processed = data.files.filter(f => f.status === 'processed');
      const rejected = data.files.filter(f => f.status === 'rejected');

      setProcessedFiles(processed);
      setRejectedFiles(rejected);
    } catch (error) {
      console.error('Error fetching files:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getPresignedUrl = async (filename) => {
    try {
      const response = await fetch(GENERATE_UPLOAD_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ filename })
      });

      if (!response.ok) {
        throw new Error('Failed to get upload URL');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting presigned URL:', error);
      throw error;
    }
  };

  const uploadToS3 = async (url, file) => {
    try {
      const response = await fetch(url, {
        method: 'PUT',
        body: file
      });

      if (!response.ok) {
        throw new Error('Upload to S3 failed');
      }

      return true;
    } catch (error) {
      console.error('Error uploading to S3:', error);
      throw error;
    }
  };

  // Filename pattern: store_XXXX_YYYY-MM-DD.json
  const FILENAME_PATTERN = /^store_\d{4}_\d{4}-\d{2}-\d{2}\.json$/;

  const handleFileUpload = async (event) => {
    event.preventDefault();
    const file = event.target.files[0];
    if (!file) return;

    // Check if file is JSON
    if (!file.name.endsWith('.json')) {
      alert('Please upload a JSON file');
      return;
    }

    // Validate filename format: store_XXXX_YYYY-MM-DD.json
    if (!FILENAME_PATTERN.test(file.name)) {
      alert('Invalid filename format.\n\nExpected: store_XXXX_YYYY-MM-DD.json\nExample: store_0001_2025-01-15.json');
      return;
    }

    // Define loadingId outside try-catch for scope access
    const loadingId = Date.now();

    try {
      // Show loading state
      setUploadedFiles(prev => [...prev, {
        id: loadingId,
        name: file.name,
        uploadTime: new Date(),
        isLoading: true
      }]);

      // Get presigned URL
      const { uploadUrl, key } = await getPresignedUrl(file.name);

      // Upload to S3
      await uploadToS3(uploadUrl, file);

      // Update uploaded files list with successful upload
      setUploadedFiles(prev => prev.map(f =>
        f.id === loadingId
          ? { id: loadingId, name: file.name, uploadTime: new Date(), s3Key: key, isLoading: false }
          : f
      ));

      // Refresh the file lists after a short delay (to allow processing)
      setTimeout(() => fetchFiles(), 2000);

      // Clear the file input
      event.target.value = '';
    } catch (error) {
      // Remove loading entry if there was an error
      setUploadedFiles(prev => prev.filter(f => f.id !== loadingId));
      console.error('Upload failed:', error);
      alert('Upload failed: ' + error.message);
      // Clear the file input
      event.target.value = '';
    }
  };

  const handleDownload = async (file) => {
    try {
      // Get presigned download URL from backend with desired filename
      const response = await fetch(GENERATE_DOWNLOAD_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          key: file.key,
          filename: file.name  // Pass desired filename for Content-Disposition
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get download URL');
      }

      const data = await response.json();

      // Trigger download using the presigned URL
      window.location.href = data.downloadUrl;
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download failed: ' + error.message);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const renderProcessedTable = (files) => {
    if (files.length === 0) {
      return (
        <div className="empty-state">
          <p>No files found</p>
        </div>
      );
    }

    return (
      <table>
        <thead>
          <tr>
            <th>Store ID</th>
            <th>Date</th>
            <th>Size</th>
            <th>Last Modified</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, index) => (
            <tr key={index}>
              <td>{file.partitions?.store_id || 'N/A'}</td>
              <td>{file.partitions ? `${file.partitions.year}-${file.partitions.month}-${file.partitions.day}` : 'N/A'}</td>
              <td>{formatBytes(file.size)}</td>
              <td>{new Date(file.last_modified).toLocaleString()}</td>
              <td>
                <div className="action-menu">
                  <button
                    onClick={() => handleDownload(file)}
                    className="action-button download"
                  >
                    Download
                  </button>
                  <button
                    onClick={() => setSelectedFile(file)}
                    className="action-button"
                  >
                    View Details
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  const renderRejectedTable = (files) => {
    if (files.length === 0) {
      return (
        <div className="empty-state">
          <p>No files found</p>
        </div>
      );
    }

    return (
      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Last Modified</th>
            <th>Error</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, index) => (
            <tr key={index}>
              <td>{file.name}</td>
              <td>{formatBytes(file.size)}</td>
              <td>{new Date(file.last_modified).toLocaleString()}</td>
              <td className="error-text" style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {file.error || 'N/A'}
              </td>
              <td>
                <div className="action-menu">
                  <button
                    onClick={() => setSelectedFile(file)}
                    className="action-button"
                  >
                    View Details
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <img src="/smurfs.jpg" alt="Smurf Memorabilia Inc." className="header-logo" />
        <h1>Smurf Memorabilia Inc. Sales Uploads and Trends Viewer</h1>
      </header>
      <div className="upload-section">
        <input
          type="file"
          accept=".json"
          id="file-upload"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
        />
        <label htmlFor="file-upload" className="upload-button">
          Upload Daily Sales JSON
        </label>
        <button
          onClick={fetchFiles}
          className="refresh-button"
          disabled={isLoading}
        >
          {isLoading ? 'Loading...' : 'Refresh Files'}
        </button>
      </div>

      {/* Recently Uploaded Files */}
      {uploadedFiles.length > 0 && (
        <div className="table-container">
          <h2>Recently Uploaded</h2>
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>S3 Key</th>
                <th>Upload Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {uploadedFiles.map((file) => (
                <tr key={file.id} className={file.isLoading ? 'loading' : ''}>
                  <td>{file.name}</td>
                  <td><code>{file.s3Key ? file.s3Key : 'Uploading...'}</code></td>
                  <td>{file.uploadTime.toLocaleString()}</td>
                  <td>{file.isLoading ? '⏳ Uploading...' : '✓ Uploaded'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Main Tabs */}
      <div className="tabs main-tabs">
        <button
          className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics Dashboard
        </button>
        <button
          className={`tab ${activeTab === 'trends' ? 'active' : ''}`}
          onClick={() => setActiveTab('trends')}
        >
          Trends
        </button>
        <button
          className={`tab ${activeTab === 'processed' ? 'active' : ''}`}
          onClick={() => setActiveTab('processed')}
        >
          Processed Files ({processedFiles.length})
        </button>
        <button
          className={`tab ${activeTab === 'rejected' ? 'active' : ''}`}
          onClick={() => setActiveTab('rejected')}
        >
          Rejected Files ({rejectedFiles.length})
        </button>
      </div>

      {/* Analytics Dashboard */}
      {activeTab === 'analytics' && (
        <AnalyticsDashboard apiBaseUrl={API_BASE_URL} />
      )}

      {/* Trends Dashboard */}
      {activeTab === 'trends' && (
        <TrendsDashboard apiBaseUrl={API_BASE_URL} />
      )}

      {/* Files Tables */}
      {activeTab === 'processed' && (
        <div className="table-container">
          <h2>Processed Files (Parquet)</h2>
          {renderProcessedTable(processedFiles)}
        </div>
      )}
      {activeTab === 'rejected' && (
        <div className="table-container">
          <h2>Rejected Files (Validation Failed)</h2>
          {renderRejectedTable(rejectedFiles)}
        </div>
      )}

      {selectedFile && (
        <FileDetailsModal
          file={selectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </div>
  );
}

export default App;
