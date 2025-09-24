# Posterizarr Webhook Integration Guide

This guide explains how to configure Sonarr and Radarr to automatically trigger Posterizarr when new files are downloaded.

## Overview

The Posterizarr chart now includes an optional webhook server that can receive HTTP POST requests from Sonarr and Radarr. When a download/import event occurs, the webhook server triggers the Posterizarr script to generate artwork for the newly added media.

## Configuration

### Enable the Webhook Server

The webhook server is enabled by default. To disable it, set:

```yaml
webhook:
  enabled: false
```

### Webhook URL

Once deployed, the webhook will be available at:
```
http://posterizarr.posterizarr:8080/
```

## Sonarr Configuration

1. **Navigate to Settings → Connect**
2. **Add a new connection** and select "Webhook"
3. **Configure the webhook:**
   - **Name**: `Posterizarr Trigger`
   - **URL**: `http://posterizarr.posterizarr:8080/`
   - **Method**: `POST`
   - **Username**: (leave empty)
   - **Password**: (leave empty)

4. **Select triggers:**
   - ✅ **On File Import** - Triggers when an episode is successfully imported
   - ❌ **On Upgrade** - (optional, may cause unnecessary triggers)

5. **Test the connection** and **Save**

## Radarr Configuration

1. **Navigate to Settings → Connect**
2. **Add a new connection** and select "Webhook"
3. **Configure the webhook:**
   - **Name**: `Posterizarr Trigger`
   - **URL**: `http://posterizarr.posterizarr:8080/`
   - **Method**: `POST`
   - **Username**: (leave empty)
   - **Password**: (leave empty)

4. **Select triggers:**
   - ✅ **On File Import** - Triggers when an episode is successfully imported
   - ❌ **On Upgrade** - (optional, may cause unnecessary triggers)

5. **Test the connection** and **Save**

## How It Works

1. **Media Download**: Sonarr/Radarr downloads new media
2. **Webhook Trigger**: Sonarr/Radarr sends a POST request to the Posterizarr webhook URL
3. **Event Processing**: The webhook server checks the event type
4. **Posterizarr Execution**: If it's a download/import event, Posterizarr is triggered
5. **Artwork Generation**: Posterizarr generates and uploads artwork to Plex

## Supported Events

The webhook server processes these event types:
- `Download` - File finished downloading
- `Import` - File successfully imported to library
- `MovieFileDownloaded` - Movie file downloaded (Radarr)
- `EpisodeFileDownloaded` - Episode file downloaded (Sonarr)

All other event types are ignored to prevent unnecessary Posterizarr runs.

## Troubleshooting

### Check Webhook Health
Visit the health endpoint: `https://posterizarr.apps.openshift.example.com/health`

Should return: `{"status": "healthy"}`

### Monitor Logs
Check the Posterizarr pod logs for webhook activity:
```bash
oc logs -f statefulset/posterizarr -c webhook -n posterizarr
```

### Test Webhook Manually
You can test the webhook with curl:
```bash
curl -X POST https://posterizarr.apps.openshift.example.com/ \
  -H "Content-Type: application/json" \
  -d '{"eventType":"Download","movie":{"title":"Test Movie"}}'
```

### Common Issues

1. **Connection Timeout**: Verify the webhook URL is accessible
2. **No Response**: Check that the webhook server container is running
3. **Posterizarr Not Triggered**: Check the webhook logs for event processing

## Security Considerations

- Only specific event types trigger Posterizarr execution
- The webhook server runs with minimal privileges and resources
