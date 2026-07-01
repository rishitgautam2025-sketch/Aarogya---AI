import React, { useState } from 'react';

export default function OnboardingForm({ onSaveSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    city: '', // <--- City added to state
    phone: '',
    caregiver_phone: '',
    chronic_conditions: [],
    custom_triggers: []
  });
  
  const [newTrigger, setNewTrigger] = useState('');

  const availableConditions = [
    "Type 2 Diabetes", 
    "Hypertension", 
    "Asthma", 
    "COPD", 
    "Chronic Kidney Disease",
    "Heart Conditions"
  ];

  const handleConditionChange = (condition) => {
    setFormData(prev => {
      const exists = prev.chronic_conditions.includes(condition);
      const updated = exists 
        ? prev.chronic_conditions.filter(c => c !== condition)
        : [...prev.chronic_conditions, condition];
      return { ...prev, chronic_conditions: updated };
    });
  };

  const addCustomTrigger = () => {
    if (newTrigger.trim() && !formData.custom_triggers.includes(newTrigger.trim().toLowerCase())) {
      setFormData(prev => ({
        ...prev,
        custom_triggers: [...prev.custom_triggers, newTrigger.trim().toLowerCase()]
      }));
      setNewTrigger('');
    }
  };

  const removeCustomTrigger = (indexToRemove) => {
    setFormData(prev => ({
      ...prev,
      custom_triggers: prev.custom_triggers.filter((_, i) => i !== indexToRemove)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`http://localhost:8000/api/onboarding`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          age: parseInt(formData.age, 10) 
        })
      });
      
      if (response.ok) {
        alert('Patient profile saved successfully!');
        if (onSaveSuccess) onSaveSuccess();
      } else {
        const errorData = await response.json();
        alert(`Failed to save: ${errorData.detail || 'Unknown Error'}`);
      }
    } catch (error) {
      console.error('Error submitting form:', error);
      alert('Network error. Check if backend is running.');
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md mt-10">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Aarogya AI: Patient Setup</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* Name, Age, and City Row (Updated to a 4-col grid) */}
        <div className="grid grid-cols-4 gap-4">
          <div className="col-span-2">
            <label className="block text-sm font-semibold text-gray-700 mb-2">Patient Full Name</label>
            <input 
              type="text" 
              required
              placeholder="e.g., Ramesh Kumar"
              className="w-full p-2 border rounded border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
            />
          </div>
          <div className="col-span-1">
            <label className="block text-sm font-semibold text-gray-700 mb-2">Age</label>
            <input 
              type="number" 
              required
              placeholder="e.g., 65"
              className="w-full p-2 border rounded border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.age}
              onChange={(e) => setFormData({...formData, age: e.target.value})}
            />
          </div>
          <div className="col-span-1">
            <label className="block text-sm font-semibold text-gray-700 mb-2">City</label>
            <input 
              type="text" 
              required
              placeholder="e.g., Pune"
              className="w-full p-2 border rounded border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.city}
              onChange={(e) => setFormData({...formData, city: e.target.value})}
            />
          </div>
        </div>

        {/* Phone Numbers Row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Patient WhatsApp Number</label>
            <input 
              type="tel" 
              placeholder="+91XXXXXXXXXX"
              required
              className="w-full p-2 border rounded border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.phone}
              onChange={(e) => setFormData({...formData, phone: e.target.value})}
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Caregiver Phone (Twilio Alert)</label>
            <input 
              type="tel" 
              placeholder="+91XXXXXXXXXX"
              required
              className="w-full p-2 border rounded border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.caregiver_phone}
              onChange={(e) => setFormData({...formData, caregiver_phone: e.target.value})}
            />
          </div>
        </div>

        {/* Chronic Conditions */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Pre-existing Chronic Conditions</label>
          <div className="grid grid-cols-2 gap-3">
            {availableConditions.map((condition) => (
              <label key={condition} className="flex items-center space-x-2 p-2 border rounded cursor-pointer hover:bg-gray-50">
                <input 
                  type="checkbox" 
                  checked={formData.chronic_conditions.includes(condition)}
                  onChange={() => handleConditionChange(condition)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{condition}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Custom Triggers */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Custom Emergency Keywords/Triggers</label>
          <div className="flex gap-2 mb-3">
            <input 
              type="text" 
              placeholder="e.g., blurry vision, chest pressure"
              className="flex-grow p-2 border rounded border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={newTrigger}
              onChange={(e) => setNewTrigger(e.target.value)}
            />
            <button 
              type="button" 
              onClick={addCustomTrigger}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium transition"
            >
              Add
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {formData.custom_triggers.map((trigger, index) => (
              <span key={index} className="flex items-center gap-1 bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm font-medium border">
                {trigger}
                <button 
                  type="button" 
                  onClick={() => removeCustomTrigger(index)}
                  className="text-gray-400 hover:text-red-500 ml-1 font-bold focus:outline-none"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>

        <button 
          type="submit" 
          className="w-full py-3 bg-green-600 text-white rounded font-semibold hover:bg-green-700 transition shadow-sm"
        >
          Initialize Patient Triage System
        </button>
      </form>
    </div>
  );
}