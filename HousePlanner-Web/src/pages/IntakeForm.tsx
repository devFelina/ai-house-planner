import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, Home, Map, DollarSign, Layers, CheckCircle2 } from 'lucide-react';
import { workflowService } from '../services/workflowService';

interface IntakeFormData {
  budget: string;
  landSize: string;
  landUnit: 'perches' | 'sqft';
  terrainType: string;
  photo: File | null;
  bedrooms: string;
  bathrooms: string;
  floors: string;
  architecturalStyle: string;
  plotWidth: string;
  plotLength: string;
  roadSide: string;
  northDirection: string;
  entranceSide: string;
  frontSetback: string;
  rearSetback: string;
  leftSetback: string;
  rightSetback: string;
  openPlan: boolean;
  masterEnsuite: boolean;
  separateDining: boolean;
  homeOffice: boolean;
  balcony: boolean;
  veranda: boolean;
  utilityRoom: boolean;
  parkingRequired: boolean;
  accessibility: boolean;
  spacePriority: string;
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
    bathrooms: '1',
    floors: '1',
    architecturalStyle: 'Modern Minimalist',
    plotWidth: '',
    plotLength: '',
    roadSide: 'south',
    northDirection: 'north',
    entranceSide: 'road_side',
    frontSetback: '', rearSetback: '', leftSetback: '', rightSetback: '',
    openPlan: false, masterEnsuite: false, separateDining: false,
    homeOffice: false, balcony: false, veranda: false, utilityRoom: false,
    parkingRequired: false, accessibility: false, spacePriority: 'balanced',
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

