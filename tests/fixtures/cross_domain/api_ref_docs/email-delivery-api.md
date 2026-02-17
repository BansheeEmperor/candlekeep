---
title: Email Delivery API
description: Programmatically send transactional and marketing emails.
keywords: [email, smtp, transactional, marketing, delivery, api]
category: api-reference
---

## Send Transactional Email
### POST /v1/emails/transactional

#### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| from | string | yes | Email address of the sender |
| to | string | yes | Email address of the recipient |
| subject | string | yes | Subject line of the email |
| text_body | string | no | Plain text content of the email |
| html_body | string | no | HTML content of the email |
| attachments | array | no | List of file attachments |

#### Request Body
```json
{
  "from": "sender@example.com",
  "to": "recipient@example.com",
  "subject": "Your order confirmation",
  "text_body": "Thank you for your order. Here are the details...",
  "html_body": "<p>Thank you for your order. Here are the details...</p>",
  "attachments": [
    {
      "filename": "invoice.pdf",
      "content": "JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwvTGVuZ3RoIDMgMCBSL0ZpbHRlci9GbGF0ZURlY29kZT4+CnN0cmVhbQp4nDWPQQrCMBBF94J9hxBc6q6gBUGQgrhQN72AlTRDmtSY3r6xoMU/7/Hm5QGALBQUETDNlSXRKlbIWZuZGKbAWjHYGVY/z7cM9mhcnLIxSdFpDuPr4bFbvQ5YtxjLOLw7BR/8Bz6Qh8rQZW5Hj4Lh2Wn0AvVuQ0EKZW5kc3RyZWFtCmVuZG9iago..."
    }
  ]
}
```

#### Response
```json
{
  "id": "abc123",
  "status": "queued"
}
```

#### Error Codes
| Code | Description |
| --- | --- |
| 400 | Missing required parameters |
| 401 | Invalid API key |
| 500 | Internal server error |

## Send Marketing Email
### POST /v1/emails/marketing

#### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| from | string | yes | Email address of the sender |
| to | string | yes | Email address of the recipient |
| subject | string | yes | Subject line of the email |
| text_body | string | no | Plain text content of the email |
| html_body | string | no | HTML content of the email |
| list_id | string | yes | ID of the mailing list to send to |

#### Request Body
```json
{
  "from": "newsletter@example.com",
  "to": "subscriber@example.com",
  "subject": "Monthly newsletter",
  "text_body": "Here is the latest news from our company...",
  "html_body": "<p>Here is the latest news from our company...</p>",
  "list_id": "abc123"
}
```

#### Response
```json
{
  "id": "def456",
  "status": "queued"
}
```

#### Error Codes
| Code | Description |
| --- | --- |
| 400 | Missing required parameters |
| 401 | Invalid API key |
| 403 | Forbidden to send to this mailing list |
| 500 | Internal server error |

## Get Email Delivery Status
### GET /v1/emails/{id}

#### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | yes | ID of the email to retrieve |

#### Response
```json
{
  "id": "abc123",
  "from": "sender@example.com",
  "to": "recipient@example.com",
  "subject": "Your order confirmation",
  "status": "delivered",
  "created_at": "2023-04-01T12:00:00Z",
  "updated_at": "2023-04-01T12:00:10Z"
}
```

#### Error Codes
| Code | Description |
| --- | --- |
| 404 | Email not found |
| 500 | Internal server error |

## List Mailing Lists
### GET /v1/lists

#### Response
```json
[
  {
    "id": "abc123",
    "name": "Newsletter Subscribers",
    "description": "Our monthly newsletter mailing list",
    "subscriber_count": 10000
  },
  {
    "id": "def456",
    "name": "Product Updates",
    "description": "Mailing list for product release announcements",
    "subscriber_count": 5000
  }
]
```

#### Error Codes
| Code | Description |
| --- | --- |
| 401 | Invalid API key |
| 500 | Internal server error |