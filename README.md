> **Wersja bota: `1.6.19`** · `/wersja`

# PINDOLZ Discord Bot

## Grafiki meczów (Cloudflare Workers AI)

- **~24 h przed meczem** – zapowiedź + obraz AI na kanał główny
- **Po wyniku** – obraz AI na kanał **LIVE**

Model: `@cf/black-forest-labs/flux-1-schnell` (darmowy limit dzienny Workers AI).

### Sekrety na GameHost

```
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...
```

Token: Cloudflare Dashboard → Workers AI → Use REST API → Create Token  
Account ID: ten sam ekran.

Bez tych sekretów bot działa normalnie (tylko bez grafik AI).

## Reszta

`DISCORD_BOT_TOKEN` · `STARTERLEAGUE_API_TOKEN` · Team **869**
