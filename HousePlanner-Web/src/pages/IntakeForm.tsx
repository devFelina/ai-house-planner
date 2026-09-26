import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Map, CheckCircle2, ChevronRight, ChevronLeft, Home, Expand, Compass, Check, CheckSquare, Info } from 'lucide-react';
import { workflowService } from '../services/workflowService';

interface IntakeFormData {
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
 targetDate: string;
}

const IntakeForm: React.FC = () => {
 const navigate = useNavigate();
 const [searchParams] = useSearchParams();
 const location = useLocation();
 const prefill = location.state?.prefill || {};

 const [formData, setFormData] = useState<IntakeFormData>({
  landSize: prefill.land_size ? String(prefill.land_size) : '',
  landUnit: prefill.land_unit === 'sqft' ? 'sqft' : 'perches',
  terrainType: prefill.terrain_type || 'flat/urban',
  photo: null,
  bedrooms: prefill.bedrooms ? String(prefill.bedrooms) : searchParams.get('beds') || '3',
  bathrooms: prefill.bathrooms ? String(prefill.bathrooms) : searchParams.get('baths') || '1',
  floors: prefill.floors ? String(prefill.floors) : searchParams.get('floors') || '1',
  architecturalStyle: prefill.style || 'Modern Minimalist',
  plotWidth: prefill.plot_width_ft ? String(prefill.plot_width_ft) : '',
  plotLength: prefill.plot_length_ft ? String(prefill.plot_length_ft) : '',
  roadSide: prefill.road_side || 'south',
  northDirection: prefill.north_direction || 'north',
  entranceSide: prefill.entrance_side || 'road_side',
  frontSetback: '', rearSetback: '', leftSetback: '', rightSetback: '',
  openPlan: prefill.open_plan || false, 
  masterEnsuite: prefill.master_ensuite || false, 
  separateDining: prefill.separate_dining || false,
  homeOffice: prefill.office || false, 
  balcony: prefill.balcony || false, 
  veranda: prefill.veranda || false, 
  utilityRoom: prefill.utility_room || false,
  parkingRequired: prefill.parking_spaces ? true : false, 
  accessibility: prefill.accessible_friendly || false,
  targetDate: '',
 });

 const [currentStep, setCurrentStep] = useState(1);
 const [isSubmitting, setIsSubmitting] = useState(false);
 const [isSuccess, setIsSuccess] = useState(false);
 const [workflowId, setWorkflowId] = useState<string | null>(null);
 const [errorMessage, setErrorMessage] = useState('');
 const [fieldErrors, setFieldErrors] = useState<{ [key: string]: string }>({});
 const [showAdvancedPlot, setShowAdvancedPlot] = useState(false);
 
 const [compatibility, setCompatibility] = useState<any>(null);
 const [compatibilityMessage, setCompatibilityMessage] = useState('');

 const steps = [
  { id: 1, title: 'Land' },
  { id: 2, title: 'Plot & Site' },
  { id: 3, title: 'House' },
  { id: 4, title: 'Features' },
  { id: 5, title: 'Review' }
 ];

 // Dynamic Compatibility Effect
 useEffect(() => {
  const fetchCompatibility = async () => {
   if (!formData.landSize || Number(formData.landSize) <= 0) return;
   try {
    const payload = {
     landSize: parseFloat(formData.landSize),
     landUnit: formData.landUnit,
     plotWidthFt: formData.plotWidth ? parseFloat(formData.plotWidth) : null,
     plotLengthFt: formData.plotLength ? parseFloat(formData.plotLength) : null,
     terrainType: formData.terrainType,
     bedrooms: formData.bedrooms ? parseInt(formData.bedrooms) : null,
     bathrooms: formData.bathrooms ? parseInt(formData.bathrooms) : null,
     floors: formData.floors ? parseInt(formData.floors) : null,
     style: formData.architecturalStyle,
     features: {
      openPlan: formData.openPlan,
      masterEnsuite: formData.masterEnsuite,
      separateDining: formData.separateDining,
      homeOffice: formData.homeOffice,
      balcony: formData.balcony,
      veranda: formData.veranda,
      utilityRoom: formData.utilityRoom,
      parkingRequired: formData.parkingRequired,
      accessibility: formData.accessibility,
     }
    };
    const res = await workflowService.checkCompatibility(payload);
    setCompatibility(res);

    // Cascading Re-evaluation
    let clearedOptions = [];
    const newFormData = { ...formData };

    if (res.supported) {
     if (formData.bedrooms && !res.supported.bedrooms.includes(parseInt(formData.bedrooms))) {
      newFormData.bedrooms = res.supported.bedrooms[0]?.toString() || '';
      clearedOptions.push('Bedrooms');
     }
     if (formData.bathrooms && !res.supported.bathrooms.includes(parseInt(formData.bathrooms))) {
      newFormData.bathrooms = res.supported.bathrooms[0]?.toString() || '';
      clearedOptions.push('Bathrooms');
     }
     if (formData.floors && !res.supported.floors.includes(parseInt(formData.floors))) {
      newFormData.floors = res.supported.floors[0]?.toString() || '';
      clearedOptions.push('Floors');
     }
     if (formData.architecturalStyle && !res.supported.styles.includes(formData.architecturalStyle)) {
      newFormData.architecturalStyle = res.supported.styles[0] || 'Modern Minimalist';
      clearedOptions.push('Style');
     }
     
     Object.keys(res.supported.features).forEach(feat => {
      if (newFormData[feat as keyof IntakeFormData] === true && !res.supported.features[feat]) {
       (newFormData as any)[feat] = false;
       clearedOptions.push(feat.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase()));
      }
     });
    }

    if (clearedOptions.length > 0) {
     setFormData(newFormData);
     setCompatibilityMessage(`Your previous selection for ${clearedOptions.join(', ')} is no longer compatible and has been cleared.`);
     setTimeout(() => setCompatibilityMessage(''), 8000);
    }
   } catch (err) {
    // Silently fail compatibility check if server error, rely on final generation validation
   }
  };
  
  // Simple debounce to avoid spamming the endpoint
  const timer = setTimeout(fetchCompatibility, 400);
  return () => clearTimeout(timer);
 }, [
  formData.landSize, formData.landUnit, formData.plotWidth, formData.plotLength, formData.terrainType,
  formData.bedrooms, formData.bathrooms, formData.floors, formData.architecturalStyle,
  formData.openPlan, formData.masterEnsuite, formData.separateDining, formData.homeOffice,
  formData.balcony, formData.veranda, formData.utilityRoom, formData.parkingRequired, formData.accessibility
 ]);

 const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
  let { name, value } = e.target;
  if (['landSize', 'plotWidth', 'plotLength'].includes(name)) {
   if (Number(value) < 0) return;
   if (name !== 'landSize' && Number(value) === 0 && value !== '') return;
  }
  setFormData((prev) => ({ ...prev, [name]: value }));
  if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: '' }));
 };


 const toggleFeature = (name: keyof IntakeFormData) => {
  // If unsupported, don't allow toggling on
  if (compatibility?.supported?.features && compatibility.supported.features[name] === false) return;
  setFormData((prev) => ({ ...prev, [name]: !prev[name] }));
 };

 const validateStep = (step: number) => {
  const errors: { [key: string]: string } = {};
  if (step === 1) {
   if (!formData.landSize || Number(formData.landSize) <= 0) {
    errors.landSize = 'Land size is required and must be greater than 0.';
   }
  }
  if (step === 3) {
   if (!formData.bedrooms || Number(formData.bedrooms) < 1) errors.bedrooms = 'Bedrooms must be at least 1.';
   if (!formData.bathrooms || Number(formData.bathrooms) < 1) errors.bathrooms = 'Bathrooms must be at least 1.';
   if (!formData.floors || Number(formData.floors) < 1) errors.floors = 'Floors must be at least 1.';
   if (compatibility?.compatiblePlanCount === 0) errors.compatibility = 'No compatible plans support this configuration.';
  }
  if (step === 4) {
   if (compatibility?.compatiblePlanCount === 0) errors.compatibility = 'No compatible plans support these features.';
  }
  setFieldErrors(errors);
  return Object.keys(errors).length === 0;
 };

 const handleNext = () => {
  if (validateStep(currentStep)) {
   setCurrentStep((prev) => Math.min(prev + 1, 5));
   window.scrollTo(0, 0);
  }
 };

 const handleBack = () => {
  setCurrentStep((prev) => Math.max(prev - 1, 1));
  window.scrollTo(0, 0);
 };

 const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!validateStep(5)) return;
  
  setIsSubmitting(true);
  setErrorMessage('');

  try {
   const payload: any = {
    ...(searchParams.get('basePlanId') ? { basePreDesignedPlanId: searchParams.get('basePlanId'), planSelectionMode: searchParams.get('mode') || 'use' } : {}),
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
     circulationPreference: 'space_efficient',
     ...(formData.targetDate ? { targetCompletionDate: formData.targetDate } : {})
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

   const result = await workflowService.startDesign(payload);
   
   setWorkflowId(result.workflowId);
   setIsSuccess(true);
  } catch (err: any) {
   setErrorMessage(err.response?.data?.message || err.message || 'Failed to generate plan.');
  } finally {
   setIsSubmitting(false);
  }
 };

 if (isSuccess) {
  return (
   <div className="min-h-[calc(100vh-65px)] flex items-center justify-center p-6 bg-gray-50 bg-background transition-colors">
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-surface rounded-[2rem] p-10 max-w-md w-full text-center shadow-xl border border-gray-100 dark:border-border-strong">
     <div className="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
      <CheckCircle2 size={40} className="text-green-600 dark:text-green-400" />
     </div>
     <h2 className="text-3xl font-bold text-gray-900 dark:text-text-primary mb-4">Project Created!</h2>
     <p className="text-text-muted text-text-secondary mb-8 leading-relaxed">
      Your requirements have been securely saved and the AI is analyzing the data.
     </p>
     <button 
      onClick={() => navigate(`/dashboard/workflows/${workflowId}`)}
      className="w-full py-4 bg-gray-900 dark:bg-surface text-text-primary dark:text-gray-900 rounded-xl font-bold hover:bg-black dark:hover:bg-gray-100 transition-colors"
     >
      Go to Project Dashboard
     </button>
    </motion.div>
   </div>
  );
 }

 const renderStepIndicator = () => (
  <div className="flex items-center justify-between mb-8 sm:mb-12 max-w-2xl mx-auto px-2 relative">
   <div className="absolute top-1/2 left-0 right-0 h-[2px] bg-gray-200 bg-surface-elevated -z-10 -translate-y-1/2"></div>
   {steps.map((step) => (
    <div key={step.id} className="flex flex-col items-center gap-2">
     <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${currentStep >= step.id ? 'bg-blue-600 text-text-primary' : 'bg-gray-100 bg-surface-elevated text-text-secondary border border-border'}`}>
      {currentStep > step.id ? <Check size={14} /> : step.id}
     </div>
     <span className={`text-[10px] uppercase font-bold tracking-wider hidden sm:block ${currentStep >= step.id ? 'text-gray-900 dark:text-text-primary' : 'text-text-secondary dark:text-text-secondary'}`}>
      {step.title}
     </span>
    </div>
   ))}
  </div>
 );

 return (
  <div className="min-h-[calc(100vh-65px)] bg-background p-4 sm:p-8 flex items-start justify-center transition-colors">
   <div className="max-w-3xl w-full">
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-surface rounded-[2rem] shadow-sm border border-border dark:border-border-strong overflow-hidden flex flex-col min-h-[600px]">
     
     <div className="p-6 sm:p-10 flex-1 relative">
      <AnimatePresence>
       {compatibilityMessage && (
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="absolute top-4 left-6 right-6 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 p-3 rounded-xl flex gap-3 z-20">
         <Info className="text-blue-500 shrink-0 mt-0.5" size={16} />
         <p className="text-sm text-blue-800 dark:text-blue-300 font-medium">{compatibilityMessage}</p>
        </motion.div>
       )}
      </AnimatePresence>

      {renderStepIndicator()}
      
      {/* STEP 1: LAND */}
      {currentStep === 1 && (
       <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
        <div>
         <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-text-primary mb-2">Tell us about your land</h2>
         <p className="text-text-muted text-text-secondary">Basic details about your property size and terrain.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Land Size *</label>
          <div className="flex gap-2">
           <input 
            type="number" name="landSize" value={formData.landSize} onChange={handleInputChange} 
            className={`flex-1 bg-gray-50 bg-surface-elevated border ${fieldErrors.landSize ? 'border-red-500' : 'border-border'} rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary focus:ring-2 focus:ring-blue-500 outline-none`} 
            placeholder="e.g. 25"
           />
           <select name="landUnit" value={formData.landUnit} onChange={handleInputChange} className="w-32 bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary outline-none">
            <option value="perches">Perches</option>
            <option value="sqft">Sq Ft</option>
           </select>
          </div>
          {fieldErrors.landSize && <p className="text-red-500 text-xs mt-2">{fieldErrors.landSize}</p>}
         </div>
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Terrain Type</label>
          <select name="terrainType" value={formData.terrainType} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary outline-none">
           <option value="flat/urban">Flat / Urban</option>
           <option value="sloped">Sloped</option>
           <option value="coastal">Coastal / Beachfront</option>
           <option value="wooded">Wooded / Forest</option>
           <option value="rural/farm">Rural / Farmland</option>
          </select>
         </div>
        </div>

       </motion.div>
      )}

      {/* STEP 2: PLOT & SITE */}
      {currentStep === 2 && (
       <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
        <div>
         <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-text-primary mb-2">Define the plot</h2>
         <p className="text-text-muted text-text-secondary">If dimensions are unavailable, the system can estimate conceptual proportions from land area.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Plot Width (ft) (Optional)</label>
          <input type="number" name="plotWidth" value={formData.plotWidth} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Optional" />
         </div>
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Plot Length (ft) (Optional)</label>
          <input type="number" name="plotLength" value={formData.plotLength} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Optional" />
         </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Road Side</label>
          <select name="roadSide" value={formData.roadSide} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary outline-none">
           <option value="south">South</option><option value="north">North</option><option value="east">East</option><option value="west">West</option>
          </select>
         </div>
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">North Direction</label>
          <select name="northDirection" value={formData.northDirection} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary outline-none">
           <option value="north">North</option><option value="east">East</option><option value="south">South</option><option value="west">West</option>
          </select>
         </div>
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Main Access</label>
          <select name="entranceSide" value={formData.entranceSide} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary outline-none">
           <option value="road_side">Road Side (Default)</option><option value="north">North</option><option value="south">South</option><option value="east">East</option><option value="west">West</option>
          </select>
         </div>
        </div>

        <div className="border border-border dark:border-border-strong rounded-2xl overflow-hidden">
         <button type="button" onClick={() => setShowAdvancedPlot(!showAdvancedPlot)} className="w-full bg-gray-50 bg-surface-elevated/50 p-4 flex items-center justify-between text-sm font-bold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          Advanced Plot Constraints {showAdvancedPlot ? <Expand className="rotate-180" size={16} /> : <Expand size={16} />}
         </button>
         <AnimatePresence>
          {showAdvancedPlot && (
           <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-4 bg-surface">
             {['front', 'rear', 'left', 'right'].map((side) => (
              <div key={side}>
               <label className="block text-xs font-bold text-text-muted text-text-secondary mb-1 capitalize">{side} Setback (ft)</label>
               <input type="number" name={`${side}Setback`} value={(formData as any)[`${side}Setback`]} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-lg px-3 py-2 text-gray-900 dark:text-text-primary outline-none" />
              </div>
             ))}
            </div>
           </motion.div>
          )}
         </AnimatePresence>
        </div>

        <div>
         <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Target Completion Date (Optional)</label>
         <input type="date" name="targetDate" value={formData.targetDate} onChange={handleInputChange} className="w-full sm:w-1/2 bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary focus:ring-2 focus:ring-blue-500 outline-none" min={new Date().toISOString().split('T')[0]} />
        </div>
       </motion.div>
      )}

      {/* STEP 3: HOUSE REQUIREMENTS */}
      {currentStep === 3 && (
       <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
        <div>
         <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-text-primary mb-2">Describe the home you want</h2>
         <p className="text-text-muted text-text-secondary">Basic requirements for the internal spaces.</p>
        </div>

        {compatibility?.supported && (
         <div className="text-sm text-text-muted text-text-secondary bg-gray-50 bg-surface-elevated/50 px-4 py-3 rounded-xl border border-gray-100 dark:border-border-strong flex gap-3">
          <Info size={18} className="text-blue-500 shrink-0" />
          <p>Based on your current inputs, options are restricted to what is feasible in our validated catalogue.</p>
         </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
         {/* Bedrooms */}
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Bedrooms *</label>
          <div className="flex gap-2 flex-wrap">
           {[2, 3, 4, 5].map(num => {
            const isSupported = compatibility?.supported ? compatibility.supported.bedrooms.includes(num) : true;
            return (
             <button
              key={num} type="button" disabled={!isSupported}
              onClick={() => { setFormData(p => ({...p, bedrooms: num.toString()})); if (fieldErrors.bedrooms) setFieldErrors(p => ({...p, bedrooms: ''})); }}
              className={`w-12 h-12 rounded-xl border flex items-center justify-center font-bold text-sm transition-all
               ${!isSupported ? 'opacity-40 border-border bg-gray-50 bg-surface-elevated cursor-not-allowed text-text-secondary' 
                : formData.bedrooms === num.toString() ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 shadow-sm' 
                : 'border-border hover:border-blue-300 dark:hover:border-blue-700 text-gray-700 dark:text-gray-300'}
              `}
              title={!isSupported ? `No validated plans support ${num} bedrooms with your current land and floor selection.` : ""}
             >
              {num}
             </button>
            );
           })}
          </div>
          {fieldErrors.bedrooms && <p className="text-red-500 text-xs mt-2">{fieldErrors.bedrooms}</p>}
         </div>
         
         {/* Bathrooms */}
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Bathrooms *</label>
          <div className="flex gap-2 flex-wrap">
           {[1, 2, 3].map(num => {
            const isSupported = compatibility?.supported ? compatibility.supported.bathrooms.includes(num) : true;
            return (
             <button
              key={num} type="button" disabled={!isSupported}
              onClick={() => { setFormData(p => ({...p, bathrooms: num.toString()})); if (fieldErrors.bathrooms) setFieldErrors(p => ({...p, bathrooms: ''})); }}
              className={`w-12 h-12 rounded-xl border flex items-center justify-center font-bold text-sm transition-all
               ${!isSupported ? 'opacity-40 border-border bg-gray-50 bg-surface-elevated cursor-not-allowed text-text-secondary' 
                : formData.bathrooms === num.toString() ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 shadow-sm' 
                : 'border-border hover:border-blue-300 dark:hover:border-blue-700 text-gray-700 dark:text-gray-300'}
              `}
              title={!isSupported ? `Not available with your current land, floor, and bedroom selection.` : ""}
             >
              {num}
             </button>
            );
           })}
          </div>
          {fieldErrors.bathrooms && <p className="text-red-500 text-xs mt-2">{fieldErrors.bathrooms}</p>}
         </div>

         {/* Floors */}
         <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Floors *</label>
          <div className="flex gap-2 flex-wrap">
           {[1, 2].map(num => {
            const isSupported = compatibility?.supported ? compatibility.supported.floors.includes(num) : true;
            return (
             <button
              key={num} type="button" disabled={!isSupported}
              onClick={() => { setFormData(p => ({...p, floors: num.toString()})); if (fieldErrors.floors) setFieldErrors(p => ({...p, floors: ''})); }}
              className={`w-12 h-12 rounded-xl border flex items-center justify-center font-bold text-sm transition-all
               ${!isSupported ? 'opacity-40 border-border bg-gray-50 bg-surface-elevated cursor-not-allowed text-text-secondary' 
                : formData.floors === num.toString() ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 shadow-sm' 
                : 'border-border hover:border-blue-300 dark:hover:border-blue-700 text-gray-700 dark:text-gray-300'}
              `}
              title={!isSupported ? "No validated plans for this floor count fit your current buildable area." : ""}
             >
              {num}
             </button>
            );
           })}
          </div>
          {fieldErrors.floors && <p className="text-red-500 text-xs mt-2">{fieldErrors.floors}</p>}
         </div>

         <div className="sm:col-span-2">
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Architectural Style</label>
          <select name="architecturalStyle" value={formData.architecturalStyle} onChange={handleInputChange} className="w-full bg-gray-50 bg-surface-elevated border border-border rounded-xl px-4 py-3 text-gray-900 dark:text-text-primary outline-none">
           {['Modern Minimalist', 'Tropical Modern', 'Traditional', 'Industrial', 'Contemporary'].map(style => {
            const isSupported = compatibility?.supported ? compatibility.supported.styles.includes(style) : true;
            return (
             <option key={style} value={style} disabled={!isSupported}>
              {style} {!isSupported ? '(Unavailable for current config)' : ''}
             </option>
            );
           })}
          </select>
         </div>
        </div>
       </motion.div>
      )}

      {/* STEP 4: EXTRA FEATURES */}
      {currentStep === 4 && (
       <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
        <div>
         <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-text-primary mb-2">Choose optional features</h2>
         <p className="text-text-muted text-text-secondary">Select any extra requirements for your home.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
         {[
          { key: 'separateDining', label: 'Separate Dining Area', desc: 'Enclosed or distinct dining room.' },
          { key: 'homeOffice', label: 'Home Office', desc: 'Dedicated workspace room.' },
          { key: 'accessibility', label: 'Accessible Layout', desc: 'Reduced-step and wheelchair friendly.' },
         ].map((feature) => {
          const featKeyAPI = feature.key;
          const isSupported = compatibility?.supported?.features ? compatibility.supported.features[featKeyAPI] !== false : true;
          const reason = compatibility?.reasons ? compatibility.reasons[`feature.${featKeyAPI.replace(/([A-Z])/g, "_$1").toLowerCase()}`] : '';

          return (
           <div 
            key={feature.key} 
            onClick={() => toggleFeature(feature.key as keyof IntakeFormData)}
            className={`cursor-pointer border rounded-xl p-4 flex gap-4 transition-all
             ${!isSupported ? 'opacity-40 border-border bg-gray-50 bg-surface-elevated/50 cursor-not-allowed' :
              formData[feature.key as keyof IntakeFormData] ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-border bg-surface-elevated'}
            `}
            title={reason || (!isSupported ? 'Not available' : '')}
           >
            <div className={`mt-1 flex-shrink-0 ${formData[feature.key as keyof IntakeFormData] ? 'text-blue-600 dark:text-blue-400' : 'text-text-secondary'}`}>
             {formData[feature.key as keyof IntakeFormData] ? <CheckSquare size={20} /> : <div className={`w-5 h-5 border-2 rounded ${!isSupported ? 'border-border' : 'border-border-strong dark:border-gray-600'}`} />}
            </div>
            <div>
             <h4 className={`font-bold text-sm ${formData[feature.key as keyof IntakeFormData] ? 'text-blue-900 dark:text-blue-200' : 'text-gray-900 dark:text-text-primary'}`}>{feature.label}</h4>
             <p className={`text-xs mt-1 ${formData[feature.key as keyof IntakeFormData] ? 'text-blue-700 dark:text-blue-300' : 'text-text-muted text-text-secondary'}`}>
              {!isSupported && reason ? <span className="text-red-500 dark:text-red-400 block mb-1 font-medium">{reason}</span> : null}
              {feature.desc}
             </p>
            </div>
           </div>
          )
         })}
        </div>
       </motion.div>
      )}

      {/* STEP 5: REVIEW */}
      {currentStep === 5 && (
       <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
        <div>
         <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-text-primary mb-2">Review your project</h2>
         <p className="text-text-muted text-text-secondary">Ensure all details are correct before generating your plan.</p>
        </div>

        {errorMessage && (
         <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-xl flex items-start gap-3">
          <Info className="text-red-500 shrink-0 mt-0.5" size={18} />
          <div>
           <p className="text-red-800 dark:text-red-300 font-semibold text-sm">Issue detected:</p>
           <p className="text-red-600 dark:text-red-400 text-sm mt-1">{errorMessage}</p>
          </div>
         </div>
        )}

        <div className="space-y-6">
         <div className="bg-gray-50 bg-surface-elevated/50 rounded-2xl p-6 border border-gray-100 dark:border-border-strong">
          <div className="flex justify-between items-center mb-4">
           <h3 className="font-bold text-gray-900 dark:text-text-primary flex items-center gap-2"><Map size={18} className="text-text-secondary" /> Land</h3>
           <button onClick={() => setCurrentStep(1)} className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline">Edit</button>
          </div>
          <ul className="text-sm text-text-secondary dark:text-gray-300 space-y-2">
           <li>• {formData.landSize} {formData.landUnit}</li>
           <li>• {formData.terrainType}</li>
          </ul>
         </div>

         <div className="bg-gray-50 bg-surface-elevated/50 rounded-2xl p-6 border border-gray-100 dark:border-border-strong">
          <div className="flex justify-between items-center mb-4">
           <h3 className="font-bold text-gray-900 dark:text-text-primary flex items-center gap-2"><Compass size={18} className="text-text-secondary" /> Plot & Site</h3>
           <button onClick={() => setCurrentStep(2)} className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline">Edit</button>
          </div>
          <ul className="text-sm text-text-secondary dark:text-gray-300 space-y-2">
           <li>• {formData.plotWidth && formData.plotLength ? `${formData.plotWidth} ft x ${formData.plotLength} ft` : 'Dimensions estimated'}</li>
           <li>• Road: <span className="capitalize">{formData.roadSide}</span></li>
           <li>• Entrance: <span className="capitalize">{formData.entranceSide === 'road_side' ? formData.roadSide : formData.entranceSide}</span></li>
          </ul>
         </div>

         <div className="bg-gray-50 bg-surface-elevated/50 rounded-2xl p-6 border border-gray-100 dark:border-border-strong">
          <div className="flex justify-between items-center mb-4">
           <h3 className="font-bold text-gray-900 dark:text-text-primary flex items-center gap-2"><Home size={18} className="text-text-secondary" /> House Requirements</h3>
           <button onClick={() => setCurrentStep(3)} className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline">Edit</button>
          </div>
          <ul className="text-sm text-text-secondary dark:text-gray-300 space-y-2">
           <li>• {formData.bedrooms} Bedrooms, {formData.bathrooms} Bathrooms, {formData.floors} Floors</li>
           <li>• Style: {formData.architecturalStyle}</li>
          </ul>
         </div>

         <div className="bg-gray-50 bg-surface-elevated/50 rounded-2xl p-6 border border-gray-100 dark:border-border-strong">
          <div className="flex justify-between items-center mb-4">
           <h3 className="font-bold text-gray-900 dark:text-text-primary flex items-center gap-2"><CheckCircle2 size={18} className="text-text-secondary" /> Features</h3>
           <button onClick={() => setCurrentStep(4)} className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline">Edit</button>
          </div>
          <ul className="text-sm text-text-secondary dark:text-gray-300 flex flex-wrap gap-2">
           {['separateDining', 'homeOffice', 'accessibility'].filter(k => (formData as any)[k]).map(k => (
            <li key={k} className="bg-gray-200 dark:bg-gray-700 px-3 py-1 rounded-full text-xs">{k.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</li>
           ))}
           {['separateDining', 'homeOffice', 'accessibility'].filter(k => (formData as any)[k]).length === 0 && (
            <li>No extra features selected</li>
           )}
          </ul>
         </div>
        </div>
       </motion.div>
      )}

     </div>

     {/* STICKY FOOTER NAVIGATION */}
     <div className="p-6 sm:p-10 bg-gray-50 bg-surface-elevated/30 border-t border-gray-100 dark:border-border-strong flex items-center justify-between">
      <button 
       type="button" 
       onClick={handleBack} 
       disabled={currentStep === 1 || isSubmitting}
       className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-colors ${currentStep === 1 || isSubmitting ? 'opacity-0 pointer-events-none' : 'text-text-secondary dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 border border-border'}`}
      >
       <ChevronLeft size={18} /> Back
      </button>
      
      {currentStep < 5 ? (
       <button 
        type="button" 
        onClick={handleNext}
        disabled={currentStep === 3 && fieldErrors.compatibility !== undefined || currentStep === 4 && fieldErrors.compatibility !== undefined}
        className="flex items-center gap-2 px-8 py-3 bg-gray-900 dark:bg-surface hover:bg-black dark:hover:bg-gray-200 text-text-primary dark:text-gray-900 rounded-xl font-bold text-sm transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
       >
        Next <ChevronRight size={18} />
       </button>
      ) : (
       <button 
        type="button" 
        onClick={handleSubmit}
        disabled={isSubmitting}
        className="flex items-center justify-center gap-3 px-8 py-4 bg-blue-600 hover:bg-blue-700 text-text-primary rounded-xl font-bold text-sm transition-colors shadow-sm disabled:opacity-70 min-w-[200px]"
       >
        {isSubmitting ? (
         <>
          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
          Generating your plan...
         </>
        ) : (
         <>
          Generate AI Plan <CheckCircle2 size={18} />
         </>
        )}
       </button>
      )}
     </div>

    </motion.div>
   </div>
  </div>
 );
};

export default IntakeForm;
