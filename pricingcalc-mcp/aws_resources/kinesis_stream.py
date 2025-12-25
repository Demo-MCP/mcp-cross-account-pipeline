from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class KinesisStream:
    """
    Python equivalent of Infracost KinesisStream resource.
    Auto-generated from Go struct definition.
    """
    address: str = ''
    region: str = ''
    stream_mode: str = ''
    shard_count: int = 0
    monthly_on_demand_data_ingested_gb: Optional[float] = None
    monthly_on_demand_data_retrieval_gb: Optional[float] = None
    monthly_on_demand_efo_data_retrieval_gb: Optional[float] = None
    monthly_on_demand_extended_retention_gb: Optional[float] = None
    monthly_on_demand_long_term_retention_gb: Optional[float] = None
    monthly_provisioned_put_units: Optional[float] = None
    monthly_provisioned_extended_retention_gb: Optional[float] = None
    monthly_provisioned_long_term_retention_gb: Optional[float] = None
    monthly_provisioned_long_term_retrieval_gb: Optional[float] = None
    monthly_provisioned_efo_data_retrieval_gb: Optional[float] = None
    monthly_provisioned_efo_consumer_hours: Optional[float] = None

    def core_type(self) -> str:
        return "KinesisStream"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "monthly_on_demand_data_in_gb", default_value: 0}
        {key: "monthly_on_demand_data_out_gb", default_value: 0}
        {key: "monthly_on_demand_efo_data_out_gb", default_value: 0}
        {key: "monthly_on_demand_extended_retention_gb", default_value: 0}
        {key: "monthly_on_demand_long_term_retention_gb", default_value: 0}
        {key: "monthly_provisioned_put_units", default_value: 0}
        {key: "monthly_provisioned_extended_retention_gb", default_value: 0}
        {key: "monthly_provisioned_long_term_retention_gb", default_value: 0}
        {key: "monthly_provisioned_long_term_retrieval_gb", default_value: 0}
        {key: "monthly_provisioned_efo_data_out_gb", default_value: 0}
        {key: "monthly_provisioned_efo_consumer_hours", default_value: 0}
        ]

    def build_resource(self) -> Dict[str, Any]:
        # TODO: Implement pricing logic based on Infracost patterns
        return {
            'name': getattr(self, 'address', self.core_type()),
            'cost_components': self._build_cost_components(),
            'usage_schema': self.usage_schema()
        }
    
    def _build_cost_components(self) -> List[Dict[str, Any]]:
        # TODO: Extract cost component logic from Go implementation
        return []



# Usage schema mappings extracted from Go structs
USAGE_SCHEMAS = {
  "KinesisStream": [
    {
      "key": "monthly_on_demand_data_in_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_on_demand_data_out_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_on_demand_efo_data_out_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_on_demand_extended_retention_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_on_demand_long_term_retention_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_provisioned_put_units",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_provisioned_extended_retention_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_provisioned_long_term_retention_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_provisioned_long_term_retrieval_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_provisioned_efo_data_out_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_provisioned_efo_consumer_hours",
      "type": "Optional[float]",
      "default_value": 0
    }
  ]
}
