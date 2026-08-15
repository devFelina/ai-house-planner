import React, { useRef, useState, Suspense, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Environment, Html, useGLTF, ContactShadows } from '@react-three/drei';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import { Mic, ArrowRight, Layers, Sparkles, Building2, Eye, Box, Moon, Sun, ChevronRight, ChevronLeft } from 'lucide-react';
import * as THREE from 'three';

// ---------------------------------------------------------
// 3D Components
// ---------------------------------------------------------

const ProceduralHouse = () => {
  const groupRef = useRef<THREE.Group>(null);
  return (
    <group ref={groupRef} position={[2, -1, 0]} scale={1.2}>
      {/* Foundation Base */}
      <mesh position={[0, -0.1, 0]}>
        <boxGeometry args={[9, 0.2, 7]} />
        <meshStandardMaterial color="#d1d5db" roughness={0.9} />
      </mesh>
      {/* Main Ground Floor */}
      <mesh position={[0, 1.4, 0]}>
        <boxGeometry args={[7.6, 2.8, 5.6]} />
        <meshStandardMaterial color="#ffffff" roughness={0.1} />
      </mesh>
      {/* Large Glass Windows Front */}
      <mesh position={[0, 1.4, 2.85]}>
        <boxGeometry args={[4.5, 2.6, 0.1]} />
        <meshStandardMaterial color="#111827" roughness={0.05} metalness={0.95} transparent opacity={0.85} />
      </mesh>
      {/* Second Floor Cantilever */}
      <mesh position={[0.5, 4.0, 0.5]}>
        <boxGeometry args={[6, 2.4, 6]} />
        <meshStandardMaterial color="#1f2937" roughness={0.7} />
      </mesh>
      {/* Second Floor Glass */}
      <mesh position={[0.5, 4.0, 3.55]}>
        <boxGeometry args={[5, 2.2, 0.1]} />
        <meshStandardMaterial color="#0f172a" roughness={0.1} metalness={0.9} transparent opacity={0.8} />
      </mesh>
      {/* Wood Paneling Accent */}
      <mesh position={[-2.6, 4.0, 3.5]}>
        <boxGeometry args={[1.2, 2.4, 0.2]} />
        <meshStandardMaterial color="#92400e" roughness={0.8} />
      </mesh>
      {/* Roof */}
      <mesh position={[0.5, 5.3, 0.5]}>
        <boxGeometry args={[6.4, 0.2, 6.4]} />
        <meshStandardMaterial color="#374151" roughness={0.9} />
      </mesh>
      {/* Swimming Pool Water */}
      <mesh position={[-2.5, -0.05, 4.5]}>
        <boxGeometry args={[3, 0.1, 2.5]} />
        <meshStandardMaterial color="#0ea5e9" roughness={0.1} metalness={0.3} transparent opacity={0.9} />
      </mesh>
      {/* Pool Deck */}
      <mesh position={[-2.5, -0.08, 4.5]}>
        <boxGeometry args={[3.4, 0.05, 2.9]} />
        <meshStandardMaterial color="#9ca3af" roughness={1} />
      </mesh>
      {/* Minimalist Tree / Landscaping */}
      <group position={[3.5, 0, 3]}>
        <mesh position={[0, 1, 0]}>
          <cylinderGeometry args={[0.1, 0.1, 2]} />
          <meshStandardMaterial color="#4b5563" />
        </mesh>
        <mesh position={[0, 2.5, 0]}>
          <sphereGeometry args={[1.2, 16, 16]} />
          <meshStandardMaterial color="#15803d" roughness={0.9} />
        </mesh>
      </group>
    </group>
  );
};

