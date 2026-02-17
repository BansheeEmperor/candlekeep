---
title: Video Transcoding API
description: API for transcoding video files to different formats and resolutions.
keywords: [video, transcoding, format, resolution, encoding]
category: api-reference
---

## `POST /transcode`
Transcode a video file to a new format and resolution.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `input_file` | `string` | Yes | URL or path to the input video file. |
| `output_format` | `string` | Yes | Output video format (e.g., "mp4", "avi", "mov"). |
| `output_resolution` | `string` | Yes | Output video resolution (e.g., "1920x1080", "1280x720", "640x360"). |
| `bitrate` | `integer` | No | Target video bitrate in kbps (default: 5000). |
| `framerate` | `number` | No | Target video framerate in fps (default: 30). |

### Request Body
```json
{
  "input_file": "https://example.com/video.mp4",
  "output_format": "mp4",
  "output_resolution": "1920x1080",
  "bitrate": 8000,
  "framerate": 24
}
```

### Response
```json
{
  "job_id": "12345",
  "input_file": "https://example.com/video.mp4",
  "output_file": "https://example.com/video_transcoded.mp4",
  "output_format": "mp4",
  "output_resolution": "1920x1080",
  "bitrate": 8000,
  "framerate": 24,
  "status": "queued"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 400 | Bad Request (e.g., missing required parameters) |
| 404 | Input file not found |
| 500 | Internal Server Error |

## `GET /transcode/{job_id}`
Check the status of a transcoding job.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `job_id` | `string` | Yes | The ID of the transcoding job. |

### Response
```json
{
  "job_id": "12345",
  "input_file": "https://example.com/video.mp4",
  "output_file": "https://example.com/video_transcoded.mp4",
  "output_format": "mp4",
  "output_resolution": "1920x1080",
  "bitrate": 8000,
  "framerate": 24,
  "status": "completed",
  "progress": 100
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Job not found |
| 500 | Internal Server Error |

## `DELETE /transcode/{job_id}`
Cancel a pending transcoding job.

### Parameters
| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `job_id` | `string` | Yes | The ID of the transcoding job to cancel. |

### Response
```json
{
  "job_id": "12345",
  "status": "canceled"
}
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 404 | Job not found |
| 500 | Internal Server Error |

## `GET /formats`
List the available output formats supported by the API.

### Response
```json
[
  "mp4",
  "avi",
  "mov",
  "webm",
  "mkv"
]
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 500 | Internal Server Error |

## `GET /resolutions`
List the available output resolutions supported by the API.

### Response
```json
[
  "1920x1080",
  "1280x720",
  "640x360",
  "3840x2160",
  "1024x576"
]
```

### Error Codes
| Status Code | Description |
| --- | --- |
| 500 | Internal Server Error |