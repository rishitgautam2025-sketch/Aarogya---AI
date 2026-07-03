import React from 'react';

const PatientProfile = () => {
  return (
    // MAIN BACKGROUND
    <div style={{ minHeight: '100vh', backgroundColor: '#FBF9F6', padding: '2rem', fontFamily: 'sans-serif' }}>
      <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* 1. CARE STATUS HEADER */}
        <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #EBE6E1', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#2B2624', margin: '0' }}>Devendra Sharma</h1>
            <p style={{ color: '#7A726D', marginTop: '0.25rem', fontSize: '1.125rem', marginBottom: 0 }}>Age: 74 • Primary Contact: Priya (Daughter)</p>
          </div>
          <div style={{ padding: '0.5rem 1rem', backgroundColor: '#FEF2F2', border: '1px solid #F8D7DA', borderRadius: '8px' }}>
            <span style={{ color: '#B91C1C', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#B91C1C', animation: 'pulse 2s infinite' }}></span>
              Emergency Alert Triggered
            </span>
          </div>
        </div>

        {/* 2. TRIAGE TELEMETRY GRID */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          
          {/* Active Symptoms Card */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #EBE6E1' }}>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#7A726D', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', marginTop: 0 }}>Active Symptoms</h2>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              <span style={{ padding: '0.375rem 0.75rem', backgroundColor: '#FEF2F2', color: '#B91C1C', borderRadius: '6px', fontSize: '0.875rem', fontWeight: '500' }}>Chest Pain</span>
              <span style={{ padding: '0.375rem 0.75rem', backgroundColor: '#F4F1ED', color: '#2B2624', borderRadius: '6px', fontSize: '0.875rem', fontWeight: '500' }}>Shortness of Breath</span>
              <span style={{ padding: '0.375rem 0.75rem', backgroundColor: '#F4F1ED', color: '#2B2624', borderRadius: '6px', fontSize: '0.875rem', fontWeight: '500' }}>Fatigue</span>
            </div>
          </div>

          {/* AI Monitoring Status */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #EBE6E1' }}>
             <h2 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#7A726D', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', marginTop: 0 }}>System Status</h2>
             <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#7A726D' }}>Last WhatsApp Sync:</span>
                  <span style={{ color: '#2B2624', fontWeight: '500' }}>Just now</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#7A726D' }}>Twilio Voice Alert:</span>
                  <span style={{ color: '#C88B4B', fontWeight: '500' }}>Dispatched (02:06 AM)</span>
                </div>
             </div>
          </div>
        </div>

        {/* 3. CHRONOLOGICAL FEED (WHATSAPP LOGS) */}
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#2B2624', marginBottom: '1rem', marginTop: '1rem' }}>Recent Triage Logs</h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            
            {/* EMERGENCY LOG CARD */}
            <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #F8D7DA', borderLeft: '4px solid #B91C1C' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                <p style={{ color: '#B91C1C', fontSize: '0.875rem', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>High Severity Flag</p>
                <p style={{ color: '#7A726D', fontSize: '0.875rem', margin: 0 }}>Today, 02:06 AM</p>
              </div>
              <p style={{ color: '#2B2624', fontSize: '1.125rem', lineHeight: '1.6', margin: '0 0 1rem 0' }}>
                "I am feeling very unwell and I have severe chest pain."
              </p>
              <div style={{ backgroundColor: '#F4F1ED', padding: '1rem', borderRadius: '8px' }}>
                <p style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#2B2624', margin: '0 0 0.25rem 0' }}>Gemini AI Analysis:</p>
                <p style={{ color: '#7A726D', fontSize: '0.875rem', margin: 0 }}>Patient reports acute chest pain. Classified as a critical cardiac event symptom. Immediate caretaker notification required. Anti-spam cooldown initiated for 15 minutes.</p>
              </div>
            </div>

            {/* ROUTINE LOG CARD */}
            <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #EBE6E1', opacity: 0.75 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                <p style={{ color: '#7A726D', fontSize: '0.875rem', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>Routine Update</p>
                <p style={{ color: '#7A726D', fontSize: '0.875rem', margin: 0 }}>Yesterday, 08:30 PM</p>
              </div>
              <p style={{ color: '#2B2624', fontSize: '1.125rem', lineHeight: '1.6', margin: '0 0 1rem 0' }}>
                "I took my evening blood pressure medication after dinner."
              </p>
              <div style={{ backgroundColor: '#F4F1ED', padding: '1rem', borderRadius: '8px' }}>
                <p style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#2B2624', margin: '0 0 0.25rem 0' }}>Gemini AI Analysis:</p>
                <p style={{ color: '#7A726D', fontSize: '0.875rem', margin: 0 }}>Routine medication adherence noted. No critical symptoms present.</p>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};

export default PatientProfile;