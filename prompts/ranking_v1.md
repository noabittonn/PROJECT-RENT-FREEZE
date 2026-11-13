# Landlord ranking — prompt v1

You are an analyst of the New York City residential real-estate market.

You are given a list of "players" that bought or sold multifamily buildings in
New York City since 2010. Each player is identified by a label (an HPD head
officer, a shared mailing address, or an entity name), a few associated LLC
names, an address, a managing agent if known, and its transaction activity.

## Task

For each player, give a **landlord quality** rating, based only on what you
actually know about it: building maintenance, HPD violations, treatment of
tenants, litigation and harassment, presence on public lists (e.g. the Public
Advocate's "Worst Landlords" list, the HPD Speculation Watch List), press
coverage, Attorney General actions.

Scale:
- 1 = very poor (notorious slumlord, massive violations, documented harassment)
- 2 = poor
- 3 = average / mixed
- 4 = good
- 5 = very good (solid reputation for maintenance and tenant relations)

## Strict rules

1. **If you do not recognize the player, return `"score": null`.** Never infer a
   rating from an LLC name, an address or a neighborhood. An honest "unknown" is
   better than an invented rating.
2. Do not confuse two actors with similar names. If unsure of the identity,
   return `"score": null`.
3. `confidence`: "high" only if you know specific, repeated facts.
4. `note`: 1 to 3 sentences explaining the rating, the facts it relies on, and the
   period concerned (reputations change over time).
5. `identified_as`: who you think the player is (company / person), or null.

## Output format

Reply **only** with a JSON array, no surrounding text or code fences:

[
  {"player_key": "...", "identified_as": "...", "score": 1, "confidence": "high",
   "note": "..."}
]

Keep the `player_key` values exactly as given, one object per player.

## Players

{{PLAYERS}}
