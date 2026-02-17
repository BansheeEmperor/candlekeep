---
title: Translation API
description: A RESTful API for translating text between languages
keywords: [translation, language, text, api, multilingual]
category: api-reference
---

## `POST /translate`
Translate text from one language to another.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `source_lang` | string | Yes | The source language code (e.g. "en", "es", "zh") |
| `target_lang` | string | Yes | The target language code (e.g. "en", "es", "zh") |
| `text` | string | Yes | The text to be translated |

### Request Body
```json
{
  "source_lang": "en",
  "target_lang": "es",
  "text": "Hello, how are you?"
}
```

### Response
```json
{
  "translated_text": "Hola, ¿cómo estás?"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 404 | Language not supported |
| 500 | Internal server error |

## `GET /languages`
Retrieve a list of supported languages.

### Response
```json
[
  {
    "code": "en",
    "name": "English"
  },
  {
    "code": "es",
    "name": "Spanish"
  },
  {
    "code": "zh",
    "name": "Chinese"
  },
  {
    "code": "fr",
    "name": "French"
  },
  {
    "code": "de",
    "name": "German"
  }
]
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 500 | Internal server error |

## `POST /batch_translate`
Translate multiple texts in a single request.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `source_lang` | string | Yes | The source language code (e.g. "en", "es", "zh") |
| `target_lang` | string | Yes | The target language code (e.g. "en", "es", "zh") |
| `texts` | array | Yes | An array of texts to be translated |

### Request Body
```json
{
  "source_lang": "en",
  "target_lang": "es",
  "texts": [
    "Hello, how are you?",
    "I am doing well, thank you.",
    "Have a great day!"
  ]
}
```

### Response
```json
{
  "translations": [
    "Hola, ¿cómo estás?",
    "Estoy bien, gracias.",
    "¡Que tengas un buen día!"
  ]
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Invalid request parameters |
| 404 | Language not supported |
| 500 | Internal server error |

## `GET /usage`
Retrieve your current API usage statistics.

### Response
```json
{
  "total_requests": 1234,
  "remaining_requests": 4766,
  "reset_time": "2023-04-01T00:00:00Z"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 401 | Unauthorized access |
| 500 | Internal server error |