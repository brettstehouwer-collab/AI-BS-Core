import React, { useState, useEffect, useRef } from 'react';
import './TourGuideEngine.css';

// Pre-configured Guided Spotlight Tours per Tab
export const TAB_TOURS = {
  power_washing: {
    title: 'Prestige Mobile Services (Power Washing Suite) Tour',
    steps: [
      {
        targetSelector: '.pw-header-deck',
        title: '💦 Rig & Telemetry Command Deck',
        content: 'Displays Prestige Mobile Services live rig specifications (Chevy 3500 HD Dually, 275-Gal IBC tote), call center number (616-901-6536), and aggregated revenue metrics.'
      },
      {
        targetSelector: '.pw-nav-ribbon',
        title: '🎛️ Master 6-Tool Navigation Ribbon',
        content: 'Switch between the 5 AI-BS Engineering Tools: (1) CV Surface Estimator, (2) GIS Quoting, (3) Route & Payload GVWR, (4) Weather Dispatch, (5) Commercial Fleet Portal, and (6) Client CRM.'
      },
      {
        targetSelector: '.pw-tool-header',
        title: '🔬 Active Tool Workspace',
        content: 'This workspace dynamically adapts to whichever tool you select. Dial in substrates, roof pitches, or fleet truck units to calculate field parameters instantly.'
      },
      {
        targetSelector: '.pw-tips-toggle-btn',
        title: '💡 In-Tab Operational Tips & Formulas',
        content: 'Click here to expand or collapse chemical mixing rules (SH % by substrate), safe pressure PSI thresholds, and step-by-step field checklists.'
      },
      {
        targetSelector: '.top-navbar-share-btn',
        title: '🔗 1-Click Share Tool Hyperlink',
        content: 'Click this button anytime to copy the direct, shareable URL (https://ai-bs-dashboard.web.app/?tab=power_washing) to collaborate with other team admins.'
      }
    ]
  },
  shared_cloud_drive: {
    title: 'Admin Shared Cloud Drive & Workspace Tour',
    steps: [
      {
        targetSelector: '.drive-header-deck',
        title: '☁️ Cloud Drive Mission Control',
        content: 'Rooted at C:\\AI-BS\\shared_cloud_drive. Allows drag-and-drop ingestion of any file type (scripts, MP4s, WAVs, JSON, Python).'
      },
      {
        targetSelector: '.drive-new-btn',
        title: '➕ "+ New" Creation Dropdown',
        content: 'Click to create new folders, upload entire folder directories, or create new Fountain screenplays, Markdown notes, JSON files, or Python scripts directly in the browser.'
      },
      {
        targetSelector: '.drive-category-pills',
        title: '🏷️ Category Breakdown & Quick Filters',
        content: 'Filter across Screenplays, Media, Audio, Hospitality, Corporate, Marketing, and AI Models with 1 click.'
      },
      {
        targetSelector: '.drive-tips-btn',
        title: '💡 Drive Tips & Studio Bridges',
        content: 'Toggle in-tab tips explaining multi-select batch downloads, streaming ZIP archives, and direct 1-click bridges into the Screenwriting and Video Studios.'
      }
    ]
  },
  unified_creation: {
    title: 'Universal Screenwriting Studio Tour',
    steps: [
      {
        targetSelector: '.screenplay-top-toolbar, .screenplay-header, h2',
        title: '🎬 Final Draft 12/13 AST Editor',
        content: 'Industry-standard screenplay formatting with instant element hotkeys (Ctrl+1 for Scene, Ctrl+2 for Action, Ctrl+3 for Character, Ctrl+4 for Dialogue).'
      },
      {
        targetSelector: '.screenplay-doctor-btn, .proof-btn, button',
        title: '🔍 AI Page Review Doctor & !proof',
        content: 'Automated formatting doctor that capitalizes character cues, standardizes scene headings, and polishes parentheticals page-by-page.'
      },
      {
        targetSelector: '.audio-player-deck, .project-audio-toggle, button',
        title: '🎙️ ElevenLabs 2h 39m Master Audio Drama',
        content: 'Listen to the full audio drama performance with scrubbable timecodes, variable playback speed (1.0x-2.0x), and timecode synchronization.'
      }
    ]
  },
  dashboard: {
    title: 'AI-BS System Mission Control Tour',
    steps: [
      {
        targetSelector: '.top-navbar',
        title: '🧭 Master Navigation & Hub Switcher',
        content: 'Access all 5 Master Hubs (Stehouwer Publishing, Entertainment Industry, Hospitality Industry, General Operations, and System & AI).'
      },
      {
        targetSelector: '#top-navbar-llm-select, .top-navbar select',
        title: '🧠 Multi-Provider AI Engine Selector',
        content: 'Switch inference on the fly between local RTX 4090 Ollama models, Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro, and DeepSeek.'
      },
      {
        targetSelector: '.top-navbar-guide-btn, button',
        title: '💡 Global Walkthrough Guide & Search',
        content: 'Press "?" or F1 anytime to open the master searchable tool dictionary, step-by-step checklists, and interactive formula calculators.'
      },
      {
        targetSelector: '.top-navbar-share-btn, button',
        title: '🔗 Universal Shareable Hyperlink',
        content: 'Generates deep URLs for https://ai-bs-dashboard.web.app/ to share exact tools and views with collaborators instantly.'
      }
    ]
  }
};

