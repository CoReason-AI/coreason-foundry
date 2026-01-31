# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from coreason_foundry.utils.hashing import compute_agent_hash

def test_hashing_consistency() -> None:
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}

    hash1 = compute_agent_hash(data1)
    hash2 = compute_agent_hash(data2)

    assert hash1 == hash2

def test_hashing_nested() -> None:
    data1 = {"config": {"a": 1}, "list": [1, 2]}
    data2 = {"list": [1, 2], "config": {"a": 1}}

    assert compute_agent_hash(data1) == compute_agent_hash(data2)
