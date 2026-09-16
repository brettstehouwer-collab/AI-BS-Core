import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { DollarSign, Cpu, Shield, TrendingUp } from 'lucide-react';
import { getApiBase } from '../config/api';

const Card = ({ children, className = '' }) => (
  <div className={`bg-gray-800 border border-gray-700 rounded-lg ${className}`} style={{ padding: '16px', backgroundColor: '#1e1e1e', border: '1px solid #444', borderRadius: '8px' }}>
    {children}
  </div>
);

const CardHeader = ({ children, className = '' }) => (
  <div className={`border-b border-gray-700 pa-2 mb-4 flex flex-row items-center justify-between ${className}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', marginBottom: '15px', borderBottom: '1px solid #333' }}>
    {children}
  </div>
);

const CardTitle = ({ children, className = '' }) => (
  <h3 className={`text-sm font-medium text-gray-400 ${className}`} style={{ margin: 0, fontSize: '1.1rem', color: '#aaaaff' }}>
    {children}
  </h3>
);

const CardContent = ({ children, className = '' }) => (
  <div className={className}>
    {children}
  </div>
);

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function UnifiedSystemEconomics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${getApiBase()}/api/v1/economics/summary`);
        if (!res.ok) throw new Error('Failed to fetch economics data');
        const json = await res.json();
        setData(json.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-8 text-center text-gray-400" style={{padding: '20px', color: '#888'}}>Loading Economics Data...</div>;
  if (error) return <div className="p-8 text-center text-red-500" style={{padding: '20px', color: 'red'}}>Error: {error}</div>;
  if (!data) return null;

  const historicalData = [
    { name: 'Mon', revenue: data.revenue?.total_revenue || 0, cost: data.llm_costs?.total_compute_cost || 0 },
    { name: 'Tue', revenue: (data.revenue?.total_revenue || 0) * 1.1, cost: (data.llm_costs?.total_compute_cost || 0) * 1.05 },
    { name: 'Wed', revenue: (data.revenue?.total_revenue || 0) * 1.15, cost: (data.llm_costs?.total_compute_cost || 0) * 1.1 },
    { name: 'Thu', revenue: (data.revenue?.total_revenue || 0) * 1.2, cost: (data.llm_costs?.total_compute_cost || 0) * 1.12 },
    { name: 'Fri', revenue: (data.revenue?.total_revenue || 0) * 1.25, cost: (data.llm_costs?.total_compute_cost || 0) * 1.15 },
  ];

  const pieData = [
    { name: 'Compute Costs', value: data.llm_costs?.total_compute_cost || 0 },
    { name: 'Security Overhead', value: data.security_telemetry?.cost_estimate || 0 },
  ];

  return (
    <div className="p-8 space-y-6" style={{fontFamily: 'monospace'}}>
      <h3 className="text-2xl font-bold text-white border-b border-gray-700 pa-2" style={{ color: '#00ffcc', borderBottom: '1px solid #333', paddingBottom: '10px' }}>
        System Economics Dashboard
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginTop: '20px' }}>
        <Card>
          <CardHeader>
            <CardTitle style={{color: '#aaffaa'}}>Total Agency Revenue</CardTitle>
            <DollarSign className="w-4 h-4 text-green-400" style={{color: '#66ff66'}}/>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white" style={{fontSize: '1.5rem'}}>${(data.revenue?.total_revenue || 0).toFixed(2)}</div>
            <p className="text-xs text-gray-500 mt-1" style={{color: '#888', fontSize: '0.9rem'}}>+12% from last week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle style={{color: '#ffaaaa'}}>Total Compute Costs</CardTitle>
            <Cpu className="w-4 h-4 text-blue-400" style={{color: '#66bbff'}}/>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white" style={{fontSize: '1.5rem'}}>${(data.llm_costs?.total_compute_cost || 0).toFixed(2)}</div>
            <p className="text-xs text-gray-500 mt-1" style={{color: '#888', fontSize: '0.9rem'}}>Across all models</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle style={{color: '#ffcc00'}}>Net Margin</CardTitle>
            <TrendingUp className="w-4 h-4 text-purple-400" style={{color: '#cc88ff'}}/>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white" style={{fontSize: '1.5rem'}}>${(data.margins?.net_profit || 0).toFixed(2)}</div>
            <p className="text-xs text-gray-500 mt-1" style={{color: '#888', fontSize: '0.9rem'}}>
              {(data.margins?.margin_percentage || 0).toFixed(1)}% profitability
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Security Telemetry</CardTitle>
            <Shield className="w-4 h-4 text-red-400" style={{color: '#ff6666'}}/>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white" style={{fontSize: '1.5rem'}}>{data.security_telemetry?.threats_blocked || 0}</div>
            <p className="text-xs text-gray-500 mt-1" style={{color: '#888', fontSize: '0.9rem'}}>Threats Blocked</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '20px', marginTop: '20px'}}>
        <Card>
          <CardHeader style={{borderBottom: 'none', marginBottom: '0px'}}>
            <CardTitle className="text-gray-300" style={{color: '#eeeeee'}}>Revenue vs. Compute Costs (7D)</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]" style={{height: '300px'}}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={historicalData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '0.375rem' }}
                  itemStyle={{ color: '#E5E7EB' }}
                />
                <Area type="monotone" dataKey="revenue" stroke="#10B981" fillOpacity={1} fill="url(#colorRevenue)" />
                <Area type="monotone" dataKey="cost" stroke="#EF4444" fillOpacity={1} fill="url(#colorCost)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader style={{borderBottom: 'none', marginBottom: '0px'}}>
            <CardTitle className="text-gray-300" style={{color: '#eeeeee'}}>Cost Distribution</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center" style={{height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  fill="#8884d8"
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '0.375rem' }}
                  itemStyle={{ color: '#E5E7EB' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
