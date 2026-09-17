# Google Home Hoso

## Endpoints of `./server.py`

### Abstract
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend web page |
| POST | `/api/speak` | Convert text to speech and play |
| POST | `/api/play` | Play audio from URL or Base64 data |
| GET | `/api/audio/<audio_id>` | Retrieve cached audio |
| GET | `/api/devices` | Discover Google Home devices |

### POST /api/speak
**Request:**
- Content-Type: `application/json`
- Body: `{ "text": string }`

**Response:**
- Success (200): `{ "status": "Success" }`
- Error (400): `{ "error": string }`

### POST /api/play
**Request:**
- Content-Type: `application/json`
- Body: `{ "url": string }` or `{ "base64": string }`

**Response:**
- Success (200): `{ "status": "Success" }`
- Error (400): `{ "error": string }`

### GET /api/audio/<audio_id>
**Parameters:**
- `audio_id` (string): Audio file ID

**Response:**
- Success (200): `audio/mpeg` (binary data)
- Not found (404): `{ "error": string }`

### GET /api/devices
**Response:**
- Success (200): `{ "devices": array }`
- Error (400): `{ "error": string }`

