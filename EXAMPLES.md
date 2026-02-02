# FFmpeg API - Examples

## Example 1: Video Rescaling

Convert a 4K video to 1080p:

```bash
# Register task
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 -vf scale=1920:1080 output.mp4",
    "input_files": {
      "input.mp4": "https://example.com/4k-video.mp4"
    },
    "output_filename": "output.mp4"
  }'

# Response: {"task_id": "550e8400-e29b-41d4-a716-446655440000", ...}

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/550e8400-e29b-41d4-a716-446655440000

# Check status
curl http://localhost:8000/ffmpeg/status/550e8400-e29b-41d4-a716-446655440000
```

---

## Example 2: Video to Audio Extraction

Extract audio from a video:

```bash
# Register task
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 -q:a 0 -map a output.mp3",
    "input_files": {
      "input.mp4": "https://example.com/video.mp4"
    },
    "output_filename": "output.mp3"
  }'

# Response: {"task_id": "abc123..."}

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/abc123...
```

---

## Example 3: Image Sequence to Video

Create a video from image sequence:

```bash
# Register task
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-framerate 30 -i input_%03d.jpg -c:v libx264 -pix_fmt yuv420p output.mp4",
    "input_files": {
      "input_001.jpg": "https://example.com/images/img_001.jpg",
      "input_002.jpg": "https://example.com/images/img_002.jpg",
      "input_003.jpg": "https://example.com/images/img_003.jpg"
    },
    "output_filename": "output.mp4"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Example 4: Concatenate Videos

Merge multiple videos:

Create a text file `concat.txt`:

```
file 'input1.mp4'
file 'input2.mp4'
file 'input3.mp4'
```

Then register task:

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-f concat -safe 0 -i concat.txt -c copy output.mp4",
    "input_files": {
      "input1.mp4": "https://example.com/video1.mp4",
      "input2.mp4": "https://example.com/video2.mp4",
      "input3.mp4": "https://example.com/video3.mp4",
      "concat.txt": "https://example.com/concat.txt"
    },
    "output_filename": "output.mp4"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Example 5: Add Watermark

Add an image watermark to a video:

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 -i watermark.png -filter_complex \"overlay=10:10\" -c:a aac output.mp4",
    "input_files": {
      "input.mp4": "https://example.com/video.mp4",
      "watermark.png": "https://example.com/watermark.png"
    },
    "output_filename": "output.mp4"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Example 6: Convert Image Format

Convert PNG to JPEG:

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.png -q:v 2 output.jpg",
    "input_files": {
      "input.png": "https://example.com/image.png"
    },
    "output_filename": "output.jpg"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Example 7: Extract Video Frames

Extract specific frames from a video:

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 -vf fps=1 frame_%03d.jpg",
    "input_files": {
      "input.mp4": "https://example.com/video.mp4"
    },
    "output_filename": "frame_001.jpg"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Example 8: Transcode to Different Codec

Convert video codec:

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mov -c:v libx265 -crf 28 -c:a aac -b:a 128k output.mp4",
    "input_files": {
      "input.mov": "https://example.com/video.mov"
    },
    "output_filename": "output.mp4"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Example 9: Add Subtitles

Burn subtitles into video:

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 -vf subtitles=subs.srt output.mp4",
    "input_files": {
      "input.mp4": "https://example.com/video.mp4",
      "subs.srt": "https://example.com/subtitles.srt"
    },
    "output_filename": "output.mp4"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Example 10: Trim Video

Trim a video from 10 seconds to 30 seconds:

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 -ss 10 -to 30 -c copy output.mp4",
    "input_files": {
      "input.mp4": "https://example.com/video.mp4"
    },
    "output_filename": "output.mp4"
  }'

# Execute task
curl -X POST http://localhost:8000/ffmpeg/execute/{task_id}
```

---

## Checking Results

After executing any task, check the status:

```bash
# Check status
curl http://localhost:8000/ffmpeg/status/{task_id}

# Response when completed:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "output_url": "s3://your-bucket/ffmpeg-outputs/550e8400-e29b-41d4-a716-446655440000/output.mp4",
  "error_message": null
}

# Response when failed:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "output_url": null,
  "error_message": "FFmpeg error: file not found"
}
```

---

## Notes

- FFmpeg commands should **NOT** include the `ffmpeg` prefix
- Input file paths in commands must match the keys in `input_files` dictionary
- Output filename must match the `output_filename` field
- All file downloads happen asynchronously
- Output files are uploaded to S3 with key format: `ffmpeg-outputs/{task_id}/{output_filename}`
- Returned S3 URLs use the `s3://` scheme by default
