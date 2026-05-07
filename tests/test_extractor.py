from unmet_demand.extract.extractor import extract_from_text


def test_extracts_wish_pattern():
    rows = extract_from_text(
        1,
        "Godot workflow",
        "I wish there was a Godot plugin that exported clean Steam capsule art from in-game screenshots.",
        "Godot",
    )

    assert len(rows) == 1
    assert "Steam capsule art" in rows[0].desired_solution
    assert rows[0].niche == "Godot"
    assert 1 <= rows[0].urgency_score <= 5


def test_extracts_multiple_patterns():
    rows = extract_from_text(
        2,
        None,
        "I hate that I have to rebuild tileset collisions by hand. Is there a plugin for syncing Aseprite slices into Godot?",
        "Game assets",
    )

    assert len(rows) == 2
    assert any("Aseprite" in row.desired_solution for row in rows)
