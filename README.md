# Reservo MCP Server

An MCP (Model Context Protocol) server for checking reservation availability.

## Features

- **Single Date Check**: Check if a specific date is available for booking
- **Date Range Check**: Check availability for a date range with detailed conflict information
- **Detailed Responses**: Provides reservation details and available periods when conflicts exist

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure the server by editing `config.json`:
```json
{
  "backend_url": "http://localhost:3001",
  "default_entity_id": "1",
  "timeout_seconds": 30
}
```

## Usage

Run the MCP server:
```bash
python server.py
```

## Available Tools

### check_date_availability
Check if a specific date is available for booking.

**Parameters:**
- `entity_id` (string): ID of the entity to check
- `date` (string): Date to check in YYYY-MM-DD format

**Example:**
```
check_date_availability(entity_id="1", date="2024-01-15")
```

### check_date_range_availability
Check availability for a date range with detailed conflict information.

**Parameters:**
- `entity_id` (string): ID of the entity to check
- `start_date` (string): Start date in YYYY-MM-DD format
- `end_date` (string): End date in YYYY-MM-DD format

**Example:**
```
check_date_range_availability(entity_id="1", start_date="2024-01-15", end_date="2024-01-20")
```

## Response Format

### Available Date
```json
{
  "available": true,
  "date": "2024-01-15",
  "entity_id": "1",
  "message": "Entity 1 is available on 2024-01-15"
}
```

### Occupied Date
```json
{
  "available": false,
  "date": "2024-01-15",
  "entity_id": "1",
  "reservation": {
    "id": "uuid-123",
    "booked_by": "John Doe",
    "start_date": "2024-01-14",
    "end_date": "2024-01-16",
    "created_at": "2024-01-01T10:00:00Z"
  }
}
```

### Date Range with Conflicts
```json
{
  "available": false,
  "entity_id": "1",
  "requested_period": {
    "start_date": "2024-01-15",
    "end_date": "2024-01-20"
  },
  "conflicts": [
    {
      "id": "uuid-123",
      "booked_by": "John Doe",
      "start_date": "2024-01-16",
      "end_date": "2024-01-18"
    }
  ],
  "available_periods": [
    {
      "start_date": "2024-01-15",
      "end_date": "2024-01-16"
    },
    {
      "start_date": "2024-01-18",
      "end_date": "2024-01-20"
    }
  ]
}
```
