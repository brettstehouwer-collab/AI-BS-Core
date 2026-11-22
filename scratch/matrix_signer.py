import os
import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from io import BytesIO


class DigitalSigner:
    def __init__(self, cert_dir="contracts_vault/certs"):
        self.cert_dir = cert_dir
        self.key_path = os.path.join(cert_dir, "stehouwer_private_key.pem")
        self.cert_path = os.path.join(cert_dir, "stehouwer_cert.pem")
        os.makedirs(cert_dir, exist_ok=True)
        self._ensure_keys_exist()

    def _ensure_keys_exist(self):
        if os.path.exists(self.key_path) and os.path.exists(self.cert_path):
            return

        print("Generating new self-signed Digital Signature Certificate for Stehouwer Publishing...")
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Los Angeles"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Stehouwer Publishing"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"Brett Stehouwer"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650)
        ).sign(private_key, hashes.SHA256())

        with open(self.key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        with open(self.cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

    def sign_pdf(
            self,
            input_pdf_bytes: bytes,
            output_path: str,
            reason: str = "Cryptographically signed by AI-BS Matrix",
            location: str = "Los Angeles, CA"):
        signer = signers.SimpleSigner.load(
            self.key_path, self.cert_path,
            key_passphrase=None
        )

        with open(output_path, 'wb') as out_file:
            pdf_writer = IncrementalPdfFileWriter(BytesIO(input_pdf_bytes))
            signers.sign_pdf(
                pdf_writer,
                signers.PdfSignatureMetadata(
                    field_name='Signature1',
                    reason=reason,
                    location=location),
                signer=signer,
                in_place=False,
                output=out_file)
        return output_path
