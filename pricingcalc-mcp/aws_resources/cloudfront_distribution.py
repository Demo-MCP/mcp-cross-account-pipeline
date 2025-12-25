from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class CloudfrontDistribution:
    """
    Python equivalent of Infracost CloudfrontDistribution resource.
    Auto-generated from Go struct definition.
    """
    address: str = ''
    region: str = ''
    is_origin_shield_enabled: bool = False
    is_ssl_support_method_vip: bool = False
    has_logging_config_bucket: bool = False
    has_field_level_encryption_id: bool = False
    origin_shield_region: str = ''
    monthly_http_requests: Any
    monthly_https_requests: Any
    monthly_shield_requests: Any
    monthly_invalidation_requests: Optional[int] = None
    monthly_encryption_requests: Optional[int] = None
    monthly_log_lines: Optional[int] = None
    monthly_data_transfer_to_internet_gb: Any
    monthly_data_transfer_to_origin_gb: Any
    custom_ssl_certificates: Optional[int] = None

    def core_type(self) -> str:
        return "CloudfrontDistribution"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "monthly_http_requests", default_value: 0}
        {key: "monthly_https_requests", default_value: 0}
        {key: "monthly_shield_requests", default_value: 0}
        {key: "monthly_invalidation_requests", default_value: 0}
        {key: "monthly_encryption_requests", default_value: 0}
        {key: "monthly_log_lines", default_value: 0}
        {key: "monthly_data_transfer_to_internet_gb", default_value: 0}
        {key: "monthly_data_transfer_to_origin_gb", default_value: 0}
        {key: "custom_ssl_certificates", default_value: 0}
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
class cloudfrontDistributionRegionDataTransferUsage:
    """
    Python equivalent of Infracost cloudfrontDistributionRegionDataTransferUsage resource.
    Auto-generated from Go struct definition.
    """
    us: Optional[float] = None
    europe: Optional[float] = None
    south_africa: Optional[float] = None
    south_america: Optional[float] = None
    japan: Optional[float] = None
    australia: Optional[float] = None
    asia_pacific: Optional[float] = None
    india: Optional[float] = None

    def core_type(self) -> str:
        return "cloudfrontDistributionRegionDataTransferUsage"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "us", default_value: 0}
        {key: "europe", default_value: 0}
        {key: "south_africa", default_value: 0}
        {key: "south_america", default_value: 0}
        {key: "japan", default_value: 0}
        {key: "australia", default_value: 0}
        {key: "asia_pacific", default_value: 0}
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
class cloudfrontDistributionRegionRequestsUsage:
    """
    Python equivalent of Infracost cloudfrontDistributionRegionRequestsUsage resource.
    Auto-generated from Go struct definition.
    """
    us: Optional[int] = None
    europe: Optional[int] = None
    south_africa: Optional[int] = None
    south_america: Optional[int] = None
    japan: Optional[int] = None
    australia: Optional[int] = None
    asia_pacific: Optional[int] = None
    india: Optional[int] = None

    def core_type(self) -> str:
        return "cloudfrontDistributionRegionRequestsUsage"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "us", default_value: 0}
        {key: "europe", default_value: 0}
        {key: "south_africa", default_value: 0}
        {key: "south_america", default_value: 0}
        {key: "japan", default_value: 0}
        {key: "australia", default_value: 0}
        {key: "asia_pacific", default_value: 0}
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
class cloudfrontDistributionShieldRequestsUsage:
    """
    Python equivalent of Infracost cloudfrontDistributionShieldRequestsUsage resource.
    Auto-generated from Go struct definition.
    """
    us: Optional[int] = None
    europe: Optional[int] = None
    south_america: Optional[int] = None
    japan: Optional[int] = None
    australia: Optional[int] = None
    singapore: Optional[int] = None
    south_korea: Optional[int] = None
    indonesia: Optional[int] = None
    india: Optional[int] = None
    middle_east: Optional[int] = None

    def core_type(self) -> str:
        return "cloudfrontDistributionShieldRequestsUsage"

    def usage_schema(self) -> List[Dict[str, Any]]:
        return [
        {key: "us", default_value: 0}
        {key: "europe", default_value: 0}
        {key: "south_america", default_value: 0}
        {key: "japan", default_value: 0}
        {key: "australia", default_value: 0}
        {key: "singapore", default_value: 0}
        {key: "south_korea", default_value: 0}
        {key: "indonesia", default_value: 0}
        {key: "india", default_value: 0}
        {key: "middle_east", default_value: 0}
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
class cloudfrontDistributionRegionData:
    """
    Python equivalent of Infracost cloudfrontDistributionRegionData resource.
    Auto-generated from Go struct definition.
    """
    aws_grouped_name: str = ''
    price_region: str = ''
    monthly_http_requests: Optional[int] = None
    monthly_https_requests: Optional[int] = None
    monthly_data_transfer_to_internet_gb: Optional[float] = None
    monthly_data_transfer_to_origin_gb: Optional[float] = None

    def core_type(self) -> str:
        return "cloudfrontDistributionRegionData"

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
  "CloudfrontDistribution": [
    {
      "key": "monthly_http_requests",
      "type": "Any",
      "default_value": 0
    },
    {
      "key": "monthly_https_requests",
      "type": "Any",
      "default_value": 0
    },
    {
      "key": "monthly_shield_requests",
      "type": "Any",
      "default_value": 0
    },
    {
      "key": "monthly_invalidation_requests",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "monthly_encryption_requests",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "monthly_log_lines",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "monthly_data_transfer_to_internet_gb",
      "type": "Any",
      "default_value": 0
    },
    {
      "key": "monthly_data_transfer_to_origin_gb",
      "type": "Any",
      "default_value": 0
    },
    {
      "key": "custom_ssl_certificates",
      "type": "Optional[int]",
      "default_value": 0
    }
  ],
  "cloudfrontDistributionRegionDataTransferUsage": [
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
      "key": "japan",
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
      "key": "india",
      "type": "Optional[float]",
      "default_value": 0
    }
  ],
  "cloudfrontDistributionRegionRequestsUsage": [
    {
      "key": "us",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "europe",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "south_africa",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "south_america",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "japan",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "australia",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "asia_pacific",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "india",
      "type": "Optional[int]",
      "default_value": 0
    }
  ],
  "cloudfrontDistributionShieldRequestsUsage": [
    {
      "key": "us",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "europe",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "south_america",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "japan",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "australia",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "singapore",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "south_korea",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "indonesia",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "india",
      "type": "Optional[int]",
      "default_value": 0
    },
    {
      "key": "middle_east",
      "type": "Optional[int]",
      "default_value": 0
    }
  ]
}
