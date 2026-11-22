"""Pinned AWS CLI read-only readiness; supports existing AWS login credentials."""
from datetime import date, datetime
from decimal import Decimal
import json
import math
import os
import subprocess
from types import SimpleNamespace

PROFILE = "stehouwer-productions"
REGION = "us-east-2"
AWS_CLI = r"C:\Users\Administrator\AppData\Local\Programs\Amazon\AWSCLIV2\aws.exe"
_clients = {}


class MissingIdentity(Exception):
    pass


class ReadUnavailable(Exception):
    pass


def cli_read(service, operation, domain=None):
    allowed = {("sesv2", "get-account"), ("sesv2", "get-email-identity"), ("freetier", "get-account-plan-state")}
    if (service, operation) not in allowed:
        raise ValueError("Unsupported readiness operation")
    command = [AWS_CLI, service, operation]
    if operation == "get-email-identity":
        if domain not in ("stehouwerproductions.com", "stehouwer-publishing.com"):
            raise ValueError("Unsupported owned identity")
        command.extend(["--email-identity", domain])
    elif domain is not None:
        raise ValueError("Unexpected identity argument")
    command.extend(["--profile", PROFILE, "--region", REGION, "--output", "json", "--no-cli-pager",
                    "--cli-connect-timeout", "2", "--cli-read-timeout", "4"])
    environment = {**os.environ, "AWS_PAGER": "", "AWS_CLI_AUTO_PROMPT": "off", "AWS_MAX_ATTEMPTS": "2", "AWS_RETRY_MODE": "standard"}
    try:
        result = subprocess.run(command, shell=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=18, env=environment, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReadUnavailable("AWS readiness transport unavailable") from error
    if result.returncode:
        if operation == "get-email-identity" and "(NotFoundException)" in result.stderr:
            raise MissingIdentity()
        # Provider stdout/stderr can contain account information; never expose it.
        raise ReadUnavailable("AWS readiness read did not succeed")
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError("Invalid readiness result")
    except (ValueError, TypeError) as error:
        raise ReadUnavailable("AWS readiness response invalid") from error
    return value


class ReadClient:
    exceptions = SimpleNamespace(NotFoundException=MissingIdentity)

    def __init__(self, service):
        self.service = service

    def get_account(self):
        if self.service != "sesv2":
            raise ValueError("Unsupported account service")
        return cli_read(self.service, "get-account")

    def get_email_identity(self, *, EmailIdentity):
        if self.service != "sesv2":
            raise ValueError("Unsupported identity service")
        return cli_read(self.service, "get-email-identity", EmailIdentity)

    def get_account_plan_state(self):
        if self.service != "freetier":
            raise ValueError("Unsupported plan service")
        return cli_read(self.service, "get-account-plan-state")


def client(service):
    if service not in ("sesv2", "freetier"):
        raise ValueError("Unsupported readiness service")
    if service not in _clients:
        _clients[service] = ReadClient(service)
    return _clients[service]


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    result = float(value)
    return result if math.isfinite(result) and result >= 0 else None


def read_ses_status(domain):
    ses = client("sesv2")
    account = ses.get_account()
    try:
        identity = ses.get_email_identity(EmailIdentity=domain)
    except ses.exceptions.NotFoundException:
        identity = {}
    dkim = identity.get("DkimAttributes", {})
    verified = identity.get("VerifiedForSendingStatus") is True
    dkim_status = str(dkim.get("Status", "NOT_ESTABLISHED"))[:40]
    quota = account.get("SendQuota", {})
    result = {
        "domain_identity_verified": verified,
        "domain_verification_status": str(identity.get("VerificationStatus", "NOT_ESTABLISHED"))[:40],
        "dkim_status": dkim_status,
        "verified": verified and dkim_status == "SUCCESS",
        "sandbox": not account["ProductionAccessEnabled"] if isinstance(account.get("ProductionAccessEnabled"), bool) else None,
        "sending_enabled": account.get("SendingEnabled") if isinstance(account.get("SendingEnabled"), bool) else None,
        "quota": {"max_24_hour_send": number(quota.get("Max24HourSend")),
                  "max_send_rate": number(quota.get("MaxSendRate")),
                  "sent_last_24_hours": number(quota.get("SentLast24Hours"))},
        "current_plan": str(account.get("PricingAttributes", {}).get("CurrentPlan", "unknown"))[:40],
        "account_plan": {"type": "unknown", "status": "unknown", "remaining_credits": None, "unit": "", "expires_at": ""},
    }
    # Account-plan visibility is optional; an IAM denial must not invent free-credit status.
    try:
        plan = client("freetier").get_account_plan_state()
        expiration = plan.get("accountPlanExpirationDate", "")
        if isinstance(expiration, (datetime, date)):
            expiration = expiration.isoformat()
        credits = plan.get("accountPlanRemainingCredits", {})
        result["account_plan"] = {"type": str(plan.get("accountPlanType", "unknown"))[:20],
                                  "status": str(plan.get("accountPlanStatus", "unknown"))[:20],
                                  "remaining_credits": number(credits.get("amount")),
                                  "unit": str(credits.get("unit", ""))[:12], "expires_at": str(expiration)[:80]}
    except Exception:
        result["account_plan"]["visibility"] = "unavailable"
    return result
