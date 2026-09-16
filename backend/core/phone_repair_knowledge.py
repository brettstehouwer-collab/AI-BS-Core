"""
AI-BS Comprehensive Phone, iPad, Android & Tablet Repair Knowledge Engine
Houses step-by-step master hardware repair procedures, diagnostic troubleshooting decision trees,
micro-soldering IC reference tables, chemical/tooling presets, and customer repair ticket management.
"""

import os
import sys
import json
import sqlite3
import time
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "aibs_phone_repair.db")


class PhoneRepairEngine:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()
        self._seed_repair_data_if_empty()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # 1. Guides Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repair_guides (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL, -- 'apple_iphone', 'apple_ipad', 'android_phone', 'android_tablet'
                    brand TEXT NOT NULL,
                    model_range TEXT NOT NULL,
                    title TEXT NOT NULL,
                    repair_type TEXT NOT NULL, -- 'screen', 'battery', 'charge_port', 'camera', 'housing', 'microsoldering', 'software'
                    difficulty TEXT NOT NULL, -- 'Beginner', 'Intermediate', 'Advanced', 'Master Technician'
                    estimated_time_min INTEGER NOT NULL,
                    heat_temp_c INTEGER DEFAULT 75,
                    required_tools JSON NOT NULL,
                    safety_precautions JSON NOT NULL,
                    steps JSON NOT NULL,
                    pro_tips JSON NOT NULL,
                    post_qa_checklist JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Diagnostic Troubleshooting Decision Trees
            conn.execute("""
                CREATE TABLE IF NOT EXISTS diagnostic_trees (
                    id TEXT PRIMARY KEY,
                    symptom TEXT NOT NULL,
                    category TEXT NOT NULL,
                    primary_suspects JSON NOT NULL,
                    current_draw_analysis JSON NOT NULL,
                    multimeter_probe_steps JSON NOT NULL,
                    resolution_pathways JSON NOT NULL
                );
            """)

            # 3. Micro-Soldering IC Reference Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ic_reference (
                    id TEXT PRIMARY KEY,
                    chip_name TEXT NOT NULL,
                    part_numbers JSON NOT NULL,
                    function_description TEXT NOT NULL,
                    common_symptoms JSON NOT NULL,
                    expected_diode_readings JSON NOT NULL,
                    replacement_difficulty TEXT NOT NULL
                );
            """)

            # 4. Customer Repair Ticket Log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repair_tickets (
                    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT DEFAULT 'stehouwer_publishing',
                    customer_name TEXT NOT NULL,
                    customer_phone TEXT DEFAULT '',
                    device_category TEXT NOT NULL,
                    device_model TEXT NOT NULL,
                    serial_imei TEXT DEFAULT '',
                    reported_issue TEXT NOT NULL,
                    diagnosis_notes TEXT DEFAULT '',
                    part_grade_used TEXT DEFAULT 'Premium OLED',
                    parts_cost_usd REAL DEFAULT 0.0,
                    labor_charge_usd REAL DEFAULT 0.0,
                    total_price_usd REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'Checked-In', -- 'Checked-In', 'Diagnosing', 'Awaiting Parts', 'In Repair', 'Testing QA', 'Completed', 'Picked Up'
                    qa_passed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def _seed_repair_data_if_empty(self):
        with self._get_connection() as conn:
            # Seed or update guides
            guides = [
                # ==========================================
                # UBREAKIFIX ACADEMY / SOP GUIDES
                # ==========================================
                {
                    "id": "uifix_14_day_training",
                    "category": "android_tablet",
                    "brand": "Universal / SOP",
                    "model_range": "All Devices",
                    "title": "14-Day Accelerated Training: Architecture & Disassembly",
                    "repair_type": "screen",
                    "difficulty": "Beginner",
                    "estimated_time_min": 14,
                    "heat_temp_c": 75,
                    "required_tools": ["Magnetic Screw Mat", "Nylon Spudgers", "iFlex", "99% IPA"],
                    "safety_precautions": [
                        "Long-Screw Damage: Driving an incorrect screw into a standoff can sever traces, resulting in permanent boot-loops.",
                        "Pry Tool Depth: Insertion of metal tools past 2-3 mm risks severing ambient light sensors or display flex cables."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Pillars 1-3: Fundamentals & Architecture",
                            "instructions": "Master lithium-ion safety, thermal runaway procedures, and tool hierarchy. Practice zero-metal contact rules. Drill Apple display transfers (ambient light sensor, flood illuminator). Drill Android service pack swaps and rear glass removal."
                        },
                        {
                            "step_num": 2,
                            "title": "Pillar 4: OEM Calibration Software",
                            "instructions": "Execute Samsung GSPN, Google AST, and Apple System Configuration workflows. Review USB-debugging failures and biometrics calibration (optical fingerprints)."
                        },
                        {
                            "step_num": 3,
                            "title": "Pillars 5-6: Operations & Speed Testing",
                            "instructions": "Run timed intake simulations (check-in, diagnostic, ticket generation under 4 mins). Run full cycle practice: screen replacement from intake to post-QC in under 45 minutes."
                        }
                    ],
                    "pro_tips": [
                        "Always use a magnetic screw mat to prevent long-screw damage and board fracture."
                    ],
                    "post_qa_checklist": [
                        "Completed 14-day curriculum milestones",
                        "Passed 45-minute repair speed test",
                        "Passed 4-minute intake simulation"
                    ]
                },
                {
                    "id": "uifix_store_operations",
                    "category": "android_phone",
                    "brand": "Universal / SOP",
                    "model_range": "Store Wide",
                    "title": "Store Operations & Turnaround Metrics",
                    "repair_type": "battery",
                    "difficulty": "Intermediate",
                    "estimated_time_min": 5,
                    "heat_temp_c": 0,
                    "required_tools": ["NextGen Portal", "Store Queue Monitor"],
                    "safety_precautions": [
                        "Delays over 3 days cause SLA penalties with OEM partners (Asurion/Samsung/Google)."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Queue Triage & VIP SLA",
                            "instructions": "Standard smartphone repairs are promised at 2 hours. OEM Warranty repairs (Samsung/Google/Apple) are promised Same-Day. Walk-in diagnostic promises are Next-Day."
                        },
                        {
                            "step_num": 2,
                            "title": "Escalation & Communication",
                            "instructions": "If a part is defective (DOA), immediately log note in Portal, re-order via Supply Chain, and call customer within 15 minutes of discovery."
                        },
                        {
                            "step_num": 3,
                            "title": "End of Day (EOD) Operations",
                            "instructions": "All pending tickets must have notes updated. Bench must be cleared of unassigned screws. Hazardous waste (swollen batteries) must be sealed in the sand bucket. Safe drops completed."
                        }
                    ],
                    "pro_tips": [
                        "Communicate expectations early. If an iPad is checked in at 5 PM, promise it for 2 PM the next day to allow chemical adhesive overnight breakdown."
                    ],
                    "post_qa_checklist": [
                        "2-hour turnaround time achieved for standard screens",
                        "EOD notes updated on all open tickets",
                        "Bench swept and hazardous waste secured"
                    ]
                },
                {
                    "id": "uifix_intake_iqc",
                    "category": "apple_iphone",
                    "brand": "Universal / POS",
                    "model_range": "All Devices",
                    "title": "Asurion Claim Intake, IQC & Fraud Prevention Workflow",
                    "repair_type": "software",
                    "difficulty": "Beginner",
                    "estimated_time_min": 15,
                    "heat_temp_c": 0,
                    "required_tools": ["NextGen Portal POS", "NETePay Terminal", "Asurion Dealer Support Line"],
                    "safety_precautions": [
                        "Always verify IMEI exactly. 'SIM-Swap' IMEI traps will cause the claim to fail validation, leaving the store with unbillable parts.",
                        "Inspect LCI (Liquid Contact Indicators). A pink/red LCI means a screen-only claim must be escalated to a WUR (Whole Unit Replacement)."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Claim Retrieval & Verification",
                            "instructions": "Query open claim in NextGen Portal. Verify status is 'Approved for In-Store Repair'. Compare hardware IMEI (*#06# or SIM tray) to Portal. If mismatch, halt intake."
                        },
                        {
                            "step_num": 2,
                            "title": "Physical Damage & Geometry Check",
                            "instructions": "Inspect LCI. Check for chassis warping/bent rails. If frame is twisted, decline screen-only repair as the frame will crack the replacement OLED."
                        },
                        {
                            "step_num": 3,
                            "title": "Pre-Repair IQC Checklist",
                            "instructions": "Test Touch grid, Optics (cameras), Audio/Haptics, Connectivity, and Biometrics. Document EVERY pre-existing scuff on the ticket to prevent fraud/liability."
                        },
                        {
                            "step_num": 4,
                            "title": "Signatures & Serialization",
                            "instructions": "Customer signs Data Loss Waiver and Disassembly Auth. Assign OEM SKU to the ticket. Print routing slips for the ESD bin."
                        }
                    ],
                    "pro_tips": [
                        "If the device has a passcode but the customer won't provide it, flag the ticket as 'Untestable / Customer Assumes Diagnostic Risk'."
                    ],
                    "post_qa_checklist": [
                        "Intake ticket generated in under 4 minutes",
                        "All waivers signed in Portal",
                        "OEM part scanned and bound to ticket"
                    ]
                },
                {
                    "id": "uifix_ipad_chemical_release",
                    "category": "apple_ipad",
                    "brand": "Apple",
                    "model_range": "iPad / All Models",
                    "title": "Chemical Adhesive-Release Protocol for Pouch Batteries",
                    "repair_type": "battery",
                    "difficulty": "Advanced",
                    "estimated_time_min": 45,
                    "heat_temp_c": 70,
                    "required_tools": ["99% Isopropyl Alcohol (IPA)", "Blunt Syringe / Fine-Tip Dropper", "Flexible Plastic Pry Cards", "Heavy-Duty Dental Floss / Kevlar Thread", "Fire-Safe Sand Bucket"],
                    "safety_precautions": [
                        "Never puncture or bend lithium-ion battery cells. Puncturing causes immediate sparks and toxic white smoke.",
                        "Never exceed 70°C or use direct localized heat guns on the battery.",
                        "If you smell a sweet, metallic odor (bubblegum/nail polish remover), STOP IMMEDIATELY. Toxic electrolyte gas is leaking. Evacuate device to sand bucket."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Phase 1: Power Isolation",
                            "instructions": "Discharge battery below 25%. Isolate power by inserting a plastic pick between the battery contact and logic board pins."
                        },
                        {
                            "step_num": 2,
                            "title": "Phase 2: Thermal Softening",
                            "instructions": "Place iPad rear-down onto the heating pad at 70°C for 5-10 mins to soften the rigid adhesive matrix."
                        },
                        {
                            "step_num": 3,
                            "title": "Phase 3: Solvent Injection",
                            "instructions": "Elevate one edge 15-20 degrees. Drip 2-3 mL of 99% IPA along the upper seam. Wait 3-5 minutes for capillary action to break the adhesive."
                        },
                        {
                            "step_num": 4,
                            "title": "Phase 4: Mechanical Separation (Floss Saw)",
                            "instructions": "Use the Floss Saw technique (pulling kevlar thread back and forth underneath the cell) or slide a thin plastic card completely horizontally to sever the weakened adhesive. Do not pry upward (The 'Taco' Effect)."
                        }
                    ],
                    "pro_tips": [
                        "Avoid the 'Alcohol Tsunami': Flooding the chassis with too much IPA can permanently dissolve internal membranes of ambient microphones or the Face ID dot projector."
                    ],
                    "post_qa_checklist": [
                        "Old battery removed with zero bending or puncturing",
                        "Chassis perfectly clean of gummy residue before new battery installation",
                        "No IPA leakage into display backlight layers"
                    ]
                },
                {
                    "id": "uifix_ber_escalation",
                    "category": "android_phone",
                    "brand": "Universal / SOP",
                    "model_range": "Catastrophic Damage",
                    "title": "Beyond Economical Repair (BER) Escalation Protocol",
                    "repair_type": "software",
                    "difficulty": "Master Technician",
                    "estimated_time_min": 10,
                    "heat_temp_c": 0,
                    "required_tools": ["NextGen Portal", "High-Resolution Camera", "Asurion Dealer Support"],
                    "safety_precautions": [
                        "Executing a standard repair on a BER device transfers liability for future hardware failures to the technician and store.",
                        "If battery thermal runaway has occurred (soot/charring), isolate hardware immediately."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Identification of Catastrophic Failure",
                            "instructions": "Identify BER conditions: Frame shearing, logic board fracture, triggered LCI (pink/red) with galvanic corrosion on ICs, or repair cost exceeding secondary market value."
                        },
                        {
                            "step_num": 2,
                            "title": "Photographic Documentation",
                            "instructions": "Capture high-resolution photographic evidence of the structural or liquid damage."
                        },
                        {
                            "step_num": 3,
                            "title": "Status Modification & Claim Release",
                            "instructions": "Update NextGen Portal job status to 'Unrepairable / BER' and attach photos. Contact Asurion Dealer Support to release the IMEI claim lock so the customer can transition to a WUR (Whole Unit Replacement)."
                        },
                        {
                            "step_num": 4,
                            "title": "Customer Conversion & Handback",
                            "instructions": "Inform customer physical repair is aborted. Direct them to Asurion to pay the WUR deductible. Reassemble the damaged device to exact intake state. Close Portal ticket as $0 balance."
                        }
                    ],
                    "pro_tips": [
                        "Never attempt to clean extensive liquid corrosion on an Asurion insurance claim—it voids the WUR transition capability if you fail to fix it."
                    ],
                    "post_qa_checklist": [
                        "Photographic evidence attached to Portal ticket",
                        "Asurion claim lock successfully released",
                        "Device returned to customer in exact intake condition"
                    ]
                },
                # ==========================================
                # LEAD TECH OPERATIONS (BATCHES 1-6)
                # ==========================================
                {
                    "id": "uifix_lead_tech_ops",
                    "category": "universal",
                    "brand": "uBreakiFix / Asurion Franchise",
                    "model_range": "All Store Operations",
                    "title": "Lead Technician Operations & Visual Field Guide (Batches 1–6)",
                    "repair_type": "operations",
                    "difficulty": "Master Tech",
                    "estimated_time_min": 30,
                    "heat_temp_c": 75,
                    "required_tools": [
                        "NextGen Portal Tablet POS",
                        "Blue Anti-Static ESD Mat (1MΩ Grounded)",
                        "4K Trinocular Microscopic Camera",
                        "Active Carbon HEPA Fume Extractor",
                        "4-Digit Calibrated DC Power Supply (0-30V / 0-5A)",
                        "Fireproof Lithium Battery Charging Bag & Sand Bucket",
                        "99% Isopropyl Alcohol (IPA) Precision Pipette",
                        "Kevlar Friction Thread / Dental Floss"
                    ],
                    "safety_precautions": [
                        "Batch 1 Liability Defense: Always verify exact 15-digit IMEI (*#06#) against Asurion claim. Mismatches void billing.",
                        "Batch 2 ESD Bench: Never operate without grounded anti-static wrist strap. Maintain dry uncompacted sand bucket.",
                        "Batch 3 Serialization: Face ID flood illuminators & battery BMS ICs are cryptographically locked to Secure Enclave.",
                        "Batch 4 Liquid Metal APU: PS5 Gallium-Indium alloy is highly conductive; single droplet destroys motherboard.",
                        "Batch 5 Chemical Extraction: Zero-prying rule on iPad pouch cells. Inject 2-3 mL 99% IPA; sever adhesive with floss-saw.",
                        "Batch 6 Governance: Audit rework rate (<2% target), 2-hr queue triage SLA, and 7-day OEM core return compliance."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Batch 1: Front-of-House & Liability Defense",
                            "instructions": "Audit NextGen Portal interface. Validate Asurion Audit Readiness, physical IMEI match, customer liability waiver sign-off, and LCI moisture status before disassembling hardware."
                        },
                        {
                            "step_num": 2,
                            "title": "Batch 2: The Professional Repair Bench",
                            "instructions": "Maintain ESD-safe blue mat workspace. Calibrate 4-digit DC power supply, position trinocular 4K microscope, engage HEPA fume extractor, and verify fireproof battery bag."
                        },
                        {
                            "step_num": 3,
                            "title": "Batch 3: Smartphone Architecture & Serialization Hazards",
                            "instructions": "Navigate stacked sandwich logic boards. Protect cryptographically paired Face ID arrays, spot-weld OEM BMS to preserve battery health, and transfer TrueTone EEPROM data."
                        },
                        {
                            "step_num": 4,
                            "title": "Batch 4: Consoles & Tablets Hardware Hazards",
                            "instructions": "PS5 APU Liquid Metal: Mask surrounding SMD capacitors with foam barriers. Tablet screens: Heat to 75°C and slice adhesive horizontally without upward prying torque."
                        },
                        {
                            "step_num": 5,
                            "title": "Batch 5: High-Liability Battery Chemical Extraction",
                            "instructions": "Discharge pouch below 25%. Dispense 2-3 mL 99% IPA via precision pipette. Wait 3-5 min for capillary breakdown. Sever adhesive matrix with horizontal floss-saw motion."
                        },
                        {
                            "step_num": 6,
                            "title": "Batch 6: Lead Technician Focus & Metrics Management",
                            "instructions": "Manage live store telemetry dashboard: Maintain rework rate < 2%, triage intake queue under 2-hour SLA, and audit 100% of harvested OEM cores for weekly return."
                        }
                    ],
                    "pro_tips": [
                        "The Lead Tech transitions from an individual repairer into the store's chief quality assurance and liability defense officer."
                    ],
                    "post_qa_checklist": [
                        "All 6 operational batches understood and executed across technicians",
                        "Weekly audit of sand bucket and battery charging bags completed",
                        "Zero unverified IMEI chargebacks recorded"
                    ]
                },
                # ==========================================
                # APPLE IPHONE GUIDES
                # ==========================================
                {
                    "id": "uifix_intake_iqc",
                    "category": "apple_iphone",
                    "brand": "Universal / POS",
                    "model_range": "All Devices",
                    "title": "Asurion Claim Intake, IQC & Fraud Prevention Workflow",
                    "repair_type": "software",
                    "difficulty": "Beginner",
                    "estimated_time_min": 15,
                    "heat_temp_c": 0,
                    "required_tools": ["NextGen Portal POS", "NETePay Terminal", "Asurion Dealer Support Line"],
                    "safety_precautions": [
                        "Always verify IMEI exactly. 'SIM-Swap' IMEI traps will cause the claim to fail validation, leaving the store with unbillable parts.",
                        "Inspect LCI (Liquid Contact Indicators). A pink/red LCI means a screen-only claim must be escalated to a WUR (Whole Unit Replacement)."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Claim Retrieval & Verification",
                            "instructions": "Query open claim in NextGen Portal. Verify status is 'Approved for In-Store Repair'. Compare hardware IMEI (*#06# or SIM tray) to Portal. If mismatch, halt intake."
                        },
                        {
                            "step_num": 2,
                            "title": "Physical Damage & Geometry Check",
                            "instructions": "Inspect LCI. Check for chassis warping/bent rails. If frame is twisted, decline screen-only repair as the frame will crack the replacement OLED."
                        },
                        {
                            "step_num": 3,
                            "title": "Pre-Repair IQC Checklist",
                            "instructions": "Test Touch grid, Optics (cameras), Audio/Haptics, Connectivity, and Biometrics. Document EVERY pre-existing scuff on the ticket to prevent fraud/liability."
                        },
                        {
                            "step_num": 4,
                            "title": "Signatures & Serialization",
                            "instructions": "Customer signs Data Loss Waiver and Disassembly Auth. Assign OEM SKU to the ticket. Print routing slips for the ESD bin."
                        }
                    ],
                    "pro_tips": [
                        "If the device has a passcode but the customer won't provide it, flag the ticket as 'Untestable / Customer Assumes Diagnostic Risk'."
                    ],
                    "post_qa_checklist": [
                        "Intake ticket generated in under 4 minutes",
                        "All waivers signed in Portal",
                        "OEM part scanned and bound to ticket"
                    ]
                },
                {
                    "id": "uifix_ipad_chemical_release",
                    "category": "apple_ipad",
                    "brand": "Apple",
                    "model_range": "iPad / All Models",
                    "title": "Chemical Adhesive-Release Protocol for Pouch Batteries",
                    "repair_type": "battery",
                    "difficulty": "Advanced",
                    "estimated_time_min": 45,
                    "heat_temp_c": 70,
                    "required_tools": ["99% Isopropyl Alcohol (IPA)", "Blunt Syringe / Fine-Tip Dropper", "Flexible Plastic Pry Cards", "Heavy-Duty Dental Floss / Kevlar Thread", "Fire-Safe Sand Bucket"],
                    "safety_precautions": [
                        "Never puncture or bend lithium-ion battery cells. Puncturing causes immediate sparks and toxic white smoke.",
                        "Never exceed 70°C or use direct localized heat guns on the battery.",
                        "If you smell a sweet, metallic odor (bubblegum/nail polish remover), STOP IMMEDIATELY. Toxic electrolyte gas is leaking. Evacuate device to sand bucket."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Phase 1: Power Isolation",
                            "instructions": "Discharge battery below 25%. Isolate power by inserting a plastic pick between the battery contact and logic board pins."
                        },
                        {
                            "step_num": 2,
                            "title": "Phase 2: Thermal Softening",
                            "instructions": "Place iPad rear-down onto the heating pad at 70°C for 5-10 mins to soften the rigid adhesive matrix."
                        },
                        {
                            "step_num": 3,
                            "title": "Phase 3: Solvent Injection",
                            "instructions": "Elevate one edge 15-20 degrees. Drip 2-3 mL of 99% IPA along the upper seam. Wait 3-5 minutes for capillary action to break the adhesive."
                        },
                        {
                            "step_num": 4,
                            "title": "Phase 4: Mechanical Separation (Floss Saw)",
                            "instructions": "Use the Floss Saw technique (pulling kevlar thread back and forth underneath the cell) or slide a thin plastic card completely horizontally to sever the weakened adhesive. Do not pry upward (The 'Taco' Effect)."
                        }
                    ],
                    "pro_tips": [
                        "Avoid the 'Alcohol Tsunami': Flooding the chassis with too much IPA can permanently dissolve internal membranes of ambient microphones or the Face ID dot projector."
                    ],
                    "post_qa_checklist": [
                        "Old battery removed with zero bending or puncturing",
                        "Chassis perfectly clean of gummy residue before new battery installation",
                        "No IPA leakage into display backlight layers"
                    ]
                },
                {
                    "id": "uifix_ber_escalation",
                    "category": "android_phone",
                    "brand": "Universal / SOP",
                    "model_range": "Catastrophic Damage",
                    "title": "Beyond Economical Repair (BER) Escalation Protocol",
                    "repair_type": "software",
                    "difficulty": "Master Technician",
                    "estimated_time_min": 10,
                    "heat_temp_c": 0,
                    "required_tools": ["NextGen Portal", "High-Resolution Camera", "Asurion Dealer Support"],
                    "safety_precautions": [
                        "Executing a standard repair on a BER device transfers liability for future hardware failures to the technician and store.",
                        "If battery thermal runaway has occurred (soot/charring), isolate hardware immediately."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Identification of Catastrophic Failure",
                            "instructions": "Identify BER conditions: Frame shearing, logic board fracture, triggered LCI (pink/red) with galvanic corrosion on ICs, or repair cost exceeding secondary market value."
                        },
                        {
                            "step_num": 2,
                            "title": "Photographic Documentation",
                            "instructions": "Capture high-resolution photographic evidence of the structural or liquid damage."
                        },
                        {
                            "step_num": 3,
                            "title": "Status Modification & Claim Release",
                            "instructions": "Update NextGen Portal job status to 'Unrepairable / BER' and attach photos. Contact Asurion Dealer Support to release the IMEI claim lock so the customer can transition to a WUR (Whole Unit Replacement)."
                        },
                        {
                            "step_num": 4,
                            "title": "Customer Conversion & Handback",
                            "instructions": "Inform customer physical repair is aborted. Direct them to Asurion to pay the WUR deductible. Reassemble the damaged device to exact intake state. Close Portal ticket as $0 balance."
                        }
                    ],
                    "pro_tips": [
                        "Never attempt to clean extensive liquid corrosion on an Asurion insurance claim—it voids the WUR transition capability if you fail to fix it."
                    ],
                    "post_qa_checklist": [
                        "Photographic evidence attached to Portal ticket",
                        "Asurion claim lock successfully released",
                        "Device returned to customer in exact intake condition"
                    ]
                },
                # ==========================================
                # APPLE IPHONE GUIDES
                # ==========================================
                {
                    "id": "iphone_screen_truetone",
                    "category": "apple_iphone",
                    "brand": "Apple",
                    "model_range": "iPhone X to 16 Pro Max",
                    "title": "OLED / Screen Replacement & TrueTone / EEPROM Serialization",
                    "repair_type": "screen",
                    "difficulty": "Intermediate",
                    "estimated_time_min": 30,
                    "heat_temp_c": 75,
                    "required_tools": ["Pentalobe P2 (0.8mm)", "Tri-Point Y000 (0.6mm)", "Phillips PH000", "iFlex / iSesamo pry tool", "Suction handle", "99% Isopropyl Alcohol", "JCID V1SE or QianLi iCopy Plus Programmer", "Pre-cut waterproof seal adhesive"],
                    "safety_precautions": [
                        "Discharge battery below 25% to prevent thermal runaway if punctured.",
                        "DISCONNECT BATTERY FIRST before touching display, touch, or sensor flex cables.",
                        "Do not damage the proximity/flood illuminator flex on the ear speaker assembly—Face ID is paired to the logic board."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Lower Pentalobe Removal & Thermal Pre-Heat",
                            "instructions": "Remove the two 0.8mm Pentalobe screws flanking the Lightning / USB-C port. Place device on heating pad at 75°C for 2.5 minutes to soften perimeter waterproof adhesive."
                        },
                        {
                            "step_num": 2,
                            "title": "Display Separation & Book-Fold Opening",
                            "instructions": "Apply suction handle to bottom-left glass. Insert thin iFlex blade into seam with a drop of 99% IPA. Slice adhesive around perimeter. Open screen strictly like a book (swing to the right for iPhone 11 and earlier, swing to the left for iPhone 12/13/14/15/16). Never open beyond 90 degrees."
                        },
                        {
                            "step_num": 3,
                            "title": "Connector Bracket Removal & Battery Isolation",
                            "instructions": "Remove Tri-Point Y000 screws holding the motherboard battery and display EMI shield. Use nylon spudger to pry battery connector up FIRST, killing all power rails."
                        },
                        {
                            "step_num": 4,
                            "title": "Display Disconnection & Ear Speaker Flex Transfer",
                            "instructions": "Disconnect display flex, touch flex, and ear speaker sensor flex. Remove ear speaker assembly from broken screen using hot air (60°C) to peel microphone and proximity sensor without tearing gold traces. Transfer carefully to new display."
                        },
                        {
                            "step_num": 5,
                            "title": "TrueTone & Display Serial Cloning",
                            "instructions": "Connect original display to JCID V1SE / QianLi Programmer. Read MTSN / EEPROM data. Disconnect original, connect new display, and execute WRITE. For iPhone 11+, transfer original Touch IC chip or use JCID tag-on flex if eliminating 'Important Display Message' alert."
                        },
                        {
                            "step_num": 6,
                            "title": "Gasket Installation & Reassembly",
                            "instructions": "Clean old glue residue with 99% IPA. Install fresh OEM perimeter waterproof gasket. Connect display flexes, connect battery connector last. Fasten EMI shields. Press display evenly into frame until clips snap flush. Reinstall bottom P2 screws."
                        }
                    ],
                    "pro_tips": [
                        "Keep screws organized by exact placement on a magnetic mat; putting a longer screw into a short standoff causes irreparable 'Long Screw Damage' by severing motherboard data traces beneath the standoff.",
                        "Soft OLED panels are identical to Apple OEM (flexible substrate, resilient against drops). Avoid cheap Hard OLEDs or Incell LCDs on flagship models as they consume 30% more battery and crack easily."
                    ],
                    "post_qa_checklist": [
                        "TrueTone toggle appears in Control Center brightness slider",
                        "Face ID operates cleanly at multiple angles",
                        "Touch digitization passes full drag-grid test across all keyboard keys",
                        "Proximity sensor blanks screen when ear is placed against receiver",
                        "Auto-brightness adjusts to ambient light changes"
                    ]
                },
                {
                    "id": "iphone_battery_bms",
                    "category": "apple_iphone",
                    "brand": "Apple",
                    "model_range": "iPhone XS to 16 Series",
                    "title": "Battery Replacement, BMS Board Welding & Cycle Reset",
                    "repair_type": "battery",
                    "difficulty": "Advanced",
                    "estimated_time_min": 40,
                    "heat_temp_c": 70,
                    "required_tools": ["Pentalobe P2", "Tri-Point Y000", "Spot Welder (QianLi Macaron / Relife)", "BMS Tag-on Flex", "JCID V1SE / QianLi Programmer", "99% Isopropyl alcohol", "Kapton Tape", "OEM Battery Adhesive Pull Tabs"],
                    "safety_precautions": [
                        "Never puncture or bend lithium-ion battery cells. Puncturing causes immediate sparks and toxic white smoke.",
                        "Use only plastic or ceramic tools near battery leads to prevent shorting anode to cathode."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Chassis Opening & Battery Isolation",
                            "instructions": "Open screen to 90 degrees. Disconnect battery connector immediately."
                        },
                        {
                            "step_num": 2,
                            "title": "Adhesive Pull-Tab Extraction",
                            "instructions": "Grasp black adhesive pull tabs at top and bottom of battery. Pull slowly and horizontally at a 15-degree angle. If tab snaps, apply 3 drops of 99% IPA under battery edge and heat rear housing to 70°C for 2 minutes, then slide plastic card underneath."
                        },
                        {
                            "step_num": 3,
                            "title": "Original BMS PCB Transplant (100% Health & No Warning)",
                            "instructions": "Peel Kapton wrap from original battery top. Snip nickel tabs clean from old cell. Take new high-capacity replacement cell (core only, without BMS). Align original BMS board nickel tabs with new cell terminals. Use battery spot welder at Level 4 pulse to create 4 solid weld spots on positive and negative tabs."
                        },
                        {
                            "step_num": 4,
                            "title": "BMS Tag-on Flex & Cycle Reset",
                            "instructions": "Attach JCID tag-on flex to battery BMS. Connect to programmer to clear battery cycle count to 0 and reset Health to 100%. Insulate all exposed solder joints with Kapton tape and wrap with OEM battery tape."
                        },
                        {
                            "step_num": 5,
                            "title": "Installation & Calibration",
                            "instructions": "Install fresh OEM double-sided pull tabs. Seat battery firmly in chassis. Perform a hard reset (Volume Up, Volume Down, hold Power) to calibrate the fuel gauge IC."
                        }
                    ],
                    "pro_tips": [
                        "For rapid customer turnarounds where 100% Battery Health display is not mandatory, install standard premium TI-cell battery. Advise customer that Battery Health menu will display 'Important Battery Message' but battery runs at full peak performance."
                    ],
                    "post_qa_checklist": [
                        "Battery Health shows 100% with Peak Performance Capability",
                        "Device draws 2.1A - 3.0A at 9V on USB Power Delivery fast charger",
                        "Wireless Qi charging triggers cleanly without excessive thermal rise",
                        "No sudden battery drop under 100% CPU benchmark stress"
                    ]
                },
                {
                    "id": "iphone_15_16_usbc_port",
                    "category": "apple_iphone",
                    "brand": "Apple",
                    "model_range": "iPhone 15 / 15 Pro / 16 / 16 Pro Max",
                    "title": "USB-C Charge Port Dock Flex & Action Button Assembly",
                    "repair_type": "charge_port",
                    "difficulty": "Intermediate",
                    "estimated_time_min": 45,
                    "heat_temp_c": 75,
                    "required_tools": ["Pentalobe P2", "Tri-Point Y000", "Phillips PH000", "Standoff Bit", "99% IPA", "Tweezers", "OEM USB-C Dock Flex"],
                    "safety_precautions": [
                        "On iPhone 15/16 series, the back glass opens independently from the front screen. Remove back glass for dock and battery access.",
                        "Do not damage the bottom microphone acoustic mesh when seating the port."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Rear Glass Removal",
                            "instructions": "Remove bottom P2 screws. Heat rear glass to 75°C. Open rear glass to the right side and disconnect wireless charging flex."
                        },
                        {
                            "step_num": 2,
                            "title": "Taptic Engine & Loudspeaker Extraction",
                            "instructions": "Unscrew and remove the Taptic Engine and lower loudspeaker assembly to expose the USB-C dock flex."
                        },
                        {
                            "step_num": 3,
                            "title": "USB-C Dock Port Replacement",
                            "instructions": "Unscrew the USB-C metal bracket screws. Apply 2 drops of 99% IPA to release dock adhesive. Seat new OEM dock flex with dual microphones."
                        },
                        {
                            "step_num": 4,
                            "title": "Reassembly & Seal",
                            "instructions": "Reinstall loudspeaker, Taptic Engine, and reconnect dock flex to logic board. Install new rear glass perimeter seal and clamp."
                        }
                    ],
                    "pro_tips": [
                        "iPhone 15 and 16 dock ports feature USB 3.0 (10Gbps on Pro models). Ensure replacement flex is Pro-rated if working on 15 Pro / 16 Pro to preserve high-speed data transfer."
                    ],
                    "post_qa_checklist": [
                        "Fast charging negotiates 9V / 3A (27W PD)",
                        "Microphone 1 and Microphone 2 record clear audio in Voice Memos and Loudspeaker calls",
                        "Taptic Engine provides crisp haptic clicks on Action Button press"
                    ]
                },
                {
                    "id": "iphone_microsoldering_vdd_main",
                    "category": "apple_iphone",
                    "brand": "Apple",
                    "model_range": "iPhone X to 16 Pro Max (Sandwich Boards)",
                    "title": "Logic Board Sandwich Separation & PP_VDD_MAIN Short Detection",
                    "repair_type": "microsoldering",
                    "difficulty": "Master Technician",
                    "estimated_time_min": 60,
                    "heat_temp_c": 190,
                    "required_tools": ["Mijing / QianLi Heating Pre-Heater Station (185-195°C)", "Stereo Microscope", "Thermal Imaging Camera", "DC Bench Power Supply", "Fluke Multimeter", "Low-melt Solder Paste (183°C)", "Middle Layer Reballing Stencil"],
                    "safety_precautions": [
                        "Do not overheat past 200°C to avoid blistering CPU / NAND underfill.",
                        "Always limit DC power supply to 4.0V and 1.5A when injecting voltage into PP_VDD_MAIN."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "DC Power Supply Benchmark Diagnostics",
                            "instructions": "Connect iPower cable to battery connector. If current draws 1.0A - 2.5A immediately before pressing power button, there is a hard short on PP_VDD_MAIN or PP_VDD_BOOST."
                        },
                        {
                            "step_num": 2,
                            "title": "Double-Decker Logic Board Separation",
                            "instructions": "Place logic board on model-specific preheater plate set to 190°C. When molten, gently lift top board (AP logic) from bottom board (RF baseband) vertically with zero shear force."
                        },
                        {
                            "step_num": 3,
                            "title": "Short Isolation with Thermal Camera",
                            "instructions": "In Diode Mode, probe PP_VDD_MAIN (normal ~0.380V). If 0.000V, inject 3.8V @ 1.5A into the rail. View board under thermal camera to locate glowing capacitor."
                        },
                        {
                            "step_num": 4,
                            "title": "Component Removal & Diode Retest",
                            "instructions": "Remove shorted capacitor using micro-hot air (360°C). Retest diode mode on PP_VDD_MAIN. Value should restore to ~0.380V."
                        },
                        {
                            "step_num": 5,
                            "title": "Middle Layer Reballing & Re-joining",
                            "instructions": "Wick old solder from interposer pads. Align stencil, apply 183°C solder paste. Reflow boards on preheater at 195°C."
                        }
                    ],
                    "pro_tips": [
                        "90% of sudden death / no power iPhones are caused by a single shorted 0201 ceramic filter capacitor on VDD_MAIN next to the audio codec or WiFi module."
                    ],
                    "post_qa_checklist": [
                        "Board draws 0.000A standby current before prompt to boot",
                        "Boots cleanly into iOS without panic logs in Analytics",
                        "Cellular modem registers LTE/5G and SIM"
                    ]
                },

                # ==========================================
                # APPLE IPAD GUIDES
                # ==========================================
                {
                    "id": "ipad_digitizer_glass",
                    "category": "apple_ipad",
                    "brand": "Apple",
                    "model_range": "iPad 7th / 8th / 9th / 10th Gen & iPad Air",
                    "title": "Air-Gap Digitizer Glass Replacement (Non-Laminated Models)",
                    "repair_type": "screen",
                    "difficulty": "Intermediate",
                    "estimated_time_min": 45,
                    "heat_temp_c": 90,
                    "required_tools": ["Heating Mat (90°C)", "iFlex / Guitar picks (plastic)", "Phillips PH000", "Anti-dust air blower", "T-7000 / 3M Primer 94"],
                    "safety_precautions": [
                        "Do not slide metal tools deep into the right side of the frame where the digitizer flex resides.",
                        "Protect the exposed LCD display from dust and fingerprints."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Heating & Adhesive Softening",
                            "instructions": "Place iPad face down on 90°C heating mat for 5 minutes until perimeter glass reaches 80°C."
                        },
                        {
                            "step_num": 2,
                            "title": "Glass Separation without LCD Damage",
                            "instructions": "Insert razor blade into top corner, insert plastic picks, and cut through thick black foam adhesive. Swing cracked glass open to the right side like a book."
                        },
                        {
                            "step_num": 3,
                            "title": "LCD Unscrewing & Isolation",
                            "instructions": "Remove 4 corner Phillips screws holding LCD panel. Lift LCD, disconnect battery isolation pick, and disconnect LCD and digitizer flex cables."
                        },
                        {
                            "step_num": 4,
                            "title": "Home Button / Touch ID Transfer",
                            "instructions": "Apply heat (70°C) to bottom bezel. Peel original Home Button cable without tearing thin membrane to preserve Touch ID."
                        },
                        {
                            "step_num": 5,
                            "title": "Housing Bevel Straightening & Dust Removal",
                            "instructions": "Straighten dented aluminum corners. Blow dust off LCD. Apply 3M Primer 94 and install new digitizer glass."
                        }
                    ],
                    "pro_tips": [
                        "Always test touch drawing across 100% of the screen BEFORE pressing the glass adhesive into the housing frame."
                    ],
                    "post_qa_checklist": [
                        "Touch ID unlocks instantly with enrolled finger",
                        "Apple Pencil tracks smoothly across full glass surface",
                        "No glass lifting at corners due to warped frame"
                    ]
                },
                {
                    "id": "ipad_pro_m4_screen",
                    "category": "apple_ipad",
                    "brand": "Apple",
                    "model_range": "iPad Pro 11 / 12.9 / 13 (M1, M2, M4 Tandem OLED)",
                    "title": "Laminated Tandem OLED / Liquid Retina XDR Screen Swap",
                    "repair_type": "screen",
                    "difficulty": "Advanced",
                    "estimated_time_min": 50,
                    "heat_temp_c": 80,
                    "required_tools": ["Heating Mat (80°C)", "Torx T3 / T4", "iFlex", "Suction Pliers", "OEM Adhesive Tape", "Face ID Transfer Bracket"],
                    "safety_precautions": [
                        "Laminated screen combines ultra-thin OLED/LCD and digitizer into single fused unit. Handle strictly by frame edges.",
                        "Disconnect battery screw blocker before disconnecting display flex."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Perimeter Heat Softening",
                            "instructions": "Heat screen to 80°C for 4 minutes. Use suction handle and thin plastic picks to release waterproof perimeter tape."
                        },
                        {
                            "step_num": 2,
                            "title": "Display Bracket Unscrewing",
                            "instructions": "Tilt display up to 45 degrees. Remove Torx screws holding display FPC metal cover. Disconnect display and ambient light sensor flexes."
                        },
                        {
                            "step_num": 3,
                            "title": "Front Sensor Transfer",
                            "instructions": "Transfer TrueDepth / Face ID sensor module carefully using hot air (60°C) to prevent sensor crystal fracture."
                        },
                        {
                            "step_num": 4,
                            "title": "Adhesive Installation & Bonding",
                            "instructions": "Install pre-cut perimeter adhesive. Reconnect display, test 120Hz ProMotion touch and brightness, snap flush into aluminum chassis."
                        }
                    ],
                    "pro_tips": [
                        "120Hz ProMotion panels require precision FPC alignment. If screen exhibits touch jitter, clean connector with contact cleaner and reseat."
                    ],
                    "post_qa_checklist": [
                        "120Hz ProMotion high refresh rate active",
                        "Face ID operates cleanly at landscape and portrait orientations",
                        "Apple Pencil hover and tilt response verified"
                    ]
                },
                {
                    "id": "ipad_usbc_lightning_port",
                    "category": "apple_ipad",
                    "brand": "Apple",
                    "model_range": "iPad 6th-10th Gen, iPad Pro 11 / 12.9",
                    "title": "Lightning & USB-C Dock Port Micro-Soldering Replacement",
                    "repair_type": "charge_port",
                    "difficulty": "Advanced",
                    "estimated_time_min": 50,
                    "heat_temp_c": 350,
                    "required_tools": ["Hot Air Rework Station (Quick 861DW)", "Soldering Iron with J-tip", "Lead-free solder wire", "Amtech NC-559 Flux", "Solder Wick"],
                    "safety_precautions": [
                        "Shield plastic battery connectors and CPU shield with thick Kapton tape before applying hot air."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Board Removal & Thermal Shielding",
                            "instructions": "Remove logic board from chassis. Cover nearby ICs with double-layer Kapton tape."
                        },
                        {
                            "step_num": 2,
                            "title": "Port Desoldering",
                            "instructions": "Add low-melt alloy solder to all 36 dock pins. Apply hot air at 350°C from underside of board until port slides off smoothly."
                        },
                        {
                            "step_num": 3,
                            "title": "Pad Preparation & Cleaning",
                            "instructions": "Apply flux and clean pads with solder wick. Ensure all 36 gold traces are flat, shiny, and unbroken."
                        },
                        {
                            "step_num": 4,
                            "title": "New Port Alignment & Drag Soldering",
                            "instructions": "Seat new OEM port. Anchor ground mounting lugs first. Apply flux to pins and perform micro drag-soldering with fine J-tip."
                        }
                    ],
                    "pro_tips": [
                        "If a customer yanked the cable, inspect pads under microscope for ripped traces and run 0.02mm enameled jumper wires if needed."
                    ],
                    "post_qa_checklist": [
                        "Charges in both standard and inverted cable orientations",
                        "Draws 2.4A on Lightning / 3.0A (30W PD) on USB-C",
                        "Data transfer connects cleanly to computer"
                    ]
                },

                # ==========================================
                # ANDROID PHONES (SAMSUNG / PIXEL / MOTO)
                # ==========================================
                {
                    "id": "samsung_curved_amoled_frame",
                    "category": "android_phone",
                    "brand": "Samsung",
                    "model_range": "Galaxy S20 to S24 Ultra & Note Series",
                    "title": "Curved Dynamic AMOLED Screen & Chassis Swap",
                    "repair_type": "screen",
                    "difficulty": "Intermediate",
                    "estimated_time_min": 35,
                    "heat_temp_c": 80,
                    "required_tools": ["Hot Plate / Heat Gun (80°C)", "Phillips PH000", "iSesamo tool", "Curved suction pliers", "99% Isopropyl alcohol", "B-7000 / OEM rear glass adhesive", "Samsung *#0*# Service Calibration Menu"],
                    "safety_precautions": [
                        "Do not bend the glass back panel during removal—Samsung rear glass has color film on interior that can peel.",
                        "Disconnect battery flex before unscrewing motherboard or sub-board."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Rear Glass De-Gluing",
                            "instructions": "Heat back cover to 80°C for 3 minutes. Insert thin plastic card with 2 drops of IPA. Slice adhesive along edges, avoiding the camera housing and wireless charging coil."
                        },
                        {
                            "step_num": 2,
                            "title": "Wireless Charging Coil & Motherboard Removal",
                            "instructions": "Remove Phillips PH000 screws holding mid-frame / NFC coil assembly. Unclip mid-frame. Disconnect battery, screen interconnect flex, and sub-board flex. Unscrew and remove main logic board."
                        },
                        {
                            "step_num": 3,
                            "title": "Sub-Board, Battery & Vibrator Transfer",
                            "instructions": "Transfer sub-board (charging port), haptic vibrator motor, and ear speaker into new Service Pack (Screen + Frame assembly). Apply IPA under battery to dissolve stretch adhesive and transfer to new frame."
                        },
                        {
                            "step_num": 4,
                            "title": "Ultrasonic / Optical Fingerprint Calibration",
                            "instructions": "Reassemble logic board, reconnect all flexes, power on. Dial *#0*# in phone dialer. Run SENSOR -> FINGERPRINT TEST -> RE-CALIBRATE to register optical/ultrasonic sensor against new AMOLED panel."
                        },
                        {
                            "step_num": 5,
                            "title": "Back Glass Re-sealing",
                            "instructions": "Clean frame perimeter, apply fresh OEM cut adhesive, clamp rear cover for 15 minutes for IP68 water resistance restoration."
                        }
                    ],
                    "pro_tips": [
                        "Always buy 'Service Pack with Frame' (Official Samsung Service Pack) rather than screen-only glass. Service Pack with frame saves 30 minutes of labor and eliminates crooked edge-fit or glue mess."
                    ],
                    "post_qa_checklist": [
                        "Dial *#0*# and pass Touch (fill all green boxes), RED, GREEN, BLUE sub-pixel test",
                        "Fingerprint sensor enrolls and unlocks reliably within 0.2s",
                        "Both speakers output distortion-free stereo",
                        "Wireless PowerShare operates"
                    ]
                },
                {
                    "id": "samsung_z_fold_hinge_inner_screen",
                    "category": "android_phone",
                    "brand": "Samsung",
                    "model_range": "Galaxy Z Fold 3 / 4 / 5 / 6 & Z Flip",
                    "title": "Folding Ultra-Thin Glass (UTG) & Gear Hinge Dust Service",
                    "repair_type": "screen",
                    "difficulty": "Master Technician",
                    "estimated_time_min": 75,
                    "heat_temp_c": 70,
                    "required_tools": ["Heated Mat (70°C)", "Plastic Micro-Pry Cards", "Phillips PH000", "Hinge alignment jig", "T-7000 adhesive", "Synthetic Watch Grease"],
                    "safety_precautions": [
                        "The inner folding OLED is covered in Ultra-Thin Glass (UTG) that fractures under fingernail pressure. Never press metal tools against inner screen bezel.",
                        "Dual batteries must be disconnected simultaneously."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Outer Screen & Rear Glass Extraction",
                            "instructions": "Heat both outer panels to 70°C. Slice perimeter adhesive and disconnect outer display and rear cover."
                        },
                        {
                            "step_num": 2,
                            "title": "Dual Motherboard Disassembly",
                            "instructions": "Disconnect main board and sub-board interconnect bridge flexes running through the spine hinge."
                        },
                        {
                            "step_num": 3,
                            "title": "Hinge Sweeper De-Gunking",
                            "instructions": "Disassemble hinge spine covers. Clean bristled sweepers with 99% IPA and apply micro-drop of synthetic watch lubricant to dual-axis gears."
                        },
                        {
                            "step_num": 4,
                            "title": "Inner Service Pack Installation",
                            "instructions": "Mount dual boards into new folding Service Pack assembly. Ensure hinge opens 180 degrees dead flat."
                        }
                    ],
                    "pro_tips": [
                        "Most 'won't open fully flat' Z Folds are caused by pocket lint lodged in the gear teeth. Cleaning the hinge gears without replacing the screen restores 180° flat opening in 80% of cases."
                    ],
                    "post_qa_checklist": [
                        "Hinge opens to 180 degrees completely flat with zero crunching sound",
                        "Inner folding OLED displays zero crease dead pixels or touch anomalies",
                        "Flex Mode detects angles between 75° and 115°"
                    ]
                },
                {
                    "id": "pixel_fingerprint_calibration",
                    "category": "android_phone",
                    "brand": "Google Pixel",
                    "model_range": "Pixel 6, 7, 8, 9 Series",
                    "title": "OLED Replacement & Optical Fingerprint Calibration Web Tool",
                    "repair_type": "screen",
                    "difficulty": "Intermediate",
                    "estimated_time_min": 30,
                    "heat_temp_c": 75,
                    "required_tools": ["Heat Pad (75°C)", "Torx T3", "iSesamo", "99% IPA", "Google Pixel Web Calibration Tool (Chrome WebUSB)"],
                    "safety_precautions": [
                        "Optical fingerprint sensor under Pixel displays requires software calibration via Google official web tool after replacement or biometric unlock will permanently fail."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Display Removal from Front",
                            "instructions": "Pixel displays open from the front. Heat perimeter to 75°C, slice adhesive, open like a book from right to left."
                        },
                        {
                            "step_num": 2,
                            "title": "Bracket & Screen Disconnection",
                            "instructions": "Remove Torx T3 screw holding metal FPC bracket. Disconnect display cable."
                        },
                        {
                            "step_num": 3,
                            "title": "WebUSB Fingerprint Calibration",
                            "instructions": "Connect new screen. Boot phone into Fastboot mode. Connect to PC via Chrome browser at `pixelrepair.withgoogle.com`. Select 'Fingerprint Calibration', follow on-screen prompt to calibrate optical scanner, and reboot."
                        },
                        {
                            "step_num": 4,
                            "title": "Adhesive Gasket Sealing",
                            "instructions": "Install fresh perimeter adhesive cut, connect screen, snap into frame."
                        }
                    ],
                    "pro_tips": [
                        "Always restart phone twice after completing Google WebUSB calibration before enrolling new fingerprints."
                    ],
                    "post_qa_checklist": [
                        "Under-display fingerprint enrolls and unlocks in <0.3s",
                        "High brightness mode triggers under direct flashlight",
                        "Smooth 120Hz display refresh active"
                    ]
                },
                {
                    "id": "android_flashing_unbrick_odin",
                    "category": "android_phone",
                    "brand": "Samsung / Google Pixel",
                    "model_range": "Universal Android / Odin 3.14.4 / Fastboot",
                    "title": "Firmware Flashing, Bootloop Recovery & Unbricking",
                    "repair_type": "software",
                    "difficulty": "Intermediate",
                    "estimated_time_min": 25,
                    "heat_temp_c": 0,
                    "required_tools": ["Windows PC (WSL2 / AI-BS Rig)", "Odin v3.14.4 (Samsung) or Android Platform Tools ADB/Fastboot", "SamFirm / Frija 4-File Firmware Downloader", "High-speed USB 3.0 Type-C Cable"],
                    "safety_precautions": [
                        "Ensure battery is charged to at least 40% before flashing.",
                        "Use 'HOME_CSC' file if customer wishes to preserve photos/data; use 'CSC' if performing a full clean factory wipe."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Download Official 4-File Firmware",
                            "instructions": "Use Frija tool to download binary-matching firmware (BL, AP, CP, CSC) for exact model number."
                        },
                        {
                            "step_num": 2,
                            "title": "Enter Download Mode",
                            "instructions": "Hold Volume Down + Volume Up simultaneously and plug in USB-C cable connected to PC. Press Volume Up to confirm Download / Odin Mode."
                        },
                        {
                            "step_num": 3,
                            "title": "Odin Slot Population & Flash Execution",
                            "instructions": "Load BL into BL slot, AP into AP slot, CP into CP slot, and HOME_CSC into CSC slot. Click START and allow 4-6 minutes for NAND partition writes."
                        },
                        {
                            "step_num": 4,
                            "title": "Reboot & Cache Verification",
                            "instructions": "Upon 'PASS!' message, device reboots. Enter recovery mode and wipe cache partition."
                        }
                    ],
                    "pro_tips": [
                        "You can never downgrade Samsung bootloader binaries (e.g., cannot flash Binary 2 on a Binary 3 board)."
                    ],
                    "post_qa_checklist": [
                        "Device boots cleanly without crashing",
                        "IMEI and Baseband firmware intact (*#06# valid)",
                        "Google Play Protect certification passes"
                    ]
                },

                # ==========================================
                # ANDROID TABLETS
                # ==========================================
                {
                    "id": "android_tablet_battery_port",
                    "category": "android_tablet",
                    "brand": "Samsung / Lenovo / Amazon Fire",
                    "model_range": "Galaxy Tab A/S Series, Lenovo Tab, Amazon Fire HD",
                    "title": "Tablet Battery Replacement & Sub-Board Port Repair",
                    "repair_type": "battery",
                    "difficulty": "Beginner",
                    "estimated_time_min": 30,
                    "heat_temp_c": 75,
                    "required_tools": ["Plastic Spudger / Pry Cards", "Phillips PH000", "99% Isopropyl alcohol", "B-7000 adhesive", "Multimeter"],
                    "safety_precautions": [
                        "Take care around perimeter clips on snap-fit plastic tablet housings.",
                        "Disconnect battery flex cable immediately once back cover is off."
                    ],
                    "steps": [
                        {
                            "step_num": 1,
                            "title": "Chassis Unclipping",
                            "instructions": "Insert plastic spudger into seam between glass and plastic back cover. Slide around perimeter to pop snap clips."
                        },
                        {
                            "step_num": 2,
                            "title": "Battery & Port Disconnection",
                            "instructions": "Disconnect battery connector from motherboard. Unscrew 3 Phillips screws holding USB-C charging daughterboard. Disconnect ribbon cable."
                        },
                        {
                            "step_num": 3,
                            "title": "Battery De-Gluing & Replacement",
                            "instructions": "Apply 99% IPA under battery. Use broad plastic card to lift battery cell cleanly. Seat replacement battery and connect new charging sub-board."
                        },
                        {
                            "step_num": 4,
                            "title": "Snap-Fit Reassembly",
                            "instructions": "Align motherboard connectors. Press plastic shell firmly until all perimeter clips click flush."
                        }
                    ],
                    "pro_tips": [
                        "On budget tablets, loose charging ports are usually caused by cracked solder joints on the surface-mount USB legs. Re-flowing the 5 pins with fresh leaded solder fixes it in 5 minutes."
                    ],
                    "post_qa_checklist": [
                        "Draws stable 5V @ 2.0A charging current",
                        "Battery percentage increments smoothly during charging",
                        "SD Card reader and speakers functional"
                    ]
                }
            ]

            for g in guides:
                conn.execute("""
                    INSERT OR REPLACE INTO repair_guides (
                        id, category, brand, model_range, title, repair_type, difficulty,
                        estimated_time_min, heat_temp_c, required_tools, safety_precautions,
                        steps, pro_tips, post_qa_checklist
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    g["id"], g["category"], g["brand"], g["model_range"], g["title"],
                    g["repair_type"], g["difficulty"], g["estimated_time_min"], g["heat_temp_c"],
                    json.dumps(g["required_tools"]), json.dumps(g["safety_precautions"]),
                    json.dumps(g["steps"]), json.dumps(g["pro_tips"]), json.dumps(g["post_qa_checklist"])
                ))

            # Diagnostic Troubleshooting Trees Seed
            trees = [
                {
                    "id": "diag_no_power_dc_bench",
                    "symptom": "No Power / Completely Dead (Won't Turn On)",
                    "category": "universal",
                    "primary_suspects": ["Dead Battery", "Torn Screen Flex", "PP_VDD_MAIN Shorted Cap", "Tristar / Hydra USB IC Failure", "PMIC (Power Management IC)"],
                    "current_draw_analysis": [
                        {"draw": "0.000A (No draw on power button)", "cause": "Broken battery connector, severed power button flex, or dead PMIC crystal oscillator."},
                        {"draw": "0.05A - 0.08A (Stuck immediately)", "cause": "CPU / NAND communication failure or missing I2C / PMU power rail."},
                        {"draw": "0.20A - 0.45A (Static freeze)", "cause": "Blown secondary power rail (e.g. PP_1V8_S2 or PP_GPU short)."},
                        {"draw": "1.0A - 3.0A+ (Immediate max current draw before power button)", "cause": "Direct hard short on PP_VDD_MAIN, PP_BATT_VCC, or VDD_BOOST."}
                    ],
                    "multimeter_probe_steps": [
                        "Switch multimeter to Diode Mode (Red probe on Ground / Shield, Black probe on rail test points).",
                        "Probe Battery VCC: Expect ~0.450V. If 0.000V -> Battery connector short.",
                        "Probe VDD_MAIN: Expect ~0.380V. If 0.000V -> Shorted decoupling capacitor.",
                        "Probe 1.8V Always-On: Expect ~0.320V. If missing -> PMIC failure."
                    ],
                    "resolution_pathways": [
                        "If VDD_MAIN is shorted: Use Thermal Camera @ 3.8V 1.5A to locate glowing capacitor and remove it.",
                        "If device bootloops at 0.15A - 0.80A: Inspect front ear speaker flex; torn flood illuminator sensor causes reboot panic.",
                        "If device charges with USB tester at 0.00A: Inspect dock port pins for lint, clean with tweezers, or replace dock flex."
                    ]
                },
                {
                    "id": "diag_no_display_black_screen",
                    "symptom": "No Display / Black Screen (Phone Vibrates / Makes Sounds)",
                    "category": "universal",
                    "primary_suspects": ["Cracked OLED Substrate", "Blown Backlight Filter Coil (FL)", "Chestnut / Display PMIC", "Damaged FPC Connector"],
                    "current_draw_analysis": [
                        {"draw": "Normal boot curve (0.2A -> 0.8A -> 1.5A -> drops to 0.1A sleep)", "cause": "Logic board is fully operational; fault is 100% localized to screen assembly or display backlight rail."}
                    ],
                    "multimeter_probe_steps": [
                        "Shine bright flashlight directly at black screen at an angle. If icons are faintly visible -> Backlight circuit failure (blown fuse/filter).",
                        "Inspect motherboard FPC display connector under microscope for bent or burnt pins.",
                        "In Diode Mode, probe display power rails (PP5V7_MESON, PP_DISPLAY_BL_ANODE)."
                    ],
                    "resolution_pathways": [
                        "Test with known-good Premium Soft OLED screen first.",
                        "If still black on iPhone: Bridge blown backlight EMI filter (FL coil) with jumper wire.",
                        "If Samsung Galaxy: Ensure display flex connector is fully seated into sub-board and main board."
                    ]
                },
                {
                    "id": "diag_fast_drain_overheating",
                    "symptom": "Rapid Battery Drain / Phone Gets Burning Hot Around Camera",
                    "category": "universal",
                    "primary_suspects": ["Degraded Battery Internal Short", "Tristar / Hydra IC Partial Leakage", "WiFi Module Internal Short", "Corroded Audio Codec / Baseband"],
                    "current_draw_analysis": [
                        {"draw": "Standby current draw in sleep mode sits at 0.15A - 0.40A instead of dropping to 0.000A - 0.010A", "cause": "VCC leakage on active subsystem."}
                    ],
                    "multimeter_probe_steps": [
                        "Check Tristar tester dock reading (reads 'FAIL' on CC1/CC2 lines if USB IC is burnt from cheap car charger).",
                        "Inspect motherboard under thermal camera while phone is locked in sleep mode."
                    ],
                    "resolution_pathways": [
                        "If USB IC is hot: Replace Tristar / Hydra IC (1610A3 / 1612A1).",
                        "If WiFi module heats up: Separate sandwich board and check WiFi decoupling caps."
                    ]
                }
            ]

            for t in trees:
                conn.execute("""
                    INSERT OR REPLACE INTO diagnostic_trees (
                        id, symptom, category, primary_suspects, current_draw_analysis,
                        multimeter_probe_steps, resolution_pathways
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    t["id"], t["symptom"], t["category"],
                    json.dumps(t["primary_suspects"]), json.dumps(t["current_draw_analysis"]),
                    json.dumps(t["multimeter_probe_steps"]), json.dumps(t["resolution_pathways"])
                ))

            # Micro-Soldering IC Reference Seed
            ics = [
                {
                    "id": "tristar_hydra_usb",
                    "chip_name": "Tristar / Hydra USB Charging Controller",
                    "part_numbers": ["1610A1", "1610A2", "1610A3", "1612A1", "CBTL1612A1"],
                    "function_description": "Manages USB accessory handshake, Lightning orientation detection, CC communication, and 5V USB routing.",
                    "common_symptoms": ["Fake charging (shows lightning bolt but battery % drops)", "Charges only when phone is turned completely off", "Draws 0.20A static sleep current (drains overnight in 3 hours)", "Unable to connect to PC / iTunes error 4013/4014"],
                    "expected_diode_readings": {"PP_TRISTAR_PIN_1": "0.450V", "PP_TRISTAR_PIN_5": "0.380V", "TRISTAR_VBUS": "0.520V"},
                    "replacement_difficulty": "Advanced (BGA 36-ball micro-soldering @ 340°C)"
                },
                {
                    "id": "chestnut_display_pmic",
                    "chip_name": "Chestnut / Display Power Management IC",
                    "part_numbers": ["TPS65730", "65730AOP", "TI-Chestnut"],
                    "function_description": "Generates +5.7V (PP5V7_MESON) and -5.7V (PN5V7_MESON) dual rails to power the OLED / LCD matrix and touch digitizer.",
                    "common_symptoms": ["Black screen while phone boots normally", "Lines on screen or touch unresponsive with good screen", "0.25A short on board before boot"],
                    "expected_diode_readings": {"PP5V7_MESON": "0.540V", "PN5V7_MESON": "0.590V"},
                    "replacement_difficulty": "Advanced (BGA underfill removal @ 320°C)"
                },
                {
                    "id": "audio_codec_u3101",
                    "chip_name": "Audio Codec IC",
                    "part_numbers": ["338S00105", "338S00248", "Cirrus Logic Audio"],
                    "function_description": "Decodes microphone inputs, speaker outputs, and ear-piece DAC channels.",
                    "common_symptoms": ["Voice Memos recording button greyed out", "Loudspeaker icon greyed out on calls", "Phone takes 3 to 5 minutes to boot past Apple logo (Loop Disease)", "Audio IC C12 pad severed trace"],
                    "expected_diode_readings": {"PP_1V8_AUDIO": "0.320V", "C12_I2S0_AP_TO_CODEC_MCLK": "0.450V"},
                    "replacement_difficulty": "Intermediate (Micro-jumper wire on C12 pad + reball)"
                }
            ]

            for ic in ics:
                conn.execute("""
                    INSERT OR REPLACE INTO ic_reference (
                        id, chip_name, part_numbers, function_description,
                        common_symptoms, expected_diode_readings, replacement_difficulty
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    ic["id"], ic["chip_name"], json.dumps(ic["part_numbers"]),
                    ic["function_description"], json.dumps(ic["common_symptoms"]),
                    json.dumps(ic["expected_diode_readings"]), ic["replacement_difficulty"]
                ))

            conn.commit()

    def get_all_guides(self, category: Optional[str] = None, repair_type: Optional[str] = None, difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches repair guides filtered optionally by category, repair_type, and difficulty."""
        with self._get_connection() as conn:
            query = "SELECT * FROM repair_guides WHERE 1=1"
            params = []
            if category and category != "all":
                query += " AND category = ?"
                params.append(category)
            if repair_type and repair_type != "all":
                query += " AND repair_type = ?"
                params.append(repair_type)
            if difficulty and difficulty != "all":
                query += " AND difficulty = ?"
                params.append(difficulty)
            
            query += " ORDER BY category, title ASC;"
            rows = conn.execute(query, params).fetchall()
            
            guides = []
            for r in rows:
                d = dict(r)
                d["required_tools"] = json.loads(d["required_tools"])
                d["safety_precautions"] = json.loads(d["safety_precautions"])
                d["steps"] = json.loads(d["steps"])
                d["pro_tips"] = json.loads(d["pro_tips"])
                d["post_qa_checklist"] = json.loads(d["post_qa_checklist"])
                guides.append(d)
            return guides

    def get_guide_by_id(self, guide_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM repair_guides WHERE id = ?;", (guide_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["required_tools"] = json.loads(d["required_tools"])
            d["safety_precautions"] = json.loads(d["safety_precautions"])
            d["steps"] = json.loads(d["steps"])
            d["pro_tips"] = json.loads(d["pro_tips"])
            d["post_qa_checklist"] = json.loads(d["post_qa_checklist"])
            return d

    def get_diagnostic_trees(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM diagnostic_trees;").fetchall()
            trees = []
            for r in rows:
                d = dict(r)
                d["primary_suspects"] = json.loads(d["primary_suspects"])
                d["current_draw_analysis"] = json.loads(d["current_draw_analysis"])
                d["multimeter_probe_steps"] = json.loads(d["multimeter_probe_steps"])
                d["resolution_pathways"] = json.loads(d["resolution_pathways"])
                trees.append(d)
            return trees

    def get_ic_references(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM ic_reference;").fetchall()
            ics = []
            for r in rows:
                d = dict(r)
                d["part_numbers"] = json.loads(d["part_numbers"])
                d["common_symptoms"] = json.loads(d["common_symptoms"])
                d["expected_diode_readings"] = json.loads(d["expected_diode_readings"])
                ics.append(d)
            return ics

    def create_repair_ticket(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO repair_tickets (
                    client_id, customer_name, customer_phone, device_category,
                    device_model, serial_imei, reported_issue, diagnosis_notes,
                    part_grade_used, parts_cost_usd, labor_charge_usd, total_price_usd, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                data.get("client_id", "stehouwer_publishing"),
                data.get("customer_name", "Walk-In Customer"),
                data.get("customer_phone", ""),
                data.get("device_category", "apple_iphone"),
                data.get("device_model", "iPhone 14 Pro"),
                data.get("serial_imei", ""),
                data.get("reported_issue", "Cracked Screen"),
                data.get("diagnosis_notes", "Touch operational, cracked glass"),
                data.get("part_grade_used", "Premium Soft OLED"),
                float(data.get("parts_cost_usd", 65.0)),
                float(data.get("labor_charge_usd", 60.0)),
                float(data.get("total_price_usd", 125.0)),
                data.get("status", "Checked-In")
            ))
            conn.commit()
            ticket_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM repair_tickets WHERE ticket_id = ?;", (ticket_id,)).fetchone()
            return dict(row)

    def update_ticket_status(self, ticket_id: int, new_status: str, qa_passed: int = 0) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE repair_tickets 
                SET status = ?, qa_passed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE ticket_id = ?;
            """, (new_status, qa_passed, ticket_id))
            conn.commit()
            row = conn.execute("SELECT * FROM repair_tickets WHERE ticket_id = ?;", (ticket_id,)).fetchone()
            return dict(row) if row else None

    def get_repair_tickets(self, client_id: str = "stehouwer_publishing") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM repair_tickets WHERE client_id = ? ORDER BY ticket_id DESC;", (client_id,)).fetchall()
            return [dict(r) for r in rows]


# Global singleton instance
phone_repair_engine = PhoneRepairEngine.get_instance()
