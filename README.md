## FEATURES
- Chunked upload and reassemble
- Partial Streaming
- Hotlinking protection

## RUN
uvicorn app.main:app --reload --host 0.0.0.0

## FIXING ERRORS:
- netstat -ano | findstr :8000

- taskkill /PID <PID> /F

## TODO:
- Add a Button to Cancel/Stop upload midway which does cleanup as well
- The URL of the uploaded file page should not need a token, only the partial streaming requests should need token
- Button to copy the link of the video page
- Add fields to input the description, title and tags to the content
- Add feature to solve captcha before downloading a non-video file
- Auth (google, email)
- Add a page to show list of videos (including self)
- Add a page to show the profile of logged in user along with their uploaded videos
- Add a Feature to delete uploaded content which does cleanup as well
