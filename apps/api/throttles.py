from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RoomWriteAnonRateThrottle(AnonRateThrottle):
    scope = "room_write_anon"


class RoomWriteUserRateThrottle(UserRateThrottle):
    scope = "room_write_user"


class AnalysisAnonRateThrottle(AnonRateThrottle):
    scope = "analysis_anon"


class AnalysisUserRateThrottle(UserRateThrottle):
    scope = "analysis_user"


class OfflineSyncRateThrottle(UserRateThrottle):
    scope = "offline_sync"
