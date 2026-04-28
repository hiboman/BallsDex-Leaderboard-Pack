# BallsDex V3 Leaderboard Package

Leaderboard system for **BallsDex V3**. Players can view the leaderboard of people with the most caught countryballs.

## Commands

| Command | Description |
|---|---|
| `/balls leaderboard` | Show the leaderboard of players with the most caught countryballs |

## Installation

### 1 — Configure extra.toml

**If the file doesn't exist:** Create a new file `extra.toml` in your `config` folder under the BallsDex directory.

**If you already have other packages installed:** Simply add the following configuration to your existing `extra.toml` file. Each package is defined by a `[[ballsdex.packages]]` section, so you can have multiple packages installed.

Add the following configuration:

```toml
[[ballsdex.packages]]
location = "git+https://github.com/hiboman/BallsDex-Leaderboard-Pack.git"
path = "leaderboard"
enabled = true
editable = false
```

**Example of multiple packages:**

```toml
# First package
[[ballsdex.packages]]
location = "git+https://github.com/example/other-package.git"
path = "other"
enabled = true
editable = false

# Leaderboard Package
[[ballsdex.packages]]
location = "git+https://github.com/hiboman/BallsDex-Leaderboard-Pack.git"
path = "leaderboard"
enabled = true
editable = false
```

### 2 — Rebuild and start the bot

```bash
docker compose build
docker compose up -d
```

This will install the package and start the bot.
