/**
 * AI-BS Hardware Master Repair & Diagnostics Hub - Offline-First Default Datasets
 * Guarantees instantaneous, zero-latency, 100% offline data population on both local development
 * and live production Firebase hosting (https://ai-bs-dashboard.web.app).
 */

export const DEFAULT_GUIDES = [
  {
    id: "uifix_lead_tech_ops",
    category: "apple_iphone",
    brand: "uBreakiFix / Asurion Franchise",
    model_range: "All Store Operations",
    title: "Lead Technician Operations & Visual Field Guide (Batches 1–6)",
    repair_type: "microsoldering",
    difficulty: "Master Technician",
    estimated_time_min: 30,
    heat_temp_c: 75,
    required_tools: [
      "NextGen Portal Tablet POS",
      "Blue Anti-Static ESD Mat (1MΩ Grounded)",
      "4K Trinocular Microscopic Camera",
      "Active Carbon HEPA Fume Extractor",
      "4-Digit Calibrated DC Power Supply (0-30V / 0-5A)",
      "Fireproof Lithium Battery Charging Bag & Sand Bucket",
      "99% Isopropyl Alcohol (IPA) Precision Pipette",
      "Kevlar Friction Thread / Dental Floss"
    ],
    safety_precautions: [
      "Batch 1 Liability Defense: Always verify exact 15-digit IMEI (*#06#) against Asurion claim. Mismatches void billing.",
      "Batch 2 ESD Bench: Never operate without grounded anti-static wrist strap. Maintain dry uncompacted sand bucket.",
      "Batch 3 Serialization: Face ID flood illuminators & battery BMS ICs are cryptographically locked to Secure Enclave.",
      "Batch 4 Liquid Metal APU: PS5 Gallium-Indium alloy is highly conductive; single droplet destroys motherboard.",
      "Batch 5 Chemical Extraction: Zero-prying rule on iPad pouch cells. Inject 2-3 mL 99% IPA; sever adhesive with floss-saw.",
      "Batch 6 Governance: Audit rework rate (<2% target), 2-hr queue triage SLA, and 7-day OEM core return compliance."
    ],
    steps: [
      {
        step_num: 1,
        title: "Batch 1: Front-of-House & Liability Defense",
        instructions: "Audit NextGen Portal interface. Validate Asurion Audit Readiness, physical IMEI match, customer liability waiver sign-off, and LCI moisture status before disassembling hardware."
      },
      {
        step_num: 2,
        title: "Batch 2: The Professional Repair Bench",
        instructions: "Maintain ESD-safe blue mat workspace. Calibrate 4-digit DC power supply, position trinocular 4K microscope, engage HEPA fume extractor, and verify fireproof battery bag."
      },
      {
        step_num: 3,
        title: "Batch 3: Smartphone Architecture & Serialization Hazards",
        instructions: "Navigate stacked sandwich logic boards. Protect cryptographically paired Face ID arrays, spot-weld OEM BMS to preserve battery health, and transfer TrueTone EEPROM data."
      },
      {
        step_num: 4,
        title: "Batch 4: Consoles & Tablets Hardware Hazards",
        instructions: "PS5 APU Liquid Metal: Mask surrounding SMD capacitors with foam barriers. Tablet screens: Heat to 75°C and slice adhesive horizontally without upward prying torque."
      },
      {
        step_num: 5,
        title: "Batch 5: High-Liability Battery Chemical Extraction",
        instructions: "Discharge pouch below 25%. Dispense 2-3 mL 99% IPA via precision pipette. Wait 3-5 min for capillary breakdown. Sever adhesive matrix with horizontal floss-saw motion."
      },
      {
        step_num: 6,
        title: "Batch 6: Lead Technician Focus & Metrics Management",
        instructions: "Manage live store telemetry dashboard: Maintain rework rate < 2%, triage intake queue under 2-hour SLA, and audit 100% of harvested OEM cores for weekly return."
      }
    ],
    pro_tips: [
      "The Lead Tech transitions from an individual repairer into the store's chief quality assurance and liability defense officer."
    ],
    post_qa_checklist: [
      "All 6 operational batches understood and executed across technicians",
      "Weekly audit of sand bucket and battery charging bags completed",
      "Zero unverified IMEI chargebacks recorded"
    ]
  },
  {
    id: "iphone_screen_truetone",
    category: "apple_iphone",
    brand: "Apple",
    model_range: "iPhone X to 16 Pro Max",
    title: "OLED / Screen Replacement & TrueTone / EEPROM Serialization",
    repair_type: "screen",
    difficulty: "Intermediate",
    estimated_time_min: 30,
    heat_temp_c: 75,
    required_tools: [
      "Pentalobe P2 (0.8mm)",
      "Tri-Point Y000 (0.6mm)",
      "Phillips PH000",
      "iFlex / iSesamo pry tool",
      "Suction handle",
      "99% Isopropyl Alcohol",
      "JCID V1SE or QianLi iCopy Plus Programmer",
      "Pre-cut waterproof seal adhesive"
    ],
    safety_precautions: [
      "Discharge battery below 25% to prevent thermal runaway if punctured.",
      "DISCONNECT BATTERY FIRST before touching display, touch, or sensor flex cables.",
      "Do not damage the proximity/flood illuminator flex on the ear speaker assembly—Face ID is paired to the logic board."
    ],
    steps: [
      {
        step_num: 1,
        title: "Lower Pentalobe Removal & Thermal Pre-Heat",
        instructions: "Remove the two 0.8mm Pentalobe screws flanking the Lightning / USB-C port. Place device on heating pad at 75°C for 2.5 minutes to soften perimeter waterproof adhesive."
      },
      {
        step_num: 2,
        title: "Display Separation & Book-Fold Opening",
        instructions: "Apply suction handle to bottom-left glass. Insert thin iFlex blade into seam with a drop of 99% IPA. Slice adhesive around perimeter. Open screen strictly like a book (swing to the right for iPhone 11 and earlier, swing to the left for iPhone 12/13/14/15/16). Never open beyond 90 degrees."
      },
      {
        step_num: 3,
        title: "Connector Bracket Removal & Battery Isolation",
        instructions: "Remove Tri-Point Y000 screws holding the motherboard battery and display EMI shield. Use nylon spudger to pry battery connector up FIRST, killing all power rails."
      },
      {
        step_num: 4,
        title: "Display Disconnection & Ear Speaker Flex Transfer",
        instructions: "Disconnect display flex, touch flex, and ear speaker sensor flex. Remove ear speaker assembly from broken screen using hot air (60°C) to peel microphone and proximity sensor without tearing gold traces. Transfer carefully to new display."
      },
      {
        step_num: 5,
        title: "TrueTone & Display Serial Cloning",
        instructions: "Connect original display to JCID V1SE / QianLi Programmer. Read MTSN / EEPROM data. Disconnect original, connect new display, and execute WRITE. For iPhone 11+, transfer original Touch IC chip or use JCID tag-on flex if eliminating 'Important Display Message' alert."
      },
      {
        step_num: 6,
        title: "Gasket Installation & Reassembly",
        instructions: "Clean old glue residue with 99% IPA. Install fresh OEM perimeter waterproof gasket. Connect display flexes, connect battery connector last. Fasten EMI shields. Press display evenly into frame until clips snap flush. Reinstall bottom P2 screws."
      }
    ],
    pro_tips: [
      "Keep screws organized by exact placement on a magnetic mat; putting a longer screw into a short standoff causes irreparable 'Long Screw Damage' by severing motherboard data traces beneath the standoff.",
      "Soft OLED panels are identical to Apple OEM (flexible substrate, resilient against drops). Avoid cheap Hard OLEDs or Incell LCDs on flagship models as they consume 30% more battery and crack easily."
    ],
    post_qa_checklist: [
      "TrueTone toggle appears in Control Center brightness slider",
      "Face ID operates cleanly at multiple angles",
      "Touch digitization passes full drag-grid test across all keyboard keys",
      "Proximity sensor blanks screen when ear is placed against receiver",
      "Auto-brightness adjusts to ambient light changes"
    ]
  },
  {
    id: "iphone_battery_bms",
    category: "apple_iphone",
    brand: "Apple",
    model_range: "iPhone XS to 16 Series",
    title: "Battery Replacement, BMS Board Welding & Cycle Reset",
    repair_type: "battery",
    difficulty: "Advanced",
    estimated_time_min: 40,
    heat_temp_c: 70,
    required_tools: [
      "Pentalobe P2",
      "Tri-Point Y000",
      "Spot Welder (QianLi Macaron / Relife)",
      "BMS Tag-on Flex",
      "JCID V1SE / QianLi Programmer",
      "99% Isopropyl alcohol",
      "Kapton Tape",
      "OEM Battery Adhesive Pull Tabs"
    ],
    safety_precautions: [
      "Never puncture or bend lithium-ion battery cells. Puncturing causes immediate sparks and toxic white smoke.",
      "Use only plastic or ceramic tools near battery leads to prevent shorting anode to cathode."
    ],
    steps: [
      {
        step_num: 1,
        title: "Chassis Opening & Battery Isolation",
        instructions: "Open screen to 90 degrees. Disconnect battery connector immediately."
      },
      {
        step_num: 2,
        title: "Adhesive Pull-Tab Extraction",
        instructions: "Grasp black adhesive pull tabs at top and bottom of battery. Pull slowly and horizontally at a 15-degree angle. If tab snaps, apply 3 drops of 99% IPA under battery edge and heat rear housing to 70°C for 2 minutes, then slide plastic card underneath."
      },
      {
        step_num: 3,
        title: "Original BMS PCB Transplant (100% Health & No Warning)",
        instructions: "Peel Kapton wrap from original battery top. Snip nickel tabs clean from old cell. Take new high-capacity replacement cell (core only, without BMS). Align original BMS board nickel tabs with new cell terminals. Use battery spot welder at Level 4 pulse to create 4 solid weld spots on positive and negative tabs."
      },
      {
        step_num: 4,
        title: "BMS Tag-on Flex & Cycle Reset",
        instructions: "Attach JCID tag-on flex to battery BMS. Connect to programmer to clear battery cycle count to 0 and reset Health to 100%. Insulate all exposed solder joints with Kapton tape and wrap with OEM battery tape."
      },
      {
        step_num: 5,
        title: "Installation & Calibration",
        instructions: "Install fresh OEM double-sided pull tabs. Seat battery firmly in chassis. Perform a hard reset (Volume Up, Volume Down, hold Power) to calibrate the fuel gauge IC."
      }
    ],
    pro_tips: [
      "For rapid customer turnarounds where 100% Battery Health display is not mandatory, install standard premium TI-cell battery. Advise customer that Battery Health menu will display 'Important Battery Message' but battery runs at full peak performance."
    ],
    post_qa_checklist: [
      "Battery Health shows 100% with Peak Performance Capability",
      "Device draws 2.1A - 3.0A at 9V on USB Power Delivery fast charger",
      "Wireless Qi charging triggers cleanly without excessive thermal rise",
      "No sudden battery drop under 100% CPU benchmark stress"
    ]
  },
  {
    id: "iphone_15_16_usbc_port",
    category: "apple_iphone",
    brand: "Apple",
    model_range: "iPhone 15 / 15 Pro / 16 / 16 Pro Max",
    title: "USB-C Charge Port Dock Flex & Action Button Assembly",
    repair_type: "charge_port",
    difficulty: "Intermediate",
    estimated_time_min: 45,
    heat_temp_c: 75,
    required_tools: ["Pentalobe P2", "Tri-Point Y000", "Phillips PH000", "Standoff Bit", "99% IPA", "Tweezers", "OEM USB-C Dock Flex"],
    safety_precautions: [
      "On iPhone 15/16 series, the back glass opens independently from the front screen. Remove back glass for dock and battery access.",
      "Do not damage the bottom microphone acoustic mesh when seating the port."
    ],
    steps: [
      {
        step_num: 1,
        title: "Rear Glass Removal",
        instructions: "Remove bottom P2 screws. Heat rear glass to 75°C. Open rear glass to the right side and disconnect wireless charging flex."
      },
      {
        step_num: 2,
        title: "Taptic Engine & Loudspeaker Extraction",
        instructions: "Unscrew and remove the Taptic Engine and lower loudspeaker assembly to expose the USB-C dock flex."
      },
      {
        step_num: 3,
        title: "USB-C Dock Port Replacement",
        instructions: "Unscrew the USB-C metal bracket screws. Apply 2 drops of 99% IPA to release dock adhesive. Seat new OEM dock flex with dual microphones."
      },
      {
        step_num: 4,
        title: "Reassembly & Seal",
        instructions: "Reinstall loudspeaker, Taptic Engine, and reconnect dock flex to logic board. Install new rear glass perimeter seal and clamp."
      }
    ],
    pro_tips: [
      "iPhone 15 and 16 dock ports feature USB 3.0 (10Gbps on Pro models). Ensure replacement flex is Pro-rated if working on 15 Pro / 16 Pro to preserve high-speed data transfer."
    ],
    post_qa_checklist: [
      "Fast charging negotiates 9V / 3A (27W PD)",
      "Microphone 1 and Microphone 2 record clear audio in Voice Memos and Loudspeaker calls",
      "Taptic Engine provides crisp haptic clicks on Action Button press"
    ]
  },
  {
    id: "iphone_microsoldering_vdd_main",
    category: "apple_iphone",
    brand: "Apple",
    model_range: "iPhone X to 16 Pro Max (Sandwich Boards)",
    title: "Logic Board Sandwich Separation & PP_VDD_MAIN Short Detection",
    repair_type: "microsoldering",
    difficulty: "Master Technician",
    estimated_time_min: 60,
    heat_temp_c: 190,
    required_tools: ["Mijing / QianLi Heating Pre-Heater Station (185-195°C)", "Stereo Microscope", "Thermal Imaging Camera", "DC Bench Power Supply", "Fluke Multimeter", "Low-melt Solder Paste (183°C)", "Middle Layer Reballing Stencil"],
    safety_precautions: [
      "Do not overheat past 200°C to avoid blistering CPU / NAND underfill.",
      "Always limit DC power supply to 4.0V and 1.5A when injecting voltage into PP_VDD_MAIN."
    ],
    steps: [
      {
        step_num: 1,
        title: "DC Power Supply Benchmark Diagnostics",
        instructions: "Connect iPower cable to battery connector. If current draws 1.0A - 2.5A immediately before pressing power button, there is a hard short on PP_VDD_MAIN or PP_VDD_BOOST."
      },
      {
        step_num: 2,
        title: "Double-Decker Logic Board Separation",
        instructions: "Place logic board on model-specific preheater plate set to 190°C. When molten, gently lift top board (AP logic) from bottom board (RF baseband) vertically with zero shear force."
      },
      {
        step_num: 3,
        title: "Short Isolation with Thermal Camera",
        instructions: "In Diode Mode, probe PP_VDD_MAIN (normal ~0.380V). If 0.000V, inject 3.8V @ 1.5A into the rail. View board under thermal camera to locate glowing capacitor."
      },
      {
        step_num: 4,
        title: "Component Removal & Diode Retest",
        instructions: "Remove shorted capacitor using micro-hot air (360°C). Retest diode mode on PP_VDD_MAIN. Value should restore to ~0.380V."
      },
      {
        step_num: 5,
        title: "Middle Layer Reballing & Re-joining",
        instructions: "Wick old solder from interposer pads. Align stencil, apply 183°C solder paste. Reflow boards on preheater at 195°C."
      }
    ],
    pro_tips: [
      "90% of sudden death / no power iPhones are caused by a single shorted 0201 ceramic filter capacitor on VDD_MAIN next to the audio codec or WiFi module."
    ],
    post_qa_checklist: [
      "Board draws 0.000A standby current before prompt to boot",
      "Boots cleanly into iOS without panic logs in Analytics",
      "Cellular modem registers LTE/5G and SIM"
    ]
  },
  {
    id: "ipad_digitizer_glass",
    category: "apple_ipad",
    brand: "Apple",
    model_range: "iPad 7th / 8th / 9th / 10th Gen & iPad Air",
    title: "Air-Gap Digitizer Glass Replacement (Non-Laminated Models)",
    repair_type: "screen",
    difficulty: "Intermediate",
    estimated_time_min: 45,
    heat_temp_c: 90,
    required_tools: ["Heating Mat (90°C)", "iFlex / Guitar picks (plastic)", "Phillips PH000", "Anti-dust air blower", "T-7000 / 3M Primer 94"],
    safety_precautions: [
      "Do not slide metal tools deep into the right side of the frame where the digitizer flex resides.",
      "Protect the exposed LCD display from dust and fingerprints."
    ],
    steps: [
      {
        step_num: 1,
        title: "Heating & Adhesive Softening",
        instructions: "Place iPad face down on 90°C heating mat for 5 minutes until perimeter glass reaches 80°C."
      },
      {
        step_num: 2,
        title: "Glass Separation without LCD Damage",
        instructions: "Insert razor blade into top corner, insert plastic picks, and cut through thick black foam adhesive. Swing cracked glass open to the right side like a book."
      },
      {
        step_num: 3,
        title: "LCD Unscrewing & Isolation",
        instructions: "Remove 4 corner Phillips screws holding LCD panel. Lift LCD, disconnect battery isolation pick, and disconnect LCD and digitizer flex cables."
      },
      {
        step_num: 4,
        title: "Home Button / Touch ID Transfer",
        instructions: "Apply heat (70°C) to bottom bezel. Peel original Home Button cable without tearing thin membrane to preserve Touch ID."
      },
      {
        step_num: 5,
        title: "Housing Bevel Straightening & Dust Removal",
        instructions: "Straighten dented aluminum corners. Blow dust off LCD. Apply 3M Primer 94 and install new digitizer glass."
      }
    ],
    pro_tips: [
      "Always test touch drawing across 100% of the screen BEFORE pressing the glass adhesive into the housing frame."
    ],
    post_qa_checklist: [
      "Touch ID unlocks instantly with enrolled finger",
      "Apple Pencil tracks smoothly across full glass surface",
      "No glass lifting at corners due to warped frame"
    ]
  },
  {
    id: "ipad_pro_m4_screen",
    category: "apple_ipad",
    brand: "Apple",
    model_range: "iPad Pro 11 / 12.9 / 13 (M1, M2, M4 Tandem OLED)",
    title: "Laminated Tandem OLED / Liquid Retina XDR Screen Swap",
    repair_type: "screen",
    difficulty: "Advanced",
    estimated_time_min: 50,
    heat_temp_c: 80,
    required_tools: ["Heating Mat (80°C)", "Torx T3 / T4", "iFlex", "Suction Pliers", "OEM Adhesive Tape", "Face ID Transfer Bracket"],
    safety_precautions: [
      "Laminated screen combines ultra-thin OLED/LCD and digitizer into single fused unit. Handle strictly by frame edges.",
      "Disconnect battery screw blocker before disconnecting display flex."
    ],
    steps: [
      {
        step_num: 1,
        title: "Perimeter Heat Softening",
        instructions: "Heat screen to 80°C for 4 minutes. Use suction handle and thin plastic picks to release waterproof perimeter tape."
      },
      {
        step_num: 2,
        title: "Display Bracket Unscrewing",
        instructions: "Tilt display up to 45 degrees. Remove Torx screws holding display FPC metal cover. Disconnect display and ambient light sensor flexes."
      },
      {
        step_num: 3,
        title: "Front Sensor Transfer",
        instructions: "Transfer TrueDepth / Face ID sensor module carefully using hot air (60°C) to prevent sensor crystal fracture."
      },
      {
        step_num: 4,
        title: "Adhesive Installation & Bonding",
        instructions: "Install pre-cut perimeter adhesive. Reconnect display, test 120Hz ProMotion touch and brightness, snap flush into aluminum chassis."
      }
    ],
    pro_tips: [
      "120Hz ProMotion panels require precision FPC alignment. If screen exhibits touch jitter, clean connector with contact cleaner and reseat."
    ],
    post_qa_checklist: [
      "120Hz ProMotion high refresh rate active",
      "Face ID operates cleanly at landscape and portrait orientations",
      "Apple Pencil hover and tilt response verified"
    ]
  },
  {
    id: "ipad_usbc_lightning_port",
    category: "apple_ipad",
    brand: "Apple",
    model_range: "iPad 6th-10th Gen, iPad Pro 11 / 12.9",
    title: "Lightning & USB-C Dock Port Micro-Soldering Replacement",
    repair_type: "charge_port",
    difficulty: "Advanced",
    estimated_time_min: 50,
    heat_temp_c: 350,
    required_tools: ["Hot Air Rework Station (Quick 861DW)", "Soldering Iron with J-tip", "Lead-free solder wire", "Amtech NC-559 Flux", "Solder Wick"],
    safety_precautions: [
      "Shield plastic battery connectors and CPU shield with thick Kapton tape before applying hot air."
    ],
    steps: [
      {
        step_num: 1,
        title: "Board Removal & Thermal Shielding",
        instructions: "Remove logic board from chassis. Cover nearby ICs with double-layer Kapton tape."
      },
      {
        step_num: 2,
        title: "Port Desoldering",
        instructions: "Add low-melt alloy solder to all 36 dock pins. Apply hot air at 350°C from underside of board until port slides off smoothly."
      },
      {
        step_num: 3,
        title: "Pad Preparation & Cleaning",
        instructions: "Apply flux and clean pads with solder wick. Ensure all 36 gold traces are flat, shiny, and unbroken."
      },
      {
        step_num: 4,
        title: "New Port Alignment & Drag Soldering",
        instructions: "Seat new OEM port. Anchor ground mounting lugs first. Apply flux to pins and perform micro drag-soldering with fine J-tip."
      }
    ],
    pro_tips: [
      "If a customer yanked the cable, inspect pads under microscope for ripped traces and run 0.02mm enameled jumper wires if needed."
    ],
    post_qa_checklist: [
      "Charges in both standard and inverted cable orientations",
      "Draws 2.4A on Lightning / 3.0A (30W PD) on USB-C",
      "Data transfer connects cleanly to computer"
    ]
  },
  {
    id: "samsung_curved_amoled_frame",
    category: "android_phone",
    brand: "Samsung",
    model_range: "Galaxy S20 to S24 Ultra & Note Series",
    title: "Curved Dynamic AMOLED Screen & Chassis Swap",
    repair_type: "screen",
    difficulty: "Intermediate",
    estimated_time_min: 35,
    heat_temp_c: 80,
    required_tools: ["Hot Plate / Heat Gun (80°C)", "Phillips PH000", "iSesamo tool", "Curved suction pliers", "99% Isopropyl alcohol", "B-7000 / OEM rear glass adhesive", "Samsung *#0*# Service Calibration Menu"],
    safety_precautions: [
      "Do not bend the glass back panel during removal—Samsung rear glass has color film on interior that can peel.",
      "Disconnect battery flex before unscrewing motherboard or sub-board."
    ],
    steps: [
      {
        step_num: 1,
        title: "Rear Glass De-Gluing",
        instructions: "Heat back cover to 80°C for 3 minutes. Insert thin plastic card with 2 drops of IPA. Slice adhesive along edges, avoiding the camera housing and wireless charging coil."
      },
      {
        step_num: 2,
        title: "Wireless Charging Coil & Motherboard Removal",
        instructions: "Remove Phillips PH000 screws holding mid-frame / NFC coil assembly. Unclip mid-frame. Disconnect battery, screen interconnect flex, and sub-board flex. Unscrew and remove main logic board."
      },
      {
        step_num: 3,
        title: "Sub-Board, Battery & Vibrator Transfer",
        instructions: "Transfer sub-board (charging port), haptic vibrator motor, and ear speaker into new Service Pack (Screen + Frame assembly). Apply IPA under battery to dissolve stretch adhesive and transfer to new frame."
      },
      {
        step_num: 4,
        title: "Ultrasonic / Optical Fingerprint Calibration",
        instructions: "Reassemble logic board, reconnect all flexes, power on. Dial *#0*# in phone dialer. Run SENSOR -> FINGERPRINT TEST -> RE-CALIBRATE to register optical/ultrasonic sensor against new AMOLED panel."
      },
      {
        step_num: 5,
        title: "Back Glass Re-sealing",
        instructions: "Clean frame perimeter, apply fresh OEM cut adhesive, clamp rear cover for 15 minutes for IP68 water resistance restoration."
      }
    ],
    pro_tips: [
      "Always buy 'Service Pack with Frame' (Official Samsung Service Pack) rather than screen-only glass. Service Pack with frame saves 30 minutes of labor and eliminates crooked edge-fit or glue mess."
    ],
    post_qa_checklist: [
      "Dial *#0*# and pass Touch (fill all green boxes), RED, GREEN, BLUE sub-pixel test",
      "Fingerprint sensor enrolls and unlocks reliably within 0.2s",
      "Both speakers output distortion-free stereo",
      "Wireless PowerShare operates"
    ]
  },
  {
    id: "samsung_z_fold_hinge_inner_screen",
    category: "android_phone",
    brand: "Samsung",
    model_range: "Galaxy Z Fold 3 / 4 / 5 / 6 & Z Flip",
    title: "Folding Ultra-Thin Glass (UTG) & Gear Hinge Dust Service",
    repair_type: "screen",
    difficulty: "Master Technician",
    estimated_time_min: 75,
    heat_temp_c: 70,
    required_tools: ["Heated Mat (70°C)", "Plastic Micro-Pry Cards", "Phillips PH000", "Hinge alignment jig", "T-7000 adhesive", "Synthetic Watch Grease"],
    safety_precautions: [
      "The inner folding OLED is covered in Ultra-Thin Glass (UTG) that fractures under fingernail pressure. Never press metal tools against inner screen bezel.",
      "Dual batteries must be disconnected simultaneously."
    ],
    steps: [
      {
        step_num: 1,
        title: "Outer Screen & Rear Glass Extraction",
        instructions: "Heat both outer panels to 70°C. Slice perimeter adhesive and disconnect outer display and rear cover."
      },
      {
        step_num: 2,
        title: "Dual Motherboard Disassembly",
        instructions: "Disconnect main board and sub-board interconnect bridge flexes running through the spine hinge."
      },
      {
        step_num: 3,
        title: "Hinge Sweeper De-Gunking",
        instructions: "Disassemble hinge spine covers. Clean bristled sweepers with 99% IPA and apply micro-drop of synthetic watch lubricant to dual-axis gears."
      },
      {
        step_num: 4,
        title: "Inner Service Pack Installation",
        instructions: "Mount dual boards into new folding Service Pack assembly. Ensure hinge opens 180 degrees dead flat."
      }
    ],
    pro_tips: [
      "Most 'won't open fully flat' Z Folds are caused by pocket lint lodged in the gear teeth. Cleaning the hinge gears without replacing the screen restores 180° flat opening in 80% of cases."
    ],
    post_qa_checklist: [
      "Hinge opens to 180 degrees completely flat with zero crunching sound",
      "Inner folding OLED displays zero crease dead pixels or touch anomalies",
      "Flex Mode detects angles between 75° and 115°"
    ]
  },
  {
    id: "pixel_fingerprint_calibration",
    category: "android_phone",
    brand: "Google Pixel",
    model_range: "Pixel 6, 7, 8, 9 Series",
    title: "OLED Replacement & Optical Fingerprint Calibration Web Tool",
    repair_type: "screen",
    difficulty: "Intermediate",
    estimated_time_min: 30,
    heat_temp_c: 75,
    required_tools: ["Heat Pad (75°C)", "Torx T3", "iSesamo", "99% IPA", "Google Pixel Web Calibration Tool (Chrome WebUSB)"],
    safety_precautions: [
      "Optical fingerprint sensor under Pixel displays requires software calibration via Google official web tool after replacement or biometric unlock will permanently fail."
    ],
    steps: [
      {
        step_num: 1,
        title: "Display Removal from Front",
        instructions: "Pixel displays open from the front. Heat perimeter to 75°C, slice adhesive, open like a book from right to left."
      },
      {
        step_num: 2,
        title: "Bracket & Screen Disconnection",
        instructions: "Remove Torx T3 screw holding metal FPC bracket. Disconnect display cable."
      },
      {
        step_num: 3,
        title: "WebUSB Fingerprint Calibration",
        instructions: "Connect new screen. Boot phone into Fastboot mode. Connect to PC via Chrome browser at `pixelrepair.withgoogle.com`. Select 'Fingerprint Calibration', follow on-screen prompt to calibrate optical scanner, and reboot."
      },
      {
        step_num: 4,
        title: "Adhesive Gasket Sealing",
        instructions: "Install fresh perimeter adhesive cut, connect screen, snap into frame."
      }
    ],
    pro_tips: [
      "Always restart phone twice after completing Google WebUSB calibration before enrolling new fingerprints."
    ],
    post_qa_checklist: [
      "Under-display fingerprint enrolls and unlocks in <0.3s",
      "High brightness mode triggers under direct flashlight",
      "Smooth 120Hz display refresh active"
    ]
  },
  {
    id: "android_flashing_unbrick_odin",
    category: "android_phone",
    brand: "Samsung / Google Pixel",
    model_range: "Universal Android / Odin 3.14.4 / Fastboot",
    title: "Firmware Flashing, Bootloop Recovery & Unbricking",
    repair_type: "software",
    difficulty: "Intermediate",
    estimated_time_min: 25,
    heat_temp_c: 0,
    required_tools: ["Windows PC (WSL2 / AI-BS Rig)", "Odin v3.14.4 (Samsung) or Android Platform Tools ADB/Fastboot", "SamFirm / Frija 4-File Firmware Downloader", "High-speed USB 3.0 Type-C Cable"],
    safety_precautions: [
      "Ensure battery is charged to at least 40% before flashing.",
      "Use 'HOME_CSC' file if customer wishes to preserve photos/data; use 'CSC' if performing a full clean factory wipe."
    ],
    steps: [
      {
        step_num: 1,
        title: "Download Official 4-File Firmware",
        instructions: "Use Frija tool to download binary-matching firmware (BL, AP, CP, CSC) for exact model number."
      },
      {
        step_num: 2,
        title: "Enter Download Mode",
        instructions: "Hold Volume Down + Volume Up simultaneously and plug in USB-C cable connected to PC. Press Volume Up to confirm Download / Odin Mode."
      },
      {
        step_num: 3,
        title: "Odin Slot Population & Flash Execution",
        instructions: "Load BL into BL slot, AP into AP slot, CP into CP slot, and HOME_CSC into CSC slot. Click START and allow 4-6 minutes for NAND partition writes."
      },
      {
        step_num: 4,
        title: "Reboot & Cache Verification",
        instructions: "Upon 'PASS!' message, device reboots. Enter recovery mode and wipe cache partition."
      }
    ],
    pro_tips: [
      "You can never downgrade Samsung bootloader binaries (e.g., cannot flash Binary 2 on a Binary 3 board)."
    ],
    post_qa_checklist: [
      "Device boots cleanly without crashing",
      "IMEI and Baseband firmware intact (*#06# valid)",
      "Google Play Protect certification passes"
    ]
  },
  {
    id: "android_tablet_battery_port",
    category: "android_tablet",
    brand: "Samsung / Lenovo / Amazon Fire",
    model_range: "Galaxy Tab A/S Series, Lenovo Tab, Amazon Fire HD",
    title: "Tablet Battery Replacement & Sub-Board Port Repair",
    repair_type: "battery",
    difficulty: "Beginner",
    estimated_time_min: 30,
    heat_temp_c: 75,
    required_tools: ["Plastic Spudger / Pry Cards", "Phillips PH000", "99% Isopropyl alcohol", "B-7000 adhesive", "Multimeter"],
    safety_precautions: [
      "Take care around perimeter clips on snap-fit plastic tablet housings.",
      "Disconnect battery flex cable immediately once back cover is off."
    ],
    steps: [
      {
        step_num: 1,
        title: "Chassis Unclipping",
        instructions: "Insert plastic spudger into seam between glass and plastic back cover. Slide around perimeter to pop snap clips."
      },
      {
        step_num: 2,
        title: "Battery & Port Disconnection",
        instructions: "Disconnect battery connector from motherboard. Unscrew 3 Phillips screws holding USB-C charging daughterboard. Disconnect ribbon cable."
      },
      {
        step_num: 3,
        title: "Battery De-Gluing & Replacement",
        instructions: "Apply 99% IPA under battery. Use broad plastic card to lift battery cell cleanly. Seat replacement battery and connect new charging sub-board."
      },
      {
        step_num: 4,
        title: "Snap-Fit Reassembly",
        instructions: "Align motherboard connectors. Press plastic shell firmly until all perimeter clips click flush."
      }
    ],
    pro_tips: [
      "On budget tablets, loose charging ports are usually caused by cracked solder joints on the surface-mount USB legs. Re-flowing the 5 pins with fresh leaded solder fixes it in 5 minutes."
    ],
    post_qa_checklist: [
      "Draws stable 5V @ 2.0A charging current",
      "Battery percentage increments smoothly during charging",
      "SD Card reader and speakers functional"
    ]
  }
];

