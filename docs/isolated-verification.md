# Isolated verification record

## Environment

- Music Assistant source: tag `2.9.9`, commit `e9dea6d49fd1e5d8570293f171369169f2b02d9d`
- Python: 3.14.2
- Models: `music-assistant-models==1.1.129.post1`
- Yoto client: `yoto-api==4.3.2`
- Provider source: reversible symlink from the isolated source checkout
- Data: `/home/dave/work/music-assistant-yoto-isolated-data`
- Cache: `/home/dave/work/music-assistant-yoto-isolated-cache`
- UI: local port 8095
- Production Home Assistant add-on: untouched

## Verified

- Full standalone server dependency environment installed and imports passed.
- Server started from the exact 2.9.9 source with its own data/cache directories.
- Provider appeared in **Add a music source** as `Yoto` with its description.
- Selecting it opened **Setup provider: Yoto**.
- Setup displayed the unofficial warning, required Yoto OAuth client-ID field, and authorization action.
- No production Music Assistant add-on file/config was edited or restarted.

## Live-account verification

Completed on 2026-07-29 against the isolated instance:

- Browser Authorization Code + PKCE completed with `family:library:view` and `offline_access`.
- Music Assistant loaded the real Yoto provider and imported 676 tracks.
- Card and track artwork rendered in Music Assistant.
- Search for `Moshi` returned the cards `Moshi: Bedtime with Moshi` and `Close Your Eyes`.
- The Moshi results included ordered tracks such as `Bobo the Lullaby Llama`, `Buster's Sleepy Egg Hunt`, `Close Your Eyes Sleepy Paws`, `Dawdles the Twiilight Tortoise`, `Jeepers Brings the Nightime Ease`, `Night Swimming with Yawnsy`, `Nodkins Goes Dream Hopping`, and `Wuzzle's Windchime Wood`.
- Restarting the isolated Music Assistant server loaded Yoto again without browser authorization, confirming persisted refresh authentication.
- A real `Bobo the Lullaby Llama` stream resolved in 173 ms. Music Assistant detected AAC at 44.1 kHz/128 kb/s and received its first audio chunk after 0.18 seconds.
- Log and settings scans found no access token, refresh token, or signed stream URL text.

## Deferred audible playback

The approved Kitchen Sonos test reached stream resolution and decoding, but the Sonos returned `ERROR_PLAYBACK_NO_CONTENT`. The isolated stream relay is `192.168.100.33:8097` while Kitchen is `192.168.20.76`; the host firewall is open, but the Sonos VLAN cannot initiate the relay fetch. Kitchen remained idle.

The audible retry is deferred. It requires either a narrow temporary allowance from `192.168.20.76` to `192.168.100.33` TCP 8097 or an isolated Music Assistant host reachable from the Sonos VLAN. Production deployment remains blocked until this test is completed or the user explicitly changes that requirement.
