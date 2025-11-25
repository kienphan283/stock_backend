""
HTTP helper utilities shared across ETL modules.
""
from typing import Any, Dict, Optional

import requests


def get_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Perform an HTTP GET request and return the JSON payload.
    """
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()