export const DEFAULT_DIAGNOSTICS = [
  {
    id: "diag_no_power_dc_bench",
    symptom: "No Power / Completely Dead (Won't Turn On)",
    category: "universal",
    primary_suspects: ["Dead Battery", "Torn Screen Flex", "PP_VDD_MAIN Shorted Cap", "Tristar / Hydra USB IC Failure", "PMIC (Power Management IC)"],
    current_draw_analysis: [
      { draw: "0.000A (No draw on power button)", cause: "Broken battery connector, severed power button flex, or dead PMIC crystal oscillator." },
      { draw: "0.05A - 0.08A (Stuck immediately)", cause: "CPU / NAND communication failure or missing I2C / PMU power rail." },
      { draw: "0.20A - 0.45A (Static freeze)", cause: "Blown secondary power rail (e.g. PP_1V8_S2 or PP_GPU short)." },
      { draw: "1.0A - 3.0A+ (Immediate max current draw before power button)", cause: "Direct hard short on PP_VDD_MAIN, PP_BATT_VCC, or VDD_BOOST." }
    ],
    multimeter_probe_steps: [
      "Switch multimeter to Diode Mode (Red probe on Ground / Shield, Black probe on rail test points).",
      "Probe Battery VCC: Expect ~0.450V. If 0.000V -> Battery connector short.",
      "Probe VDD_MAIN: Expect ~0.380V. If 0.000V -> Shorted decoupling capacitor.",
      "Probe 1.8V Always-On: Expect ~0.320V. If missing -> PMIC failure."
    ],
    resolution_pathways: [
      "If VDD_MAIN is shorted: Use Thermal Camera @ 3.8V 1.5A to locate glowing capacitor and remove it.",
      "If device bootloops at 0.15A - 0.80A: Inspect front ear speaker flex; torn flood illuminator sensor causes reboot panic.",
      "If device charges with USB tester at 0.00A: Inspect dock port pins for lint, clean with tweezers, or replace dock flex."
    ]
  },
  {
    id: "diag_no_display_black_screen",
    symptom: "No Display / Black Screen (Phone Vibrates / Makes Sounds)",
    category: "universal",
    primary_suspects: ["Cracked OLED Substrate", "Blown Backlight Filter Coil (FL)", "Chestnut / Display PMIC", "Damaged FPC Connector"],
    current_draw_analysis: [
      { draw: "Normal boot curve (0.2A -> 0.8A -> 1.5A -> drops to 0.1A sleep)", cause: "Logic board is fully operational; fault is 100% localized to screen assembly or display backlight rail." }
    ],
    multimeter_probe_steps: [
      "Shine bright flashlight directly at black screen at an angle. If icons are faintly visible -> Backlight circuit failure (blown fuse/filter).",
      "Inspect motherboard FPC display connector under microscope for bent or burnt pins.",
      "In Diode Mode, probe display power rails (PP5V7_MESON, PP_DISPLAY_BL_ANODE)."
    ],
    resolution_pathways: [
      "Test with known-good Premium Soft OLED screen first.",
      "If still black on iPhone: Bridge blown backlight EMI filter (FL coil) with jumper wire.",
      "If Samsung Galaxy: Ensure display flex connector is fully seated into sub-board and main board."
    ]
  },
  {
    id: "diag_fast_drain_overheating",
    symptom: "Rapid Battery Drain / Phone Gets Burning Hot Around Camera",
    category: "universal",
    primary_suspects: ["Degraded Battery Internal Short", "Tristar / Hydra IC Partial Leakage", "WiFi Module Internal Short", "Corroded Audio Codec / Baseband"],
    current_draw_analysis: [
      { draw: "Standby current draw in sleep mode sits at 0.15A - 0.40A instead of dropping to 0.000A - 0.010A", cause: "VCC leakage on active subsystem." }
    ],
    multimeter_probe_steps: [
      "Check Tristar tester dock reading (reads 'FAIL' on CC1/CC2 lines if USB IC is burnt from cheap car charger).",
      "Inspect motherboard under thermal camera while phone is locked in sleep mode."
    ],
    resolution_pathways: [
      "If USB IC is hot: Replace Tristar / Hydra IC (1610A3 / 1612A1).",
      "If WiFi module heats up: Separate sandwich board and check WiFi decoupling caps."
    ]
  }
];

