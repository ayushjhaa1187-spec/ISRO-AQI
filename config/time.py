import pytz

# Canonical time convention
MASTER_TIMELINE = "daily"
TIMEZONE = pytz.UTC

# CPCB Timezone (IST is UTC+5:30)
CPCB_TIMEZONE = pytz.timezone('Asia/Kolkata')
MIN_VALID_HOURS_PER_DAY = 16
