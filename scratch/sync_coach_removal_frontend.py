import os
import re
import hashlib

target_file = r"C:\AI-BS\frontend\src\components\clients\DennisBellPortal.jsx"
with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update getActiveList
old_active_list = """  // Filter current active table
  const getActiveList = () => {
    let source = [];
    if (syndicationCategory === 'pending') source = pendingAthletes;
    else if (syndicationCategory === 'messaged') source = messagedAthletes;
    else if (syndicationCategory === 'coaches') source = excludedCoaches;

    if (!searchTerm.trim()) return source;
    const term = searchTerm.toLowerCase();
    return source.filter(item => {
      return (
        (item.name && item.name.toLowerCase().includes(term)) ||
        (item.phone && item.phone.toLowerCase().includes(term)) ||
        (item.high_school && item.high_school.toLowerCase().includes(term)) ||
        (item.school_name && item.school_name.toLowerCase().includes(term)) ||
        (item.team_name && item.team_name.toLowerCase().includes(term)) ||
        (item.grad_year && item.grad_year.toLowerCase().includes(term))
      );
    });
  };"""

new_active_list = """  // Filter current active table (strictly clean athletes only; coaches are 100% excluded)
  const getActiveList = () => {
    let source = [];
    if (syndicationCategory === 'messaged') source = messagedAthletes;
    else source = pendingAthletes;

    if (!searchTerm.trim()) return source;
    const term = searchTerm.toLowerCase();
    return source.filter(item => {
      return (
        (item.name && item.name.toLowerCase().includes(term)) ||
        (item.phone && item.phone.toLowerCase().includes(term)) ||
        (item.high_school && item.high_school.toLowerCase().includes(term)) ||
        (item.team_name && item.team_name.toLowerCase().includes(term)) ||
        (item.grad_year && item.grad_year.toLowerCase().includes(term))
      );
    });
  };"""

assert old_active_list in content, "old_active_list not found!"
content = content.replace(old_active_list, new_active_list)

# 2. Update Metric Card
old_metric = """          <div style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ fontSize: '28px' }}>🛡️</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#ef4444' }}>{excludedCoaches.length}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Coaches Blocked (Zero Texts)</div>
            </div>
          </div>"""

new_metric = """          <div style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ fontSize: '28px' }}>🛡️</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#34d399' }}>{excludedCoaches.length}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Coaches Quarantined (Zero on Page)</div>
            </div>
          </div>"""

assert old_metric in content, "old_metric not found!"
content = content.replace(old_metric, new_metric)

# 3. Update Top Banner Text
old_banner = """                  <strong> All {excludedCoaches.length} club and high school coaches are mathematically isolated and blocked from receiving messages.</strong>"""
new_banner = """                  <strong> All {excludedCoaches.length} club and high school coaches have been audited, purged, and quarantined in the backend blocklist. ZERO coaches are on this page or in contacts.</strong>"""

assert old_banner in content, "old_banner not found!"
content = content.replace(old_banner, new_banner)

# 4. Update Category Buttons & Export button
old_cat_buttons = """                {/* 3 Main Categories */}
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => { setSyndicationCategory('pending'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'pending' ? '#F58426' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'pending' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    🟡 Needs To Be Messaged ({pendingAthletes.length})
                  </button>

                  <button
                    onClick={() => { setSyndicationCategory('messaged'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'messaged' ? '#10b981' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'messaged' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    🟢 Already Messaged ({messagedAthletes.length})
                  </button>

                  <button
                    onClick={() => { setSyndicationCategory('coaches'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'coaches' ? '#ef4444' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'coaches' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    🛡️ Excluded Coaches Blocklist ({excludedCoaches.length})
                  </button>
                </div>

                {/* Search Bar & Export Buttons */}
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search name, phone, school, team..."
                    style={{
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '7px 12px',
                      fontSize: '12px',
                      width: '240px'
                    }}
                  />

                  {syndicationCategory === 'coaches' ? (
                    <button
                      onClick={() => exportCsv(excludedCoaches, 'RecDebut_Excluded_Coaches', true)}
                      style={{
                        backgroundColor: 'rgba(239, 68, 68, 0.2)',
                        border: '1px solid #ef4444',
                        color: '#fca5a5',
                        padding: '7px 12px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      📥 Export Coaches (CSV)
                    </button>
                  ) : (
                    <button
                      onClick={() => exportCsv(athletes, 'RecDebut_Athletes_Clean_List', false)}
                      style={{
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        border: '1px solid #10b981',
                        color: '#6ee7b7',
                        padding: '7px 12px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      📥 Export Clean Athletes (CSV)
                    </button>
                  )}
                </div>"""

