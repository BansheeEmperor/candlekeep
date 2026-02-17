---
title: Snapshot API
description: A RESTful API for managing user snapshots
keywords:
  - snapshot
  - user
  - image
  - storage
  - backup
category: api-reference
---

## Get User Snapshots
`GET /users/{userId}/snapshots`

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| userId | string | The ID of the user | Yes |
| page | integer | The page number (default: 1) | No |
| perPage | integer | The number of results per page (default: 20) | No |

### Response
```json
{
  "data": [
    {
      "id": "1234567890",
      "userId": "abc123",
      "name": "My Snapshot",
      "createdAt": "2023-04-01T12:00:00Z",
      "updatedAt": "2023-04-01T12:00:00Z",
      "size": 1024000,
      "url": "https://example.com/snapshots/1234567890.jpg"
    },
    {
      "id": "0987654321",
      "userId": "abc123",
      "name": "Another Snapshot",
      "createdAt": "2023-03-15T09:30:00Z",
      "updatedAt": "2023-03-15T09:30:00Z",
      "size": 2048000,
      "url": "https://example.com/snapshots/0987654321.jpg"
    }
  ],
  "meta": {
    "page": 1,
    "perPage": 20,
    "totalCount": 2
  }
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | User not found |

## Create a Snapshot
`POST /users/{userId}/snapshots`

### Request Body
```json
{
  "name": "My New Snapshot",
  "file": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBwgHBgkIBwgKCgkLDRYPDQwMDRsUFRAWIB0iIiAdHx8kKDQsJCYxJx8fLT0tMTU3Ojo6Iys/RD84QzQ5OjcBCgoKDQwNGg8PGjclHyU3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3N//AABEIAIAAgAMBIgACEQEDEQH/xAAbAAACAwEBAQAAAAAAAAAAAAADBAIFBgEAB//EADYQAAIBAwMCBAQEBQUBAQAAAAECAwAEEQUSITETQVFhBiJxgRQyQpGhscHR8CNS4RYzYnLxFf/EABkBAAMBAQEAAAAAAAAAAAAAAAECAwAEBf/EACERAQEBAQEAAgMBAQEBAAAAAAABAhEDITESQVEEImET/9oADAMBAAIRAxEAPwD7jQKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA