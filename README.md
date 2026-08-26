# plugin.video.ceknito.sk

Kodi video doplnok pre [ceknito.sk](https://ceknito.sk). Postavený na rovnakom
frameworku (`script.module.stream.resolver`) ako `plugin.video.mojevideo.sk`.

## Funkcie

- prehliadanie podľa kategórií (živo stiahnuté z `/kategorie`)
- zoznamy Najnovšie / Najlepšie hodnotené / Najviac komentované
- vyhľadávanie
- súvisiace videá a komentáre (len najvyššia úroveň) cez kontextové menu
- zobrazenie plného popisu videa
- prehrávanie priamo v natívnej kvalite (360p/480p/720p podľa dostupnosti)

## Inštalácia

1. Skopírujte priečinok `plugin.video.ceknito.sk` do Kodi addons priečinka
   (`~/.kodi/addons/` alebo ekvivalent na danej platforme).
2. Uistite sa, že je nainštalovaný `script.module.stream.resolver`
   (rovnaká závislosť ako `plugin.video.mojevideo.sk`).
3. Reštartujte Kodi, doplnok sa objaví medzi video doplnkami.

## Ako to funguje

- **Zoznamy** (`resources/lib/ceknito.py: list_content`) parsujú HTML bloky
  `<article class="theme2026-video-card">` — spoločnú šablónu pre homepage,
  `/videa` aj `/vyhladavanie`.
- **Prehrávanie** (`resolve`) načíta stránku videa, z atribútu
  `data-manifest-url` zistí odkaz na XML manifest (`/xml/video.xml?fid=...`)
  a z neho priamo vytiahne mp4 URL pre jednotlivé rozlíšenia — žiadne
  dekódovanie hash/cache URL ako pri mojevideo.sk nie je potrebné.
- **Kategórie** sa berú zo stránky `/kategorie` (názov + `categ=<id>`).

Ak sa web ceknito.sk redizajnuje, najpravdepodobnejšie miesto na opravu je
práve `resources/lib/ceknito.py` (regulárne výrazy naviazané na CSS triedy
`theme2026-*`).

## Nastavenia

| Nastavenie | Popis |
|---|---|
| Počet zapamätaných hľadaní | veľkosť histórie vyhľadávania |
| Kvalita videa | Vždy sa spýtať / Najlepšia / Najhoršia |
| Sťahovania | priečinok a notifikácie pri sťahovaní |

## Licencia

GPL-2.0-or-later (rovnako ako `plugin.video.mojevideo.sk`).
