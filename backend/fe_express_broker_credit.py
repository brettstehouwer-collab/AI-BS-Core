import sqlite3
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("FE_Express_BrokerSentinel")
DB_PATH = Path(r"C:\AI-BS\saved_data\fe_express.db")

# Known Broker Credit & Factoring Database Baseline
BROKER_CREDIT_PROFILES = {
    "sureway": {
        "score": 96,
        "rating": "A+",
        "days_to_pay": 22,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Fast direct deposit / RTS & Triumph factoring tier 1 approved."
    },
    "anderson trucking": {
        "score": 96,
        "rating": "A+",
        "days_to_pay": 22,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Large national carrier brokerage. Excellent credit rating."
    },
    "echo global logistics": {
        "score": 98,
        "rating": "A+",
        "days_to_pay": 20,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Top 10 US 3PL. Quick pay available, all major factoring houses approve."
    },
    "c.h. robinson": {
        "score": 99,
        "rating": "A+",
        "days_to_pay": 19,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Highest volume US broker. Universal factor approval."
    },
    "tql": {
        "score": 92,
        "rating": "A",
        "days_to_pay": 28,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Strict check-in rules. Approved with standard factor terms."
    },
    "ampersand transport": {
        "score": 85,
        "rating": "B+",
        "days_to_pay": 34,
        "factoring_status": "CONDITIONAL",
        "factoring_eligible": True,
        "notes": "Regional broker. Verified MC, check factoring limits before booking."
    },
    "dsf toad": {
        "score": 88,
        "rating": "B+",
        "days_to_pay": 31,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Regional direct dispatch. Standard factor acceptance."
    },
    "allen lund": {
        "score": 95,
        "rating": "A+",
        "days_to_pay": 21,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Produce & dry van specialist. Outstanding payment record."
    },
    "atlantic logistics": {
        "score": 91,
        "rating": "A",
        "days_to_pay": 25,
        "factoring_status": "APPROVED",
        "factoring_eligible": True,
        "notes": "Solid mid-tier 3PL. Standard RTS and OTR approval."
    }
}


class BrokerCreditSentinel:
    @staticmethod
    def get_broker_credit(broker_name: str) -> Dict[str, Any]:
        """
        Inspects broker name against factoring eligibility rules and credit scores.
        """
        name_lower = (broker_name or "").lower().strip()
        
        for key, profile in BROKER_CREDIT_PROFILES.items():
            if key in name_lower:
                return {
                    "matched": True,
                    "broker_name": broker_name,
                    **profile
                }

        # Default standard conservative profile for unlisted brokers
        return {
            "matched": False,
            "broker_name": broker_name or "Unknown Broker",
            "score": 82,
            "rating": "B",
            "days_to_pay": 35,
            "factoring_status": "VERIFY_FACTOR",
            "factoring_eligible": True,
            "notes": "Unindexed broker. Verify active authority on FMCSA SAFER & run credit check before booking."
        }
