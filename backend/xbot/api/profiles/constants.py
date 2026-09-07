import logging
import re
from ruamel.yaml import YAML
from fastapi import APIRouter
from xbot.models.profile import ProfileStatus
logger = logging.getLogger(__name__)

yaml = YAML(typ="safe")
yaml.default_flow_style = False

router = APIRouter(prefix="/profiles", tags=["Profiles"])
from xbot.config import settings

BASE_PROFILE_DIR = settings.BASE_PROFILE_DIR

