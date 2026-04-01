# Superpowers install status

Date: 2026-04-01 (UTC)

Fetched install instructions from:
- https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md

Attempted commands:
```bash
mkdir -p ~/.codex ~/.agents/skills
git clone https://github.com/obra/superpowers.git ~/.codex/superpowers
ln -s ~/.codex/superpowers/skills ~/.agents/skills/superpowers
```

Result:
- Clone failed in this environment with `CONNECT tunnel failed, response 403`.
- As a result, the symlink target does not exist and installation could not be completed.

Next step in a network-enabled environment:
```bash
git clone https://github.com/obra/superpowers.git ~/.codex/superpowers
mkdir -p ~/.agents/skills
ln -s ~/.codex/superpowers/skills ~/.agents/skills/superpowers
ls -la ~/.agents/skills/superpowers
```