export const DEFAULT_IC_REFERENCES = [
  {
    id: "tristar_hydra_usb",
    chip_name: "Tristar / Hydra USB Charging Controller",
    part_numbers: ["1610A1", "1610A2", "1610A3", "1612A1", "CBTL1612A1"],
    function_description: "Manages USB accessory handshake, Lightning orientation detection, CC communication, and 5V USB routing.",
    common_symptoms: ["Fake charging (shows lightning bolt but battery % drops)", "Charges only when phone is turned completely off", "Draws 0.20A static sleep current (drains overnight in 3 hours)", "Unable to connect to PC / iTunes error 4013/4014"],
    expected_diode_readings: { PP_TRISTAR_PIN_1: "0.450V", PP_TRISTAR_PIN_5: "0.380V", TRISTAR_VBUS: "0.520V" },
    replacement_difficulty: "Advanced (BGA 36-ball micro-soldering @ 340°C)"
  },
  {
    id: "chestnut_display_pmic",
    chip_name: "Chestnut / Display Power Management IC",
    part_numbers: ["TPS65730", "65730AOP", "TI-Chestnut"],
    function_description: "Generates +5.7V (PP5V7_MESON) and -5.7V (PN5V7_MESON) dual rails to power the OLED / LCD matrix and touch digitizer.",
    common_symptoms: ["Black screen while phone boots normally", "Lines on screen or touch unresponsive with good screen", "0.25A short on board before boot"],
    expected_diode_readings: { PP5V7_MESON: "0.540V", PN5V7_MESON: "0.590V" },
    replacement_difficulty: "Advanced (BGA underfill removal @ 320°C)"
  },
  {
    id: "audio_codec_u3101",
    chip_name: "Audio Codec IC",
    part_numbers: ["338S00105", "338S00248", "Cirrus Logic Audio"],
    function_description: "Decodes microphone inputs, speaker outputs, and ear-piece DAC channels.",
    common_symptoms: ["Voice Memos recording button greyed out", "Loudspeaker icon greyed out on calls", "Phone takes 3 to 5 minutes to boot past Apple logo (Loop Disease)", "Audio IC C12 pad severed trace"],
    expected_diode_readings: { PP_1V8_AUDIO: "0.320V", C12_I2S0_AP_TO_CODEC_MCLK: "0.450V" },
    replacement_difficulty: "Intermediate (Micro-jumper wire on C12 pad + reball)"
  }
];

