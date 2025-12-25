from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class EKSNodeGroup:
    """
    Python equivalent of Infracost EKSNodeGroup resource.
    Auto-generated from Go struct definition.
    """
    address: str = ''
    region: str = ''
    name: str = ''
    cluster_name: str = ''
    instance_type: str = ''
    purchase_option: str = ''
    disk_size: float = 0
    root_block_device: Any
    launch_template: Any
    instance_count: Optional[int] = None
    operating_system: Optional[str] = None
    reserved_instance_type: Optional[str] = None
    reserved_instance_term: Optional[str] = None
    reserved_instance_payment_option: Optional[str] = None
    monthly_cpu_credit_hours: Optional[int] = None
    vcpu_count: Optional[int] = None

    def core_type(self) -> str:
        return "EKSNodeGroup"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "instances", default_value: 0}
        {key: "operating_system", default_value: 0}
        {key: "reserved_instance_type", default_value: 0}
        {key: "reserved_instance_term", default_value: 0}
        {key: "reserved_instance_payment_option", default_value: 0}
        {key: "monthly_cpu_credit_hrs", default_value: 0}
        {key: "vcpu_count", default_value: 0}
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
  "EKSNodeGroup": [
    {
      "key": "instances",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "operating_system",
      "type": "Optional[str]",
      "default_value": 0
    },
    {
      "key": "reserved_instance_type",
      "type": "Optional[str]",
      "default_value": 0
    },
    {
      "key": "reserved_instance_term",
      "type": "Optional[str]",
      "default_value": 0
    },
    {
      "key": "reserved_instance_payment_option",
      "type": "Optional[str]",
      "default_value": 0
    },
    {
      "key": "monthly_cpu_credit_hrs",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "vcpu_count",
      "type": "Optional[int]",
      "default_value": 0
    }
  ]
}
