# mysuuntoocean

Modello 3D parametrico della Suunto Ocean, costruito con [CadQuery](https://cadquery.readthedocs.io).

## Fase 1: corpo cassa (revolve)

Il corpo è la rivoluzione a 360° della mezza sezione dell'orologio. La sezione non è
disegnata a mano: `tools/trace_profile.py` la ricalca sul disegno tecnico ufficiale
(`reference/suunto_ocean_drawing.png`), misurando la mezzeria di ogni tratto con
precisione sub-pixel (scala dalla quota Ø 49,9 mm = 624,2 px).

- Faccia superiore piana, raccordo e fianco di lunetta/cassa: ricalcati riga per riga.
- Sotto la lunetta il fianco è una retta (pendenza 0,594, letta nel tratto visibile
  tra le anse) prolungata fino alla linea di fondo **più bassa** del disegno.
- Fondello bombato e gradino del sensore: ricalcati colonna per colonna.
- Le linee orizzontali che attraversano tutta la vista (lunetta/cassa, attacco anse,
  linea di fondo più alta) sono giunzioni tra pezzi e non cambiano il profilo.

Scarto tra il modello e il disegno: medio 0,24 px, massimo 0,79 px (0,063 mm).
Spessore risultante dal disegno: 15,32 mm (il dato ufficiale è 15,1 mm).

![overlay](docs/overlay.png)
![overlay zoom](docs/overlay_zoom.png)

## Fase 2: piattaforma dei tasti + tasti

Il corpo della fase 1 non cambia. `watch_buttons.py` aggiunge due layer separati,
ricavati da `tools/trace_buttons.py` (`data/buttons_mm.json`):

- **Piattaforma** (`export/suunto_ocean_platform.*`): loft di sezioni radiali da -46° a
  +46° (passo 1.5°). Ogni sezione, vista di lato: dalla giunzione con la lunetta la
  superficie si apre fino a una spalla (z 10.96, la linea "a lente" della vista frontale),
  scende in verticale al raggio del contorno in pianta, e sotto rientra inclinata fino al
  fianco del corpo (bordo esterno z 5.84 sui lobi, 5.35 sotto il tasto centrale; incontro
  col fianco a z 4.57: le linee y≈427/433/443 della vista frontale). Il contorno in pianta
  è il bordo in comune con il tasto, ricalcato, che alle estremità entra tangente nel
  cerchio della cassa (`BLEND_END_DEG`); verso le anse la fascia si riassorbe nel corpo.
- **Tasti** (`export/suunto_ocean_buttons.*`): ogni tasto è l'intersezione tra la forma in
  pianta (estrusa in verticale) e la sagoma della vista frontale (estrusa in profondità),
  quindi entrambe le viste coincidono con il disegno. Le dentellature sono le tacche
  del contorno in pianta. In pianta la parte interna dei tasti laterali è coperta dalla
  piattaforma e dal bordo della cassa: lì l'estensione la decide la vista frontale.
- `export/suunto_ocean_case.*` = corpo + piattaforma in un solido unico.

## Fase 3: anse

`watch_lugs.py` (layer separato, `export/suunto_ocean_lugs.*`), forme da
`tools/trace_lugs.py` (`data/lugs_mm.json`). Ogni ansa è un tronco di piramide deformato:
l'involucro convesso (facce piane) di pochi punti presi dal disegno:

- in alto, nascosto sotto la lunetta, il rettangolo alla giunzione lunetta/cassa (z 11.53),
  largo in X quanto la gamba lì (tra bordo esterno e bordo interno della vista frontale)
  e in Y dal lato cinturino (Y -11.04) al bordo esterno della pianta;
- il piede, piatto: l'estremità dell'ansa in pianta (punta, lato cinturino e la linea
  tratteggiata, che è lo spigolo di sotto), da z 2.17 (dove nella vista frontale comincia
  la punta) a z 0;
- l'attacco in basso alla cassa, dove la linea di fondo della vista frontale incontra la
  cassa (z 2.81).

Ne escono il contorno in pianta, la sagoma frontale della gamba e il bordo interno della
gamba come spigolo tra due facce. Si costruisce un'ansa, le altre tre sono speculari.
Spazio tra le anse: ~22 mm.

Orientamento: le anse stanno a destra e a sinistra nella pianta del disegno, quindi il
lato dei tasti (in basso nella pianta, -Y) è il lato **ore 3** dell'orologio.

## Uso

```bash
pip install -r requirements.txt
python tools/trace_profile.py      # disegno -> data/profile_mm.json
python watch_body.py               # -> export/suunto_ocean_body.step + .stl
python tools/trace_buttons.py      # disegno -> data/buttons_mm.json
python watch_buttons.py            # -> export/suunto_ocean_{platform,buttons,case}.step + .stl
python tools/trace_lugs.py         # disegno -> data/lugs_mm.json
python watch_lugs.py               # -> export/suunto_ocean_lugs.step + .stl
python tools/overlay.py            # controllo: docs/overlay.png, docs/overlay_zoom.png + scarto
python tools/export_preview.py     # anteprima web: docs/preview.html + piani di riferimento docs/ref_*.png
```