export const DEFAULT_TOOLS_REF = {
  screwdrivers: [
    { type: "Pentalobe P2 (0.8mm)", use_cases: "Apple iPhone lower chassis perimeter screws (iPhone 4 to 16 Pro Max)" },
    { type: "Pentalobe P5 (1.2mm)", use_cases: "MacBook Air & Pro lower case screws" },
    { type: "Tri-Point Y000 (0.6mm)", use_cases: "iPhone 7 to 16 display brackets, battery EMI shields, and Taptic engine screws" },
    { type: "Phillips PH000 (1.5mm)", use_cases: "Internal frame screws on Samsung, Google Pixel, iPad LCD mounts, and tablets" },
    { type: "Torx T3 / T4 / T5", use_cases: "Google Pixel brackets, Motorola housings, and iPad Pro Face ID brackets" },
    { type: "Standoff Bit (2.5mm)", use_cases: "iPhone logic board grounded standoff screws" }
  ],
  thermal_presets: [
    { substrate: "iPhone OLED Screen Opening", temp_c: 75, time_min: 2.5, warning: "Do not exceed 80°C on soft OLEDs" },
    { substrate: "iPad Digitizer Separation", temp_c: 90, time_min: 5.0, warning: "Keep frame flat; monitor LCD temp with IR thermometer" },
    { substrate: "Samsung Rear Glass De-Gluing", temp_c: 80, time_min: 3.0, warning: "Avoid direct heat on camera lenses to prevent sensor haze" },
    { substrate: "Logic Board Sandwich Separation", temp_c: 190, time_min: 2.0, warning: "Use low-melt 138°C alloy or 183°C leaded solder" }
  ],
  chemicals_and_adhesives: [
    { chemical: "99.9% Isopropyl Alcohol (IPA)", usage: "Dissolves battery stretch adhesive and frame glue instantly without shorting active circuits." },
    { chemical: "B-7000 Adhesive", usage: "Clear slow-cure elastomeric glue (24h full cure). Ideal for phone rear glass and plastic frames." },
    { chemical: "T-7000 Adhesive", usage: "Black high-strength rubber adhesive. Superior for iPad digitizers and plastic bezel bonding." },
    { chemical: "Amtech NC-559-V2-TF Flux", usage: "No-clean rosin flux for micro-BGA reballing and connector drag-soldering." },
    { chemical: "3M Primer 94", usage: "Adhesion promoter applied to aluminum chamfers before seating glass." }
  ]
};

