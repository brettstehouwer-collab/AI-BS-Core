"""
Stehouwer Publishing, LLC — Sovereign NDA & Anti-Tamper Document Engine Router
Handles generating cryptographically signed, watermarked, anti-tamper Master NDA PDFs,
calculating SHA-256 HMAC integrity checksums, and validating file tamper status.
"""

import os
import io
import time
import base64
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from security.host_control_access import AdminHostControlRoute

router = APIRouter(prefix="/api/v1/nda", tags=["Sovereign NDA & Anti-Tamper Suite"], route_class=AdminHostControlRoute)

# Storage directory
SIGNED_NDAS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Documents", "signed_ndas"))


# Cryptographic Master Secret for Anti-Tamper Checksum Verification
HMAC_SECRET = None  # Signing remains held; no fallback signing credentials.


class NdaSignRequest(BaseModel):
    collaborator_name: str
    collaborator_title: Optional[str] = "Collaborator / Technical Advisor"
    collaborator_company: Optional[str] = "Independent"
    collaborator_email: str
    collaborator_phone: Optional[str] = ""
    collaborator_address: Optional[str] = ""
    effective_date: Optional[str] = None
    signature_data_url: str  # Base64 image data URL
    signature_type: Optional[str] = "draw"
    ip_address: Optional[str] = "127.0.0.1"
    verified_sections: Optional[List[str]] = []


def generate_signed_nda_pdf_bytes(data: NdaSignRequest, doc_hash_str: str, timestamp_str: str) -> bytes:
    """Held pending verified signer, consent, and durable whole-file receipt contracts."""
    raise HTTPException(status_code=503, detail="Signing and document mutation are unavailable pending verified signer, consent, and durable whole-file receipt contracts.")


def embed_anti_tamper_seal(raw_pdf_bytes: bytes, signer_name: str, signer_email: str) -> tuple[bytes, str]:
    """Held pending verified signer, consent, and durable whole-file receipt contracts."""
    raise HTTPException(status_code=503, detail="Signing and document mutation are unavailable pending verified signer, consent, and durable whole-file receipt contracts.")


