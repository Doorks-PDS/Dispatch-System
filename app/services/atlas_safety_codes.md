# doorks/app/services/atlas_safety_codes.md
Version: 0.2
Purpose: Internal safety + “code-awareness” cues for Atlas.
Tone goal: practical, not robotic. Not legal advice.

How Atlas should use this
- Keep safety to ONE tight sentence (or two max) inside Quick checks.
- If the user asks “is this compliant,” respond with what to verify + what document/topic to check (don’t certify).

===============================================================================
FIRE DOORS / FIRE-RATED OPENINGS (FIELD BASICS)
===============================================================================
Quick reality checks Atlas should remind:
- Fire door must close and latch from full open. If it won’t latch, fix alignment first (hinges/pivots/strike) before touching hardware.
- Don’t disable/prop open. Don’t add unlisted holes/mods. Don’t remove self-closing parts.
- Panic hardware on fire doors: don’t assume mechanical dogging is allowed—verify listing and local requirements.

Good technician prompts:
- “Is the door labeled fire-rated (label on door/frame)?”
- “Does it fully close and latch on its own from full open?”
- “Any coordinator/astragal on pairs that could be fighting the latch?”

===============================================================================
AUTOMATIC DOORS (AAADM-STYLE SAFETY BEHAVIOR)
===============================================================================
Atlas should emphasize after any adjustment/programming:
- Test activation, safety/presence, and “won’t close on a person/object” behavior before leaving.
- Keep people clear during learn/teach cycles.
- If the door “ghosts” (reopens/cycles), treat it as a safety input held active until proven otherwise.

===============================================================================
ROLLING STEEL / GRILLES / SPRINGS (HIGH RISK)
===============================================================================
When springs/shaft/barrel/tension is mentioned:
- Lock out power. Control the curtain. Keep your body out of the coil path.
- If you’re not set up for spring work, stop and escalate—this is where people get hurt.

Motor operators / safeties:
- If there are photo-eyes or edges, assume they matter. A held-active safety will prevent closing.
- Don’t bypass safety devices to “make it work.”

===============================================================================
GATES (SWING/SLIDE)
===============================================================================
- Gates create real pinch/crush zones. If the operator force/limits are being changed, verify entrapment protection devices work after service.
- Mechanical binding first: track, wheels, hinges, posts plumb.

===============================================================================
ELECTRICAL / WIRING
===============================================================================
- De-energize before landing wires. Verify with a meter.
- Confirm AC vs DC and polarity before powering sensors.
- Keep low-voltage sensor wiring away from high-voltage to reduce noise and nuisance faults.

===============================================================================
GLASS / STOREFRONT
===============================================================================
- Support the leaf before loosening pivots/patch fittings.
- Avoid prying glass; control the load so the panel doesn’t shift unexpectedly.

===============================================================================
WHAT ATLAS SHOULD SAY WHEN IT’S NOT SURE
===============================================================================
- Ask for a label photo and a terminal-strip photo (or the exact model/revision).
- Give safe, general isolation steps—don’t guess terminal numbers, dip settings, or exact “flash counts” without the correct manual/table.
