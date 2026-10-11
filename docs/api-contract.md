# API Contract

Base URL: `http://localhost:8000`

## Health

### `GET /api/health`
Returns service status.

**Response 200**
```json
{ "status": "ok", "version": "0.1.0" }
```

---

## Chat

### `POST /api/chat`
Streams an AI response as Server-Sent Events.

**Request Body**
```json
{
  "message": "string",
  "conversation_id": "string | null"
}
```

**Response** `text/event-stream`
```
data: {"chunk": "Hello"}
data: {"chunk": " world"}
data: [DONE]
```

**Error** `500`
```json
{ "detail": "AI service unavailable" }
```

---

## Items

### `GET /api/items`
List all items.

**Response 200**
```json
[{ "id": 1, "title": "string", "description": "string", "created_at": "ISO8601" }]
```

### `POST /api/items`
Create an item.

**Request Body**
```json
{ "title": "string", "description": "string" }
```

**Response 201**
```json
{ "id": 1, "title": "string", "description": "string", "created_at": "ISO8601" }
```

### `GET /api/items/{id}`
Get single item.

### `PUT /api/items/{id}`
Update item.

### `DELETE /api/items/{id}`
Delete item. Returns `204 No Content`.
