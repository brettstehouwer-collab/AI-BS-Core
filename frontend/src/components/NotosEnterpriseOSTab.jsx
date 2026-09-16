import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, Calendar, Users, MessageSquare, Utensils, Award, 
  MapPin, CheckCircle, Clock, AlertTriangle, ShieldCheck, 
  FileText, Download, Search, Filter, Wine, Building2, Flame,
  DollarSign, ChevronRight, RefreshCw, Send, PlusCircle, Check,
  Play, Pause, FastForward, Rewind, Presentation, Layers, ArrowRight
} from 'lucide-react';

export default function NotosEnterpriseOSTab({ backendUrl }) {
  const baseUrl = backendUrl || import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

  // 🏛️ Location Switcher: 'GR' (Grand Rapids 28th St) vs 'GH' (Grand Haven at the Bil-Mar)
  const [activeLocation, setActiveLocation] = useState(() => {
    return localStorage.getItem('aibs_notos_active_location') || 'GR';
  });

  // 🧭 Active Operational Subsystem
  const [activeSubsystem, setActiveSubsystem] = useState('overview');

  // 🎬 ─── Executive Presentation Engine State ───
  const [isPresentationMode, setIsPresentationMode] = useState(false);
  const [presentationStep, setPresentationStep] = useState(0);
  const [isAutoTour, setIsAutoTour] = useState(false);

  // ─── 1. Joanne's 12,000-Bottle Cellar Master State ───
  const [cellarSearch, setCellarSearch] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('ALL');
  const [cellarInventory, setCellarInventory] = useState([
    { id: 'W-01', name: '2016 Tenuta San Guido Sassicaia', region: 'Tuscany (Bolgheri)', vintage: 2016, varietal: 'Cabernet Sauvignon/Cab Franc', bin: 'Vault North • Bin A-14-3', bottles: 18, wholesale: 165.00, menuPrice: 385.00, pairing: 'Prime Dry-Aged Ribeye, Braised Short Ribs' },
    { id: 'W-02', name: '2015 Biondi-Santi Brunello di Montalcino Riserva', region: 'Tuscany', vintage: 2015, varietal: 'Sangiovese Grosso', bin: 'Vault North • Bin B-08-1', bottles: 12, wholesale: 220.00, menuPrice: 520.00, pairing: 'Mary Noto\'s Lasagna, Osso Buco alla Milanese' },
    { id: 'W-03', name: '2018 Gaja Barbaresco DOP', region: 'Piedmont', vintage: 2018, varietal: 'Nebbiolo', bin: 'Aisle 2 • Bin P-04-2', bottles: 24, wholesale: 140.00, menuPrice: 310.00, pairing: 'Veal Saltimbocca, Wild Mushroom Risotto' },
    { id: 'W-04', name: '2017 Giuseppe Quintarelli Amarone della Valpolicella', region: 'Veneto', vintage: 2017, varietal: 'Corvina/Rondinella', bin: 'Vault South • Bin V-01-4', bottles: 8, wholesale: 210.00, menuPrice: 480.00, pairing: 'Gorgonzola Filet Mignon, Aged Parmigiano Reggiano' },
    { id: 'W-05', name: '2019 Planeta Santa Cecilia Noto DOC', region: 'Sicily (Noto Origin)', vintage: 2019, varietal: 'Nero d\'Avola', bin: 'Heritage Bin S-01-1', bottles: 36, wholesale: 32.00, menuPrice: 88.00, pairing: 'Mary Noto\'s Eggplant Parmesan, House Sicilian Sausage' },
    { id: 'W-06', name: '2021 Marchesi Antinori Tignanello Toscana IGT', region: 'Tuscany', vintage: 2021, varietal: 'Sangiovese/Cabernet', bin: 'Aisle 1 • Bin T-12-2', bottles: 42, wholesale: 95.00, menuPrice: 240.00, pairing: 'Wood-Fired Pizza, Handcrafted Bolognese' }
  ]);

  // ─── 2. Valentina's Live BEO & Banquet Engine State ───
  const [beoList, setBeoList] = useState([
    { id: 'BEO-8841', name: 'Stehouwer Wedding Gala', client: 'Mr. & Mrs. Stehouwer', location: 'GR', room: 'Grand Ballroom (700 Capacity)', date: 'Saturday, Nov 14, 2026', time: '5:30 PM - 11:30 PM', guests: 220, menu: 'Plated Prime Filet Mignon & Chilean Sea Bass', bar: 'Joanne Noto Cellar Reserve & Premium Open Bar', total: 27720.00, deposit: 5000.00, balance: 22720.00, status: 'Confirmed' },
    { id: 'BEO-8842', name: 'Amway Executive Leadership Retreat', client: 'Amway Global', location: 'GH', room: 'La Grande Vista (Balcony & Sunset Views)', date: 'Thursday, Oct 22, 2026', time: '6:00 PM - 10:00 PM', guests: 85, menu: 'Lakeshore Wood-Fired Feast & Antipasti Misto', bar: 'Noto\'s Selected Italian Wines & Craft Cocktails', total: 9850.00, deposit: 3000.00, balance: 6850.00, status: 'Confirmed' }
  ]);
  const [isExportingBeo, setIsExportingBeo] = useState(false);

  // ─── 3. Tom's Kitchen Expo & Live 86'd Board State ───
  const [eightySixItems, setEightySixItems] = useState([
    { id: '86-01', item: 'Chilean Sea Bass (Fresh Catch)', category: 'Entree', reason: 'Sold out 38 portions; fresh delivery arriving tomorrow 8 AM', station: 'Grill / Sauté', time: '6:14 PM', reportedBy: 'Chef Marco' }
  ]);
  const [newItemTo86, setNewItemTo86] = useState('');
  const [new86Reason, setNew86Reason] = useState('');

  // ─── 4. Dual-Location Shift Logs State ───
  const [shiftLogs, setShiftLogs] = useState({
    GR: { date: 'Tonight • Aug 19, 2026', diningCovers: 248, banquetGuests: 220, totalRevenue: 34850.00, wineRevenue: 11420.00, laborVariance: '+0.4%', kitchenTicketAvg: '18 mins', managerNotes: 'Grand Ballroom wedding executed seamlessly. Joanne hosted private tasting in Vault for party of 12.', maintenanceAlerts: 'Air filtration unit in private dining room #2 cleared.', status: 'On Track' },
    GH: { date: 'Tonight • Aug 19, 2026', diningCovers: 310, banquetGuests: 85, totalRevenue: 28400.00, wineRevenue: 7850.00, laborVariance: '-1.2%', kitchenTicketAvg: '14 mins', managerNotes: 'Sunset dining was at 100% capacity. Wood-fired pizza turned 180 pies. Bocce courts ran 6 matches.', maintenanceAlerts: 'Deck heater pilot light serviced.', status: 'High Volume' }
  });
  const [isExportingBrief, setIsExportingBrief] = useState(false);

  // ─── 5. Employee Chat State ───
  const [employeeChatDepts, setEmployeeChatDepts] = useState(() => {
    try {
      const saved = localStorage.getItem('aibs_notos_employee_chat');
      if (saved) return JSON.parse(saved);
    } catch {}
    return [
      {
        department: 'Management & Family Executive',
        icon: '👑',
        channels: [
          {
            id: 'exec-urgent-86',
            name: 'urgent-86-executive-alerts',
            position: 'Tony, Tom, Valentina, GMs & Head Chefs',
            unread: 2,
            messages: [
              { sender: 'Chef Marco', role: 'Executive Chef', time: '6:14 PM', text: '🚨 86 Chilean Sea Bass for the rest of tonight! Substituting Grilled Mediterranean Halibut.' },
              { sender: 'Tony Noto', role: 'Co-Owner / Director', time: '6:18 PM', text: 'Acknowledged. Update POS table screens and alert host stand immediately.' }
            ]
          },
          {
            id: 'gr-gh-sync',
            name: 'gr-gh-cross-location-sync',
            position: 'Grand Rapids & Grand Haven Leadership',
            unread: 0,
            messages: [
              { sender: 'Valentina Noto', role: 'Event Coordinator', time: '4:45 PM', text: 'GR Ballroom locked in for 220 guests at 5:30 PM. Champagne flutes staged.' },
              { sender: 'David L.', role: 'General Manager (Grand Haven)', time: '5:02 PM', text: 'Lakeshore deck at Bil-Mar prepped. Sunset forecast is clear; expecting heavy walk-in patio volume.' }
            ]
          }
        ]
      },
      {
        department: 'Wine Cellar & Sommelier Team',
        icon: '🍾',
        channels: [
          {
            id: 'joanne-cellar',
            name: 'joanne-wine-vault-sommeliers',
            position: 'Joanne Noto & Floor Sommeliers',
            unread: 1,
            messages: [
              { sender: 'Joanne Noto', role: 'Master Sommelier', time: '4:30 PM', text: 'Table 18 ordered the 2015 Biondi-Santi Brunello. Bin B-08-1. Decant 25 minutes prior to main course.' },
              { sender: 'Matteo V.', role: 'Lead Sommelier', time: '4:35 PM', text: 'Decanter prepped in the cellar tasting room.' }
            ]
          }
        ]
      },
      {
        department: 'Banquets & Event Operations',
        icon: '🏛️',
        channels: [
          {
            id: 'valentina-banquets',
            name: 'valentina-banquet-logistics',
            position: 'Valentina Noto & Banquet Captains',
            unread: 0,
            messages: [
              { sender: 'Valentina Noto', role: 'Event Coordinator', time: '3:30 PM', text: 'Head table centerpieces and audiovisual projection for Stehouwer wedding verified.' }
            ]
          }
        ]
      },
      {
        department: 'Kitchen & Culinary Masters',
        icon: '🍳',
        channels: [
          {
            id: 'tom-kitchen',
            name: 'tom-noto-kitchen-line',
            position: 'Tom Noto, Line Cooks & Prep Chefs',
            unread: 0,
            messages: [
              { sender: 'Tom Noto', role: 'Culinary Operator', time: '5:00 PM', text: 'Mary Noto\'s lasagna batch #3 is resting. Fresh bread warmers stocked.' }
            ]
          }
        ]
      },
      {
        department: 'Front of House & Guest Service',
        icon: '🤵',
        channels: [
          {
            id: 'nicoletta-foh',
            name: 'nicoletta-foh-service',
            position: 'Nicoletta Noto, Host Stand & Servers',
            unread: 0,
            messages: [
              { sender: 'Nicoletta Noto', role: 'FOH Operations', time: '5:15 PM', text: 'Remember Santina\'s standard: greet every guest by name within 30 seconds of arrival.' }
            ]
          }
        ]
      }
    ];
  });
  const [activeChannelId, setActiveChannelId] = useState('exec-urgent-86');
  const [chatMessageInput, setChatMessageInput] = useState('');
  const [selectedPostingRole, setSelectedPostingRole] = useState('Tony Noto (Co-Owner)');
  const chatEndRef = useRef(null);

  // Presentation Storyboard Matrix
  const presentationSlides = [
    {
      step: 0,
      title: "1. The AI-BS Executive Value Proposition",
      entity: "AI-BS Enterprise Operating System",
      subsystem: "overview",
      roi: "Automates Multi-Location Ops • Replaces 6 Disconnected SaaS Subscriptions",
      audio: "/assets/notos/audio/executive_overview.mp3",
      pitch: "[Spoken Word] [Enthusiastic Italian Radio Commercial] (Excited, charismatic) Benvenuti, my friends! Today, we show you how the AI-BS Operating System takes your beautiful family business—like our very own Noto's with 40 years of amore—and turns it into an absolute powerhouse! Capisce? [Sound effect: cash register ding] We take you on a tour of five incredible tools that make running multiple locations, the wine cellar, the grand banquets, and our beautiful staff as smooth as a fine olive oil. Andiamo! [Slide transition: whoosh]"
    },
    {
      step: 1,
      title: "2. Joanne Noto's 12,000-Bottle Cellar Master AI",
      entity: "Wine & Beverage Inventory Logistics",
      subsystem: "cellar",
      roi: "Recovers +24% High-Margin Wine Sales • Zero Lost Bottles Across Bins",
      audio: "/assets/notos/audio/joannes_cellar_master.mp3",
      pitch: "[Spoken Word] [Passionate Theatrical Speech] (Passionate) Mamma mia, the wine! We got 12,000 bottles, and believe me, you don't wanna lose track of the Brunello! Joanne's Cellar Master AI knows exactly where every single bottle is hiding—which aisle, which rack, which shelf! And it tells your servers exactly what to pair with the chef's special tonight. We’re talkin' zero lost bottles and a whole lot of happy customers. [Sound effect: wine glasses clinking] Magnifico! [Slide transition: whoosh]"
    },
    {
      step: 2,
      title: "3. Valentina's Banquet Engine & Word BEO Pipeline",
      entity: "Event Sales & Contract Automation",
      subsystem: "banquets",
      roi: "Cuts BEO Drafting from 3 Hours to 30 Seconds • 1-Click OpenXML Word Output",
      audio: "/assets/notos/audio/valentinas_banquets.mp3",
      pitch: "[Spoken Word] [Professional Confident Voiceover] (Confident, proud) When you throw a party for 700 people, it’s gotta be perfect, eh? Valentina’s Banquet Engine takes the headache right out of the paperwork! It calculates the food, the bar, the taxes, the tip—bam! In thirty seconds flat, you get a beautiful Microsoft Word contract, ready for the signature. [Sound effect: stamp of approval] No more three-hour headaches, just beautiful events! [Slide transition: whoosh]"
    },
    {
      step: 3,
      title: "4. Tom's Kitchen Expo & Real-Time 86'd Board",
      entity: "BOH Kitchen Line & POS Interceptor",
      subsystem: "kitchen",
      roi: "Eliminates 100% of Awkward Table Re-Orders & Server Confusion",
      audio: "/assets/notos/audio/toms_kitchen.mp3",
      pitch: "[Spoken Word] [Fast-paced Intense Speech] (Intense, fast-talking) Listen to me, when the kitchen runs out of the fresh Chilean Sea Bass, there’s no time to yell across the restaurant! Tom hits one button, and boom—it’s 86'd! [Sound effect: digital alert ping] Instantly, every iPad, every host stand, and every server knows. No more taking orders for food we don't have, no more apologizing to the table. Just perfect harmony in the kitchen, like a beautiful symphony! [Slide transition: whoosh]"
    },
    {
      step: 4,
      title: "5. Dual-Location Command Center & Operations Brief",
      entity: "Cross-Location GM Executive Handoff",
      subsystem: "handoff",
      roi: "Synchronizes Multiple Properties • Generates Nightly Executive Word Briefs",
      audio: "/assets/notos/audio/two_locations.mp3",
      pitch: "[Spoken Word] [Authoritative Business Voiceover] (Authoritative, commanding) Running two locations at once? Grand Rapids here, Grand Haven there—you gotta be everywhere! The Dual-Location Command Center brings it all together! The managers log the covers, the wine sales, the ticket times. Then, with one click, you get a beautiful nightly report in a Word document. [Sound effect: satisfying paper shuffle] You see everything, you know everything. That’s how a boss runs the business! [Slide transition: whoosh]"
    },
    {
      step: 5,
      title: "6. Horizontal Scalability Across Multiple Business Entities",
      entity: "Multi-Entity Enterprise Ecosystem",
      subsystem: "overview",
      roi: "One Architecture Scales to Fleet Services, Media Production, & Cloud Storage",
      audio: "/assets/notos/audio/powerhouse_family.mp3",
      pitch: "[Spoken Word] [Professional Closing Sales Pitch] (Confident, authoritative, persuasive) And you know what the best part is? This beautiful AI-BS architecture isn’t just for the restaurant. It scales horizontally. We're talking mobile wash fleets, Hollywood screenwriting, cloud drives—everything. It’s the ultimate operational stack for the family empire that wants continuous growth. [Sound effect: confident corporate swoosh] Salute to the future!"
    }
  ];

  // Auto-Tour Interval
  useEffect(() => {
    let timer;
    if (isPresentationMode && isAutoTour) {
      timer = setInterval(() => {
        setPresentationStep(prev => {
          if (prev < presentationSlides.length - 1) return prev + 1;
          setIsAutoTour(false);
          return prev;
        });
      }, 10000);
    }
    return () => clearInterval(timer);
  }, [isPresentationMode, isAutoTour]);

  // Sync Subsystem to Presentation Slide
  useEffect(() => {
    if (isPresentationMode) {
      const slide = presentationSlides[presentationStep];
      if (slide && slide.subsystem) {
        setActiveSubsystem(slide.subsystem);
      }
    }
  }, [presentationStep, isPresentationMode]);

  // Auto-save local state
  useEffect(() => {
    localStorage.setItem('aibs_notos_active_location', activeLocation);
  }, [activeLocation]);

  useEffect(() => {
    localStorage.setItem('aibs_notos_employee_chat', JSON.stringify(employeeChatDepts));
  }, [employeeChatDepts]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [employeeChatDepts, activeChannelId]);

  // Handlers
  const handleAdd86 = () => {
    if (!newItemTo86.trim()) return;
    const newEntry = {
      id: `86-${Date.now()}`,
      item: newItemTo86.trim(),
      category: 'Kitchen / Bar',
      reason: new86Reason.trim() || 'Item depleted during active service',
      station: 'Floor & Kitchen Stations',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      reportedBy: selectedPostingRole.split(' (')[0]
    };
    setEightySixItems(prev => [newEntry, ...prev]);

    const alertMsg = {
      sender: selectedPostingRole.split(' (')[0],
      role: selectedPostingRole.split(' (')[1]?.replace(')', '') || 'Manager',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: `🚨 86 BROADCAST: ${newItemTo86.trim()} is 86'd across all POS screens and kitchen expo stations! (${new86Reason.trim() || 'Depleted'})`
    };
    setEmployeeChatDepts(prev => prev.map(d => ({
      ...d,
      channels: d.channels.map(c => c.id === 'exec-urgent-86' ? { ...c, messages: [...c.messages, alertMsg] } : c)
    })));

    setNewItemTo86('');
    setNew86Reason('');
  };

  const handleResolve86 = (id) => {
    setEightySixItems(prev => prev.filter(item => item.id !== id));
  };

  const handleSendChatMessage = () => {
    if (!chatMessageInput.trim()) return;
    const parts = selectedPostingRole.split(' (');
    const sender = parts[0];
    const role = parts[1]?.replace(')', '') || 'Staff';

    const msg = {
      sender: sender.trim(),
      role: role.trim(),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: chatMessageInput.trim()
    };

    setEmployeeChatDepts(prev => prev.map(dept => ({
      ...dept,
      channels: dept.channels.map(ch => ch.id === activeChannelId ? { ...ch, messages: [...ch.messages, msg] } : ch)
    })));
    setChatMessageInput('');
  };

  const handleExportBeoDocx = async (beo) => {
    setIsExportingBeo(true);
    try {
      const res = await fetch(`${baseUrl}/api/documents/banquet/generate_beo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_name: beo.name,
          client_name: beo.client,
          contact_email: 'events@notosoldworld.com',
          contact_phone: '(616) 493-6686',
          event_date: beo.date,
          event_time: beo.time,
          room_name: beo.room,
          guest_count: beo.guests,
          menu_package: beo.menu,
          bar_service: beo.bar,
          special_requests: 'Staged head table, champagne toast upon arrival, customized lighting.',
          subtotal: beo.total / 1.26,
          service_charge: (beo.total / 1.26) * 0.20,
          tax: (beo.total / 1.26) * 0.06,
          total: beo.total,
          deposit_paid: beo.deposit,
          balance_due: beo.balance
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Noto_BEO_${beo.id}_${beo.client.replace(/\s+/g, '_')}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('Could not export Word BEO contract.');
      }
    } catch (e) {
      alert(`BEO export error: ${e.message}`);
    } finally {
      setIsExportingBeo(false);
    }
  };

  const handleExportOperationsBrief = async () => {
    setIsExportingBrief(true);
    try {
      const currentLog = shiftLogs[activeLocation];
      const res = await fetch(`${baseUrl}/api/documents/export_docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `Noto's Executive Operations Brief — ${activeLocation === 'GR' ? 'Grand Rapids 28th St' : 'Grand Haven at the Bil-Mar'}`,
          content: `# Noto's Enterprise Operations Brief\n\n**Location:** ${activeLocation === 'GR' ? 'Grand Rapids Complex (28th St SE)' : 'Grand Haven Waterfront (Noto\'s at the Bil-Mar)'}\n**Date:** ${currentLog.date}\n**Status:** ${currentLog.status}\n\n## 1. Daily Financial & Guest Metrics\n- Total Dining Covers: ${currentLog.diningCovers}\n- Banquet / Private Event Guests: ${currentLog.banquetGuests}\n- Total Daily Revenue: $${currentLog.totalRevenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}\n- Joanne Noto Wine Cellar Revenue: $${currentLog.wineRevenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}\n- Labor Variance: ${currentLog.laborVariance}\n- Kitchen Ticket Average: ${currentLog.kitchenTicketAvg}\n\n## 2. General Manager Operations Log\n${currentLog.managerNotes}\n\n## 3. Maintenance & Facility Notes\n${currentLog.maintenanceAlerts}\n\n## 4. Active 86'd Inventory & Kitchen Alerts\n${eightySixItems.map(item => `- **${item.item}** (${item.station}): ${item.reason} [Reported by ${item.reportedBy} at ${item.time}]`).join('\n')}\n\n## 5. Upcoming Banquets & Private Events\n${beoList.filter(b => b.location === activeLocation).map(b => `- **${b.name}** | ${b.date} | Room: ${b.room} | Guests: ${b.guests} | Total: $${b.total.toLocaleString()}`).join('\n')}\n\n---\n*Generated by Noto's Enterprise Operating System.*`
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Notos_Operations_Brief_${activeLocation}_${new Date().toISOString().split('T')[0]}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('Could not download Operations Brief.');
      }
    } catch (e) {
      alert(`Export error: ${e.message}`);
    } finally {
      setIsExportingBrief(false);
    }
  };

  const currentSlide = presentationSlides[presentationStep] || presentationSlides[0];

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#0a0204',
      color: '#fef3c7',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {/* ── Top Header Navigation Bar ── */}
      <header style={{
        padding: '12px 28px',
        backgroundColor: '#190408',
        borderBottom: '1px solid rgba(159, 18, 57, 0.4)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 20
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            backgroundColor: 'rgba(217, 119, 6, 0.2)',
            border: '1px solid rgba(217, 119, 6, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.3rem'
          }}>
            🍷
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.3rem', fontFamily: '"Playfair Display", Georgia, serif', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '10px' }}>
              Noto's Enterprise <span style={{ color: '#ffffff', fontSize: '0.9rem', fontWeight: '400', padding: '2px 8px', borderRadius: '6px', background: 'rgba(159, 18, 57, 0.5)', border: '1px solid rgba(159, 18, 57, 0.8)' }}>OS v5.26</span>
            </h1>
            <p style={{ margin: 0, fontSize: '0.75rem', color: '#fda4af' }}>
              Authentic Sicilian-American Heritage • Est. 1982 • Built Debt-Free
            </p>
          </div>
        </div>

        {/* Action Controls & Presentation Trigger */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* 🍸 Open Multi-Bar Stock & Dispatch Engine */}
          <button
            onClick={() => window.location.search = '?tab=noto_inventory'}
            style={{
              backgroundColor: 'rgba(217, 119, 6, 0.2)',
              color: '#f59e0b',
              border: '1px solid #d97706',
              padding: '8px 14px',
              borderRadius: '8px',
              fontWeight: '800',
              fontSize: '0.8rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            🍸 Multi-Bar Stock & Dispatch
          </button>

          {/* 🎬 Start Presentation Button */}
          <button
            onClick={() => {
              setIsPresentationMode(!isPresentationMode);
              if (!isPresentationMode) setPresentationStep(0);
            }}
            style={{
              backgroundColor: isPresentationMode ? '#e11d48' : 'linear-gradient(90deg, #d97706 0%, #b45309 100%)',
              background: isPresentationMode ? '#e11d48' : 'linear-gradient(90deg, #d97706 0%, #b45309 100%)',
              color: '#ffffff',
              border: 'none',
              padding: '8px 18px',
              borderRadius: '8px',
              fontWeight: '800',
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 16px rgba(217, 119, 6, 0.4)',
              transition: 'all 0.2s'
            }}
          >
            <Presentation size={16} /> {isPresentationMode ? '✕ Exit Presentation' : '🎬 Start Executive Presentation'}
          </button>

          {/* Location Switcher */}
          <div style={{
            display: 'flex',
            backgroundColor: '#120205',
            padding: '4px',
            borderRadius: '10px',
            border: '1px solid rgba(159, 18, 57, 0.6)'
          }}>
            <button
              onClick={() => setActiveLocation('GR')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: activeLocation === 'GR' ? '#881337' : 'transparent',
                color: activeLocation === 'GR' ? '#ffffff' : '#fda4af',
                fontWeight: activeLocation === 'GR' ? '800' : '600',
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              <Building2 size={14} /> Grand Rapids
            </button>
            <button
              onClick={() => setActiveLocation('GH')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: activeLocation === 'GH' ? '#0284c7' : 'transparent',
                color: activeLocation === 'GH' ? '#ffffff' : '#93c5fd',
                fontWeight: activeLocation === 'GH' ? '800' : '600',
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              <Flame size={14} /> Grand Haven
            </button>
          </div>

          <button
            onClick={handleExportOperationsBrief}
            disabled={isExportingBrief}
            style={{
              backgroundColor: '#d97706',
              color: '#000000',
              border: 'none',
              padding: '8px 14px',
              borderRadius: '8px',
              fontWeight: '800',
              fontSize: '0.8rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Download size={14} /> {isExportingBrief ? 'Exporting...' : '📥 Daily Brief (.docx)'}
          </button>
        </div>
      </header>

      {/* ── 🎬 Floating Presentation Spotlight HUD (When Active) ── */}
      {isPresentationMode && (
        <div style={{
          backgroundColor: '#1b060b',
          borderBottom: '2px solid #f59e0b',
          padding: '16px 32px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '24px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.8)',
          zIndex: 30
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
              <span style={{ backgroundColor: '#f59e0b', color: '#000000', fontSize: '0.72rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                SLIDE {presentationStep + 1} OF {presentationSlides.length}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: '700' }}>
                🎯 ROI IMPACT: {currentSlide.roi}
              </span>
            </div>
            <h3 style={{ margin: '0 0 4px 0', fontSize: '1.2rem', color: '#ffffff', fontFamily: 'serif' }}>
              {currentSlide.title}
            </h3>
            <p style={{ margin: '0 0 8px 0', fontSize: '0.85rem', color: '#fef3c7', lineHeight: '1.4' }}>
              {currentSlide.pitch}
            </p>
            {currentSlide.audio && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: '800', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  🎙️ SUNO VOICE PITCH:
                </span>
                <audio
                  key={currentSlide.audio}
                  src={currentSlide.audio?.startsWith('http') || currentSlide.audio?.startsWith('data:') || currentSlide.audio?.startsWith('blob:') ? currentSlide.audio : `${baseUrl}${currentSlide.audio?.startsWith('/') ? '' : '/'}${currentSlide.audio}`}
                  controls
                  autoPlay
                  style={{ height: '32px', filter: 'invert(0.9) sepia(1) hue-rotate(330deg) saturate(3)' }}
                />
              </div>
            )}
          </div>

          {/* Stepper Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
            <button
              onClick={() => setPresentationStep(Math.max(0, presentationStep - 1))}
              disabled={presentationStep === 0}
              style={{
                backgroundColor: 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.15)',
                color: '#ffffff',
                padding: '8px 14px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: '700',
                cursor: presentationStep === 0 ? 'not-allowed' : 'pointer'
              }}
            >
              ⏮️ Prev
            </button>

            <button
              onClick={() => setIsAutoTour(!isAutoTour)}
              style={{
                backgroundColor: isAutoTour ? '#e11d48' : '#d97706',
                color: '#ffffff',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {isAutoTour ? <Pause size={14} /> : <Play size={14} />} {isAutoTour ? 'Pause Tour' : 'Auto Tour (10s)'}
            </button>

            <button
              onClick={() => setPresentationStep(Math.min(presentationSlides.length - 1, presentationStep + 1))}
              disabled={presentationStep === presentationSlides.length - 1}
              style={{
                backgroundColor: '#f59e0b',
                color: '#000000',
                border: 'none',
                padding: '8px 18px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: '800',
                cursor: presentationStep === presentationSlides.length - 1 ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              Next Tool <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ── Subsystem Navigation Ribbon ── */}
      <nav style={{
        padding: '8px 28px',
        backgroundColor: '#120205',
        borderBottom: '1px solid rgba(159, 18, 57, 0.3)',
        display: 'flex',
        gap: '8px',
        overflowX: 'auto'
      }}>
        {[
          { id: 'overview', label: 'Executive Overview', icon: Sparkles },
          { id: 'cellar', label: "Joanne's 12,000-Bottle Cellar", icon: Wine },
          { id: 'banquets', label: "Valentina's Banquets & BEOs", icon: Award },
          { id: 'kitchen', label: "Tom's Kitchen & 86'd Board", icon: Utensils },
          { id: 'chat', label: 'Position & Staff Chat', icon: MessageSquare },
          { id: 'handoff', label: 'Daily GM Shift Handoff', icon: FileText }
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeSubsystem === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubsystem(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 16px',
                borderRadius: '8px',
                border: isActive ? '1px solid #f59e0b' : '1px solid transparent',
                backgroundColor: isActive ? 'rgba(217, 119, 6, 0.18)' : 'transparent',
                color: isActive ? '#ffffff' : '#fda4af',
                fontSize: '0.82rem',
                fontWeight: isActive ? '800' : '600',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
            >
              <Icon size={14} color={isActive ? '#f59e0b' : '#fda4af'} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* ── Main Viewport ── */}
      <main style={{
        flex: 1,
        padding: '24px 32px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px'
      }}>

        {/* ══════════ 1. EXECUTIVE OVERVIEW ══════════ */}
        {activeSubsystem === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{
              padding: '20px 24px',
              borderRadius: '16px',
              background: activeLocation === 'GR'
                ? 'linear-gradient(135deg, rgba(136, 19, 55, 0.4) 0%, rgba(30, 4, 8, 0.8) 100%)'
                : 'linear-gradient(135deg, rgba(2, 132, 199, 0.3) 0%, rgba(8, 20, 36, 0.8) 100%)',
              border: `1px solid ${activeLocation === 'GR' ? 'rgba(159, 18, 57, 0.6)' : 'rgba(2, 132, 199, 0.6)'}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <img src={activeLocation === 'GR' ? '/assets/notos/notos_logo_gr.png' : '/assets/notos/notos_logo_gh.png'} alt="Noto's Logo" style={{ height: '48px', objectFit: 'contain' }} />
                  <span style={{ fontSize: '0.75rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#f59e0b' }}>
                    {activeLocation === 'GR' ? '🏛️ GRAND RAPIDS (28TH ST SE)' : '🌅 GRAND HAVEN (NOTO\'S AT THE BIL-MAR)'}
                  </span>
                </div>
                <h2 style={{ margin: '4px 0 6px 0', fontSize: '1.6rem', fontFamily: '"Playfair Display", serif', color: '#ffffff' }}>
                  {activeLocation === 'GR' ? 'Fine Dining, 12,000-Bottle Cellar & 700-Seat Ballroom' : 'Panoramic Lake Michigan Sunset Dining & Wood-Fired Kitchen'}
                </h2>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#fda4af' }}>
                  {activeLocation === 'GR'
                    ? 'Managing Mary Noto’s traditional Sicilian kitchen, Joanne Noto’s underground vault, and Valentina’s Grand Ballroom galas.'
                    : 'Managing Russ Baltz’s historic 1952 beachside footprint rebuilt in 2019, contemporary wood-fired pizza expo, and La Grande Vista.'}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ backgroundColor: 'rgba(0,0,0,0.5)', padding: '12px 18px', borderRadius: '12px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <span style={{ fontSize: '0.72rem', color: '#fda4af', display: 'block' }}>TONIGHT'S COVERS</span>
                  <strong style={{ fontSize: '1.4rem', color: '#ffffff' }}>{shiftLogs[activeLocation].diningCovers}</strong>
                </div>
                <div style={{ backgroundColor: 'rgba(0,0,0,0.5)', padding: '12px 18px', borderRadius: '12px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <span style={{ fontSize: '0.72rem', color: '#fda4af', display: 'block' }}>EVENT GUESTS</span>
                  <strong style={{ fontSize: '1.4rem', color: '#f59e0b' }}>{shiftLogs[activeLocation].banquetGuests}</strong>
                </div>
                <div style={{ backgroundColor: 'rgba(0,0,0,0.5)', padding: '12px 18px', borderRadius: '12px', textAlign: 'center', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <span style={{ fontSize: '0.72rem', color: '#fda4af', display: 'block' }}>CELLAR REVENUE</span>
                  <strong style={{ fontSize: '1.4rem', color: '#34d399' }}>${shiftLogs[activeLocation].wineRevenue.toLocaleString()}</strong>
                </div>
              </div>
            </div>

            {/* 📸 Upscaled Family & Legacy Facility Banners */}
            <div style={{ display: 'flex', gap: '20px' }}>
              <div style={{ flex: 1, borderRadius: '18px', overflow: 'hidden', border: '1px solid rgba(217, 119, 6, 0.4)', height: '360px', position: 'relative', boxShadow: '0 8px 24px rgba(0,0,0,0.6)' }}>
                <img src="/assets/notos/notos_family_indoors.jpg" alt="Noto Family Indoors" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 15%' }} />
                <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '16px 20px', background: 'linear-gradient(to top, rgba(15, 2, 5, 0.95) 0%, rgba(15, 2, 5, 0) 100%)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: '800', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    👑 Mary & Tony Noto Family Heritage • 40+ Years of Amore
                  </span>
                  <span style={{ fontSize: '0.72rem', backgroundColor: 'rgba(217, 119, 6, 0.3)', border: '1px solid rgba(217, 119, 6, 0.6)', color: '#ffffff', padding: '3px 10px', borderRadius: '12px', fontWeight: '700' }}>
                    HQ 4K Upscaled
                  </span>
                </div>
              </div>

              <div style={{ flex: 1, borderRadius: '18px', overflow: 'hidden', border: '1px solid rgba(217, 119, 6, 0.4)', height: '360px', position: 'relative', boxShadow: '0 8px 24px rgba(0,0,0,0.6)' }}>
                <img src="/assets/notos/notos_family_outdoors.png" alt="Noto Family Outdoors" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 20%' }} />
                <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '16px 20px', background: 'linear-gradient(to top, rgba(15, 2, 5, 0.95) 0%, rgba(15, 2, 5, 0) 100%)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: '800', color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    🌅 Grand Rapids & Grand Haven Waterfront Legacy Footprint
                  </span>
                  <span style={{ fontSize: '0.72rem', backgroundColor: 'rgba(16, 185, 129, 0.3)', border: '1px solid rgba(16, 185, 129, 0.6)', color: '#ffffff', padding: '3px 10px', borderRadius: '12px', fontWeight: '700' }}>
                    HQ 4K Upscaled
                  </span>
                </div>
              </div>
            </div>

            {/* 🖼️ Rich Visual Quick Cards for Core Operational Modules */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
              <div
                onClick={() => setActiveSubsystem('cellar')}
                style={{
                  position: 'relative',
                  height: '200px',
                  borderRadius: '16px',
                  overflow: 'hidden',
                  border: '1px solid rgba(217, 119, 6, 0.5)',
                  cursor: 'pointer',
                  boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
                  transition: 'transform 0.2s'
                }}
              >
                <img src="/assets/notos/notos_wine_cellar.jpg" alt="Cellar" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 30%' }} />
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(15, 2, 5, 0.95) 15%, rgba(15, 2, 5, 0.4) 100%)', padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Wine size={26} color="#f59e0b" />
                    <span style={{ backgroundColor: 'rgba(217, 119, 6, 0.3)', color: '#f59e0b', border: '1px solid rgba(217, 119, 6, 0.6)', fontSize: '0.7rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                      12,000 BOTTLES
                    </span>
                  </div>
                  <div>
                    <h3 style={{ margin: '0 0 4px 0', fontSize: '1.1rem', color: '#ffffff', fontFamily: 'serif' }}>Joanne's Cellar Master</h3>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#fda4af' }}>Bin location database & sommelier pairings.</p>
                  </div>
                </div>
              </div>

              <div
                onClick={() => setActiveSubsystem('banquets')}
                style={{
                  position: 'relative',
                  height: '200px',
                  borderRadius: '16px',
                  overflow: 'hidden',
                  border: '1px solid rgba(217, 119, 6, 0.5)',
                  cursor: 'pointer',
                  boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
                  transition: 'transform 0.2s'
                }}
              >
                <img src="/assets/notos/notos_banquet_hall.png" alt="Banquets" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 20%' }} />
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(15, 2, 5, 0.95) 15%, rgba(15, 2, 5, 0.4) 100%)', padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Award size={26} color="#f59e0b" />
                    <span style={{ backgroundColor: 'rgba(217, 119, 6, 0.3)', color: '#f59e0b', border: '1px solid rgba(217, 119, 6, 0.6)', fontSize: '0.7rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                      700-SEAT BALLROOM
                    </span>
                  </div>
                  <div>
                    <h3 style={{ margin: '0 0 4px 0', fontSize: '1.1rem', color: '#ffffff', fontFamily: 'serif' }}>Valentina's Banquets</h3>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#fda4af' }}>Live BEO contract generator & Word export.</p>
                  </div>
                </div>
              </div>

              <div
                onClick={() => setActiveSubsystem('kitchen')}
                style={{
                  position: 'relative',
                  height: '200px',
                  borderRadius: '16px',
                  overflow: 'hidden',
                  border: '1px solid rgba(217, 119, 6, 0.5)',
                  cursor: 'pointer',
                  boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
                  transition: 'transform 0.2s'
                }}
              >
                <img src="/assets/notos/notos_pizza.png" alt="Kitchen" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 40%' }} />
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(15, 2, 5, 0.95) 15%, rgba(15, 2, 5, 0.4) 100%)', padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Utensils size={26} color="#f59e0b" />
                    <span style={{ backgroundColor: 'rgba(225, 29, 72, 0.4)', color: '#fb7185', border: '1px solid rgba(225, 29, 72, 0.7)', fontSize: '0.7rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                      LIVE POS 86'D
                    </span>
                  </div>
                  <div>
                    <h3 style={{ margin: '0 0 4px 0', fontSize: '1.1rem', color: '#ffffff', fontFamily: 'serif' }}>Tom's Kitchen & 86'd</h3>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#fda4af' }}>Live 86'd broadcast syncing line and POS.</p>
                  </div>
                </div>
              </div>

              <div
                onClick={() => setActiveSubsystem('handoff')}
                style={{
                  position: 'relative',
                  height: '200px',
                  borderRadius: '16px',
                  overflow: 'hidden',
                  border: '1px solid rgba(217, 119, 6, 0.5)',
                  cursor: 'pointer',
                  boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
                  transition: 'transform 0.2s'
                }}
              >
                <img src="/assets/notos/notos_menu.png" alt="Shift Log" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 20%' }} />
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(15, 2, 5, 0.95) 15%, rgba(15, 2, 5, 0.4) 100%)', padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <FileText size={26} color="#f59e0b" />
                    <span style={{ backgroundColor: 'rgba(52, 211, 153, 0.3)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.6)', fontSize: '0.7rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                      NIGHTLY BRIEF
                    </span>
                  </div>
                  <div>
                    <h3 style={{ margin: '0 0 4px 0', fontSize: '1.1rem', color: '#ffffff', fontFamily: 'serif' }}>Multi-Location Shift Log</h3>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#fda4af' }}>Unified nightly logbook and Word brief.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ══════════ 2. JOANNE'S WINE CELLAR ══════════ */}
        {activeSubsystem === 'cellar' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                Joanne Noto's Master Italian Cellar Vault
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                12,000 bottles • Exact bin locator (Aisle, Rack, Shelf) & table-side sommelier pairing co-pilot.
              </p>
            </div>

            <div style={{ borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(159, 18, 57, 0.4)', height: '180px' }}>
              <img src="/assets/notos/notos_wine_cellar.jpg" alt="Joanne's Wine Cellar" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center 30%' }} />
            </div>

            <div style={{ display: 'flex', gap: '12px', backgroundColor: 'rgba(20, 4, 8, 0.9)', padding: '10px 16px', borderRadius: '12px', border: '1px solid rgba(159, 18, 57, 0.4)' }}>
              <Search size={18} color="#fda4af" style={{ marginTop: '2px' }} />
              <input
                type="text"
                value={cellarSearch}
                onChange={e => setCellarSearch(e.target.value)}
                placeholder="Search vintages (e.g. Sassicaia, Brunello, Barbaresco, Bin A-14)..."
                style={{ flex: 1, background: 'transparent', border: 'none', color: '#fef3c7', fontSize: '0.9rem', outline: 'none' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
              {cellarInventory.map(wine => (
                <div key={wine.id} style={{ backgroundColor: 'rgba(20, 4, 8, 0.9)', border: '1px solid rgba(159, 18, 57, 0.4)', borderRadius: '14px', padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <span style={{ backgroundColor: 'rgba(217, 119, 6, 0.2)', color: '#f59e0b', border: '1px solid rgba(217, 119, 6, 0.4)', padding: '2px 8px', borderRadius: '6px', fontSize: '0.72rem', fontWeight: '700' }}>
                        {wine.region}
                      </span>
                      <h4 style={{ margin: '6px 0 2px 0', fontSize: '1.1rem', color: '#ffffff', fontFamily: 'serif' }}>{wine.name}</h4>
                      <span style={{ fontSize: '0.8rem', color: '#fda4af' }}>{wine.varietal}</span>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '1.2rem', fontWeight: '800', color: '#f59e0b', display: 'block' }}>${wine.menuPrice.toFixed(2)}</span>
                      <span style={{ fontSize: '0.72rem', color: '#34d399' }}>{wine.bottles} Bottles in Vault</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.4)', padding: '8px 12px', borderRadius: '8px', fontSize: '0.78rem' }}>
                    <span style={{ color: '#fef3c7' }}>📍 <strong>Bin Coordinates:</strong> {wine.bin}</span>
                    <span style={{ color: 'rgba(254, 205, 211, 0.6)' }}>Wholesale: ${wine.wholesale.toFixed(2)}</span>
                  </div>

                  <div style={{ fontSize: '0.8rem', color: '#fda4af', borderTop: '1px solid rgba(159, 18, 57, 0.2)', paddingTop: '8px' }}>
                    🍽️ <strong>Sommelier Pairing:</strong> {wine.pairing}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════ 3. VALENTINA'S BANQUETS & BEOS ══════════ */}
        {activeSubsystem === 'banquets' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                Valentina's Banquet & Event Order (BEO) Engine
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                Managing Grand Rapids 700-seat European ballroom & Grand Haven's La Grande Vista events.
              </p>
            </div>

            <div style={{ borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(159, 18, 57, 0.4)', height: '220px' }}>
              <img src="/assets/notos/notos_banquet_hall.png" alt="Valentina's Banquet Hall" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {beoList.map(beo => (
                <div key={beo.id} style={{ backgroundColor: 'rgba(20, 4, 8, 0.9)', border: '1px solid rgba(159, 18, 57, 0.4)', borderLeft: '4px solid #f59e0b', borderRadius: '14px', padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '60%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: '800', color: '#f59e0b', backgroundColor: 'rgba(217, 119, 6, 0.2)', padding: '2px 8px', borderRadius: '6px' }}>
                        {beo.id} • {beo.location === 'GR' ? 'Grand Rapids' : 'Grand Haven'}
                      </span>
                      <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#ffffff', fontFamily: 'serif' }}>{beo.name}</h3>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: '#fef3c7' }}>
                      <strong>Client:</strong> {beo.client} • <strong>Date:</strong> {beo.date} ({beo.time})
                    </p>
                    <p style={{ margin: 0, fontSize: '0.8rem', color: '#fda4af' }}>
                      🏛️ <strong>Room:</strong> {beo.room} • 👥 <strong>Guaranteed Guests:</strong> {beo.guests}
                    </p>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '10px' }}>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '1.35rem', fontWeight: '800', color: '#f59e0b', display: 'block' }}>
                        ${beo.total.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: '#34d399' }}>
                        Deposit: ${beo.deposit.toLocaleString()} • Balance: ${beo.balance.toLocaleString()}
                      </span>
                    </div>

                    <button
                      onClick={() => handleExportBeoDocx(beo)}
                      disabled={isExportingBeo}
                      style={{
                        backgroundColor: '#881337',
                        color: '#ffffff',
                        border: '1px solid #be123c',
                        padding: '8px 16px',
                        borderRadius: '8px',
                        fontWeight: '700',
                        fontSize: '0.82rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <Download size={14} /> {isExportingBeo ? 'Exporting...' : '📥 Export Word BEO (.docx)'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════ 4. TOM'S KITCHEN & 86'D BOARD ══════════ */}
        {activeSubsystem === 'kitchen' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                Tom Noto's Kitchen Expo & Live 86'd Board
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                Real-time broadcast synchronizing line cooks, floor sommeliers, POS screens, and host stands.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1, borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(159, 18, 57, 0.4)', height: '220px' }}>
                <img src="/assets/notos/notos_menu.png" alt="Noto's Menu" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
              <div style={{ flex: 1, borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(159, 18, 57, 0.4)', height: '220px' }}>
                <img src="/assets/notos/notos_pizza.png" alt="Noto's Pizza" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
            </div>

            <div style={{ backgroundColor: 'rgba(25, 4, 8, 0.9)', padding: '18px 24px', borderRadius: '14px', border: '1px solid rgba(225, 29, 72, 0.5)', display: 'flex', gap: '12px', alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#fb7185' }}>Menu Item / Vintage to 86:</span>
                <input
                  type="text"
                  value={newItemTo86}
                  onChange={e => setNewItemTo86(e.target.value)}
                  placeholder="e.g. Veal Chop alla Parmigiana, Chilean Sea Bass, 2015 Barolo..."
                  style={{ backgroundColor: '#120205', border: '1px solid rgba(159, 18, 57, 0.6)', borderRadius: '8px', padding: '10px 14px', color: '#fef3c7', fontSize: '0.88rem', outline: 'none' }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1.5 }}>
                <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#fb7185' }}>Depletion Reason & Next Supply:</span>
                <input
                  type="text"
                  value={new86Reason}
                  onChange={e => setNew86Reason(e.target.value)}
                  placeholder="e.g. 42 portions sold; fresh delivery arriving tomorrow at 9 AM..."
                  style={{ backgroundColor: '#120205', border: '1px solid rgba(159, 18, 57, 0.6)', borderRadius: '8px', padding: '10px 14px', color: '#fef3c7', fontSize: '0.88rem', outline: 'none' }}
                />
              </div>

              <button
                onClick={handleAdd86}
                style={{
                  backgroundColor: '#e11d48',
                  color: '#ffffff',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontWeight: '800',
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  alignSelf: 'flex-end',
                  boxShadow: '0 4px 14px rgba(225, 29, 72, 0.4)'
                }}
              >
                🚨 Broadcast 86
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {eightySixItems.map(item => (
                <div key={item.id} style={{ backgroundColor: 'rgba(225, 29, 72, 0.12)', border: '1px solid rgba(225, 29, 72, 0.5)', borderRadius: '12px', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ backgroundColor: '#e11d48', color: '#ffffff', fontSize: '0.72rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                        86'D ACTIVE
                      </span>
                      <h4 style={{ margin: 0, fontSize: '1.15rem', color: '#ffffff' }}>{item.item}</h4>
                      <span style={{ fontSize: '0.78rem', color: 'rgba(254, 205, 211, 0.7)' }}>({item.station})</span>
                    </div>
                    <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#fecdd3' }}>
                      {item.reason} • <em>Reported by {item.reportedBy} at {item.time}</em>
                    </p>
                  </div>

                  <button
                    onClick={() => handleResolve86(item.id)}
                    style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid #10b981', padding: '6px 14px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: '700', cursor: 'pointer' }}
                  >
                    ✓ Restock / Clear 86
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════ 5. POSITION & STAFF CHAT ══════════ */}
        {activeSubsystem === 'chat' && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: '320px 1fr',
            gap: '20px',
            height: '620px',
            backgroundColor: 'rgba(15, 2, 5, 0.95)',
            border: '1px solid rgba(159, 18, 57, 0.5)',
            borderRadius: '18px',
            overflow: 'hidden'
          }}>
            <div style={{
              backgroundColor: 'rgba(22, 4, 8, 0.98)',
              borderRight: '1px solid rgba(159, 18, 57, 0.4)',
              padding: '20px 14px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}>
              <span style={{ padding: '0 8px', fontSize: '0.75rem', fontWeight: '800', letterSpacing: '0.1em', color: '#f59e0b' }}>
                POSITION DEPARTMENTS
              </span>
              {employeeChatDepts.map((dept, dIdx) => (
                <div key={dIdx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 8px', color: '#fda4af', fontWeight: '700', fontSize: '0.8rem' }}>
                    <span>{dept.icon}</span>
                    <span>{dept.department}</span>
                  </div>
                  {dept.channels.map(channel => (
                    <button
                      key={channel.id}
                      onClick={() => setActiveChannelId(channel.id)}
                      style={{
                        textAlign: 'left',
                        padding: '10px 12px',
                        backgroundColor: activeChannelId === channel.id ? 'rgba(159, 18, 57, 0.4)' : 'transparent',
                        border: 'none',
                        borderRadius: '8px',
                        color: activeChannelId === channel.id ? '#ffffff' : '#fef3c7',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.1s'
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontWeight: activeChannelId === channel.id ? '700' : '500' }}># {channel.name}</span>
                        <span style={{ fontSize: '0.7rem', color: 'rgba(254, 205, 211, 0.6)' }}>{channel.position}</span>
                      </div>
                      {channel.unread > 0 && (
                        <span style={{ backgroundColor: '#e11d48', color: '#fff', fontSize: '0.7rem', fontWeight: '800', padding: '2px 6px', borderRadius: '10px' }}>
                          {channel.unread}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              ))}
            </div>
            
            {/* Active Channel Chat Area */}
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ padding: '16px 24px', borderBottom: '1px solid rgba(159, 18, 57, 0.4)', backgroundColor: 'rgba(20, 4, 8, 0.8)' }}>
                <h3 style={{ margin: '0 0 4px 0', fontSize: '1.2rem', color: '#ffffff' }}># {activeChannel.name}</h3>
                <span style={{ fontSize: '0.8rem', color: '#fda4af' }}>{activeChannel.position}</span>
              </div>
              
              <div style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {activeChannel.messages.map((msg, mIdx) => (
                  <div key={mIdx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: '700', color: '#f59e0b', fontSize: '0.9rem' }}>{msg.sender}</span>
                      <span style={{ fontSize: '0.75rem', color: 'rgba(254, 205, 211, 0.6)', border: '1px solid rgba(159, 18, 57, 0.5)', padding: '2px 6px', borderRadius: '4px' }}>{msg.role}</span>
                      <span style={{ fontSize: '0.75rem', color: '#fda4af' }}>{msg.time}</span>
                    </div>
                    <div style={{ backgroundColor: 'rgba(159, 18, 57, 0.1)', border: '1px solid rgba(159, 18, 57, 0.3)', padding: '12px 16px', borderRadius: '0 12px 12px 12px', color: '#fef3c7', fontSize: '0.9rem', lineHeight: '1.4', maxWidth: '85%' }}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
              
              <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(159, 18, 57, 0.4)', backgroundColor: 'rgba(20, 4, 8, 0.8)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#fda4af' }}>Posting as:</span>
                  <select
                    value={selectedPostingRole}
                    onChange={e => setSelectedPostingRole(e.target.value)}
                    style={{ backgroundColor: '#120205', border: '1px solid rgba(159, 18, 57, 0.6)', color: '#fef3c7', padding: '4px 8px', borderRadius: '6px', fontSize: '0.8rem', outline: 'none' }}
                  >
                    <option>Tony Noto (Co-Owner)</option>
                    <option>Joanne Noto (Master Sommelier)</option>
                    <option>Tom Noto (Culinary Operator)</option>
                    <option>Valentina Noto (Event Coordinator)</option>
                    <option>Nicoletta Noto (FOH Operations)</option>
                    <option>Chef Marco (Executive Chef)</option>
                    <option>David L. (General Manager GH)</option>
                  </select>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <input
                    type="text"
                    value={chatMessageInput}
                    onChange={e => setChatMessageInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSendChatMessage()}
                    placeholder={`Message #${activeChannel.name}...`}
                    style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159, 18, 57, 0.6)', borderRadius: '10px', padding: '12px 16px', color: '#fef3c7', fontSize: '0.95rem', outline: 'none' }}
                  />
                  <button
                    onClick={handleSendChatMessage}
                    style={{
                      backgroundColor: '#881337',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '10px',
                      padding: '0 20px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <Send size={18} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* ══════════ 6. HANDOFF / SHIFT LOGS ══════════ */}
        {activeSubsystem === 'handoff' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
            <FileText size={48} color="#f59e0b" style={{ opacity: 0.8 }} />
            <h3 style={{ margin: 0, fontSize: '1.4rem', color: '#ffffff' }}>Daily GM Shift Log</h3>
            <p style={{ color: '#fda4af', textAlign: 'center', maxWidth: '400px' }}>
              The end-of-day executive handover is generated automatically using the active location's data. 
              Switch between Grand Rapids and Grand Haven in the top bar to view respective logs.
            </p>
            <button
              onClick={handleExportOperationsBrief}
              disabled={isExportingBrief}
              style={{
                backgroundColor: '#d97706',
                color: '#000000',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '8px',
                fontWeight: '800',
                fontSize: '0.9rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 12px rgba(217, 119, 6, 0.35)',
                marginTop: '10px'
              }}
            >
              <Download size={16} /> {isExportingBrief ? 'Generating...' : `Export ${activeLocation} Brief to Word`}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
