"""Detect explicit PDS document email intents without capturing ordinary quote lookup.

Never interpret this classifier as consent to send; only the approved mail
ledger and an independently signed-in person may send a customer email.
"""
import re


def is_pds_document_mail_request(message):
    if not isinstance(message, str) or len(message) > 1500:
        return False
    text = message.casefold()
    action = bool(re.search(r'\b(?:send|email|e-mail|mail|deliver|forward|resend|prepare to send|draft an? email)\b', text))
    document = bool(re.search(r'\b(?:estimate|quote|invoice|document|pdf)\b|\b(?:re|js)[0-9]{5,}\b', text))
    return action and document
