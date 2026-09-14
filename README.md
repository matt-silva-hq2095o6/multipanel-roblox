# multipanel-roblox

Terminal dashboard and multi-instance manager for Roblox Open Cloud places and universes.

I built this because checking live server states, logs, and datastore entries across 4 different test universes meant keeping a dozen browser tabs open. This puts them all in one terminal view with live polling and quick actions.

## Requirements

- Python 3.11+
- Roblox Open Cloud API key (with Universe, MessagingService, and Datastore permissions)

## Install

```bash
git clone https://github.com/user/multipanel-roblox.git
cd multipanel-roblox
pip install -e .
```

## Configuration

Create `~/.config/multipanel-roblox/config.toml` or set `ROBLOX_API_KEY` in your environment:

```toml
api_key = "your-open-cloud-key"
poll_interval = 5

[[universes]]
name = "staging-eu"
universe_id = 123456789
places = [1234567890, 1234567891]

[[universes]]
name = "prod-main"
universe_id = 987654321
places = [9876543210]
```

## Usage

Start the interactive panel:

```bash
multipanel-roblox watch
```

Tail logs for a specific place:

```bash
multipanel-roblox logs --universe 123456789 --tail 50
```

Trigger a server message broadcast:

```bash
multipanel-roblox broadcast --universe 123456789 --topic Maintenance --data "Restarting in 2m"
```

Inspect datastore keys:

```bash
multipanel-roblox datastore list --universe 123456789 --name PlayerData
```

## License

MIT

<!-- checked: 2026-09-14 -->
