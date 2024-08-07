from pathlib import Path

from botocore.endpoint_provider import Enum

MODELS_DIR = "pretrained_models"

DERAIN = Path(__file__).parent / MODELS_DIR / "derain.pth"
DEFOCUS = Path(__file__).parent / MODELS_DIR / "defocus.pth"
DEBLUR = Path(__file__).parent / MODELS_DIR / "deblur.pth"

class Model(str, Enum):
    DERAIN = "derain"
    DEFOCUS = "defocus"
    DEBLUR = "deblur"
