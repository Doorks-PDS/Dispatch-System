def safety_notice(q: str) -> str:
    s = (q or "").lower()

    # Rolling steel / roll-up / spring energy
    if any(k in s for k in ["rolling steel", "roll up", "rsd", "tension", "spring", "winding bar", "barrel", "tension wheel"]):
        return "Rolling steel/roll-up springs store serious energy—use proper winding bars, keep your body out of the winding path, and clamp/secure the curtain before loosening hardware."

    # Glass / herculite / patch fittings
    if any(k in s for k in ["herculite", "glass door", "patch", "rail", "spindle", "floor closer"]):
        return "Support the door weight before loosening pivots/patch hardware—glass can shift fast and crack; use a helper and protect the glass edges."

    # General powered operator caution (only if relevant)
    if any(k in s for k in ["operator", "automatic", "controller", "ed400", "ed250", "record 8100", "mc521"]):
        return "Keep clear of the door swing/slide path during testing and verify safeties are operational before returning the opening to service."

    return ""

