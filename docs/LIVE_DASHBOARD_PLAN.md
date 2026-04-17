# Live Dashboard Plan for OBD2 Data Viewer

## Goal
Replace the single-pass table printout with a continuously updating, in-place live dashboard using `rich.live`.

---

## Why `rich.live`?
- Pure Python, integrates natively with `asyncio`
- Requires minimal changes to existing code (~20 lines)
- No curses, no threading, no complex TUI framework
- Table renders in-place — no terminal scrolling

---

## Steps

### 1. Install `rich`
```bash
pip install rich
```

### 2. Add a shared data store in `main()`
Create a `dict` (e.g., `dashboard_data = {}`) keyed by PID code. Each entry holds `{name, value, unit}`. This replaces direct printing. ✅

### 3. Refactor `notification_handler` in `main.py`
Instead of `print()`ing each row, update `dashboard_data[result['pid']] = result`. For unrecognized responses, either skip or store in a separate log. ✅

### 4. Add a `build_table()` helper
A function that reads `dashboard_data` and returns a `rich.table.Table` object with columns PID, Name, Value. Called on every refresh.

### 5. Wrap the PID request loop in `while True`
Replace the single-pass loop with an infinite loop that continuously cycles through `PID_LIST`, requesting each PID and sleeping between requests. Add a small extra sleep between full sweeps if desired.

### 6. Use `rich.live.Live` as an async context manager
Wrap the polling loop inside a `Live(build_table(), refresh_per_second=4)` context. After each PID response arrives and updates `dashboard_data`, call `live.update(build_table())` to re-render the table in-place.

### 7. Move init output out of the live region
Keep the initialization commands and their `print()` output *before* entering the `Live` context so they don't get overwritten.

### 8. Handle graceful exit
Wrap the `while True` loop in a `try/except KeyboardInterrupt` so Ctrl+C stops the loop cleanly before calling `stop_notify`.

---

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Rendering library | `rich.live` over `curses`/`textual` | ~20 lines of changes, zero architectural rework |
| Data store | Shared `dict` over queue | Single-threaded event loop makes a plain dict safe and simple |
| Update timing | `live.update()` after each PID (not after full sweep) | Snappier visual feedback as values trickle in |

---

## Verification Checklist

- [ ] Run with `simulation_on = True` — table renders in-place with values updating every ~2s
- [ ] Values change randomly each sweep (simulator already randomizes)
- [ ] Ctrl+C exits cleanly without a traceback
- [ ] Terminal does not scroll — table stays fixed in place

---

*Plan created: March 6, 2026*