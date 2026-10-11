"""Optional offline image generation with a predownloaded Diffusers pipeline.

The model directory is local to the workspace, and no download fallback exists.
Images are written only to fresh PNG files after explicit approval.
"""
import importlib.util
from pathlib import Path
from workspace_data import safe_path

def image_model_status(workspace,model_folder):
    path=safe_path(workspace,model_folder)
    return {"model_ready":path.is_dir() and (path/"model_index.json").is_file(),
            "diffusers_installed":importlib.util.find_spec("diffusers") is not None,
            "torch_installed":importlib.util.find_spec("torch") is not None,
            "offline_only":True}

def generate_local_image(workspace,prompt,model_folder,target,approve,steps=20):
    if not isinstance(prompt,str) or not 3<=len(prompt)<=1500:
        raise ValueError("Invalid image description")
    if not isinstance(steps,int) or not 1<=steps<=40:
        raise ValueError("Invalid inference steps")
    dst=safe_path(workspace,target)
    if dst.suffix.lower()!=".png" or dst.exists() or dst.is_symlink():
        raise ValueError("Expected a new PNG target")
    model=safe_path(workspace,model_folder)
    if not model.is_dir() or not (model/"model_index.json").is_file():
        return {"unavailable":"No local Diffusers model at selected path"}
    state=image_model_status(workspace,model_folder)
    if not state["diffusers_installed"] or not state["torch_installed"]:
        return {"unavailable":"Install Diffusers and Torch explicitly to use local image generation"}
    if not approve("ליצור תמונה בעזרת מודל מקומי? התהליך עשוי לצרוך משאבי מחשב רבים."):
        return {"cancelled":True}
    from diffusers import DiffusionPipeline
    # Model must be entirely local; pipeline does not contact the internet.
    pipeline=DiffusionPipeline.from_pretrained(str(model),local_files_only=True)
    result=pipeline(prompt,num_inference_steps=steps)
    if not result.images:
        return {"error":"Image model did not return an image"}
    output=result.images[0]
    if output.width*output.height>16_000_000:
        return {"error":"Image dimensions exceed safety limit"}
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open("xb") as out:output.save(out,format="PNG")
    return {"created_image":str(dst),"width":output.width,"height":output.height}