export const DEFAULT_TICKETS = [
  {
    ticket_id: 101,
    customer_name: "Sarah Jenkins",
    customer_phone: "(616) 555-0144",
    device_category: "apple_iphone",
    device_model: "iPhone 15 Pro",
    serial_imei: "354892110948214",
    reported_issue: "Cracked OLED & TrueTone serialization required",
    diagnosis_notes: "Front glass shattered, touch responsive, Face ID undamaged",
    part_grade_used: "Soft OLED",
    parts_cost_usd: 120.0,
    labor_charge_usd: 179.0,
    total_price_usd: 299.0,
    status: "In Repair",
    qa_passed: 0
  },
  {
    ticket_id: 102,
    customer_name: "Michael Chang",
    customer_phone: "(616) 555-0823",
    device_category: "android_phone",
    device_model: "Samsung Galaxy S24 Ultra",
    serial_imei: "358712093481239",
    reported_issue: "Curved Dynamic AMOLED frame damage",
    diagnosis_notes: "Corner chassis dented, display lines visible",
    part_grade_used: "OEM Refurb / Pull",
    parts_cost_usd: 220.0,
    labor_charge_usd: 149.0,
    total_price_usd: 369.0,
    status: "Testing QA",
    qa_passed: 1
  }
];

export const DEFAULT_PART_SKUS = [
  {
    id: "sku_iphone_13_14_screen",
    category: "apple_iphone",
    model: "iPhone 13 vs iPhone 14",
    component: "OLED Screen Assembly",
    oem_sku: "AP-IP13-SCR-OEM / AP-IP14-SCR-OEM",
    compatibility_rule: "⚠️ NOT Interchangeable. Although both screens are 6.1\" 60Hz OLED, the display connector pinout and ear speaker sensor flex mounting are inverted. Installing a 13 screen on a 14 results in zero backlight and blown logic board FL coils.",
    grades: [
      { grade: "OEM Pull / Refurb", rating: "★★★★★", cost_range: "$85 - $115", pros: "100% color gamut, perfect TrueTone cloning, original flexible substrate." },
      { grade: "Soft OLED", rating: "★★★★☆", cost_range: "$55 - $75", pros: "Flexible substrate resilient to drops, identical 1200 nit brightness." },
      { grade: "Hard OLED", rating: "★★☆☆☆", cost_range: "$35 - $45", pros: "Cheap but rigid glass fractures easily; thicker bezel borders." },
      { grade: "Incell LCD", rating: "★☆☆☆☆", cost_range: "$22 - $30", pros: "DO NOT USE. Drains battery 35% faster, runs hot, causes touch lag." }
    ],
    pitfalls: "Transfer the ambient light sensor flex carefully with 60°C hot air to avoid tearing Face ID data traces."
  },
  {
    id: "sku_iphone_12_12pro_battery",
    category: "apple_iphone",
    model: "iPhone 12 & iPhone 12 Pro",
    component: "Battery Cell (2815 mAh)",
    oem_sku: "A2479 / AP-BATT-IP12-OEM",
    compatibility_rule: "✅ 100% Interchangeable. iPhone 12 and iPhone 12 Pro share the exact same 2815 mAh A2479 battery cell and FPC connector.",
    grades: [
      { grade: "OEM Core Cell (No BMS)", rating: "★★★★★", cost_range: "$18 - $24", pros: "Spot-weld original Apple BMS to retain 100% Battery Health with zero popup alert." },
      { grade: "Premium TI Fuel Gauge", rating: "★★★★☆", cost_range: "$14 - $18", pros: "High cycle life, stable discharge curve; displays 'Important Battery Message' on iOS 15+." }
    ],
    pitfalls: "Never pry battery with metal tools. Use pull tabs horizontally or soften with 99% IPA."
  },
  {
    id: "sku_samsung_s24u_service_pack",
    category: "android_phone",
    model: "Galaxy S24 Ultra (SM-S928U)",
    component: "Dynamic AMOLED 2X Display + Titanium Frame",
    oem_sku: "GH82-33421A (Titanium Black) / GH82-33421B (Titanium Gray)",
    compatibility_rule: "⚠️ Model-Specific. Does NOT fit S23 Ultra (S24 Ultra display is flat, whereas S23 Ultra display has curved edges).",
    grades: [
      { grade: "Official Samsung Service Pack", rating: "★★★★★", cost_range: "$210 - $250", pros: "Factory pre-bonded to titanium frame, pre-installed ear speaker, buttons, and thermal vapor chamber." },
      { grade: "Glass-Only Refurb", rating: "★★★☆☆", cost_range: "$150 - $180", pros: "Lower cost but requires manual gluing into old frame; risk of corner light bleed." }
    ],
    pitfalls: "Must dial *#0*# after assembly to recalibrate ultrasonic under-display fingerprint sensor."
  },
  {
    id: "sku_pixel_7_8_fingerprint",
    category: "android_phone",
    model: "Google Pixel 7 / 7 Pro / 8 / 8 Pro",
    component: "OLED Screen & Optical Fingerprint Module",
    oem_sku: "G949-00124-01",
    compatibility_rule: "⚠️ Requires WebUSB Software Calibration. Screen will display normally, but fingerprint biometric unlock will be completely disabled until calibrated via pixelrepair.withgoogle.com.",
    grades: [
      { grade: "OEM Service Pack", rating: "★★★★★", cost_range: "$110 - $145", pros: "Official optical sensor bracket, perfect 120Hz refresh rate, HDR10+ support." }
    ],
    pitfalls: "Fastboot mode connection to Chrome browser required. Reboot phone twice post-calibration."
  },
  {
    id: "sku_ipad_9th_digitizer",
    category: "apple_ipad",
    model: "iPad 7th / 8th / 9th Gen (10.2\")",
    component: "Air-Gap Digitizer Touch Glass",
    oem_sku: "AP-IPD102-DIG-BLK / AP-IPD102-DIG-WHT",
    compatibility_rule: "✅ 100% Interchangeable. iPad 7 (2019), iPad 8 (2020), and iPad 9 (2021) share the exact same 10.2\" digitizer touch glass and Home Button bracket.",
    grades: [
      { grade: "Premium Glass + Pre-Soldered Flex", rating: "★★★★★", cost_range: "$12 - $18", pros: "High-grade tempered glass with pre-attached camera bracket and foam dust gasket." }
    ],
    pitfalls: "Transfer original Home Button to preserve Touch ID pairing. Clean LCD with air blower before seating glass."
  },
  {
    id: "sku_ps5_hdmi_port",
    category: "consoles_computers",
    model: "PlayStation 5 (Fat CFI-1000/1100/1200 & Slim CFI-2000)",
    component: "HDMI 2.1 4K@120Hz Output Port",
    oem_sku: "PS5-HDMI-2.1-OEM",
    compatibility_rule: "⚠️ Check Leg Mounting Alignment. Fat PS5 and Slim PS5 HDMI ports share 19 internal pins but have different chassis ground through-hole anchor leg spacing.",
    grades: [
      { grade: "Solid Copper Reinforced Pin Port", rating: "★★★★★", cost_range: "$4 - $8", pros: "Reinforced bridge tabs prevent pin push-back when cables are yanked." }
    ],
    pitfalls: "PS5 APU is cooled with conductive Gallium-Indium liquid metal. Mask surrounding motherboard capacitors with tape during rework."
  }
];

