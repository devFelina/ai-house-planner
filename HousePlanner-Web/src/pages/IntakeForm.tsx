import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle2, ChevronRight, ChevronLeft } from 'lucide-react';
import { workflowService } from '../services/workflowService';

const IntakeForm: React.FC = () => {
  const navigate = useNavigate();

  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const submitLockRef = useRef(false);

  // Step 1: Land Information
  const [landSizeCategory, setLandSizeCategory] = useState<'small' | 'medium' | ''>('');
  
  // Step 2: Bedroom Requirements
  const [bedrooms, setBedrooms] = useState<number | null>(null);
  const [bathrooms, setBathrooms] = useState<number | null>(null);

  // Step 3: House Style
  const [houseType, setHouseType] = useState<'simple' | 'modern' | ''>('');
  
  // Step 4 (Optional): Target Duration
  const [targetDuration, setTargetDuration] = useState<number | ''>('');

  const steps = [
    { id: 1, title: 'Land' },
    { id: 2, title: 'Rooms' },
    { id: 3, title: 'Style' }
  ];

  const validateStep = (step: number) => {
    if (step === 1) return landSizeCategory !== '';
    if (step === 2) {
      return bedrooms !== null && bedrooms >= 1 && bedrooms <= 3 && bathrooms !== null && bathrooms >= 1 && bathrooms <= 2;
    }
    if (step === 3) return houseType !== '';
    return true;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep((prev) => Math.min(prev + 1, 3));
      window.scrollTo(0, 0);
    }
  };

  const handleBack = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
    window.scrollTo(0, 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitLockRef.current) return;
    if (!validateStep(3)) return;

    submitLockRef.current = true;
    setIsSubmitting(true);

    let landSizePerches = 15;
    if (landSizeCategory === 'small') landSizePerches = 15;
    if (landSizeCategory === 'medium') landSizePerches = 25;

    try {
      const payload = {
        landSizeCategory: landSizeCategory as 'small' | 'medium',
        landSizePerches,
        bedrooms: bedrooms!,
        bathrooms: bathrooms!,
        houseType: houseType as 'simple' | 'modern',
        targetDurationDays: targetDuration === '' ? undefined : targetDuration
      };

      console.log('Frontend payload before POST:', payload);

      const result = await workflowService.startDesign(payload);
      setWorkflowId(result.workflowId);
      setIsSuccess(true);
    } catch (err: any) {
      console.error('Failed to generate plan.', err);
    } finally {
      submitLockRef.current = false;
      setIsSubmitting(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-[calc(100vh-65px)] flex items-center justify-center p-6 bg-background">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-surface rounded-[2rem] p-10 max-w-md w-full text-center shadow-xl border border-border">
          <div className="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 size={40} className="text-green-600 dark:text-green-400" />
          </div>
          <h2 className="text-3xl font-bold text-text-primary mb-4">Project Created!</h2>
          <p className="text-text-muted mb-8 leading-relaxed">
            AI will optimize the design based on your land size.
          </p>
          <button 
            onClick={() => navigate(`/dashboard/workflows/${workflowId}`)}
            className="w-full py-4 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl font-bold hover:bg-black dark:hover:bg-gray-200 transition-colors"
          >
            Go to Project Dashboard
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-65px)] bg-background p-4 sm:p-8 flex items-start justify-center transition-colors">
      <div className="max-w-3xl w-full">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-surface rounded-[2rem] shadow-sm border border-border overflow-hidden flex flex-col min-h-[500px]">
          
          <div className="p-6 sm:p-10 flex-1 relative">
            {/* Step Indicator */}
            <div className="flex items-center justify-between mb-8 max-w-2xl mx-auto px-2 relative">
              <div className="absolute top-1/2 left-0 right-0 h-[2px] bg-border -z-10 -translate-y-1/2"></div>
              {steps.map((step) => (
                <div key={step.id} className="flex flex-col items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${currentStep >= step.id ? 'bg-blue-600 text-white' : 'bg-surface-elevated text-text-muted border border-border'}`}>
                    {currentStep > step.id ? <CheckCircle2 size={16} /> : step.id}
                  </div>
                  <span className={`text-[10px] uppercase font-bold tracking-wider hidden sm:block ${currentStep >= step.id ? 'text-text-primary' : 'text-text-muted'}`}>
                    {step.title}
                  </span>
                </div>
              ))}
            </div>
            
            {/* STEP 1: LAND */}
            {currentStep === 1 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2">How big is your land?</h2>
                  <p className="text-text-secondary">Choose a supported single-floor residential plot size.</p>
                </div>

                <div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <button type="button" onClick={() => setLandSizeCategory('small')} className={`p-4 border rounded-xl text-left transition-all ${landSizeCategory === 'small' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-200 dark:ring-blue-800' : 'border-border hover:border-blue-300 dark:hover:border-blue-700 bg-surface'}`}>
                      <h4 className="font-bold text-text-primary">Small Plot</h4>
                      <p className="text-xs text-blue-600 dark:text-blue-400 font-semibold mb-1">10 - 20 perches</p>
                      <p className="text-xs text-text-muted">Compact family home</p>
                    </button>
                    <button type="button" onClick={() => setLandSizeCategory('medium')} className={`p-4 border rounded-xl text-left transition-all ${landSizeCategory === 'medium' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-200 dark:ring-blue-800' : 'border-border hover:border-blue-300 dark:hover:border-blue-700 bg-surface'}`}>
                      <h4 className="font-bold text-text-primary">Medium Plot</h4>
                      <p className="text-xs text-blue-600 dark:text-blue-400 font-semibold mb-1">20 - 35 perches</p>
                      <p className="text-xs text-text-muted">Comfortable family home</p>
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* STEP 2: BEDROOMS */}
            {currentStep === 2 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2">How many rooms does your family need?</h2>
                  <p className="text-text-secondary">Choose the bedroom and bathroom counts for your single-floor home.</p>
                </div>

                <div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {[1, 2, 3].map(num => (
                      <button 
                        key={num} 
                        type="button" 
                        onClick={() => { setBedrooms(num); if (num === 1 && bathrooms === null) setBathrooms(1); }}
                        className={`p-4 border rounded-xl font-bold transition-all ${bedrooms === num ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 ring-2 ring-blue-200 dark:ring-blue-800' : 'border-border text-text-primary hover:border-blue-300 dark:hover:border-blue-700 bg-surface'}`}
                      >
                        {num} Bedroom{num > 1 ? 's' : ''}
                      </button>
                    ))}
                  </div>
                  <h3 className="text-lg font-bold text-text-primary mt-8 mb-3">How many bathrooms do you need?</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {[1, 2].map(num => <button key={num} type="button" onClick={() => setBathrooms(num)} className={`p-4 border rounded-xl font-bold transition-all ${bathrooms === num ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 ring-2 ring-blue-200 dark:ring-blue-800' : 'border-border text-text-primary hover:border-blue-300 dark:hover:border-blue-700 bg-surface'}`}>{num} Bathroom{num > 1 ? 's' : ''}{bedrooms === 1 && num === 1 ? ' (Recommended)' : ''}</button>)}
                  </div>
                </div>
              </motion.div>
            )}

            {/* STEP 3: STYLE */}
            {currentStep === 3 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2">Choose your home style</h2>
                  <p className="text-text-secondary">Choose one of the supported family-home styles.</p>
                </div>

                <div>
                  <div className="flex flex-col gap-4">
                    {[
                      { id: 'simple', label: 'Simple Family Home', description: 'Practical single-floor home with essential spaces: Living room, kitchen, dining area, bedrooms and bathrooms.' },
                      { id: 'modern', label: 'Modern Family Home', description: 'Comfortable modern single-floor home with an open living area, modern kitchen, better room spacing and natural lighting.' },
                    ].map(style => (
                      <button key={style.id} type="button" onClick={() => setHouseType(style.id as any)} className={`p-4 border rounded-xl text-left font-bold transition-all ${houseType === style.id ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 ring-2 ring-blue-200 dark:ring-blue-800' : 'border-border text-text-primary hover:border-blue-300 dark:hover:border-blue-700 bg-surface'}`}>
                        <span className="block">{style.label}</span><span className="block mt-1 text-sm font-normal text-text-muted">{style.description}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pt-6 border-t border-border mt-8">
                  <h3 className="text-lg font-bold text-text-primary mb-2">Target Construction Duration (Optional)</h3>
                  <p className="text-sm text-text-secondary mb-4">Let us know if you have a specific timeline in days.</p>
                  <input
                    type="number"
                    value={targetDuration}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (!val) setTargetDuration('');
                      else if (Number(val) > 0) setTargetDuration(Number(val));
                    }}
                    className="w-full p-4 bg-surface-elevated border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g. 120"
                    min="1"
                  />
                </div>

              </motion.div>
            )}

          </div>

          {/* FOOTER NAVIGATION */}
          <div className="p-6 sm:p-10 bg-surface-elevated border-t border-border flex items-center justify-between">
            <button 
              type="button" 
              onClick={handleBack} 
              disabled={currentStep === 1 || isSubmitting}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-colors ${currentStep === 1 || isSubmitting ? 'opacity-0 pointer-events-none' : 'text-text-primary hover:bg-surface border border-border-strong'}`}
            >
              <ChevronLeft size={18} /> Back
            </button>
            
            {currentStep < 3 ? (
              <button 
                type="button" 
                onClick={handleNext}
                disabled={!validateStep(currentStep)}
                className="flex items-center gap-2 px-8 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-black dark:hover:bg-gray-200 rounded-xl font-bold text-sm transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ChevronRight size={18} />
              </button>
            ) : (
              <button 
                type="button" 
                onClick={handleSubmit}
                disabled={isSubmitting || !validateStep(3)}
                className="flex items-center justify-center gap-3 px-8 py-3 bg-green-600 dark:bg-green-500 hover:bg-green-700 dark:hover:bg-green-600 text-white rounded-xl font-bold text-sm transition-colors shadow-sm disabled:opacity-70 disabled:cursor-not-allowed min-w-[200px]"
              >
                {isSubmitting ? 'Generating...' : 'Generate AI Plan'}
              </button>
            )}
          </div>

        </motion.div>
      </div>
    </div>
  );
};

export default IntakeForm;
