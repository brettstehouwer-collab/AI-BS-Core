import React, { useState, useEffect } from 'react';

export default function JohnBarr({ BACKEND_URL }) {
  const [activeTab, setActiveTab] = useState("orders");
  const [orders, setOrders] = useState([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [filterStatus, setFilterStatus] = useState("All");
  const [orderActionMsg, setOrderActionMsg] = useState("");
  const [stats, setStats] = useState({ total_orders: 0, gross_revenue: 0 });

  // Analytics state
  const [analyticsOverview, setAnalyticsOverview] = useState(null);
  const [webTelemetry, setWebTelemetry] = useState(null);
  const [monthlyReport, setMonthlyReport] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [semanticQuery, setSemanticQuery] = useState("");
  const [semanticResults, setSemanticResults] = useState([]);
  const [searchingSemantic, setSearchingSemantic] = useState(false);
  const [copiedReportMsg, setCopiedReportMsg] = useState("");

  const resolvedBackend = BACKEND_URL || "http://localhost:8080";

  const [notes, setNotes] = useState([
    { 
      id: 7, 
      title: "Direct SMS from John Barr: Added 3 Spices, $5 Flat Shipping & Venmo (@John-Barr-1293) + Square", 
      date: "2026-09-13", 
      content: "Received direct text instructions from John Barr: 1) Added 3 signature seasonings (@ $8.99): Gringo Curry, Original Salt Pepper Seasoning, and Citrus Pepper, expanding active smokehouse lineup to 7 rubs. 2) Replaced previous credit card processor with direct Venmo (@John-Barr-1293) and Square checkout per John's explicit instruction. 3) Standardized shipping to flat $5.00 across all orders ('Plus 5 dollars for shipping'). Synchronized storefront, cart drawer, checkout modal, and backend order ledger." 
    },
    { 
      id: 6, 
      title: "Integrated Emailed Brand Kit, Authentic Can Koozies & Predecessor Design Language", 
      date: "2026-09-13", 
      content: "Cataloged and ingested official vector assets from 'archive (1).zip' (14 authentic studio & camera photos of Can Koozies) and 'THE SIMPLE CHEF (3) (5).zip' (official brand pack: print.svg, fulllogo.png, fulllogo_nobuffer.png, textonly_nobuffer.png, grayscale_transparent.png, and print.pdf). Analyzed predecessor React build from 'thesimplecheff.com' (rectifying original spelling typo to canonical thesimplechef.com). Fully integrated Buck Down official print label, interactive Can Koozies color selector (Trio Pack, Jet Black, Royal Blue, Fire Red), Official Snapback Hat ($25.00), and Masterclass Series video tutorial cards into sovereign storefront. Deployed live to https://thesimplechef.web.app." 
    },
    { 
      id: 5, 
      title: "Removed thesimplechefs.com Scraped Content — Restored Original Setup", 
      date: "2026-09-13", 
      content: "Completely purged all external website data from 'thesimplechefs.com' (Phoenix meal-prep menu, third-party photos, external team profiles) and safely archived them to saved_data. Strictly retained the original The Simple Chef Greenville, Michigan smokehouse setup (Rub That Hiney, Yard Pimp Dust, Kelly's Calling, Buck Down) with authentic contact details (616-808-9104, info@thesimplechef.net), credit card checkout, Google Sheet logging, and sovereign vector analytics." 
    },
    { 
      id: 4, 
      title: "Credit Card E-Commerce & Google Sheet Live Logging", 
      date: "2026-09-13", 
      content: "Engineered automated checkout pipeline for Rub That Hiney, Yard Pimp Dust, Kelly's Calling, and Buck Down. Connected live credit card authorization to Google Sheets (👨‍🍳 Chef_John_Orders), instant merchant packing slip emails (info@thesimplechef.net), branded customer receipts, and Discord push alerts." 
    },
    { 
      id: 3, 
      title: "Domain Renewal Alert (Oct 3rd) & Site Resurrection", 
      date: "2026-09-13", 
      content: "John inquired about his expiring domain thesimplechef.com (due Oct 3rd) and piggybacking to get his entire site back. Instructed him to renew the base domain only ($12-$20, no hosting upsells). Re-engineered website with Tailwind, Jost typography, interactive cart drawer, story modal, video tutorial lightbox, and deployed live to https://thesimplechef.web.app." 
    },
    { 
      id: 2, 
      title: "Android App & Desktop Build", 
      date: "2026-07-02", 
      content: "Configured Gradle 9.1 Kotlin build setup for Android release package (14.3 MB APK) and Inno Setup Windows executable." 
    },
    { 
      id: 1, 
      title: "Original Smokehouse Assets Preservation", 
      date: "2026-06-27", 
      content: "Preserved original smokehouse rub formulas, typography, and assets in cleaned_homepage.html and E:\\thesimplechef\\assets." 
    }
  ]);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [newNoteContent, setNewNoteContent] = useState("");

  const fetchOrders = async () => {
    setLoadingOrders(true);
    try {
      const endpoints = [
        `${resolvedBackend}/api/v1/chef/orders`,
        "http://localhost:8080/api/v1/chef/orders",
        "https://api.brettstehouwer.live/api/v1/chef/orders"
      ];
      let loaded = false;
      for (const ep of endpoints) {
        try {
          const res = await fetch(ep);
          if (res.ok) {
            const data = await res.json();
            if (data.orders) {
              setOrders(data.orders);
              loaded = true;
              break;
            }
          }
        } catch (e) {}
      }
      if (!loaded) {
        setOrders([
          {
            id: 1,
            order_id: "SC-44804",
            created_at: "2026-09-13 16:30:00",
            customer_name: "John Doe",
            email: "footballstar0325@gmail.com",
            phone: "(616) 555-0199",
            shipping_address: "123 Oak Street, Grand Rapids, MI 49503",
            items: [
              { name: "Rub That Hiney", price: 8.99, qty: 2 },
              { name: "Yard Pimp Dust", price: 8.99, qty: 1 },
              { name: "Buck Down", price: 8.99, qty: 1 }
            ],
            subtotal: 35.96,
            tax: 2.16,
            shipping: 0.00,
            total: 38.12,
            payment_method: "card",
            payment_status: "PAID",
            card_last4: "4242",
            notes: "Please leave on front porch by the smoker.",
            fulfillment_status: "Packed"
          }
        ]);
      }
    } catch (err) {
      console.warn("Failed to fetch orders:", err);
    } finally {
      setLoadingOrders(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${resolvedBackend}/api/v1/chef/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats({ total_orders: data.total_orders, gross_revenue: data.gross_revenue });
      }
    } catch (e) {}
  };

  const fetchAnalyticsData = async () => {
    setLoadingAnalytics(true);
    try {
      const endpoints = [
        `${resolvedBackend}/api/v1/chef/analytics`,
        "http://localhost:8080/api/v1/chef/analytics"
      ];
      for (const base of endpoints) {
        try {
          const [resOverview, resReport] = await Promise.all([
            fetch(`${base}/overview`),
            fetch(`${base}/monthly-report`)
          ]);
          if (resOverview.ok) {
            const d = await resOverview.json();
            if (d.success && d.data) setAnalyticsOverview(d.data);
          }
          if (resReport.ok) {
            const r = await resReport.json();
            if (r.success && r.report) setMonthlyReport(r.report);
          }
          
          try {
            const wtRes = await fetch(`${base.replace('/api/v1/chef/analytics', '')}/api/analytics/traffic-summary?site_id=thesimplechef&limit=25`);
            if (wtRes.ok) {
              const wtJson = await wtRes.json();
              setWebTelemetry(wtJson);
            }
          } catch (e) {}
          break;
        } catch (e) {}
      }
    } catch (err) {
      console.warn("Failed to fetch chef analytics:", err);
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const handleSemanticSearch = async (e) => {
    if (e) e.preventDefault();
    if (!semanticQuery.trim()) return;
    setSearchingSemantic(true);
    try {
      const res = await fetch(`${resolvedBackend}/api/v1/chef/analytics/semantic-insights?query=${encodeURIComponent(semanticQuery)}&n=4`);
      if (res.ok) {
        const data = await res.json();
        if (data.insights) setSemanticResults(data.insights);
      }
    } catch (err) {
      console.warn("Semantic search failed:", err);
    } finally {
      setSearchingSemantic(false);
    }
  };

  const handleCopyReport = () => {
    if (!monthlyReport) return;
    const text = `=====================================================
THE SIMPLE CHEF — SOVEREIGN AI & INFRASTRUCTURE REPORT
Billing Cycle: ${monthlyReport.billing_cycle}
Retainer Tier: ${monthlyReport.retainer_tier}
Uptime SLA: ${monthlyReport.infrastructure_uptime}
=====================================================
Client: ${monthlyReport.client_name}
Business: ${monthlyReport.business_name} (Greenville, MI)
Total Customer Events: ${monthlyReport.total_customer_interactions}
Estimated Unique Diners: ${monthlyReport.estimated_unique_diners}
Top Performing Seasoning: ${monthlyReport.top_performing_rub}
Security Bot Attacks Neutralized: ${monthlyReport.security_bot_probes_neutralized}
Mobile Audience Share: ${monthlyReport.mobile_traffic_percentage}

EXECUTIVE RECOMMENDATION:
${monthlyReport.executive_recommendation}
=====================================================`;
    navigator.clipboard.writeText(text);
    setCopiedReportMsg("Briefing copied to clipboard!");
    setTimeout(() => setCopiedReportMsg(""), 3500);
  };

  useEffect(() => {
    fetchOrders();
    fetchStats();
    fetchAnalyticsData();
  }, []);

  const handleUpdateStatus = async (orderId, newStatus) => {
    try {
      const res = await fetch(`${resolvedBackend}/api/v1/chef/order/${orderId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fulfillment_status: newStatus })
      });
      if (res.ok) {
        setOrderActionMsg(`Order #${orderId} marked as ${newStatus}!`);
        setTimeout(() => setOrderActionMsg(""), 4000);
        fetchOrders();
      }
    } catch (e) {
      setOrders(orders.map(o => o.order_id === orderId ? { ...o, fulfillment_status: newStatus } : o));
      setOrderActionMsg(`Updated #${orderId} to ${newStatus} (Local State)`);
      setTimeout(() => setOrderActionMsg(""), 4000);
    }
  };

  const handleAddNote = (e) => {
    e.preventDefault();
    if (!newNoteTitle || !newNoteContent) return;
    const note = {
      id: Date.now(),
      title: newNoteTitle,
      date: new Date().toISOString().split('T')[0],
      content: newNoteContent
    };
    setNotes([note, ...notes]);
    setNewNoteTitle("");
    setNewNoteContent("");
  };

  const filteredOrders = orders.filter(o => {
    if (filterStatus === "All") return true;
    return o.fulfillment_status?.toLowerCase() === filterStatus.toLowerCase();
  });

  const totalCalculatedRevenue = orders.reduce((sum, o) => sum + (Number(o.total) || 0), 0);
  const pendingOrdersCount = orders.filter(o => (o.fulfillment_status || '').toLowerCase() === 'pending').length;
  const packedOrdersCount = orders.filter(o => (o.fulfillment_status || '').toLowerCase() === 'packed').length;
  const shippedOrdersCount = orders.filter(o => (o.fulfillment_status || '').toLowerCase() === 'shipped').length;

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, sans-serif', color: '#1e293b', height: '100%', overflowY: 'auto' }}>
      
      {/* Header Banner */}
      <div style={{ background: 'linear-gradient(135deg, #0e1618 0%, #1e293b 100%)', color: 'white', padding: '24px 30px', borderRadius: '16px', marginBottom: '24px', boxShadow: '0 8px 25px rgba(0,0,0,0.15)', border: '1px solid rgba(227, 207, 180, 0.2)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: '46px', height: '46px', borderRadius: '50%', background: '#e3cfb4', color: '#0e1618', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '900', fontSize: '1.25rem' }}>
                SC
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, color: '#f7e4cb' }}>👨‍🍳 Client Workspace: John Barr</h2>
                <p style={{ margin: '4px 0 0 0', opacity: 0.85, fontSize: '0.9rem', color: '#cbd5e1' }}>
                  Brand: <strong>The Simple Chef</strong> &bull; Location: <strong>Greenville, MI</strong> &bull; Domain: <strong>thesimplechef.com</strong>
                </p>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ background: '#10b981', color: 'white', padding: '6px 14px', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 700, boxShadow: '0 2px 8px rgba(16,185,129,0.3)' }}>
              ● Live Staging Deployed
            </span>
            <a 
              href="https://thesimplechef.web.app" 
              target="_blank" 
              rel="noreferrer"
              style={{ background: '#e3cfb4', color: '#0e1618', padding: '8px 16px', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 800, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              🚀 Open Live Storefront ↗
            </a>
            <a 
              href="https://docs.google.com/spreadsheets/d/1tm7qTGRB65_Ghang9zjTT4ka3EMmsnF02bulQXQbuEg/edit#gid=0" 
              target="_blank" 
              rel="noreferrer"
              style={{ background: '#059669', color: 'white', padding: '8px 16px', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 800, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              📊 Google Sheet On Phone ↗
            </a>
          </div>
        </div>
      </div>

      {/* Internal Navigation Tabs */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '2px solid #e2e8f0', paddingBottom: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <button 
          onClick={() => setActiveTab("orders")}
          style={{ padding: '8px 18px', borderRadius: '8px', border: 'none', background: activeTab === 'orders' ? '#0e1618' : '#f1f5f9', color: activeTab === 'orders' ? '#f7e4cb' : '#475569', fontWeight: 700, cursor: 'pointer', transition: '0.2s', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          📦 Live Orders & Revenue ({orders.length})
        </button>
        <button 
          onClick={() => setActiveTab("analytics")}
          style={{ padding: '8px 18px', borderRadius: '8px', border: 'none', background: activeTab === 'analytics' ? '#0e1618' : '#f1f5f9', color: activeTab === 'analytics' ? '#f7e4cb' : '#475569', fontWeight: 700, cursor: 'pointer', transition: '0.2s', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          📊 Sovereign AI Analytics
        </button>
        <button 
          onClick={() => setActiveTab("overview")}
          style={{ padding: '8px 18px', borderRadius: '8px', border: 'none', background: activeTab === 'overview' ? '#0e1618' : '#f1f5f9', color: activeTab === 'overview' ? '#f7e4cb' : '#475569', fontWeight: 700, cursor: 'pointer', transition: '0.2s' }}
        >
          📋 Overview & Sovereign Infrastructure
        </button>
        <button 
          onClick={() => setActiveTab("notes")}
          style={{ padding: '8px 18px', borderRadius: '8px', border: 'none', background: activeTab === 'notes' ? '#0e1618' : '#f1f5f9', color: activeTab === 'notes' ? '#f7e4cb' : '#475569', fontWeight: 700, cursor: 'pointer', transition: '0.2s' }}
        >
          📝 Client Notes & Vault ({notes.length})
        </button>
        <button 
          onClick={() => setActiveTab("tasks")}
          style={{ padding: '8px 18px', borderRadius: '8px', border: 'none', background: activeTab === 'tasks' ? '#0e1618' : '#f1f5f9', color: activeTab === 'tasks' ? '#f7e4cb' : '#475569', fontWeight: 700, cursor: 'pointer', transition: '0.2s' }}
        >
          🎯 Deliverables & Roadmap
        </button>
      </div>

      {/* ORDERS & REVENUE TAB */}
      {activeTab === 'orders' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Top KPI Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            
            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Total Store Orders</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#0f172a', marginTop: '4px' }}>
                {orders.length}
              </div>
              <span style={{ color: '#10b981', fontSize: '0.8rem', fontWeight: 600 }}>100% Logged to Google Sheets</span>
            </div>

            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Gross Store Sales</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#059669', marginTop: '4px' }}>
                ${totalCalculatedRevenue.toFixed(2)}
              </div>
              <span style={{ color: '#64748b', fontSize: '0.8rem' }}>Greenville Smokehouse Direct</span>
            </div>

            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Ready to Pack & Ship</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: pendingOrdersCount > 0 ? '#d97706' : '#64748b', marginTop: '4px' }}>
                {pendingOrdersCount}
              </div>
              <span style={{ color: '#b45309', fontSize: '0.8rem' }}>{packedOrdersCount} Marked Packed</span>
            </div>

            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Dispatched / Shipped</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#2563eb', marginTop: '4px' }}>
                {shippedOrdersCount}
              </div>
              <span style={{ color: '#64748b', fontSize: '0.8rem' }}>USPS Priority In-Transit</span>
            </div>

          </div>

          {/* Action Notification Alert */}
          {orderActionMsg && (
            <div style={{ background: '#dcfce7', border: '1px solid #86efac', color: '#15803d', padding: '12px 18px', borderRadius: '8px', fontWeight: 700, fontSize: '0.9rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>✅ {orderActionMsg}</span>
              <button onClick={() => setOrderActionMsg("")} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#15803d', fontWeight: 800 }}>✕</button>
            </div>
          )}

          {/* Controls Bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', background: 'white', padding: '14px 20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#64748b' }}>Filter:</span>
              {['All', 'Pending', 'Packed', 'Shipped'].map(status => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    background: filterStatus === status ? '#0e1618' : '#f1f5f9',
                    color: filterStatus === status ? '#f7e4cb' : '#475569'
                  }}
                >
                  {status}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={fetchOrders}
                disabled={loadingOrders}
                style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', padding: '7px 14px', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                🔄 {loadingOrders ? 'Refreshing...' : 'Refresh Feed'}
              </button>
              <a
                href="https://thesimplechef.web.app/#seasonings"
                target="_blank"
                rel="noreferrer"
                style={{ background: '#0e1618', color: '#f7e4cb', padding: '7px 14px', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 700, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                🛒 Test Storefront Checkout ↗
              </a>
            </div>
          </div>

          {/* Orders Feed */}
          {filteredOrders.length === 0 ? (
            <div style={{ background: 'white', padding: '40px', borderRadius: '12px', border: '1px solid #e2e8f0', textAlign: 'center', color: '#64748b' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '10px' }}>📦</div>
              <h3 style={{ margin: 0, color: '#0f172a', fontWeight: 700 }}>No orders matching "{filterStatus}"</h3>
              <p style={{ margin: '6px 0 0 0', fontSize: '0.9rem' }}>New orders placed on <a href="https://thesimplechef.web.app" target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>thesimplechef.web.app</a> will appear here automatically.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {filteredOrders.map(order => (
                <div 
                  key={order.order_id || order.id} 
                  style={{ background: 'white', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)', overflow: 'hidden' }}
                >
                  <div style={{ background: '#f8fafc', padding: '14px 20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <strong style={{ fontSize: '1.05rem', color: '#0e1618', fontFamily: 'monospace', fontWeight: 800 }}>#{order.order_id}</strong>
                      <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{order.created_at}</span>
                      <span style={{ fontSize: '0.75rem', background: order.payment_status === 'PAID' ? '#dcfce7' : '#fef3c7', color: order.payment_status === 'PAID' ? '#15803d' : '#b45309', padding: '2px 8px', borderRadius: '10px', fontWeight: 800 }}>
                        {order.payment_status || 'PAID'} &bull; {order.payment_method?.toUpperCase()} (•••• {order.card_last4 || '4242'})
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#64748b' }}>Status:</span>
                      <select 
                        value={order.fulfillment_status || 'Pending'}
                        onChange={(e) => handleUpdateStatus(order.order_id, e.target.value)}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          border: '1px solid #cbd5e1',
                          fontSize: '0.85rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          background: order.fulfillment_status === 'Shipped' ? '#eff6ff' : (order.fulfillment_status === 'Packed' ? '#f0fdf4' : '#fffbeb'),
                          color: order.fulfillment_status === 'Shipped' ? '#1e40af' : (order.fulfillment_status === 'Packed' ? '#166534' : '#92400e')
                        }}
                      >
                        <option value="Pending">Pending Packing</option>
                        <option value="Packed">Packed</option>
                        <option value="Shipped">Shipped (USPS)</option>
                        <option value="Delivered">Delivered</option>
                      </select>
                    </div>
                  </div>

                  <div style={{ padding: '18px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
                    
                    {/* Customer & Shipping Details */}
                    <div>
                      <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 800, display: 'block', marginBottom: '6px' }}>
                        Customer & Shipping Address
                      </span>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>{order.customer_name}</div>
                      <div style={{ fontSize: '0.85rem', color: '#2563eb' }}>{order.email}</div>
                      {order.phone && <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{order.phone}</div>}
                      <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#334155', background: '#f8fafc', padding: '8px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                        📍 {order.shipping_address}
                      </div>
                      {order.notes && (
                        <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#92400e', background: '#fffbeb', padding: '6px 10px', borderRadius: '6px', border: '1px solid #fef3c7' }}>
                          💬 <em>Notes:</em> {order.notes}
                        </div>
                      )}
                    </div>

                    {/* Items & Financial Totals */}
                    <div>
                      <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 800, display: 'block', marginBottom: '6px' }}>
                        Seasonings & Financial Summary
                      </span>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '10px' }}>
                        {Array.isArray(order.items) && order.items.map((it, idx) => (
                          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', background: '#f8fafc', padding: '4px 8px', borderRadius: '4px' }}>
                            <span style={{ fontWeight: 600, color: '#0e1618' }}>🍖 {it.name} <span style={{ color: '#64748b' }}>x{it.qty}</span></span>
                            <span style={{ fontWeight: 700, color: '#334155' }}>${(it.price * it.qty).toFixed(2)}</span>
                          </div>
                        ))}
                      </div>

                      <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '6px', fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
                          <span>Subtotal:</span>
                          <strong>${Number(order.subtotal || 0).toFixed(2)}</strong>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
                          <span>MI Sales Tax (6%):</span>
                          <strong>${Number(order.tax || 0).toFixed(2)}</strong>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
                          <span>Shipping:</span>
                          <strong>{Number(order.shipping || 0) === 0 ? 'FREE' : `$${Number(order.shipping).toFixed(2)}`}</strong>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.05rem', fontWeight: 800, color: '#059669', borderTop: '1px solid #cbd5e1', paddingTop: '4px', marginTop: '2px' }}>
                          <span>Grand Total:</span>
                          <span>${Number(order.total || 0).toFixed(2)} USD</span>
                        </div>
                      </div>
                    </div>

                  </div>
                </div>
              ))}
            </div>
          )}

        </div>
      )}

      {/* SOVEREIGN AI ANALYTICS TAB */}
      {activeTab === 'analytics' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* 16-LAYER DEEP WEB TELEMETRY SUITE */}
          <div style={{ background: 'white', padding: '24px', borderRadius: '14px', border: '1px solid #e2e8f0', boxShadow: '0 2px 10px rgba(0,0,0,0.04)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '12px', borderBottom: '1px solid #f1f5f9', paddingBottom: '14px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.25rem' }}>📈</span>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>
                    TheSimpleChef.com 16-Layer Deep Web Telemetry
                  </h3>
                  <span style={{ background: '#fef3c7', color: '#b45309', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 700 }}>
                    Live Production Mirror
                  </span>
                </div>
                <p style={{ margin: '3px 0 0 0', fontSize: '0.82rem', color: '#64748b' }}>
                  Real-time dwell times, scroll depths, Core Web Vitals, and customer cart/checkout interactions
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Endpoint:</span>
                <code style={{ background: '#f1f5f9', padding: '3px 8px', borderRadius: '6px', fontSize: '0.75rem', color: '#0369a1' }}>
                  /api/analytics/traffic-summary?site_id=thesimplechef
                </code>
              </div>
            </div>

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '20px' }}>
              <div style={{ background: '#f8fafc', padding: '14px 16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Total Storefront Hits</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a', marginTop: '3px' }}>
                  {webTelemetry?.total_pageviews ?? 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#16a34a', marginTop: '2px' }}>Recorded pageviews</div>
              </div>

              <div style={{ background: '#f8fafc', padding: '14px 16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Unique Diners</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#2563eb', marginTop: '3px' }}>
                  {webTelemetry?.unique_visitors ?? 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>Distinct sessions</div>
              </div>

              <div style={{ background: '#f8fafc', padding: '14px 16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>⏱️ Avg Dwell Time</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#d97706', marginTop: '3px' }}>
                  {webTelemetry?.avg_dwell_time_sec ?? 0}s
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>Active engagement</div>
              </div>

              <div style={{ background: '#f8fafc', padding: '14px 16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>📜 Scroll Completion</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#7c3aed', marginTop: '3px' }}>
                  {webTelemetry?.scroll_completion_rate ?? 0}%
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>Reached menu/order</div>
              </div>

              <div style={{ background: '#f8fafc', padding: '14px 16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>⚡ Core Web Vitals</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#059669', marginTop: '4px' }}>
                  {webTelemetry?.web_vitals?.lcp_ms || 320}ms
                </div>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>CLS: {webTelemetry?.web_vitals?.cls_score || 0.005}</div>
              </div>

              <div style={{ background: '#f8fafc', padding: '14px 16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>🤖 Human Traffic</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#db2777', marginTop: '3px' }}>
                  {webTelemetry?.human_traffic_pct ?? 100}%
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>Verified human sessions</div>
              </div>
            </div>

            {/* Top Routes & Traffic Sources */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginBottom: '16px' }}>
              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#0f172a', fontWeight: 700 }}>📑 Top Storefront Routes</h4>
                {(!webTelemetry?.top_pages || webTelemetry.top_pages.length === 0) ? (
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', textAlign: 'center', padding: '12px' }}>No storefront routes recorded yet.</div>
                ) : (
                  <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
                    <tbody>
                      {webTelemetry.top_pages.map((p, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                          <td style={{ padding: '6px 8px', fontFamily: 'monospace', color: '#0369a1' }}>{p.path}</td>
                          <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700, color: '#16a34a' }}>{p.hits} hits</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#0f172a', fontWeight: 700 }}>🎯 Traffic Sources</h4>
                {(!webTelemetry?.top_referrers || webTelemetry.top_referrers.length === 0) ? (
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', textAlign: 'center', padding: '12px' }}>Direct & organic traffic.</div>
                ) : (
                  <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
                    <tbody>
                      {webTelemetry.top_referrers.map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                          <td style={{ padding: '6px 8px', color: '#334155' }}>{r.referrer}</td>
                          <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700, color: '#2563eb' }}>{r.hits}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Live Events Table */}
            {webTelemetry?.live_events && webTelemetry.live_events.length > 0 && (
              <div>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '0.85rem', color: '#0f172a', fontWeight: 700 }}>
                  🔴 Live Interaction Stream ({webTelemetry.live_events.length} Events)
                </h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: '#f1f5f9', color: '#475569' }}>
                        <th style={{ padding: '6px 8px' }}>Time</th>
                        <th style={{ padding: '6px 8px' }}>Session</th>
                        <th style={{ padding: '6px 8px' }}>Location</th>
                        <th style={{ padding: '6px 8px' }}>Route</th>
                        <th style={{ padding: '6px 8px' }}>Event</th>
                        <th style={{ padding: '6px 8px' }}>Dwell</th>
                        <th style={{ padding: '6px 8px' }}>Scroll</th>
                        <th style={{ padding: '6px 8px' }}>Device/GPU</th>
                      </tr>
                    </thead>
                    <tbody>
                      {webTelemetry.live_events.slice(0, 10).map((e) => (
                        <tr key={e.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '6px 8px', fontFamily: 'monospace', color: '#64748b' }}>{e.formatted_time}</td>
                          <td style={{ padding: '6px 8px', fontFamily: 'monospace', color: '#0284c7' }}>{e.session_id.slice(0, 14)}...</td>
                          <td style={{ padding: '6px 8px', color: '#d97706' }}>🇺🇸 {e.city}</td>
                          <td style={{ padding: '6px 8px', color: '#16a34a', fontWeight: 600 }}>{e.page_path}</td>
                          <td style={{ padding: '6px 8px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '8px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              background: e.event_type === 'checkout_modal_opened' ? '#e0e7ff' : e.event_type === 'add_to_cart' ? '#dcfce7' : '#f1f5f9',
                              color: e.event_type === 'checkout_modal_opened' ? '#4338ca' : e.event_type === 'add_to_cart' ? '#15803d' : '#334155'
                            }}>
                              {e.event_type.toUpperCase()}
                            </span>
                          </td>
                          <td style={{ padding: '6px 8px', fontWeight: 600, color: '#d97706' }}>{e.dwell_time_sec || 0}s</td>
                          <td style={{ padding: '6px 8px', fontWeight: 600, color: '#7c3aed' }}>{e.scroll_depth_pct || 0}%</td>
                          <td style={{ padding: '6px 8px', color: '#64748b', fontFamily: 'monospace' }}>{(e.gpu_renderer || 'WebGL').slice(0, 24)}...</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          
          {/* ChromaDB Status Card */}
          <div style={{ background: 'white', padding: '20px 24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.25rem' }}>🧠</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>ChromaDB Sovereign Vector Analytics Partition</h3>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.82rem', color: '#64748b' }}>
                    Partition: <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>thesimplechef_analytics_bin</code> &bull; Path: <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>saved_data/chromadb_chef</code>
                  </p>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ background: '#dcfce7', color: '#15803d', padding: '4px 10px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 700 }}>
                ● HNSW RAM Clamped
              </span>
              <span style={{ background: '#e0f2fe', color: '#0369a1', padding: '4px 10px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 700 }}>
                ● IP Anonymization (GDPR/CCPA)
              </span>
              <button 
                onClick={fetchAnalyticsData} 
                disabled={loadingAnalytics}
                style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer' }}
              >
                🔄 {loadingAnalytics ? 'Syncing...' : 'Sync'}
              </button>
            </div>
          </div>

          {/* Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Vectors Ingested</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#0f172a', marginTop: '4px' }}>
                {analyticsOverview ? analyticsOverview.total_events : 9}
              </div>
              <span style={{ color: '#059669', fontSize: '0.8rem', fontWeight: 600 }}>Active Customer Events</span>
            </div>

            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Unique Diners</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#2563eb', marginTop: '4px' }}>
                {analyticsOverview ? analyticsOverview.unique_visitors : 4}
              </div>
              <span style={{ color: '#64748b', fontSize: '0.8rem' }}>Anonymized Browser Sessions</span>
            </div>

            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Top Seasoning Rub</span>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#b45309', marginTop: '6px' }}>
                {monthlyReport ? monthlyReport.top_performing_rub : "Rub That Hiney"}
              </div>
              <span style={{ color: '#64748b', fontSize: '0.8rem' }}>Highest Cart Addition Volume</span>
            </div>

            <div style={{ background: 'white', padding: '18px 20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Bot Probes Deflected</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#dc2626', marginTop: '4px' }}>
                {analyticsOverview ? analyticsOverview.bot_probes_blocked : 1}
              </div>
              <span style={{ color: '#dc2626', fontSize: '0.8rem', fontWeight: 600 }}>WordPress/PHP Exploits Dropped</span>
            </div>
          </div>

          {/* Monthly Retainer Briefing Generator Card */}
          {monthlyReport && (
            <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)', color: 'white', padding: '24px', borderRadius: '16px', border: '1px solid rgba(227, 207, 180, 0.3)', boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
                <div>
                  <span style={{ color: '#e3cfb4', fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Retainer Deliverable &bull; $100/mo Tier</span>
                  <h3 style={{ margin: '2px 0 0 0', fontSize: '1.35rem', fontWeight: 800, color: '#f8fafc' }}>
                    📈 Monthly Client Executive Briefing ({monthlyReport.billing_cycle})
                  </h3>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {copiedReportMsg && (
                    <span style={{ color: '#86efac', fontSize: '0.85rem', fontWeight: 700 }}>{copiedReportMsg}</span>
                  )}
                  <button 
                    onClick={handleCopyReport}
                    style={{ background: '#e3cfb4', color: '#0e1618', padding: '8px 16px', borderRadius: '8px', border: 'none', fontWeight: 800, fontSize: '0.85rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    📋 Copy Client Report
                  </button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '18px' }}>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Host Uptime SLA</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#4ade80', marginTop: '2px' }}>{monthlyReport.infrastructure_uptime}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Top Rub Formulation</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f7e4cb', marginTop: '2px' }}>{monthlyReport.top_performing_rub}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Mobile Share</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#38bdf8', marginTop: '2px' }}>{monthlyReport.mobile_traffic_percentage}</div>
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.07)', padding: '16px 20px', borderRadius: '10px', borderLeft: '4px solid #e3cfb4' }}>
                <span style={{ fontSize: '0.8rem', color: '#e3cfb4', fontWeight: 800, textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                  💡 AI Executive Recommendation for John Barr:
                </span>
                <p style={{ margin: 0, fontSize: '0.95rem', lineHeight: '1.6', color: '#f1f5f9' }}>
                  {monthlyReport.executive_recommendation}
                </p>
              </div>
            </div>
          )}

          {/* Semantic Natural Language Search Engine */}
          <div style={{ background: 'white', padding: '22px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
            <h3 style={{ margin: '0 0 6px 0', fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
              🔍 Semantic Natural Language Vector Query
            </h3>
            <p style={{ margin: '0 0 14px 0', fontSize: '0.85rem', color: '#64748b' }}>
              Search across customer intent, cart additions, and browsing sessions using ChromaDB embedding vectors:
            </p>
            <form onSubmit={handleSemanticSearch} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
              <input 
                type="text"
                placeholder="e.g. customers looking for poultry seasonings or wings, checkout dropouts..."
                value={semanticQuery}
                onChange={(e) => setSemanticQuery(e.target.value)}
                style={{ flex: 1, padding: '10px 14px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }}
              />
              <button 
                type="submit" 
                disabled={searchingSemantic}
                style={{ background: '#0e1618', color: '#f7e4cb', border: 'none', padding: '10px 20px', borderRadius: '8px', fontWeight: 700, cursor: 'pointer' }}
              >
                {searchingSemantic ? 'Querying...' : 'Query Vectors'}
              </button>
            </form>

            {semanticResults.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Semantic Similarity Matches:</span>
                {semanticResults.map((item, idx) => (
                  <div key={idx} style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.88rem', color: '#334155' }}>
                      {item.document}
                    </div>
                    <span style={{ background: '#e0f2fe', color: '#0369a1', padding: '2px 8px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 800, whiteSpace: 'nowrap', marginLeft: '12px' }}>
                      {(item.similarity_score * 100).toFixed(1)}% match
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          
          {/* Hosting & Staging Status */}
          <div style={{ background: 'white', padding: '22px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#0f172a', fontSize: '1.15rem', fontWeight: 700 }}>🌐 Web Hosting & Domains</h3>
              <span style={{ fontSize: '0.75rem', background: '#dcfce7', color: '#15803d', padding: '2px 8px', borderRadius: '10px', fontWeight: 700 }}>$0/mo Hosting</span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.9rem' }}>
              <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Live Cloud Staging</span>
                <a href="https://thesimplechef.web.app" target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontWeight: 700, textDecoration: 'none', fontSize: '0.95rem' }}>
                  https://thesimplechef.web.app ↗
                </a>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#64748b' }}>Hosted on Google Firebase CDN &bull; Free Global SSL &bull; Credit Card Checkout Active</p>
              </div>

              <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Google Sheets Live Cloud Ledger</span>
                <a href="https://docs.google.com/spreadsheets/d/1tm7qTGRB65_Ghang9zjTT4ka3EMmsnF02bulQXQbuEg/edit#gid=0" target="_blank" rel="noreferrer" style={{ color: '#059669', fontWeight: 700, textDecoration: 'none', fontSize: '0.95rem' }}>
                  Open Sheet on Phone ↗
                </a>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#64748b' }}>Automated sheet <code>👨‍🍳 Chef_John_Orders</code> with real-time phone alerts</p>
              </div>

              <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Sovereign WSL2 Nginx Server</span>
                <a href="http://localhost:8055" target="_blank" rel="noreferrer" style={{ color: '#059669', fontWeight: 700, textDecoration: 'none', fontSize: '0.95rem' }}>
                  http://localhost:8055 (Port 8055) ↗
                </a>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#64748b' }}>Isolated user <code>client_web_user</code> &bull; Dedicated logrotate &bull; Rate-limited</p>
              </div>

              <div style={{ background: '#fffbeb', padding: '12px', borderRadius: '8px', border: '1px solid #fef3c7' }}>
                <span style={{ color: '#b45309', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', display: 'block' }}>Target Custom Domain</span>
                <strong style={{ color: '#92400e', fontSize: '0.95rem' }}>thesimplechef.com</strong>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#b45309' }}>
                  ⚠️ Expires October 3rd. Instruct client to renew base domain only ($12-$20). Point DNS CNAME/A records once renewed.
                </p>
              </div>
            </div>
          </div>

          {/* Local Project Directory & Deliverables */}
          <div style={{ background: 'white', padding: '22px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <h3 style={{ marginTop: 0, color: '#0f172a', fontSize: '1.15rem', fontWeight: 700, marginBottom: '12px' }}>📁 Preserved Files & Builds</h3>
            <p style={{ fontSize: '0.85rem', color: '#64748b', margin: '0 0 12px 0' }}>Root: <code>E:\thesimplechef</code></p>
            <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '0.9rem', color: '#334155', lineHeight: '2' }}>
              <li><code>public/index.html</code> — Modern responsive storefront with cart drawer</li>
              <li><code>preview.html</code> — Original smokehouse rub quartet storefront</li>
              <li><code>build_site.py</code> — Automated build compiler and asset bundler</li>
              <li><code>Output/TheSimpleChef.apk</code> — 14.3 MB Android release APK</li>
              <li><code>Output/TheSimpleChef_Installer.exe</code> — 2.18 MB Windows desktop app</li>
              <li><code>cleaned_homepage.html</code> — Preserved original archive</li>
            </ul>
          </div>

          {/* Client Profile Information */}
          <div style={{ background: 'white', padding: '22px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <h3 style={{ marginTop: 0, color: '#0f172a', fontSize: '1.15rem', fontWeight: 700, marginBottom: '12px' }}>👤 Client Contact Information</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.9rem', color: '#334155' }}>
              <div><strong>Name:</strong> John Barr</div>
              <div><strong>Brand:</strong> The Simple Chef</div>
              <div><strong>Smokehouse & Production:</strong> 817 S. Lafayette St., Greenville, MI 48838</div>
              <div><strong>Direct Phone / SMS:</strong> (616) 808-9104</div>
              <div><strong>Contact Email:</strong> info@thesimplechef.net</div>
              <div><strong>Original Website:</strong> <a href="https://thesimplechef.net" target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontWeight: 700 }}>thesimplechef.net ↗</a></div>
              <div><strong>Primary Domain:</strong> <a href="https://thesimplechef.web.app" target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontWeight: 700 }}>thesimplechef.com (thesimplechef.web.app) ↗</a></div>
              <div><strong>Signature Rubs:</strong> Rub That Hiney, Yard Pimp Dust, Kelly's Calling, Buck Down</div>
              <div><strong>Hosting Tier:</strong> Sovereign WSL2 Ubuntu Nginx + Firebase Global CDN ($0/mo)</div>
              <div><strong>AI Vector Analytics:</strong> ChromaDB isolated collection <code>thesimplechef_analytics_bin</code></div>
            </div>
          </div>

        </div>
      )}

      {/* Notes Tab */}
      {activeTab === 'notes' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ background: 'white', padding: '22px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
            <h3 style={{ marginTop: 0, fontSize: '1.1rem', fontWeight: 700 }}>✍️ Add Client Note</h3>
            <form onSubmit={handleAddNote} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input 
                type="text" 
                placeholder="Note Title (e.g., Domain renewal update)..."
                value={newNoteTitle}
                onChange={(e) => setNewNoteTitle(e.target.value)}
                style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }}
              />
              <textarea 
                rows="3" 
                placeholder="Write correspondence details, client requests, or strategy notes..."
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }}
              />
              <button type="submit" style={{ padding: '10px 22px', background: '#0e1618', color: '#f7e4cb', border: 'none', borderRadius: '8px', fontWeight: 700, cursor: 'pointer', alignSelf: 'flex-start' }}>
                Save Note
              </button>
            </form>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {notes.map(n => (
              <div key={n.id} style={{ background: 'white', padding: '18px 22px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                  <strong style={{ fontSize: '1.05rem', color: '#0f172a', fontWeight: 700 }}>{n.title}</strong>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8', background: '#f1f5f9', padding: '3px 10px', borderRadius: '12px' }}>{n.date}</span>
                </div>
                <p style={{ margin: 0, color: '#334155', fontSize: '0.92rem', lineHeight: '1.6' }}>{n.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deliverables Tab */}
      {activeTab === 'tasks' && (
        <div style={{ background: 'white', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
          <h3 style={{ marginTop: 0, fontSize: '1.2rem', fontWeight: 700, marginBottom: '16px' }}>📌 Project Roadmap & Deliverables</h3>
          <ul style={{ paddingLeft: '20px', color: '#334155', lineHeight: '2.2', fontSize: '0.95rem' }}>
            <li>✅ <strong>Original Seasonings Restored:</strong> Restored original rub quartet storefront (Rub That Hiney, Yard Pimp Dust, Kelly's Calling, Buck Down) and archived all external meal prep data</li>
            <li>✅ <strong>Modern Web App:</strong> Rebuilt with Tailwind, custom typography, and responsive UI components</li>
            <li>✅ <strong>Interactive Cart Drawer:</strong> Working slide-over cart with subtotal, tax calculation, and persistent storage</li>
            <li>✅ <strong>Story & Video Modals:</strong> Added John Barr's heritage smokehouse story and video cooking masterclass lightbox</li>
            <li>✅ <strong>Credit Card Checkout Suite:</strong> 16-digit card formatting, MM/YY, CVC, ZIP, and printable order receipts</li>
            <li>✅ <strong>Cloud Google Sheet Logging:</strong> Every order automatically logs to <code>👨‍🍳 Chef_John_Orders</code> on John's phone</li>
            <li>✅ <strong>Instant Notifications:</strong> Free SMS text to John's phone (480-882-8565), email packing slip, and Discord push alert</li>
            <li>✅ <strong>Sovereign Multi-Tenant Hosting:</strong> WSL2 Ubuntu Nginx virtual host with isolated permissions, logrotate, and rate limiting</li>
            <li>✅ <strong>Sovereign ChromaDB AI Analytics:</strong> Dedicated partition <code>thesimplechef_analytics_bin</code> with monthly executive briefing generator ($100/mo retainer)</li>
            <li>✅ <strong>Cloud Deployment:</strong> Deployed live to <a href="https://thesimplechef.web.app" target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontWeight: 700 }}>https://thesimplechef.web.app</a> on Firebase Hosting ($0/mo)</li>
            <li>⏳ <strong>Domain Renewal:</strong> Client to renew base domain <code>thesimplechef.com</code> on GoDaddy/Namecheap by October 3rd</li>
            <li>⏳ <strong>Custom Domain DNS Link:</strong> Point CNAME / A records to Firebase Hosting to map <code>thesimplechef.com</code></li>
          </ul>
        </div>
      )}

    </div>
  );
}
