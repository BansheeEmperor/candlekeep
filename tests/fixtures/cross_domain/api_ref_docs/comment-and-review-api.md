---
title: Comment and Review API
description: API for creating, retrieving, updating, and deleting comments and reviews.
keywords: [comments, reviews, feedback, ratings, user-generated content]
category: api-reference
---

## Create Comment
`POST /api/v1/comments`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `post_id` | integer | Yes | ID of the post the comment is for |
| `author_name` | string | Yes | Name of the comment author |
| `author_email` | string | Yes | Email of the comment author |
| `content` | string | Yes | Text content of the comment |
| `parent_id` | integer | No | ID of the parent comment, if this is a reply |

### Request Body
```json
{
  "post_id": 123,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "content": "Great post, thanks for sharing!",
  "parent_id": null
}
```

### Response
```json
{
  "id": 456,
  "post_id": 123,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "content": "Great post, thanks for sharing!",
  "parent_id": null,
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `400 Bad Request`: Missing required parameters or invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User not authorized to perform this action

## Get Comment
`GET /api/v1/comments/{id}`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | integer | Yes | ID of the comment to retrieve |

### Response
```json
{
  "id": 456,
  "post_id": 123,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "content": "Great post, thanks for sharing!",
  "parent_id": null,
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:00Z"
}
```

### Error Codes
- `404 Not Found`: Comment not found

## Update Comment
`PUT /api/v1/comments/{id}`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | integer | Yes | ID of the comment to update |

### Request Body
```json
{
  "content": "Thanks for the feedback, glad you enjoyed the post!"
}
```

### Response
```json
{
  "id": 456,
  "post_id": 123,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "content": "Thanks for the feedback, glad you enjoyed the post!",
  "parent_id": null,
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-02T15:30:00Z"
}
```

### Error Codes
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User not authorized to perform this action
- `404 Not Found`: Comment not found

## Delete Comment
`DELETE /api/v1/comments/{id}`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | integer | Yes | ID of the comment to delete |

### Response
```json
{
  "message": "Comment deleted successfully"
}
```

### Error Codes
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User not authorized to perform this action
- `404 Not Found`: Comment not found

## Create Review
`POST /api/v1/reviews`

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `product_id` | integer | Yes | ID of the product the review is for |
| `author_name` | string | Yes | Name of the review author |
| `author_email` | string | Yes | Email of the review author |
| `rating` | integer | Yes | Rating value (1-5) |
| `title` | string | Yes | Title of the review |
| `content` | string | Yes | Text content of the review |

### Request Body
```json
{
  "product_id": 789,
  "author_name": "Jane Smith",
  "author_email": "jane@example.com",
  "rating": 4,
  "title": "Great product, highly recommended",
  "content": "I've been using this product for a few weeks and it's been fantastic. Highly recommended!"
}
```

### Response
```json
{
  "id": 321,
  "product_id": 789,
  "author_name": "Jane Smith",
  "author_email": "jane@example.com",
  "rating": 4,
  "title": "Great product, highly recommended",
  "content": "I've been using this product for a few weeks and it's been fantastic. Highly recommended!",
  "created_at": "2023-04-03T09:15:00Z",
  "updated_at": "2023-04-03T09:15:00Z"
}
```

### Error Codes
- `400 Bad Request`: Missing required parameters or invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: User not authorized to perform this action