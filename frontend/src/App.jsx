import React, { useEffect, useState } from 'react'
import { supabase } from './supabase'
import OnboardingForm from './components/OnboardingForm'
import PatientProfile from './components/PatientProfile'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard') 
  const [patientLogs, setPatientLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  async function fetchDashboardData() {
    try {
      setLoading(true)
      const { data: logsData, error: logsError } = await supabase
        .from('voice_logs')
        .select('*')
        .order('created_at', { ascending: false })

      const { data: tagsData, error: tagsError } = await supabase
        .from('symptom_tags')
        .select('*')

      if (logsError) throw logsError
      if (tagsError) throw tagsError

      const combinedLogs = logsData.map(log => ({
        ...log,
        symptoms: tagsData.filter(tag => tag.log_id === log.id)
      }))

      setPatientLogs(combinedLogs)
    } catch (error) {
      console.error('Error fetching data:', error.message)
    } finally {
      setLoading(false)
    }
  }

  // Helper for Nav Buttons
  const getNavStyle = (tabName) => ({
    padding: '0.6rem 1.5rem',
    borderRadius: '99px',
    border: 'none',
    fontWeight: '600',
    cursor: 'pointer',
    fontSize: '0.95rem',
    backgroundColor: activeTab === tabName ? '#2B2624' : 'transparent',
    color: activeTab === tabName ? '#FFFFFF' : '#7A726D',
    transition: 'all 0.2s ease-in-out'
  })

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FBF9F6', fontFamily: 'sans-serif' }}>
      
      {/* --- PREMIUM NAVIGATION BAR --- */}
      <div style={{ backgroundColor: '#FFFFFF', borderBottom: '1px solid #EBE6E1', padding: '1rem 2rem', position: 'sticky', top: 0, zIndex: 50, boxShadow: '0 2px 10px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        
        {/* 1. THE VYTERA LOGO (Left Aligned) */}
        <div style={{ width: '200px' }}>
          <img 
            src="/vytera-logo.png" 
            alt="Vytera Logo" 
            style={{ height: '45px', width: 'auto', objectFit: 'contain' }} 
          />
        </div>

        {/* 2. THE NAV BUTTONS (Center Aligned) */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', backgroundColor: '#F4F1ED', padding: '0.35rem', borderRadius: '99px' }}>
          <button onClick={() => setActiveTab('dashboard')} style={getNavStyle('dashboard')}>Live Dashboard</button>
          <button onClick={() => setActiveTab('setup')} style={getNavStyle('setup')}>Patient Setup</button>
          <button onClick={() => setActiveTab('profile')} style={getNavStyle('profile')}>Patient Profile</button>
        </div>

        {/* 3. INVISIBLE SPACER (Keeps the buttons perfectly centered) */}
        <div style={{ width: '200px' }}></div>
        
      </div>

      {/* --- MAIN CONTENT AREA --- */}
      <div style={{ padding: '2rem' }}>
        
        {/* VIEW 1: THE DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFFFFF', padding: '1.5rem', borderRadius: '16px', border: '1px solid #EBE6E1' }}>
              <div>
                <h1 style={{ color: '#2B2624', margin: '0 0 0.25rem 0', fontSize: '1.875rem' }}>Global Triage Feed</h1>
                <p style={{ color: '#7A726D', margin: '0', fontSize: '1.125rem' }}>Monitoring all incoming WhatsApp alerts</p>
              </div>
              <button 
                onClick={fetchDashboardData}
                style={{ padding: '0.6rem 1.25rem', backgroundColor: '#F4F1ED', color: '#2B2624', border: '1px solid #EBE6E1', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                <span style={{ fontSize: '1.2rem' }}>↻</span> Refresh Feed
              </button>
            </div>
            
            {loading ? (
              <div style={{ textAlign: 'center', color: '#7A726D', padding: '3rem', backgroundColor: '#FFFFFF', borderRadius: '16px', border: '1px solid #EBE6E1' }}>Syncing with Supabase...</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {patientLogs.map(log => {
                  const isCritical = log.symptoms.some(tag => tag.tag_type === 'NEW_SYMPTOM')
                  
                  return (
                    <div key={log.id} style={{ padding: '1.5rem', border: isCritical ? '1px solid #F8D7DA' : '1px solid #EBE6E1', borderLeft: isCritical ? '4px solid #B91C1C' : '1px solid #EBE6E1', borderRadius: '16px', backgroundColor: '#FFFFFF', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
                      
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', color: '#7A726D', fontSize: '0.875rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        <span>Patient ID: {log.patient_id.substring(0, 8)}</span>
                        <span>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      
                      <p style={{ fontSize: '1.125rem', color: '#2B2624', marginBottom: '1rem', lineHeight: '1.6' }}>
                        "{log.raw_text}"
                      </p>

                      {log.audio_url && (
                        <div style={{ marginBottom: '1.5rem', backgroundColor: '#F4F1ED', padding: '0.75rem', borderRadius: '8px' }}>
                          <audio controls src={log.audio_url} style={{ width: '100%', height: '36px' }} />
                        </div>
                      )}
                      
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {log.symptoms.map(tag => (
                          <span 
                            key={tag.id} 
                            style={{ 
                              padding: '0.35rem 0.75rem', 
                              borderRadius: '6px', 
                              fontSize: '0.875rem',
                              backgroundColor: tag.tag_type === 'NEW_SYMPTOM' ? '#FEF2F2' : '#F4F1ED',
                              color: tag.tag_type === 'NEW_SYMPTOM' ? '#B91C1C' : '#2B2624',
                              fontWeight: '600'
                            }}
                          >
                            {tag.label}
                          </span>
                        ))}
                        {log.symptoms.length === 0 && (
                          <span style={{ color: '#7A726D', fontStyle: 'italic', fontSize: '0.875rem' }}>No critical symptoms extracted</span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: THE ONBOARDING / SETUP FORM */}
        {activeTab === 'setup' && (
          <OnboardingForm 
            elderId="12345" 
            onSaveSuccess={() => setActiveTab('dashboard')} 
          />
        )}

        {/* VIEW 3: THE PATIENT PROFILE */}
        {activeTab === 'profile' && (
          <PatientProfile logs={patientLogs} />
        )}

      </div>
    </div>
  )
}