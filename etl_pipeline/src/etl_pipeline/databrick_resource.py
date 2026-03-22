from dagster import ConfigurableResource
from databricks.connect import DatabricksSession
from pydantic import Field

class DatabricksServerlessResource(ConfigurableResource):
    def get_session(self):
        return DatabricksSession.builder.serverless().getOrCreate()

db_resource = DatabricksServerlessResource()

