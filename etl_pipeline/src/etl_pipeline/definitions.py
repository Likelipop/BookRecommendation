from dagster import Definitions, load_assets_from_modules

from .defs import bronze, silver, gold

from .checks import (
    check_books_error_rate,
    check_users_error_rate,
    check_ratings_error_rate,
    check_ratings_no_null_keys
)

from .sensors.silver_sensors import silver_books_error_sensor, silver_users_error_sensor, silver_ratings_error_sensor


from .databrick_resource import DatabricksServerlessResource

bronze_assets = load_assets_from_modules([bronze])
silver_assets = load_assets_from_modules([silver])
gold_assets = load_assets_from_modules([gold])

db_resource = DatabricksServerlessResource()

defs = Definitions(
    assets=[*bronze_assets, *silver_assets, *gold_assets],
    asset_checks=[
        check_books_error_rate,
        check_users_error_rate,
        check_ratings_error_rate,
        check_ratings_no_null_keys
    ],
    sensors=[
        silver_books_error_sensor,
        silver_users_error_sensor,
        silver_ratings_error_sensor
    ],
    resources={
        "db_resource": db_resource
    }
)