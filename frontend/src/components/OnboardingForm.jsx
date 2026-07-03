import React from 'react';

const OnboardingForm = ({ onSaveSuccess }) => {
  
  const inputStyle = {
    width: '100%',
    padding: '0.75rem 1rem',
    borderRadius: '8px',
    border: '1px solid #EBE6E1',
    backgroundColor: '#FBF9F6',
    color: '#2B2624',
    fontSize: '1rem',
    boxSizing: 'border-box',
    marginTop: '0.25rem'
  };

  const labelStyle = {
    fontSize: '0.875rem',
    fontWeight: 'bold',
    color: '#7A726D',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  };

  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      
      <div style={{ backgroundColor: '#FFFFFF', padding: '2rem', borderRadius: '16px', border: '1px solid #EBE6E1', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
        <h2 style={{ fontSize: '1.875rem', color: '#2B2624', margin: '0 0 0.5rem 0' }}>Patient Registration</h2>
        <p style={{ color: '#7A726D', margin: '0 0 2rem 0', fontSize: '1.125rem' }}>Initialize a new patient for AI monitoring</p>

        <form style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Top Row: Name & Age */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
            <div>
              <label style={labelStyle}>Patient Full Name</label>
              <input type="text" placeholder="e.g., Ramesh Kumar" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Age</label>
              <input type="number" placeholder="e.g., 65" style={inputStyle} />
            </div>
          </div>

          {/* Location & Contacts */}
          <div>
            <label style={labelStyle}>City</label>
            <input type="text" placeholder="e.g., Pune" style={inputStyle} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={labelStyle}>Patient WhatsApp</label>
              <input type="text" placeholder="+91XXXXXXXXXX" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Caregiver Phone (Twilio Alert)</label>
              <input type="text" placeholder="+91XXXXXXXXXX" style={inputStyle} />
            </div>
          </div>

          {/* Chronic Conditions */}
          <div style={{ padding: '1.5rem', backgroundColor: '#F4F1ED', borderRadius: '8px', border: '1px solid #EBE6E1' }}>
            <label style={{...labelStyle, color: '#2B2624'}}>Pre-existing Chronic Conditions</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '1rem' }}>
              {['Type 2 Diabetes', 'Hypertension', 'Asthma', 'COPD', 'Kidney Disease', 'Heart Conditions'].map(condition => (
                <label key={condition} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#4B4543', fontSize: '0.95rem', cursor: 'pointer' }}>
                  <input type="checkbox" style={{ width: '16px', height: '16px', accentColor: '#2B2624' }} />
                  {condition}
                </label>
              ))}
            </div>
          </div>

          {/* Custom Triggers */}
          <div>
            <label style={labelStyle}>Custom Emergency Triggers</label>
            <p style={{ fontSize: '0.85rem', color: '#7A726D', margin: '0.25rem 0 0.75rem 0' }}>The AI will immediately call the caregiver if these specific keywords are mentioned.</p>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input type="text" placeholder="e.g., blurry vision, severe chest pressure" style={inputStyle} />
              <button type="button" style={{ marginTop: '0.25rem', padding: '0 1.5rem', backgroundColor: '#2B2624', color: '#FFFFFF', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Add</button>
            </div>
          </div>

          {/* Submit Button */}
          <button 
            type="button" 
            onClick={onSaveSuccess}
            style={{ 
              marginTop: '1rem',
              padding: '1rem', 
              backgroundColor: '#10B981', 
              color: '#FFFFFF', 
              border: 'none', 
              borderRadius: '8px', 
              fontSize: '1.125rem', 
              fontWeight: 'bold', 
              cursor: 'pointer',
              boxShadow: '0 4px 6px rgba(16, 185, 129, 0.2)'
            }}
          >
            Initialize Patient Triage System
          </button>
        </form>

      </div>
    </div>
  );
};

export default OnboardingForm;