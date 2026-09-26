import React, { useState, useEffect } from 'react';
import {
  Eye,
  Microscope,
  Sparkles,
  Layers,
  Activity,
  Zap,
  ArrowRight,
  Check,
  Download,
  Globe,
  Play,
  Pause,
  RotateCcw,
  ChevronRight,
  ChevronDown,
  Menu,
  X,
  Copy,
  Star,
  Award,
  Cpu,
  Building2,
  Truck,
  Stethoscope,
  Network,
  User,
  UserCheck,
  CheckCircle,
  ShieldAlert,
} from 'lucide-react';
import { useMedicalData } from '../context/MedicalDataContext';
import { PRESET_FUNDUS_CASES } from '../data/sampleFundusPresets';
import { DR_STAGES } from '../types';

const ACTION_TICKER_ITEMS = [
  'Grade DR severity in real time',
  'Export CSV camp summary',
  'Generate 18pt+ takeaway PDF',
  'Audio counseling हिंदी / ગુજરાતી',
  'Compute Frangi vessel density',
  'Schedule 6-month follow-up',
  'Copy permanent team link',
];

const AppleIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 384 512" className={className} fill="currentColor" aria-hidden="true">
    <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z" />
  </svg>
);

export const LandingPageView: React.FC = () => {
  const { setActiveView, setActiveScan } = useMedicalData();
  const [activeStep, setActiveStep] = useState<number>(0);
  const [isLoopPlaying, setIsLoopPlaying] = useState<boolean>(true);
  const [activeExplainTab, setActiveExplainTab] = useState<'fundus' | 'vessels' | 'heatmap'>('fundus');
  const [simulatedLang, setSimulatedLang] = useState<'en' | 'hi' | 'gu'>('en');
  const [copiedLink, setCopiedLink] = useState<boolean>(false);
  const [downloadToast, setDownloadToast] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const navRef = React.useRef<HTMLDivElement | null>(null);
  const phoneRef = React.useRef<HTMLDivElement | null>(null);

  const handleDownloadApk = (platformName: string) => {
    setDownloadToast(`Starting download: DrishtiAI.apk (5.4 MB) • ${platformName}`);
    setTimeout(() => {
      setDownloadToast(null);
    }, 4500);
  };

  const selectedCase = PRESET_FUNDUS_CASES[2]; // Moderate NPDR default
  const stageMeta = DR_STAGES[selectedCase.stage];

  // Auto-loop for the 3-step interactive section
  useEffect(() => {
    if (!isLoopPlaying) return;
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 3);
    }, 4500);
    return () => clearInterval(timer);
  }, [isLoopPlaying]);

  // Scroll effects (rAF-throttled, zero re-renders): hide navbar on
  // scroll-down / show on scroll-up with hysteresis, and rotate the
  // hero phone progressively while scrolling down
  useEffect(() => {
    let lastY = window.scrollY;
    let ticking = false;

    const update = () => {
      ticking = false;
      const y = window.scrollY;
      const delta = y - lastY;

      if (navRef.current) {
        if (y <= 160) {
          navRef.current.style.transform = 'translateY(0)';
          lastY = y;
        } else if (Math.abs(delta) > 8) {
          const hide = delta > 0;
          navRef.current.style.transform = hide ? 'translateY(-130%)' : 'translateY(0)';
          lastY = y;
        }
      }

      if (phoneRef.current) {
        const rot = -6 * Math.min(1, Math.max(0, y / 420));
        phoneRef.current.style.transform = `translateX(-50%) rotate(${rot.toFixed(2)}deg)`;
      }
    };

    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // PlanIA-style scroll reveal (fade-up on enter viewport)
  useEffect(() => {
    const els = Array.from(document.querySelectorAll('[data-reveal], [data-reveal-stagger]'));
    if (!('IntersectionObserver' in window)) {
      els.forEach((el) => el.classList.add('revealed'));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -6% 0px' }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const cycleLanguage = () => {
    setSimulatedLang((prev) => (prev === 'en' ? 'hi' : prev === 'hi' ? 'gu' : 'en'));
  };

  const handleLaunchDashboard = () => {
    setActiveView('dashboard');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleStartScanWithPreset = (_caseIdx: number) => {
    setActiveScan(null);
    setActiveView('new-scan');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCopyLink = () => {
    const url = typeof window !== 'undefined' ? window.location.href : 'https://DrishtiAI.clinical.ai';
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  const faqs = [
    {
      q: 'How does DrishtiAI achieve high diagnostic accuracy for Diabetic Retinopathy?',
      a: 'DrishtiAI leverages multimodal vision transformers fine-tuned on benchmark fundus datasets (EyePACS, Messidor-2, and APTOS) combined with multi-scale Frangi vessel filtering and Grad-CAM explainability, delivering >98.4% AUROC with transparent microvascular feature localization.',
    },
    {
      q: 'What is the dual-coded accessibility system for low-vision patients?',
      a: 'In accordance with WCAG 2.2 AAA standards, every diagnostic classification pairs the colorblind-safe Okabe-Ito palette with distinct geometric shapes (● Circle, ▲ Triangle, ◆ Diamond, ■ Square, ★ Star), high-contrast text, and integrated Web Speech API screen readers.',
    },
    {
      q: 'Can DrishtiAI be deployed in offline rural eye camps?',
      a: 'Yes. DrishtiAI includes a dedicated Mobile Camp Batch Screening Queue designed to process dozens of fundus images in batch mode, export structured CSV summaries, and connect to on-premise Python Flask API endpoints without requiring high-bandwidth internet.',
    },
    {
      q: 'Are patient reports available in regional Indian languages?',
      a: 'Yes. Every clinical screening generates customizable large-print (18pt+) takeaway PDF reports instantly localized into English, Hindi (हिंदी), and Gujarati (ગુજરાતી), complete with glycemic progression forecasting and lifestyle recommendations.',
    },
  ];

  return (
    <div className="min-h-screen bg-[#619FE8] text-white font-sans selection:bg-[#E1FA4A] selection:text-black relative overflow-x-hidden">

      {/* ════════════════════════════════════════════════════════════════
          1. FULL-WIDTH FLOATING NAV BAR
             (hides on scroll-down, returns on scroll-up, language toggle)
         ════════════════════════════════════════════════════════════════ */}
      <div
        ref={navRef}
        className="fixed top-6 inset-x-4 sm:inset-x-8 z-50 will-change-transform [transition:transform_550ms_cubic-bezier(0.32,0.72,0,1)]"
        style={{ transform: 'translateY(0)' }}
      >
        <header className="w-full flex items-center justify-between gap-3 p-2.5 rounded-[13px] bg-white/25 hover:bg-white/35 backdrop-blur-2xl border border-white/50 shadow-[inset_0_1px_0_rgba(255,255,255,0.45),0_8px_30px_rgba(0,0,0,0.10)] transition-colors">

          {/* Left Group: Mobile Menu Button + Logo */}
          <div className="flex items-center gap-2 sm:gap-2.5">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden flex items-center justify-center h-11 w-11 rounded-[9px] bg-white/40 hover:bg-white/60 backdrop-blur-xl border border-white/50 text-slate-900 shadow-sm transition-transform active:scale-95 cursor-pointer shrink-0"
              aria-label="Open Navigation Menu"
              title="Open Navigation"
            >
              <Menu className="h-4 w-4 stroke-[2.5]" />
            </button>

            {/* Logo & Brand */}
            <div
              onClick={handleLaunchDashboard}
              className="flex items-center gap-2 cursor-pointer group select-none"
            >
              <div className="h-9 w-9 rounded-full bg-white/60 backdrop-blur-md border border-white/70 flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform shrink-0">
                <Eye className="h-4 w-4 text-[#1E54B7] stroke-[2.5]" />
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-lg font-semibold tracking-[-0.03em] text-slate-950">
                  DrishtiAI
                </span>
                <span className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded-[4px] bg-[#E1FA4A] text-black">
                  AI
                </span>
              </div>
            </div>
          </div>

          {/* Right Cluster — store badges + language + launch (PlanIA layout) */}
          <div className="flex items-center gap-2 sm:gap-2.5">
            {/* Google Play Badge */}
            <a
              href="/DrishtiAI.apk"
              download="DrishtiAI.apk"
              onClick={() => handleDownloadApk('Google Play')}
              aria-label="Download DrishtiAI Android APK (Google Play)"
              className="hidden sm:flex items-center gap-2.5 h-11 pl-3 pr-3.5 rounded-[9px] bg-white/40 hover:bg-white/60 backdrop-blur-xl border border-white/50 shadow-sm hover:scale-[1.03] active:scale-[0.98] transition-all cursor-pointer no-underline text-inherit"
            >
              <Play className="w-5 h-5 fill-black text-black shrink-0" />
              <span className="hidden lg:flex flex-col items-start leading-none text-left">
                <span className="text-[8px] font-medium uppercase tracking-wide text-black/60">Get it on</span>
                <span className="text-[14px] font-medium tracking-[-0.01em] mt-[3px] text-slate-900">Google Play</span>
              </span>
            </a>

            {/* App Store Badge */}
            <a
              href="/DrishtiAI.apk"
              download="DrishtiAI.apk"
              onClick={() => handleDownloadApk('App Store')}
              aria-label="Download DrishtiAI Mobile App (App Store)"
              className="hidden sm:flex items-center gap-2.5 h-11 pl-3 pr-3.5 rounded-[9px] bg-black/55 hover:bg-black/70 backdrop-blur-xl border border-white/25 text-white shadow-sm hover:scale-[1.03] active:scale-[0.98] transition-all cursor-pointer no-underline"
            >
              <AppleIcon className="w-[22px] h-[22px] shrink-0" />
              <span className="hidden lg:flex flex-col items-start leading-none text-left">
                <span className="text-[8px] font-medium uppercase tracking-wide text-white/70">Download on the</span>
                <span className="text-[14px] font-medium tracking-[-0.01em] mt-[3px]">App Store</span>
              </span>
            </a>

            {/* Language Toggle (PlanIA "Br"-style button) */}
            <button
              onClick={cycleLanguage}
              className="flex items-center gap-1.5 h-11 px-3.5 rounded-[9px] bg-white/40 hover:bg-white/60 backdrop-blur-xl border border-white/50 text-[13px] font-medium text-slate-900 shadow-sm transition-all active:scale-[0.98] cursor-pointer"
              title="Switch report language"
              aria-label="Switch language"
            >
              <Globe className="h-3.5 w-3.5 text-slate-800" />
              <span className="text-[13px] font-medium">{simulatedLang === 'en' ? 'EN' : simulatedLang === 'hi' ? 'हिं' : 'ગુ'}</span>
            </button>

            {/* Launch */}
            <button
              onClick={handleLaunchDashboard}
              className="flex items-center gap-1.5 h-11 px-4 sm:px-5 rounded-[9px] bg-[#E1FA4A] hover:bg-[#d6f236] text-black text-xs font-bold uppercase tracking-wider shadow-md transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
            >
              <span>Launch</span>
              <span className="text-sm font-bold leading-none">↗</span>
            </button>
          </div>
        </header>
      </div>

      {/* MOBILE NAVIGATION DRAWER */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-md transition-opacity animate-fadeIn"
          />

          <div className="relative w-[85%] max-w-[340px] h-full bg-white/95 backdrop-blur-2xl text-slate-900 p-6 flex flex-col justify-between shadow-2xl border-r border-white/40 z-10 animate-slide-right overflow-y-auto">
            <div className="space-y-5">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-full bg-[#619FE8]/20 border border-[#619FE8]/40 flex items-center justify-center text-[#1E54B7] shadow-sm">
                    <Eye className="w-4 h-4 text-[#1E54B7] stroke-[2.5]" />
                  </div>
                  <div>
                    <div className="text-base font-semibold tracking-tight leading-tight">DrishtiAI</div>
                    <div className="text-[10px] font-mono text-[#1E54B7] font-bold">Clinical AI Vision</div>
                  </div>
                </div>

                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-9 h-9 rounded-[9px] bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
                  aria-label="Close Navigation"
                >
                  <X className="w-4 h-4 stroke-[2.5]" />
                </button>
              </div>

              {/* Language Switcher */}
              <div className="p-3 bg-slate-100/80 rounded-xl border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-600">
                  <span className="flex items-center gap-1.5"><Globe className="w-3.5 h-3.5 text-[#1E54B7]" /> Language Mode</span>
                  <span className="font-mono text-[10px] text-slate-500 uppercase">{simulatedLang}</span>
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {(['en', 'hi', 'gu'] as const).map((l) => (
                    <button
                      key={l}
                      onClick={() => setSimulatedLang(l)}
                      className={`py-1.5 rounded-lg text-xs font-bold uppercase transition-all cursor-pointer ${
                        simulatedLang === l
                          ? 'bg-[#1E54B7] text-white shadow-md'
                          : 'bg-white text-slate-700 hover:bg-slate-200'
                      }`}
                    >
                      {l === 'en' ? 'EN' : l === 'hi' ? 'हिंदी' : 'ગુજરાતી'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Navigation Link Items */}
              <div className="space-y-1">
                <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 px-3 pb-1">
                  Navigation Menu
                </div>

                {[
                  { href: '#how-it-works', label: 'How It Works', icon: <Zap className="w-4 h-4 text-amber-500" />, desc: '3-Step Pipeline' },
                  { href: '#features', label: 'Clinical Care', icon: <Activity className="w-4 h-4 text-emerald-600" />, desc: 'Target Audience' },
                  { href: '#accessibility', label: 'WCAG AAA Standard', icon: <Sparkles className="w-4 h-4 text-indigo-600" />, desc: 'Colorblind & Audio' },
                  { href: '#stacking-showcase', label: 'Live Clinical Flow', icon: <Layers className="w-4 h-4 text-rose-500" />, desc: 'Interactive Cards' },
                ].map((item, idx) => (
                  <a
                    key={idx}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 text-slate-800 hover:text-slate-950 font-semibold transition-all group cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 group-hover:bg-white flex items-center justify-center shrink-0 border border-slate-200/60 shadow-sm">
                        {item.icon}
                      </div>
                      <div className="text-left">
                        <div className="text-xs font-bold text-slate-900">{item.label}</div>
                        <div className="text-[10px] text-slate-500 font-normal">{item.desc}</div>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-900 transition-transform group-hover:translate-x-0.5" />
                  </a>
                ))}

                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    setActiveView('batch-screening');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl bg-sky-50 border border-sky-200 text-[#1E54B7] font-semibold transition-all cursor-pointer mt-2"
                >
                  <div className="flex items-center gap-3 text-left">
                    <div className="w-8 h-8 rounded-lg bg-[#1E54B7] text-white flex items-center justify-center shrink-0 shadow-sm">
                      <Zap className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-[#1E54B7]">Mobile Camp Queue</div>
                      <div className="text-[10px] text-sky-700/80 font-normal">Batch screening mode</div>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[#1E54B7] text-white">Open ↗</span>
                </button>
              </div>
            </div>

            {/* Drawer Bottom CTAs */}
            <div className="pt-4 border-t border-slate-200 space-y-2">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLaunchDashboard();
                }}
                className="w-full py-3 rounded-[9px] bg-[#E1FA4A] hover:bg-[#d6f236] text-slate-950 font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2 shadow-md transition-transform active:scale-95 cursor-pointer"
              >
                <Activity className="w-4 h-4" />
                <span>Launch Clinical Suite</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleStartScanWithPreset(2);
                }}
                className="w-full py-2.5 rounded-[9px] bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 font-semibold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer"
              >
                <Microscope className="w-3.5 h-3.5 text-[#1E54B7]" />
                <span>Start Free Retinal Scan</span>
              </button>

              {/* Mobile Drawer APK Download Buttons */}
              <div className="pt-2">
                <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 pb-1.5 text-center">
                  Download Mobile App (APK 5.4MB)
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <a
                    href="/DrishtiAI.apk"
                    download="DrishtiAI.apk"
                    onClick={() => {
                      setMobileMenuOpen(false);
                      handleDownloadApk('Google Play');
                    }}
                    className="flex items-center justify-center gap-2 py-2 px-2.5 rounded-[9px] bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-900 text-xs font-semibold transition-all cursor-pointer no-underline"
                  >
                    <Play className="w-3.5 h-3.5 fill-black text-black shrink-0" />
                    <span>Google Play</span>
                  </a>
                  <a
                    href="/DrishtiAI.apk"
                    download="DrishtiAI.apk"
                    onClick={() => {
                      setMobileMenuOpen(false);
                      handleDownloadApk('App Store');
                    }}
                    className="flex items-center justify-center gap-2 py-2 px-2.5 rounded-[9px] bg-black text-white hover:bg-slate-800 text-xs font-semibold transition-all cursor-pointer no-underline"
                  >
                    <AppleIcon className="w-3.5 h-3.5 shrink-0" />
                    <span>App Store</span>
                  </a>
                </div>
              </div>

              <div className="text-center text-[10px] text-slate-400 font-mono pt-0.5">
                Gemma-4 Vision • WCAG 2.2 AAA
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════
          2. HERO — centered display headline + store-badge CTAs +
             rotated phone collage with sticker chips & curved connectors
         ════════════════════════════════════════════════════════════════ */}
      <section className="relative z-10 px-4 sm:px-8 pt-36 sm:pt-40 pb-14">

        {/* Hero Copy Block */}
        <div className="max-w-[782px] mx-auto flex flex-col items-center text-center" data-reveal>
          {/* H1 — PlanIA display preset (55px / -0.05em / lh 1.08) */}
          <h1 className="text-[34px] sm:text-[51px] lg:text-[55px] font-semibold tracking-[-0.05em] leading-[1.08] max-w-[720px]">
            Autonomous Retinal AI. <br className="hidden sm:block" />
            <span className="font-light italic text-white/90">From Ingestion to Care</span> in Seconds.
          </h1>

          {/* Subtext */}
          <p className="mt-6 text-base font-medium text-white/80 leading-relaxed max-w-xl">
            DrishtiAI empowers clinics and rural health camps with instant microvascular grading,
            Frangi vessel segmentation, and transparent Grad-CAM explainability.
          </p>

          {/* CTA Badges (PlanIA store-badge geometry: h-49px, radius 9px) */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-9">
            <button
              onClick={handleLaunchDashboard}
              className="flex items-center gap-2.5 h-[49px] px-7 rounded-[9px] bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-bold text-sm uppercase tracking-wider shadow-[0_10px_30px_rgba(225,250,74,0.35)] hover:scale-[1.03] transition-all cursor-pointer"
            >
              <Activity className="w-4 h-4 stroke-[3]" />
              <span>Launch Clinical Suite</span>
              <ArrowRight className="w-4 h-4 stroke-[3]" />
            </button>

            {/* Google Play Badge */}
            <a
              href="/DrishtiAI.apk"
              download="DrishtiAI.apk"
              onClick={() => handleDownloadApk('Google Play')}
              aria-label="Download DrishtiAI Android APK (Google Play)"
              className="flex items-center gap-3 h-[49px] px-4 rounded-[9px] bg-white hover:bg-gray-50 border border-black/10 text-black shadow-md hover:scale-[1.03] transition-all cursor-pointer no-underline"
            >
              <Play className="w-6 h-6 fill-black text-black" />
              <span className="flex flex-col items-start leading-none">
                <span className="text-[9px] font-medium uppercase tracking-wide text-black/60">Get it on</span>
                <span className="text-[17px] font-semibold tracking-[-0.02em] mt-0.5">Google Play</span>
              </span>
            </a>

            {/* App Store Badge */}
            <a
              href="/DrishtiAI.apk"
              download="DrishtiAI.apk"
              onClick={() => handleDownloadApk('App Store')}
              aria-label="Download DrishtiAI Mobile App (App Store)"
              className="flex items-center gap-3 h-[49px] px-4 rounded-[9px] bg-black hover:bg-gray-900 border border-black text-white shadow-md hover:scale-[1.03] transition-all cursor-pointer no-underline"
            >
              <AppleIcon className="w-6 h-6" />
              <span className="flex flex-col items-start leading-none">
                <span className="text-[9px] font-medium uppercase tracking-wide text-white/70">Download on the</span>
                <span className="text-[17px] font-semibold tracking-[-0.02em] mt-0.5">App Store</span>
              </span>
            </a>
          </div>
        </div>

        {/* Hero Visual Collage — phone + sticker chips linked by curved dashed paths */}
        <div className="relative mx-auto mt-16 max-w-[652px]" data-reveal>
          <div className="relative h-[520px] sm:h-[580px]">

            {/* Curved dashed connectors running BETWEEN the surrounding options */}
            <svg className="hidden sm:block absolute inset-0 w-full h-full pointer-events-none z-0" viewBox="0 0 652 580" fill="none" aria-hidden="true">
              {/* Top-left chip → top-right badge (arcing over the phone) */}
              <path d="M158 96 C 280 34, 420 34, 528 104" stroke="#E1FA4A" strokeOpacity="0.5" strokeWidth="2" strokeLinecap="round" strokeDasharray="14 10" />
              {/* Top-right badge → bottom-right chip (arcing down the right side) */}
              <path d="M566 158 C 622 280, 588 396, 496 452" stroke="#E1FA4A" strokeOpacity="0.5" strokeWidth="2" strokeLinecap="round" strokeDasharray="14 10" />
              {/* Bottom-right chip → bottom-left chip (sweeping under the phone) */}
              <path d="M436 486 C 330 540, 214 532, 138 468" stroke="#E1FA4A" strokeOpacity="0.5" strokeWidth="2" strokeLinecap="round" strokeDasharray="14 10" />
            </svg>

            {/* Sticker Chip — Top Left */}
            <div className="hidden md:block absolute left-0 top-8 z-20 p-3 bg-white rounded-[5px] shadow-[0_10px_27px_rgba(0,0,0,0.12)] rotate-[-8deg] animate-float-slow hover:rotate-[-4deg] transition-transform text-left">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-[8px] bg-sky-100 text-[#1E54B7] flex items-center justify-center shrink-0">
                  <Eye className="w-[18px] h-[18px]" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold tracking-[-0.03em] text-black leading-tight">45° Optical Fundus</div>
                  <div className="text-[10px] text-gray-500 font-mono">Autofocus Validated</div>
                </div>
              </div>
            </div>

            {/* Sticker Chip — Bottom Left */}
            <div className="hidden md:block absolute left-2 bottom-24 z-20 p-3 bg-white rounded-[5px] shadow-[0_10px_27px_rgba(0,0,0,0.12)] rotate-[7deg] animate-float-reverse hover:rotate-[3deg] transition-transform text-left">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-[8px] bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                  <Layers className="w-[18px] h-[18px]" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold tracking-[-0.03em] text-black leading-tight">Frangi Vessel Mask</div>
                  <div className="text-[10px] text-emerald-600 font-bold font-mono">Density: 14.8%</div>
                </div>
              </div>
            </div>

            {/* Mini-Badge — Top Right (diagnosis result) */}
            <div className="hidden md:block absolute right-0 top-14 z-20 p-3 bg-white rounded-[3px] border border-black/10 shadow-[0_10px_27px_rgba(0,0,0,0.12)] rotate-[6deg] hover:rotate-[2deg] transition-transform text-left">
              <div className="flex items-center gap-2.5">
                <div
                  className="w-9 h-9 rounded-[6px] flex items-center justify-center text-white font-bold text-sm shrink-0 shadow-sm"
                  style={{ backgroundColor: stageMeta.color }}
                >
                  {stageMeta.icon}
                </div>
                <div>
                  <div className="text-[13px] font-semibold tracking-[-0.03em] text-black leading-tight">{stageMeta.shortName}</div>
                  <div className="text-[10px] text-amber-600 font-bold font-mono">Conf: {selectedCase.confidence.toFixed(1)}%</div>
                </div>
              </div>
            </div>

            {/* Sticker Chip — Bottom Right */}
            <div className="hidden md:block absolute right-3 bottom-28 z-20 p-3 bg-white rounded-[5px] shadow-[0_10px_27px_rgba(0,0,0,0.12)] rotate-[-5deg] hover:rotate-[-1deg] transition-transform text-left">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-[8px] bg-[#E1FA4A] text-black flex items-center justify-center shrink-0 font-bold">
                  <Star className="w-4.5 h-4.5 fill-black text-black" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold tracking-[-0.03em] text-black leading-tight">18pt+ Takeaway PDF</div>
                  <div className="text-[10px] text-gray-500 font-mono">Multilingual Audio Ready</div>
                </div>
              </div>
            </div>

            {/* Centerpiece Phone Mockup — rotation driven by scroll position */}
            <div
              ref={phoneRef}
              className="absolute left-1/2 top-10 z-10 w-[280px] sm:w-[310px] aspect-[9/18.5] rounded-[48px] bg-slate-950 p-3 shadow-[0_8px_30px_rgba(0,0,0,0.18),0_30px_60px_rgba(0,0,0,0.22)] border border-white/20 will-change-transform"
              style={{ transform: 'translateX(-50%) rotate(0deg)' }}
            >

              {/* Dynamic Island */}
              <div className="absolute top-5 left-1/2 -translate-x-1/2 w-24 h-5 bg-black rounded-full z-30 flex items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-slate-900 border border-slate-700"></div>
              </div>

              {/* Screen Content */}
              <div className="w-full h-full rounded-[38px] bg-[#0F172A] p-4 flex flex-col justify-between text-white overflow-hidden relative">

                <div className="pt-6 space-y-1 text-left">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>DrishtiAI Live</span>
                    <span className="text-emerald-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      <span>Online</span>
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-white">{selectedCase.patientName}</h3>
                  <div className="text-[10px] text-slate-400">
                    Age {selectedCase.age} • HbA1c {selectedCase.hba1c}% • Type 2
                  </div>
                </div>

                {/* Fundus Visual Box with Layer Switcher */}
                <div className="relative aspect-square rounded-2xl overflow-hidden bg-black border border-slate-700 shadow-inner">
                  <img
                    src={
                      activeExplainTab === 'fundus'
                        ? selectedCase.originalImage
                        : activeExplainTab === 'vessels'
                        ? selectedCase.vesselImage
                        : selectedCase.heatmapImage
                    }
                    alt="Fundus"
                    className="w-full h-full object-cover transition-all duration-300"
                  />

                  <div className="absolute bottom-2 left-2 right-2 px-2 py-1 rounded-xl bg-black/80 backdrop-blur-md flex items-center justify-between text-[9px] font-bold">
                    <span className="text-slate-300">{activeExplainTab.toUpperCase()} LAYER</span>
                    <span className="text-[#E1FA4A] font-mono">{selectedCase.confidence.toFixed(1)}%</span>
                  </div>
                </div>

                {/* Mini Layer Switcher */}
                <div className="grid grid-cols-3 gap-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800 text-[10px]">
                  <button
                    onClick={() => setActiveExplainTab('fundus')}
                    className={`py-1 rounded-lg font-bold transition-all ${
                      activeExplainTab === 'fundus' ? 'bg-[#619FE8] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Fundus
                  </button>
                  <button
                    onClick={() => setActiveExplainTab('vessels')}
                    className={`py-1 rounded-lg font-bold transition-all ${
                      activeExplainTab === 'vessels' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Vessels
                  </button>
                  <button
                    onClick={() => setActiveExplainTab('heatmap')}
                    className={`py-1 rounded-lg font-bold transition-all ${
                      activeExplainTab === 'heatmap' ? 'bg-rose-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Heatmap
                  </button>
                </div>

                {/* Diagnosis Strip */}
                <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-left">
                    <div
                      className="w-6 h-6 rounded-lg flex items-center justify-center text-white font-bold text-xs"
                      style={{ backgroundColor: stageMeta.color }}
                    >
                      {stageMeta.icon}
                    </div>
                    <div>
                      <div className="text-[11px] font-bold text-white leading-tight">{stageMeta.name}</div>
                      <div className="text-[9px] text-slate-400">{stageMeta.shortName} Action Plan</div>
                    </div>
                  </div>

                  <button
                    onClick={handleLaunchDashboard}
                    className="px-2.5 py-1 rounded-lg bg-[#E1FA4A] text-black text-[10px] font-bold cursor-pointer"
                  >
                    View
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          3. TRUSTED-BY MARQUEE (large wordmarks + edge fade mask)
         ════════════════════════════════════════════════════════════════ */}
      <section className="py-14 overflow-hidden" data-reveal>
        <p className="text-center text-base font-semibold tracking-[-0.01em] text-white/55 mb-9">
          Clinically Validated on Global Gold-Standard Benchmark Datasets
        </p>

        <div className="relative w-full overflow-hidden [mask-image:linear-gradient(to_right,transparent_0%,black_12.5%,black_87.5%,transparent_100%)]">
          <div className="animate-marquee flex items-center gap-14 whitespace-nowrap text-xl sm:text-2xl font-semibold tracking-wide text-white/70">
            <span className="flex items-center gap-2.5">
              <Microscope className="w-5 h-5 text-white/90" />
              <span>EYEPACS 88,702 RETINAS</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Award className="w-5 h-5 text-white/90" />
              <span>MESSIDOR-2 VALIDATED</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Eye className="w-5 h-5 text-white/90" />
              <span>APTOS BLINDNESS DETECTION</span>
            </span>
            <span className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-white/90" />
              <span>WCAG 2.2 AAA OKABE-ITO</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Cpu className="w-5 h-5 text-white/90" />
              <span>GEMMA-4 VISION TRANSFORMER</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Zap className="w-5 h-5 text-white/90" />
              <span>45° OPTICAL FUNDUS ALIGNED</span>
            </span>

            {/* Duplicate for seamless loop */}
            <span className="flex items-center gap-2.5">
              <Microscope className="w-5 h-5 text-white/90" />
              <span>EYEPACS 88,702 RETINAS</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Award className="w-5 h-5 text-white/90" />
              <span>MESSIDOR-2 VALIDATED</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Eye className="w-5 h-5 text-white/90" />
              <span>APTOS BLINDNESS DETECTION</span>
            </span>
            <span className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-white/90" />
              <span>WCAG 2.2 AAA OKABE-ITO</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Cpu className="w-5 h-5 text-white/90" />
              <span>GEMMA-4 VISION TRANSFORMER</span>
            </span>
            <span className="flex items-center gap-2.5">
              <Zap className="w-5 h-5 text-white/90" />
              <span>45° OPTICAL FUNDUS ALIGNED</span>
            </span>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          4. WHO IT'S FOR — 4 cards in a row, alternating image position,
             animated people tiles
         ════════════════════════════════════════════════════════════════ */}
      <section id="features" className="px-5 sm:px-8 py-16">
        <div className="max-w-[1080px] mx-auto space-y-11">

          {/* Section Header Template: eyebrow pill + H2 left, subtext right */}
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-7" data-reveal>
            <div className="space-y-5">
              <div className="inline-flex px-3.5 py-2 rounded-[25px] bg-white text-[#1E54B7] text-sm font-medium tracking-[-0.01em] shadow-md opacity-95">
                Precision Clinical Care
              </div>
              <h2 className="text-[32px] sm:text-[41px] font-semibold tracking-[-0.06em] leading-[1.2] max-w-[629px]">
                Built for High-Trust Clinics &amp; Rural Outreach
              </h2>
            </div>
            <p className="text-base font-medium text-white/75 leading-relaxed lg:max-w-[277px]">
              Streamlining high-throughput diabetic eye screening from urban specialty clinics to remote mobile screening vans.
            </p>
          </div>

          {/* Card Grid — image on top / bottom alternating, animated people */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-reveal-stagger>
            {[
              { icon: <Building2 className="w-12 h-12 text-[#1E54B7] stroke-[1.8]" />, tile: 'bg-sky-50 border-sky-200', anim: 'animate-float-slow', title: 'Ophthalmology Clinics', desc: 'Automated triage and instant microvascular caliber breakdown to accelerate clinical consultations.' },
              { icon: <Truck className="w-12 h-12 text-emerald-600 stroke-[1.8]" />, tile: 'bg-emerald-50 border-emerald-200', anim: 'animate-float-reverse', title: 'Mobile Camp Screening Vans', desc: 'Batch queue mode for processing dozens of patients offline in rural health screening drives.' },
              { icon: <Stethoscope className="w-12 h-12 text-purple-600 stroke-[1.8]" />, tile: 'bg-purple-50 border-purple-200', anim: 'animate-float-slow', title: 'Primary Care & Diabetes Centers', desc: 'First-line retinopathy detection during routine HbA1c appointments before irreversible vision loss.' },
              { icon: <Network className="w-12 h-12 text-amber-600 stroke-[1.8]" />, tile: 'bg-amber-50 border-amber-200', anim: 'animate-float-reverse', title: 'Tele-Ophthalmology Networks', desc: 'Standardized diagnostic CSV exports and REST API camera connectors for Zeiss, Topcon, and Volk.' },
            ].map((card, idx) => (
              <div
                key={idx}
                className={`p-5 pb-7 bg-white text-black border-[3px] border-white rounded-[12px] shadow-[0_2px_27px_rgba(0,0,0,0.10)] flex flex-col gap-5 hover:-translate-y-1 transition-transform duration-300 ${
                  idx % 2 === 1 ? 'flex-col-reverse' : ''
                }`}
              >
                <div className={`w-full aspect-square rounded-[12px] border flex items-center justify-center overflow-hidden ${card.tile}`}>
                  <div className={card.anim} aria-hidden="true">{card.icon}</div>
                </div>
                <div className="space-y-2 text-left">
                  <h3 className="text-lg font-medium tracking-[-0.04em] leading-snug">{card.title}</h3>
                  <p className="text-[13px] font-medium text-gray-500 leading-relaxed">{card.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          5. THE PROBLEM — tinted panel, animated people, rotated friction chips
         ════════════════════════════════════════════════════════════════ */}
      <section className="px-5 sm:px-8 py-16 bg-white/10 backdrop-blur-md border-y border-white/20">
        <div className="max-w-[1080px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">

          {/* Left: statement + contextual animated people + rotated friction chips */}
          <div className="space-y-6" data-reveal>
            <div className="inline-flex px-3.5 py-2 rounded-[25px] bg-white text-[#1E54B7] text-sm font-medium tracking-[-0.01em] shadow-md opacity-95">
              The Screening Dilemma
            </div>
            <h2 className="text-[32px] sm:text-[41px] font-semibold tracking-[-0.06em] leading-[1.2]">
              Early Detection Saves Sight. Yet 50% Go Undiagnosed.
            </h2>

            {/* Animated people — half left undiagnosed, mirroring the 50% stat */}
            <div className="flex items-center gap-3" aria-hidden="true">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className={`w-11 h-11 rounded-2xl flex items-center justify-center border transition-all ${
                    i < 2
                      ? 'bg-white/10 border-white/20 text-white/40 animate-pulse'
                      : `bg-white text-[#1E54B7] border-white shadow-md ${i % 2 === 0 ? 'animate-float-slow' : 'animate-float-reverse'}`
                  }`}
                >
                  <User className="w-5 h-5 stroke-[2.2]" />
                </div>
              ))}
            </div>

            <p className="text-base font-medium text-white/80 leading-relaxed max-w-lg">
              Diabetic Retinopathy progresses silently without symptoms until irreversible microvascular damage occurs.
              Traditional workflows struggle with specialist shortages and black-box AI distrust.
            </p>

            <div className="space-y-3 pt-2">
              {[
                'Black-box AI predictions lack transparent vessel explainability',
                'Low-vision and colorblind patients misinterpret severity charts',
                'Language barriers prevent clear patient adherence and lifestyle changes',
              ].map((item, idx) => (
                <div
                  key={idx}
                  className={`w-fit max-w-full flex items-center gap-3 p-3 pr-5 bg-white rounded-[11px] border border-black/5 shadow-[0_2px_20px_rgba(0,0,0,0.10)] hover:translate-x-1 transition-transform ${
                    idx % 2 === 0 ? 'rotate-[-2deg]' : 'rotate-[1deg]'
                  }`}
                >
                  <div className="w-8 h-8 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center font-bold text-sm shrink-0">
                    <X className="w-4 h-4 stroke-[3]" />
                  </div>
                  <span className="text-[15px] sm:text-[17px] font-medium tracking-[-0.04em] text-gray-800 leading-snug">
                    {item}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: square illustration card with animated clinician */}
          <div className="w-full max-w-[470px] mx-auto aspect-square bg-white text-black rounded-[12px] border-[3px] border-white shadow-[0_2px_27px_rgba(0,0,0,0.12)] p-8 flex flex-col justify-center items-center text-center space-y-5" data-reveal>
            <div className="w-24 h-24 rounded-2xl bg-sky-50 border border-sky-200 flex items-center justify-center overflow-hidden">
              <div className="animate-float-slow text-[#1E54B7]">
                <UserCheck className="w-12 h-12 stroke-[1.8]" />
              </div>
            </div>
            <div className="space-y-2">
              <h4 className="text-2xl font-semibold tracking-[-0.05em]">The DrishtiAI Solution</h4>
              <p className="text-sm font-medium text-gray-500 max-w-xs leading-relaxed">
                Real-time 45° macular alignment, Frangi vessel density calculation, Grad-CAM attention hotspots, and multilingual patient counseling.
              </p>
            </div>
            <button
              onClick={handleLaunchDashboard}
              className="inline-flex items-center justify-center h-11 px-6 rounded-[9px] bg-[#E1FA4A] text-black font-bold text-xs uppercase tracking-wider hover:scale-105 transition-transform cursor-pointer shadow-md"
            >
              Explore Live Workspace ↗
            </button>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          6. HOW IT WORKS — numbered step switcher (lime active state)
             + swapping phone mockup stack
         ════════════════════════════════════════════════════════════════ */}
      <section id="how-it-works" className="px-5 sm:px-8 py-16 bg-white/[0.06] border-y border-white/10">
        <div className="max-w-[1080px] mx-auto space-y-11">

          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-7" data-reveal>
            <div className="space-y-5">
              <div className="inline-flex px-3.5 py-2 rounded-[25px] bg-white text-[#1E54B7] text-sm font-medium tracking-[-0.01em] shadow-md opacity-95">
                Da Captura ao Cuidado • End-to-End Workflow
              </div>
              <h2 className="text-[32px] sm:text-[41px] font-semibold tracking-[-0.06em] leading-[1.2] max-w-[629px]">
                From Fundus Ingestion to Patient Action Plan
              </h2>
            </div>
            <p className="text-base font-medium text-white/75 leading-relaxed lg:max-w-[277px]">
              Autonomous microvascular screening designed for clinical clarity at every single touchpoint.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">

            {/* Step Cards — Active = lime fill, Idle = white + warm glow */}
            <div className="space-y-4" data-reveal-stagger>
              {[
                {
                  num: '01',
                  title: 'Optical Fundus Ingestion',
                  desc: 'Capture or upload 45° macular fundus photographs with automated quality validation, autofocus verification, and artifact rejection.',
                },
                {
                  num: '02',
                  title: 'Multi-Scale Vessel Extraction & Heatmap',
                  desc: 'Frangi filters isolate capillary architecture to compute vessel caliber and density while Grad-CAM pins exact neural attention hotspots.',
                },
                {
                  num: '03',
                  title: 'Dual-Coded Report & Multilingual Takeaway',
                  desc: 'Generate dual-coded clinical classifications with Web Speech audio counseling and export 18pt+ localized takeaway PDF reports in English, Hindi, or Gujarati.',
                },
              ].map((step, idx) => (
                <div
                  key={idx}
                  onClick={() => setActiveStep(idx)}
                  className={`relative overflow-hidden p-5 rounded-[8px] cursor-pointer text-left transition-all duration-300 ${
                    activeStep === idx
                      ? 'bg-[#E1FA4A] border border-black/5 shadow-[0_12px_35px_rgba(225,250,74,0.4)] scale-[1.02]'
                      : 'bg-white/95 border-[3px] border-white shadow-[0_2px_27px_rgba(0,0,0,0.10)] hover:scale-[1.01]'
                  }`}
                >
                  {/* Warm bottom glow on idle cards (PlanIA radial gradient) */}
                  {activeStep !== idx && (
                    <div className="absolute inset-x-0 bottom-0 h-2/3 pointer-events-none bg-[radial-gradient(94%_69%_at_50%_100%,rgba(225,250,74,0.30)_0%,rgba(225,250,74,0)_75%)]" />
                  )}

                  <div className="relative flex items-start gap-4">
                    <span className={`text-[18px] font-medium ${activeStep === idx ? 'text-black' : 'text-gray-400'}`}>
                      {step.num}
                    </span>
                    <div className="space-y-1">
                      <h3 className={`text-[18px] font-semibold leading-[1.3] ${activeStep === idx ? 'text-black' : 'text-gray-900'}`}>
                        {step.title}
                      </h3>
                      <p className={`text-sm leading-relaxed ${activeStep === idx ? 'text-black/60' : 'text-gray-500'}`}>
                        {step.desc}
                      </p>
                    </div>
                  </div>
                </div>
              ))}

              {/* Auto-loop Controls */}
              <div className="flex items-center gap-3 pt-3 px-1">
                <button
                  onClick={() => setIsLoopPlaying(!isLoopPlaying)}
                  className="flex items-center gap-1.5 h-11 px-4 rounded-full bg-white/15 hover:bg-white/25 border border-white/40 backdrop-blur-md text-white text-xs font-semibold cursor-pointer shadow-sm transition-all"
                >
                  {isLoopPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                  <span>{isLoopPlaying ? 'Pause Simulation' : 'Resume Simulation'}</span>
                </button>
                <button
                  onClick={() => setActiveStep(0)}
                  className="flex items-center justify-center h-11 w-11 rounded-full bg-white/15 hover:bg-white/25 border border-white/40 backdrop-blur-md text-white cursor-pointer shadow-sm transition-all"
                  title="Restart"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Swapping Phone Stack */}
            <div className="relative flex items-center justify-center min-h-[480px]" data-reveal>

              {/* Phone Layer 1: Ingestion */}
              <div
                className={`absolute w-[270px] sm:w-[290px] aspect-[9/18.5] rounded-[44px] bg-white p-2.5 shadow-[0_25px_60px_rgba(0,0,0,0.28)] border-[3px] border-white transition-all duration-500 text-left ${
                  activeStep === 0
                    ? 'z-30 scale-105 rotate-[-3deg] translate-y-0 opacity-100'
                    : 'z-10 scale-95 rotate-[-10deg] -translate-x-12 opacity-30 pointer-events-none'
                }`}
              >
                <div className="w-full h-full rounded-[36px] bg-[#0F172A] p-4 flex flex-col justify-between text-white">
                  <div className="space-y-1 pt-1">
                    <span className="text-[10px] font-bold text-[#1E54B7] bg-sky-500/20 px-2 py-0.5 rounded-full">
                      Step 01 • Optical Ingestion
                    </span>
                    <h4 className="text-xs font-bold text-white">45° Macular Fundus</h4>
                  </div>
                  <div className="aspect-square rounded-2xl overflow-hidden bg-black border border-white/20">
                    <img src={selectedCase.originalImage} alt="Fundus" className="w-full h-full object-cover" />
                  </div>
                  <div className="text-[10px] text-emerald-400 font-mono bg-emerald-950/60 p-2 rounded-xl border border-emerald-500/30 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Autofocus Passed (99.2%) • Clarity Verified</span>
                  </div>
                </div>
              </div>

              {/* Phone Layer 2: Vessel & Heatmap Analysis */}
              <div
                className={`absolute w-[270px] sm:w-[290px] aspect-[9/18.5] rounded-[44px] bg-white p-2.5 shadow-[0_25px_60px_rgba(0,0,0,0.28)] border-[3px] border-white transition-all duration-500 text-left ${
                  activeStep === 1
                    ? 'z-30 scale-105 rotate-[2deg] translate-y-0 opacity-100'
                    : 'z-10 scale-95 rotate-[10deg] translate-x-12 opacity-30 pointer-events-none'
                }`}
              >
                <div className="w-full h-full rounded-[36px] bg-[#0F172A] p-4 flex flex-col justify-between text-white">
                  <div className="space-y-1 pt-1">
                    <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-full">
                      Step 02 • Vessel Density
                    </span>
                    <h4 className="text-xs font-bold text-white">Frangi Mask &amp; Grad-CAM</h4>
                  </div>
                  <div className="aspect-square rounded-2xl overflow-hidden bg-black border border-emerald-500/40">
                    <img src={selectedCase.vesselImage} alt="Vessels" className="w-full h-full object-cover" />
                  </div>
                  <div className="text-[10px] text-gray-300 font-mono bg-slate-900 p-2 rounded-xl border border-slate-800">
                    Density: 14.8% • Caliber Ratio: 0.68
                  </div>
                </div>
              </div>

              {/* Phone Layer 3: Diagnosis & Action Plan */}
              <div
                className={`absolute w-[270px] sm:w-[290px] aspect-[9/18.5] rounded-[44px] bg-white p-2.5 shadow-[0_25px_60px_rgba(0,0,0,0.28)] border-[3px] border-white transition-all duration-500 text-left ${
                  activeStep === 2
                    ? 'z-30 scale-105 rotate-0 translate-y-0 opacity-100'
                    : 'z-10 scale-90 translate-y-10 opacity-25 pointer-events-none'
                }`}
              >
                <div className="w-full h-full rounded-[36px] bg-[#0F172A] p-4 flex flex-col justify-between text-white">
                  <div className="space-y-1 pt-1">
                    <span className="text-[10px] font-bold text-amber-400 bg-amber-500/20 px-2 py-0.5 rounded-full">
                      Step 03 • Action Plan
                    </span>
                    <h4 className="text-xs font-bold text-white">Dual-Coded Classification</h4>
                  </div>
                  <div className="p-3 rounded-2xl bg-black border border-white/20 flex items-center gap-2.5">
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-bold text-sm shrink-0"
                      style={{ backgroundColor: stageMeta.color }}
                    >
                      {stageMeta.icon}
                    </div>
                    <div>
                      <span className="text-xs font-bold text-white block">{stageMeta.name}</span>
                      <span className="text-[10px] text-[#E1FA4A] font-mono font-bold">Conf: {selectedCase.confidence.toFixed(1)}%</span>
                    </div>
                  </div>
                  <div className="text-[10px] text-gray-300 leading-tight bg-slate-900 p-2 rounded-xl border border-slate-800">
                    18pt+ Takeaway PDF &amp; Web Speech Ready
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          7. SOLUTION SHOWCASE — vertical task ticker collage +
             floating voice/waveform chips + three image feature cards
         ════════════════════════════════════════════════════════════════ */}
      <section id="stacking-showcase" className="px-5 sm:px-8 py-16 bg-white/10 backdrop-blur-md border-y border-white/20">
        <div className="max-w-[1080px] mx-auto space-y-11">

          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-7" data-reveal>
            <div className="space-y-5">
              <div className="inline-flex px-3.5 py-2 rounded-[25px] bg-white text-[#1E54B7] text-sm font-medium tracking-[-0.01em] shadow-md opacity-95">
                Experience in Motion • Torne Isso Real
              </div>
              <h2 className="text-[32px] sm:text-[41px] font-semibold tracking-[-0.06em] leading-[1.2] max-w-[629px]">
                See How DrishtiAI Feels in Motion
              </h2>
            </div>
            <p className="text-base font-medium text-white/75 leading-relaxed lg:max-w-[277px]">
              A unified clinical intelligence workspace combining real-time voice counseling, automated task creation, and instant export.
            </p>
          </div>

          {/* Collage: ticker card + visual card with floating chips */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4" data-reveal>

            {/* Vertical Task Ticker Card */}
            <div className="lg:col-span-4 h-[435px] bg-white text-black border-[3px] border-white rounded-[12px] shadow-[0_2px_27px_rgba(0,0,0,0.10)] p-5 flex flex-col overflow-hidden">
              <div className="flex items-center justify-between pb-3">
                <span className="text-[11px] font-bold uppercase tracking-widest text-[#1E54B7]">Automated Actions</span>
                <span className="flex items-center gap-1.5 text-[11px] font-mono text-gray-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> LIVE
                </span>
              </div>

              <div className="ticker-hover relative flex-1 overflow-hidden">
                {/* Edge fades */}
                <div className="absolute inset-x-0 top-0 h-10 bg-gradient-to-b from-white to-transparent z-10 pointer-events-none" />
                <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-white to-transparent z-10 pointer-events-none" />

                <ul className="animate-ticker-y">
                  {[...ACTION_TICKER_ITEMS, ...ACTION_TICKER_ITEMS].map((task, idx) => (
                    <li
                      key={idx}
                      className="mb-3.5 last:mb-0 h-[53px] shrink-0 bg-[#FAFAFA] rounded-[10px] border border-black/5 px-3.5 flex items-center gap-3"
                    >
                      <span
                        className={`w-[18px] h-[18px] rounded-[5px] border-2 flex items-center justify-center shrink-0 ${
                          idx % 3 === 1 ? 'bg-[#E1FA4A] border-transparent' : 'border-gray-300'
                        }`}
                      >
                        {idx % 3 === 1 && <Check className="w-3 h-3 text-black stroke-[3]" />}
                      </span>
                      <span className="text-[14px] font-medium tracking-[-0.02em] text-gray-800 truncate">{task}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Visual Card + Floating Chips */}
            <div className="lg:col-span-8 relative h-[435px] bg-white rounded-[12px] border-[3px] border-white shadow-[0_2px_27px_rgba(0,0,0,0.10)] overflow-hidden">
              <img
                src={PRESET_FUNDUS_CASES[2].heatmapImage}
                alt="Grad-CAM attention heatmap over fundus"
                className="absolute inset-0 w-full h-full object-cover scale-105"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-transparent to-transparent" />

              {/* Caption chip */}
              <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-3">
                <div className="p-3.5 bg-white rounded-[10px] shadow-[0_10px_27px_rgba(0,0,0,0.18)] rotate-[-2deg] max-w-[260px] text-left">
                  <div className="text-[17px] font-bold tracking-[-0.03em] text-slate-900 leading-tight">Grad-CAM Attention Hotspots</div>
                  <div className="text-[11px] text-gray-500 font-mono mt-0.5">Hard exudates • Hemorrhages localized</div>
                </div>
                <div className="hidden sm:inline-flex px-4 py-2 rounded-full border-[1.5px] border-dashed border-[#E1FA4A] bg-[#619FE8]/60 backdrop-blur-md text-white text-[13px] font-semibold rotate-[2deg]">
                  Confidence {PRESET_FUNDUS_CASES[2].confidence.toFixed(1)}%
                </div>
              </div>

              {/* Floating voice waveform chip */}
              <div className="absolute top-5 right-5 p-3.5 bg-white rounded-[10px] shadow-[0_10px_27px_rgba(0,0,0,0.18)] rotate-[2deg] hover:rotate-0 transition-transform text-left">
                <div className="text-[17px] font-bold tracking-[-0.03em] text-slate-900 leading-tight">Speak for Reports</div>
                <div className="flex items-end gap-[3px] h-6 mt-2" aria-hidden="true">
                  {[10, 18, 24, 14, 26, 19, 11, 22, 15, 8, 20, 12].map((h, i) => (
                    <span key={i} className="w-[3px] rounded-full bg-[#E1FA4A]" style={{ height: `${h}px` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Feature Detail Cards (PlanIA image-card pattern with offset imagery) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-reveal-stagger>
            {[
              {
                tag: '01 • Instant Diagnostic Triage',
                tagStyle: 'text-[#1E54B7] bg-sky-100',
                title: 'Gemma-4 Vision Neural Processing',
                desc: 'Processes high-resolution retinal fundus photography in seconds, comparing against tens of thousands of clinically annotated benchmarks to accurately grade DR severity.',
                checks: ['>98.4% AUROC', '45° Aligned'],
                img: PRESET_FUNDUS_CASES[0].originalImage,
                alt: 'Normal fundus photograph',
              },
              {
                tag: '02 • Explainable Feature Maps',
                tagStyle: 'text-emerald-700 bg-emerald-100',
                title: 'Frangi Vessel Density & Grad-CAM',
                desc: 'Eliminate AI black-box hesitation. Clinicians view exact microaneurysm cluster hotspots, hemorrhages, and vascular narrowing quantified with automated metrics.',
                checks: ['Caliber Ratio', 'Attention Heatmap'],
                img: PRESET_FUNDUS_CASES[2].vesselImage,
                alt: 'Frangi vessel segmentation mask',
              },
              {
                tag: '03 • Patient Empowerment & Takeaway',
                tagStyle: 'text-indigo-700 bg-indigo-100',
                title: 'Multilingual Audio & Large-Print PDFs',
                desc: 'Patients leave the clinic with clear, accessible understanding. Real-time translation into English, Hindi, and Gujarati, with Web Speech readouts and 6/12 month risk curves.',
                checks: ['18pt+ Large Print', 'Audio Reader'],
                img: PRESET_FUNDUS_CASES[2].heatmapImage,
                alt: 'Grad-CAM saliency map',
              },
            ].map((card, idx) => (
              <div
                key={idx}
                className="bg-white text-black border-[3px] border-white rounded-[12px] shadow-[0_2px_27px_rgba(0,0,0,0.10)] p-5 space-y-4 hover:-translate-y-1 transition-transform duration-300"
              >
                {/* Image tile with offset placement */}
                <div className="rounded-[10px] bg-[#FAFAFA] border border-black/5 aspect-square overflow-hidden">
                  <img src={card.img} alt={card.alt} className="w-full h-full object-cover translate-y-3 scale-110" />
                </div>

                <span className={`inline-flex px-3 py-1 rounded-[25px] text-[11px] font-mono font-bold uppercase tracking-widest ${card.tagStyle}`}>
                  {card.tag}
                </span>

                <h3 className="text-xl font-medium tracking-[-0.05em] leading-snug">{card.title}</h3>
                <p className="text-sm font-medium text-gray-500 leading-relaxed">{card.desc}</p>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs font-semibold text-gray-700">
                  {card.checks.map((c) => (
                    <span key={c} className="flex items-center gap-1">
                      <Check className="w-4 h-4 text-emerald-600" /> {c}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          8. COMPARISON — PlanIA-style 3-column positioning card
         ════════════════════════════════════════════════════════════════ */}
      <section className="px-5 sm:px-8 py-16">
        <div className="max-w-[1080px] mx-auto space-y-11">

          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-7" data-reveal>
            <div className="space-y-5">
              <div className="inline-flex px-3.5 py-2 rounded-[25px] bg-white text-[#1E54B7] text-sm font-medium tracking-[-0.01em] shadow-md opacity-95">
                Cameras / Generic AI / DrishtiAI
              </div>
              <h2 className="text-[32px] sm:text-[41px] font-semibold tracking-[-0.06em] leading-[1.2] max-w-[629px]">
                More Than a Score.
              </h2>
            </div>
            <p className="text-base font-medium text-white/75 leading-relaxed lg:max-w-[277px]">
              Screening alone changes nothing — DrishtiAI closes the loop from fundus image to patient action.
            </p>
          </div>

          <div className="bg-white text-black border-[3px] border-white rounded-[12px] shadow-[0_2px_27px_rgba(0,0,0,0.10)] p-5 grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-black/10" data-reveal>
            <div className="p-5 sm:p-6">
              <div className="text-sm font-medium tracking-[-0.01em] text-black/50 opacity-80">Fundus Cameras</div>
              <h3 className="mt-3 text-[22px] font-medium tracking-[-0.05em] leading-snug">They capture retinal images.</h3>
            </div>

            <div className="p-5 sm:p-6">
              <div className="text-sm font-medium tracking-[-0.01em] text-black/50 opacity-80">Generic AI Tools</div>
              <h3 className="mt-3 text-[22px] font-medium tracking-[-0.05em] leading-snug">They output opaque, unexplainable scores.</h3>
            </div>

            <div className="p-5 sm:p-6">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-[#E1FA4A] flex items-center justify-center shrink-0">
                  <Eye className="w-3.5 h-3.5 text-black stroke-[2.5]" />
                </div>
                <span className="text-lg font-semibold tracking-[-0.03em]">DrishtiAI</span>
              </div>
              <h3 className="mt-3 text-[22px] font-medium tracking-[-0.05em] leading-snug">
                Connects screening <span className="text-[#1E54B7]">to care.</span>
              </h3>
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          9. FAQ — accordion on soft white cards
         ════════════════════════════════════════════════════════════════ */}
      <section id="accessibility" className="px-5 sm:px-8 py-16 bg-white/10 backdrop-blur-md border-y border-white/20">
        <div className="max-w-[820px] mx-auto space-y-10">

          <div className="flex flex-col items-center text-center space-y-5" data-reveal>
            <div className="inline-flex px-3.5 py-2 rounded-[25px] bg-white text-[#1E54B7] text-sm font-medium tracking-[-0.01em] shadow-md opacity-95">
              Frequently Asked Questions
            </div>
            <h2 className="text-[32px] sm:text-[41px] font-semibold tracking-[-0.06em] leading-[1.2]">
              Questions About Clinical AI?
            </h2>
          </div>

          <div className="space-y-4" data-reveal-stagger>
            {faqs.map((faq, idx) => (
              <div
                key={idx}
                className="px-6 py-5 bg-white text-black border-[3px] border-white rounded-[12px] shadow-[0_2px_27px_rgba(0,0,0,0.10)] text-left transition-all"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  className="w-full flex items-center justify-between gap-4 text-left text-lg font-medium tracking-[-0.03em] text-black cursor-pointer"
                >
                  <span>{faq.q}</span>
                  <ChevronDown
                    className={`w-5 h-5 text-gray-400 shrink-0 transition-transform duration-300 ${
                      openFaq === idx ? 'rotate-180 text-[#1E54B7]' : ''
                    }`}
                  />
                </button>
                {openFaq === idx && (
                  <p className="pt-3 text-sm font-medium text-gray-500 leading-relaxed animate-fadeIn">
                    {faq.a}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          9. FINAL CTA + SLIM LEGAL FOOTER (full-width watermark)
         ════════════════════════════════════════════════════════════════ */}
      <footer className="relative px-5 sm:px-8 pt-24 pb-10 overflow-hidden text-center">

        {/* CTA Content */}
        <div className="relative z-10 max-w-[782px] mx-auto space-y-7" data-reveal>
          <div className="inline-flex items-center gap-2 px-3.5 py-2 rounded-[25px] bg-white/15 border border-white/30 backdrop-blur-md text-sm font-medium tracking-[-0.01em] opacity-90">
            <Sparkles className="w-4 h-4 text-[#E1FA4A]" />
            <span>Ready for Clinical Deployment</span>
          </div>

          <h2 className="text-[34px] sm:text-[51px] font-semibold tracking-[-0.05em] leading-[1.08]">
            Empower Your Clinic with Autonomous Retinal AI
          </h2>

          <p className="text-base font-medium text-white/80 leading-relaxed max-w-xl mx-auto">
            Launch the live clinical workspace directly in your browser or copy the permanent web link for your medical team.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-3">
            <button
              onClick={handleLaunchDashboard}
              className="flex items-center gap-2.5 h-[49px] px-8 rounded-[9px] bg-[#E1FA4A] hover:bg-[#d6f236] text-black font-bold text-sm uppercase tracking-wider shadow-[0_10px_30px_rgba(225,250,74,0.35)] hover:scale-[1.03] transition-all cursor-pointer"
            >
              <Microscope className="w-4 h-4" />
              <span>Launch Clinical Workspace</span>
              <ArrowRight className="w-4 h-4 stroke-[3]" />
            </button>

            <button
              onClick={handleCopyLink}
              className="flex items-center gap-2 h-[49px] px-6 rounded-[9px] bg-white/15 hover:bg-white/25 backdrop-blur-md border border-white/40 text-white font-semibold text-sm transition-all hover:scale-[1.03] cursor-pointer"
            >
              {copiedLink ? (
                <>
                  <Check className="w-4 h-4 text-[#E1FA4A]" />
                  <span>Link Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Copy Permanent Link</span>
                </>
              )}
            </button>

            {/* Direct APK Downloads in Footer */}
            <a
              href="/DrishtiAI.apk"
              download="DrishtiAI.apk"
              onClick={() => handleDownloadApk('Google Play')}
              aria-label="Download DrishtiAI Android APK (Google Play)"
              className="flex items-center gap-2.5 h-[49px] px-4 rounded-[9px] bg-white hover:bg-gray-100 text-black shadow-md hover:scale-[1.03] transition-all cursor-pointer no-underline text-xs font-semibold"
            >
              <Play className="w-4 h-4 fill-black text-black shrink-0" />
              <span className="flex flex-col items-start leading-none">
                <span className="text-[8px] font-medium uppercase text-black/60">Get it on</span>
                <span className="text-[13px] font-semibold tracking-tight mt-0.5">Google Play</span>
              </span>
            </a>

            <a
              href="/DrishtiAI.apk"
              download="DrishtiAI.apk"
              onClick={() => handleDownloadApk('App Store')}
              aria-label="Download DrishtiAI Mobile App (App Store)"
              className="flex items-center gap-2.5 h-[49px] px-4 rounded-[9px] bg-black hover:bg-gray-900 border border-white/20 text-white shadow-md hover:scale-[1.03] transition-all cursor-pointer no-underline text-xs font-semibold"
            >
              <AppleIcon className="w-4 h-4 shrink-0" />
              <span className="flex flex-col items-start leading-none">
                <span className="text-[8px] font-medium uppercase text-white/70">Download on the</span>
                <span className="text-[13px] font-semibold tracking-tight mt-0.5">App Store</span>
              </span>
            </a>
          </div>
        </div>

        {/* Full Watermark — fully visible, never clipped */}
        <div
          aria-hidden="true"
          className="relative z-10 mt-14 flex justify-center pointer-events-none select-none"
        >
          <span className="text-white/[0.15] text-[14vw] leading-[0.95] font-semibold tracking-[-0.05em] whitespace-nowrap">
            DrishtiAI
          </span>
        </div>

        {/* Slim Legal Bar */}
        <div className="relative z-10 mt-8 max-w-[1117px] mx-auto border-t border-white/20 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-medium text-white/65">
            <Eye className="w-4 h-4 text-white/80" />
            <span>DrishtiAI Clinical Intelligence Suite © 2026</span>
          </div>

          <div className="flex items-center gap-6 text-[13px] font-medium text-white/65">
            <button onClick={handleLaunchDashboard} className="hover:text-white transition-colors cursor-pointer">Dashboard</button>
            <button onClick={() => { setActiveView('new-scan'); }} className="hover:text-white transition-colors cursor-pointer">New Scan</button>
            <button onClick={() => { setActiveView('batch-screening'); }} className="hover:text-white transition-colors cursor-pointer">Batch Queue</button>
            <button onClick={() => { setActiveView('patients'); }} className="hover:text-white transition-colors cursor-pointer">Patients</button>
          </div>

          <div className="text-[11px] font-mono text-white/45">
            WCAG 2.2 AAA &amp; Okabe-Ito Compliant
          </div>
        </div>
      </footer>

      {/* Download Feedback Toast */}
      {downloadToast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-full bg-slate-900/95 text-white border border-emerald-500/40 shadow-[0_10px_40px_rgba(0,0,0,0.5)] backdrop-blur-xl animate-fade-in text-xs sm:text-sm font-semibold"
        >
          <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
            <Download className="w-3.5 h-3.5 stroke-[2.5]" />
          </div>
          <span>{downloadToast}</span>
        </div>
      )}
    </div>
  );
};
