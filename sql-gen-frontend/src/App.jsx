import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // import the CSS

function App() {
  const [query, setQuery] = useState('');
  const [sqlResult, setSqlResult] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://localhost:8000/ask', { query });
      setSqlResult(response.data.sql_query);
    } catch (error) {
      setSqlResult("❌ Failed to generate SQL. Please try again.");
    }
  };

  return (
    <div className="app-container">
      <div className="box">
        <h1><span role="img" aria-label="brain">🧠</span> Natural Language → <span className="highlight">SQL Generator</span></h1>

        <form onSubmit={handleSubmit} className="form">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Write a query to find customer details..."
            className="input"
          />
          <button type="submit" className="btn">Generate SQL</button>
        </form>

        {sqlResult && (
          <div className="result-box">
            <h2>✅ Generated SQL Query:</h2>
            <pre>{sqlResult}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
