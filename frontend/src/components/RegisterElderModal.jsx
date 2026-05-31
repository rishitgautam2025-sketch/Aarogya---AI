import React, { useState } from 'react';
import PhoneInput from 'react-phone-number-input';
import 'react-phone-number-input/style.css'; // Don't forget the CSS!
import { API_URL } from '../api';

const RegisterElderModal = ({ onClose }) => {
  const [name, setName] = useState("");
  // 'phone' will now automatically hold the E.164 format (e.g., "+919876543210")
  const [phone, setPhone] = useState(""); 

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const elderData = { 
      name: name, 
      phone: phone 
    };
    
    console.log("Sending clean data to backend:", elderData);
    
    try {
      // 1. Send the data to FastAPI
      const response = await fetch(`${API_URL}/api/elders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(elderData),
      });

      if (response.ok) {
        console.log("Success! Elder saved to database.");
        
        // 2. Close the modal
        if (onClose) onClose();
        
        // 3. Refresh the page so the 404 disappears and the dashboard loads!
        window.location.reload(); 
      } else {
        console.error("Backend rejected the registration.");
      }
    } catch (error) {
      console.error("Failed to connect to backend:", error);
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
      <div className="p-6 bg-white rounded-lg shadow-xl w-96">
        <h2 className="mb-4 text-xl font-bold">Register an Elder</h2>
        
        <form onSubmit={handleSubmit}>
          {/* Standard Name Input */}
          <input 
            type="text" 
            placeholder="Elder's Name (e.g., Prachi)" 
            className="w-full p-2 mb-4 border rounded text-slate-900 placeholder-slate-400"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          {/* Upgraded Phone Input with Country Code */}
          <div className="mb-6">
            <PhoneInput
              placeholder="Enter WhatsApp number"
              defaultCountry="IN"
              value={phone}
              onChange={setPhone}
              className="w-full p-2 border rounded text-slate-900 placeholder-slate-400" // Tailwind styles work here too
            />
          </div>

          <div className="flex justify-end gap-2">
            <button 
              type="button" 
              onClick={onClose} 
              className="px-4 py-2 text-gray-600 bg-gray-200 rounded"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700"
            >
              Register
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RegisterElderModal;