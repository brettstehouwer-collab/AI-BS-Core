import re

file_path = r'C:\AI-BS\frontend\src\components\MobileStehouwerChat.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the input block
pattern = r'\{\/\* Text Input Area \*\/\}.*?\{isListening \? <MicOff size=\{18\} \/> : <Mic size=\{18\} \/>\}\s*<\/button>'
replacement = """{/* Text Input Area (Auto-Expanding) */}
          <textarea
            ref={textareaRef}
            value={footerInput}
            onChange={(e) => {
              setFooterInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey || !e.shiftKey)) {
                e.preventDefault();
                if (footerInput.trim()) {
                  handleSendMessage();
                  e.target.style.height = 'auto';
                }
              }
            }}
            placeholder="Ask Stehouwer..."
            rows={1}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#e3e3e3',
              fontSize: '0.94rem',
              padding: '8px 4px',
              fontFamily: 'inherit',
              lineHeight: '1.4',
              resize: 'none',
              maxHeight: '120px',
              overflowY: 'auto'
            }}
          />

          {/* Voice Input Mic Button */}
          {!footerInput.trim() ? (
            <button
              onClick={toggleListening}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: isListening ? '#ef4444' : 'transparent',
                border: 'none',
                color: isListening ? '#fff' : '#c4c7c5',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>
          ) : (
            <button
              onClick={() => {
                if (footerInput.trim()) {
                  handleSendMessage();
                  if(textareaRef.current) textareaRef.current.style.height = 'auto';
                }
              }}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: '#4285f4',
                border: 'none',
                color: '#fff',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                boxShadow: '0 0 10px rgba(66, 133, 244, 0.4)',
                transition: 'all 0.15s ease'
              }}
            >
              <ArrowUp size={20} strokeWidth={2.5} />
            </button>
          )}"""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Textarea ergonomics applied successfully.')