@router.get("/schema")
async def get_nda_schema():
    """Returns the full agreement sections and clause hierarchy for the interactive checkbox review."""
    schema = {
        "title": "Master Services, Confidentiality, Intellectual Property, and Security Agreement",
        "company": {
            "name": "Stehouwer Publishing, LLC",
            "address": "1481 Rosewood St., Jenison, Michigan 49428",
            "representatives": [
                {"name": "Julie A. Stehouwer", "role": "CEO / Authorized Representative"},
                {"name": "Brett Adam Stehouwer", "role": "VP / CTO / Technical Architecture Lead"}
            ]
        },
        "sections": [
            {
                "id": "recitals",
                "title": "Preamble & Recitals",
                "summary": "Establishes identity of the parties, engagement scope, and corporate governance.",
                "clauses": [
                    {"id": "recitals_parties", "code": "Recitals", "title": "Corporate Identification", "text": "Confirms Stehouwer Publishing, LLC and Collaborator roles in publishing, AI systems development, and digital media architecture."},
                    {"id": "recitals_intent", "code": "Intent", "title": "Protection of Proprietary Systems", "text": "Express intent to protect trade secrets, proprietary workflows, and assign IP exclusively to Company."}
                ]
            },
            {
                "id": "sec_1",
                "title": "Section I: Master Services Agreement (MSA)",
                "summary": "Core scope of services, Statement of Work (SOW) requirement, and termination terms.",
                "clauses": [
                    {"id": "c_1_1", "code": "1.1", "title": "Purpose & Scope", "text": "Governs publishing, software systems, AI training pipelines, automation workflows, and technical system evaluation."},
                    {"id": "c_1_2", "code": "1.2", "title": "Precedence", "text": "Applies to all Company-related collaboration unless superseded by signed written agreement."},
                    {"id": "c_2_1", "code": "2.1", "title": "Corporate Authority", "text": "Stehouwer Publishing, LLC retains absolute, exclusive authority over all business operations and IP."},
                    {"id": "c_2_2", "code": "2.2", "title": "Key Representatives", "text": "Julie A. Stehouwer (CEO) and Brett Adam Stehouwer (VP/CTO) manage corporate and technical operations."},
                    {"id": "c_3_1", "code": "3.1", "title": "Written SOW Requirement", "text": "All paid services must be defined in writing via executed Statement of Work (SOW) prior to performance."},
                    {"id": "c_3_2", "code": "3.2", "title": "Consulting Fee Rule", "text": "Compensation must be finalized in writing; unauthorized work creates no payment obligation."},
                    {"id": "c_4_2", "code": "4.2", "title": "Termination for Cause/Convenience", "text": "30 days notice for convenience; immediate termination for security breach or data exfiltration."},
                    {"id": "c_4_4", "code": "4.4", "title": "Perpetual Survival", "text": "Confidentiality, IP assignment, non-circumvention, and dispute governance survive termination in perpetuity."}
                ]
            },
            {
                "id": "sec_2",
                "title": "Section II: Confidentiality & Non-Disclosure",
                "summary": "Broad definition of confidential assets, non-replication, and perpetual trade secret protection.",
                "clauses": [
                    {"id": "c_5_1", "code": "5.1-5.4", "title": "Definition of Confidential Information", "text": "Protects Creative Assets, Business Information, Technical Information (source code, schemas, prompts, algorithms), and Proprietary Systems."},
                    {"id": "c_6_1", "code": "6.1-6.2", "title": "Duty & Standard of Care", "text": "Strict confidence, reasonable care, and mandatory active encryption at rest and in transit."},
                    {"id": "c_6_3", "code": "6.3-6.4", "title": "Permitted Use & Non-Replication", "text": "Used solely for authorized Company services; strictly prohibits copying, reverse-engineering, or decompiling."},
                    {"id": "c_6_5", "code": "6.5", "title": "Perpetual Duration for Trade Secrets", "text": "Trade secrets and Proprietary Technology survive indefinitely in perpetuity; business info survives 5 years."},
                    {"id": "c_6_6", "code": "6.6", "title": "24-Hour Breach Reporting", "text": "Immediate written notice to Brett Adam Stehouwer and Julie A. Stehouwer within 24 hours of any leak."},
                    {"id": "c_7_2", "code": "7.2", "title": "DTSA Whistleblower Notice", "text": "Defend Trade Secrets Act immunity notice under 18 U.S.C. § 1833(b)."}
                ]
            },
            {
                "id": "sec_3",
                "title": "Section III: Intellectual Property Assignment",
                "summary": "Universal assignment of all work product, work-made-for-hire, and company ownership of modifications.",
                "clauses": [
                    {"id": "c_8_0", "code": "8.0", "title": "Ownership of Work Product", "text": "All deliverables, code, algorithms, and documentation developed for Company belong exclusively to Company."},
                    {"id": "c_9_1", "code": "9.1-9.2", "title": "Work Made for Hire & Universal Assignment", "text": "Under 17 U.S.C. § 101, eligible work is work for hire; all other IP globally and irrevocably assigned to Company."},
                    {"id": "c_9_3", "code": "9.3", "title": "Transfer Restrictions", "text": "No right to transfer, license, or sublicense Company IP without written consent of Julie or Brett Stehouwer."},
                    {"id": "c_10_0", "code": "10.0", "title": "Proprietary Technology Ownership", "text": "AI-BS, prompt systems, reasoning frameworks, and datasets represent exclusive Trade Secrets of Company."}
                ]
            },
            {
                "id": "sec_4",
                "title": "Section IV: Security, Access, and Data Compliance",
                "summary": "CTO authorization requirements, technical sandbox boundaries, and regulatory compliance.",
                "clauses": [
                    {"id": "c_12_0", "code": "12.0", "title": "System Access & CTO Authorization", "text": "System access is revocable at will and strictly conditioned on instructions authorized by CTO Brett Adam Stehouwer."},
                    {"id": "c_13_0", "code": "13.0", "title": "Technical Security Controls", "text": "Prohibits bypassing authentications, extracting database contents, or deploying unauthorized sniffers."},
                    {"id": "c_14_1", "code": "14.1-14.2", "title": "Sandbox Integrity & Export Controls", "text": "Respect sandbox memory boundaries; strict compliance with US EAR and OFAC export controls."},
                    {"id": "c_15_1", "code": "15.1-15.2", "title": "Data Privacy & Indemnity", "text": "GDPR, HIPAA, and CCPA compliance; Collaborator assumes sole financial responsibility for regulatory fines caused by breach."}
                ]
            },
            {
                "id": "sec_5",
                "title": "Section V: Brand & Business Protection",
                "summary": "5-year non-circumvention, 3-year non-solicitation, and public communication restrictions.",
                "clauses": [
                    {"id": "c_16_0", "code": "16.0", "title": "5-Year Non-Circumvention", "text": "Collaborator shall not exploit confidential opportunities or build competing business models using Company confidential info."},
                    {"id": "c_17_0", "code": "17.0", "title": "3-Year Non-Solicitation", "text": "Prohibits soliciting or contracting Company employees, contractors, or active clients."},
                    {"id": "c_18_0", "code": "18.0", "title": "Brand & Affiliation Restrictions", "text": "No unauthorized public representation, logo usage, or sharing internal communications on public forums."}
                ]
            },
            {
                "id": "sec_6",
                "title": "Section VI: Legal Governance, Disputes, & Indemnification",
                "summary": "Kent County Michigan venue, AAA commercial arbitration, and immediate injunctive relief.",
                "clauses": [
                    {"id": "c_19_1", "code": "19.1-19.2", "title": "Mediation & Binding Arbitration", "text": "Good-faith consultation, non-binding mediation, then binding AAA arbitration in Kent County, Michigan."},
                    {"id": "c_19_3", "code": "19.3", "title": "Immediate Injunctive Relief", "text": "Company retains absolute right to seek immediate injunctive relief in court to protect IP and security."},
                    {"id": "c_20_0", "code": "20.0-21.0", "title": "Remedies & Indemnification", "text": "Equitable remedies for irreparable harm; Collaborator indemnifies Company against breach damages and legal fees."}
                ]
            },
            {
                "id": "sec_7",
                "title": "Section VII & Exhibit A: Technical Scope & Execution",
                "summary": "Governing law, CISG exclusion, explicit AI-BS trade secret scope, and execution signatures.",
                "clauses": [
                    {"id": "c_23_27", "code": "23-27", "title": "Michigan Law & Counterparts", "text": "Governed by Michigan law; digital and electronic signatures deemed legally binding originals."},
                    {"id": "c_exhibit_a", "code": "Exhibit A", "title": "AI-BS & Hallucination Mitigation Scope", "text": "Explicitly locks down AI-BS, reasoning graphs, autograd engines, prompt architectures, and hallucination mitigation pipelines."}
                ]
            }
        ]
    }
    all_clauses = [c["id"] for sec in schema["sections"] for c in sec.get("clauses", [])]
    schema["all_clause_ids"] = all_clauses
    schema["total_clauses"] = len(all_clauses)
    return schema


