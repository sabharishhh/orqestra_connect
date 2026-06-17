import React, { useState, useEffect } from 'react';
import { Activity, ShieldAlert, Cpu, AlertTriangle, Clock, BrainCircuit, CheckCircle2 } from 'lucide-react';

function App() {
  const [feed, setFeed] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState(null);

  // Polling Engine: Fetches from the backend GET endpoint every 5 seconds
  useEffect(() => {
    const fetchFeed = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/contradictions');
        if (!res.ok) throw new Error('Failed to fetch data');
        const json = await res.json();
        setFeed(json.data);
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
      } catch (err) {
        setError('Lost connection to Orqestra Engine.');
        console.error(err);
      }
    };

    fetchFeed(); // Initial fetch on load
    const interval = setInterval(fetchFeed, 5000); 
    return () => clearInterval(interval); // Cleanup on unmount
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans p-8">
      {/* HEADER */}
      <header className="max-w-5xl mx-auto mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-lg text-white">
            <Activity size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Orqestra Console</h1>
            <p className="text-sm text-slate-500">Live Cross-System Contradiction Feed</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-500 font-mono">
            {lastUpdated ? `LAST SYNC: ${lastUpdated}` : 'CONNECTING...'}
          </div>
          <div className={`flex items-center gap-2 text-sm font-medium px-3 py-1 rounded-full border ${
            error ? 'bg-red-50 text-red-600 border-red-200' : 'bg-emerald-50 text-emerald-600 border-emerald-200'
          }`}>
            <span className="relative flex h-2 w-2">
              {!error && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${error ? 'bg-red-500' : 'bg-emerald-500'}`}></span>
            </span>
            {error ? 'System Offline' : 'Engine Active'}
          </div>
        </div>
      </header>

      {/* MAIN FEED */}
      <main className="max-w-5xl mx-auto space-y-6">
        {feed.length === 0 && !error && (
          <div className="h-[400px] border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center text-slate-400">
            <ShieldAlert size={48} className="mb-4 opacity-30" />
            <p className="text-lg font-medium text-slate-500">No contradictions detected</p>
            <p className="text-sm">Monitoring cross-system traffic in real-time...</p>
          </div>
        )}

        {feed.map((item) => (
          <div key={item.contradiction_id} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* Card Header (Collision Alert) */}
            <div className="bg-red-50 border-b border-red-100 px-6 py-4 flex justify-between items-center">
              <div className="flex items-center gap-3 text-red-800 font-semibold text-lg">
                <ShieldAlert size={20} className="text-red-600" />
                Collision Detected
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                  <Clock size={14} />
                  {new Date(item.detected_at).toLocaleTimeString()}
                </div>
                <div className="flex items-center gap-2 text-sm font-mono bg-white px-3 py-1 rounded-md border border-red-200 text-red-700 shadow-sm">
                  <Cpu size={14} />
                  Conf: {(item.confidence_score * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Claims Comparison */}
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* System A */}
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">System A</div>
                <div className="font-semibold text-indigo-900 mb-2 font-mono text-sm">{item.system_a_name}</div>
                <p className="text-slate-700 text-sm italic">"{item.claim_a_text}"</p>
              </div>

              {/* System B */}
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-rose-500"></div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">System B</div>
                <div className="font-semibold text-rose-900 mb-2 font-mono text-sm">{item.system_b_name}</div>
                <p className="text-slate-700 text-sm italic">"{item.claim_b_text}"</p>
              </div>
            </div>

            {/* AI Explainer Section */}
            <div className="px-6 pb-6">
              <div className="bg-slate-900 rounded-xl p-5 text-slate-300 shadow-inner">
                <div className="flex justify-between items-center mb-4 pb-3 border-b border-slate-700">
                  <span className="font-bold text-white flex items-center gap-2">
                    <BrainCircuit size={18} className="text-indigo-400" />
                    DSPy Explainer Engine
                  </span>
                  {item.risk_level && (
                    <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-xs font-bold flex items-center gap-1 border border-red-500/30">
                      <AlertTriangle size={12} />
                      {item.risk_level} RISK
                    </span>
                  )}
                </div>
                
                <div className="space-y-4 text-sm">
                  <div>
                    <span className="text-slate-400 font-mono text-xs block mb-1.5 font-semibold tracking-wider">BUSINESS / CLINICAL RISK:</span>
                    <p className="text-slate-200 leading-relaxed">{item.why_they_contradict}</p>
                  </div>
                  
                  {item.recommended_action ? (
                    <div className="pt-2">
                      <span className="text-emerald-400 font-mono text-xs block mb-1.5 font-semibold tracking-wider">RECOMMENDED ACTION:</span>
                      <p className="text-emerald-50 bg-emerald-950/50 p-3 rounded-lg border border-emerald-900/50 flex items-start gap-2">
                        <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" />
                        {item.recommended_action}
                      </p>
                    </div>
                  ) : (
                    <div className="pt-2 text-slate-500 italic flex items-center gap-2">
                      <Activity size={14} className="animate-spin" />
                      DSPy worker generating risk profile and remediation steps...
                    </div>
                  )}
                </div>
              </div>
            </div>

          </div>
        ))}
      </main>
    </div>
  );
}

export default App;