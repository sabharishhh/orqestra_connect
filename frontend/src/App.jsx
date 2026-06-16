import React, { useState } from 'react';
import { Shield, ShieldAlert, Cpu, BrainCircuit, Activity, Clock, Database, ChevronRight } from 'lucide-react';

function App() {
  const [systemName, setSystemName] = useState('HealthTrack_Mobile');
  const [claimText, setClaimText] = useState("Metformin therapy must be immediately discontinued if the patient's eGFR drops beneath a 45 mL/min boundary metric.");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          system_name: systemName,
          claim_text: claimText,
        }),
      });

      if (!response.ok) throw new Error('Failed to connect to Orqestra Engine');
      
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans p-8">
      {/* HEADER */}
      <header className="max-w-6xl mx-auto mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-lg text-white">
            <Activity size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Orqestra Console</h1>
            <p className="text-sm text-slate-500">Neuro-Symbolic Contradiction Detection</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          Engine Online
        </div>
      </header>

      <main className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* LEFT COLUMN: INGESTION FORM */}
        <div className="lg:col-span-1 bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-fit">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Database size={18} className="text-slate-400" />
            Ingest New Claim
          </h2>
          <form onSubmit={handleAnalyze} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Originating System</label>
              <input 
                type="text" 
                className="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                value={systemName}
                onChange={(e) => setSystemName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Claim Text / Rule Logic</label>
              <textarea 
                rows="5"
                className="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none"
                value={claimText}
                onChange={(e) => setClaimText(e.target.value)}
              />
            </div>
            <button 
              type="submit"
              disabled={loading}
              className="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-2.5 rounded-lg transition-colors flex justify-center items-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span className="animate-pulse">Running Triage Cascade...</span>
              ) : (
                <>Run Analysis <ChevronRight size={16} /></>
              )}
            </button>
          </form>
        </div>

        {/* RIGHT COLUMN: RESULTS DASHBOARD */}
        <div className="lg:col-span-2 space-y-6">
          
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg border border-red-200 flex items-start gap-3">
              <ShieldAlert size={20} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold">Connection Error</p>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}

          {!result && !loading && !error && (
            <div className="h-full min-h-[300px] border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center text-slate-400">
              <Activity size={48} className="mb-4 opacity-50" />
              <p>Awaiting claim ingestion...</p>
            </div>
          )}

          {result && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              
              {/* TOP STATUS CARD */}
              <div className={`p-6 rounded-xl border shadow-sm flex items-start justify-between ${
                result.status === 'SAFE' ? 'bg-emerald-50 border-emerald-200' :
                result.status === 'BOUNCER_INTERCEPT' ? 'bg-orange-50 border-orange-200' :
                'bg-red-50 border-red-200'
              }`}>
                <div className="flex gap-4">
                  <div className={`p-3 rounded-full h-fit ${
                    result.status === 'SAFE' ? 'bg-emerald-100 text-emerald-600' :
                    result.status === 'BOUNCER_INTERCEPT' ? 'bg-orange-100 text-orange-600' :
                    'bg-red-100 text-red-600'
                  }`}>
                    {result.status === 'SAFE' ? <Shield size={28} /> : <ShieldAlert size={28} />}
                  </div>
                  <div>
                    <h2 className="text-xl font-bold mb-1">
                      {result.status === 'SAFE' ? 'Cleared / Safe' : 
                       result.status === 'BOUNCER_INTERCEPT' ? 'Intercepted by NLI Filter' : 
                       'Contradiction Confirmed'}
                    </h2>
                    <p className={`text-sm ${
                      result.status === 'SAFE' ? 'text-emerald-700' :
                      result.status === 'BOUNCER_INTERCEPT' ? 'text-orange-700' :
                      'text-red-700'
                    }`}>{result.message}</p>
                  </div>
                </div>
                {/* TELEMETRY BADGE */}
                {result.processing_time_ms && (
                  <div className="flex items-center gap-1.5 text-xs font-semibold bg-white px-3 py-1.5 rounded-lg border shadow-sm text-slate-600">
                    <Clock size={14} />
                    {result.processing_time_ms} ms
                  </div>
                )}
              </div>

              {/* COLLISION DETAILS (Only show if not strictly SAFE with no matches) */}
              {result.matched_text && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="bg-slate-50 px-6 py-3 border-b border-slate-200 flex justify-between items-center">
                    <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                      Target System: <span className="text-indigo-600 font-mono text-sm bg-indigo-50 px-2 py-0.5 rounded">{result.matched_system}</span>
                    </h3>
                    {result.similarity_score && (
                      <span className="text-xs font-medium text-slate-500 bg-slate-200 px-2 py-1 rounded">
                        Vector Match: {(result.similarity_score * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                  
                  <div className="p-6 space-y-4">
                    <div>
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Conflicting Claim Found</p>
                      <p className="text-sm bg-slate-50 border border-slate-100 p-3 rounded-lg text-slate-700 italic">
                        "{result.matched_text}"
                      </p>
                    </div>

                    <div className="pt-4 border-t border-slate-100">
                      <div className="flex items-center gap-2 mb-2">
                        {result.routing_tier === "DeBERTa Local" ? (
                          <Cpu size={16} className="text-orange-500" />
                        ) : (
                          <BrainCircuit size={16} className="text-red-500" />
                        )}
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                          {result.routing_tier} Reasoning
                        </p>
                        {result.confidence && (
                          <span className="text-xs text-orange-600 bg-orange-50 px-2 py-0.5 rounded border border-orange-100">
                            Confidence: {(result.confidence * 100).toFixed(2)}%
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-medium text-slate-800">
                        {result.reasoning}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;