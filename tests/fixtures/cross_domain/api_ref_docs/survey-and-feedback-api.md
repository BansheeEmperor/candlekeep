---
title: Survey and Feedback API
description: API for managing customer surveys and feedback
keywords: [survey, feedback, customer, response, analytics]
category: api-reference
---

## GET /surveys
Retrieve a list of all customer surveys.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| page | integer | Page number for pagination | No |
| per_page | integer | Number of results per page | No |
| status | string | Filter by survey status (draft, active, closed) | No |

### Response
```json
{
  "data": [
    {
      "id": "survey_123",
      "title": "Customer Satisfaction Survey",
      "status": "active",
      "created_at": "2023-04-01T12:00:00Z",
      "updated_at": "2023-04-15T09:30:00Z"
    },
    {
      "id": "survey_456",
      "title": "Product Feedback Survey",
      "status": "closed",
      "created_at": "2023-03-15T08:45:00Z",
      "updated_at": "2023-04-10T14:20:00Z"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "per_page": 10
  }
}
```

## POST /surveys
Create a new customer survey.

### Request Body
```json
{
  "title": "New Customer Survey",
  "description": "Survey to gather feedback on our latest product release.",
  "status": "draft",
  "questions": [
    {
      "type": "rating",
      "text": "How would you rate your overall satisfaction with our product?"
    },
    {
      "type": "text",
      "text": "What did you like most about the product?"
    },
    {
      "type": "text",
      "text": "What improvements would you suggest?"
    }
  ]
}
```

### Response
```json
{
  "id": "survey_789",
  "title": "New Customer Survey",
  "description": "Survey to gather feedback on our latest product release.",
  "status": "draft",
  "questions": [
    {
      "type": "rating",
      "text": "How would you rate your overall satisfaction with our product?"
    },
    {
      "type": "text",
      "text": "What did you like most about the product?"
    },
    {
      "type": "text",
      "text": "What improvements would you suggest?"
    }
  ],
  "created_at": "2023-04-20T15:30:00Z",
  "updated_at": "2023-04-20T15:30:00Z"
}
```

## GET /surveys/{id}
Retrieve details of a specific customer survey.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the survey to retrieve | Yes |

### Response
```json
{
  "id": "survey_123",
  "title": "Customer Satisfaction Survey",
  "description": "Survey to gather feedback on our customer service.",
  "status": "active",
  "questions": [
    {
      "type": "rating",
      "text": "How would you rate your overall satisfaction with our customer service?"
    },
    {
      "type": "text",
      "text": "What did you like most about your customer service experience?"
    },
    {
      "type": "text",
      "text": "How can we improve our customer service?"
    }
  ],
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-15T09:30:00Z"
}
```

## POST /surveys/{id}/responses
Submit a response to a customer survey.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the survey to respond to | Yes |

### Request Body
```json
{
  "answers": [
    {
      "question_id": "question_1",
      "value": 4
    },
    {
      "question_id": "question_2",
      "value": "The customer service representatives were very helpful and friendly."
    },
    {
      "question_id": "question_3",
      "value": "I would like to see faster response times from the customer service team."
    }
  ]
}
```

### Response
```json
{
  "id": "response_456",
  "survey_id": "survey_123",
  "answers": [
    {
      "question_id": "question_1",
      "value": 4
    },
    {
      "question_id": "question_2",
      "value": "The customer service representatives were very helpful and friendly."
    },
    {
      "question_id": "question_3",
      "value": "I would like to see faster response times from the customer service team."
    }
  ],
  "created_at": "2023-04-20T16:45:00Z"
}
```

## GET /surveys/{id}/responses
Retrieve all responses for a specific customer survey.

### Parameters
| Name | Type | Description | Required |
| --- | --- | --- | --- |
| id | string | ID of the survey to retrieve responses for | Yes |
| page | integer | Page number for pagination | No |
| per_page | integer | Number of results per page | No |

### Response
```json
{
  "data": [
    {
      "id": "response_456",
      "survey_id": "survey_123",
      "answers": [
        {
          "question_id": "question_1",
          "value": 4
        },
        {
          "question_id": "question_2",
          "value": "The customer service representatives were very helpful and friendly."
        },
        {
          "question_id": "question_3",
          "value": "I would like to see faster response times from the customer service team."
        }
      ],
      "created_at": "2023-04-20T16:45:00Z"
    },
    {
      "id": "response_789",
      "survey_id": "survey_123",
      "answers": [
        {
          "question_id": "question_1",
          "value": 5
        },
        {
          "question_id": "question_2",
          "value": "I was very satisfied with the overall customer service experience."
        },
        {
          "question_id": "question_3",
          "value": "No improvements needed, the customer service was excellent."
        }
      ],
      "created_at": "2023-04-21T09:15:00Z"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "per_page": 10
  }
}
```

## Error Codes
| Code | Description |
| --- | --- |
| 400 | Bad Request - Invalid or missing parameters |
| 401 | Unauthorized - Invalid or missing authentication credentials |
| 404 | Not Found - The requested resource was not found |
| 500 | Internal Server Error - An unexpected error occurred on the server |