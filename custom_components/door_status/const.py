"""Constants for the Door Status component."""
from datetime import timedelta
from typing import Final

DOMAIN: Final = "door_status"
EVENT_DOOR_STATUS_UPDATED: Final = "door_status_updated"

# Default values
DEFAULT_MIN_COLOR: Final = (0, 0, 0)  # Black
DEFAULT_MAX_COLOR: Final = (255, 255, 255)  # White
DEFAULT_IDLE_INTERVAL: Final = 10  # seconds
DEFAULT_ACTIVE_INTERVAL: Final = 1  # seconds
DEFAULT_CHANGE_THRESHOLD: Final = 10  # percent
DEFAULT_CLOSED_POSITION: Final = 90  # percent
DEFAULT_OPEN_POSITION: Final = 10  # percent
DEFAULT_TRANSITION_THRESHOLD: Final = 5  # percent
DEFAULT_STATE_TIMEOUT: Final = 5  # seconds

# Configuration keys
CONF_CAMERA_ENTITY: Final = "camera_entity"
CONF_POINT_A: Final = "point_a"
CONF_POINT_B: Final = "point_b"
CONF_MIN_COLOR: Final = "min_color"
CONF_MAX_COLOR: Final = "max_color"
CONF_IDLE_INTERVAL: Final = "idle_interval"
CONF_ACTIVE_INTERVAL: Final = "active_interval"
CONF_CHANGE_THRESHOLD: Final = "change_threshold"
CONF_CLOSED_POSITION: Final = "closed_position"
CONF_OPEN_POSITION: Final = "open_position"
CONF_TRANSITION_THRESHOLD: Final = "transition_threshold"
CONF_STATE_TIMEOUT: Final = "state_timeout"

# State options
STATE_OPEN: Final = "open"
STATE_CLOSED: Final = "closed"
STATE_OPENING: Final = "opening"
STATE_CLOSING: Final = "closing"
STATE_PARTIALLY_OPEN: Final = "partially_open"
STATE_UNKNOWN: Final = "unknown"

# Next action options
NEXT_ACTION_OPEN: Final = "open"
NEXT_ACTION_CLOSE: Final = "close"
NEXT_ACTION_UNKNOWN: Final = "unknown"