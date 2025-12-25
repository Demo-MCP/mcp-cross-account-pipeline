from typing import Dict, List, Any
import importlib

class CostEstimator:
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.usage_profiles = {
            "low": {
                "monthly_hours": 100,
                "internet_egress_gb": 10,
                "alb_requests_million": 1,
                "logs_gb": 5,
                "lambda_requests": 1000,
                "s3_storage_gb": 10,
                "s3_requests_get": 1000,
                "s3_requests_put": 100
            },
            "medium": {
                "monthly_hours": 500,
                "internet_egress_gb": 100,
                "alb_requests_million": 10,
                "logs_gb": 50,
                "lambda_requests": 100000,
                "s3_storage_gb": 100,
                "s3_requests_get": 10000,
                "s3_requests_put": 1000
            },
            "high": {
                "monthly_hours": 730,
                "internet_egress_gb": 1000,
                "alb_requests_million": 100,
                "logs_gb": 500,
                "lambda_requests": 1000000,
                "s3_storage_gb": 1000,
                "s3_requests_get": 100000,
                "s3_requests_put": 10000
            }
        }
    
    def estimate_costs(self, bom: List[Dict], profiles: List[str], 
                      overrides: Dict = None, profile_overrides: Dict = None) -> Dict[str, Any]:
        estimates = {}
        
        for profile in profiles:
            profile_usage = self.usage_profiles[profile].copy()
            
            # Apply overrides
            if overrides:
                profile_usage.update(overrides)
            if profile_overrides and profile in profile_overrides:
                profile_usage.update(profile_overrides[profile])
            
            profile_estimates = []
            total_monthly_cost = 0
            
            for resource in bom:
                try:
                    # Import resource class dynamically
                    module = importlib.import_module(f'aws_resources.{resource["class"].lower()}')
                    resource_class = getattr(module, resource["class"])
                    
                    # Create instance with properties
                    instance = resource_class(
                        address=resource["name"],
                        region=self.region,
                        **self._map_properties(resource["properties"], resource["class"])
                    )
                    
                    # Estimate cost (simplified)
                    cost = self._estimate_resource_cost(instance, profile_usage)
                    
                    profile_estimates.append({
                        "resource": resource["name"],
                        "type": resource["type"],
                        "monthly_cost": cost,
                        "usage": profile_usage
                    })
                    
                    total_monthly_cost += cost
                    
                except Exception as e:
                    profile_estimates.append({
                        "resource": resource["name"],
                        "type": resource["type"],
                        "error": str(e),
                        "monthly_cost": 0
                    })
            
            estimates[profile] = {
                "resources": profile_estimates,
                "total_monthly_cost": round(total_monthly_cost, 2)
            }
        
        return estimates
    
    def _map_properties(self, props: Dict, class_name: str) -> Dict:
        # Basic property mapping - extend as needed
        mapped = {}
        
        if class_name == "Instance":
            mapped["instance_type"] = props.get("InstanceType", "t3.micro")
        elif class_name == "EcsService":
            mapped["desired_count"] = props.get("DesiredCount", 1)
            mapped["launch_type"] = props.get("LaunchType", "FARGATE")
        elif class_name == "LambdaFunction":
            mapped["memory_size"] = props.get("MemorySize", 128)
        
        return mapped
    
    def _estimate_resource_cost(self, resource, usage: Dict) -> float:
        # Simplified cost estimation - replace with actual pricing logic
        resource_type = resource.core_type()
        
        if resource_type == "Instance":
            # EC2 pricing stub
            instance_type = getattr(resource, 'instance_type', 't3.micro')
            hours = usage.get('monthly_hours', 730)
            
            # Rough pricing per hour
            pricing = {
                't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
                't3.large': 0.0832, 't3.xlarge': 0.1664, 't3.2xlarge': 0.3328
            }
            
            return pricing.get(instance_type, 0.05) * hours
        
        elif resource_type == "ECSService":
            # Fargate pricing stub
            desired_count = getattr(resource, 'desired_count', 1)
            hours = usage.get('monthly_hours', 730)
            return 0.04048 * desired_count * hours  # 0.25 vCPU, 0.5 GB
        
        elif resource_type == "LambdaFunction":
            requests = usage.get('lambda_requests', 1000)
            return max(0, (requests - 1000000) * 0.0000002) + requests * 0.0000166667
        
        else:
            # Default stub cost
            return 5.0
    
    def get_assumptions(self) -> List[str]:
        return [
            "Costs are estimates based on standard AWS pricing",
            "Usage profiles applied: low/medium/high",
            "Prices may vary by region and actual usage patterns",
            "Some resources use simplified pricing models"
        ]
