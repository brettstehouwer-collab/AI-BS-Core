import os
from typing import Dict, Any

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Dial
import logging

logger = logging.getLogger(__name__)


class TelecomEngine:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER")

        self.is_active = bool(self.account_sid and self.auth_token and self.from_phone)
        if self.is_active:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            logger.warning(
                "Twilio keys missing in .env. TelecomEngine is running in fallback mock mode."
            )

    def trigger_call_whisper(
        self, agent_phone: str, lead_name: str, lead_phone: str, property_interest: str
    ) -> Dict[str, Any]:
        """
        Initiates a call to the agent (Joe). When he picks up, he hears the whisper message
        and is prompted to press 1 to connect to the lead.
        """

        # Build the TwiML response
        response = VoiceResponse()
        gather = Gather(
            numDigits=1,
            action=f"/api/v1/telecom/bridge-call?lead_phone={lead_phone}",
            method="POST",
        )
        gather.say(
            f"You have a new high intent lead from your website. Name: {lead_name}. Interest: {property_interest}. Press 1 to connect to the lead right now.",
            voice="Polly.Joanna-Neural",
        )
        response.append(gather)
        response.say("We didn't receive any input. Goodbye!")

        twiml_string = str(response)

        if not self.is_active:
            print("==================================================")
            print(f"[MOCK TWILIO] Initiating call to Agent at: {agent_phone}")
            print(f"[MOCK TWILIO] From Twilio Number: {self.from_phone}")
            print("[MOCK TWILIO] Call connected! Playing TwiML:")
            print(twiml_string)
            print("==================================================")
            return {
                "status": "success",
                "message": f"Mock call initiated to {agent_phone}",
                "lead": lead_name,
                "property": property_interest,
            }

        try:
            call = self.client.calls.create(
                twiml=twiml_string, to=agent_phone, from_=self.from_phone
            )
            return {
                "status": "success",
                "message": f"Live call initiated to {agent_phone}. Call SID: {call.sid}",
                "lead": lead_name,
                "property": property_interest,
            }
        except Exception as e:
            logger.error(f"Failed to trigger Twilio call: {e}")
            return {"status": "error", "message": str(e)}

    def bridge_call_twiml(self, lead_phone: str) -> str:
        """
        Generates the TwiML to bridge the call to the lead after Joe presses 1.
        """
        response = VoiceResponse()
        response.say("Connecting you now.", voice="Polly.Joanna-Neural")
        response.dial(lead_phone)
        return str(response)


# Singleton instance
telecom = TelecomEngine()