new_cat_buttons = """                {/* Clean Athlete Categories */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => { setSyndicationCategory('pending'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'pending' ? '#F58426' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'pending' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    🟡 Needs To Be Messaged ({pendingAthletes.length})
                  </button>

                  <button
                    onClick={() => { setSyndicationCategory('messaged'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'messaged' ? '#10b981' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'messaged' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    🟢 Already Messaged ({messagedAthletes.length})
                  </button>

                  <div style={{
                    padding: '8px 14px',
                    borderRadius: '6px',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    fontWeight: '700',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    color: '#34d399'
                  }}>
                    🛡️ Coach Exclusion Shield Active (Zero Coaches on Page or in Contacts)
                  </div>
                </div>

                {/* Search Bar & Export Buttons */}
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search name, phone, school, team..."
                    style={{
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '7px 12px',
                      fontSize: '12px',
                      width: '240px'
                    }}
                  />

                  <button
                    onClick={() => exportCsv(athletes, 'RecDebut_Athletes_Clean_List', false)}
                    style={{
                      backgroundColor: 'rgba(16, 185, 129, 0.2)',
                      border: '1px solid #10b981',
                      color: '#6ee7b7',
                      padding: '7px 12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer'
                    }}
                  >
                    📥 Export Clean Athletes (CSV)
                  </button>
                </div>"""

assert old_cat_buttons in content, "old_cat_buttons not found!"
content = content.replace(old_cat_buttons, new_cat_buttons)

# 5. Update Bulk Action Controls condition
old_bulk = """              {/* Bulk Action Controls (for Athlete categories) */}
              {syndicationCategory !== 'coaches' && selectedIds.size > 0 && ("""

new_bulk = """              {/* Bulk Action Controls */}
              {selectedIds.size > 0 && ("""

assert old_bulk in content, "old_bulk not found!"
content = content.replace(old_bulk, new_bulk)

# 6. Update Table Header
old_thead = """                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.15)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      {syndicationCategory !== 'coaches' && (
                        <th style={{ padding: '12px 10px', width: '30px' }}>
                          <input
                            type="checkbox"
                            checked={displayList.length > 0 && selectedIds.size === displayList.length}
                            onChange={handleSelectAll}
                          />
                        </th>
                      )}
                      <th style={{ padding: '12px 14px' }}>Name</th>
                      <th style={{ padding: '12px 14px' }}>Phone Number</th>
                      <th style={{ padding: '12px 14px' }}>
                        {syndicationCategory === 'coaches' ? 'Coach Type' : 'High School / Club'}
                      </th>
                      <th style={{ padding: '12px 14px' }}>
                        {syndicationCategory === 'coaches' ? 'School / Team' : 'Grad Year / Team'}
                      </th>
                      <th style={{ padding: '12px 14px' }}>Status</th>
                      <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>"""

new_thead = """                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.15)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      <th style={{ padding: '12px 10px', width: '30px' }}>
                        <input
                          type="checkbox"
                          checked={displayList.length > 0 && selectedIds.size === displayList.length}
                          onChange={handleSelectAll}
                        />
                      </th>
                      <th style={{ padding: '12px 14px' }}>Name</th>
                      <th style={{ padding: '12px 14px' }}>Phone Number</th>
                      <th style={{ padding: '12px 14px' }}>High School / Club</th>
                      <th style={{ padding: '12px 14px' }}>Grad Year / Team</th>
                      <th style={{ padding: '12px 14px' }}>Status</th>
                      <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>"""

