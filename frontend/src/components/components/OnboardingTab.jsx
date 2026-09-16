import React, { useState } from 'react';
import { collection, addDoc } from 'firebase/firestore';
import { db } from '../firebase';
import { FileText, Send, User, Briefcase, Target, Database } from 'lucide-react';

export default function OnboardingTab() {
  const [formData, setFormData] = useState({
    clientName: '',
    companyName: '',
    primaryObjective: '',
    techStack: 'Python/React',
    deploymentPreference: 'Firebase Hosting'
  });
  const [status, setStatus] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatus('Writing to database...');

    try {
      await addDoc(collection(db, 'clients'), {
        clientName: formData.clientName,
        companyName: formData.companyName,
        primaryObjective: formData.primaryObjective,
        techStack: formData.techStack,
        deploymentPreference: formData.deploymentPreference,
        status: 'Active Pipeline',
        createdAt: new Date().toISOString()
      });

      setStatus('Success: Client added to database and routed to Clients Tab.');
      setFormData({
        clientName: '',
        companyName: '',
        primaryObjective: '',
        techStack: 'Python/React',
        deploymentPreference: 'Firebase Hosting'
      });
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 p-6 overflow-y-auto bg-slate-900 text-slate-100">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-3 mb-8">
          <FileText className="w-8 h-8 text-blue-400" />
          <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
            Client Onboarding Portal
          </h2>
        </div>

        <div className="bg-slate-800 rounded-xl p-8 border border-slate-700 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                  <User className="w-4 h-4 text-blue-400" /> Client Name
                </label>
                <input 
                  type="text" 
                  name="clientName" 
                  value={formData.clientName} 
                  onChange={handleChange} 
                  required 
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  placeholder="John Doe"
                />
              </div>

              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                  <Briefcase className="w-4 h-4 text-blue-400" /> Company Name
                </label>
                <input 
                  type="text" 
                  name="companyName" 
                  value={formData.companyName} 
                  onChange={handleChange} 
                  required 
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  placeholder="Acme Corp"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                <Target className="w-4 h-4 text-blue-400" /> Primary Objective
              </label>
              <textarea 
                name="primaryObjective" 
                value={formData.primaryObjective} 
                onChange={handleChange} 
                required 
                rows="4"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors resize-none"
                placeholder="Describe the main goal of the project..."
              />
            </div>

            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                <Database className="w-4 h-4 text-blue-400" /> Tech Stack
              </label>
              <select 
                name="techStack" 
                value={formData.techStack} 
                onChange={handleChange}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
              >
                <option value="Python/React">Python / React / Go</option>
                <option value="Node/Firebase">Node.js / Firebase Hosting</option>
                <option value="Custom">Custom Infrastructure</option>
              </select>
            </div>

            <div className="pt-4 flex items-center justify-between">
              <button 
                type="submit" 
                disabled={isSubmitting}
                className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-6 py-3 rounded-lg font-medium transition-all transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-5 h-5" />
                {isSubmitting ? 'Transmitting...' : 'Submit & Route to Clients Tab'}
              </button>

              {status && (
                <div className={`px-4 py-2 rounded-lg text-sm font-medium animate-pulse ${status.includes('Error') ? 'bg-red-900/50 text-red-400 border border-red-800' : 'bg-emerald-900/50 text-emerald-400 border border-emerald-800'}`}>
                  {status}
                </div>
              )}
            </div>

          </form>
        </div>
      </div>
    </div>
  );
}