export default function TourGuideEngine({ activeTab, isOpen, onClose }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState(null);
  const popoverRef = useRef(null);

  const activeTour = TAB_TOURS[activeTab] || {
    title: `AI-BS Tab Guide: ${activeTab ? activeTab.replace('_', ' ').toUpperCase() : 'Workspace'}`,
    steps: [
      {
        targetSelector: '.top-navbar',
        title: '🧭 Workspace Navigation Ribbon',
        content: 'Use the top navigation bar to explore the 5 Master Hubs, switch AI providers, and monitor server telemetry.'
      },
      {
        targetSelector: '.top-navbar-guide-btn',
        title: '💡 Interactive Walkthrough Guide',
        content: 'Open the comprehensive button dictionary and step-by-step checklist for this workspace at any time.'
      },
      {
        targetSelector: '.top-navbar-share-btn',
        title: '🔗 Share Tool Link',
        content: 'Copy the direct link to this exact tab to collaborate with team members on https://ai-bs-dashboard.web.app/.'
      }
    ]
  };

  const steps = activeTour.steps;
  const currentStep = steps[currentStepIndex] || steps[0];

  // Calculate target element bounding box on step change or resize
  useEffect(() => {
    if (!isOpen) return;

    const updateRect = () => {
      if (!currentStep) return;
      
      let el = null;
      if (currentStep.targetSelector) {
        const selectors = currentStep.targetSelector.split(',').map(s => s.trim());
        for (const sel of selectors) {
          try {
            el = document.querySelector(sel);
            if (el) break;
          } catch (e) {
            // ignore invalid selector
          }
        }
      }

      if (el) {
        const rect = el.getBoundingClientRect();
        setTargetRect({
          top: rect.top + window.scrollY,
          left: rect.left + window.scrollX,
          width: rect.width,
          height: rect.height,
          viewportTop: rect.top,
          viewportLeft: rect.left
        });
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        // Fallback to center spotlight if element not found
        setTargetRect(null);
      }
    };

    updateRect();
    window.addEventListener('resize', updateRect);
    window.addEventListener('scroll', updateRect);
    const timer = setTimeout(updateRect, 100);

    return () => {
      window.removeEventListener('resize', updateRect);
      window.removeEventListener('scroll', updateRect);
      clearTimeout(timer);
    };
  }, [isOpen, currentStepIndex, currentStep, activeTab]);

  // Keyboard navigation: Esc to close, Left/Right arrow to navigate
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        if (currentStepIndex < steps.length - 1) {
          setCurrentStepIndex(prev => prev + 1);
        } else {
          onClose();
        }
      } else if (e.key === 'ArrowLeft') {
        if (currentStepIndex > 0) {
          setCurrentStepIndex(prev => prev - 1);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentStepIndex, steps.length, onClose]);

  if (!isOpen) return null;

  return (
    <div className="tour-overlay-backdrop" onClick={onClose}>
      {/* Target Element Spotlight Cutout / Glow */}
      {targetRect && (
        <div
          className="tour-spotlight-box"
          style={{
            top: `${targetRect.viewportTop - 6}px`,
            left: `${targetRect.viewportLeft - 6}px`,
            width: `${targetRect.width + 12}px`,
            height: `${targetRect.height + 12}px`
          }}
          onClick={(e) => e.stopPropagation()}
        />
      )}

      {/* Floating Tour Popover Dialog */}
      <div
        className="tour-popover-card"
        ref={popoverRef}
        onClick={(e) => e.stopPropagation()}
        style={
          targetRect
            ? {
                top: targetRect.viewportTop + targetRect.height + 20 > window.innerHeight - 240
                  ? `${Math.max(20, targetRect.viewportTop - 220)}px`
                  : `${targetRect.viewportTop + targetRect.height + 16}px`,
                left: `${Math.min(window.innerWidth - 380, Math.max(20, targetRect.viewportLeft))}px`
              }
            : {
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)'
              }
        }
      >
        <div className="tour-popover-header">
          <div className="tour-step-badge">
            Step {currentStepIndex + 1} of {steps.length}
          </div>
          <button className="tour-close-btn" onClick={onClose} title="Exit Tour (Esc)">
            &times;
          </button>
        </div>

        <div className="tour-popover-body">
          <h3 className="tour-popover-title">{currentStep.title}</h3>
          <p className="tour-popover-text">{currentStep.content}</p>
        </div>

        <div className="tour-popover-footer">
          <button className="tour-btn-skip" onClick={onClose}>
            Skip Tour
          </button>
          <div className="tour-nav-buttons">
            {currentStepIndex > 0 && (
              <button
                className="tour-btn-prev"
                onClick={() => setCurrentStepIndex(prev => prev - 1)}
              >
                ◀ Back
              </button>
            )}
            {currentStepIndex < steps.length - 1 ? (
              <button
                className="tour-btn-next"
                onClick={() => setCurrentStepIndex(prev => prev + 1)}
              >
                Next ▶
              </button>
            ) : (
              <button className="tour-btn-finish" onClick={onClose}>
                ✓ Finish Tour
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
