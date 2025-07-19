import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [file, setFile] = useState(null);
  const [sqlResult, setSqlResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setSqlResult("❌ Please upload a schema (.txt, .pdf, .sqlite, .sql, .psql) file.");
      return;
    }

    const formData = new FormData();
    formData.append('query', query);
    formData.append('file', file);

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/ask', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSqlResult(response.data.sql_query);
    } catch (error) {
      setSqlResult("❌ Failed to generate SQL. Please try again.");
    }
    setLoading(false);
  };

  return (
    <div className="app-container" style={{ minHeight: '100vh', background: '#f5f7fa', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <div className="box" style={{
        background: 'white', borderRadius: '22px', boxShadow: '0 6px 32px #cfd6e6',
        maxWidth: '630px', width: '100%', padding: '36px 34px'
      }}>
        <h1 style={{marginBottom: '1.3em'}}>
          <span role="img" aria-label="brain">🧠</span> <span style={{fontWeight: 500}}>Natural Language</span> → <span className="highlight" style={{color:'#5548ee', fontWeight: 700}}>SQL Generator</span>
        </h1>
        <form onSubmit={handleSubmit} className="form" style={{marginBottom: '2em', display:'flex', flexDirection:'column', gap:'15px'}}>
          <div>
            <label style={{fontWeight: 600, fontSize: 16, marginBottom: 4, display: 'block'}}>Your Question</label>
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Write a query to find customer details…"
              className="input"
              rows={2}
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "8px",
                border: "1px solid #ccc",
                fontSize: "16px",
                background: "#fafaff",
                resize: "vertical",
                color: "black"
              }}
              required
            />
          </div>
          <div>
            <label style={{fontWeight: 600, fontSize: 16, marginBottom: 4, display: 'block'}}>Schema File (.txt, .pdf, .sqlite, .sql, .psql)</label>
            <input
              type="file"
              accept=".txt,.pdf,.sqlite,.sql,.psql"
              onChange={e => setFile(e.target.files[0])}
              className="input"
              style={{ width: "100%", borderRadius: "8px" }}
              required
            />
            {file && <span style={{marginTop:5, fontSize:13, color:'#8692ab', display: 'inline-block'}}>📁 {file.name}</span>}
          </div>
          <button type="submit" className="btn" style={{
            marginTop: "10px",
            padding: '12px 0', 
            background: '#5548ee',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '18px',
            cursor: 'pointer'
          }}>
            {loading ? "Generating..." : "Generate SQL"}
          </button>
        </form>
        {/* Show full question and result */}
        {sqlResult && (
          <div className="result-box" style={{
            background: "#f3f7ff",
            borderRadius: "11px",
            padding: "1.2em 1.1em",
            marginTop: '12px',
            boxShadow: '0 2px 10px #e9eefd'
          }}>
            <div style={{marginBottom: 9, fontWeight: 500, display:'flex', alignItems:'center', color:'#10bb73'}}>
              <span style={{fontSize: 22, marginRight: 7}}>✔️</span> Generated SQL Query:
            </div>
            <div style={{
              background: '#f7fbff',
              borderRadius: "6px",
              padding: "10px 15px",
              fontSize: "16px",
              lineHeight: 1.7,
              border: "1px solid #e2eaff"
            }}>
              <div style={{marginBottom: "7px", color:"#4e565f", fontWeight:600}}>Your Question:</div>
              <div style={{marginBottom: "10px", color:"#575d63"}}>{query}</div>
              <div style={{marginBottom: "7px", color:"#4e565f", fontWeight:600}}>SQL:</div>
              <pre style={{margin:0, fontSize:"15px", color:"#111"}}>{sqlResult}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