const ExternalHouseModel = ({ url }: { url: string }) => {
  const { scene } = useGLTF(url);
  const groupRef = useRef<THREE.Group>(null);
  
  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        if (child.material) {
          if (child.material.name.toLowerCase().includes('glass')) {
            child.material.transparent = true;
            child.material.opacity = 0.4;
            child.material.roughness = 0;
            child.material.metalness = 1;
            child.material.envMapIntensity = 2;
          } else if (child.material.name.toLowerCase().includes('concrete') || child.material.name.toLowerCase().includes('wall')) {
            child.material.roughness = 0.9;
            child.material.metalness = 0.1;
          }
        }
      }
    });
  }, [scene]);

  return <primitive ref={groupRef} object={scene} position={[0, -1, 0]} scale={1} />;
};

const HouseScene = ({ isDark }: { isDark: boolean }) => {
  useFrame((state) => {
    state.camera.position.lerp(new THREE.Vector3(12, 4, 15), 0.02);
    state.camera.lookAt(0, 2, 0);
  });

  return (
    <>
      <ambientLight intensity={isDark ? 0.1 : 0.2} color="#f8fafc" />
      <directionalLight 
        position={[15, 25, 10]} 
        intensity={isDark ? 1.0 : 2.5} 
        color={isDark ? "#e2e8f0" : "#fffbeb"} 
        castShadow 
        shadow-mapSize={[2048, 2048]} 
        shadow-camera-far={50}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
        shadow-bias={-0.0001}
      />
      <directionalLight position={[-15, -10, -15]} color={isDark ? "#1e40af" : "#38bdf8"} intensity={isDark ? 0.3 : 0.5} />
      
      <Environment preset={isDark ? "night" : "city"} blur={0.8} />
      
      <Suspense fallback={null}>
        <ProceduralHouse />
      </Suspense>

      <ContactShadows position={[0, -1.05, 0]} opacity={isDark ? 0.9 : 0.6} scale={30} blur={2.5} far={4} color="#000000" />

      {/* Floating Architectural Annotations */}
      <Html position={[3, 4, 2]} center className="pointer-events-none">
        <div className="relative flex items-center gap-4">
          <div className="w-16 h-[1px] bg-white/50 dark:bg-gray-500/50 hidden md:block"></div>
          <div className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border border-gray-200/50 dark:border-gray-700/50 px-4 py-2 rounded-lg shadow-xl text-xs font-mono w-max transition-colors">
            <div className="text-gray-400 dark:text-gray-500 text-[9px] uppercase tracking-wider mb-1 font-bold">Floor Area</div>
            <div className="text-gray-900 dark:text-white font-bold">2,450 SQ FT</div>
          </div>
        </div>
      </Html>
      <Html position={[-3, 5, 2]} center className="pointer-events-none">
        <div className="relative flex items-center gap-4 flex-row-reverse">
          <div className="w-16 h-[1px] bg-gray-900/50 dark:bg-gray-500/50 hidden md:block"></div>
          <div className="bg-gray-900/90 dark:bg-black/90 backdrop-blur-md border border-gray-700/50 px-4 py-2 rounded-lg shadow-xl text-xs font-mono w-max transition-colors">
            <div className="text-gray-400 text-[9px] uppercase tracking-wider mb-1 font-bold">Bedrooms</div>
            <div className="text-white font-bold">04</div>
          </div>
        </div>
      </Html>
    </>
  );
};


// ---------------------------------------------------------
// Page Component
// ---------------------------------------------------------

const carouselImages = [
  "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?q=80&w=1000&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1600566752355-35792bedcfea?q=80&w=1000&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1556912173-3bb406ef7e77?q=80&w=1000&auto=format&fit=crop"
];

