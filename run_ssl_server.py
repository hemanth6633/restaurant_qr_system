import os
import ssl
from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.management import call_command
from django.conf import settings

# Generate self-signed certificate
def generate_ssl_cert():
    from OpenSSL import crypto
    
    # Generate key
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    
    # Generate certificate
    cert = crypto.X509()
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for one year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')
    
    # Save certificate and private key
    with open("localhost.crt", "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open("localhost.key", "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

if __name__ == '__main__':
    # Generate certificate if it doesn't exist
    if not (os.path.exists("localhost.crt") and os.path.exists("localhost.key")):
        generate_ssl_cert()
    
    # Run Django development server with SSL
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')
    call_command(
        'runserver',
        '0.0.0.0:8000',
        '--cert', 'localhost.crt',
        '--key', 'localhost.key'
    )
