path = r"C:\AI-BS\frontend\src\components\ProjectNoCoStudioTab.jsx"
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

target = """      {/* 6 Master Pillars Navigation Grid */}
      <div
        role="tablist"
        aria-label="Project NoCo Master Pillars"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '10px',
          marginBottom: '22px'
        }}
      >"""

repl = """      {/* 6 Master Pillars Navigation Grid (Adaptive 2D Grid on Desktop, Horizontal Swipe Ribbon on Mobile) */}
      <div
        role="tablist"
        aria-label="Project NoCo Master Pillars"
        className="mobile-scroll-ribbon"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '10px',
          marginBottom: '20px'
        }}
      >"""

if target in code:
    code = code.replace(target, repl)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(code)
    print("ProjectNoCoStudioTab.jsx updated with mobile-scroll-ribbon!")
elif target.replace('\n', '\r\n') in code:
    code = code.replace(target.replace('\n', '\r\n'), repl.replace('\n', '\r\n'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(code)
    print("ProjectNoCoStudioTab.jsx updated with mobile-scroll-ribbon (CRLF)!")
else:
    print("Target not found in ProjectNoCoStudioTab.jsx")
