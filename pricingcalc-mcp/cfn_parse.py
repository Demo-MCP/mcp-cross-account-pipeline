import yaml
import json
from typing import Dict, List, Any, Optional
from cfn_mappings import CFN_TO_CLASS_MAPPINGS

class CFNParser:
    def parse_template(self, template_content: str) -> Dict[str, Any]:
        try:
            if template_content.strip().startswith('{'):
                template = json.loads(template_content)
            else:
                template = yaml.safe_load(template_content)
        except Exception as e:
            raise ValueError(f"Failed to parse template: {e}")
        
        resources = template.get('Resources', {})
        bom = []
        unpriced_resources = []
        
        for resource_name, resource_def in resources.items():
            resource_type = resource_def.get('Type')
            
            if resource_type in CFN_TO_CLASS_MAPPINGS:
                props = resource_def.get('Properties', {})
                bom.append({
                    'name': resource_name,
                    'type': resource_type,
                    'class': CFN_TO_CLASS_MAPPINGS[resource_type],
                    'properties': props
                })
            else:
                unpriced_resources.append({
                    'name': resource_name,
                    'type': resource_type,
                    'reason': 'Unsupported resource type'
                })
        
        return {'bom': bom, 'unpriced_resources': unpriced_resources}
