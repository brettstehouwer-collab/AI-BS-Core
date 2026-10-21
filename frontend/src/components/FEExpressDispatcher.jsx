import React, { useState, useEffect } from 'react';

const INITIAL_FALLBACK_LOADS = [
  {
    "load_id": "TR-23750836",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Chicago, IL",
    "dest_city_state": "Milwaukee, WI",
    "equipment_type": "Flatbed (Hotshot) (Full) [10-22-2026]",
    "weight_lbs": 10000.0,
    "total_miles": 91.5,
    "deadhead_miles": 179.3,
    "flat_rate_pay": 600.0,
    "rpm": 6.56,
    "true_rpm": 2.22,
    "broker_name": "DSV Road (Dispatch) \u2022 (541) 630-5024",
    "broker_phone": "(541) 630-5024",
    "broker_email": "FH\nCONTAINERS\n982 - Central Point, OR",
    "score": "Greenlight",
    "priority_tier": 1,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23739199",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Bridgeport, OH",
    "dest_city_state": "Charleston, WV",
    "equipment_type": "Flatbed (Full) [10-21-2026]",
    "weight_lbs": 5000.0,
    "total_miles": 177.8,
    "deadhead_miles": 437.9,
    "flat_rate_pay": 1100.0,
    "rpm": 6.19,
    "true_rpm": 1.79,
    "broker_name": "Atlantic Logistics (Extension in Comments)",
    "broker_phone": "",
    "broker_email": "X139 KASEY@SHIPATLANTIC.COM NO TARP,EDGE PROTECTORS",
    "score": "Greenlight",
    "priority_tier": 1,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750841",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Chicago, IL",
    "dest_city_state": "Waukesha, WI",
    "equipment_type": "Flatbed/Step Deck (Full) [10-22-2026]",
    "weight_lbs": 10000.0,
    "total_miles": 105.2,
    "deadhead_miles": 179.3,
    "flat_rate_pay": 600.0,
    "rpm": 5.7,
    "true_rpm": 2.11,
    "broker_name": "DSV Road (Dispatch) \u2022 (541) 630-5024",
    "broker_phone": "(541) 630-5024",
    "broker_email": "FOSD\nCONTAINERS\n982 - Central Point, OR",
    "score": "Greenlight",
    "priority_tier": 1,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750837",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Chicago, IL",
    "dest_city_state": "Waukesha, WI",
    "equipment_type": "Flatbed/Step Deck (Full) [10-22-2026]",
    "weight_lbs": 10000.0,
    "total_miles": 105.2,
    "deadhead_miles": 179.3,
    "flat_rate_pay": 600.0,
    "rpm": 5.7,
    "true_rpm": 2.11,
    "broker_name": "DSV Road (Dispatch) \u2022 (541) 630-5024",
    "broker_phone": "(541) 630-5024",
    "broker_email": "FOSD\nCONTAINERS\n982 - Central Point, OR",
    "score": "Greenlight",
    "priority_tier": 1,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750835",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Chicago, IL",
    "dest_city_state": "Waukesha, WI",
    "equipment_type": "Flatbed (Hotshot) (Full) [10-22-2026]",
    "weight_lbs": 10000.0,
    "total_miles": 105.2,
    "deadhead_miles": 179.3,
    "flat_rate_pay": 600.0,
    "rpm": 5.7,
    "true_rpm": 2.11,
    "broker_name": "DSV Road (Dispatch) \u2022 (541) 630-5024",
    "broker_phone": "(541) 630-5024",
    "broker_email": "FH\nCONTAINERS\n982 - Central Point, OR",
    "score": "Greenlight",
    "priority_tier": 1,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750834",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Chicago, IL",
    "dest_city_state": "Waukesha, WI",
    "equipment_type": "Flatbed/Step Deck (Full) [10-22-2026]",
    "weight_lbs": 10000.0,
    "total_miles": 105.2,
    "deadhead_miles": 179.3,
    "flat_rate_pay": 600.0,
    "rpm": 5.7,
    "true_rpm": 2.11,
    "broker_name": "DSV Road (Dispatch) \u2022 (541) 630-5024",
    "broker_phone": "(541) 630-5024",
    "broker_email": "FOSD\nCONTAINERS\n982 - Central Point, OR",
    "score": "Greenlight",
    "priority_tier": 1,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750833",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Chicago, IL",
    "dest_city_state": "Waukesha, WI",
    "equipment_type": "Flatbed/Step Deck (Full) [10-22-2026]",
    "weight_lbs": 10000.0,
    "total_miles": 105.2,
    "deadhead_miles": 179.3,
    "flat_rate_pay": 600.0,
    "rpm": 5.7,
    "true_rpm": 2.11,
    "broker_name": "DSV Road (Dispatch) \u2022 (541) 630-5024",
    "broker_phone": "(541) 630-5024",
    "broker_email": "FOSD\nCONTAINERS\n982 - Central Point, OR",
    "score": "Greenlight",
    "priority_tier": 1,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23711965",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Howell, MI",
    "dest_city_state": "Hudson, CO",
    "equipment_type": "Flatbed (Hotshot) (Full) [10-22-2026]",
    "weight_lbs": 10000.0,
    "total_miles": 705.1,
    "deadhead_miles": 104.8,
    "flat_rate_pay": 1175.0,
    "rpm": 1.67,
    "true_rpm": 1.45,
    "broker_name": "Sureway Transportation Co / Anderson Trucking Serv (Mary Anderson) \u2022 (320) 304-6150",
    "broker_phone": "(320) 304-6150",
    "broker_email": "HOTSHOT, NO TARPS, ASK FOR MARY PARTIAL",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23746716",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Fowler, IN",
    "dest_city_state": "Wisconsin Rapi, WI",
    "equipment_type": "Van (Full) [10-22-2026]",
    "weight_lbs": 440.0,
    "total_miles": 755.2,
    "deadhead_miles": 218.8,
    "flat_rate_pay": 1200.0,
    "rpm": 1.59,
    "true_rpm": 1.23,
    "broker_name": "Sureway Transportation Co / Anderson Trucking Serv (Lisa Anderson) \u2022 (320) 534-2221",
    "broker_phone": "(320) 534-2221",
    "broker_email": "ask for lisa",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23747240",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Michigan City, IN",
    "dest_city_state": "Fort Worth, TX",
    "equipment_type": "Flatbed/Step Deck (Partial) [10-22-2026]",
    "weight_lbs": 8000.0,
    "total_miles": 980.1,
    "deadhead_miles": 122.8,
    "flat_rate_pay": 1400.0,
    "rpm": 1.43,
    "true_rpm": 1.27,
    "broker_name": "Sureway Transportation Co / Anderson Trucking Serv (Brian Bjorklund) \u2022 (320) 258-8028",
    "broker_phone": "(320) 258-8028",
    "broker_email": "13FT PARTIAL / TARP / FLAT OR STEP / BRIANBJO@ATS-INC.COM",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23737857",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Michigan City, IN",
    "dest_city_state": "Baton Rouge, LA",
    "equipment_type": "Flatbed/Step Deck (Partial) [10-22-2026]",
    "weight_lbs": 8000.0,
    "total_miles": 937.7,
    "deadhead_miles": 122.8,
    "flat_rate_pay": 1200.0,
    "rpm": 1.28,
    "true_rpm": 1.13,
    "broker_name": "Sureway Transportation Co / Anderson Trucking Serv (Brian Bjorklund) \u2022 (320) 258-8028",
    "broker_phone": "(320) 258-8028",
    "broker_email": "10FT PARTIAL / TARP / BRIANBJO@ATS-INC.COM",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23745578",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Michigan City, IN",
    "dest_city_state": "Kenner, LA",
    "equipment_type": "Flatbed/Step Deck (Partial) [10-22-2026]",
    "weight_lbs": 7000.0,
    "total_miles": 938.7,
    "deadhead_miles": 122.8,
    "flat_rate_pay": 1200.0,
    "rpm": 1.28,
    "true_rpm": 1.13,
    "broker_name": "Sureway Transportation Co / Anderson Trucking Serv (Brian Bjorklund) \u2022 (320) 258-8028",
    "broker_phone": "(320) 258-8028",
    "broker_email": "12FT PARTIAL / NO TARP / BRIANBJO@ATS-INC.COM",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750721",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Apple Creek, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Flatbed (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 750.3,
    "deadhead_miles": 334.7,
    "flat_rate_pay": 900.0,
    "rpm": 1.2,
    "true_rpm": 0.83,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 5 loose attachments, no tarps, 6,000 lbs -Conestoga Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750722",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Apple Creek, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Flatbed/Step Deck (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 750.3,
    "deadhead_miles": 334.7,
    "flat_rate_pay": 900.0,
    "rpm": 1.2,
    "true_rpm": 0.83,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 5 loose attachments, no tarps, 6,000 lbs -Conestoga Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750731",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Apple Creek, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Step Deck (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 750.3,
    "deadhead_miles": 334.7,
    "flat_rate_pay": 900.0,
    "rpm": 1.2,
    "true_rpm": 0.83,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 5 loose attachments, no tarps, 6,000 lbs -Conestoga Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750733",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Apple Creek, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Double Drop (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 750.3,
    "deadhead_miles": 334.7,
    "flat_rate_pay": 900.0,
    "rpm": 1.2,
    "true_rpm": 0.83,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 5 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750734",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "Apple Creek, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Double Drop (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 750.3,
    "deadhead_miles": 334.7,
    "flat_rate_pay": 900.0,
    "rpm": 1.2,
    "true_rpm": 0.83,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 5 loose attachments, no tarps, 6,000 lbs -Landoll Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750521",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Flatbed (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs -Conestoga Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750525",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Flatbed/Step Deck (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs -Conestoga Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750528",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Step Deck (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs -Conestoga Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750532",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Double Drop (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750533",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Double Drop (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs -Landoll Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750535",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Flatbed (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750536",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Flatbed/Step Deck (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750548",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Flatbed (Hotshot) (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750549",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Lowboy (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750572",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Lowboy (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs -OR RGN Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750573",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Step Deck (Removable Gooseneck) (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750615",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Step Deck (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  },
  {
    "load_id": "TR-23750705",
    "source": "Trulos Public Board (Live)",
    "origin_city_state": "South Vienna, OH",
    "dest_city_state": "Jefferson, NH",
    "equipment_type": "Step Deck (Partial) [10-21-2026]",
    "weight_lbs": 6000.0,
    "total_miles": 867.6,
    "deadhead_miles": 327.8,
    "flat_rate_pay": 700.0,
    "rpm": 0.81,
    "true_rpm": 0.59,
    "broker_name": "Ampersand Transport ((856) 807-5810 Milton)",
    "broker_phone": "",
    "broker_email": "(856) 807-5810 Milton, 6 loose attachments, no tarps, 6,000 lbs -OR RGN Requested-",
    "score": "Reject",
    "priority_tier": 3,
    "status": "LIVE",
    "created_at": "2026-10-21 19:25:08"
  }
];

function evaluateLocally(payload) {
  const eqLower = (payload.equipment_type || '').toLowerCase();
  const allowed = ["24'", "26'", 'box truck', 'straight truck', 'boxtruck', 'box'];
  const rejected = ["53'", 'dry van', 'flatbed', 'reefer', 'semi', 'stepdeck'];
  const isBox = !(rejected.some(r => eqLower.includes(r)) && !['box', 'straight'].some(k => eqLower.includes(k))) &&
                allowed.some(k => eqLower.includes(k));
  const weight = parseFloat(payload.weight_lbs || 0);
  const underWeight = weight <= 10000.0;
  const miles = Math.max(parseFloat(payload.total_miles || 1), 1.0);
  const deadhead = Math.max(parseFloat(payload.deadhead_miles || 0), 0.0);
  const pay = parseFloat(payload.flat_rate_pay || 0);
  const rpm = Number((pay / miles).toFixed(2));
  const true_rpm = Number((pay / (miles + deadhead)).toFixed(2));

  let score = 'Reject';
  let priority_tier = 3;
  if (isBox && underWeight) {
    if (true_rpm >= 2.50) {
      score = 'Greenlight';
      priority_tier = 1;
    } else if (true_rpm >= 2.00) {
      score = 'Caution';
      priority_tier = 2;
    }
  }
  return {
    ...payload,
    rpm,
    true_rpm,
    score,
    priority_tier,
    is_valid_box_truck: isBox,
    under_weight_limit: underWeight
  };
}

export default function FEExpressDispatcher({ BACKEND_URL }) {
  const baseUrl = BACKEND_URL || 'http://127.0.0.1:8080';
  const [loads, setLoads] = useState(INITIAL_FALLBACK_LOADS);
  const [status, setStatus] = useState({
    status: 'ONLINE',
    total_loads: INITIAL_FALLBACK_LOADS.length,
    greenlight_loads: INITIAL_FALLBACK_LOADS.filter(l => l.score === 'Greenlight').length
  });
  const [loading, setLoading] = useState(false);
  const [filterScore, setFilterScore] = useState('ALL');

  // Ad-hoc Quick Calculator
  const [calcOrigin, setCalcOrigin] = useState('Grand Rapids, MI');
  const [calcDest, setCalcDest] = useState('Chicago, IL');
  const [calcEquip, setCalcEquip] = useState("26' Box Truck w/ Liftgate");
  const [calcMiles, setCalcMiles] = useState(180);
  const [calcDeadhead, setCalcDeadhead] = useState(15);
  const [calcPay, setCalcPay] = useState(550);
  const [calcWeight, setCalcWeight] = useState(6500);
  const [calcBroker, setCalcBroker] = useState('Echo Global Logistics');
  const [evalResult, setEvalResult] = useState(null);

  const fetchLoads = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${baseUrl}/api/v1/fe-express/loads?limit=50`);
      if (res.ok) {
        const data = await res.json();
        if (data.loads && data.loads.length > 0) {
          setLoads(data.loads);
        }
      }
      const stRes = await fetch(`${baseUrl}/api/v1/fe-express/status`);
      if (stRes.ok) {
        const stData = await stRes.json();
        setStatus(stData);
      }
    } catch {
      // Fallback to local state when viewing on static Firebase or before backend reload
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLoads();
    const interval = setInterval(fetchLoads, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleCalculate = async (e) => {
    e.preventDefault();
    const payload = {
      load_id: `FE-${Math.floor(100 + Math.random() * 900)}`,
      origin_city_state: calcOrigin,
      dest_city_state: calcDest,
      equipment_type: calcEquip,
      weight_lbs: parseFloat(calcWeight),
      total_miles: parseFloat(calcMiles),
      deadhead_miles: parseFloat(calcDeadhead),
      flat_rate_pay: parseFloat(calcPay),
      broker_name: calcBroker
    };
    try {
      const res = await fetch(`${baseUrl}/api/v1/fe-express/loads/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setEvalResult(data.evaluated);
        setLoads(prev => [data.evaluated, ...prev]);
        return;
      }
    } catch {
      // Local evaluation fallback
    }
    const localEval = evaluateLocally(payload);
    setEvalResult(localEval);
    if (localEval.is_valid_box_truck && localEval.under_weight_limit) {
      setLoads(prev => [localEval, ...prev]);
    }
  };

  const filteredLoads = loads.filter(l => {
    if (filterScore === 'ALL') return true;
    return l.score === filterScore;
  });

  return (
    <div style={{ padding: '24px', backgroundColor: '#0B0F19', color: '#F8FAFC', minHeight: '100%', overflowY: 'auto', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #1E293B', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 800, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '10px' }}>
            🚚 FE EXPRESS | Box Truck Automation Hub
          </h1>
          <p style={{ margin: '4px 0 0', color: '#94A3B8', fontSize: '13px' }}>
            Real-Time RPM Scoring, Deadhead Analysis, and Automated Expediter Lead Filtering (24&apos;/26&apos; Box &amp; Straight Trucks ≤ 10,000 lbs)
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={fetchLoads}
            style={{ padding: '8px 16px', backgroundColor: '#1E293B', color: '#38BDF8', border: '1px solid #38BDF8', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
          >
            🔄 Refresh Board
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Active Hub Status</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#10B981', marginTop: '4px' }}>🟢 OPERATIONAL</div>
        </div>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Greenlight Loads</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#38BDF8', marginTop: '4px' }}>
            {loads.filter(l => l.score === 'Greenlight').length}
          </div>
        </div>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Total Qualified Loads</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#F3F4F6', marginTop: '4px' }}>
            {loads.length}
          </div>
        </div>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Greenlight Threshold</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#F59E0B', marginTop: '4px' }}>≥ $2.50 / True Mi</div>
        </div>
      </div>

      {/* Quick Load Calculator & Feed Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '24px' }}>
        {/* Left: Quick Evaluator */}
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', borderRadius: '8px', padding: '18px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#38BDF8', margin: '0 0 16px' }}>⚡ Instant Lane Evaluator</h2>
          <form onSubmit={handleCalculate} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Origin</label>
              <input type="text" value={calcOrigin} onChange={e => setCalcOrigin(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Destination</label>
              <input type="text" value={calcDest} onChange={e => setCalcDest(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Loaded Miles</label>
                <input type="number" value={calcMiles} onChange={e => setCalcMiles(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Deadhead Miles</label>
                <input type="number" value={calcDeadhead} onChange={e => setCalcDeadhead(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Flat Rate Pay ($)</label>
                <input type="number" value={calcPay} onChange={e => setCalcPay(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Weight (lbs)</label>
                <input type="number" value={calcWeight} onChange={e => setCalcWeight(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Equipment String</label>
              <input type="text" value={calcEquip} onChange={e => setCalcEquip(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Broker Name</label>
              <input type="text" value={calcBroker} onChange={e => setCalcBroker(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
            </div>
            <button type="submit" style={{ marginTop: '8px', padding: '10px', backgroundColor: '#2563EB', color: '#FFF', border: 'none', borderRadius: '4px', fontWeight: 700, cursor: 'pointer' }}>
              ⚡ Evaluate &amp; Add to Board
            </button>
          </form>

          {evalResult && (
            <div style={{ marginTop: '16px', padding: '12px', backgroundColor: evalResult.score === 'Greenlight' ? '#064E3B' : evalResult.score === 'Caution' ? '#78350F' : '#7F1D1D', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.2)' }}>
              <div style={{ fontSize: '16px', fontWeight: 800 }}>Decision: {evalResult.score.toUpperCase()}</div>
              <div style={{ fontSize: '13px', marginTop: '4px' }}>True RPM (w/ Deadhead): <strong>${evalResult.true_rpm} / mi</strong></div>
              <div style={{ fontSize: '13px' }}>Loaded RPM: ${evalResult.rpm} / mi</div>
              <div style={{ fontSize: '12px', color: '#E2E8F0', marginTop: '4px' }}>
                Box Truck Match: {evalResult.is_valid_box_truck ? '✅ Yes' : '❌ No'} | Under 10k lbs: {evalResult.under_weight_limit ? '✅ Yes' : '❌ No'}
              </div>
            </div>
          )}
        </div>

        {/* Right: Filtered Live Board Stream */}
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', borderRadius: '8px', padding: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#F3F4F6', margin: 0 }}>📋 Filtered Box Truck Loads</h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              {['ALL', 'Greenlight', 'Caution', 'Reject'].map(t => (
                <button
                  key={t}
                  onClick={() => setFilterScore(t)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '12px',
                    borderRadius: '4px',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: 600,
                    backgroundColor: filterScore === t ? '#38BDF8' : '#1F2937',
                    color: filterScore === t ? '#000' : '#94A3B8'
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#1F2937', textAlign: 'left', color: '#9CA3AF' }}>
                  <th style={{ padding: '8px' }}>Tier</th>
                  <th style={{ padding: '8px' }}>Load ID</th>
                  <th style={{ padding: '8px' }}>Lane (Origin ➡️ Dest)</th>
                  <th style={{ padding: '8px' }}>Pay</th>
                  <th style={{ padding: '8px' }}>Loaded RPM</th>
                  <th style={{ padding: '8px' }}>True RPM</th>
                  <th style={{ padding: '8px' }}>Equipment / Wt</th>
                  <th style={{ padding: '8px' }}>Broker</th>
                </tr>
              </thead>
              <tbody>
                {filteredLoads.length === 0 ? (
                  <tr>
                    <td colSpan="8" style={{ textAlign: 'center', padding: '24px', color: '#6B7280' }}>
                      {loading ? 'Refreshing loads...' : 'No loads matching current filter.'}
                    </td>
                  </tr>
                ) : (
                  filteredLoads.map(load => (
                    <tr key={load.load_id} style={{ borderBottom: '1px solid #1F2937' }}>
                      <td style={{ padding: '8px' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 700,
                          backgroundColor: load.score === 'Greenlight' ? '#065F46' : load.score === 'Caution' ? '#92400E' : '#991B1B',
                          color: '#FFF'
                        }}>
                          {load.score}
                        </span>
                      </td>
                      <td style={{ padding: '8px', fontWeight: 600 }}>{load.load_id}</td>
                      <td style={{ padding: '8px' }}>{load.origin_city_state} ➡️ {load.dest_city_state} ({load.total_miles} mi)</td>
                      <td style={{ padding: '8px', color: '#10B981', fontWeight: 700 }}>${load.flat_rate_pay}</td>
                      <td style={{ padding: '8px' }}>${load.rpm}/mi</td>
                      <td style={{ padding: '8px', fontWeight: 700, color: '#38BDF8' }}>${load.true_rpm}/mi</td>
                      <td style={{ padding: '8px', color: '#9CA3AF' }}>{load.equipment_type} ({load.weight_lbs} lbs)</td>
                      <td style={{ padding: '8px' }}>{load.broker_name}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
