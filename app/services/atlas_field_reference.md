# doorks/app/services/atlas_field_reference.md
Version: 0.4
Purpose: Internal “field brain” to stabilize Atlas troubleshooting across:
- automatic operators (slide/swing)
- storefront hardware
- mechanical doors (alignment, hinges, pivots, closers)
- electrified hardware (power, strikes, exit devices, EL)
- RSD (rolling steel doors) and operators

===============================================================================
0) NON-NEGOTIABLES (THE STUFF THAT FIXES 80% OF CALLS)
===============================================================================

0.1 Mechanical-first isolation
If it binds by hand, stop changing settings. Fix the door first.
- Automatic swing: door must swing freely by hand through full range (no latch preload fight).
- Automatic slide: leaf must travel smoothly (track/hangers/anti-rise/guides).
- RSD: curtain must move without guide pinch or telescoping; operator can’t overcome a mechanical jam.

0.2 “Runs but doesn’t move” = coupling/clutch/drive issue until proven otherwise
Common: loose set screw, missing key, slipping clutch, stripped gear, broken chain/sprocket.
Field move: paint-mark the shaft and coupler, jog it, see what slips.

0.3 “Worked yesterday” usually means a change
Top repeat offenders:
- Loose termination / broken conductor in header or hinge jamb
- Sensor aim drift / dirty lens / reflections on glass or polished floors
- Door sag (hinge screws backed out, pivot wear)
- Voltage sag under load (bad PSU/battery, long run voltage drop)

0.4 Monitored vs non-monitored (big difference)
If controller expects supervised safety:
- A basic NO/NC dry contact can fault.
- Don’t guess. Confirm monitoring/EOL/two-channel requirements.

===============================================================================
1) INTAKE QUESTIONS (ASK THESE EARLY TO AVOID GENERIC ANSWERS)
===============================================================================
- What exact make/model/revision? (photo of label)
- Door type: swing / slide / bi-part / folding / storefront manual / fire door / RSD / gate?
- Symptom: dead / opens only / won’t close / reverses / drags / slams / ghosting / error code?
- Any display code / LED pattern?
- What changed last? flooring, weatherstrip, hinges, sensor swap, operator swap, strike/lock work, impact
- What safeties are installed? (presence, beams, edges) and are they monitored?

===============================================================================
2) MECHANICAL DOORS — ALIGNMENT, HINGES, STRIKES (HIGH-VALUE FIELD FIXES)
===============================================================================

2.1 Find the rub point first (don’t guess)
- Lead edge drags: usually sag, pivot wear, frame rack, threshold raised/new flooring.
- Hinge side binds: hinge leaf/bearing wear, hinge mortise depth, frame twist.
- Head rub: frame out of square, door warp, hinge set.

2.2 Hinge screw reality (fastest win)
- Loose screws: tighten and check again.
- Stripped screws:
  - wood backing: longer screws into stud (commonly 3")
  - hollow metal: correct thread, sex bolts, or proper anchors (don’t jam drywall screws)

2.3 Shimming hinges (field basics)
Goal: move the door leaf relative to the frame to restore reveals.
- Lead edge dragging at floor:
  - often shim TOP hinge (behind hinge leaf) to lift latch side and reduce sag effect
  - sometimes shim MIDDLE hinge to tune reveal
- Hinge side bind:
  - shim appropriate hinge(s) to move leaf away from bind (small increments)

Rule: small shims + re-check. Don’t “stack” blindly.

2.4 Strike chasing (don’t do it too early)
If you move the strike to “make it latch” on a sagging door, it’ll come back.
Order:
1) fix sag/bind
2) then align strike/latch
3) then fine tune latch preload

2.5 Door won’t latch (repeat patterns)
- latch preload from sag: door hits strike face
- frame spread: reveal tight at top/bottom on strike side
- weatherstrip too aggressive
- closer mis-set (closing too slow or latch valve too closed)

===============================================================================
3) CLOSERS (SURFACE / CONCEALED / FLOOR) — TROUBLE PATTERNS
===============================================================================
- Sweep = main speed, Latch = last few inches, Backcheck = opening cushion
Trouble patterns:
- “Slams” → latch valve too open or door binding then releasing
- “Won’t close all the way” → latch valve too closed OR latch preload/binding
- “Hard to open” → binding/hinges/threshold first, then closer power

Floor closer notes:
- Leaking oil / spongy adjustment = often replacement, not tuning.

===============================================================================
4) STOREFRONT / ALUMINUM & GLASS (CRL/JACKSON, PATCH, PIVOTS)
===============================================================================

4.1 Core components
- Top pivot/patch, bottom pivot, threshold, header, closer (if floor closer), lock/exit device.

4.2 Common storefront problems
- Lead-edge drag: bottom pivot shift/wear, top pivot wear, threshold height change, door sag.
- Door won’t latch: pivot wear + strike misalignment, frame rack, latch preload.
- Glass panel shift: loose clamps/patch fittings, missing shims.

4.3 Safe adjustment workflow
- Support the door BEFORE loosening pivots/patch screws.
- Make small adjustments, re-check reveal and latch each time.

