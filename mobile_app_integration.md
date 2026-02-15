
# Mobile Field Investigator App Integration

## Overview
The MediFraudy system includes a backend API designed to support a mobile application (e.g., React Native) for field investigators. This allows investigators to access case details, upload evidence (photos/gps), and update status while on-site.

## API Endpoints for Mobile
The `InvestigationCase` API (`/api/cases`) provides the following capabilities:

### 1. Case Management
- **List Assigned Cases**: `GET /api/cases?status=assigned&assigned_investigator_id={user_id}`
- **View Details**: `GET /api/cases/{case_id}`
- **Update Status**: `PUT /api/cases/{case_id}/status`

### 2. Evidence Collection (Planned)
- **Upload GPS Logs**: Future endpoint to push to `evv_gps_logs` table.
- **Upload Photos**: Future endpoint to upload to S3 and link via `timeline_events`.

## Database Support
- **`investigation_cases` Table**: Tracks workflow status, priority, and assignment.
- **`evv_gps_logs` Table**: Designed to store high-frequency GPS pings from the mobile app for route verification.
- **`provider_screenings` Table**: Allows investigators to checklist site visit requirements (e.g., `site_visit_conducted` boolean).

## Authentication (Placeholder)
- The mobile app should authenticate via JWT tokens.
- Currently, the API uses a placeholder `user_id="system"`. In production, this would be the logged-in investigator's ID.

## Future React Native Features
1. **Push Notifications**: Use Redis + FCM/APNS to alert investigators of new high-priority cases.
2. **Offline Mode**: Cache case details locally (SQLite) and sync when online.
3. **Geo-Fencing**: Alert when an investigator enters a high-risk provider zone.
