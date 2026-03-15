"""
Club-specific configuration constants for Alleyn Cricket Club.

These are separated from the generic API configuration in config.py so that
the core pc/utils classes remain club-agnostic.  Import this module only
from alleyn.py.
"""

TEAM_NAME_TO_IDS_LOOKUP = {
    '1s': 59723, '2s': 59724, '3s': 241803,
    '4s': 267647, '5s': 394397, 'Barbarians': 279276,
    'Badgers': 268144, 'Honey Badgers': 368707, 'Friendly': 320697,
}

TEAM_NAMES = ['Brixton Barbarians', 'Alleyn CC']

# Words and suffixes stripped from opposition team names before display.
TEAM_NAME_BANNED_WORDS = [
    ', Surrey', 'CC - ', ' XI', 'Saturday', 'Sunday',
    'Sat', 'Sun', ' CC', ', Kent', '(Kent)',
]

# Ordinal suffixes that are replaced with a plain 's' in team names
# (e.g. "1st XI" → "1s").
N_TEAM_SWAP = ['st XI', 'nd XI', 'rd XI', 'th XI']