const HomePage: React.FC = () => {
  const { scrollY } = useScroll();
  
  // Theme Toggle with LocalStorage for persistence
  const [isDark, setIsDark] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      return savedTheme === 'dark';
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const navBackground = useTransform(scrollY, [0, 50], [isDark ? 'rgba(3, 7, 18, 0)' : 'rgba(252, 252, 253, 0)', isDark ? 'rgba(3, 7, 18, 0.9)' : 'rgba(252, 252, 253, 0.9)']);
  const navBackdrop = useTransform(scrollY, [0, 50], ['blur(0px)', 'blur(12px)']);
  const navBorder = useTransform(scrollY, [0, 50], [isDark ? 'rgba(31, 41, 55, 0)' : 'rgba(229, 231, 235, 0)', isDark ? 'rgba(31, 41, 55, 1)' : 'rgba(229, 231, 235, 1)']);
  
  const heroOpacity = useTransform(scrollY, [0, 300], [1, 0]);
  const heroY = useTransform(scrollY, [0, 300], [0, -50]);

  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentImgIndex, setCurrentImgIndex] = useState(0);

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt) return;
    setIsGenerating(true);
    setTimeout(() => setIsGenerating(false), 3000);
  };

  const nextImg = () => setCurrentImgIndex((prev) => (prev + 1) % carouselImages.length);
  const prevImg = () => setCurrentImgIndex((prev) => (prev - 1 + carouselImages.length) % carouselImages.length);

  return (
    <div className={`font-sans selection:bg-gray-900 dark:selection:bg-white selection:text-white dark:selection:text-gray-900 min-h-screen relative overflow-x-hidden bg-[#fcfcfd] dark:bg-gray-950 transition-colors duration-300`}>
      
      {/* 1. NAVIGATION */}
      <motion.nav 
        style={{ backgroundColor: navBackground, backdropFilter: navBackdrop, borderBottomColor: navBorder }}
        className="fixed top-0 w-full z-50 transition-all border-b border-transparent"
      >
        <div className="max-w-[1600px] mx-auto px-8 h-24 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 relative flex items-center justify-center">
              <Box className="absolute text-gray-900 dark:text-white transition-colors" size={24} strokeWidth={1.5} />
              <Sparkles className="absolute text-yellow-600 -top-1 -right-1" size={12} />
            </div>
            <span className="text-sm font-bold text-gray-900 dark:text-white tracking-[0.2em] transition-colors">HOMEPLANNER<span className="text-gray-400">AI</span></span>
          </div>
          
          <div className="hidden lg:flex items-center gap-10 text-[11px] font-semibold tracking-[0.15em] text-gray-500 dark:text-gray-400">
            <a href="#" className="text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors">HOME</a>
            <a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">AI DESIGN</a>
            <a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">3D PLANNER</a>
            <a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">HOUSE PLANS</a>
            <a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">HOW IT WORKS</a>
          </div>

          <div className="flex items-center gap-6">
            <button onClick={() => setIsDark(!isDark)} className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <Link to="/login" className="text-[11px] font-bold tracking-[0.15em] text-gray-900 dark:text-white hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
              SIGN IN
            </Link>
            <Link 
              to="/login" 
              className="bg-gray-900 dark:bg-white hover:bg-black dark:hover:bg-gray-200 text-white dark:text-gray-900 px-7 py-3.5 rounded-none text-[11px] font-bold tracking-[0.15em] transition-all"
            >
              START DESIGNING
            </Link>
          </div>
        </div>
      </motion.nav>

      {/* MAIN HERO */}
      <section className="relative h-[100vh] w-full flex items-center pt-24 pb-12 lg:pt-0 lg:pb-0">
        
        {/* 3D Canvas on the Right (60% width) */}
        <div className="absolute inset-0 z-0 lg:left-[40%] lg:w-[60%] pointer-events-auto">
          <Canvas shadows camera={{ position: [20, 10, 20], fov: 35 }} className="w-full h-full cursor-grab active:cursor-grabbing">
            <HouseScene isDark={isDark} />
            <OrbitControls 
              enableZoom={false} 
              enablePan={false} 
              maxPolarAngle={Math.PI / 2 - 0.05} 
              minPolarAngle={Math.PI / 4} 
              minAzimuthAngle={-Math.PI / 4}
              maxAzimuthAngle={Math.PI / 2}
            />
          </Canvas>
          
          {/* Subtle gradient overlay to blend 3D with background on the left */}
          <div className={`absolute inset-0 bg-gradient-to-r ${isDark ? 'from-gray-950 via-gray-950/70' : 'from-[#fcfcfd] via-[#fcfcfd]/70'} to-transparent pointer-events-none w-1/3 hidden lg:block transition-colors duration-300`}></div>
        </div>

        {/* Hero Content on the Left (40% width) */}
        <motion.div 
          style={{ opacity: heroOpacity, y: heroY }}
          className="relative z-10 w-full max-w-[1600px] mx-auto px-8 pointer-events-none flex flex-col justify-center h-full"
        >
          <div className="max-w-[45%] pointer-events-auto mt-20 lg:mt-0">
            <div className="inline-block mb-6">
              <p className="text-[10px] font-bold tracking-[0.2em] text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <span className="w-8 h-[1px] bg-gray-300 dark:bg-gray-700 transition-colors"></span>
                AI-POWERED ARCHITECTURE
              </p>
            </div>
            
            <h1 className="text-5xl lg:text-[5rem] font-medium text-gray-900 dark:text-white tracking-tight leading-[1.05] mb-6 font-serif transition-colors">
              Design the Home<br/>
              <span className="relative inline-block text-gray-800 dark:text-gray-300 transition-colors">
                You Imagine.
              </span>
            </h1>
            
            <p className="text-lg text-gray-500 dark:text-gray-400 mb-10 leading-relaxed font-light pr-10 transition-colors">
              Turn your ideas into intelligent architecture, immersive 3D spaces, and build-ready plans.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 mb-12">
              <Link to="/login" className="bg-gray-900 dark:bg-white hover:bg-black dark:hover:bg-gray-200 text-white dark:text-gray-900 px-8 py-4 text-xs font-bold tracking-[0.15em] transition-all flex items-center justify-center gap-3 w-max">
                START DESIGNING <ArrowRight size={16} />
              </Link>
            </div>

            {/* AI Prompt Bar embedded below text */}
            <div className="w-full max-w-xl">
              <motion.div 
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.5, duration: 0.8 }}
                className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl border border-gray-200 dark:border-gray-800 p-2 rounded-2xl shadow-xl flex flex-col relative overflow-hidden transition-colors"
              >
                {/* Scanning animation overlay */}
                <AnimatePresence>
                  {isGenerating && (
                    <motion.div 
                      initial={{ left: '-100%' }}
                      animate={{ left: '200%' }}
                      transition={{ duration: 1.5, ease: "linear", repeat: Infinity }}
                      className="absolute top-0 bottom-0 w-1/2 bg-gradient-to-r from-transparent via-blue-400/20 dark:via-blue-500/20 to-transparent z-0 pointer-events-none skew-x-12"
                    />
                  )}
                </AnimatePresence>

                <div className="flex items-center gap-2 px-4 pt-2 pb-1 relative z-10">
                  <Sparkles size={12} className="text-yellow-600" />
                  <span className="text-[9px] font-bold tracking-[0.2em] text-gray-500 dark:text-gray-400">AI ARCHITECT</span>
                </div>
                
                <form onSubmit={handleGenerate} className="flex items-center gap-2 relative z-10">
                  <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Describe your dream home..."
                    className="flex-1 bg-transparent border-none focus:ring-0 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 px-4 py-3 outline-none text-sm font-light transition-colors"
                  />
                  <button type="button" className="p-3 text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors hidden sm:block">
                    <Mic size={18} />
                  </button>
                  <button 
                    type="submit"
                    disabled={isGenerating}
                    className="bg-gray-900 dark:bg-white hover:bg-black dark:hover:bg-gray-200 text-white dark:text-gray-900 px-6 py-3 rounded-xl text-xs font-bold tracking-[0.1em] transition-colors disabled:opacity-70 flex items-center gap-2"
                  >
                    {isGenerating ? 'ANALYZING' : 'GENERATE'}
                  </button>
                </form>
              </motion.div>
            </div>
          </div>
        </motion.div>

        <motion.div 
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="absolute bottom-8 left-8 z-20 flex flex-col items-center gap-2 hidden lg:flex"
        >
          <span className="text-[9px] font-bold tracking-[0.2em] text-gray-400 dark:text-gray-600 rotate-90 origin-left translate-y-20 -translate-x-3 w-max transition-colors">SCROLL TO EXPLORE</span>
        </motion.div>
      </section>

      {/* 8. SMALL SECOND SECTION */}
      <section className="py-32 bg-white dark:bg-gray-900 relative z-10 transition-colors duration-300">
        <div className="max-w-[1400px] mx-auto px-6">
          <div className="mb-20">
            <p className="text-[10px] font-bold tracking-[0.2em] text-gray-500 dark:text-gray-400 mb-4 transition-colors">FROM IDEA TO ARCHITECTURE</p>
            <h2 className="text-4xl lg:text-5xl font-medium text-gray-900 dark:text-white tracking-tight max-w-2xl font-serif transition-colors">
              One intelligent platform for imagining, designing and visualizing your future home.
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-12">
            {[
              { 
                num: '01', 
                title: 'DESCRIBE', 
                desc: 'Tell AI what your dream home should look like using natural language or reference images.',
                img: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=800&auto=format&fit=crop'
              },
              { 
                num: '02', 
                title: 'DESIGN', 
                desc: 'AI generates an intelligent architectural concept, calculating structural logic and cost.',
                img: 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?q=80&w=800&auto=format&fit=crop'
              },
              { 
                num: '03', 
                title: 'VISUALIZE', 
                desc: 'Explore your home in immersive 3D, adjusting materials, layouts, and lighting instantly.',
                img: 'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?q=80&w=800&auto=format&fit=crop'
              }
            ].map((step, i) => (
              <div key={i} className="group cursor-pointer">
                <div className="h-48 bg-gray-100 dark:bg-gray-800 mb-8 overflow-hidden relative rounded-xl shadow-sm transition-colors">
                  <img src={step.img} alt={step.title} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                </div>
                <div className="flex items-baseline gap-4 mb-3">
                  <span className="text-xs font-mono text-gray-400 dark:text-gray-500 transition-colors">{step.num} —</span>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white tracking-wide transition-colors">{step.title}</h3>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed font-light transition-colors">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NEW SECTION 1: Beautiful Rooms & Floor Plans */}
      <section className="py-32 bg-white dark:bg-gray-900 relative z-10 border-t border-gray-100 dark:border-gray-800 transition-colors duration-300">
        <div className="max-w-[1400px] mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Tall Image Carousel */}
          <div className="relative h-[600px] rounded-3xl overflow-hidden group">
            <AnimatePresence initial={false}>
              <motion.img 
                key={currentImgIndex}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5 }}
                src={carouselImages[currentImgIndex]} 
                alt="Beautiful Bathroom" 
                className="absolute inset-0 w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105"
              />
            </AnimatePresence>
            {/* Overlay UI */}
            <div className="absolute bottom-6 left-6 flex items-center gap-2 text-white/80 z-10">
              <Box size={16} />
              <span className="text-xs font-medium tracking-wide">Created in Home Planner</span>
            </div>
            <div className="absolute bottom-6 right-6 flex items-center gap-3 z-10">
              <button onClick={prevImg} className="w-10 h-10 rounded-full bg-black/40 backdrop-blur-md flex items-center justify-center text-white hover:bg-black/60 transition-colors">
                <ChevronLeft size={20} />
              </button>
              <button onClick={nextImg} className="w-10 h-10 rounded-full bg-black/40 backdrop-blur-md flex items-center justify-center text-white hover:bg-black/60 transition-colors">
                <ChevronRight size={20} />
              </button>
            </div>
          </div>

          {/* Right: Content blocks */}
          <div className="flex flex-col gap-16">
            <div className="grid sm:grid-cols-2 gap-8 items-center">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 leading-tight transition-colors">Beautiful Rooms —<br/>No Experience Needed</h3>
                <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed transition-colors">Create detailed layouts, arrange furniture freely, and see exactly how your space will look before making changes in real life.</p>
              </div>
              <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl h-48 overflow-hidden transition-colors">
                <img src="https://images.unsplash.com/photo-1600607686527-6fb886090705?q=80&w=600&auto=format&fit=crop" alt="3D Floor Plan" className="w-full h-full object-cover mix-blend-multiply dark:mix-blend-normal opacity-90" />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-8 items-center">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 leading-tight transition-colors">See Your Floor Plan<br/>Come to Life in 3D</h3>
                <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed transition-colors">Upload a photo or blueprint, and let AI instantly analyze and convert it into an editable 3D floor plan.</p>
              </div>
              <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl h-48 overflow-hidden p-6 flex items-center justify-center transition-colors">
                {/* Simulated 2D Blueprint */}
                <div className="w-full h-full border-2 border-gray-800 dark:border-gray-400 rounded relative bg-white dark:bg-gray-700 transition-colors">
                   <div className="absolute top-1/2 left-0 w-full h-[2px] bg-gray-800 dark:bg-gray-400 transition-colors"></div>
                   <div className="absolute top-0 left-1/3 w-[2px] h-full bg-gray-800 dark:bg-gray-400 transition-colors"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* NEW SECTION 2: Design with precision */}
      <section className="py-24 bg-[#fcfcfd] dark:bg-gray-950 relative z-10 transition-colors duration-300">
        <div className="max-w-[1400px] mx-auto px-6">
          <div className="bg-white dark:bg-gray-900 rounded-[2.5rem] p-10 lg:p-16 border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-white mb-3 transition-colors">Design your room with precision</h2>
            <p className="text-gray-500 dark:text-gray-400 mb-10 transition-colors">Not just ideas — real projects built in Home Planner. Move, customize, and recreate every detail in your own 3D design.</p>
            
            {/* Categories */}
            <div className="flex flex-wrap items-center gap-3 mb-10">
              <button className="px-6 py-2.5 bg-black dark:bg-white text-white dark:text-gray-900 rounded-full text-sm font-semibold transition-colors">Living Room</button>
              <button className="px-6 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-sm font-semibold transition-colors">Bedroom</button>
              <button className="px-6 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-sm font-semibold transition-colors">Kitchen</button>
              <button className="px-6 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-sm font-semibold transition-colors">Bathroom</button>
              <button className="px-6 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-sm font-semibold transition-colors">Outdoor Space</button>
              <button className="px-6 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-sm font-semibold transition-colors">20+ Other Rooms</button>
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
              {/* Left Large Image */}
              <div className="lg:col-span-2 relative rounded-3xl overflow-hidden h-[500px]">
                <img src="https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?q=80&w=1200&auto=format&fit=crop" alt="Living Room" className="w-full h-full object-cover" />
                {/* Interactive Tags */}
                <div className="absolute top-1/3 left-1/3 w-8 h-8 bg-black/50 backdrop-blur-md rounded-full flex items-center justify-center border border-white/30 cursor-pointer animate-pulse hover:scale-125 transition-transform">
                  <div className="w-2 h-2 bg-white rounded-full"></div>
                </div>
                <div className="absolute bottom-1/4 right-1/4 w-8 h-8 bg-black/50 backdrop-blur-md rounded-full flex items-center justify-center border border-white/30 cursor-pointer animate-pulse hover:scale-125 transition-transform">
                  <div className="w-2 h-2 bg-white rounded-full"></div>
                </div>
                <div className="absolute bottom-6 left-6 flex items-center gap-2 text-white/80">
                  <Box size={16} />
                  <span className="text-xs font-medium tracking-wide">Created in Home Planner</span>
                </div>
              </div>

              {/* Right Products */}
              <div className="flex flex-col justify-between h-[500px]">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl p-4 aspect-square flex items-center justify-center mb-3 transition-colors">
                      <div className="w-20 h-20 bg-gray-200 dark:bg-gray-700 rounded-full transition-colors"></div>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white transition-colors">Mirror Silver</p>
                  </div>
                  <div>
                    <div className="bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl p-4 aspect-square flex items-center justify-center mb-3 transition-colors">
                      <div className="w-24 h-12 bg-gray-300 dark:bg-gray-600 rounded transition-colors"></div>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white transition-colors">Sofa SKEJBY</p>
                  </div>
                  <div>
                    <div className="bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl p-4 aspect-square flex items-center justify-center mb-3 transition-colors">
                      <div className="w-8 h-16 bg-green-800 rounded-t-full rounded-b-md"></div>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white transition-colors">Ficus Benjamina</p>
                  </div>
                  <div>
                    <div className="bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl p-4 aspect-square flex items-center justify-center mb-3 transition-colors">
                      <div className="w-16 h-8 bg-amber-700 rounded-full"></div>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white transition-colors">Molly Coffee Table</p>
                  </div>
                </div>
                
                <button className="w-full py-4 bg-black dark:bg-white hover:bg-gray-900 dark:hover:bg-gray-200 text-white dark:text-gray-900 rounded-xl font-bold transition-colors">
                  Try it for free
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 9. FINAL CTA */}
      <section className="py-32 bg-gray-900 text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-5 pointer-events-none" style={{ backgroundImage: 'linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)', backgroundSize: '50px 50px' }}></div>
        
        <div className="max-w-[1400px] mx-auto px-6 relative z-10 text-center flex flex-col items-center">
          <h2 className="text-5xl lg:text-7xl font-medium tracking-tight mb-6 font-serif">
            Your Dream Home<br/>Starts With an Idea.
          </h2>
          <p className="text-xl text-gray-400 font-light mb-12">
            Let AI turn that idea into architecture.
          </p>
          <Link to="/login" className="bg-white hover:bg-gray-100 text-gray-900 px-10 py-5 text-xs font-bold tracking-[0.15em] transition-all flex items-center justify-center gap-3 w-max">
            CREATE YOUR HOME <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-white dark:bg-gray-950 border-t border-gray-100 dark:border-gray-800 pt-20 pb-10 transition-colors duration-300">
        <div className="max-w-[1400px] mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-10 mb-16">
            <div className="col-span-2 lg:col-span-2">
              <div className="flex items-center gap-2 mb-6">
                <Box className="text-gray-900 dark:text-white transition-colors" size={20} strokeWidth={2} />
                <span className="text-sm font-bold text-gray-900 dark:text-white tracking-[0.2em] transition-colors">HOMEPLANNER<span className="text-gray-400">AI</span></span>
              </div>
              <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed max-w-sm mb-6 transition-colors">
                The most advanced AI architecture platform. Design, visualize, and plan your perfect home with precision and ease.
              </p>
            </div>
            
            <div>
              <h4 className="font-bold text-gray-900 dark:text-white mb-4 text-sm tracking-wider uppercase transition-colors">Product</h4>
              <ul className="space-y-3 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Features</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">AI Floor Plans</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">3D Visualization</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Pricing</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 dark:text-white mb-4 text-sm tracking-wider uppercase transition-colors">Resources</h4>
              <ul className="space-y-3 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Design Gallery</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Architecture Blog</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Help Center</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Community</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 dark:text-white mb-4 text-sm tracking-wider uppercase transition-colors">Company</h4>
              <ul className="space-y-3 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">About Us</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Careers</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Contact</a></li>
                <li><a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors">Privacy Policy</a></li>
              </ul>
            </div>
          </div>
          
          <div className="pt-8 border-t border-gray-100 dark:border-gray-800 flex flex-col md:flex-row items-center justify-between gap-4 transition-colors">
            <p className="text-xs text-gray-400">© 2026 HomePlanner AI. All rights reserved.</p>
            <div className="flex items-center gap-4 text-gray-400">
              <a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path></svg></a>
              <a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z"></path></svg></a>
              <a href="#" className="hover:text-gray-900 dark:hover:text-white transition-colors"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg></a>
            </div>
          </div>
        </div>
      </footer>
      
    </div>
  );
};

export default HomePage;
