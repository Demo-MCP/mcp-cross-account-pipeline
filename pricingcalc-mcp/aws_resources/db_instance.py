from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class DBInstance:
    """
    Python equivalent of Infracost DBInstance resource.
    Auto-generated from Go struct definition.
    """
    address: str = ''
    region: str = ''
    license_model: str = ''
    storage_type: str = ''
    backup_retention_period: int = 0
    io_optimized: bool = False
    performance_insights_enabled: bool = False
    performance_insights_long_term_retention: bool = False
    multi_az: bool = False
    instance_class: str = ''
    engine: str = ''
    version: str = ''
    iops: float = 0
    allocated_storage_gb: Optional[float] = None
    monthly_standard_io_requests: Optional[int] = None
    additional_backup_storage_gb: Optional[float] = None
    monthly_additional_performance_insights_requests: Optional[int] = None
    reserved_instance_term: Optional[str] = None
    reserved_instance_payment_option: Optional[str] = None

    def core_type(self) -> str:
        return "DBInstance"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "monthly_standard_io_requests", default_value: 0}
        {key: "additional_backup_storage_gb", default_value: 0}
        {key: "monthly_additional_performance_insights_requests", default_value: 0}
        {key: "reserved_instance_term", default_value: 0}
        {key: "reserved_instance_payment_option", default_value: 0}
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



@dataclass
class ExtendedSupportDates:
    """
    Python equivalent of Infracost ExtendedSupportDates resource.
    Auto-generated from Go struct definition.
    """
    usagetype_version: str = ''
    year1: Any
    year3: Any

    def core_type(self) -> str:
        return "ExtendedSupportDates"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return []

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



@dataclass
class ExtendedSupport:
    """
    Python equivalent of Infracost ExtendedSupport resource.
    Auto-generated from Go struct definition.
    """
    engine: str = ''
    versions: Any

    def core_type(self) -> str:
        return "ExtendedSupport"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return []

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
  "DBInstance": [
    {
      "key": "monthly_standard_io_requests",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "additional_backup_storage_gb",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "monthly_additional_performance_insights_requests",
      "type": "Optional[int]",
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
    }
  ]
}
