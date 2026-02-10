"""
Telemedicine utilities - Twilio Video integration.

Per EMR Rules:
- All sessions must be visit-scoped
- Access tokens must be secure
- Audit logging mandatory
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Optional Twilio imports
try:
    from twilio.jwt.access_token import AccessToken
    from twilio.jwt.access_token.grants import VideoGrant
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio package not installed. Telemedicine features will be limited.")


def generate_twilio_access_token(user, room_name=None, room_sid=None):
    """
    Generate Twilio Access Token for video room access.
    
    Args:
        user: User object requesting access
        room_name: Twilio Room name (optional, prefer room_sid)
        room_sid: Twilio Room SID (optional, preferred over room_name)
    
    Returns:
        str: JWT access token
    """
    if not TWILIO_AVAILABLE:
        raise ImportError("twilio package not installed. Install with: pip install twilio")
    
    try:
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        api_key = getattr(settings, 'TWILIO_API_KEY', None)
        api_secret = getattr(settings, 'TWILIO_API_SECRET', None)
        
        if not all([account_sid, api_key, api_secret]):
            raise ValueError("Twilio credentials not configured")
        
        # Prefer room_name over room_sid for consistency with frontend
        # Frontend connects using room name, so token should use room name too
        room_identifier = room_name or room_sid
        if not room_identifier:
            raise ValueError("Either room_name or room_sid must be provided")
        
        # Log token generation info for debugging
        identifier_type = 'name' if room_name else 'SID'
        logger.info(f"Generating token for room: {room_identifier} (type: {identifier_type}), user: {user.id}")
        logger.info(f"Using Account SID: {account_sid[:8]}...{account_sid[-4:] if account_sid else 'None'}, API Key: {api_key[:8]}...{api_key[-4:] if api_key else 'None'}")
        
        # Create access token
        token = AccessToken(account_sid, api_key, api_secret, identity=str(user.id))
        
        # Grant video access
        # For Group rooms, we can use either room name or room SID
        # Using room name to match what frontend uses when connecting
        video_grant = VideoGrant(room=room_identifier)
        token.add_grant(video_grant)
        
        jwt_token = token.to_jwt()
        logger.info(f"Token generated successfully (length: {len(jwt_token)})")
        
        return jwt_token
        
    except Exception as e:
        logger.error(f"Failed to generate Twilio access token: {e}")
        raise


def create_twilio_room(room_name, max_participants=2, record_participants_on_connect=None):
    """
    Create a Twilio Video Room.
    
    Args:
        room_name: Name for the room
        max_participants: Maximum number of participants (default: 2)
        record_participants_on_connect: If True, Twilio will record the room when participants join.
            If None, falls back to settings.TWILIO_RECORDING_ENABLED.
    
    Returns:
        dict: Room information including room_sid
    """
    if not TWILIO_AVAILABLE:
        raise ImportError("twilio package not installed. Install with: pip install twilio")
    
    try:
        from twilio.rest import Client
        
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        
        if not all([account_sid, auth_token]):
            raise ValueError("Twilio credentials not configured")
        
        if record_participants_on_connect is None:
            record_participants_on_connect = getattr(settings, 'TWILIO_RECORDING_ENABLED', False)
        
        # Log credential info for debugging (masked)
        logger.info(f"Creating Twilio room with Account SID: {account_sid[:8]}...{account_sid[-4:] if account_sid else 'None'}, recording={record_participants_on_connect}")
        
        client = Client(account_sid, auth_token)
        
        # Create room
        # Note: 'go' room type is deprecated. Use 'group' for new accounts (post Oct 2024)
        room = client.video.rooms.create(
            unique_name=room_name,
            max_participants=max_participants,
            type='group',  # Group room type (supports up to 50 participants)
            record_participants_on_connect=record_participants_on_connect,
        )
        
        # Log room creation details
        logger.info(f"Room created - SID: {room.sid}, Unique Name: {room.unique_name}, Status: {room.status}")
        
        # Use unique_name if available, otherwise fall back to room_name
        # For Group rooms, unique_name should match what we passed
        final_room_name = room.unique_name if room.unique_name else room_name
        
        return {
            'room_sid': room.sid,
            'room_name': final_room_name,
            'status': room.status,
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to create Twilio room: {error_msg}")
        logger.error(f"Account SID configured: {bool(account_sid)}, Auth Token configured: {bool(auth_token)}")
        # Re-raise with a more user-friendly message
        if 'Authentication Error' in error_msg or 'invalid username' in error_msg:
            raise ValueError(f"Twilio authentication failed. Please verify your Account SID and Auth Token in the .env file. Error: {error_msg}")
        raise


def end_twilio_room(room_sid):
    """
    End a Twilio Video Room.
    
    Args:
        room_sid: Twilio Room SID
    
    Returns:
        dict: Updated room information
    
    Note: If room doesn't exist (already deleted/expired), returns None gracefully.
    """
    if not TWILIO_AVAILABLE:
        raise ImportError("twilio package not installed. Install with: pip install twilio")
    
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException
        
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        
        if not all([account_sid, auth_token]):
            raise ValueError("Twilio credentials not configured")
        
        client = Client(account_sid, auth_token)
        
        try:
            # Update room to completed
            room = client.video.rooms(room_sid).update(status='completed')
            
            return {
                'room_sid': room.sid,
                'status': room.status,
            }
        except TwilioRestException as e:
            # Room not found (20404) - room may have been auto-deleted or expired
            if e.code == 20404:
                logger.warning(f"Room {room_sid} not found - may have been auto-deleted or expired")
                # Return None to indicate room was already gone
                return None
            else:
                # Re-raise other Twilio errors
                raise
        
    except Exception as e:
        logger.error(f"Failed to end Twilio room: {e}")
        raise


def get_room_recordings(room_sid):
    """
    Get recordings for a Twilio Video Room.
    Uses the Rooms API (room.recordings) for reliable listing.
    Only returns recordings with status 'completed' (media available).
    
    Args:
        room_sid: Twilio Room SID
    
    Returns:
        list: List of recording info with sid, status, media_url (for playback), duration
    """
    if not TWILIO_AVAILABLE:
        raise ImportError("twilio package not installed. Install with: pip install twilio")
    
    try:
        from twilio.rest import Client
        
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        
        if not all([account_sid, auth_token]):
            raise ValueError("Twilio credentials not configured")
        
        client = Client(account_sid, auth_token)
        
        # Prefer Rooms API: room.recordings.list() (per Twilio docs)
        try:
            recordings = client.video.rooms(room_sid).recordings.list()
        except Exception:
            # Fallback: list recordings with grouping_sid filter (API expects array)
            recordings = client.video.recordings.list(
                grouping_key_sid=[room_sid]
            )
        
        result = []
        for rec in recordings:
            # Only include completed recordings (media is available)
            if getattr(rec, 'status', None) != 'completed':
                continue
            # rec.url is the API resource URL; playback uses the Media subresource
            media_url = None
            if getattr(rec, 'links', None) and isinstance(rec.links, dict):
                media_url = rec.links.get('media')
            result.append({
                'sid': rec.sid,
                'status': getattr(rec, 'status', None),
                'url': getattr(rec, 'url', None),
                'media_url': media_url,
                'duration': getattr(rec, 'duration', None),
                'date_created': rec.date_created.isoformat() if getattr(rec, 'date_created', None) else None,
            })
        return result
        
    except Exception as e:
        logger.error(f"Failed to get room recordings: {e}")
        raise
