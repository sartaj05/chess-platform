# Module 2: Rooms, Invite URLs, LAN Lobby, and WebSocket Room Foundation

This module adds the room layer that sits between authentication and the chess game engine.

## Included features

- Public and private rooms
- Online rooms
- LAN rooms
- Offline and same-PC room modes
- Guest room creation
- Registered user room creation
- Join by room code
- Join by invite URL: `/play/<ROOM_CODE>/`
- Automatic guest session identity
- Room participants with roles: host, player, spectator
- Room presence tracking
- Room ready/not-ready state
- Realtime room chat over WebSockets
- Room state JSON endpoint for reconnect/recovery
- REST API for mobile-ready room creation, list, detail, and join
- Admin management for rooms, participants, and events
- Celery task to expire stale waiting rooms
- Database migrations, indexes, constraints, and tests

## Important URLs

- `/rooms/` — public live rooms
- `/rooms/create/` — create room
- `/rooms/join/` — join by code
- `/rooms/lan/` — LAN multiplayer instructions
- `/play/<ROOM_CODE>/` — room invite URL
- `/play/<ROOM_CODE>/state/` — room state JSON
- `/api/rooms/` — REST list/create
- `/api/rooms/<ROOM_CODE>/` — REST detail
- `/api/rooms/<ROOM_CODE>/join/` — REST join
- `/ws/rooms/<ROOM_CODE>/` — WebSocket room channel

## LAN usage

1. Run the stack on one computer or server in the local network.
2. Open `/rooms/create/?mode=lan`.
3. Create a LAN room.
4. Share the generated URL with the second computer.
5. Replace `localhost` with the host IP address if needed, for example `http://192.168.1.50/play/ABCD1234/`.
6. Make sure the firewall allows the application port.

## Next module dependency

Module 3 will attach the chessboard, legal move validation, timers, PGN/FEN, and server-side game state to the room created in this module.
