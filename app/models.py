# Import all models in correct order to avoid SQLAlchemy relationship resolution issues
# Projects and audits MUST be imported before auth so that Proyecto/Auditoria are
# registered in the mapper before Usuario's string relationships resolve.
from app.projects.models import Proyecto, ArchivoProyecto
from app.audits.models import (
    Auditoria, ResultadoWorker, Vulnerabilidad,
    MapeoEstandar, TareaRemediacion, HistorialEjecucion,
)
from app.auth.models import Rol, Usuario