export const DEFAULT_DC_PRESETS = [
  {
    id: "dc_0_000_dead",
    name: "0.000A Dead Standby (No Draw)",
    voltage: 4.2,
    current_amp: 0.000,
    waveform: "Flat line at 0.000A",
    status_type: "dead",
    primary_fault: "Complete Open Circuit / Missing VBAT",
    root_causes: [
      "Severed battery connector solder pads",
      "Blown main input MOSFET (Q2101 / Tigris)",
      "Dead 32.768 kHz PMIC crystal oscillator",
      "Cracked power button flex cable trace"
    ],
    probe_points: [
      { rail: "PP_BATT_VCC", expected_diode: "0.450V", test_step: "Probe battery positive terminal to ground." },
      { rail: "PP_VDD_MAIN", expected_diode: "0.380V", test_step: "Probe main VDD inductor next to PMIC." },
      { rail: "BUTTON_TO_PMIC_KEY_L", expected_diode: "1.800V (Volt Mode)", test_step: "Measure voltage on power button line while pressing." }
    ],
    resolution: "Inspect battery connector pins under microscope. Reseat or replace Tigris/PMIC if VBAT is present but PMIC will not generate always-on rails."
  },
  {
    id: "dc_0_050_nand_freeze",
    name: "0.050A - 0.080A Stuck NAND Lock",
    voltage: 4.2,
    current_amp: 0.065,
    waveform: "Step jump to 0.065A and permanent freeze",
    status_type: "freeze",
    primary_fault: "CPU / NAND Bus Hang (DFU Loop)",
    root_causes: [
      "Corrupted iOS / Android firmware partition",
      "Missing PP0V9_NAND or PP1V8_IO power rail",
      "Severed I2C communication bus (I2C0 / I2C1 pull-up resistor blown)",
      "Cracked NAND flash memory BGA solder balls from drop"
    ],
    probe_points: [
      { rail: "PP1V8_IO", expected_diode: "0.340V", test_step: "Check NAND 1.8V IO supply rail." },
      { rail: "PP0V9_NAND", expected_diode: "0.280V", test_step: "Check NAND core voltage regulator." },
      { rail: "I2C0_SCL / SDA", expected_diode: "0.460V", test_step: "Verify pull-up lines on EEPROM/NAND." }
    ],
    resolution: "Connect device to PC. If detected in DFU mode, flash via 3uTools/iTunes/Odin. If error 4013/4014, reball or replace NAND flash IC."
  },
  {
    id: "dc_0_200_vdd_leak",
    name: "0.180A - 0.250A Static Subsystem Leak",
    voltage: 4.2,
    current_amp: 0.220,
    waveform: "Constant steady 0.220A draw in sleep mode",
    status_type: "leak",
    primary_fault: "VCC Leakage (Battery Drains in 3 Hours)",
    root_causes: [
      "Burnt Tristar / Hydra USB controller IC (damaged by cheap 12V car charger)",
      "Corroded Audio Codec (Loop Disease / C12 pad)",
      "WiFi IC internal semiconductor leakage"
    ],
    probe_points: [
      { rail: "PP_TRISTAR_PIN_1", expected_diode: "0.450V", test_step: "Check USB controller input line." },
      { rail: "PP_1V8_AUDIO", expected_diode: "0.320V", test_step: "Check audio codec supply rail." }
    ],
    resolution: "Run Tristar tester. If FAIL, replace 1610A3 / 1612A1 chip. If pass, use thermal camera at 4.0V to locate warm subsystem."
  },
  {
    id: "dc_panic_reboot",
    name: "0.450A - 0.850A Panic Reboot Loop",
    voltage: 4.2,
    current_amp: 0.650,
    waveform: "Oscillating pulse 0.2A -> 0.8A -> drop to 0.0A -> repeat every 3 mins",
    status_type: "bootloop",
    primary_fault: "Sensor Panic Reset (Kernel Watchdog Timeout)",
    root_causes: [
      "Torn front microphone / flood illuminator flex on ear speaker",
      "Disconnected battery gas gauge thermal line (HDQ / I2C)",
      "Corroded charging port dock thermistor (mic1_temp sensor failure)"
    ],
    probe_points: [
      { rail: "I2C_ALS_SCL / SDA", expected_diode: "0.480V", test_step: "Probe ambient light sensor bus." },
      { rail: "BATT_SWI", expected_diode: "0.620V", test_step: "Probe battery single-wire gas gauge." }
    ],
    resolution: "Disconnect front ear speaker flex and charge port flex. If phone boots to home screen, replace the failed sensor assembly."
  },
  {
    id: "dc_2_500_hard_short",
    name: "1.500A - 3.500A+ PP_VDD_MAIN Hard Short",
    voltage: 3.8,
    current_amp: 2.850,
    waveform: "Immediate spike to max current limit before power button is pressed",
    status_type: "short",
    primary_fault: "Primary Power Rail Dead Short to Ground",
    root_causes: [
      "Cracked 0201 multilayer ceramic capacitor (MLCC) on PP_VDD_MAIN or PP_VDD_BOOST",
      "Blown baseband power amplifier or audio amp IC",
      "Liquid ingress galvanic corrosion across main decoupling capacitors"
    ],
    probe_points: [
      { rail: "PP_VDD_MAIN", expected_diode: "0.000V (Beeps short)", test_step: "Diode mode probe main capacitor bank." }
    ],
    resolution: "Set DC power supply to 3.8V and 1.5A limit. Inject voltage into PP_VDD_MAIN test pad. View board under thermal camera to locate glowing capacitor and remove with micro hot air."
  }
];

