path = r"C:\AI-BS\frontend\responsive-fixes.css"
with open(path, 'r', encoding='utf-8') as f:
    css = f.read()

target = """  .mobile-scroll-ribbon,
  [role="tablist"] {
    display: flex !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
  }"""

repl = """  .mobile-scroll-ribbon,
  [role="tablist"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    gap: 8px !important;
    padding-bottom: 6px !important;
  }

  .mobile-scroll-ribbon > button,
  [role="tablist"] > button {
    flex: 0 0 180px !important;
    min-width: 180px !important;
  }"""

if target in css:
    css = css.replace(target, repl)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(css)
    print("responsive-fixes.css updated with ribbon flex rules!")
elif target.replace('\n', '\r\n') in css:
    css = css.replace(target.replace('\n', '\r\n'), repl.replace('\n', '\r\n'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(css)
    print("responsive-fixes.css updated with ribbon flex rules (CRLF)!")
else:
    print("Target in css not found")