@router.post("/generate-signed")
async def generate_signed_nda(req: NdaSignRequest):
    """Held pending verified signer, consent, and durable whole-file receipt contracts."""
    raise HTTPException(status_code=503, detail="Signing and document mutation are unavailable pending verified signer, consent, and durable whole-file receipt contracts.")


@router.post("/verify-integrity")
async def verify_pdf_integrity(file: UploadFile = File(...)):
    """Observe bounded bytes only; a digest does not establish authenticity."""
    digest = hashlib.sha256()
    size = 0
    limit = 8 * 1024 * 1024
    try:
        while True:
            chunk = await file.read(min(65536, limit - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                return JSONResponse({"valid": None, "tamper_detected": None,
                    "authenticity": "unverified", "status": "observation_limit_exceeded"}, status_code=413)
            digest.update(chunk)
    except Exception:
        return JSONResponse({"valid": None, "tamper_detected": None,
            "authenticity": "unverified", "status": "observation_unavailable"}, status_code=503)
    return JSONResponse({"valid": None, "tamper_detected": None,
        "authenticity": "unverified", "status": "digest_observed",
        "current_sha256": digest.hexdigest(), "bytes_observed": size,
        "message": "SHA-256 observation only; no trusted whole-file receipt or signer verification is available."})


@router.post("/simulate-tamper")
async def simulate_tamper_attack(file: UploadFile = File(...)):
    """Held pending verified signer, consent, and durable whole-file receipt contracts."""
    raise HTTPException(status_code=503, detail="Signing and document mutation are unavailable pending verified signer, consent, and durable whole-file receipt contracts.")
