import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import api from './services/api';
import './styles/App.css';

function App() {
  const [eventId, setEventId] = useState(1);
  const [riskData, setRiskData] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [correlations, setCorrelations] = useState({ known_loops: [], new_correlations: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch predictions
  const fetchPrediction = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post('/predict-risk', {
        event_id: eventId,
        current_state: { stock_flow: 500, filler_flow: 50, steam_pressure: 5.5 },
        basis_weight_target: 120,
      });
      setRiskData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch prediction');
    } finally {
      setLoading(false);
    }
  };

  // Fetch recommendations
  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post('/recommend-setpoints', {
        event_id: eventId,
        current_state: { stock_flow: 500, filler_flow: 50, steam_pressure: 5.5 },
        target_state: { stock_flow: 520, filler_flow: 55, steam_pressure: 5.8 },
        risk_probability: 0.4,
      });
      setRecommendations(response.data.recommendations);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch recommendations');
    } finally {
      setLoading(false);
    }
  };

  // Fetch correlations
  const fetchCorrelations = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/correlations?event_id=${eventId}`);
      setCorrelations(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch correlations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrediction();
  }, [eventId]);

  return (
    <div className="App">
      <header className="header">
        <h1>📊 PaperMill Grade-Change Assistant</h1>
        <p>AI-powered advisory system for paper machine operators</p>
      </header>

      <div className="control-panel">
        <div className="input-group">
          <label>Event ID:</label>
          <input
            type="number"
            value={eventId}
            onChange={(e) => setEventId(parseInt(e.target.value))}
            min="1"
          />
        </div>
        <button onClick={fetchPrediction} disabled={loading}>
          {loading ? 'Loading...' : 'Predict Risk'}
        </button>
        <button onClick={fetchRecommendations} disabled={loading}>
          {loading ? 'Loading...' : 'Get Recommendations'}
        </button>
        <button onClick={fetchCorrelations} disabled={loading}>
          {loading ? 'Loading...' : 'Analyze Correlations'}
        </button>
      </div>

      {error && <div className="error-message">⚠️ {error}</div>}

      <div className="dashboard">
        {/* Risk Panel */}
        {riskData && (
          <div className="panel risk-panel">
            <h2>🎯 Risk Assessment</h2>
            <div className="risk-gauge">
              <div className="gauge-value">
                <span className="risk-probability">{(riskData.risk_probability * 100).toFixed(1)}%</span>
                <p>Off-Spec Risk</p>
              </div>
              {riskData.time_to_breach_sec && (
                <div className="time-to-breach">
                  <span>{riskData.time_to_breach_sec.toFixed(0)}s</span>
                  <p>Time to Breach</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Recommendations Panel */}
        <div className="panel recommendations-panel">
          <h2>💡 Recommendations</h2>
          {recommendations.length > 0 ? (
            <div className="recommendations-list">
              {recommendations.map((rec, idx) => (
                <div key={idx} className="recommendation-card">
                  <div className="rec-header">
                    <h4>{rec.variable_name}</h4>
                    <span className={`source-tag ${rec.source_tag}`}>{rec.source_tag.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="rec-values">
                    {rec.current_value.toFixed(2)} → {rec.recommended_value.toFixed(2)}
                  </p>
                  <p className="rec-effect">{rec.expected_effect}</p>
                  <p className="rec-rationale">{rec.rationale}</p>
                  <div className="rec-footer">
                    <span>Confidence: {(rec.confidence * 100).toFixed(0)}%</span>
                    <div className="rec-actions">
                      <button className="btn-accept">✓ Accept</button>
                      <button className="btn-reject">✗ Reject</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">Click "Get Recommendations" to generate suggestions</p>
          )}
        </div>

        {/* Correlations Panel */}
        <div className="panel correlations-panel">
          <h2>🔗 Variable Correlations</h2>
          {correlations.known_loops.length > 0 && (
            <div>
              <h3>Known Control Loops</h3>
              <ul>
                {correlations.known_loops.map((corr, idx) => (
                  <li key={idx}>
                    <strong>{corr.variable_a} ↔ {corr.variable_b}</strong>
                    <p>{corr.impact_statement}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {correlations.new_correlations.length > 0 && (
            <div>
              <h3>Newly Discovered Correlations 🆕</h3>
              <ul>
                {correlations.new_correlations.map((corr, idx) => (
                  <li key={idx}>
                    <strong>{corr.variable_a} ↔ {corr.variable_b}</strong>
                    <p>{corr.impact_statement}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {correlations.known_loops.length === 0 && correlations.new_correlations.length === 0 && (
            <p className="no-data">Click "Analyze Correlations" to discover relationships</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
