"""HTTPS requests with certificate verification, including Windows system roots."""
import ssl
import urllib.request

CONTEXT=ssl.create_default_context()
if hasattr(ssl,'enum_certificates'):
    for store in ('ROOT','CA'):
        for cert,encoding,trust in ssl.enum_certificates(store):
            if encoding=='x509_asn' and (trust is True or ssl.Purpose.SERVER_AUTH.oid in trust):
                try:CONTEXT.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(cert))
                except ssl.SSLError:pass

def urlopen(request,timeout=25):
    return urllib.request.urlopen(request,timeout=timeout,context=CONTEXT)
