import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, Home, Map, DollarSign, Layers, CheckCircle2 } from 'lucide-react';

interface IntakeFormData {
  budget: string;
  landSize: string;
  landUnit: 'perches' | 'sqft';
  terrainType: string;
  photo: File | null;
  bedrooms: string;
  floors: string;
  architecturalStyle: string;
}

const IntakeForm: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<IntakeFormData>({
    budget: '',
    landSize: '',
    landUnit: 'perches',
    terrainType: 'flat/urban',
    photo: null,
    bedrooms: '3',
    floors: '1',
    architecturalStyle: 'Modern Minimalist',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData((prev) => ({ ...prev, photo: e.target.files![0] }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');

    try {
      // Construct payload for Python Agentic Service
      const payload = {
        submission_id: crypto.randomUUID(),
        budget_lkr: parseFloat(formData.budget) || 15000000,
        land_size_perches: formData.landUnit === 'perches' ? parseFloat(formData.landSize) : (parseFloat(formData.landSize) / 272.25),
        manual_terrain_type: formData.terrainType,
        preferences: {
          bedrooms: parseInt(formData.bedrooms) || 3,
          floors: parseInt(formData.floors) || 1,
          architecturalStyle: formData.architecturalStyle
        }
      };

      // Call Python LangGraph API directly to start the workflow
      const response = await fetch('http://127.0.0.1:8001/workflows/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Internal-API-Key': 'shared-internal-secret' // Required by Python API
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to connect to the backend server.');
      }

      const result = await response.json();
      console.log('AI Coordinator Result:', result);
      
      setWorkflowId(result.workflow_id);
      setIsSuccess(true);
    } catch (error: any) {
      console.error('Error submitting form:', error);
      setErrorMessage(error.message || 'An error occurred while connecting to the server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSuccess && workflowId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="text-green-500 mb-4">
          <CheckCircle2 size={64} />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">AI Plan Generated!</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          The AI Architect has processed your requirements and generated a 2D structural floor plan.
        </p>
        <button 
          onClick={() => navigate(`/dashboard/workflows/${workflowId}`)}
          className="px-6 py-3 bg-indigo-600 text-white font-bold tracking-wide rounded-lg hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/30"
        >
          Review Floor Plan
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6 bg-white dark:bg-gray-900 rounded-2xl custom-shadow-md border border-gray-100 dark:border-gray-800">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">New Home Project Setup</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Component A: Provide your budget and land details to initialize the AI planner.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg text-sm border border-red-200">
          {errorMessage}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* Section 1: Financials & Land */}
        <div className="p-5 bg-gray-50 dark:bg-gray-800/50 rounded-xl space-y-4">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <DollarSign size={18} className="text-indigo-500" /> Budget & Land Constraints
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Total Budget (LKR)</label>
              <input 
                type="number" 
                name="budget"
                required
                placeholder="e.g. 15000000"
                value={formData.budget}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Land Size</label>
                <input 
                  type="number" 
                  name="landSize"
                  required
                  placeholder="e.g. 10"
                  value={formData.landSize}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="w-1/3">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Unit</label>
                <select 
                  name="landUnit" 
                  value={formData.landUnit} 
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="perches">Perches</option>
                  <option value="sqft">Sq Ft</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Terrain & Upload */}
        <div className="p-5 bg-gray-50 dark:bg-gray-800/50 rounded-xl space-y-4">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Map size={18} className="text-green-500" /> Terrain & Topography
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Upload Land Photo (Optional)</label>
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-8 h-8 mb-3 text-gray-400" />
                    <p className="text-xs text-gray-500 dark:text-gray-400 text-center px-2">
                      {formData.photo ? formData.photo.name : "Click to upload or drag and drop"}
                    </p>
                  </div>
                  <input type="file" className="hidden" accept="image/*" onChange={handleFileChange} />
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Terrain Fallback Type</label>
              <p className="text-xs text-gray-500 mb-2">Used if photo is missing or AI vision fails.</p>
              <select 
                name="terrainType"
                value={formData.terrainType}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              >
                <option value="flat/urban">Flat / Urban</option>
                <option value="hillside">Hillside / Sloped</option>
                <option value="coastal">Coastal</option>
                <option value="forested">Forested</option>
              </select>
            </div>
          </div>
        </div>

        {/* Section 3: Design Preferences */}
        <div className="p-5 bg-gray-50 dark:bg-gray-800/50 rounded-xl space-y-4">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Home size={18} className="text-purple-500" /> Design Preferences
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Bedrooms</label>
              <input 
                type="number" 
                name="bedrooms"
                min="1"
                required
                value={formData.bedrooms}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Floors</label>
              <input 
                type="number" 
                name="floors"
                min="1"
                required
                value={formData.floors}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Architectural Style</label>
              <select 
                name="architecturalStyle"
                value={formData.architecturalStyle}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              >
                <option value="Modern Minimalist">Modern Minimalist</option>
                <option value="Contemporary">Contemporary</option>
                <option value="Traditional">Traditional Sri Lankan</option>
                <option value="Tropical Modernism">Tropical Modernism</option>
              </select>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end pt-4">
          <button 
            type="submit" 
            disabled={isSubmitting}
            className="flex items-center gap-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition shadow-lg shadow-indigo-200 dark:shadow-none disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <Layers className="animate-spin" size={18} /> Processing...
              </span>
            ) : (
              "Generate AI Plan"
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default IntakeForm;