===============================================================================
5) LOCKSETS vs EXIT DEVICES — DON’T MIX THESE UP
===============================================================================

5.1 Locksets
- Cylindrical: bored latch; common hollow metal
- Mortise: body inside door pocket; higher grade
- Leverset: trim type (could be cyl or mortise)

Common lock issues:
- latch preload (alignment)
- worn latch / loose chassis
- electrified trim: polarity/voltage/continuous duty

5.2 Exit devices (panic)
- Rim / vertical rod (SVR/CVR) / mortise
Common panic issues:
- door sag causes latch/strike miss
- vertical rod timing (top/bottom latch out of sync)
- device loose to door skin, dogging misuse

===============================================================================
6) AUTOMATIC SLIDING DOORS — FIELD TROUBLESHOOTING MAP
===============================================================================

6.1 Ghosting / won’t close / cycling
Almost always:
- presence held active (overhead presence or threshold presence)
- safety beam blocked/misaligned
- input stuck active (wiring NO/NC wrong, monitored mismatch)
- reflections/moving signs/HVAC

Field method:
1) Look for input LEDs / diagnostics (which input is active?)
2) Isolate sensors one at a time (remove input) to find culprit
3) Clean/aim/reduce field; confirm wiring type and monitoring

6.2 Dragging / scraping
Likely:
- worn hangers/rollers
- track debris/damage
- anti-rise/bottom guide misadjusted
- header shifted / leaf sag

6.3 Motor runs but belt/chain doesn’t move
Likely:
- coupler/key/setscrew loose
- clutch slipping
- sprocket/drive wheel not engaged
- gearbox stripped

===============================================================================
7) AUTOMATIC SWING OPERATORS — LEARN CYCLE FAILS & SLAMMERS
===============================================================================

7.1 Learn/teach cycle fails
Most common:
- door binds mechanically (hinges, latch preload, warped frame)
- arm geometry wrong (push/pull, shoe location)
- safety input held active during learn

Field method:
1) door swings freely by hand through full range
2) confirm arm geometry/handing
3) remove activation inputs temporarily; ensure safety not held active
4) run learn; then re-enable and test

7.2 Door slams / won’t latch
- fix mechanical alignment first
- then tune valves in small steps

===============================================================================
8) RSD (ROLLING STEEL DOOR) — CORRECT TERMINOLOGY & REAL DIAGNOSIS
===============================================================================
RSDs do NOT have “rollers.”
They have: curtain/slats, guides, barrel/shaft, torsion springs, headplates/bearings, bottom bar, stops, sometimes operator.

8.1 “Stuck halfway” causes
- guide damage/crush or debris
- curtain telescoping (coil tracking to one side)
- endlocks binding
- bottom bar cocked
- lock engaged / slide bolts

8.2 Operator runs but curtain doesn’t move
- coupling/key/setscrew loose
- clutch slipping
- drive chain broken
- sprocket slip
- gearbox stripped

8.3 “Hard to lift / operator struggling”
- door out of balance (springs)
- binding in guides
- bearing/headplate issues
- curtain rubbing hard (coil tracking)

Field method:
- Lock out power; inspect guides/headplates; check coil tracking; verify coupling/clutch.

===============================================================================
9) ELECTRIFIED HARDWARE — PRACTICAL RULES (NO/NC, VOLTAGE, FAIL SAFE/SECURE)
===============================================================================

9.1 NO vs NC (fast field decision)
- Meter the sensor relay:
  - COM-NC closed at idle → NC pair
  - COM-NO open at idle → NO pair
- Confirm what the controller expects:
  - Activation often uses NO closure
  - Safety/stop often uses NC for fail-safe
But: monitored inputs override “normal” assumptions.

9.2 Voltage pitfalls
- Sensor wants 12–24VDC (or 24VAC on some legacy).
- Long runs cause drop; low voltage causes chatter/false triggers.
- Separate high/low voltage routing to reduce noise.

===============================================================================
10) WHAT ATLAS SHOULD DO WHEN IT CAN’T BE EXACT
===============================================================================
- Give the safest next 3–6 steps that isolate the fault.
- Ask for the one photo that unlocks exactness:
  - label photo + terminal strip photo + any screen/LED code
- Do NOT guess terminal numbers, flash counts, or programming indexes without the correct model/table.

===============================================================================
11) HIGH-VALUE TERMS ATLAS SHOULD RECOGNIZE
===============================================================================
automatic slide: fis, handing, bi-parting, breakout, presence, activation, safety beam, monitored, header, hanger, anti-rise
automatic swing: learn/teach, push/pull arm, handing, backcheck, latch, presence/safety
exit devices: rim, cvr, svr, mortise, dogging, latchbolt, strike, rod timing
locksets: cylindrical, mortise, lever, latch preload, strike alignment
electrified: EL, EPT, power transfer, REX, DPS, fail safe/secure, continuous duty
rsd: curtain, slats, guides, headplates, barrel, torsion springs, clutch, sprocket, coupling, limits
