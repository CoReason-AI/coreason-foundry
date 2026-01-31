# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import hashlib
import json
from typing import Any, Dict


def compute_agent_hash(data: Dict[str, Any]) -> str:
    """
    Computes the SHA256 integrity hash of a dictionary.

    The dictionary is first serialized to a canonical JSON string
    (sorted keys, no whitespace).
    """
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
