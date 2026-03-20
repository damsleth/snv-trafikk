import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE_DEMAND_PATH = REPO_ROOT / "scripts" / "03_generate_demand.py"


def load_generate_demand_module():
    spec = importlib.util.spec_from_file_location("generate_demand_under_test", GENERATE_DEMAND_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generate_demand = load_generate_demand_module()


def test_scale_matrix_preserves_total_with_largest_remainder() -> None:
    matrix = {
        "zone_a": [0, 3, 1],
        "zone_b": [2, 0, 0],
        "zone_c": [1, 1, 0],
    }

    scaled = generate_demand.scale_matrix(matrix, 0.5)

    assert scaled == {
        "zone_a": [0, 2, 1],
        "zone_b": [1, 0, 0],
        "zone_c": [0, 0, 0],
    }
    assert sum(sum(row) for row in scaled.values()) == 4


def test_resolve_demand_variants_includes_catalog_and_cli_scales() -> None:
    variants = generate_demand.resolve_demand_variants([0.9])

    assert variants["1A"] == [0.9, 1.0]
    assert variants["4A"] == [0.8, 0.9, 1.0]


def test_od_matrices_reaggregate_to_official_appendix_tables() -> None:
    zone_groups = {
        "snv_syd": ["snv_syd"],
        "bbv_west": ["bbv_west"],
        "snv_nordost": ["e18_vest", "e18_ost", "ring3_nord", "snv_nordost"],
        "wideroe_nordvest": ["wideroe_nordvest"],
        "odd_nansens_vest": ["odd_nansens_vest"],
        "snv_east": ["snv_east"],
        "martin_linges_sydost": ["martin_linges_sydost"],
        "rolfsbukt_syd": ["rolfsbukt_syd"],
    }
    official_order = list(zone_groups)

    for demand_name, periods in generate_demand.OFFICIAL_OD_MATRICES.items():
        for period_name, official_matrix in periods.items():
            generated = generate_demand.OD_MATRICES[demand_name][period_name]
            reaggregated = {}

            for row_name, members in zone_groups.items():
                collapsed_row = []
                for column_name, column_members in zone_groups.items():
                    collapsed_row.append(
                        sum(
                            generated[member][generate_demand.ZONE_ORDER.index(column_member)]
                            for member in members
                            for column_member in column_members
                        )
                    )
                reaggregated[row_name] = collapsed_row

            assert reaggregated == {
                zone_name: official_matrix[zone_name]
                for zone_name in official_order
            }
