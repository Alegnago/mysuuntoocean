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

Scarto tra il modello e il disegno: medio 0,25 px, massimo 1 px (0,08 mm).
Spessore risultante dal disegno: 15,32 mm (il dato ufficiale è 15,1 mm).

![overlay](docs/overlay.png)
![overlay zoom](docs/overlay_zoom.png)

Anse e bottoni non ci sono ancora.

## Uso

```bash
pip install -r requirements.txt
python tools/trace_profile.py      # disegno -> data/profile_mm.json
python watch_body.py               # -> export/suunto_ocean_body.step + .stl
python tools/overlay.py            # controllo: docs/overlay.png, docs/overlay_zoom.png + scarto
python tools/export_preview.py     # aggiorna l'anteprima web docs/preview.html
```
