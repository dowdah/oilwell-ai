from oilwell_ml.split import grouped_split


def test_grouped_split_is_stable_and_never_leaks_a_group() -> None:
    records = [
        {"instance_id": f"normal-{index}", "well_id": f"well-{index}", "label": "0"}
        for index in range(5)
    ] + [
        {"instance_id": f"abnormal-{index}", "well_id": f"well-a-{index}", "label": "3"}
        for index in range(5)
    ]
    first, second = grouped_split(records), grouped_split(records)
    assert first == second
    all_groups = [group for split in first.values() for group in split]
    assert len(all_groups) == len(set(all_groups)) == 10
    assert all(first[name] for name in ("train", "validation", "test"))
