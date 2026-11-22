/** @typedef {{id:string,title:string,description:string,due_date:string,due_time:string,priority:string,status:string,category:string,assigned_to:string,subtasks:{id:string,title:string,done:boolean}[]}} CalendarTask */
import { useState, useEffect, useCallback } from 'react';
import './collaborationService';

/** @param {{backendUrl?: string}} props */
export default function CalendarActionTasksTab({ backendUrl = 'http://127.0.0.1:8000' }) {
  const [tasks, setTasks] = useState(/** @returns {CalendarTask[]} */ () => {
    try {
      const cached = localStorage.getItem('aibs_calendar_tasks_backup');
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });
  const [stats, setStats] = useState({ total: 0, completed: 0, in_progress: 0, todo: 0, urgent: 0, overdue: 0, completion_rate: 0 });
  useState(false);
  const [viewMode, setViewMode] = useState('kanban'); // 'kanban' or 'list'
  const [filterTab, setFilterTab] = useState('all'); // 'all', 'today', 'week', 'overdue', 'completed'
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // AI Action Item Extractor State
  const [aiInput, setAiInput] = useState('');
  const [aiExtracting, setAiExtracting] = useState(false);
  const [aiSuccessMsg, setAiSuccessMsg] = useState('');

  // Task Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingTask, setEditingTask] = useState(/** @type {CalendarTask|null} */ (null));
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    due_date: new Date().toISOString().slice(0, 10),
    due_time: '12:00',
    priority: 'Medium',
    status: 'Todo',
    category: 'Screenplay & Writing',
    assigned_to: 'Brett',
    subtasks: /** @type {CalendarTask["subtasks"]} */ ([])
  });
  const [newSubtaskInput, setNewSubtaskInput] = useState('');

  const fetchTasksAndStats = useCallback(async () => {
    try {
      const [tasksRes, statsRes] = await Promise.all([
        fetch(`${backendUrl}/api/calendar/tasks`),
        fetch(`${backendUrl}/api/calendar/stats`)
      ]);

      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();
        setTasks(tasksData);
        try {
          localStorage.setItem('aibs_calendar_tasks_backup', JSON.stringify(tasksData));
        } catch {}
      }
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (err) {
      console.error('Failed to fetch tasks & stats:', err);
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchTasksAndStats();
  }, [fetchTasksAndStats]);

  // AI Extraction
  /** @param {import("react").FormEvent} e */
  const handleAiExtract = async (e) => {
    e.preventDefault();
    if (!aiInput.trim()) return;
    setAiExtracting(true);
    setAiSuccessMsg('');
    try {
      const res = await fetch(`${backendUrl}/api/calendar/tasks/ai-extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: aiInput })
      });
      if (res.ok) {
        const data = await res.json();
        setAiInput('');
        setAiSuccessMsg(`✨ Successfully extracted and scheduled ${data.count || 0} action items!`);
        setTimeout(() => setAiSuccessMsg(''), 5000);
        fetchTasksAndStats();
      } else {
        alert('AI Task Extraction encountered an error.');
      }
    } catch (err) {
      console.error(err);
      alert('Failed to connect to AI Task Extractor.');
    } finally {
      setAiExtracting(false);
    }
  };

  // Toggle Completion
  /** @param {string} taskId */
  const handleToggleTask = async (taskId) => {
    try {
      const res = await fetch(`${backendUrl}/api/calendar/tasks/${taskId}/toggle`, {
        method: 'PATCH'
      });
      if (res.ok) {
        fetchTasksAndStats();
      }
    } catch (err) {
      console.error('Failed to toggle task:', err);
    }
  };

  // Change Status (Kanban drag or click)
  /** @param {string} taskId @param {string} newStatus */
  const handleChangeStatus = async (taskId, newStatus) => {
    try {
      const res = await fetch(`${backendUrl}/api/calendar/tasks/${taskId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        fetchTasksAndStats();
      }
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  // Delete Task
  /** @param {string} taskId */
  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Delete this action item?')) return;
    try {
      const res = await fetch(`${backendUrl}/api/calendar/tasks/${taskId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchTasksAndStats();
      }
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
  };

  // Open Form
  /** @param {CalendarTask|null} task */
  const openTaskModal = (task = null) => {
    if (task) {
      setEditingTask(task);
      setFormData({
        title: task.title,
        description: task.description || '',
        due_date: task.due_date || new Date().toISOString().slice(0, 10),
        due_time: task.due_time || '12:00',
        priority: task.priority || 'Medium',
        status: task.status || 'Todo',
        category: task.category || 'Screenplay & Writing',
        assigned_to: task.assigned_to || 'Brett',
        subtasks: Array.isArray(task.subtasks) ? [...task.subtasks] : []
      });
    } else {
      setEditingTask(null);
      setFormData({
        title: '',
        description: '',
        due_date: new Date().toISOString().slice(0, 10),
        due_time: '12:00',
        priority: 'Medium',
        status: 'Todo',
        category: 'Screenplay & Writing',
        assigned_to: 'Brett',
        subtasks: /** @type {CalendarTask["subtasks"]} */ ([])
      });
    }
    setShowModal(true);
  };

  // Add Subtask to Form
  const handleAddSubtask = () => {
    if (!newSubtaskInput.trim()) return;
    setFormData(prev => ({
      ...prev,
      subtasks: [...prev.subtasks, { id: `st-${Date.now()}`, title: newSubtaskInput.trim(), done: false }]
    }));
    setNewSubtaskInput('');
  };

  /** @param {number} index */
  const handleToggleSubtaskInForm = (index) => {
    setFormData(prev => {
      const updated = [...prev.subtasks];
      updated[index] = { ...updated[index], done: !updated[index].done };
      return { ...prev, subtasks: updated };
    });
  };

  /** @param {number} index */
  const handleRemoveSubtaskInForm = (index) => {
    setFormData(prev => ({
      ...prev,
      subtasks: prev.subtasks.filter((_, i) => i !== index)
    }));
  };

  // Save Task
  /** @param {import("react").FormEvent} e */
  const handleSaveTask = async (e) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      alert('Task title is required.');
      return;
    }

    const url = editingTask
      ? `${backendUrl}/api/calendar/tasks/${editingTask.id}`
      : `${backendUrl}/api/calendar/tasks`;
    const method = editingTask ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setShowModal(false);
        fetchTasksAndStats();
      } else {
        alert('Failed to save task.');
      }
    } catch (err) {
      console.error(err);
      alert('Error connecting to backend.');
    }
  };

  // Filtering
  const todayStr = new Date().toISOString().slice(0, 10);
  const now = new Date();
  const endOfWeek = new Date(now);
  endOfWeek.setDate(now.getDate() + 7);
  const endOfWeekStr = endOfWeek.toISOString().slice(0, 10);

  const filteredTasks = tasks.filter(t => {
    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = t.title?.toLowerCase().includes(q);
      const matchDesc = t.description?.toLowerCase().includes(q);
      const matchCat = t.category?.toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchCat) return false;
    }

    // Category
    if (categoryFilter !== 'all' && t.category !== categoryFilter) return false;

    // Priority
    if (priorityFilter !== 'all' && t.priority !== priorityFilter) return false;

    // Filter Tabs
    if (filterTab === 'today') {
      return t.due_date === todayStr;
    }
    if (filterTab === 'week') {
      return t.due_date >= todayStr && t.due_date <= endOfWeekStr;
    }
    if (filterTab === 'overdue') {
      return t.due_date && t.due_date < todayStr && t.status !== 'Completed';
    }
    if (filterTab === 'completed') {
      return t.status === 'Completed';
    }

    return true;
  });

  const columns = [
    { id: 'Todo', label: 'To Do', icon: '📋', color: '#58a6ff' },
    { id: 'In Progress', label: 'In Progress', icon: '⏳', color: '#d29922' },
    { id: 'Completed', label: 'Completed', icon: '✅', color: '#238636' },
    { id: 'Deferred', label: 'Deferred / Later', icon: '⏸️', color: '#8b949e' }
  ];

  /** @param {string} p */
  const getPriorityBadge = (p) => {
    switch (p) {
      case 'Urgent':
        return <span style={{ backgroundColor: 'rgba(248,81,73,0.2)', color: '#f85149', border: '1px solid rgba(248,81,73,0.4)', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold' }}>🔴 Urgent</span>;
      case 'High':
        return <span style={{ backgroundColor: 'rgba(210,153,34,0.2)', color: '#e3b341', border: '1px solid rgba(210,153,34,0.4)', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold' }}>🟠 High</span>;
      case 'Medium':
        return <span style={{ backgroundColor: 'rgba(88,166,255,0.2)', color: '#58a6ff', border: '1px solid rgba(88,166,255,0.4)', padding: '2px 8px', borderRadius: '12px', fontSize: '11px' }}>🟡 Med</span>;
      default:
        return <span style={{ backgroundColor: 'rgba(139,148,158,0.2)', color: '#8b949e', border: '1px solid rgba(139,148,158,0.4)', padding: '2px 8px', borderRadius: '12px', fontSize: '11px' }}>🟢 Low</span>;
    }
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9', overflowY: 'auto' }}>
      
      {/* 1. Header & Metric Progress Ribbon */}
      <div style={{ padding: '16px 24px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ margin: 0, fontSize: '20px', color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>✅</span> Action Items & Task Suite
            </h2>
            <span style={{ fontSize: '12px', padding: '3px 8px', backgroundColor: '#21262d', borderRadius: '12px', color: '#58a6ff', border: '1px solid #30363d' }}>
              SQLite + Calendar Synced
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#8b949e' }}>
            Manage deadlines, Hollywood writing sprints, tech tasks, and AI-extracted action items.
          </p>
        </div>

        {/* Action Buttons & Counters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Quick Metrics */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', backgroundColor: '#0d1117', padding: '6px 12px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>Total</div>
              <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#f0f6fc' }}>{stats.total}</div>
            </div>
            <div style={{ width: '1px', height: '24px', backgroundColor: '#30363d' }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#3fb950' }}>Done</div>
              <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#3fb950' }}>{stats.completed}</div>
            </div>
            <div style={{ width: '1px', height: '24px', backgroundColor: '#30363d' }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: stats.overdue > 0 ? '#f85149' : '#8b949e' }}>Overdue</div>
              <div style={{ fontSize: '14px', fontWeight: 'bold', color: stats.overdue > 0 ? '#f85149' : '#8b949e' }}>{stats.overdue}</div>
            </div>
            <div style={{ width: '1px', height: '24px', backgroundColor: '#30363d' }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#58a6ff' }}>Rate</div>
              <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#58a6ff' }}>{stats.completion_rate}%</div>
            </div>
          </div>

          <button
            onClick={() => openTaskModal()}
            style={{
              padding: '8px 16px',
              backgroundColor: '#238636',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>➕</span> New Action Item
          </button>
        </div>
      </div>

      {/* 2. AI Action Item Smart Extractor */}
      <div style={{ padding: '14px 24px', backgroundColor: '#0d1117', borderBottom: '1px solid #21262d' }}>
        <form onSubmit={handleAiExtract} style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <span style={{ position: 'absolute', left: '12px', top: '10px', fontSize: '14px' }}>✨</span>
            <input
              type="text"
              value={aiInput}
              onChange={(e) => setAiInput(e.target.value)}
              placeholder='AI Smart Ingest: e.g. "Draft scene 4 outline by tomorrow 3 PM, review sound stems by Friday, send pitch to studio"'
              style={{
                width: '100%',
                padding: '9px 12px 9px 36px',
                backgroundColor: '#161b22',
                border: '1px solid #30363d',
                borderRadius: '6px',
                color: '#c9d1d9',
                fontSize: '13px'
              }}
            />
          </div>
          <button
            type="submit"
            disabled={aiExtracting || !aiInput.trim()}
            style={{
              padding: '9px 16px',
              backgroundColor: aiExtracting ? '#30363d' : '#1f6feb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: aiExtracting ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '13px'
            }}
          >
            {aiExtracting ? 'Extracting...' : '✨ AI Extract Tasks'}
          </button>
        </form>
        {aiSuccessMsg && (
          <div style={{ marginTop: '8px', fontSize: '12px', color: '#3fb950', fontWeight: '500' }}>
            {aiSuccessMsg}
          </div>
        )}
      </div>

      {/* 3. Filter Bar & View Mode Toggle */}
      <div style={{ padding: '12px 24px', backgroundColor: '#161b22', borderBottom: '1px solid #21262d', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: '6px' }}>
          {[
            { id: 'all', label: 'All Tasks' },
            { id: 'today', label: 'Due Today' },
            { id: 'week', label: 'This Week' },
            { id: 'overdue', label: `Overdue (${stats.overdue})`, color: stats.overdue > 0 ? '#f85149' : null },
            { id: 'completed', label: 'Completed' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilterTab(tab.id)}
              style={{
                padding: '6px 12px',
                backgroundColor: filterTab === tab.id ? '#21262d' : 'transparent',
                color: filterTab === tab.id ? (tab.color || '#f0f6fc') : '#8b949e',
                border: filterTab === tab.id ? '1px solid #30363d' : '1px solid transparent',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: filterTab === tab.id ? '600' : 'normal'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dropdown Filters & Search */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 Search tasks..."
            style={{
              padding: '6px 10px',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '12px',
              width: '150px'
            }}
          />

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{
              padding: '6px 10px',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '12px'
            }}
          >
            <option value="all">All Categories</option>
            <option value="Screenplay & Writing">🎬 Screenplay & Writing</option>
            <option value="Tech & Dev">💻 Tech & Dev</option>
            <option value="Client & Publishing">📚 Client & Publishing</option>
            <option value="Personal">👤 Personal</option>
            <option value="General">📌 General</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            style={{
              padding: '6px 10px',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '12px'
            }}
          >
            <option value="all">All Priorities</option>
            <option value="Urgent">🔴 Urgent</option>
            <option value="High">🟠 High</option>
            <option value="Medium">🟡 Medium</option>
            <option value="Low">🟢 Low</option>
          </select>

          {/* View Toggle */}
          <div style={{ display: 'flex', backgroundColor: '#0d1117', borderRadius: '6px', border: '1px solid #30363d', padding: '2px' }}>
            <button
              onClick={() => setViewMode('kanban')}
              style={{
                padding: '4px 10px',
                backgroundColor: viewMode === 'kanban' ? '#21262d' : 'transparent',
                color: viewMode === 'kanban' ? '#58a6ff' : '#8b949e',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              📊 Board
            </button>
            <button
              onClick={() => setViewMode('list')}
              style={{
                padding: '4px 10px',
                backgroundColor: viewMode === 'list' ? '#21262d' : 'transparent',
                color: viewMode === 'list' ? '#58a6ff' : '#8b949e',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              📋 List
            </button>
          </div>
        </div>
      </div>

      {/* 4. Main Tasks Area */}
      <div style={{ flex: 1, padding: '20px 24px', overflowY: 'auto' }}>
        
        {/* KANBAN BOARD VIEW */}
        {viewMode === 'kanban' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', alignItems: 'flex-start' }}>
            {columns.map(col => {
              const colTasks = filteredTasks.filter(t => t.status === col.id);
              return (
                <div
                  key={col.id}
                  style={{
                    backgroundColor: '#161b22',
                    borderRadius: '8px',
                    border: '1px solid #30363d',
                    display: 'flex',
                    flexDirection: 'column',
                    maxHeight: 'calc(100vh - 280px)'
                  }}
                >
                  {/* Column Header */}
                  <div style={{ padding: '12px 16px', borderBottom: '1px solid #21262d', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold', fontSize: '13px', color: '#f0f6fc' }}>
                      <span>{col.icon}</span> {col.label}
                    </div>
                    <span style={{ fontSize: '12px', padding: '2px 8px', backgroundColor: '#21262d', borderRadius: '10px', color: col.color, fontWeight: 'bold' }}>
                      {colTasks.length}
                    </span>
                  </div>

                  {/* Task Card List */}
                  <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', flex: 1 }}>
                    {colTasks.map(task => {
                      const isOverdue = task.due_date && task.due_date < todayStr && task.status !== 'Completed';
                      const subtaskTotal = Array.isArray(task.subtasks) ? task.subtasks.length : 0;
                      const subtaskDone = Array.isArray(task.subtasks) ? task.subtasks.filter(st => st.done).length : 0;

                      return (
                        <div
                          key={task.id}
                          style={{
                            backgroundColor: '#0d1117',
                            border: isOverdue ? '1px solid #f85149' : '1px solid #30363d',
                            borderRadius: '6px',
                            padding: '12px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                            transition: 'border-color 0.2s',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                          }}
                        >
                          {/* Top row: Priority & Category */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            {getPriorityBadge(task.priority)}
                            <span style={{ fontSize: '11px', color: '#8b949e', backgroundColor: '#161b22', padding: '2px 6px', borderRadius: '4px' }}>
                              {task.category}
                            </span>
                          </div>

                          {/* Title & Checkbox */}
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                            <input
                              type="checkbox"
                              checked={task.status === 'Completed'}
                              onChange={() => handleToggleTask(task.id)}
                              style={{ marginTop: '3px', cursor: 'pointer' }}
                            />
                            <div style={{ flex: 1 }}>
                              <div
                                onClick={() => openTaskModal(task)}
                                style={{
                                  fontSize: '13px',
                                  fontWeight: '600',
                                  color: task.status === 'Completed' ? '#8b949e' : '#f0f6fc',
                                  textDecoration: task.status === 'Completed' ? 'line-through' : 'none',
                                  cursor: 'pointer'
                                }}
                              >
                                {task.title}
                              </div>
                              {task.description && (
                                <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#8b949e', lineHeight: '1.3' }}>
                                  {task.description}
                                </p>
                              )}
                            </div>
                          </div>

                          {/* Subtasks Progress */}
                          {subtaskTotal > 0 && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#8b949e' }}>
                              <span>☑️ {subtaskDone}/{subtaskTotal} subtasks</span>
                              <div style={{ flex: 1, height: '4px', backgroundColor: '#21262d', borderRadius: '2px', overflow: 'hidden' }}>
                                <div style={{ width: `${(subtaskDone / subtaskTotal) * 100}%`, height: '100%', backgroundColor: '#238636' }} />
                              </div>
                            </div>
                          )}

                          {/* Footer: Due Date & Actions */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px', borderTop: '1px solid #21262d', fontSize: '11px' }}>
                            <div style={{ color: isOverdue ? '#f85149' : '#8b949e', fontWeight: isOverdue ? 'bold' : 'normal', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <span>📅</span> {task.due_date || 'No Date'} {task.due_time ? `@ ${task.due_time}` : ''}
                            </div>
                            
                            {/* Column Move / Quick Action */}
                            <div style={{ display: 'flex', gap: '4px' }}>
                              <select
                                value={task.status}
                                onChange={(e) => handleChangeStatus(task.id, e.target.value)}
                                style={{
                                  backgroundColor: '#161b22',
                                  border: '1px solid #30363d',
                                  borderRadius: '4px',
                                  color: '#8b949e',
                                  fontSize: '10px',
                                  padding: '2px 4px'
                                }}
                              >
                                <option value="Todo">Todo</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Completed">Completed</option>
                                <option value="Deferred">Deferred</option>
                              </select>
                              <button
                                onClick={() => handleDeleteTask(task.id)}
                                title="Delete task"
                                style={{
                                  backgroundColor: 'transparent',
                                  border: 'none',
                                  color: '#8b949e',
                                  cursor: 'pointer',
                                  fontSize: '11px',
                                  padding: '0 4px'
                                }}
                              >
                                🗑️
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}

                    {colTasks.length === 0 && (
                      <div style={{ textAlign: 'center', padding: '24px 12px', color: '#484f58', fontSize: '12px' }}>
                        No items in {col.label}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* LIST VIEW */}
        {viewMode === 'list' && (
          <div style={{ backgroundColor: '#161b22', borderRadius: '8px', border: '1px solid #30363d', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#21262d', color: '#8b949e', textAlign: 'left', borderBottom: '1px solid #30363d' }}>
                  <th style={{ padding: '10px 16px', width: '40px' }}>Done</th>
                  <th style={{ padding: '10px 16px' }}>Task & Action Item</th>
                  <th style={{ padding: '10px 16px', width: '120px' }}>Priority</th>
                  <th style={{ padding: '10px 16px', width: '160px' }}>Category</th>
                  <th style={{ padding: '10px 16px', width: '140px' }}>Due Date</th>
                  <th style={{ padding: '10px 16px', width: '130px' }}>Status</th>
                  <th style={{ padding: '10px 16px', width: '90px', textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTasks.map(task => {
                  const isOverdue = task.due_date && task.due_date < todayStr && task.status !== 'Completed';
                  return (
                    <tr
                      key={task.id}
                      style={{
                        borderBottom: '1px solid #21262d',
                        backgroundColor: isOverdue ? 'rgba(248,81,73,0.05)' : 'transparent'
                      }}
                    >
                      <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={task.status === 'Completed'}
                          onChange={() => handleToggleTask(task.id)}
                          style={{ cursor: 'pointer' }}
                        />
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div
                          onClick={() => openTaskModal(task)}
                          style={{
                            fontWeight: '600',
                            color: task.status === 'Completed' ? '#8b949e' : '#f0f6fc',
                            textDecoration: task.status === 'Completed' ? 'line-through' : 'none',
                            cursor: 'pointer'
                          }}
                        >
                          {task.title}
                        </div>
                        {task.description && (
                          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
                            {task.description}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '12px 16px' }}>{getPriorityBadge(task.priority)}</td>
                      <td style={{ padding: '12px 16px', color: '#8b949e' }}>{task.category}</td>
                      <td style={{ padding: '12px 16px', color: isOverdue ? '#f85149' : '#8b949e', fontWeight: isOverdue ? 'bold' : 'normal' }}>
                        {task.due_date || 'No Date'} {task.due_time ? `@ ${task.due_time}` : ''}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <select
                          value={task.status}
                          onChange={(e) => handleChangeStatus(task.id, e.target.value)}
                          style={{
                            backgroundColor: '#0d1117',
                            border: '1px solid #30363d',
                            borderRadius: '4px',
                            color: '#c9d1d9',
                            fontSize: '12px',
                            padding: '4px 8px'
                          }}
                        >
                          <option value="Todo">📋 Todo</option>
                          <option value="In Progress">⏳ In Progress</option>
                          <option value="Completed">✅ Completed</option>
                          <option value="Deferred">⏸️ Deferred</option>
                        </select>
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                          <button
                            onClick={() => openTaskModal(task)}
                            style={{ backgroundColor: 'transparent', border: 'none', color: '#58a6ff', cursor: 'pointer' }}
                            title="Edit"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleDeleteTask(task.id)}
                            style={{ backgroundColor: 'transparent', border: 'none', color: '#f85149', cursor: 'pointer' }}
                            title="Delete"
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {filteredTasks.length === 0 && (
              <div style={{ textAlign: 'center', padding: '32px', color: '#8b949e' }}>
                No tasks match your current filters.
              </div>
            )}
          </div>
        )}
      </div>

      {/* 5. ADD / EDIT TASK MODAL */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.75)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', width: '560px', maxWidth: '90vw', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #30363d', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', color: '#f0f6fc' }}>
                {editingTask ? '✏️ Edit Action Item' : '➕ Create New Action Item'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                style={{ backgroundColor: 'transparent', border: 'none', color: '#8b949e', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveTask} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Task Title *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Complete Scene 12 Dialogue Polish"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', fontSize: '13px' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Due Date</label>
                  <input
                    type="date"
                    value={formData.due_date}
                    onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', fontSize: '13px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Due Time</label>
                  <input
                    type="time"
                    value={formData.due_time}
                    onChange={(e) => setFormData({ ...formData, due_time: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', fontSize: '13px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Priority</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', fontSize: '13px' }}
                  >
                    <option value="Urgent">🔴 Urgent</option>
                    <option value="High">🟠 High</option>
                    <option value="Medium">🟡 Medium</option>
                    <option value="Low">🟢 Low</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', fontSize: '13px' }}
                  >
                    <option value="Screenplay & Writing">🎬 Screenplay & Writing</option>
                    <option value="Tech & Dev">💻 Tech & Dev</option>
                    <option value="Client & Publishing">📚 Client & Publishing</option>
                    <option value="Personal">👤 Personal</option>
                    <option value="General">📌 General</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Notes / Context</label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Key milestones, script notes, or references..."
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', fontSize: '13px' }}
                />
              </div>

              {/* Subtasks Builder */}
              <div>
                <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Subtask Checklist</label>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                  <input
                    type="text"
                    value={newSubtaskInput}
                    onChange={(e) => setNewSubtaskInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddSubtask(); } }}
                    placeholder="Add step or milestone..."
                    style={{ flex: 1, padding: '6px 10px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '4px', color: '#c9d1d9', fontSize: '12px' }}
                  />
                  <button
                    type="button"
                    onClick={handleAddSubtask}
                    style={{ padding: '6px 12px', backgroundColor: '#21262d', border: '1px solid #30363d', borderRadius: '4px', color: '#58a6ff', cursor: 'pointer', fontSize: '12px' }}
                  >
                    Add
                  </button>
                </div>
                {formData.subtasks.map((st, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 8px', backgroundColor: '#0d1117', borderRadius: '4px', marginBottom: '4px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="checkbox"
                        checked={st.done}
                        onChange={() => handleToggleSubtaskInForm(idx)}
                      />
                      <span style={{ color: st.done ? '#8b949e' : '#f0f6fc', textDecoration: st.done ? 'line-through' : 'none' }}>
                        {st.title}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveSubtaskInForm(idx)}
                      style={{ backgroundColor: 'transparent', border: 'none', color: '#f85149', cursor: 'pointer' }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px', borderTop: '1px solid #30363d', paddingTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  style={{ padding: '8px 16px', backgroundColor: '#21262d', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '8px 16px', backgroundColor: '#238636', border: 'none', borderRadius: '6px', color: '#ffffff', fontWeight: 'bold', cursor: 'pointer' }}
                >
                  {editingTask ? 'Save Changes' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
