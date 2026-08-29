from xbot.ai.client import get_ai_client
from .models import (
    OptimizedPostResult,
    _ViralHookResponse,
    HookCandidate,
    HookOptimizationResult,
    _HookGenerationResponse,
)
from .templates import (
    _build_hook_optimizer_system_prompt,
    _build_hook_optimizer_user_prompt,
    _build_virality_system_prompt,
    _build_virality_user_prompt,
    _infer_archetype_from_text,
)
from .scorer import (
    extract_links,
    calculate_bookmark_score,
    trim_open_loop_hook,
    clean_text_for_json,
    clean_hook_text,
    format_optimized_post,
    _get_persona_field,
    _normalize_candidate,
)
from .optimizer import (
    _parse_candidates_from_json,
    optimize_post_hook,
    optimize_post_for_virality,
)
from .constants import *

