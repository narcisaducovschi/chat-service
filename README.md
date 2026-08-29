# Chat Service

Chat en tiempo real con salas, construido sobre WebSockets, que reutiliza la autenticación de un servicio independiente (`auth-service`) en lugar de duplicar la lógica de login.

Proyecto de portafolio centrado en comunicación en tiempo real y en cómo varios microservicios pueden compartir una misma identidad de usuario sin depender el uno del otro en cada petición.

## Arquitectura

```
auth-service (puerto 8000)              chat-service (puerto 8001)
       │                                        │
       │  POST /auth/login                      │
       │  devuelve un JWT firmado                │
       │◄────────────────────────────────────────┤ (el usuario se loguea aquí)
       │                                          │
       │                                          ▼
       │                                el cliente conecta el WebSocket
       │                                pasando el JWT como query param
       │                                          │
       │                                          ▼
       │                                el chat-service decodifica el JWT
       │                                usando la MISMA SECRET_KEY,
       │                                sin llamar al auth-service
       │                                          │
       │                                          ▼
       │                                WebSocket aceptado, unido a una sala
       │
       ▼
GET /ws/{room}?token=...
  │
  ├─ valida el token (tipo "access", firma, expiración)
  ├─ crea la sala si no existe
  ├─ envía el historial reciente de la sala (Postgres)
  ├─ difunde la lista de usuarios conectados
  └─ retransmite mensajes, avisos de sistema y de "escribiendo…"
     solo a los conectados de esa sala
```

## Stack

- **API / WebSockets**: FastAPI
- **Base de datos**: PostgreSQL + SQLAlchemy (salas y mensajes)
- **Autenticación**: JWT emitidos por un servicio externo (`auth-service`), verificados aquí con la misma clave de firma
- **Frontend**: HTML + JavaScript vanilla, servido como estáticos desde FastAPI
- **Infraestructura local**: Docker Compose

## Funcionalidades

- [x] Conexión WebSocket autenticada mediante JWT compartido con `auth-service`
- [x] Rechazo de conexiones sin token válido o con un token que no sea de tipo `access`
- [x] Salas: los mensajes solo se difunden entre quienes están conectados a la misma sala
- [x] Persistencia de mensajes en PostgreSQL
- [x] Historial reciente enviado automáticamente al conectarse a una sala
- [x] Lista de usuarios conectados por sala, actualizada en tiempo real
- [x] Indicador de "usuario escribiendo…" (efímero, no se persiste)
- [x] Frontend funcional: login, elegir sala, chat con mensajes propios/ajenos diferenciados
- [x] Protección básica contra XSS al mostrar mensajes (escapado de HTML)
- [ ] Broadcast distribuido con Redis pub/sub (necesario si el servicio corriera en más de una instancia; ahora mismo el estado de conexiones vive en memoria de un único proceso)
- [ ] Reconexión automática del WebSocket en el cliente si la conexión se corta
- [ ] Tests automatizados

## Cómo ejecutarlo en local

### Requisitos

