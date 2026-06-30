import { useEffect, useState } from 'react'
import { supabase } from './supabase'

export default function App() {
  const [patientLogs, setPatientLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  async function fetchDashboardData() {
    try {
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

  if (loading) return <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>Loading Aarogya AI Dashboard...</div>

 return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ color: '#111827', marginBottom: '0.5rem' }}>Aarogya AI Dashboard</h1>
      <p style={{ color: '#6b7280', marginBottom: '2rem' }}>Live patient updates from WhatsApp</p>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {patientLogs.map(log => (
          <div key={log.id} style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '12px', backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', color: '#6b7280', fontSize: '0.875rem' }}>
              <span>Patient ID: {log.patient_id.substring(0, 8)}...</span>
              <span>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            
            {/* 1. Transcript */}
            <p style={{ fontSize: '1.125rem', color: '#1f2937', marginBottom: '1rem', lineHeight: '1.5' }}>
              "{log.raw_text}"
            </p>

            {/* 2. Audio Playback - The Core Feature */}
            {log.audio_url && (
              <div style={{ marginBottom: '1.5rem', backgroundColor: '#f3f4f6', padding: '0.5rem', borderRadius: '8px' }}>
                <audio controls src={log.audio_url} style={{ width: '100%' }} />
              </div>
            )}
            
            {/* 3. Symptom Tags */}
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {log.symptoms.map(tag => (
                <span 
                  key={tag.id} 
                  style={{ 
                    padding: '0.35rem 0.75rem', 
                    borderRadius: '9999px', 
                    fontSize: '0.875rem',
                    backgroundColor: tag.tag_type === 'NEW SYMPTOM' ? '#fee2e2' : '#e0e7ff',
                    color: tag.tag_type === 'NEW SYMPTOM' ? '#991b1b' : '#3730a3',
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
    </div>
  )
}