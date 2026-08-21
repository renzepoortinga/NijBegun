"""Gedeelde TLS-context voor HTTP-calls naar MagicPlan."""
import ssl


def magicplan_ssl_context():
    """Behoud alle TLS-controles behalve de extra strikte RFC 5280-profielcheck."""
    context = ssl.create_default_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context
