import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from './api'; // 👈 Secured live API link
import RegisterElderModal from './components/RegisterElderModal'; // 👈 Imported your Modal
import { 
  Phone, 
  ShieldCheck, 
  ChevronDown,
  ChevronUp,
  Activity,
  FileText,
  Download,
  Plus // 👈 Added a Plus icon for the button
} from 'lucide-react';

/* ------------------------------------------------------------------ */
//  1. DATA PROCESSING
/* ------------------------------------------------------------------ */
const computeDailySummaries = (logs) => {
  return logs.map(log => {
    // Safely parse the SQLite stringified array
    let parsedSymptoms = [];
    if (Array.isArray(log.symptoms)) {
        parsedSymptoms = log.symptoms;
    } else if (typeof log.symptoms === 'string') {
        try {
            parsedSymptoms = JSON.parse(log.symptoms.replace(/'/g, '"'));
        } catch (e) {
            parsedSymptoms = [log.symptoms];
        }
    }

    const counts = {};
    parsedSymptoms.forEach(s => { counts[s] = (counts[s] || 0) + 1; });
    
    const safeTags = Object.entries(counts).map(([symptom, count]) => {
      if (symptom.toLowerCase().includes("chest pain") && count > 1) return { type: "WORSENING", label: `${symptom}` };
      if (count > 1) return { type: "REPEATED", label: `${symptom} (x${count})` };
      return { type: "NEW SYMPTOM", label: symptom };
    });

    return {
      date: log.date,
      totalVoiceNotes: 1, 
      symptoms: safeTags, // This is now an array of formatted objects!
      sentiment: log.sentiment
    };
  });
};

/* ------------------------------------------------------------------ */
//  2. UI COMPONENTS
/* ------------------------------------------------------------------ */
const EmergencyAlert = ({ onCall, onToggleDetails, showDetails, onDismiss }) => (
  <div className="w-full max-w-5xl mx-auto mt-8 bg-[#0f172a] border-2 border-red-600 rounded-3xl overflow-hidden shadow-[0_0_60px_rgba(220,38,38,0.25)]">
    <div className="p-16 flex flex-col items-center text-center space-y-8">
      <div className="flex items-center space-x-3 text-red-500 font-bold tracking-widest uppercase text-sm bg-red-950/30 px-6 py-2 rounded-full border border-red-500/20">
        <span className="relative flex h-3 w-3"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-red-600"></span></span>
        <span>Immediate Caretaker Action Required</span>
      </div>
      <h1 className="text-3xl md:text-5xl text-white font-extrabold leading-tight max-w-3xl">Repeated shortness of breath and chest tightness reported.</h1>
      <button onClick={onCall} className="w-full md:w-3/4 py-6 bg-red-600 hover:bg-red-500 text-white text-3xl md:text-4xl font-black rounded-2xl shadow-2xl shadow-red-600/40 transition-all">
        <Phone className="w-12 h-12 animate-pulse inline mr-4" /> CALL EMERGENCY CONTACT
      </button>
      <button onClick={onDismiss} className="text-slate-500 hover:text-white underline text-sm">Dismiss Emergency (Demo Mode)</button>
    </div>
  </div>
);

const PeaceTimeDashboard = ({ elderName, dailyLogs, onExport }) => (
  <div className="max-w-6xl mx-auto space-y-8">
    <div className="bg-white/[0.02] border border-white/10 rounded-3xl p-8 shadow-xl">
        <div className="flex items-center gap-5">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center"><ShieldCheck className="w-7 h-7 text-emerald-400" /></div>
            <div>
                <h2 className="text-2xl font-bold text-white tracking-tight">Monitoring Active</h2>
                <p className="text-slate-400 text-sm">No critical health anomalies detected today.</p>
            </div>
        </div>
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2"><FileText className="w-5 h-5 text-cyan-400" /> Symptom History</h3>
            {dailyLogs.length === 0 ? (
                <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 text-slate-400 text-center">
                   No symptom logs yet. Waiting for WhatsApp updates...
                </div>
            ) : (
                dailyLogs.map((log, index) => (
                    <div key={index} className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
                        <span className="text-sm font-bold text-slate-300">{log.date}</span>
                        
                        {/* AI Symptom Badges */}
                        <div className="flex flex-wrap gap-2 mt-3">
                          {log.symptoms && log.symptoms.length > 0 ? (
                            log.symptoms.map((badge, idx) => (
                              <span 
                                key={idx} 
                                className="px-3 py-1 text-xs font-semibold text-red-200 bg-red-900/50 border border-red-700 rounded-full"
                              >
                                {badge.label}
                              </span>
                            ))
                          ) : (
                            <span className="text-sm italic text-gray-500">No critical symptoms extracted</span>
                          )}
                        </div>

                    </div>
                ))
            )}
        </div>
        <div className="space-y-6">
            <button onClick={onExport} className="w-full flex items-center justify-center gap-2 p-4 rounded-xl bg-transparent border-2 border-slate-800 hover:border-slate-600 text-slate-400 transition-colors font-medium text-sm">
                <Download className="w-4 h-4" /> Export 30-Day Symptom Log
            </button>
        </div>
    </div>
  </div>
);

/* ------------------------------------------------------------------ */
//  3. MAIN APP CONTAINER
/* ------------------------------------------------------------------ */
export default function App() {
  const [isEmergency, setIsEmergency] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const [showRawData, setShowRawData] = useState(false);
  const [dailyLogs, setDailyLogs] = useState([]);
  const [elderName, setElderName] = useState("Loading...");
  
  // 👈 Added State to control your Modal
  const [isModalOpen, setIsModalOpen] = useState(false); 

  const exportSymptomLog = () => {
    const dataStr = JSON.stringify(dailyLogs, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Aarogya_Clinical_Export.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // 👈 Swapped out the hardcoded 127.0.0.1 for your dynamic API_URL
        const response = await axios.get(`${API_URL}/api/dashboard/1`); 
        setElderName(response.data.elder.name);
        setIsEmergency(response.data.elder.status === "attention");
        setDailyLogs(computeDailySummaries(response.data.notes));
      } catch (error) { console.error("Error fetching live data:", error); }
    };
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000); 
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 font-sans p-4 md:p-8">
      {isEmergency && (
        <audio autoPlay loop>
          <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg" />
        </audio>
      )}

      {/* 👈 Added the Add Patient button to your header */}
      <header className="max-w-6xl mx-auto mb-8 flex justify-between items-center">
        <h1 className="text-xl font-bold text-white">Aarogya AI Dashboard</h1>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-emerald-500/20"
        >
          <Plus className="w-5 h-5" /> Add Patient
        </button>
      </header>
      
      {isEmergency && !isDismissed ? (
        <EmergencyAlert 
          onCall={() => alert("Calling...")} 
          onToggleDetails={() => setShowRawData(!showRawData)} 
          showDetails={showRawData} 
          onDismiss={() => setIsDismissed(true)} // 👈 3. Change this to set your new state
        />
      ) : (
        <PeaceTimeDashboard 
            elderName={elderName} 
            dailyLogs={dailyLogs} 
            onExport={exportSymptomLog} 
        />
      )}

      {/* 👈 Placed the Modal at the bottom, hooked up to the state */}
      {isModalOpen && (
        <RegisterElderModal onClose={() => setIsModalOpen(false)} />
      )}
    </div>
  );
}