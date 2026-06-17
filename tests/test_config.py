import json
from pathlib import Path


def test_fraud_config_has_required_keys():
    config_path = Path("fraud_config.json")
    assert config_path.exists()

    config = json.loads(config_path.read_text())

    assert "train_file" in config
    assert "test_file" in config
    assert "output_file" in config
    assert "columns" in config


def test_fraud_config_has_required_column_mappings():
    config = json.loads(Path("fraud_config.json").read_text())

    required_columns = [
        "transaction_time",
        "customer",
        "merchant",
        "category",
        "amount",
        "customer_lat",
        "customer_long",
        "merchant_lat",
        "merchant_long",
        "fraud_label",
    ]

    for column in required_columns:
        assert column in config["columns"]
        assert config["columns"][column]