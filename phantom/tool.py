from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import json
import logging
from enum import Enum

class ToolParameterType(str, Enum):
    """Supported parameter types for tools"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"


logger = logging.getLogger(__name__)

@dataclass
class Field:
    """Strongly typed field definition for tool parameters."""
    name: str
    description: str
    required: bool = True
    field_type: ToolParameterType = ToolParameterType.STRING
    default_value: Optional[Any] = None


    def __post_init__(self):
        """Validate field configuration after initialization."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Field name must be a non-empty string")
        if not self.description or not isinstance(self.description, str):
            raise ValueError("Field description must be a non-empty string")
        
        valid_types = [e.value for e in ToolParameterType]
        if self.field_type not in valid_types:
            raise ValueError(f"Invalid field_type: {self.field_type}. Valid types: {valid_types}")
    
    def validate_value(self, value: Any) -> bool:
        """Validate if a value matches this field's requirements."""
        if value is None:
            return not self.required
        
        type_mapping = {
            ToolParameterType.STRING: str,
            ToolParameterType.INTEGER: int,
            ToolParameterType.NUMBER: (int, float),
            ToolParameterType.BOOLEAN: bool,
            ToolParameterType.ARRAY: list,
            ToolParameterType.OBJECT: dict,
            ToolParameterType.ANY: object
        }
        
        expected_type = type_mapping.get(self.field_type)
        if expected_type and self.field_type != ToolParameterType.ANY:
            if not isinstance(value, expected_type):
                logger.error(f"Field {self.name} expects {self.field_type.value} but got {type(value).__name__}")
                return False
        
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert field to dictionary representation for JSON Schema."""
        schema = {
            "type": self.field_type.value,
            "description": self.description
        }
        # Note: default values are handled separately and not included in the schema
        # as they're not supported by all LLM function calling implementations
        return schema

@dataclass
class ToolResult:
    """Standardized tool execution result."""
    success: bool
    result: Any
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "result": self.result,
            "error_message": self.error_message,
            "metadata": self.metadata
        }

class BaseTool(ABC):
    """Enhanced base class for all tools with strong typing and validation."""
    
    def __init__(self):
        self.name: str = getattr(self, 'name', self.__class__.__name__)
        self.description: str = getattr(self, 'description', '')
        self.params: List[Field] = getattr(self, 'params', [])
        self._validate_tool_config()
    
    def _validate_tool_config(self) -> None:
        """Validate tool configuration."""
        if not self.name:
            raise ValueError(f"Tool {self.__class__.__name__} must have a name")
        if not self.description:
            raise ValueError(f"Tool {self.name} must have a description")
        if not isinstance(self.params, list):
            raise ValueError(f"Tool {self.name} params must be a list of Field objects")
        
        for param in self.params:
            if not isinstance(param, Field):
                raise ValueError(f"Tool {self.name} params must contain only Field objects")
    
    def validate_parameters(self, kwargs: Dict[str, Any]) -> ToolResult:
        """Validate input parameters against field definitions."""
        try:
            for param in self.params:
                if param.required and param.name not in kwargs:
                    return ToolResult(success=False, result=None, error_message=f"Missing required parameter: {param.name}")
                if param.name in kwargs and not param.validate_value(kwargs[param.name]):
                    return ToolResult(success=False, result=None, error_message=f"Invalid type for parameter {param.name}: expected {param.field_type.value}, got {type(kwargs[param.name]).__name__}")
            return ToolResult(success=True, result="Parameters validated successfully")
        except Exception as e:
            logger.error(f"Parameter validation error in {self.name}: {str(e)}")
            return ToolResult(success=False, result=None, error_message=f"Parameter validation error: {str(e)}")
    
    def run(self, **kwargs) -> Any:
        """Execute tool with parameter validation and error handling."""
        validation_result = self.validate_parameters(kwargs)
        if not validation_result.success:
            return validation_result.to_dict()
        
        for param in self.params:
            if param.name not in kwargs and param.default_value is not None:
                kwargs[param.name] = param.default_value
        
        try:
            return self._run(**kwargs)
        except Exception as e:
            logger.error(f"Tool execution error in {self.name}: {str(e)}")
            return {"success": False, "error_message": f"Tool execution error: {str(e)}"}
    
    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """Abstract method to be implemented by concrete tools."""
        raise NotImplementedError("Please implement the _run method")
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema compatible with Gemini function calling."""
        properties = {param.name: param.to_dict() for param in self.params}
        required = [param.name for param in self.params if param.required]
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
    
    def __str__(self) -> str:
        """String representation of the tool."""
        return f"Tool({self.name}): {self.description}"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"BaseTool(name='{self.name}', params={len(self.params)})"