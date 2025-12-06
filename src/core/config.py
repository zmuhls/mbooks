"""Configuration management for the book listing system."""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Config:
    """Central configuration management."""

    _instance: Optional['Config'] = field(default=None, repr=False, init=False)
    _config: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, config_path: Optional[str] = None):
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = self._find_config()

        self._config_path = Path(config_path)
        self._load_config()

    def _find_config(self) -> str:
        """Find configuration file in standard locations."""
        locations = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path(__file__).parent.parent.parent / "config.yaml",
        ]

        for loc in locations:
            if loc.exists():
                return str(loc)

        raise FileNotFoundError("No config.yaml found in standard locations")

    def _load_config(self):
        """Load and parse YAML configuration."""
        with open(self._config_path, 'r') as f:
            self._config = yaml.safe_load(f)

        # Expand environment variables for sensitive values
        self._expand_env_vars()

    def _expand_env_vars(self):
        """Expand environment variable references in config."""
        ebay_creds = self.get('ebay.credentials', {})
        for key, env_var in ebay_creds.items():
            if env_var and isinstance(env_var, str):
                self._config.setdefault('ebay', {}).setdefault('credentials_resolved', {})
                self._config['ebay']['credentials_resolved'][key.replace('_env', '')] = os.getenv(env_var, '')

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'ebay.api_version')."""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    @property
    def base_path(self) -> Path:
        """Get base path for the project."""
        return self._config_path.parent

    @property
    def listings_path(self) -> Path:
        """Get path to listings directory."""
        return self.base_path / self.get('paths.listings_dir', './listings')

    @property
    def exports_path(self) -> Path:
        """Get path to exports directory."""
        return self.base_path / self.get('paths.exports_dir', './exports')

    @property
    def site_path(self) -> Path:
        """Get path to website directory."""
        return self.base_path / self.get('paths.website_dir', './site')

    @property
    def ebay_environment(self) -> str:
        """Get eBay environment (sandbox/production)."""
        return self.get('ebay.environment', 'sandbox')

    def get_ebay_endpoint(self, endpoint_type: str) -> str:
        """Get eBay API endpoint URL."""
        env = self.ebay_environment
        return self.get(f'ebay.endpoints.{env}.{endpoint_type}', '')

    @property
    def vision_model(self) -> str:
        """Get vision model for extraction."""
        return self.get('vision.model', 'claude-sonnet-4-5-20250929')

    @property
    def website_colors(self) -> Dict[str, str]:
        """Get website color palette."""
        return self.get('website.colors', {})

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return self._config.copy()


# Singleton accessor
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Get or create configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
