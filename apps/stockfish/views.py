from __future__ import annotations

from django.http import JsonResponse
from django.views import View

from apps.stockfish.models import StockfishEngineProfile
from apps.stockfish.services import engine_available


class StockfishStatusView(View):
    def get(self, request):
        profile = StockfishEngineProfile.default_profile()
        return JsonResponse(
            {
                "available": engine_available(profile.binary_path),
                "profile": profile.name,
                "binary_path": profile.binary_path,
                "depth": profile.default_depth,
                "movetime_ms": profile.default_movetime_ms,
            }
        )
