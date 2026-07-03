import React from 'react';

const PatientProfile = () => {
  return (
    // MAIN BACKGROUND: Warm, breathable cream (avoids hospital white)
    <div className="min-h-screen bg-[#FBF9F6] p-4 md:p-8 font-sans">
      
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* 1. CARE STATUS HEADER */}
        <div className="bg-[#FFFFFF] p-6 rounded-2xl shadow-sm border border-[#EBE6E1] flex flex-col md:flex-row justify-between items-start md:items-center">
          <div>
            <h1 className="text-3xl font-bold text-[#2B2624]">Devendra Sharma</h1>
            <p className="text-[#7A726D] mt-1 text-lg">Age: 74 • Primary Contact: Priya (Daughter)</p>
          </div>
          {/* Status Badge: Muted, professional alert state */}
          <div className="mt-4 md:mt-0 px-4 py-2 bg-[#FEF2F2] border border-[#F8D7DA] rounded-lg">
            <span className="text-[#B91C1C] font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#B91C1C] animate-pulse"></span>
              Emergency Alert Triggered
            </span>
          </div>
        </div>

        {/* 2. TRIAGE TELEMETRY GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Active Symptoms Card */}
          <div className="bg-[#FFFFFF] p-6 rounded-2xl shadow-sm border border-[#EBE6E1]">
            <h2 className="text-sm font-bold text-[#7A726D] uppercase tracking-wider mb-4">Active Symptoms</h2>
            <div className="flex flex-wrap gap-2">
              <span className="px-3 py-1.5 bg-[#FEF2F2] text-[#B91C1C] rounded-md text-sm font-medium">Chest Pain</span>
              <span className="px-3 py-1.5 bg-[#F4F1ED] text-[#2B2624] rounded-md text-sm font-medium">Shortness of Breath</span>
              <span className="px-3 py-1.5 bg-[#F4F1ED] text-[#2B2624] rounded-md text-sm font-medium">Fatigue</span>
            </div>
          </div>

          {/* AI Monitoring Status */}
          <div className="bg-[#FFFFFF] p-6 rounded-2xl shadow-sm border border-[#EBE6E1]">
             <h2 className="text-sm font-bold text-[#7A726D] uppercase tracking-wider mb-4">System Status</h2>
             <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-[#7A726D]">Last WhatsApp Sync:</span>
                  <span className="text-[#2B2624] font-medium">Just now</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#7A726D]">Twilio Voice Alert:</span>
                  <span className="text-[#C88B4B] font-medium">Dispatched (02:06 AM)</span>
                </div>
             </div>
          </div>
        </div>

        {/* 3. CHRONOLOGICAL FEED (WHATSAPP LOGS) */}
        <div>
          <h2 className="text-xl font-bold text-[#2B2624] mb-4 mt-8">Recent Triage Logs</h2>
          
          <div className="space-y-4">
            
            {/* EMERGENCY LOG CARD */}
            <div className="bg-[#FFFFFF] p-6 rounded-2xl shadow-sm border border-[#F8D7DA] border-l-4 border-l-[#B91C1C]">
              <div className="flex justify-between items-start mb-3">
                <p className="text-[#B91C1C] text-sm font-bold uppercase tracking-wide">High Severity Flag</p>
                <p className="text-[#7A726D] text-sm">Today, 02:06 AM</p>
              </div>
              <p className="text-[#2B2624] text-lg leading-relaxed mb-4">
                "I am feeling very unwell and I have severe chest pain."
              </p>
              <div className="bg-[#F4F1ED] p-4 rounded-lg">
                <p className="text-sm font-bold text-[#2B2624] mb-1">Gemini AI Analysis:</p>
                <p className="text-[#7A726D] text-sm">Patient reports acute chest pain. Classified as a critical cardiac event symptom. Immediate caretaker notification required. Anti-spam cooldown initiated for 15 minutes.</p>
              </div>
            </div>

            {/* ROUTINE LOG CARD */}
            <div className="bg-[#FFFFFF] p-6 rounded-2xl shadow-sm border border-[#EBE6E1] opacity-75">
              <div className="flex justify-between items-start mb-3">
                <p className="text-[#7A726D] text-sm font-bold uppercase tracking-wide">Routine Update</p>
                <p className="text-[#7A726D] text-sm">Yesterday, 08:30 PM</p>
              </div>
              <p className="text-[#2B2624] text-lg leading-relaxed mb-4">
                "I took my evening blood pressure medication after dinner."
              </p>
              <div className="bg-[#F4F1ED] p-4 rounded-lg">
                <p className="text-sm font-bold text-[#2B2624] mb-1">Gemini AI Analysis:</p>
                <p className="text-[#7A726D] text-sm">Routine medication adherence noted. No critical symptoms present.</p>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};

export default PatientProfile;