export const DEFAULT_QA_CHECKPOINTS = [
  { id: "qa_1", group: "Display & Touch", name: "OLED / LCD Image Integrity", desc: "No dead pixels, color tinting, lines, or backlight bleed under white & black test backgrounds." },
  { id: "qa_2", group: "Display & Touch", name: "Full Touch Digitizer Grid", desc: "Drag app icon across 100% of grid squares without dropping anywhere on screen." },
  { id: "qa_3", group: "Display & Touch", name: "TrueTone & Auto-Brightness", desc: "TrueTone toggle present in Control Center; display auto-adjusts to room light." },
  { id: "qa_4", group: "Display & Touch", name: "120Hz ProMotion / Smooth Refresh", desc: "High refresh rate active on Pro / flagship models with zero jitter." },
  { id: "qa_5", group: "Biometrics & Security", name: "Face ID / Front Sensor Array", desc: "Enrolls and unlocks instantly at multiple angles in light and dark conditions." },
  { id: "qa_6", group: "Biometrics & Security", name: "Touch ID / Ultrasonic Fingerprint", desc: "Enrolls fingerprint; unlocks in <0.3s; passes *#0*# sensor test." },
  { id: "qa_7", group: "Cameras & Optics", name: "Front Selfie Camera", desc: "Sharp focus, portrait mode depth map, and video recording pass." },
  { id: "qa_8", group: "Cameras & Optics", name: "Rear Primary Camera (1x)", desc: "Fast autofocus, zero lens dust, crisp 4K capture." },
  { id: "qa_9", group: "Cameras & Optics", name: "Rear Ultra-Wide (0.5x) & Telephoto (3x/5x)", desc: "Smooth optical lens switching without black preview lag." },
  { id: "qa_10", group: "Cameras & Optics", name: "Optical Image Stabilization (OIS)", desc: "No high-frequency buzzing sound or jitter under video stabilization." },
  { id: "qa_11", group: "Audio & Acoustics", name: "Earpiece Receiver Speaker", desc: "Clear, distortion-free audio during phone calls." },
  { id: "qa_12", group: "Audio & Acoustics", name: "Bottom Loudspeaker", desc: "Balanced stereo output at 100% volume with zero rattling." },
  { id: "qa_13", group: "Audio & Acoustics", name: "Microphone 1 (Bottom Voice Call)", desc: "Clear audio recording in Voice Memos without muffled noise." },
  { id: "qa_14", group: "Audio & Acoustics", name: "Microphone 2 (Top Speakerphone)", desc: "Clear audio on speakerphone calls and Siri / Google Assistant." },
  { id: "qa_15", group: "Audio & Acoustics", name: "Microphone 3 (Rear Camera Video)", desc: "Spatial audio captured on rear video recordings." },
  { id: "qa_16", group: "Sensors & Mechanics", name: "Proximity Sensor", desc: "Screen blanks immediately when phone is held up to ear during call." },
  { id: "qa_17", group: "Sensors & Mechanics", name: "Taptic Engine / Haptic Motor", desc: "Crisp vibration clicks on keyboard typing and physical button presses." },
  { id: "qa_18", group: "Sensors & Mechanics", name: "Physical Buttons & Switches", desc: "Power, Volume Up/Down, Action Button, and Mute switch click cleanly." },
  { id: "qa_19", group: "Connectivity & Radio", name: "Wi-Fi 2.4GHz / 5GHz / 6E", desc: "Discovers local networks and connects with high RSSI signal strength." },
  { id: "qa_20", group: "Connectivity & Radio", name: "Bluetooth 5.x", desc: "Discovers and pairs with audio accessories." },
  { id: "qa_21", group: "Connectivity & Radio", name: "Cellular 5G / LTE & SIM Tray", desc: "Registers carrier network, reads SIM/eSIM, *#06# valid IMEI." },
  { id: "qa_22", group: "Power & Charging", name: "Wired Fast Charging (USB-C / Lightning)", desc: "Draws 9V / 3A (27W-45W PD); charges in both standard and flipped cable orientations." },
  { id: "qa_23", group: "Power & Charging", name: "Wireless Qi Charging", desc: "Initiates wireless charge cleanly without abnormal chassis heat." },
  { id: "qa_24", group: "Chassis & Sealing", name: "Waterproof Seal & Flush Alignment", desc: "New perimeter gasket installed; screen sits 100% flush with zero corner lifting." }
];

