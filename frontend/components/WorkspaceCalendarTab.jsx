import { useState, useEffect, useCallback } from "react";
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format } from 'date-fns/format';
import { parse } from 'date-fns/parse';
import { startOfWeek } from 'date-fns/startOfWeek';
import { getDay } from 'date-fns/getDay';
import { enUS } from 'date-fns/locale/en-US';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import './WorkspaceCalendarTab.css';

const locales = {
  'en-US': enUS,
};

/** @typedef {{id: string, raw_id: string, title: string, start: Date, end: Date, isTask?: boolean, priority?: string, status?: string, category?: string, notes?: string, subtasks?: unknown[]}} CalendarEntry */
/** @typedef {{id: string, raw_id: string, title: string, start: string | number, end: string | number, isTask?: boolean, priority?: string, status?: string, category?: string, notes?: string, subtasks?: unknown[]}} CalendarWire */
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

/** @param {{"backendUrl"?: string}} props */
export default function WorkspaceCalendarTab({ backendUrl = 'http://127.0.0.1:8000' }) {
  const [events, setEvents] = useState(/** @type {CalendarEntry[]} */ ([]));
  const [showTasksOnCalendar, setShowTasksOnCalendar] = useState(true);
  const [showTaskSidebar, setShowTaskSidebar] = useState(true);
  const [sidebarTasks, setSidebarTasks] = useState(/** @type {Array<{"status": string, "due_date": string | null, "id": string, "title": string, "priority": string}>} */ ([]));
  const [nlpInput, setNlpInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingEvent, setEditingEvent] = useState(/** @type {CalendarEntry | null} */ (null));

  // Form State
  const [formData, setFormData] = useState({
    title: '',
    start_datetime: '',
    end_datetime: '',
    category: 'Work',
    notes: ''
  });

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/calendar/combined-events?include_tasks=${showTasksOnCalendar}`);
      if (res.ok) {
        /** @type {CalendarWire[]} */
        const data = await res.json();
        const mappedEvents = data.map( 
item => ({
          id: item.id,
          raw_id: item.raw_id,
          title: item.title,
          start: new Date(item.start),
          end: new Date(item.end),
          category: item.category,
          priority: item.priority,
          notes: item.notes,
          isTask: item.isTask,
          status: item.status,
          subtasks: item.subtasks || []
        }));
        setEvents(mappedEvents);
      }

      // Fetch sidebar tasks
      const tasksRes = await fetch(`${backendUrl}/api/calendar/tasks`);
      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();
        setSidebarTasks(tasksData);
      }
    } catch (err) {
      console.error("Failed to fetch calendar events & tasks:", err);
    }
  }, [backendUrl, showTasksOnCalendar]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  /** @param {string} taskId */
const handleToggleTaskFromCalendar = async ( taskId) => {
    try {
      const res = await fetch(`${backendUrl}/api/calendar/tasks/${taskId}/toggle`, {
        method: 'PATCH'
      });
      if (res.ok) {
        fetchEvents();
      }
    } catch (err) {
      console.error(err);
    }
  };

  /** @param {import('react').SyntheticEvent<HTMLElement>} e */
const handleNlpSubmit = async ( e) => {
    e.preventDefault();
    if (!nlpInput.trim()) return;
    setLoading(true);
    try {
      // Check if user is asking to extract tasks or schedule an event
      const lower = nlpInput.toLowerCase();
      const isTaskDirective = lower.includes('task') || lower.includes('todo') || lower.includes('action') || lower.includes('finish') || lower.includes('review');

      if (isTaskDirective) {
        const res = await fetch(`${backendUrl}/api/calendar/tasks/ai-extract`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: nlpInput })
        });
        if (res.ok) {
          setNlpInput('');
          fetchEvents();
        }
      } else {
        const res = await fetch(`${backendUrl}/api/calendar/nlp/parse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: nlpInput })
        });
        if (res.ok) {
          const { parsed } = await res.json();
          await fetch(`${backendUrl}/api/calendar/appointments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: parsed.title || 'New Event',
              start_datetime: parsed.start_datetime,
              end_datetime: parsed.end_datetime,
              category: parsed.category || 'General',
              notes: parsed.notes || ''
            })
          });
          setNlpInput('');
          fetchEvents();
        }
      }
    } catch (err) {
      console.error(err);
      alert('Error parsing via LLM.');
    } finally {
      setLoading(false);
    }
  };

  /** @param {CalendarEntry | null} [event] @param {import('react-big-calendar').SlotInfo | null} [slotInfo] */
  const openForm = (event = null, slotInfo = null) => {
    if (event && event.isTask) {
      // Handle task click: toggle completion
      handleToggleTaskFromCalendar(event.raw_id);
      return;
    }

    if (event) {
      setEditingEvent(event);
      setFormData({
        title: event.title,
        start_datetime: event.start.toISOString().slice(0, 16),
        end_datetime: event.end.toISOString().slice(0, 16),
        category: event.category || 'Work',
        notes: event.notes || ''
      });
    } else if (slotInfo) {
      setEditingEvent(null);
      setFormData({
        title: '',
        start_datetime: new Date(slotInfo.start).toISOString().slice(0, 16),
        end_datetime: new Date(slotInfo.end).toISOString().slice(0, 16),
        category: 'Work',
        notes: ''
      });
    } else {
      setEditingEvent(null);
      setFormData({
        title: '',
        start_datetime: new Date().toISOString().slice(0, 16),
        end_datetime: new Date(Date.now() + 3600000).toISOString().slice(0, 16),
        category: 'Work',
        notes: ''
      });
    }
    setShowModal(true);
  };

  /** @param {import('react').SyntheticEvent<HTMLElement>} e */
const handleFormSubmit = async ( e) => {
    e.preventDefault();
    const url = editingEvent 
      ? `${backendUrl}/api/calendar/appointments/${editingEvent.raw_id || editingEvent.id}`
      : `${backendUrl}/api/calendar/appointments`;
    
    const method = editingEvent ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: formData.title,
          start_datetime: formData.start_datetime,
          end_datetime: formData.end_datetime,
          category: formData.category,
          notes: formData.notes
        })
      });
      if (res.ok) {
        setShowModal(false);
        fetchEvents();
      } else {
        alert('Failed to save appointment.');
      }
    } catch (err) {
      console.error(err);
      alert('Error saving appointment.');
    }
  };

  const handleDelete = async () => {
    if (!editingEvent) return;
    if (window.confirm("Are you sure you want to delete this event?")) {
      try {
        const res = await fetch(`${backendUrl}/api/calendar/appointments/${editingEvent.raw_id || editingEvent.id}`, {
          method: 'DELETE'
        });
        if (res.ok) {
          setShowModal(false);
          fetchEvents();
        } else {
          alert('Failed to delete event.');
        }
      } catch (err) {
        console.error(err);
      }
    }
  };

  // Custom event styles
  /** @param {CalendarEntry} event @returns {{style: import('react').CSSProperties}} */
const eventPropGetter = ( event) => {
    if (event.isTask) {
      let backgroundColor = '#1f6feb';
      if (event.priority === 'Urgent') backgroundColor = '#b62324';
      else if (event.priority === 'High') backgroundColor = '#9e6a03';
      else if (event.priority === 'Low') backgroundColor = '#238636';

      if (event.status === 'Completed') {
        backgroundColor = '#21262d';
      }

      return {
        style: {
          backgroundColor,
          borderLeft: event.priority === 'Urgent' ? '4px solid #f85149' : '3px solid #58a6ff',
          borderRadius: '4px',
          color: event.status === 'Completed' ? '#8b949e' : '#ffffff',
          textDecoration: event.status === 'Completed' ? 'line-through' : 'none',
          padding: '2px 6px',
          fontSize: '11px',
          fontWeight: event.priority === 'Urgent' ? 'bold' : 'normal',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
          cursor: 'pointer'
        }
      };
    }

    let backgroundColor = '#3174ad';
    switch (event.category) {
      case 'Medical': backgroundColor = '#d93a49'; break;
      case 'Work': backgroundColor = '#2a9d8f'; break;
      case 'Personal': backgroundColor = '#e76f51'; break;
      case 'Sales': backgroundColor = '#f4a261'; break;
      default: backgroundColor = '#3174ad'; break;
    }
    return {
      style: {
        backgroundColor,
        borderRadius: '5px',
        opacity: 0.9,
        color: 'white',
        border: 'none',
        display: 'block',
        fontSize: '12px'
      }
    };
  };

  return (
    <div className="workspace-calendar-tab" style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#0d1117' }}>
      
      {/* 1. Header Toolbar */}
      <div className="calendar-header-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 20px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d', gap: '12px', flexWrap: 'wrap' }}>
        
        {/* NLP Assistant */}
        <div className="nlp-input-wrapper" style={{ flex: 1, maxWidth: '650px', display: 'flex', alignItems: 'center' }}>
          <div className="nlp-icon">🤖</div>
          <form onSubmit={handleNlpSubmit} style={{ flex: 1, display: 'flex' }}>
            <input 
              type="text" 
              placeholder="AI Smart Scheduler: 'Pitch meeting Tuesday 2 PM' or 'Finish Act 1 notes by Friday 5 PM'"
              value={nlpInput}
              onChange={
( e) => setNlpInput(e.target.value)}
              disabled={loading}
              className="nlp-input"
            />
            <button type="submit" disabled={loading} className="nlp-btn">
              {loading ? 'Thinking...' : 'AI Schedule'}
            </button>
          </form>
        </div>

        {/* View Controls & Toggles */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          
          {/* Show Tasks on Calendar Toggle */}
          <button
            onClick={() => setShowTasksOnCalendar(!showTasksOnCalendar)}
            style={{
              padding: '6px 12px',
              backgroundColor: showTasksOnCalendar ? 'rgba(35,134,54,0.2)' : '#21262d',
              color: showTasksOnCalendar ? '#3fb950' : '#8b949e',
              border: showTasksOnCalendar ? '1px solid #238636' : '1px solid #30363d',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>{showTasksOnCalendar ? '☑️' : '⬜'}</span>
            Tasks on Calendar
          </button>

          {/* Quick Dock Toggle */}
          <button
            onClick={() => setShowTaskSidebar(!showTaskSidebar)}
            style={{
              padding: '6px 12px',
              backgroundColor: showTaskSidebar ? '#21262d' : 'transparent',
              color: '#58a6ff',
              border: '1px solid #30363d',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>📋</span>
            {showTaskSidebar ? 'Hide Task Dock' : 'Show Task Dock'}
          </button>

          <button className="manual-add-btn" onClick={() => openForm()} style={{ padding: '6px 14px', fontSize: '12px' }}>
            + Event
          </button>
        </div>
      </div>

      {/* 2. Split Calendar & Task Dock View */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        
        {/* Big Calendar Grid */}
        <div className="calendar-container" style={{ flex: 1, padding: '16px', overflowY: 'auto' }}>
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            style={{ height: '100%', minHeight: '650px', backgroundColor: '#0d1117', color: '#c9d1d9' }}
            selectable
            onSelectSlot={
( slotInfo) => openForm(null, slotInfo)}
            onSelectEvent={
( event) => openForm(event)}
            eventPropGetter={eventPropGetter}
            views={['month', 'week', 'day', 'agenda']}
            popup
          />
        </div>

        {/* Collapsible Action Items Quick Dock */}
        {showTaskSidebar && (
          <div style={{ width: '320px', backgroundColor: '#161b22', borderLeft: '1px solid #30363d', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid #21262d', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 'bold', fontSize: '13px', color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>✅</span> Action Items Dock
              </div>
              <span style={{ fontSize: '11px', color: '#8b949e', backgroundColor: '#0d1117', padding: '2px 6px', borderRadius: '10px' }}>
                {sidebarTasks.filter(t => t.status !== 'Completed').length} Pending
              </span>
            </div>

            <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, overflowY: 'auto' }}>
              {sidebarTasks.map(task => {
                const isOverdue = task.due_date && task.due_date < new Date().toISOString().slice(0, 10) && task.status !== 'Completed';
                return (
                  <div
                    key={task.id}
                    style={{
                      padding: '10px',
                      backgroundColor: '#0d1117',
                      borderRadius: '6px',
                      border: isOverdue ? '1px solid #f85149' : '1px solid #30363d',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '8px'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={task.status === 'Completed'}
                      onChange={() => handleToggleTaskFromCalendar(task.id)}
                      style={{ marginTop: '2px', cursor: 'pointer' }}
                    />
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontSize: '12px',
                          fontWeight: '600',
                          color: task.status === 'Completed' ? '#8b949e' : '#f0f6fc',
                          textDecoration: task.status === 'Completed' ? 'line-through' : 'none'
                        }}
                      >
                        {task.title}
                      </div>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '4px', fontSize: '10px', color: isOverdue ? '#f85149' : '#8b949e' }}>
                        <span>📅 {task.due_date || 'No Date'}</span>
                        <span style={{ color: task.priority === 'Urgent' ? '#f85149' : (task.priority === 'High' ? '#d29922' : '#58a6ff') }}>
                          • {task.priority}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}

              {sidebarTasks.length === 0 && (
                <div style={{ textAlign: 'center', padding: '32px 12px', color: '#8b949e', fontSize: '12px' }}>
                  No tasks recorded. Use the AI bar above to add action items!
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Manual Add/Edit Appointment Modal */}
      {showModal && (
        <div className="calendar-modal-overlay" onClick={() => setShowModal(false)}>
          <div className="calendar-modal-content" onClick={ 
e => e.stopPropagation()}>
            <div className="calendar-modal-header">
              <h3>{editingEvent ? 'Edit Event' : 'Create Event'}</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleFormSubmit} className="calendar-form">
              <label>
                Title:
                <input required type="text" value={formData.title} onChange={ 
e => setFormData({...formData, title: e.target.value})} />
              </label>
              <div className="form-row">
                <label>
                  Start:
                  <input required type="datetime-local" value={formData.start_datetime} onChange={ 
e => setFormData({...formData, start_datetime: e.target.value})} />
                </label>
                <label>
                  End:
                  <input required type="datetime-local" value={formData.end_datetime} onChange={ 
e => setFormData({...formData, end_datetime: e.target.value})} />
                </label>
              </div>
              <label>
                Category:
                <select value={formData.category} onChange={ 
e => setFormData({...formData, category: e.target.value})}>
                  <option value="Work">Work</option>
                  <option value="Sales">Sales</option>
                  <option value="Personal">Personal</option>
                  <option value="Medical">Medical</option>
                  <option value="General">General</option>
                </select>
              </label>
              <label>
                Notes:
                <textarea rows={4} value={formData.notes} onChange={ 
e => setFormData({...formData, notes: e.target.value})}></textarea>
              </label>
              <div className="modal-actions">
                {editingEvent && (
                  <button type="button" className="delete-btn" onClick={handleDelete}>Delete</button>
                )}
                <div style={{ flex: 1 }}></div>
                <button type="button" className="cancel-btn" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="save-btn">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
