#!/usr/bin/env python3
import http.server
import socketserver
import ssl
import os
import sys

PORT = 8000
HTTPS_PORT = 8443

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Service-Worker-Allowed', '/')
        super().end_headers()

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

def create_self_signed_cert():
    """Create a self-signed certificate for HTTPS testing"""
    from datetime import datetime, timedelta
    import tempfile
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("\nNote: For HTTPS support, install cryptography: pip install cryptography")
        return None, None
    
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BitChat PWA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())
    
    cert_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pem')
    cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
    cert_file.close()
    
    key_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.key')
    key_file.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))
    key_file.close()
    
    return cert_file.name, key_file.name

def serve_https():
    """Serve with HTTPS (required for Web Bluetooth API)"""
    cert_file, key_file = create_self_signed_cert()
    
    if not cert_file:
        print("\nCannot create HTTPS server without cryptography module.")
        print("Falling back to HTTP (Web Bluetooth will not work).")
        serve_http()
        return
    
    handler = MyHTTPRequestHandler
    httpd = socketserver.TCPServer(("", HTTPS_PORT), handler)
    
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_file, key_file)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"\n🚀 BitChat PWA Server (HTTPS)")
    print(f"   https://localhost:{HTTPS_PORT}")
    print(f"   https://127.0.0.1:{HTTPS_PORT}")
    print(f"\n⚠️  Browser will show security warning - click 'Advanced' and 'Proceed'")
    print(f"   This is normal for self-signed certificates.")
    print(f"\n📱 Web Bluetooth API will work over HTTPS")
    print(f"\nPress Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        os.unlink(cert_file)
        os.unlink(key_file)
        sys.exit(0)

def serve_http():
    """Serve with HTTP (Web Bluetooth won't work)"""
    handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"\n🚀 BitChat PWA Server (HTTP)")
        print(f"   http://localhost:{PORT}")
        print(f"   http://127.0.0.1:{PORT}")
        print(f"\n⚠️  Warning: Web Bluetooth API requires HTTPS to work!")
        print(f"   Install 'cryptography' module for HTTPS: pip install cryptography")
        print(f"\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
            sys.exit(0)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if "--http" in sys.argv:
        serve_http()
    else:
        serve_https()