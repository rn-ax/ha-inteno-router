# ha-inteno-router

Home Assistant custom integration for the Inteno/IOPSYS home router.

**This integration is fully vibe coded** — written by an AI coding agent, not hand-written. It's been tested end-to-end against a real Home Assistant instance and a real router, but review the code yourself before trusting it with your own setup.

**Only tested against an Inteno EG300** (hardware `EG300`, model `EG300X`). Other Inteno/IOPSYS models likely expose a similar `ubus` API (IOPSYS is the same underlying firmware family), but the exact object/method names and response shapes haven't been verified on anything else — expect to need adjustments if you're running different hardware.

See `AGENTS.md` for architecture and setup.
