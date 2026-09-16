import React, { useState, useEffect } from 'react';
import { collection, onSnapshot, query, orderBy } from 'firebase/firestore';
import { db } from '../firebase';
import { Users, Clock, Loader2 } from 'lucide-react';

export default function ClientsTab() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const q = query(collection(db, 'clients'), orderBy('createdAt', 'desc'));
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const clientList = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      setClients(clientList);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          <p className="text-slate-400">Loading active client directory...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 overflow-y-auto bg-slate-900 text-slate-100">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Users className="w-8 h-8 text-blue-400" />
            <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
              Client Directory
            </h2>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-400 bg-slate-800 px-4 py-2 rounded-full border border-slate-700">
            <Clock className="w-4 h-4" /> Live Sync Active
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/50 text-slate-400 border-b border-slate-700">
                  <th className="p-4 font-medium">Company</th>
                  <th className="p-4 font-medium">Contact</th>
                  <th className="p-4 font-medium">Tech Stack</th>
                  <th className="p-4 font-medium">Deployment</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {clients.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="p-8 text-center text-slate-500">
                      No clients found. Use the Onboarding Portal to add a client.
                    </td>
                  </tr>
                ) : (
                  clients.map(client => (
                    <tr key={client.id} className="hover:bg-slate-700/30 transition-colors">
                      <td className="p-4 font-medium text-blue-400">{client.companyName}</td>
                      <td className="p-4">{client.clientName}</td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-700 text-slate-300">
                          {client.techStack}
                        </span>
                      </td>
                      <td className="p-4 text-slate-400">{client.deploymentPreference}</td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-900/50 text-emerald-400 border border-emerald-800/50">
                          {client.status}
                        </span>
                      </td>
                      <td className="p-4 text-sm text-slate-400">
                        {new Date(client.createdAt).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
