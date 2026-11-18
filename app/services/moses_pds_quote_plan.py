"""Existing PDS quote triage adapter; unpriced and read only."""
from app.services.moses_pds_quote_triage import triage

def inspect(request, limit=50):
    return triage(request,limit=limit)
