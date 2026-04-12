# Trip Sharing Feature Implementation

## Overview
This implementation adds the ability to share trip information with other users via secure, time-limited shareable links (Option 1 from your requirements).

## Features

### 1. Share Token Generation
- Create unique, time-limited tokens for any trip
- Only trip participants (customer or driver) can create tokens
- Configurable expiration time (1-168 hours, default 24 hours)
- Automatically invalidates previous active tokens when creating new ones

### 2. Public Trip Viewing
- Anyone with the share link can view trip details without authentication
- Shows limited trip information: route, driver/customer info, car details, status
- Tracks access count for analytics
- Validates token expiration and active status

### 3. Security Features
- UUID-based tokens (unpredictable)
- Automatic expiration
- Manual deactivation capability
- Access tracking

## Database Model

### TripShareToken
```python
- trip: ForeignKey to Trip
- token: UUID (auto-generated, unique)
- expires_at: DateTime
- is_active: Boolean (default True)
- accessed_count: Integer (tracks how many times link was used)
- created_at: DateTime
```

## API Endpoints

### 1. Create Share Token
**POST** `/api/trips/<uuid:trip_id>/share-token/`

**Permissions:** Authenticated + Trip Participant or Admin

**Request Body (optional):**
```json
{
  "hours_valid": 48  // 1-168 hours, default 24
}
```

**Response:**
```json
{
  "id": 1,
  "trip_id": "550e8400-e29b-41d4-a716-446655440000",
  "token": "550e8400-e29b-41d4-a716-446655440001",
  "share_url": "http://localhost:8000/api/trips/share/550e8400-e29b-41d4-a716-446655440001/",
  "expires_at": "2024-01-02T12:00:00Z",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "accessed_count": 0
}
```

### 2. List Share Tokens
**GET** `/api/trips/<uuid:trip_id>/share-tokens/`

**Permissions:** Authenticated + Trip Participant or Admin

**Response:**
```json
[
  {
    "id": 1,
    "trip_id": "...",
    "token": "...",
    "share_url": "...",
    "expires_at": "...",
    "is_active": true,
    "created_at": "...",
    "accessed_count": 5
  }
]
```

### 3. Public Trip Details (No Auth Required)
**GET** `/api/trips/share/<uuid:token>/`

**Permissions:** AllowAny (public access)

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer": {
    "id": 1,
    "phone": "+1234567890",
    "first_name": "John",
    "last_name": "Doe",
    "roles": ["customer"]
  },
  "driver": {
    "id": 2,
    "phone": "+0987654321",
    "first_name": "Jane",
    "last_name": "Smith",
    "roles": ["driver"]
  },
  "car": {
    "id": 1,
    "brand": "Toyota",
    "car_type": "comfort",
    "plate_number": "ABC123",
    "year": 2022
  },
  "tariff": {
    "code": "comfort",
    "base_price": "100.00",
    "price_per_km": "10.00",
    "price_per_min": "2.00"
  },
  "start_lat": 40.7128,
  "start_lng": -74.0060,
  "end_lat": 40.7580,
  "end_lng": -73.9855,
  "distance_km": 5.2,
  "price": "152.00",
  "status": "on_route",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Error Responses:**
- `404 Not Found`: Invalid token
- `410 Gone`: Token expired or deactivated

## Usage Examples

### JavaScript/Frontend Example
```javascript
// Create share link
async function createShareLink(tripId, hoursValid = 24) {
  const response = await fetch(`/api/trips/${tripId}/share-token/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ hours_valid: hoursValid })
  });
  
  const data = await response.json();
  return data.share_url; // Share this URL
}

// Share via WhatsApp/SMS
function shareViaWhatsApp(shareUrl, phoneNumber) {
  const message = encodeURIComponent(
    `Track my taxi ride in real-time: ${shareUrl}`
  );
  window.open(`https://wa.me/${phoneNumber}?text=${message}`);
}

// Share via SMS (using Web Share API or backend service)
function shareViaSMS(shareUrl, phoneNumber) {
  // Use Twilio, Vonage, or similar service
  // Or use Web Share API on mobile
  if (navigator.share) {
    navigator.share({
      title: 'Track My Ride',
      text: `Track my taxi: ${shareUrl}`,
      url: shareUrl
    });
  }
}
```

### Mobile App Integration
```swift
// iOS Swift Example
func createAndShareTrip(tripId: String) {
    let parameters: [String: Any] = ["hours_valid": 24]
    
    API.post("/trips/\(tripId)/share-token/", parameters: parameters) { result in
        switch result {
        case .success(let shareToken):
            let shareUrl = shareToken["share_url"] as! String
            let activityVC = UIActivityViewController(
                activityItems: ["Track my ride: \(shareUrl)"],
                applicationActivities: nil
            )
            present(activityVC, animated: true)
        case .failure(let error):
            print("Error: \(error)")
        }
    }
}
```

## Frontend Display Page

Create a simple HTML page at `/track/<token>` that:
1. Fetches trip data from `/api/trips/share/<token>/`
2. Displays map with route (using Google Maps, Mapbox, etc.)
3. Shows driver/car information
4. Updates status in real-time (optional WebSocket integration)

Example HTML structure:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Track Ride</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <div id="map"></div>
    <div id="trip-info">
        <h2>Your Ride is <span id="status"></span></h2>
        <div id="driver-info"></div>
        <div id="car-info"></div>
        <div id="eta"></div>
    </div>
    
    <script>
        const token = window.location.pathname.split('/').pop();
        fetch(`/api/trips/share/${token}/`)
            .then(res => res.json())
            .then(data => {
                // Display trip information
                document.getElementById('status').textContent = data.status;
                // Initialize map with start/end coordinates
                // Show driver/car info
            });
    </script>
</body>
</html>
```

## Migration Required

Run these commands in your Docker container:
```bash
docker-compose exec web python manage.py makemigrations taxi
docker-compose exec web python manage.py migrate
```

## Admin Panel

The TripShareToken model is registered in Django Admin with:
- List view showing token, trip, expiration, access count
- Filter by active/expired status
- Search by token or trip ID
- Read-only token field (auto-generated)

## Security Considerations

1. **Token Unpredictability**: Uses UUID4 for unguessable tokens
2. **Expiration**: Default 24 hours, max 1 week
3. **Access Tracking**: Monitors usage patterns
4. **Manual Deactivation**: Admins can disable tokens
5. **Limited Information**: Public endpoint shows only necessary trip details

## Future Enhancements

- Real-time location updates via WebSocket for shared trips
- Email/SMS notifications when trip status changes
- QR code generation for share tokens
- Multiple active tokens per trip (instead of auto-invalidating)
- Custom messages with share links
- Analytics dashboard for share link usage