- Python 3.11+
- Docker y Docker Compose
- Una instancia de [`auth-service`](https://github.com/narcisaducovschi/auth-service) corriendo, con la **misma** `SECRET_KEY` que este proyecto

### 1. Clonar el repositorio

```bash
git clone https://github.com/narcisaducovschi/chat-service.git
cd chat-service
```

### 2. Crear el entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate  # en Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configurar las variables de entorno

```bash
cp .env.example .env
```

**Importante**: copia el valor de `SECRET_KEY` directamente desde el `.env` de tu `auth-service` — debe ser exactamente el mismo en ambos proyectos, o el chat-service no podrá validar los tokens.

### 4. Levantar Postgres

```bash
docker-compose up -d
```

### 5. Arrancar el auth-service (en otra terminal, desde su propia carpeta)

Este proyecto depende de tener el auth-service disponible en `http://localhost:8000` para poder loguearse. Consulta su propio README para levantarlo.

### 6. Arrancar el chat-service

```bash
uvicorn app.main:app --reload --port 8001
```

### 7. Probar con el frontend

```
http://localhost:8001/static/index.html
```

Inicia sesión con un usuario ya registrado en el auth-service, elige o crea una sala, y empieza a chatear. Abre una segunda pestaña (o navegador) para probar el chat con más de un usuario.

## Uso a bajo nivel (WebSocket)

Conectarse a una sala requiere un access token válido, obtenido primero desde el auth-service:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "tu_contraseña"}'
```

Con el `access_token` de la respuesta, conectarse a una sala:

```
ws://localhost:8001/ws/{nombre_de_sala}?token=TU_ACCESS_TOKEN
```

Los mensajes que viajan por el WebSocket son JSON con un campo `type`:

```json
{"type": "message", "content": "hola a todos"}
{"type": "typing"}
```

Y el servidor responde con distintos tipos:

```json
{"type": "message", "user_email": "...", "content": "...", "created_at": "..."}
{"type": "system", "content": "alguien@ejemplo.com se unió a la sala"}
{"type": "user_list", "users": ["alguien@ejemplo.com", "otro@ejemplo.com"]}
{"type": "typing", "user_email": "alguien@ejemplo.com"}
```

## Estructura del proyecto

```
app/
├── main.py                # endpoint WebSocket y lógica de la sala
├── config.py                # configuración (variables de entorno)
├── database.py               # conexión a Postgres (SQLAlchemy)
├── models.py                  # modelos: Room, Message
├── schemas.py                  # validación de salida (Pydantic)
├── security.py                  # SOLO decodificación de JWT (no genera tokens)
├── connection_manager.py         # conexiones activas, agrupadas por sala
├── crud.py                        # salas, guardado y recuperación de mensajes
└── static/                         # frontend (HTML, CSS, JS)
    ├── index.html                   # login + elegir sala
    ├── room.html                     # la sala de chat
    ├── style.css
    └── app.js
```

## Decisiones de diseño

- **El chat-service no genera tokens, solo los verifica**: toda la responsabilidad de autenticar usuarios (registro, login, hashing de contraseñas) vive exclusivamente en `auth-service`. Este servicio confía en la firma del JWT porque comparte la misma clave secreta, sin necesitar llamar al auth-service en cada conexión — así funciona la verificación de identidad en arquitecturas de microservicios reales.
- **El token viaja como query parameter, no como header**: la API nativa `WebSocket` del navegador no permite adjuntar headers personalizados al conectar, así que el token se pasa en la URL de conexión (`?token=...`).
- **Distinción de tipo de token también aquí**: igual que en el auth-service, se valida que el token sea de tipo `access` y no `refresh`, para que un token pensado para otro propósito no pueda usarse para abrir una conexión de chat.
- **Estado de conexiones en memoria, agrupado por sala**: `ConnectionManager` mantiene un diccionario de sala → conexiones activas. Es simple y rápido, pero solo funciona con una única instancia del servicio corriendo; escalar a varias instancias requeriría un mecanismo compartido (Redis pub/sub) para que un mensaje llegue a un usuario conectado a otra instancia distinta a la que lo recibió.
- **Mensajes con un campo `type` explícito**: todo lo que viaja por el WebSocket, en cualquier dirección, es JSON con un campo `type` (`message`, `system`, `typing`, `user_list`). Esto evita ambigüedad en el cliente sobre cómo interpretar cada mensaje entrante.
- **El indicador de "escribiendo" no se persiste ni pasa por la base de datos**: es información efímera por naturaleza, así que solo se retransmite en memoria, sin tocar Postgres.
- **`sessionStorage` en el frontend, no `localStorage`**: a diferencia del frontend del auth-service, aquí la sesión se limpia automáticamente al cerrar la pestaña, lo cual encaja mejor con la naturaleza de una sesión de chat.
- **Escapado de HTML en los mensajes mostrados**: el contenido de cada mensaje se inserta de forma segura en el DOM para evitar que un mensaje con código HTML/JavaScript se ejecute en el navegador de otros usuarios (XSS).

## Limitaciones conocidas

- El servicio asume una única instancia corriendo; con varias instancias, dos usuarios conectados a réplicas distintas del chat-service no se verían entre sí sin un mecanismo de broadcast compartido (Redis pub/sub sería el siguiente paso natural).
- El frontend no reconecta automáticamente el WebSocket si la conexión se corta (por ejemplo, al expirar el access token a mitad de una sesión larga); habría que refrescar la página o implementar reconexión con renovación de token.
- No hay límite en la cantidad de salas ni en la longitud del historial cargado más allá de los últimos 50 mensajes.

## Licencia

MIT