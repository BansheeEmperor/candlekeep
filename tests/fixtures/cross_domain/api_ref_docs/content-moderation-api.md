---
title: Content Moderation API
description: Moderate user-generated content for inappropriate or harmful material.
keywords: [content moderation, content filtering, user-generated content, abuse detection, harmful content]
category: api-reference
---

## `POST /v1/moderate`
Analyze a piece of text or image content and return a moderation decision.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `content` | `string` | The text or base64-encoded image content to moderate. | Yes |
| `content_type` | `string` | The type of content, either `"text"` or `"image"`. | Yes |

### Request Body
```json
{
  "content": "This is an example of some user-generated text content.",
  "content_type": "text"
}
```

### Response
```json
{
  "is_flagged": false,
  "moderation_score": 0.15,
  "flagged_reasons": []
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad request - invalid parameters or content type. |
| 500 | Internal server error - an unexpected error occurred during moderation. |

## `GET /v1/stats`
Retrieve moderation statistics for the past 30 days.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `start_date` | `string` | The start date for the statistics (YYYY-MM-DD format). | No |
| `end_date` | `string` | The end date for the statistics (YYYY-MM-DD format). | No |

### Response
```json
{
  "total_moderated": 1234567,
  "total_flagged": 12345,
  "flagged_rate": 0.01,
  "top_flagged_reasons": [
    {
      "reason": "violence",
      "count": 5678
    },
    {
      "reason": "profanity",
      "count": 3456
    },
    {
      "reason": "hate_speech",
      "count": 2345
    }
  ]
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad request - invalid date parameters. |
| 500 | Internal server error - an unexpected error occurred retrieving the statistics. |

## `POST /v1/batch_moderate`
Analyze a batch of text or image content and return moderation decisions.

### Parameters
None

### Request Body
```json
[
  {
    "content": "This is another example of user-generated text content.",
    "content_type": "text"
  },
  {
    "content": "aGVsbG8gd29ybGQh",
    "content_type": "image"
  }
]
```

### Response
```json
[
  {
    "is_flagged": false,
    "moderation_score": 0.12,
    "flagged_reasons": []
  },
  {
    "is_flagged": true,
    "moderation_score": 0.87,
    "flagged_reasons": [
      "profanity",
      "hate_speech"
    ]
  }
]
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad request - invalid batch content or types. |
| 500 | Internal server error - an unexpected error occurred during batch moderation. |

## `GET /v1/history`
Retrieve the moderation history for a specific content item.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| `content_id` | `string` | The unique identifier of the content item. | Yes |

### Response
```json
{
  "content_id": "abc123",
  "moderation_history": [
    {
      "timestamp": "2023-04-01T12:34:56Z",
      "is_flagged": true,
      "moderation_score": 0.85,
      "flagged_reasons": [
        "violence",
        "hate_speech"
      ]
    },
    {
      "timestamp": "2023-04-02T09:12:34Z",
      "is_flagged": false,
      "moderation_score": 0.25,
      "flagged_reasons": []
    }
  ]
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Not found - the specified content item was not found. |
| 500 | Internal server error - an unexpected error occurred retrieving the moderation history. |