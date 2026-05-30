import React, { useState } from 'react';
import { api } from '../api'; // Make sure this path is correct for your project!

export default function LogHealthModal({ elderId, onClose, onSuccess }) {

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const FEELING_OPTIONS = ['Very Good', 'Good', 'Okay', 'Poor', 'Very Poor'];
  const APPETITE_OPTIONS = ['Normal', 'Reduced', 'Not Eating'];
  const MOBILITY_OPTIONS = ['Normal', 'Reduced', 'Cannot Get Up'];
  const [form, setForm] = useState({
    feeling_today: '',
    appetite: '',
    mobility: '',
    had_fall: false,
    new_pain: false,
    new_pain_location: '',
    temperature: '',
    blood_pressure_systolic: '',
    blood_pressure_diastolic: '',
    symptoms: [],
    symptom_severity: 'mild',
    notes: '',
  });

  const [currentSymptom, setCurrentSymptom] = useState('');
 

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleAddSymptom = (e) => {
    if (e.key === 'Enter' && currentSymptom.trim()) {
      e.preventDefault();
      if (!form.symptoms.includes(currentSymptom.trim())) {
        setForm(prev => ({
          ...prev,
          symptoms: [...prev.symptoms, currentSymptom.trim()]
        }));
      }
      setCurrentSymptom('');
    }
  };

  const removeSymptom = (sym) => {
    setForm(prev => ({
      ...prev,
      symptoms: prev.symptoms.filter(s => s !== sym)
    }));
  };

  const handleSubmit = async (e) => {
      e.preventDefault();
      
      // Clear old messages
      setErrorMsg('');
      setSuccessMsg('');

      // --- 1. FRONTEND VALIDATION ---
      // Only validate if they actually typed a number into the boxes
      if (form.temperature) {
          const temp = parseFloat(form.temperature);
          if (temp < 30 || temp > 45) {
              setErrorMsg("Validation Error: Please enter a realistic human temperature (30°C - 45°C).");
              return;
          }
      }
      
      if (form.heart_rate) {
          const hr = parseInt(form.heart_rate);
          if (hr < 20 || hr > 250) {
              setErrorMsg("Validation Error: Please enter a realistic heart rate.");
              return;
          }
      }

      // --- 2. TRIGGER LOADING STATE ---
      setIsSubmitting(true);

      try {
          // Format the payload exactly like your original code
          const payload = {
              elder_id: elderId,
              ...form,
              // Convert strings to numbers for clinical vitals if they exist
              temperature: form.temperature ? parseFloat(form.temperature) : null,
              blood_pressure_systolic: form.blood_pressure_systolic ? parseFloat(form.blood_pressure_systolic) : null,
              blood_pressure_diastolic: form.blood_pressure_diastolic ? parseFloat(form.blood_pressure_diastolic) : null,
          };

          // Your original API call!
          const res = await api.logHealth(payload);

          // --- 3. SUCCESS FEEDBACK ---
          setSuccessMsg("✅ Health data analyzed and logged successfully!");
          
          // Trigger the dashboard refresh in App.jsx
          onSuccess(res.data); 

          // Wait 1.5 seconds so the user can see the green success message, then close the modal
          setTimeout(() => {
              onClose(); 
          }, 1500);

      } catch (err) {
          // --- 4. FRIENDLY ERROR HANDLING ---
          console.error("Error logging health:", err);
          setErrorMsg("❌ Oops! We couldn't reach the Aarogya AI server. Please check your connection.");
      } finally {
          setIsSubmitting(false);
      }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b sticky top-0 bg-white z-10 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-800">Daily Health Check-in</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-800 text-2xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-8">
          
          {/* SECTION 1: The 30-Second Check-in */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-700 border-b pb-2">General Wellbeing</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">How are they feeling?</label>
                <select name="feeling_today" value={form.feeling_today} onChange={handleChange} className="w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500">
                  <option value="">Select...</option>
                  {FEELING_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Appetite today?</label>
                <select name="appetite" value={form.appetite} onChange={handleChange} className="w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500">
                  <option value="">Select...</option>
                  {APPETITE_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Mobility</label>
                <select name="mobility" value={form.mobility} onChange={handleChange} className="w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500">
                  <option value="">Select...</option>
                  {MOBILITY_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-6 pt-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input type="checkbox" name="had_fall" checked={form.had_fall} onChange={handleChange} className="w-5 h-5 text-red-600 rounded" />
                <span className="text-gray-700 font-medium">Experienced a fall today</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input type="checkbox" name="new_pain" checked={form.new_pain} onChange={handleChange} className="w-5 h-5 text-orange-500 rounded" />
                <span className="text-gray-700 font-medium">Reporting new pain</span>
              </label>
            </div>

            {form.new_pain && (
              <div className="mt-2">
                <label className="block text-sm font-medium text-gray-600 mb-1">Where is the pain?</label>
                <input type="text" name="new_pain_location" value={form.new_pain_location} onChange={handleChange} placeholder="e.g., lower back, right knee" className="w-full p-2 border rounded" />
              </div>
            )}
          </div>

          {/* SECTION 2: Symptoms */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-700 border-b pb-2">Symptoms</h3>
            <div>
              <input 
                type="text" 
                value={currentSymptom} 
                onChange={(e) => setCurrentSymptom(e.target.value)} 
                onKeyDown={handleAddSymptom}
                placeholder="Type a symptom and press Enter (e.g., fever, dizziness)" 
                className="w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="flex flex-wrap gap-2 mt-3">
                {form.symptoms.map(sym => (
                  <span key={sym} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm flex items-center">
                    {sym}
                    <button type="button" onClick={() => removeSymptom(sym)} className="ml-2 text-blue-600 hover:text-blue-900 font-bold">&times;</button>
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* SECTION 3: Clinical Data (Optional) */}
          <div className="space-y-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Clinical Vitals (Optional)</h3>
            <p className="text-xs text-gray-400 mb-3">For use by healthcare workers with diagnostic equipment.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Temperature (°C)</label>
                <input type="number" step="0.1" name="temperature" value={form.temperature} onChange={handleChange} placeholder="e.g. 37.5" className="w-full p-2 border rounded" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">BP Systolic</label>
                <input type="number" name="blood_pressure_systolic" value={form.blood_pressure_systolic} onChange={handleChange} placeholder="e.g. 120" className="w-full p-2 border rounded" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">BP Diastolic</label>
                <input type="number" name="blood_pressure_diastolic" value={form.blood_pressure_diastolic} onChange={handleChange} placeholder="e.g. 80" className="w-full p-2 border rounded" />
              </div>
            </div>
          </div>

          {/* SECTION 4: Notes & Submit */}
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Additional Notes</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} rows="2" className="w-full p-2 border rounded" placeholder="Any other observations..."></textarea>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded text-gray-600 hover:bg-gray-50 font-medium disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={isSubmitting} className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium shadow-sm transition-colors disabled:opacity-50">
              {isSubmitting ? 'Saving...' : 'Save Health Log'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}