import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, X, MessageSquare, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/apiClient';

export type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  action?: any;
  intent?: string;
};

interface AIArchitectChatProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  prompt: string;
  setPrompt: (prompt: string) => void;
  showFab?: boolean;
}

export const AIArchitectChat: React.FC<AIArchitectChatProps> = ({ isOpen, setIsOpen, prompt, setPrompt, showFab = false }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const submitLockRef = useRef(false);
  const navigate = useNavigate();

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitLockRef.current) return;
    if (!prompt) return;
    submitLockRef.current = true;
    setIsGenerating(true);
    const currentPrompt = prompt;
    setPrompt(''); 
    
    setChatHistory(prev => [...prev, { role: 'user', content: currentPrompt }]);
    
    try {
     const historyToSend = chatHistory.map(msg => ({ role: msg.role, content: msg.content }));
     const { data } = await apiClient.post('/assistant/interpret', { 
      message: currentPrompt,
      history: historyToSend 
     });
     if (data.reply) {
      setChatHistory(prev => [...prev, { 
       role: 'assistant', 
       content: data.reply,
       action: data.action,
       intent: data.intent
      }]);
     }
    } catch (err) {
     console.error('Assistant error:', err);
     setChatHistory(prev => [...prev, { role: 'assistant', content: 'Failed to interpret message.' }]);
    } finally {
     submitLockRef.current = false;
     setIsGenerating(false);
    }
  };

  return (
    <>
      {/* FLOATING CHAT WIDGET */}
      <AnimatePresence>
        {isOpen && (
         <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className="fixed bottom-6 right-6 z-[100] w-[420px] max-w-[calc(100vw-2rem)] bg-surface/95 bg-surface/95 backdrop-blur-xl border border-border dark:border-border-strong rounded-2xl shadow-2xl flex flex-col overflow-hidden"
         >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 bg-surface-elevated/80 border-b border-border dark:border-border-strong">
           <div className="flex items-center gap-2">
            <Sparkles size={14} className="text-yellow-600" />
            <span className="text-[10px] font-bold tracking-[0.2em] text-text-primary">AI ARCHITECT</span>
           </div>
           <div className="flex items-center gap-4">
            {chatHistory.length > 0 && (
             <button type="button" onClick={() => setChatHistory([])} className="text-[10px] uppercase font-bold tracking-wider text-text-muted hover:text-text-primary transition-colors">
              Clear
             </button>
            )}
            <button type="button" onClick={() => setIsOpen(false)} className="text-text-secondary hover:text-text-primary transition-colors">
             <X size={18} />
            </button>
           </div>
          </div>

          {/* Chat History Area */}
          <div className="px-5 py-4 h-[400px] overflow-y-auto flex flex-col gap-4 scrollbar-thin relative">
           <AnimatePresence>
            {isGenerating && (
             <motion.div 
              initial={{ left: '-100%' }}
              animate={{ left: '200%' }}
              transition={{ duration: 1.5, ease: "linear", repeat: Infinity }}
              className="absolute top-0 bottom-0 w-1/2 bg-gradient-to-r from-transparent via-blue-400/10 dark:via-blue-500/10 to-transparent z-0 pointer-events-none skew-x-12"
             />
            )}
           </AnimatePresence>

           {chatHistory.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-70 my-8 relative z-10">
             <MessageSquare size={32} className="mb-3 text-text-secondary" />
             <p className="text-sm text-text-secondary">Describe your dream home or ask any architectural question to get started.</p>
            </div>
           ) : (
            chatHistory.map((msg, idx) => (
             <div key={idx} className={`flex flex-col relative z-10 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`px-4 py-3 rounded-2xl max-w-[90%] text-sm shadow-sm ${msg.role === 'user' ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-br-sm' : 'bg-surface-elevated text-text-primary rounded-bl-sm border border-border'}`}>
               <p className="whitespace-pre-wrap leading-relaxed">
                {msg.content}
               </p>
              </div>
              
              {/* Render actions if assistant message */}
              {msg.role === 'assistant' && msg.action && (
               <div className="mt-3 w-full pl-2">
                {msg.action.type === 'CONTINUE_TO_DESIGN' && (
                 <div className="p-4 bg-indigo-50 dark:bg-indigo-900/30 rounded-xl border border-indigo-100 dark:border-indigo-800 max-w-[90%]">
                  <p className="font-semibold text-indigo-900 dark:text-indigo-200 mb-3 text-sm">
                   Your request is feasible. I can start the design setup with these requirements.
                  </p>
                  <button 
                   onClick={() => { setIsOpen(false); navigate('/dashboard/new-project', { state: { prefill: msg.action.payload.requirements } }); }}
                   className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-bold text-xs tracking-wider transition-colors shadow-sm"
                  >
                   Continue to Design
                  </button>
                 </div>
                )}

                {msg.intent === 'DESIGN_REQUEST' && msg.action.type === 'NONE' && msg.action.payload?.feasibility && !msg.action.payload.feasibility.can_proceed && (
                 <div className="p-4 bg-amber-50 dark:bg-amber-900/30 rounded-xl border border-amber-200 dark:border-amber-800 max-w-[90%]">
                  <p className="font-semibold text-amber-900 dark:text-amber-200 mb-2 text-sm">
                   Your request is not supported with the available buildable area or catalogue.
                  </p>
                  {msg.action.payload.feasibility.suggestions?.length > 0 && (
                   <ul className="list-disc list-inside text-amber-800 dark:text-amber-300 text-xs space-y-1.5 mt-2">
                    {msg.action.payload.feasibility.suggestions.map((s: string, i: number) => (
                     <li key={i}>{s}</li>
                    ))}
                   </ul>
                  )}
                 </div>
                )}
               </div>
              )}
             </div>
            ))
           )}
          </div>

          {/* Input Form */}
          <form onSubmit={handleGenerate} className="flex items-center gap-2 p-3 bg-surface border-t border-border dark:border-border-strong relative z-10">
           <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Message AI Architect..."
            className="flex-1 bg-surface-elevated border border-border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-text-primary placeholder-text-muted px-4 py-3 outline-none text-sm transition-all"
           />
           <button 
            type="submit"
            disabled={isGenerating || !prompt}
            className="bg-gray-900 dark:bg-white hover:bg-black dark:hover:bg-gray-200 text-white dark:text-gray-900 w-12 h-12 flex-shrink-0 rounded-xl flex items-center justify-center transition-colors disabled:opacity-50 shadow-sm"
           >
            {isGenerating ? <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div> : <ArrowRight size={18} />}
           </button>
          </form>
         </motion.div>
        )}
      </AnimatePresence>

      {/* FLOATING ACTION BUTTON (FAB) when chat is closed */}
      <AnimatePresence>
        {!isOpen && showFab && (
         <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          exit={{ scale: 0 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-16 h-16 bg-black dark:bg-surface border border-transparent dark:border-border-strong text-white dark:text-text-primary rounded-full shadow-2xl flex items-center justify-center"
         >
          <MessageSquare size={24} />
         </motion.button>
        )}
      </AnimatePresence>
    </>
  );
};
