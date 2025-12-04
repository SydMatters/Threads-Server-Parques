## Parqués Backend (FastAPI + TCP)

- FastAPI: health, players CRUD, crear/listar partidas (`/games`). Registro de jugadores en SQLite (ver `database/players.py`).
- Juego en tiempo real: TCP JSON newline-delimited en `tcp_host:tcp_port` (por defecto `0.0.0.0:9000`). Un hilo por cliente y un hilo por partida.

### Flujo mínimo
1. Crear partida vía REST: `POST /games`.
2. Conectar por TCP y enviar `{"type":"join","game_id":"<id>","player":"Ana"}`. El servidor auto-inicia la partida cuando hay >=2 jugadores.
3. Tirar dados: `{"type":"roll"}` → broadcast `{"type":"rolled",...}`.
4. Mover ficha: `{"type":"move","token_id":0,"steps":null}` (steps `null` usa la suma del último tiro) → broadcast `{"type":"state",...}`.
5. Sync reloj opcional: `{"type":"sync_time","client_time_ms":...}` → respuesta `sync_ack`; el servidor también envía `sync_update` periódico con `clock_ms`.
6. Finaliza con `{"type":"finished","winner":"..."}` broadcast.

Mensajes JSON van separados por salto de línea. Cada respuesta de estado incluye `state` con tablero/turno/clock_ms.