export const DEFAULT_CHEMICALS_SAFETY = [
  {
    chemical: "99.9% Isopropyl Alcohol (IPA)",
    purpose: "Adhesive Dissolution & Degreasing",
    hazard_class: "Flammable Liquid (Class 1B)",
    ppe: "Nitrile Gloves & Eye Protection",
    usage_guidelines: "Use fine-tip dropper or precision pipette. Apply 2-3 mL strictly along chassis edges to soften stretch adhesive. Keep away from Face ID optical modules and microphone acoustic membranes."
  },
  {
    chemical: "B-7000 / T-7000 Elastomeric Adhesives",
    purpose: "Rear Glass & Frame Perimeter Sealing",
    hazard_class: "Mild Skin Irritant / Vapor",
    ppe: "Ventilated Fume Extractor",
    usage_guidelines: "Apply 1.0mm thin bead around cleaned bezel chamfer. Clamp with nylon spring clamps for 15-30 minutes. Full rubberized cure reached in 24 hours."
  },
  {
    chemical: "Amtech NC-559-V2-TF Rosin Flux",
    purpose: "Micro-BGA Reballing & Drag-Soldering",
    hazard_class: "Respiratory Sensitizer (Rosin Fumes)",
    ppe: "Active Carbon HEPA Fume Extractor Arm",
    usage_guidelines: "Apply micro-dab to solder pads before hot air reflow. Prevents solder oxidation and promotes mirror-finish ball formation."
  },
  {
    chemical: "3M Primer 94 Adhesion Promoter",
    purpose: "Tablet Frame Glass Bonding",
    hazard_class: "Flammable Solvent",
    ppe: "Nitrile Gloves",
    usage_guidelines: "Wipe lightly onto aluminum frame perimeter before laying down 3M VHB tape. Quadruples tape adhesion strength on iPad chamfers."
  },
  {
    chemical: "Gallium-Indium Liquid Metal Thermal Interface",
    purpose: "PS5 APU High-Conductivity Cooling",
    hazard_class: "High Electrical Conductivity Hazard",
    ppe: "Nitrile Gloves & Cotton Micro-Swab",
    usage_guidelines: "Highly electrically conductive. A single stray microscopic droplet will short SMD capacitors and destroy the motherboard. Mask all surrounding APU capacitor banks with Kapton tape before spreading."
  }
];

