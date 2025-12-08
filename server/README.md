# SmartAC Server API Documentation

Express server for managing SmartAC system telemetry, detections, and historical data.

## Configuration

### Command Line Arguments

- `--detections-timeout <seconds>` - Timeout in seconds to clear detections after inactivity (default: 10)

### Example

```bash
node server --detections-timeout 5
```

## API Endpoints

### POST /detections

Receive detection counts from vision system.

**Request:**
- Content-Type: `application/json`
- Body: `Record<domain_name, count>`

**Example:**
```json
{
  "a": 3,
  "b": 1,
  "c": 0
}
```

**Response:**
- Status: 200 OK

**Notes:**
- Resets the detections timeout
- Removes status entries for domains not in the detections payload

---

### POST /unit/:domain

Receive telemetry from AC unit and respond with fan power setting.

**Parameters:**
- `:domain` - Domain name (e.g., "a", "b", "c")

**Request:**
- Content-Type: `application/octet-stream`
- Body: 12 bytes binary (3 floats, little-endian)
  - Bytes 0-3: Temperature (°C)
  - Bytes 4-7: Humidity (%)
  - Bytes 8-11: Fan RPM

**Response:**
- Content-Type: `application/octet-stream`
- Body: 4 bytes binary (1 float, little-endian)
  - Bytes 0-3: Fan power (0.0-1.0)

**Notes:**
- Updates status map for the domain
- Logs telemetry data to `var/domain-{domain}.log`
- Fan power calculated based on population: `min(population, 2) / 2`

---

### GET /status

Get current status of all domains.

**Response:**
- Content-Type: `application/json`
- Body: `Record<domain_name, Status>`

**Status Object:**
```typescript
{
  population: number,
  fan_power: number,
  temperature: number,
  humidity: number,
  fan_rpm: number
}
```

**Example:**
```json
{
  "a": {
    "population": 3,
    "fan_power": 1.0,
    "temperature": 23.5,
    "humidity": 45.2,
    "fan_rpm": 1250.5
  },
  "b": {
    "population": 1,
    "fan_power": 0.5,
    "temperature": 22.8,
    "humidity": 43.1,
    "fan_rpm": 850.3
  }
}
```

---

### GET /history/:domain

Get historical telemetry data for a domain with optional filtering and sampling.

**Parameters:**
- `:domain` - Domain name (e.g., "a", "b", "c")

**Query Parameters:**
- `start` (optional) - Start timestamp in seconds (Unix epoch)
- `end` (optional) - End timestamp in seconds (default: now)
- `step` (optional) - Minimum interval in seconds between data points (default: 60)

**Response:**
- Content-Type: `text/plain`
- Body: Newline-separated log entries

**Log Entry Format:**
```
<timestamp_ms>,{"temperature":<float>,"humidity":<float>,"fan_rpm":<float>,"population":<number>}
```

**Example:**
```
1733571000000,{"temperature":23.5,"humidity":45.2,"fan_rpm":1250.5,"population":3}
1733571060000,{"temperature":23.6,"humidity":45.3,"fan_rpm":1251.2,"population":3}
1733571120000,{"temperature":23.7,"humidity":45.1,"fan_rpm":1249.8,"population":2}
```

**Notes:**
- Returns empty response if domain has no log file
- Always includes first and last matching entries within the time range
- Filters entries to maintain at least `step` seconds between consecutive data points
- Timestamps are in milliseconds since Unix epoch

**Example Requests:**
- `GET /history/a` - Recent data with 60s intervals
- `GET /history/a?start=1733570000&end=1733580000` - Specific time range
- `GET /history/a?step=300` - 5-minute intervals

---

## Data Storage

### Log Files

Historical data is stored in `var/domain-{domain}.log` files with the following format:

```
<timestamp_ms>,<json_object>
```

Each line represents one telemetry reading with:
- `timestamp_ms`: Unix timestamp in milliseconds
- `json_object`: JSON object with `temperature`, `humidity`, `fan_rpm`, `population`

### In-Memory State

- `domains: Record<string, number>` - Current population count per domain
- `status: Map<string, Status>` - Latest telemetry status per domain

### Timeout Behavior

When no detections are received for `detections-timeout` seconds:
- `domains` is cleared
- `status` map is cleared
- Console logs "Detections cleared due to timeout"

## Static Files

The server serves static files from the `static/` directory for any unmatched routes.
