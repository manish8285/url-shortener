# URL Shortener Service

A scalable URL shortener service built with Flask, PostgreSQL, and Redis.

## Features

- URL shortening with custom slug support
- URL expiration
- Access tracking and statistics
- Rate limiting
- Distributed caching with Redis
- Concurrent access support
- RESTful API

## Architecture

The service uses:
- **Flask**: For the web framework
- **PostgreSQL**: Primary data storage
- **Redis**: For caching and rate limiting
- **SQLAlchemy**: ORM for database operations

### Design Decisions

1. **URL Generation**: Uses a base64-encoded SHA-256 hash of the URL + timestamp + attempt number, taking the first 6 characters. This provides:
   - Uniform distribution of URLs
   - Low collision probability
   - Fixed-length output

2. **Caching Strategy**: 
   - Redis caches URL mappings
   - Cache entries expire with URLs
   - Write-through caching for consistency

3. **Scalability Features**:
   - Stateless design
   - Distributed caching
   - Database indexing
   - Rate limiting

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd url-shortener
```

2. Create a `.env` file:
```
DATABASE_URL=postgresql://user:password@localhost/urlshortener
REDIS_HOST=localhost
REDIS_PORT=6379
BASE_URL=http://localhost:8000
```

3. (A). Install and run this application (without docker):
```bash
python3 venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
flask --app server.py run --port 8000
```

3. Start services with Docker Compose:
```bash
docker-compose up -d
```

## API Documentation

### Shorten URL
```
POST /url/shorten

Request:
{
    "url": "https://www.example.com",
    "custom_slug": "my-url",  // optional
    "expiration_days": 7      // optional
}

Response:
{
    "short_url": "http://localhost:8000/r/abc123"
}
```

### Redirect to Original URL
```
GET /r/{short_url}

Response:
302 Redirect to original URL
```

### Get URL Statistics
```
GET /stats/{short_url}

Response:
{
    "short_url": "abc123",
    "original_url": "https://www.example.com",
    "created_at": "2024-10-26T10:00:00Z",
    "expires_at": "2024-11-02T10:00:00Z",
    "access_count": 42
}
```

## Testing

Run tests with:
```bash
pytest
```

## Performance Considerations

1. **Database Indexing**:
   - Indexed short_url for fast lookups
   - Indexed original_url for duplicate checking

2. **Caching**:
   - Frequently accessed URLs cached in Redis
   - Cache invalidation on expiration

3. **Rate Limiting**:
   - Prevents abuse
   - Configurable limits

## Future Improvements

1. Analytics dashboard
2. URL validation improvements
3. User authentication
4. Batch URL shortening
5. Custom domain support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License
