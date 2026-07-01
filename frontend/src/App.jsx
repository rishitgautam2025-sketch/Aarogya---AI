import React, { useEffect, useState } from 'react'
import { supabase } from './supabase'
import OnboardingForm from './components/OnboardingForm'
import useNavigate from react-router-dom

export default function App() {
  // Navigation State
  const [activeTab, setActiveTab] = useState('dashboard') // 'dashboard' or 'setup'

  // Dashboard State
  const [patientLogs, setPatientLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  async function fetchDashboardData() {
    try {
      setLoading(true)
      // 1. Fetch the raw voice notes
      const { data: logsData, error: logsError } = await supabase
        .from('voice_logs')
        .select('*')
        .order('created_at', { ascending: false })

      // 2. Fetch the extracted AI tags
      const { data: tagsData, error: tagsError } = await supabase
        .from('symptom_tags')
        .select('*')

      if (logsError) throw logsError
      if (tagsError) throw tagsError

      // 3. Match the tags to their respective WhatsApp logs
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

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', paddingBottom: '2rem' }}>
      {/* --- TOP NAVIGATION BAR --- */}
      <div style={{ backgroundColor: '#ffffff', borderBottom: '1px solid #e5e7eb', padding: '1rem 2rem', marginBottom: '2rem', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
        <button 
          onClick={() => setActiveTab('dashboard')}
          style={{ 
            padding: '0.5rem 1.5rem', 
            borderRadius: '8px', 
            border: 'none',
            fontWeight: 'bold',
            cursor: 'pointer',
            backgroundColor: activeTab === 'dashboard' ? '#2563eb' : '#f3f4f6',
            color: activeTab === 'dashboard' ? '#ffffff' : '#4b5563',
            transition: 'all 0.2s'
          }}
        >
          Live Dashboard
        </button>
        <button 
          onClick={() => setActiveTab('setup')}
          style={{ 
            padding: '0.5rem 1.5rem', 
            borderRadius: '8px', 
            border: 'none',
            fontWeight: 'bold',
            cursor: 'pointer',
            backgroundColor: activeTab === 'setup' ? '#2563eb' : '#f3f4f6',
            color: activeTab === 'setup' ? '#ffffff' : '#4b5563',
            transition: 'all 0.2s'
          }}
        >
          Patient Setup
        </button>
      </div>

      {/* --- MAIN CONTENT AREA --- */}
      
      {/* VIEW 1: THE DASHBOARD */}
      {activeTab === 'dashboard' && (
        <div style={{ padding: '0 2rem', fontFamily: 'sans-serif', maxWidth: '800px', margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <div>
              <h1 style={{ color: '#111827', marginBottom: '0.5rem' }}>Aarogya AI Dashboard</h1>
              <p style={{ color: '#6b7280', margin: '0' }}>Live patient updates from WhatsApp</p>
            </div>
            <button 
              onClick={fetchDashboardData}
              style={{ padding: '0.5rem 1rem', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              ↻ Refresh
            </button>
          </div>
          
          {loading ? (
             <div style={{ textAlign: 'center', color: '#6b7280', marginTop: '2rem' }}>Loading patient logs...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {patientLogs.map(log => (
                <div key={log.id} style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '12px', backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', color: '#6b7280', fontSize: '0.875rem' }}>
                    <span>Patient ID: {log.patient_id.substring(0, 8)}...</span>
                    <span>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  
                  {/* Transcript */}
                  <p style={{ fontSize: '1.125rem', color: '#1f2937', marginBottom: '1rem', lineHeight: '1.5' }}>
                    "{log.raw_text}"
                  </p>

                  {/* Audio Playback */}
                  {log.audio_url && (
                    <div style={{ marginBottom: '1.5rem', backgroundColor: '#f3f4f6', padding: '0.5rem', borderRadius: '8px' }}>
                      <audio controls src={log.audio_url} style={{ width: '100%' }} />
                    </div>
                  )}
                  
                  {/* Symptom Tags */}
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {log.symptoms.map(tag => (
                      <span 
                        key={tag.id} 
                        style={{ 
                          padding: '0.35rem 0.75rem', 
                          borderRadius: '9999px', 
                          fontSize: '0.875rem',
                          backgroundColor: tag.tag_type === 'NEW_SYMPTOM' ? '#fee2e2' : '#e0e7ff',
                          color: tag.tag_type === 'NEW_SYMPTOM' ? '#991b1b' : '#3730a3',
                          fontWeight: '600'
                        }}
                      >
                        {tag.label}
                      </span>
                    ))}
                    
                    {log.symptoms.length === 0 && (
                      <span style={{ color: '#9ca3af', fontStyle: 'italic', fontSize: '0.875rem' }}>No critical symptoms extracted</span>
                    )}
                  </div>
                </div>
              ))}
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
    </div>
  )
}