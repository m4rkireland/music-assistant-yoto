# Future Music Assistant Tag Player mapping

NFC is not part of the initial Yoto provider.

When Music Assistant Tag Player is available, the narrow follow-up should be:

1. Read the physical Yoto card UID/NDEF identity in Home Assistant or Tag Player.
2. Maintain a small mapping from that UID to the already imported Yoto album provider ID (the stable Yoto card ID), or to a chosen imported track ID.
3. Ask Music Assistant to queue/play that imported item on the configured player.
4. Leave authentication, catalogue refresh, stream resolution, metadata, and ordering inside the Yoto provider.

This avoids duplicating signed URLs or Yoto credentials in NFC automations. Enrollment UX, reader hardware, LED/buzzer feedback, volume limits, resume behaviour, and child-friendly controls are separate follow-up work and must not expand the provider's first release.
