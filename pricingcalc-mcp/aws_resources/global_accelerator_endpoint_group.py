from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class GlobalacceleratorEndpointGroup:
    """
    Python equivalent of Infracost GlobalacceleratorEndpointGroup resource.
    Auto-generated from Go struct definition.
    """
    address: str = ''
    region: str = ''
    monthly_inbound_data_transfer_gb: Any
    monthly_outbound_data_transfer_gb: Any

    def core_type(self) -> str:
        return "GlobalacceleratorEndpointGroup"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "monthly_inbound_data_transfer_gb", default_value: 0}
        {key: "monthly_outbound_data_transfer_gb", default_value: 0}
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
class globalAcceleratorRegionDataTransferUsage:
    """
    Python equivalent of Infracost globalAcceleratorRegionDataTransferUsage resource.
    Auto-generated from Go struct definition.
    """
    us: Optional[float] = None
    europe: Optional[float] = None
    south_africa: Optional[float] = None
    south_america: Optional[float] = None
    south_korea: Optional[float] = None
    australia: Optional[float] = None
    asia_pacific: Optional[float] = None
    middle_east: Optional[float] = None
    india: Optional[float] = None

    def core_type(self) -> str:
        return "globalAcceleratorRegionDataTransferUsage"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "us", default_value: 0}
        {key: "europe", default_value: 0}
        {key: "south_africa", default_value: 0}
        {key: "south_america", default_value: 0}
        {key: "south_korea", default_value: 0}
        {key: "australia", default_value: 0}
        {key: "asia_pacific", default_value: 0}
        {key: "middle_east", default_value: 0}
        {key: "india", default_value: 0}
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
class globalAcceleratorRegionData:
    """
    Python equivalent of Infracost globalAcceleratorRegionData resource.
    Auto-generated from Go struct definition.
    """
    aws_grouped_name: str = ''
    code_region: str = ''
    monthly_inbound_data_transfer_gb: Optional[float] = None
    monthly_outbound_data_transfer_gb: Optional[float] = None

    def core_type(self) -> str:
        return "globalAcceleratorRegionData"

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
  "GlobalacceleratorEndpointGroup": [
    {
      "key": "monthly_inbound_data_transfer_gb",
      "type": "Any",
      "default_value": 0
    },
    {
      "key": "monthly_outbound_data_transfer_gb",
      "type": "Any",
      "default_value": 0
    }
  ],
  "globalAcceleratorRegionDataTransferUsage": [
    {
      "key": "us",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "europe",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "south_africa",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "south_america",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "south_korea",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "australia",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "asia_pacific",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "middle_east",
      "type": "Optional[float]",
      "default_value": 0
    },
    {
      "key": "india",
      "type": "Optional[float]",
      "default_value": 0
    }
  ]
}