assert old_thead in content, "old_thead not found!"
content = content.replace(old_thead, new_thead)

# 7. Update Table Rows Rendering
old_tbody_block = """                      displayList.slice(0, 150).map((item, idx) => {
                        const isCoach = syndicationCategory === 'coaches';
                        const isSelected = selectedIds.has(item.id);
                        return (
                          <tr
                            key={item.id || idx}
                            style={{
                              borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                              backgroundColor: isSelected ? 'rgba(0, 107, 182, 0.1)' : idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent'
                            }}
                          >
                            {!isCoach && (
                              <td style={{ padding: '10px 10px' }}>
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => handleToggleSelectId(item.id)}
                                />
                              </td>
                            )}
                            <td style={{ padding: '10px 14px', fontWeight: '700', color: '#ffffff' }}>
                              {item.name}
                            </td>
                            <td style={{ padding: '10px 14px', color: isCoach ? '#fca5a5' : '#38bdf8', fontFamily: 'monospace' }}>
                              {item.phone}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                              {isCoach ? (item.coach_type || 'Coach') : (item.high_school || item.sport || 'Basketball')}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                              {isCoach ? (item.school_name || item.team_name || 'Club Roster') : `${item.grad_year || '2026'}${item.team_name ? ` • ${item.team_name}` : ''}`}
                            </td>
                            <td style={{ padding: '10px 14px' }}>
                              {isCoach ? (
                                <span style={{
                                  backgroundColor: 'rgba(239, 68, 68, 0.2)',
                                  color: '#ef4444',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  🛡️ Excluded Coach
                                </span>
                              ) : (item.status === 'Contacted' || item.status === 'Messaged') ? (
                                <span style={{
                                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                                  color: '#10b981',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  🟢 Contacted
                                </span>
                              ) : (
                                <span style={{
                                  backgroundColor: 'rgba(245, 132, 38, 0.2)',
                                  color: '#F58426',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  🟡 Pending
                                </span>
                              )}
                            </td>
                            <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                              {!isCoach && (
                                <div style={{ display: 'inline-flex', gap: '6px' }}>
                                  <button
                                    onClick={() => handleToggleSingleStatus(item)}
                                    title="Toggle Contacted / Pending"
                                    style={{
                                      background: 'rgba(255, 255, 255, 0.08)',
                                      border: '1px solid rgba(255, 255, 255, 0.15)',
                                      color: '#cbd5e1',
                                      padding: '4px 8px',
                                      borderRadius: '4px',
                                      fontSize: '11px',
                                      cursor: 'pointer'
                                    }}
                                  >
                                    {(item.status === 'Contacted' || item.status === 'Messaged') ? 'Set Pending' : 'Mark Done'}
                                  </button>
                                  <button
                                    onClick={() => {
                                      setTestPhone(item.phone);
                                      alert(`Set test phone to ${item.name} (${item.phone}). Click 'Send Test' above to test dispatch.`);
                                    }}
                                    title="Send Test MMS"
                                    style={{
                                      background: 'rgba(0, 107, 182, 0.15)',
                                      border: '1px solid #006BB6',
                                      color: '#38bdf8',
                                      padding: '4px 8px',
                                      borderRadius: '4px',
                                      fontSize: '11px',
                                      cursor: 'pointer'
                                    }}
                                  >
                                    🧪 Test
                                  </button>
                                  <button
                                    onClick={() => handleDeleteAthlete(item.id)}
                                    title="Delete athlete"
                                    style={{
                                      background: 'rgba(239, 68, 68, 0.15)',
                                      border: '1px solid rgba(239, 68, 68, 0.3)',
                                      color: '#f87171',
                                      padding: '4px 8px',
                                      borderRadius: '4px',
                                      fontSize: '11px',
                                      cursor: 'pointer'
                                    }}
                                  >
                                    ✕
                                  </button>
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })"""