  const handleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData((prev) => ({ ...prev, [name]: checked }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');

    try {
      // Submit through the public gateway; Python remains an internal service.
      const parsedBudget = parseFloat(formData.budget);
      const payload: any = {
        landSizePerches: formData.landUnit === 'perches' ? parseFloat(formData.landSize) : (parseFloat(formData.landSize) / 272.25),
        manualTerrainType: formData.terrainType,
        preferences: {
          bedrooms: parseInt(formData.bedrooms) || 3,
          bathrooms: parseInt(formData.bathrooms) || 1,
          floors: parseInt(formData.floors) || 1,
          architecturalStyle: formData.architecturalStyle,
          openPlan: formData.openPlan,
          masterEnsuite: formData.masterEnsuite,
          separateDining: formData.separateDining,
          homeOffice: formData.homeOffice,
          balcony: formData.balcony,
          veranda: formData.veranda,
          utilityRoom: formData.utilityRoom,
          parkingRequired: formData.parkingRequired,
          accessibility: formData.accessibility,
          spacePriority: formData.spacePriority,
          circulationPreference: 'space_efficient'
        }
      };

      payload.plotConstraints = {
        road_side: formData.roadSide,
        north_direction: formData.northDirection,
        entrance_side: formData.entranceSide === 'road_side' ? formData.roadSide : formData.entranceSide,
        ...(formData.plotWidth ? { plot_width_ft: Number(formData.plotWidth) } : {}),
        ...(formData.plotLength ? { plot_length_ft: Number(formData.plotLength) } : {}),
        setbacks: {
          ...(formData.frontSetback ? { front: Number(formData.frontSetback) } : {}),
          ...(formData.rearSetback ? { rear: Number(formData.rearSetback) } : {}),
          ...(formData.leftSetback ? { left: Number(formData.leftSetback) } : {}),
          ...(formData.rightSetback ? { right: Number(formData.rightSetback) } : {}),
        }
      };
      
      payload.designSeed = crypto.getRandomValues(new Uint32Array(1))[0];

      if (!isNaN(parsedBudget)) {
        payload.budgetLkr = parsedBudget;
      }

      const result = await workflowService.startDesign(payload);
      
      setWorkflowId(result.workflowId);
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
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl rounded-[2rem] border border-white/60 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none max-w-2xl mx-auto transition-colors duration-300">
        <motion.div 
          initial={{ scale: 0, rotate: -180 }} 
          animate={{ scale: 1, rotate: 0 }} 
          transition={{ type: "spring", bounce: 0.5 }}
          className="text-emerald-500 mb-6 bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-full shadow-inner"
        >
          <CheckCircle2 size={64} className="drop-shadow-sm" />
        </motion.div>
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-white mb-3 tracking-tight">AI Plan Generated!</h2>
        <p className="text-zinc-500 dark:text-gray-400 mb-8 text-lg font-medium">
          The AI Architect has processed your requirements and started generating your conceptual floor plan.
        </p>
        <button 
          onClick={() => navigate(`/dashboard/workflows/${workflowId}`)}
          className="group relative flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-bold tracking-wide rounded-2xl hover:from-indigo-700 hover:to-indigo-800 transition-all shadow-[0_4px_14px_0_rgb(79,70,229,0.39)] overflow-hidden"
        >
          <div className="absolute inset-0 w-1/4 h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -skew-x-12 -translate-x-full group-hover:animate-shine"></div>
          <span>Review Floor Plan</span>
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-8 sm:p-10 bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.3)] border border-white/60 dark:border-gray-800/80 relative overflow-hidden transition-colors duration-300">
      {/* Decorative background blur inside the card */}
      <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-100/50 dark:bg-indigo-900/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-50"></div>
      
      <div className="mb-10 relative z-10 text-center">
        <h1 className="text-3xl font-extrabold text-zinc-900 dark:text-white tracking-tight mb-2 transition-colors">New Project Setup</h1>
        <p className="text-base text-zinc-500 dark:text-gray-400 font-medium transition-colors">
          Provide your land details and requirements to initialize the AI planner.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm border border-red-200 dark:border-red-900/50">
          {errorMessage}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* Section 1: Financials & Land */}
        <div className="p-6 bg-zinc-50/80 dark:bg-gray-800/50 rounded-2xl border border-zinc-100/80 dark:border-gray-700/50 space-y-5 relative z-10 hover:shadow-sm transition-all duration-300">
          <h3 className="font-bold text-zinc-900 dark:text-gray-100 flex items-center gap-2.5 text-lg">
            <div className="bg-indigo-100 dark:bg-indigo-900/30 p-2 rounded-lg text-indigo-600 dark:text-indigo-400"><DollarSign size={18} /></div> 
            Budget & Land Constraints
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Total Budget (LKR) <span className="text-gray-400 font-normal">(Optional)</span></label>
              <input 
                type="number" 
                name="budget"
                placeholder="e.g. 15000000"
                value={formData.budget}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
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
                  className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
                />
              </div>
              <div className="w-1/3">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Unit</label>
                <select 
                  name="landUnit" 
                  value={formData.landUnit} 
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                  <option value="perches">Perches</option>
                  <option value="sqft">Sq Ft</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Terrain & Upload */}
        <div className="p-6 bg-zinc-50/80 dark:bg-gray-800/50 rounded-2xl border border-zinc-100/80 dark:border-gray-700/50 space-y-5 relative z-10 hover:shadow-sm transition-all duration-300">
          <h3 className="font-bold text-zinc-900 dark:text-gray-100 flex items-center gap-2.5 text-lg">
            <div className="bg-emerald-100 dark:bg-emerald-900/30 p-2 rounded-lg text-emerald-600 dark:text-emerald-400"><Map size={18} /></div>
            Terrain & Topography
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Upload Land Photo (Optional)</label>
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 dark:border-gray-700 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-8 h-8 mb-3 text-gray-400 dark:text-gray-500" />
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
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Upload a clear land photo to help AI identify terrain characteristics. If no photo is available, choose the terrain manually.</p>
              <select 
                name="terrainType"
                value={formData.terrainType}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
              >
                <option value="flat/urban">Flat / Urban</option>
                <option value="hillside">Hillside / Sloped</option>
                <option value="coastal">Coastal</option>
                <option value="forested">Forested</option>
              </select>
            </div>
          </div>
        </div>

        <div className="p-6 bg-zinc-50/80 dark:bg-gray-800/50 rounded-2xl border border-zinc-100/80 dark:border-gray-700/50 space-y-5 relative z-10 hover:shadow-sm transition-all duration-300">
          <h3 className="font-bold text-zinc-900 dark:text-gray-100 flex items-center gap-2.5 text-lg">
            <div className="bg-orange-100 dark:bg-orange-900/30 p-2 rounded-lg text-orange-600 dark:text-orange-400"><Layers size={18} /></div>
            Plot Constraints (Optional)
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 -mt-2">Missing dimensions will be estimated for conceptual planning.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Plot Width (ft)</label>
              <input 
                name="plotWidth" 
                type="number" 
                min="1" 
                step="any"
                value={formData.plotWidth} 
                onChange={handleInputChange} 
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors" 
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Plot Length (ft)</label>
              <input 
                name="plotLength" 
                type="number" 
                min="1" 
                step="any"
                value={formData.plotLength} 
                onChange={handleInputChange} 
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors" 
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Road Side</label>
              <select 
                name="roadSide" 
                value={formData.roadSide} 
                onChange={handleInputChange} 
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
              >
                {['south', 'north', 'east', 'west'].map(side => <option key={side} value={side}>{side.charAt(0).toUpperCase() + side.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">North Direction / Orientation</label>
              <select name="northDirection" value={formData.northDirection} onChange={handleInputChange} className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500">
                {['north', 'east', 'south', 'west'].map(side => <option key={side} value={side}>{side[0].toUpperCase() + side.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Main Access / Entrance Side</label>
              <select name="entranceSide" value={formData.entranceSide} onChange={handleInputChange} className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500">
                <option value="road_side">Road Side</option>
                {['north', 'east', 'south', 'west'].map(side => <option key={side} value={side}>{side[0].toUpperCase() + side.slice(1)}</option>)}
              </select>
            </div>
          </div>

          <details className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <summary className="cursor-pointer font-semibold text-sm text-gray-700 dark:text-gray-200">Plot Setbacks (Optional)</summary>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Conceptual planning values only.</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
              {([['frontSetback', 'Front'], ['rearSetback', 'Rear'], ['leftSetback', 'Left'], ['rightSetback', 'Right']] as const).map(([name, label]) => (
                <label key={name} className="text-xs text-gray-600 dark:text-gray-300">{label} (ft)
                  <input name={name} type="number" min="0" step="any" value={formData[name]} onChange={handleInputChange} className="mt-1 w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900" />
                </label>
              ))}
            </div>
          </details>
        </div>

        {/* Section 3: Design Preferences */}
        <div className="p-6 bg-zinc-50/80 dark:bg-gray-800/50 rounded-2xl border border-zinc-100/80 dark:border-gray-700/50 space-y-5 relative z-10 hover:shadow-sm transition-all duration-300">
          <h3 className="font-bold text-zinc-900 dark:text-gray-100 flex items-center gap-2.5 text-lg">
            <div className="bg-purple-100 dark:bg-purple-900/30 p-2 rounded-lg text-purple-600 dark:text-purple-400"><Home size={18} /></div>
            Design Preferences
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Bedrooms</label>
              <input 
                type="number" 
                name="bedrooms"
                min="1"
                required
                value={formData.bedrooms}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Bathrooms</label>
              <input type="number" name="bathrooms" min="1" max="6" required value={formData.bathrooms} onChange={handleInputChange} className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500" />
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
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Architectural Style</label>
              <select 
                name="architecturalStyle"
                value={formData.architecturalStyle}
                onChange={handleInputChange}
                className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 transition-colors"
              >
                <option value="Modern Minimalist">Modern Minimalist</option>
                <option value="Contemporary">Contemporary</option>
                <option value="Traditional">Traditional Sri Lankan</option>
                <option value="Tropical Modernism">Tropical Modernism</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Space Priority</label>
            <select name="spacePriority" value={formData.spacePriority} onChange={handleInputChange} className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500">
              <option value="compact_cost_efficient">Compact &amp; Cost Efficient</option><option value="balanced">Balanced</option>
              <option value="spacious_living">Spacious Living Areas</option><option value="larger_bedrooms">Larger Bedrooms</option>
              <option value="outdoor_garden">Outdoor / Garden Priority</option>
            </select>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {([['openPlan', 'Open-plan Living / Dining'], ['masterEnsuite', 'Master Bedroom with Attached Bathroom'],
              ['separateDining', 'Separate Dining Area'], ['homeOffice', 'Home Office'], ['balcony', 'Balcony'],
              ['veranda', 'Veranda'], ['utilityRoom', 'Utility / Laundry'], ['parkingRequired', 'Parking Required'],
              ['accessibility', 'Accessible / Reduced-Step Layout']] as const).map(([name, label]) => (
              <label key={name} className="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm text-gray-700 dark:text-gray-200">
                <input type="checkbox" name={name} checked={formData[name]} onChange={handleToggle} className="h-4 w-4 accent-indigo-600" />{label}
              </label>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end pt-6 relative z-10">
          <button 
            type="submit" 
            disabled={isSubmitting}
            className="group relative flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 bg-zinc-900 dark:bg-white hover:bg-zinc-800 dark:hover:bg-gray-200 text-white dark:text-zinc-900 font-bold rounded-2xl transition-all shadow-[0_4px_14px_0_rgba(0,0,0,0.1)] overflow-hidden disabled:opacity-70 disabled:cursor-not-allowed"
          >
            <div className="absolute inset-0 w-1/4 h-full bg-gradient-to-r from-transparent via-white/10 dark:via-black/10 to-transparent -skew-x-12 -translate-x-full group-hover:animate-shine"></div>
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <Layers className="animate-spin text-indigo-400 dark:text-indigo-600" size={20} /> 
                <span className="tracking-wide">Processing Details...</span>
              </span>
            ) : (
              <span className="tracking-wide">Generate AI Plan</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default IntakeForm;
