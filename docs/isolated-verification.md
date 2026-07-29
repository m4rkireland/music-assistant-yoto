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

## Pending authorization gate

Real provider loading and library synchronization require a Yoto developer client ID followed by browser authorization. After authorization, verify card/track totals, group browse, `Moshi` search results, artwork/order/durations, token rotation, and fresh stream resolution before any audible or production test.
