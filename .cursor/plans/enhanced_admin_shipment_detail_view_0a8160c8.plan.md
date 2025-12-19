---
name: Enhanced Admin Shipment Detail View
overview: Create an enhanced admin-specific shipment detail view with a map showing pickup/dropoff locations, complete message history, and admin notes functionality. The view will be accessible from the admin shipments management page.
todos:
  - id: create_loadnote_model
    content: Create LoadNote model in models/load_note.py with load_id, admin_id, content, and timestamps
    status: pending
  - id: register_loadnote
    content: Ensure LoadNote model is imported and registered with SQLAlchemy
    status: pending
    dependencies:
      - create_loadnote_model
  - id: create_admin_detail_route
    content: Add GET /admin/shipments/<int:load_id> route in routes/admin.py to display admin detail view
    status: pending
    dependencies:
      - register_loadnote
  - id: create_note_routes
    content: Add POST /admin/shipments/<int:load_id>/notes route for adding notes and optional DELETE route
    status: pending
    dependencies:
      - register_loadnote
  - id: update_message_api
    content: Modify GET /api/messages/<int:load_id> to allow admins to access all messages regardless of status
    status: pending
  - id: create_admin_detail_template
    content: Create templates/admin/shipment_detail.html with map, message history, and notes sections
    status: pending
    dependencies:
      - create_admin_detail_route
  - id: update_shipments_link
    content: Update templates/admin/shipments.html to link to admin.shipment_detail instead of loads.detail
    status: pending
    dependencies:
      - create_admin_detail_route
  - id: test_admin_detail_view
    content: Test that admin can access detail view, see map, messages, and add notes
    status: pending
    dependencies:
      - create_admin_detail_template
      - create_note_routes
      - update_message_api
---

# Enhanced Admin Shipment Detail View

## Overview

Create an admin-specific shipment detail page that displays a map with pickup/dropoff locations, complete message history, and allows admins to add notes and additional information. This will be separate from the existing user-facing detail views.

## Changes Required

### 1. Create LoadNote Model

**File**: `models/load_note.py` (new file)Create a new model to store admin notes for shipments:

- `id`: Primary key
- `load_id`: Foreign key to Load
- `admin_id`: Foreign key to User (admin who created the note)
- `content`: Text content of the note
- `created_at`: Timestamp
- `updated_at`: Timestamp
- Relationship to Load and User

### 2. Create Admin Detail Route

**File**: `routes/admin.py`Add new route:

- `GET /admin/shipments/<int:load_id>` - Admin-specific detail view
- `POST /admin/shipments/<int:load_id>/notes` - Add admin note
- `DELETE /admin/shipments/<int:load_id>/notes/<int:note_id>` - Delete admin note (optional)

Route should:

- Fetch load with all relationships
- Fetch all messages (no status restrictions for admins)
- Fetch all admin notes for the load
- Render admin detail template

### 3. Update Admin Shipments Template Link

**File**: `templates/admin/shipments.html`Change the reference number link from `loads.detail` to `admin.shipment_detail`:

```html
<a href="{{ url_for('admin.shipment_detail', load_id=load.id) }}">
```



### 4. Create Admin Detail Template

**File**: `templates/admin/shipment_detail.html` (new file)Create comprehensive admin detail view with:

- **Header Section**: Reference number, status badge, key metrics
- **Map Section**: Small embedded Leaflet.js map showing:
- Pickup location marker (blue)
- Dropoff location marker (red)
- Route line between them
- Current driver location (if available, green marker)
- **Message History Section**: 
- Display all messages chronologically
- Show sender name, timestamp, content
- Display photos if any
- System messages clearly marked
- **Admin Notes Section**:
- List of existing notes (admin name, timestamp, content)
- Form to add new note
- Edit/delete functionality (optional)
- **Shipment Details Section**: All load information in organized cards

### 5. Update Message API for Admins

**File**: `routes/api.py`Modify `GET /api/messages/<int:load_id>` to:

- Allow admins to access messages for any load regardless of status
- Remove status restrictions for admin users
- Return all messages (not just last 50, or increase limit)

### 6. Register LoadNote Model

**File**: `models/__init__.py` or ensure it's importedEnsure LoadNote model is imported so SQLAlchemy registers it.

## Implementation Details

### LoadNote Model Structure

```python
class LoadNote(db.Model):
    __tablename__ = 'load_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    load_id = db.Column(db.Integer, db.ForeignKey('loads.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    load = db.relationship('Load', backref='admin_notes')
    admin = db.relationship('User', backref='load_notes')
```



### Map Implementation

- Use Leaflet.js (already used in map_view.html)
- Center map to show both pickup and dropoff
- Add markers with popups showing address details
- Draw route line between points
- Show current driver location if available and in transit

### Message History Display

- Chronological list (oldest first or newest first with scroll)
- Group by date if many messages
- Show sender avatar/initials
- Display timestamps in readable format
- Handle system messages with distinct styling

### Admin Notes UI

- Form with textarea for new notes
- Submit button
- List of existing notes below form
- Each note shows: admin name, timestamp, content
- Optional: Edit/delete buttons for note creator

## Files to Create/Modify

1. **`models/load_note.py`** (new) - LoadNote model
2. **`routes/admin.py`** - Add shipment_detail route and note management routes
3. **`routes/api.py`** - Update message endpoint for admin access
4. **`templates/admin/shipment_detail.html`** (new) - Admin detail template
5. **`templates/admin/shipments.html`** - Update link to use admin detail route
6. **`models/__init__.py`** - Ensure LoadNote is imported

## Testing Considerations

- Verify admin can access detail view for any shipment
- Verify map displays correctly with pickup/dropoff locations
- Verify all messages are visible regardless of shipment status