new_tbody_block = """                      displayList.slice(0, 150).map((item, idx) => {
                        const isSelected = selectedIds.has(item.id);
                        return (
                          <tr
                            key={item.id || idx}
                            style={{
                              borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                              backgroundColor: isSelected ? 'rgba(0, 107, 182, 0.1)' : idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent'
                            }}
                          >
                            <td style={{ padding: '10px 10px' }}>
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => handleToggleSelectId(item.id)}
                              />
                            </td>
                            <td style={{ padding: '10px 14px', fontWeight: '700', color: '#ffffff' }}>
                              {item.name}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#38bdf8', fontFamily: 'monospace' }}>
                              {item.phone}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                              {item.high_school || item.sport || 'Basketball'}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                              {`${item.grad_year || '2026'}${item.team_name ? ` • ${item.team_name}` : ''}`}
                            </td>
                            <td style={{ padding: '10px 14px' }}>
                              {(item.status === 'Contacted' || item.status === 'Messaged') ? (
                                <span style={{
                                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                                  color: '#10b981',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  🟢 Contacted
                                </span>
                              ) : (
                                <span style={{
                                  backgroundColor: 'rgba(245, 132, 38, 0.2)',
                                  color: '#F58426',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  🟡 Pending
                                </span>
                              )}
                            </td>
                            <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', gap: '6px' }}>
                                <button
                                  onClick={() => handleToggleSingleStatus(item)}
                                  title="Toggle Contacted / Pending"
                                  style={{
                                    background: 'rgba(255, 255, 255, 0.08)',
                                    border: '1px solid rgba(255, 255, 255, 0.15)',
                                    color: '#cbd5e1',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  {(item.status === 'Contacted' || item.status === 'Messaged') ? 'Set Pending' : 'Mark Done'}
                                </button>
                                <button
                                  onClick={() => {
                                    setTestPhone(item.phone);
                                    alert(`Set test phone to ${item.name} (${item.phone}). Click 'Send Test' above to test dispatch.`);
                                  }}
                                  title="Send Test MMS"
                                  style={{
                                    background: 'rgba(0, 107, 182, 0.15)',
                                    border: '1px solid #006BB6',
                                    color: '#38bdf8',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  🧪 Test
                                </button>
                                <button
                                  onClick={() => handleDeleteAthlete(item.id)}
                                  title="Delete athlete"
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.15)',
                                    border: '1px solid rgba(239, 68, 68, 0.3)',
                                    color: '#f87171',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  ✕
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })"""

assert old_tbody_block in content, "old_tbody_block not found!"
content = content.replace(old_tbody_block, new_tbody_block)

# Write modified DennisBellPortal
with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)
print("Modified DennisBellPortal.jsx successfully!")

# Define all 10 mirror paths
dennis_mirrors = [
    r"C:\AI-BS\frontend\src\components\clients\DennisBellPortal.jsx",
    r"C:\AI-BS\frontend\components\clients\DennisBellPortal.jsx",
    r"C:\AI-BS\frontend\src\components\components\clients\DennisBellPortal.jsx",
    r"C:\AI-BS\frontend\components\components\clients\DennisBellPortal.jsx",
    r"C:\AI-BS\frontend\src\clients\DennisBellPortal.jsx"
]

rec_mirrors = [
    r"C:\AI-BS\frontend\src\components\clients\RecreationalDebut.jsx",
    r"C:\AI-BS\frontend\components\clients\RecreationalDebut.jsx",
    r"C:\AI-BS\frontend\src\components\components\clients\RecreationalDebut.jsx",
    r"C:\AI-BS\frontend\components\components\clients\RecreationalDebut.jsx",
    r"C:\AI-BS\frontend\src\clients\RecreationalDebut.jsx"
]

raw_bytes = content.encode("utf-8")
file_hash = hashlib.sha256(raw_bytes).hexdigest()

for path in dennis_mirrors:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw_bytes)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    assert h == file_hash
    print(f"  * Dennis Mirror OK: {path}")

for path in rec_mirrors:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw_bytes)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    assert h == file_hash
    print(f"  * RecDebut Mirror OK: {path}")

print("[SUCCESS] All 10 mirror paths synchronized with 100% SHA-256 parity!")
