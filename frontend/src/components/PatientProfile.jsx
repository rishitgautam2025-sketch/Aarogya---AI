import React from 'react';

const PatientProfile = ({ logs = [] }) => {
  // 1. DYNAMIC DATA PROCESSING
  // Extract a list of unique symptoms from all the AI tags
  const allSymptoms = logs.flatMap(log => log.symptoms?.map(tag => tag.label) || []);
  const uniqueSymptoms = [...new Set(allSymptoms)];

  // Check if the most recent log has a 'NEW_SYMPTOM' tag to trigger the red alert banner
  const latestLog = logs[0];
  const isCurrentlyEmergency = latestLog?.symptoms?.some(tag => tag.tag_type === 'NEW_SYMPTOM');

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FBF9F6', padding: '2rem', fontFamily: 'sans-serif' }}>
      <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* --- CARE STATUS HEADER --- */}
        <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #EBE6E1', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            {/* Using the patient ID from the first log if available */}
            <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#2B2624', margin: '0' }}>
              Patient {latestLog ? `#${latestLog.patient_id.substring(0, 5)}` : 'Profile'}
            </h1>
            <p style={{ color: '#7A726D', marginTop: '0.25rem', fontSize: '1.125rem', marginBottom: 0 }}>Active Monitoring Setup</p>
          </div>
          
          {/* Dynamic Emergency Badge */}
          {isCurrentlyEmergency ? (
            <div style={{ padding: '0.5rem 1rem', backgroundColor: '#FEF2F2', border: '1px solid #F8D7DA', borderRadius: '8px' }}>
              <span style={{ color: '#B91C1C', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#B91C1C', animation: 'pulse 2s infinite' }}></span>
                Emergency Alert Triggered
              </span>
            </div>
          ) : (
             <div style={{ padding: '0.5rem 1rem', backgroundColor: '#F4F1ED', border: '1px solid #EBE6E1', borderRadius: '8px' }}>
              <span style={{ color: '#7A726D', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10B981' }}></span>
                Stable Monitoring
              </span>
            </div>
          )}
        </div>

        {/* --- TRIAGE TELEMETRY GRID --- */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          
          <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #EBE6E1' }}>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#7A726D', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', marginTop: 0 }}>Active Symptoms Extracted</h2>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {uniqueSymptoms.length > 0 ? (
                uniqueSymptoms.map((symptom, idx) => (
                  <span key={idx} style={{ padding: '0.375rem 0.75rem', backgroundColor: '#F4F1ED', color: '#2B2624', borderRadius: '6px', fontSize: '0.875rem', fontWeight: '500' }}>
                    {symptom}
                  </span>
                ))
              ) : (
                <span style={{ color: '#7A726D', fontSize: '0.875rem', fontStyle: 'italic' }}>No active symptoms recorded.</span>
              )}
            </div>
          </div>

          <div style={{ backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #EBE6E1' }}>
             <h2 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#7A726D', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', marginTop: 0 }}>System Status</h2>
             <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#7A726D' }}>Total Logs Analyzed:</span>
                  <span style={{ color: '#2B2624', fontWeight: '500' }}>{logs.length}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#7A726D' }}>Last Database Sync:</span>
                  <span style={{ color: '#10B981', fontWeight: '500' }}>Live</span>
                </div>
             </div>
          </div>
        </div>

        {/* --- CHRONOLOGICAL FEED (MAPPED FROM SUPABASE) --- */}
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#2B2624', marginBottom: '1rem', marginTop: '1rem' }}>Recent Triage Logs</h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {logs.length === 0 ? (
              <p style={{ color: '#7A726D' }}>Waiting for WhatsApp messages...</p>
            ) : (
              logs.map((log) => {
                // Determine if this specific log contained a critical emergency tag
                const isCritical = log.symptoms?.some(tag => tag.tag_type === 'NEW_SYMPTOM');
                const timeString = new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });

                return (
                  <div key={log.id} style={{ 
                    backgroundColor: '#FFFFFF', 
                    padding: '1.5rem', 
                    borderRadius: '16px', 
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)', 
                    border: isCritical ? '1px solid #F8D7DA' : '1px solid #EBE6E1', 
                    borderLeft: isCritical ? '4px solid #B91C1C' : 'none',
                    opacity: isCritical ? 1 : 0.85
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                      <p style={{ color: isCritical ? '#B91C1C' : '#7A726D', fontSize: '0.875rem', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                        {isCritical ? 'High Severity Flag' : 'Routine Update'}
                      </p>
                      <p style={{ color: '#7A726D', fontSize: '0.875rem', margin: 0 }}>{timeString}</p>
                    </div>
                    
                    <p style={{ color: '#2B2624', fontSize: '1.125rem', lineHeight: '1.6', margin: '0 0 1rem 0' }}>
                      "{log.raw_text}"
                    </p>
                    
                    <div style={{ backgroundColor: '#F4F1ED', padding: '1rem', borderRadius: '8px' }}>
                      <p style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#2B2624', margin: '0 0 0.25rem 0' }}>Gemini AI Analysis Labels:</p>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                        {log.symptoms && log.symptoms.length > 0 ? (
                          log.symptoms.map(tag => (
                            <span key={tag.id} style={{ fontSize: '0.8rem', backgroundColor: tag.tag_type === 'NEW_SYMPTOM' ? '#FEF2F2' : '#E0E7FF', color: tag.tag_type === 'NEW_SYMPTOM' ? '#B91C1C' : '#3730A3', padding: '2px 8px', borderRadius: '4px', fontWeight: '600' }}>
                              {tag.label}
                            </span>
                          ))
                        ) : (
                          <span style={{ color: '#7A726D', fontSize: '0.875rem' }}>No tags generated.</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default PatientProfile;