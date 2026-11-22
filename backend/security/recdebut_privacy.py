"""Personal-contact exclusions and exact phone identity for inbound forwarding."""
import csv
import os
import re
from pathlib import Path


class PrivacyCheckUnavailable(RuntimeError):
    pass


def normalize_phone(value):
    value = str(value or '').strip()
    if not value or re.search(r'[^\d+\s().-]', value):
        return ''
    digits = re.sub(r'\D', '', value)
    if len(digits) == 10 and not value.startswith('+'):
        return digits
    if len(digits) == 11 and digits.startswith('1'):
        return digits[1:]
    if value.startswith('+') and 11 <= len(digits) <= 15 and not digits.startswith(('0', '1')):
        return '+' + digits
    return ''


def load_personal_contacts():
    default = Path(__file__).resolve().parents[2] / 'saved_data' / 'MyPhoneContacts.csv'
    path = Path(os.environ.get('RECDEBUT_PERSONAL_CONTACTS_PATH') or default)
    phones, emails = set(), set()
    try:
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            phone_columns = [h for h in headers if any(x in h.casefold() for x in ('phone', 'mobile', 'telephone'))]
            email_columns = [h for h in headers if 'email' in re.sub(r'[-\s]', '', h.casefold())]
            if not phone_columns and not email_columns:
                raise ValueError('No contact columns')
            for row in reader:
                for column in phone_columns:
                    for value in re.split(r':::|[;\n]', row.get(column) or ''):
                        phone = normalize_phone(value)
                        if phone:
                            phones.add(phone)
                for column in email_columns:
                    for value in re.split(r':::|[;\n]', row.get(column) or ''):
                        email = value.strip().casefold()
                        if '@' in email:
                            emails.add(email)
        if not phones and not emails:
            raise ValueError('No usable contacts')
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        raise PrivacyCheckUnavailable('Personal contact exclusions unavailable; forwarding is blocked.') from exc
    return phones, emails
