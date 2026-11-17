"""Read-only saved-record briefing when live Moses AI fails.

No writes, approvals, inferred actions or generic AI fallback. Access enforcement
remains in moses_action_center.overview(). Unavailable queues are not counted as zero.
"""
from __future__ import annotations
import logging
import re

_PRIORITY = re.compile(r'\b(?:priority|priorities|attention|what(?:\s+do|\s+should|\s+needs)|follow[ -]?up|followthrough|next\s+(?:steps?|actions?)|(?:my|our|the)\s+week|plan\s+my\s+week|job\s+flow|quote(?:s|\s+queue)?|estimat(?:e|es|ing)|invoice(?:s|ing)|dispatch\s+schedule|work\s+queue|pending\s+approval)\b', re.I)


def recover_office_priorities(request, message: str, workspace: str) -> str | None:
    """Return a bounded factual briefing only for broad priority/queue questions.

    None means use the existing fail-closed error; no records are ever modified.
    """
    if workspace not in ('pds','doorks','sdc') or not _PRIORITY.search(message or ''):
        return None
    try:
        from app.services.moses_action_center import overview
        data=overview(request)
        if not isinstance(data,dict) or data.get('workspace')!=workspace or data.get('read_only') is not True:
            return None
        labels={'work':'Jobs and follow-ups','drafts':'Saved drafts','approvals':'Awaiting approval','delivery':'Delivery follow-ups'}
        lines=['Live AI is unavailable. Here is the verified '+workspace.upper()+' work summary:']
        available=0
        for field,label in labels.items():
            row=data.get(field)
            if not isinstance(row,dict):continue
            if row.get('available') is not True:
                lines.append(label+': unavailable')
                continue
            available+=1
            count=row.get('count')
            lines.append(label+': '+(str(count) if isinstance(count,int) and not isinstance(count,bool) and count>=0 else 'count unavailable'))
            for item in (row.get('items') or [])[:3]:
                if not isinstance(item,dict):continue
                name=str(item.get('customer') or item.get('title') or item.get('record_id') or item.get('job_number') or '').strip()
                next_step=str(item.get('next_step') or item.get('status') or item.get('state') or '').strip()
                if name:
                    lines.append('• '+name[:90]+(' — '+next_step[:110] if next_step else ''))
        if not available:return None
        lines.append('Read-only summary. No records, emails, or approvals were changed. Use the Action Center to continue.')
        return '\n'.join(lines)[:2300]
    except Exception as exc:
        logging.getLogger(__name__).warning('Moses verified briefing unavailable exception_type=%s',type(exc).__name__)
        return None
