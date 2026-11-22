"""Phone plus PIN website sessions; no Firebase or administrator impersonation."""
import re
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from security.fe_express_access import PinSessions, CONFIG


def normalize_phone(value):
    if not isinstance(value, str) or len(value) > 32 or not re.fullmatch(r'\+?[0-9() .-]+', value):
        return None
    digits = re.sub(r'[^0-9]', '', value)
    if len(digits) == 10:
        digits = '1' + digits
    return '+' + digits if len(digits) == 11 and digits.startswith('1') else None


class WebsiteSessions(PinSessions):
    token_prefix = 'wp1.'
    scope = 'website_pages'

    def login(self, phone, pin):
        normalized = normalize_phone(phone)
        valid = bool(normalized and isinstance(pin, str) and re.fullmatch(r'[0-9]{4}', pin))
        credential = normalized + '\0' + pin if valid else ''
        return self._login(credential, valid)


sessions = WebsiteSessions(CONFIG.with_name('website_phone_pin.json'))
router = APIRouter(prefix='/api/website-access', tags=['Website access'])


class PhonePinLogin(BaseModel):
    phone: str = Field(max_length=32)
    pin: str = Field(max_length=16)


@router.post('/login')
def login(payload: PhonePinLogin, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return sessions.login(payload.phone, payload.pin)


@router.get('/session')
def session(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    if not sessions.valid(request.headers.get('authorization', '')):
        raise HTTPException(401, 'Sign in with your phone number and PIN.')
    return {'scope': 'website_pages'}


@router.post('/logout')
def logout(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    sessions.revoke(request.headers.get('authorization', ''))
    return {'locked': True}
