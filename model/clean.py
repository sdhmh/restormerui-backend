from io import BytesIO
from pathlib import Path



# // 2
import torch
import torch.nn.functional as F
from runpy import run_path
from skimage import img_as_ubyte
import cv2
import numpy as np

img_multiple_of = 8

def load_model(model_path: Path):
    #? Get model weights and parameters
    parameters = {'inp_channels':3, 'out_channels':3, 'dim':48, 'num_blocks':[4,6,6,8], 'num_refinement_blocks':4, 'heads':[1,2,4,8], 'ffn_expansion_factor':2.66, 'bias':False, 'LayerNorm_type':'WithBias', 'dual_pixel_task':False}

    load_arch = run_path(str(Path(__file__).parent / 'restormer_arch.py'))
    model = load_arch['Restormer'](**parameters)


    checkpoint = torch.load(str(model_path.absolute()))
    model.load_state_dict(checkpoint['params'])
    return model

def clean_image(input_image: bytes, model) -> BytesIO:
    with torch.no_grad():
        model.eval()
        np_image = np.frombuffer(input_image, np.uint8)
        cv2_img = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
        input_ = torch.from_numpy(cv2_img).float().div(255.).permute(2,0,1).unsqueeze(0)

        h,w = input_.shape[2], input_.shape[3]
        H,W = ((h+img_multiple_of)//img_multiple_of)*img_multiple_of, ((w+img_multiple_of)//img_multiple_of)*img_multiple_of
        pad_h = H-h if h%img_multiple_of!=0 else 0
        pad_w = W-w if w%img_multiple_of!=0 else 0
        input_ = F.pad(input_, (0,pad_w,0,pad_h), 'reflect')

        restored = model(input_)
        restored = torch.clamp(restored, 0, 1)

        # Unpad the output
        restored = restored[:,:,:h,:w]

        restored = restored.permute(0, 2, 3, 1).cpu().detach().numpy()
        restored = img_as_ubyte(restored[0])

        is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(restored, cv2.IMREAD_COLOR))
        io_buf = BytesIO(buffer.tobytes())
    return io_buf


if __name__=="__main__":
    input = Path("input")/"input.jpg"
    output = Path("output")/"output.jpg"

    output.parent.mkdir(exist_ok=True)
    with open(input, "rb") as image:
        output_image = clean_image(image.read(), load_model(Path("pretrained_models")/"derain.pth"))
    with open(output, "wb") as output:
        output.write(output_image.read())
