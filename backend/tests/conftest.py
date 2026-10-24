"""
conftest.py — Configuration pytest pour le projet Maroclear.
Ajoute le dossier backend/ au path Python pour les imports.
"""
import sys
import inspect
from pathlib import Path

# Ajouter backend/ au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Compatibilité locale : Starlette 0.36.x passe encore l'argument "app" à
# httpx.Client, supprimé dans httpx 0.28. Le requirements.txt borne httpx<0.28 ;
# ce shim évite toutefois un échec si l'environnement global contient httpx 0.28+.
try:
    import httpx

    if "app" not in inspect.signature(httpx.Client.__init__).parameters:
        _httpx_client_init = httpx.Client.__init__

        def _compatible_httpx_client_init(self, *args, **kwargs):
            kwargs.pop("app", None)
            return _httpx_client_init(self, *args, **kwargs)

        httpx.Client.__init__ = _compatible_httpx_client_init
except Exception:
    pass
