import os

content = """import React, { useState } from 'react';
import { 
  Layers, Rocket, ShieldAlert, Activity, Cpu, Code, Database, Globe, Home, Scale, 
  ShoppingCart, TrendingUp, BookOpen, Factory, Sprout, Film,
  Users, Headset, Truck, Shield, HardHat, Car, Plane, Gamepad, Heart, Newspaper,
  Calendar, Landmark, Zap, Signal, Hammer, Pill, Scissors, Coffee,
  Mic, Video, Camera, PlayCircle, PenTool, Search, MessageSquare, Speaker, Trophy,
  Leaf, Building2, Thermometer, Droplets, Sparkles, Bug, Trash2
} from 'lucide-react';

import RealEstateSuiteTab from './industry_suites/RealEstateSuiteTab.jsx';
import LegalSuiteTab from './industry_suites/LegalSuiteTab.jsx';
import MedicalSuiteTab from './industry_suites/MedicalSuiteTab.jsx';
import RetailSuiteTab from './industry_suites/RetailSuiteTab.jsx';
import FinanceSuiteTab from './industry_suites/FinanceSuiteTab.jsx';
import EducationSuiteTab from './industry_suites/EducationSuiteTab.jsx';
import ManufacturingSuiteTab from './industry_suites/ManufacturingSuiteTab.jsx';
import AgricultureSuiteTab from './industry_suites/AgricultureSuiteTab.jsx';
import EntertainmentSuiteTab from './industry_suites/EntertainmentSuiteTab.jsx';
import CybersecuritySuiteTab from './industry_suites/CybersecuritySuiteTab.jsx';

import HRSuiteTab from './industry_suites/HRSuiteTab.jsx';
import CustomerSupportSuiteTab from './industry_suites/CustomerSupportSuiteTab.jsx';
import LogisticsSuiteTab from './industry_suites/LogisticsSuiteTab.jsx';
import InsuranceSuiteTab from './industry_suites/InsuranceSuiteTab.jsx';
import ConstructionSuiteTab from './industry_suites/ConstructionSuiteTab.jsx';
import AutomotiveSuiteTab from './industry_suites/AutomotiveSuiteTab.jsx';
import TravelSuiteTab from './industry_suites/TravelSuiteTab.jsx';
import GamingSuiteTab from './industry_suites/GamingSuiteTab.jsx';
import NGOSuiteTab from './industry_suites/NGOSuiteTab.jsx';
import JournalismSuiteTab from './industry_suites/JournalismSuiteTab.jsx';

import WellnessSuiteTab from './industry_suites/WellnessSuiteTab.jsx';
import EventsSuiteTab from './industry_suites/EventsSuiteTab.jsx';
import GovSuiteTab from './industry_suites/GovSuiteTab.jsx';
import EnergySuiteTab from './industry_suites/EnergySuiteTab.jsx';
import TelecomSuiteTab from './industry_suites/TelecomSuiteTab.jsx';
import MiningSuiteTab from './industry_suites/MiningSuiteTab.jsx';
import AerospaceSuiteTab from './industry_suites/AerospaceSuiteTab.jsx';
import PharmaSuiteTab from './industry_suites/PharmaSuiteTab.jsx';
import FashionSuiteTab from './industry_suites/FashionSuiteTab.jsx';
import FoodBevSuiteTab from './industry_suites/FoodBevSuiteTab.jsx';

import AudioSuiteTab from './industry_suites/AudioSuiteTab.jsx';
import VideoSuiteTab from './industry_suites/VideoSuiteTab.jsx';
import PhotographySuiteTab from './industry_suites/PhotographySuiteTab.jsx';
import AnimationSuiteTab from './industry_suites/AnimationSuiteTab.jsx';
import TranslationSuiteTab from './industry_suites/TranslationSuiteTab.jsx';
import WritingSuiteTab from './industry_suites/WritingSuiteTab.jsx';
import SEOSuiteTab from './industry_suites/SEOSuiteTab.jsx';
import SocialMediaSuiteTab from './industry_suites/SocialMediaSuiteTab.jsx';
import PRSuiteTab from './industry_suites/PRSuiteTab.jsx';
import SportsSuiteTab from './industry_suites/SportsSuiteTab.jsx';

import LandscapingSuiteTab from './industry_suites/LandscapingSuiteTab.jsx';
import RealEstateDevSuiteTab from './industry_suites/RealEstateDevSuiteTab.jsx';
import HVACSuiteTab from './industry_suites/HVACSuiteTab.jsx';
import PlumbingSuiteTab from './industry_suites/PlumbingSuiteTab.jsx';
import ElectricalSuiteTab from './industry_suites/ElectricalSuiteTab.jsx';
import CleaningSuiteTab from './industry_suites/CleaningSuiteTab.jsx';
import SecuritySuiteTab from './industry_suites/SecuritySuiteTab.jsx';
import PestControlSuiteTab from './industry_suites/PestControlSuiteTab.jsx';
import WasteMgmtSuiteTab from './industry_suites/WasteMgmtSuiteTab.jsx';
import DeliverySuiteTab from './industry_suites/DeliverySuiteTab.jsx';

export default function EnterpriseIndustryHubTab({ backendUrl }) {
  const [activeCategory, setActiveCategory] = useState('all');
  const [activeModule, setActiveModule] = useState(null);

  const categories = [
    { id: 'all', label: 'All Industries' },
    { id: 'business', label: 'Business & Finance' },
    { id: 'science', label: 'Deep Tech & Science' },
    { id: 'infrastructure', label: 'Infrastructure & IT' },
    { id: 'creative', label: 'Creative & Media' },
    { id: 'public', label: 'Public Sector & Utilities' },
    { id: 'marketing', label: 'Marketing & Comms' },
    { id: 'trades', label: 'Trades & Field Services' }
  ];

  const modules = [
    // Phase 2
    { id: 'real_estate', title: 'Real Estate & Architecture', icon: Home, Component: RealEstateSuiteTab, category: 'business' },
    { id: 'legal', title: 'Legal & Compliance', icon: Scale, Component: LegalSuiteTab, category: 'business' },
    { id: 'medical', title: 'Medical & Bioinformatics', icon: Activity, Component: MedicalSuiteTab, category: 'science' },
    { id: 'retail', title: 'E-commerce & Retail', icon: ShoppingCart, Component: RetailSuiteTab, category: 'business' },
    { id: 'finance', title: 'Financial & Hedge Fund', icon: TrendingUp, Component: FinanceSuiteTab, category: 'business' },
    { id: 'education', title: 'Education & EdTech', icon: BookOpen, Component: EducationSuiteTab, category: 'public' },
    { id: 'manufacturing', title: 'Manufacturing & Supply Chain', icon: Factory, Component: ManufacturingSuiteTab, category: 'infrastructure' },
    { id: 'agriculture', title: 'Agriculture & Farming', icon: Sprout, Component: AgricultureSuiteTab, category: 'science' },
    { id: 'entertainment', title: 'Entertainment & Media', icon: Film, Component: EntertainmentSuiteTab, category: 'creative' },
    { id: 'cybersecurity', title: 'Cybersecurity & InfoSec', icon: ShieldAlert, Component: CybersecuritySuiteTab, category: 'infrastructure' },
    
    // Phase 3
    { id: 'hr', title: 'Human Resources & Recruiting', icon: Users, Component: HRSuiteTab, category: 'business' },
    { id: 'customer_support', title: 'Customer Support & Call Centers', icon: Headset, Component: CustomerSupportSuiteTab, category: 'business' },
    { id: 'logistics', title: 'Logistics & Shipping', icon: Truck, Component: LogisticsSuiteTab, category: 'infrastructure' },
    { id: 'insurance', title: 'Insurance & Claims', icon: Shield, Component: InsuranceSuiteTab, category: 'business' },
    { id: 'construction', title: 'Construction & Engineering', icon: HardHat, Component: ConstructionSuiteTab, category: 'infrastructure' },
    { id: 'automotive', title: 'Automotive & Dealership', icon: Car, Component: AutomotiveSuiteTab, category: 'business' },
    { id: 'travel', title: 'Travel & Tourism', icon: Plane, Component: TravelSuiteTab, category: 'creative' },
    { id: 'gaming', title: 'Gaming & Esports', icon: Gamepad, Component: GamingSuiteTab, category: 'creative' },
    { id: 'ngo', title: 'Non-Profit & NGO', icon: Heart, Component: NGOSuiteTab, category: 'public' },
    { id: 'journalism', title: 'Journalism & Publishing', icon: Newspaper, Component: JournalismSuiteTab, category: 'creative' },

    // Phase 4
    { id: 'wellness', title: 'Wellness & Fitness', icon: Activity, Component: WellnessSuiteTab, category: 'science' },
    { id: 'events', title: 'Events & Ticketing', icon: Calendar, Component: EventsSuiteTab, category: 'creative' },
    { id: 'gov', title: 'Government & Public Sector', icon: Landmark, Component: GovSuiteTab, category: 'public' },
    { id: 'energy', title: 'Energy & Utilities', icon: Zap, Component: EnergySuiteTab, category: 'public' },
    { id: 'telecom', title: 'Telecommunications', icon: Signal, Component: TelecomSuiteTab, category: 'infrastructure' },
    { id: 'mining', title: 'Mining & Metals', icon: Hammer, Component: MiningSuiteTab, category: 'infrastructure' },
    { id: 'aerospace', title: 'Aerospace & Defense', icon: Rocket, Component: AerospaceSuiteTab, category: 'science' },
    { id: 'pharma', title: 'Pharmaceuticals', icon: Pill, Component: PharmaSuiteTab, category: 'science' },
    { id: 'fashion', title: 'Fashion & Apparel', icon: Scissors, Component: FashionSuiteTab, category: 'creative' },
    { id: 'foodbev', title: 'Food & Beverage', icon: Coffee, Component: FoodBevSuiteTab, category: 'business' },

    // Phase 5
    { id: 'audio', title: 'Audio & Podcasting', icon: Mic, Component: AudioSuiteTab, category: 'creative' },
    { id: 'video', title: 'Video & Broadcasting', icon: Video, Component: VideoSuiteTab, category: 'creative' },
    { id: 'photography', title: 'Photography & Imaging', icon: Camera, Component: PhotographySuiteTab, category: 'creative' },
    { id: 'animation', title: 'Animation & VFX', icon: PlayCircle, Component: AnimationSuiteTab, category: 'creative' },
    { id: 'translation', title: 'Translation & Localization', icon: Globe, Component: TranslationSuiteTab, category: 'business' },
    { id: 'writing', title: 'Creative Writing & Publishing', icon: PenTool, Component: WritingSuiteTab, category: 'creative' },
    { id: 'seo', title: 'SEO & Digital Marketing', icon: Search, Component: SEOSuiteTab, category: 'marketing' },
    { id: 'socialmedia', title: 'Social Media & Influencer', icon: MessageSquare, Component: SocialMediaSuiteTab, category: 'marketing' },
    { id: 'pr', title: 'PR & Communications', icon: Speaker, Component: PRSuiteTab, category: 'marketing' },
    { id: 'sports', title: 'Sports & Athletics', icon: Trophy, Component: SportsSuiteTab, category: 'business' },

    // Phase 6
    { id: 'landscaping', title: 'Landscaping & Grounds', icon: Leaf, Component: LandscapingSuiteTab, category: 'trades' },
    { id: 'realestatedev', title: 'Real Estate Development', icon: Home, Component: RealEstateDevSuiteTab, category: 'trades' },
    { id: 'hvac', title: 'HVAC & Climate Control', icon: Thermometer, Component: HVACSuiteTab, category: 'trades' },
    { id: 'plumbing', title: 'Plumbing & Water Systems', icon: Droplets, Component: PlumbingSuiteTab, category: 'trades' },
    { id: 'electrical', title: 'Electrical & Grid', icon: Zap, Component: ElectricalSuiteTab, category: 'trades' },
    { id: 'cleaning', title: 'Cleaning & Facility', icon: Sparkles, Component: CleaningSuiteTab, category: 'trades' },
    { id: 'security', title: 'Security & Surveillance', icon: ShieldAlert, Component: SecuritySuiteTab, category: 'infrastructure' },
    { id: 'pestcontrol', title: 'Pest Control', icon: Bug, Component: PestControlSuiteTab, category: 'trades' },
    { id: 'wastemgmt', title: 'Waste Management', icon: Trash2, Component: WasteMgmtSuiteTab, category: 'trades' },
    { id: 'delivery', title: 'Delivery & Courier', icon: Truck, Component: DeliverySuiteTab, category: 'infrastructure' }
  ];

  if (activeModule) {
    const ActiveComponent = activeModule.Component;
    return (
      <div className="h-full flex flex-col bg-slate-900">
        <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
          <button 
            onClick={() => setActiveModule(null)}
            className="text-slate-300 hover:text-white flex items-center gap-2"
          >
            ← Back to Industry Grid
          </button>
        </div>
        <div className="flex-1 overflow-hidden">
          <ActiveComponent backendUrl={backendUrl} />
        </div>
      </div>
    );
  }

  const filteredModules = activeCategory === 'all' 
    ? modules 
    : modules.filter(m => m.category === activeCategory);

  return (
    <div className="h-full flex flex-col bg-slate-900 text-slate-200">
      <div className="flex-none p-6 border-b border-slate-700/50 bg-slate-800/30">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Globe className="w-6 h-6 text-indigo-400" />
              Enterprise Industry OS
            </h1>
            <p className="text-slate-400 mt-1 max-w-2xl">
              Massive 70-Vertical AI Suite featuring advanced RAG, ComfyUI generation, Unreal Engine pixel streaming, and Deep Tech integrations.
            </p>
          </div>
          <div className="flex gap-2">
            <span className="px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-xs font-mono font-medium border border-indigo-500/30">
              PHASE 6 (50/70)
            </span>
            <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 rounded-full text-xs font-mono font-medium border border-emerald-500/30">
              E:\\AI_BS_Resources
            </span>
          </div>
        </div>

        <div className="mt-6 flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-700">
          {categories.map(c => (
            <button
              key={c.id}
              onClick={() => setActiveCategory(c.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                activeCategory === c.id 
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/20' 
                  : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-700">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4">
          {filteredModules.map(mod => (
            <div 
              key={mod.id} 
              onClick={() => setActiveModule(mod)}
              className="bg-slate-800 border border-slate-700 hover:border-indigo-500 p-6 rounded-xl cursor-pointer transition-all hover:-translate-y-1 hover:shadow-xl shadow-black/50"
            >
              <mod.icon className="w-8 h-8 text-indigo-400 mb-4" />
              <h3 className="text-lg font-bold text-white mb-2">{mod.title}</h3>
              <p className="text-slate-400 text-sm">Click to launch {mod.title} modules & dashboards.</p>
            </div>
          ))}
          {/* Mock placeholders for the remaining 20 */}
          {Array.from({length: 20}).map((_, i) => (
            <div key={`pending-${i}`} className="bg-slate-800/50 border border-slate-700/50 p-6 rounded-xl opacity-50 flex flex-col items-center justify-center text-center">
              <Layers className="w-8 h-8 text-slate-500 mb-2" />
              <p className="text-sm font-bold text-slate-400">Module {i + 51}</p>
              <p className="text-xs text-slate-500">Pending Execution Phase</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
"""

with open("C:/AI-BS/frontend/components/EnterpriseIndustryHubTab.jsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated EnterpriseIndustryHubTab with Phase 6 modules.")
