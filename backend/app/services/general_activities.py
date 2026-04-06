from app.models import GeneralActivity
from app.schemas.general_activities import GeneralActivityCreate, GeneralActivityUpdate
from app.services.base import ServiceBase


class GenericActivityService(
    ServiceBase[GeneralActivity, GeneralActivityCreate, GeneralActivityUpdate],
):
    model = GeneralActivity
