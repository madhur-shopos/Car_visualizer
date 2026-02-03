"""
Car Video Generation Pipeline - LOCAL STORAGE VERSION
Generates professional automotive showcase videos from car images.

All files stored locally - no cloud storage required.

Requirements:
pip install aiohttp requests pillow google-genai python-dotenv
"""

import asyncio
import time
import os
import sys
from pathlib import Path
from io import BytesIO
from typing import Any, Dict, Optional, List
from uuid import uuid4
from enum import Enum

import aiohttp
import requests
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION FROM .ENV
# ============================================================================

# Higgsfield/Kling Configuration - Strip whitespace and validate
HIGGSFIELD_API_KEY = os.getenv("HIGGSFIELD_API_KEY", "").strip()
HIGGSFIELD_API_SECRET = os.getenv("HIGGSFIELD_API_SECRET", "").strip()
HIGGSFIELD_API_KEY2 = os.getenv("HIGGSFIELD_API_KEY2", "").strip()
HIGGSFIELD_API_SECRET2 = os.getenv("HIGGSFIELD_API_SECRET2", "").strip()

# Google Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

# ImgBB Configuration (for temporary image hosting)
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "").strip()

# Validate Higgsfield API key format (should be UUID)
if HIGGSFIELD_API_KEY:
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, HIGGSFIELD_API_KEY, re.IGNORECASE):
        logger.warning(f"HIGGSFIELD_API_KEY format looks incorrect. Expected UUID format, got: {HIGGSFIELD_API_KEY}")
        logger.warning("Make sure your .env file has clean values without extra text")


# ============================================================================
# LOGGING
# ============================================================================

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GOOGLE GEMINI IMAGE GENERATION
# ============================================================================

from google import genai
from google.genai import types

# Initialize Google GenAI client
def get_google_client():
    """Get or create Google GenAI client"""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not configured in .env file")
    return genai.Client(api_key=GOOGLE_API_KEY)

class OutputFormat(str, Enum):
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    WEBP = "webp"

class AspectRatio(str, Enum):
    RATIO_1_1 = "1:1"
    RATIO_2_3 = "2:3"
    RATIO_3_2 = "3:2"
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_4_3 = "4:3"
    RATIO_3_4 = "3:4"
    RATIO_4_5 = "4:5"
    RATIO_5_4 = "5:4"
    RATIO_21_9 = "21:9"

def crop_image_to_aspect_ratio(img: Image.Image, aspect_ratio: str) -> Image.Image:
    """Crop image to target aspect ratio"""
    aspect_map = {
        "1:1": 1.0,
        "2:3": 2/3,
        "3:2": 3/2,
        "16:9": 16/9,
        "9:16": 9/16,
        "4:3": 4/3,
        "3:4": 3/4,
        "4:5": 4/5,
        "5:4": 5/4,
        "21:9": 21/9,
    }
    
    target_ratio = aspect_map.get(aspect_ratio, 1.0)
    current_ratio = img.width / img.height
    
    if abs(current_ratio - target_ratio) < 0.01:
        return img
    
    if current_ratio > target_ratio:
        # Image is too wide, crop width
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # Image is too tall, crop height
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))
    
    return img

async def populate_prompt_with_flash(image_paths: List[str], template_prompt: str) -> str:
    """
    Stage 1: Use Gemini 2.5 Flash to analyze images and populate prompt template.
    Replaces [VEHICLE_MAKE_MODEL_YEAR] and [VISIBLE_MODIFICATIONS] with actual details.
    """
    client = get_google_client()
    
    # Meta-prompt that instructs Flash to fill in the template
    meta_prompt = """Analyze the input image and use it to replace the bracketed example descriptors in the prompt below with accurate, image-grounded descriptions of the vehicle shown. Replace only the text inside square brackets [...]. Do not change sentence structure, ordering, or wording outside those brackets. Do not add new descriptions or remove any constraints. Do not mention tools, models, or reasoning. Return the full prompt with the bracketed descriptors replaced.

Prompt to Populate:

""" + template_prompt
    
    # Load images
    contents = [meta_prompt]
    for img_path in image_paths:
        img = Image.open(img_path)
        contents.append(img)
    
    logger.info("Stage 1: Analyzing images with Gemini 2.5 Flash to populate prompt template...")
    logger.info("=" * 80)
    logger.info("STAGE 1 PROMPT (Meta-prompt for Flash):")
    logger.info("-" * 80)
    logger.info(meta_prompt)
    logger.info("=" * 80)
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3-flash-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
                temperature=0.1,
            ),
        )
        
        # Extract text response
        populated_prompt = response.text.strip()
        logger.info(f"✓ Prompt populated with vehicle details")
        logger.info("=" * 80)
        logger.info("STAGE 1 OUTPUT (Populated Prompt):")
        logger.info("-" * 80)
        logger.info(populated_prompt)
        logger.info("=" * 80)
        
        return populated_prompt
        
    except Exception as e:
        logger.error(f"Failed to populate prompt with Flash: {e}")
        logger.warning("Falling back to original template prompt")
        return template_prompt

async def generate_image(
    prompt: str,
    image_paths: List[str],
    output_path: str,
    aspect_ratio: AspectRatio = AspectRatio.RATIO_3_2,
    output_format: OutputFormat = OutputFormat.PNG,
    model_name: str = "gemini-3-pro-image-preview",
    image_size: str = "2K",
    temperature: float = None,
    use_two_stage: bool = True,
) -> Dict[str, Any]:
    """
    Generate image using Google Gemini with optional two-stage process.
    
    If use_two_stage=True:
      Stage 1: Flash analyzes images and populates prompt template with vehicle details
      Stage 2: Pro generates contact sheet with populated prompt + images
    """
    
    output_format_str = (output_format.value if not isinstance(output_format, str) else output_format).lower()
    if output_format_str == "jpg":
        output_format_str = "jpeg"
    aspect_ratio_str = aspect_ratio.value if not isinstance(aspect_ratio, str) else aspect_ratio
    
    try:
        start_time = time.perf_counter()
        
        # Get Gemini client
        client = get_google_client()
        
        # Stage 1: Populate prompt with Flash (if enabled and template has placeholders)
        final_prompt = prompt
        if use_two_stage and "[VEHICLE_MAKE_MODEL_YEAR]" in prompt:
            final_prompt = await populate_prompt_with_flash(image_paths, prompt)
        
        # Stage 2: Generate image with Pro
        # Load images as PIL Image objects
        contents = [final_prompt]
        for img_path in image_paths:
            img = Image.open(img_path)
            contents.append(img)
        
        # Build config with image settings
        config_params = {
            "response_modalities": ["IMAGE"],
            "image_config": types.ImageConfig(
                aspect_ratio=aspect_ratio_str,
                image_size=image_size
            ),
        }
        
        if temperature is not None:
            config_params["temperature"] = temperature
        
        config = types.GenerateContentConfig(**config_params)
        
        logger.info(f"Stage 2: Generating image with {model_name} at {image_size} resolution ({aspect_ratio_str})...")
        logger.info("=" * 80)
        logger.info("STAGE 2 PROMPT (Final prompt for image generation):")
        logger.info("-" * 80)
        logger.info(final_prompt)
        logger.info("=" * 80)
        
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.warning(f"Gemini call failed: {e}, retrying with flash model...")
            
            # Fallback to flash model
            model_name = "gemini-2.5-flash-image"
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio_str,
                    image_size="1K"  # Flash doesn't support 2K
                ),
            )
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config,
            )
        
        # Extract image from response
        if not response:
            logger.error("Response is None or empty")
            raise ValueError("No response from Gemini API")
        
        if not hasattr(response, 'parts'):
            logger.error(f"Response has no 'parts' attribute. Response type: {type(response)}, dir: {dir(response)}")
            raise ValueError("Response missing 'parts' attribute")
        
        if response.parts is None:
            logger.error(f"Response.parts is None. Response: {response}")
            # Try to get more info about the response
            if hasattr(response, 'candidates') and response.candidates:
                logger.info(f"Response has candidates: {response.candidates}")
            if hasattr(response, 'prompt_feedback'):
                logger.info(f"Prompt feedback: {response.prompt_feedback}")
            raise ValueError("Response.parts is None - image generation may have been blocked or failed")
        
        for part in response.parts:
            if image := part.as_image():
                # Google API returns an Image object, save it directly
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Save the image directly
                await asyncio.to_thread(image.save, output_path)
                
                latency = round(time.perf_counter() - start_time, 3)
                logger.info(f"✓ Image saved to {output_path} ({latency}s, {image_size} resolution)")
                
                return {
                    "success": True,
                    "path": output_path,
                    "latency": latency,
                    "model": model_name,
                }
        
        raise ValueError("No image data found in response")
        
    except Exception as e:
        logger.exception("Error generating image", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }

# ============================================================================
# IMGBB IMAGE HOSTING
# ============================================================================

async def upload_to_imgbb(image_path: str) -> str:
    """
    Upload image to ImgBB and return public URL.
    ImgBB provides free image hosting with public URLs.
    """
    if not IMGBB_API_KEY:
        raise ValueError("IMGBB_API_KEY is not configured in .env file. Get one free at https://api.imgbb.com/")
    
    import base64
    
    # Check image dimensions before upload
    img = Image.open(image_path)
    logger.info(f"Image {Path(image_path).name}: {img.width}x{img.height} ({img.mode})")
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        img_bytes = f.read()
    
    b64_image = base64.b64encode(img_bytes).decode('utf-8')
    
    # Upload to ImgBB
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": b64_image,
    }
    
    logger.info(f"Uploading {Path(image_path).name} to ImgBB...")
    
    def _upload():
        response = requests.post(url, data=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    
    try:
        result = await asyncio.to_thread(_upload)
        
        if result.get("success"):
            image_url = result["data"]["url"]
            logger.info(f"✓ Uploaded to ImgBB: {image_url}")
            return image_url
        else:
            raise Exception(f"ImgBB upload failed: {result}")
            
    except Exception as e:
        logger.error(f"Failed to upload to ImgBB: {e}")
        raise

# ============================================================================
# HIGGSFIELD/KLING VIDEO GENERATION
# ============================================================================

DEFAULT_MODEL_PATH = "kling-video/v2.6/pro/image-to-video"
DEFAULT_DURATION_SECONDS = 5
MAX_RETRIES = 3

class VideoGenerationError(Exception):
    """Raised when video generation fails after retries."""

def _build_endpoint(model_name: str) -> str:
    """Build the Higgsfield endpoint for the given model path."""
    if model_name.startswith("http://") or model_name.startswith("https://"):
        return model_name
    return f"https://platform.higgsfield.ai/{model_name.lstrip('/')}"

async def _download_bytes(url: str, *, timeout: int = 180) -> bytes:
    """Download binary content."""
    def _fetch() -> bytes:
        resp = requests.get(url, stream=True, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    
    return await asyncio.to_thread(_fetch)

async def _submit_generation_request(
    start_image_path: str,
    prompt: str,
    end_image_path: Optional[str],
    duration_seconds: int,
    api_key: str,
    api_secret: str,
    model_name: str,
) -> Dict[str, Any]:
    """Submit a generation request to Higgsfield."""
    
    logger.info(f"Submitting generation to Higgsfield: {model_name}")
    
    # Upload images to ImgBB to get public URLs
    start_image_url = await upload_to_imgbb(start_image_path)
    
    payload: Dict[str, Any] = {
        "image_url": start_image_url,
        "prompt": prompt,
        "duration": duration_seconds,
        "cfg_scale": 0.5,
        "negative_prompt": "text, watermark, copyright, blur, low quality, distortion, abstract, weird, deformed",
    }
    
    if end_image_path:
        end_image_url = await upload_to_imgbb(end_image_path)
        payload["last_image_url"] = end_image_url
    
    headers = {
        "Content-Type": "application/json",
        "hf-api-key": api_key,
        "hf-secret": api_secret,
    }
    
    timeout = aiohttp.ClientTimeout(total=300)
    endpoint = _build_endpoint(model_name)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(endpoint, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "success": True,
                    "status_url": data.get("status_url"),
                    "request_id": data.get("request_id"),
                }
            
            error_text = await response.text()
            if response.status == 403:
                logger.error("Higgsfield API 403 error: %s", error_text)
                if "not enough credits" in error_text.lower():
                    return {"success": False, "error": "insufficient_credits", "details": error_text}
                return {"success": False, "error": "forbidden", "details": error_text}
            
            if response.status >= 500:
                logger.error("Higgsfield API server error: %s", error_text)
                return {"success": False, "error": f"server_error_{response.status}", "details": error_text}
            
            return {"success": False, "error": f"client_error_{response.status}", "details": error_text}

async def _poll_status(
    status_url: str,
    api_key: str,
    api_secret: str,
    model_name: str,
    max_wait_time: int = 900,
) -> Dict[str, Any]:
    """Poll the Higgsfield status endpoint until the video is ready."""
    headers = {
        "Content-Type": "application/json",
        "hf-api-key": api_key,
        "hf-secret": api_secret,
    }
    
    start_time = time.time()
    poll_interval = 2.0
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                return {"success": False, "error": "poll_timeout"}
            
            try:
                async with session.get(status_url, headers=headers) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        status = status_data.get("status")
                        
                        if status == "completed":
                            video_info = status_data.get("video") or {}
                            video_url = video_info.get("url")
                            if video_url:
                                return {"success": True, "video_url": video_url}
                            return {"success": False, "error": "missing_video_url"}
                        
                        if status == "failed":
                            return {"success": False, "error": status_data.get("error", "generation_failed")}
                        
                        poll_interval = min(poll_interval * 1.2, 10)
                        await asyncio.sleep(poll_interval)
                        continue
                    
                    if response.status >= 500:
                        await asyncio.sleep(poll_interval)
                        continue
                    
                    error_text = await response.text()
                    return {"success": False, "error": f"poll_error_{response.status}", "details": error_text}
            except (asyncio.TimeoutError, aiohttp.ClientError):
                await asyncio.sleep(poll_interval)
                continue
            except Exception as exc:
                return {"success": False, "error": f"unexpected_poll_error: {exc}"}

async def _generate_higgsfield_video(
    prompt: str,
    start_image_path: str,
    end_image_path: Optional[str],
    output_path: str,
    duration_seconds: int,
    model_name: str,
) -> Dict[str, Any]:
    """Generate a single video segment using Higgsfield (Kling 2.5 Turbo)."""
    
    api_key_primary = HIGGSFIELD_API_KEY
    api_secret_primary = HIGGSFIELD_API_SECRET or ""
    api_key_secondary = HIGGSFIELD_API_KEY2
    api_secret_secondary = HIGGSFIELD_API_SECRET2 or ""
    
    if not api_key_primary:
        raise VideoGenerationError("HIGGSFIELD_API_KEY is not configured in .env")
    
    credentials = [
        (api_key_primary, api_secret_primary),
        (api_key_secondary, api_secret_secondary),
    ]
    credentials = [(k, s) for (k, s) in credentials if k]
    
    start_time = time.perf_counter()
    cred_index = 0
    attempt = 1
    
    while attempt <= MAX_RETRIES and cred_index < len(credentials):
        api_key, api_secret = credentials[cred_index]
        
        submit_result = await _submit_generation_request(
            start_image_path=start_image_path,
            prompt=prompt,
            end_image_path=end_image_path,
            duration_seconds=duration_seconds,
            api_key=api_key,
            api_secret=api_secret,
            model_name=model_name,
        )
        
        if not submit_result.get("success"):
            error = submit_result.get("error", "unknown_submit_error")
            details = submit_result.get("details")
            logger.warning("Higgsfield submit failed (%s): %s", error, details)
            
            if error == "insufficient_credits" and cred_index + 1 < len(credentials):
                cred_index += 1
                logger.info("Switching to secondary Higgsfield credentials.")
                continue
            
            if error.startswith("server_error") and attempt < MAX_RETRIES:
                attempt += 1
                await asyncio.sleep(2 ** (attempt - 1))
                continue
            
            raise VideoGenerationError(details or error)
        
        status_url = submit_result.get("status_url")
        if not status_url:
            raise VideoGenerationError("Missing status_url in Higgsfield response")
        
        poll_result = await _poll_status(
            status_url=status_url,
            api_key=api_key,
            api_secret=api_secret,
            model_name=model_name,
        )
        
        if not poll_result.get("success"):
            error = poll_result.get("error", "unknown_poll_error")
            details = poll_result.get("details")
            logger.warning("Higgsfield poll failed (%s): %s", error, details)
            
            if error == "poll_timeout" and attempt < MAX_RETRIES:
                attempt += 1
                continue
            
            if error.startswith("poll_error_") and attempt < MAX_RETRIES:
                attempt += 1
                await asyncio.sleep(2 ** (attempt - 1))
                continue
            
            raise VideoGenerationError(details or error)
        
        video_url = poll_result.get("video_url")
        if not video_url:
            raise VideoGenerationError("Video URL missing from completed job")
        
        # Download video and save locally
        video_bytes = await _download_bytes(video_url)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(video_bytes)
        
        latency = round(time.perf_counter() - start_time, 3)
        logger.info(f"Video saved to {output_path} ({latency}s)")
        
        return {
            "success": True,
            "path": output_path,
            "latency": latency,
            "duration_seconds": duration_seconds,
        }
    
    raise VideoGenerationError("Failed to generate video after retries")

async def generate_higgsfield(
    prompt: str,
    start_image_path: str,
    end_image_path: Optional[str],
    output_path: str,
    duration_seconds: int = DEFAULT_DURATION_SECONDS,
    model_name: str = DEFAULT_MODEL_PATH,
) -> Dict[str, Any]:
    """Public API to generate a single video segment using Higgsfield/Kling."""
    
    try:
        duration = int(duration_seconds) if duration_seconds else DEFAULT_DURATION_SECONDS
    except (TypeError, ValueError):
        duration = DEFAULT_DURATION_SECONDS
    
    try:
        return await _generate_higgsfield_video(
            prompt=prompt,
            start_image_path=start_image_path,
            end_image_path=end_image_path,
            output_path=output_path,
            duration_seconds=duration,
            model_name=model_name,
        )
    except Exception as exc:
        logger.exception("Error generating video after retries", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }

# ============================================================================
# AUTOMOTIVE PROMPT TEMPLATE
# ============================================================================

AUTOMOTIVE_PROMPT_TEMPLATE = """Analyze the input image and use it to replace the bracketed example descriptors in the prompt below with accurate, image-grounded descriptions of the vehicle shown.

Replace only the text inside square brackets [...].

Do not change sentence structure, ordering, or wording outside those brackets.

Do not add new descriptions or remove any constraints.

Do not mention tools, models, or reasoning.

Return the full prompt with the bracketed descriptors replaced.

Prompt to Populate

Analyze the input image and silently inventory all automotive-critical details: the specific vehicle make, model, and year ([VEHICLE_MAKE_MODEL_YEAR]), custom modifications ([VISIBLE_MODIFICATIONS]), tire tread design, interior visibility through glass, engineering details, light direction, and reflection quality.

The setting is a pristine, high-budget automotive photography studio. A massive softbox downlight (large diffusion bank) hangs directly overhead, creating long, clean highlights on the vehicle. The background is a seamless, dark studio cyclorama. Outside the area with the car it is extremely dark, with the walls of the studio only faintly visible. Render the vehicle with hyper-realistic detail, capturing the precise texture of the materials, distinct mechanical components, and accurate light reflections.

The vehicle’s body color, wheel color, and all material colors must exactly match the input image, with no reinterpretation, correction, enhancement, or stylization. Color fidelity must be exact and consistent across all frames.

All vehicle details, styling, modifications, lighting, environment, and color grade must remain 100% unchanged across all frames. There must be NO human model present in any frame. Do not reinterpret materials or colors. Do not output any reasoning.

All frames must contain NO written text, labels, captions, UI elements, watermarks, or annotations of any kind.

Your visible output must be:

One 3×3 contact sheet image (9 frames).

Required 9-Frame Automotive Shot List

1. Low-Angle Front "Hero" Stance (Aggressive, Wide Lens)

Lens: Wide-angle (18–24 mm equivalent)

Framing: Front three-quarter, full vehicle in frame

Camera positioned very low to the studio floor at the front three-quarter view. This perspective exaggerates the front bumper, headlights, and wide stance of the car, making it appear dominant and aggressive. The massive overhead softbox creates long, sleek highlight lines across the hood and roof.

2. High-Angle Rear Quarter Abstract (Geometric, Sculptural)

Lens: Wide-angle (24–28 mm equivalent)

Framing: Rear quarter, cropped mid-body to roofline

Camera positioned high overhead, looking down sharply at the rear quarter and [REAR_BODY_FEATURES]. This frame emphasizes the vehicle’s rear geometry, rear glass curvature, and any visible aero elements against the dark studio floor.

3. Ultra-Low "Worm's Eye" Profile (Speed, Texture)

Lens: Wide-angle (20–24 mm equivalent)

Framing: Side profile with extreme foreground emphasis

Camera placed practically on the ground, looking along the side profile of the car from just behind the front wheel towards the rear. The front wheel and tire dominate the immediate foreground, showing [WHEEL_TIRE_AND_BRAKE_DETAILS], while the rest of the car body stretches away into the distance, emphasizing length and ride height.

4. Wide Environmental Studio Frame (Scale, Production Value)

Lens: Ultra-wide (14–18 mm equivalent)

Framing: Full vehicle small in frame with environment dominant

Camera positioned very wide and far back, capturing the entire vehicle small within the vastness of the studio. This shot must include the massive overhead diffusion bank hanging above the car, showing the scale of the lighting setup against the seamless dark cyclorama infinity background.

5. The "Driver's Line" Abstract (Curvature, Reflection)

Lens: Standard (35–50 mm equivalent)

Framing: Tight longitudinal crop along hood and fender

Camera positioned near the base of the windshield (cowl area), looking forward down the length of the hood and front fender curve. This angle focuses on body curvature and the precise reflection of the overhead light source on the vehicle’s paint surface.

6. Macro Engineering Detail (Texture, Precision)

Lens: True macro (90–105 mm equivalent)

Framing: Extreme close-up, single component fills frame

Extreme close-up macro shot focusing on a specific, intricate detail visible in the image — [MACRO_DETAIL]. The focus must be razor-sharp on the metallic, glass, or composite textures.

7. Overhead Centerline Top-Down (Symmetry, Geometry)

Lens: Moderate wide (28–35 mm equivalent)

Framing: Full vehicle centered, top-down orthographic feel

Camera positioned directly above the vehicle on the longitudinal centerline, looking straight down. This frame emphasizes symmetry, roofline geometry, hood alignment, and the graphic silhouette of the vehicle against the dark cyclorama floor.

8. Rear Low-Centerline Compression (Width, Power)

Lens: Short telephoto (70–85 mm equivalent)

Framing: Rear view, tightly framed horizontally

Camera positioned low and centered behind the vehicle. This compressed perspective emphasizes rear track width, bumper mass, and lower body volume, isolating the car from the surrounding darkness.

9. Front Corner Surface Study (Surface Transition, Light Falloff)

Lens: Short telephoto (85–100 mm equivalent)

Framing: Tight three-quarter detail crop

Camera positioned close to the front corner of the vehicle, angled obliquely across the headlight, fender edge, and hood seam. This frame emphasizes panel transitions, surface curvature, and controlled light falloff across the paint.

Continuity & Technical Requirements

Maintain perfect vehicle fidelity in every frame: exact paint, exact wheel finish, exact materials, modifications, tires, and cleanliness.

Environment, textures, and massive overhead lighting source must remain consistent.

Depth of field shifts naturally with focal length (deep for wide/environmental shots, shallow for telephoto, very shallow for macro).

Photoreal textures and physically plausible light behavior (especially metallic paint reflections and glass refractions) required.

Frames must feel like different high-end camera placements within the same shoot.

All keyframes must be the exact same aspect ratio, and exactly 9 keyframes should be output. Maintain the exact visual style in all keyframes: shot on Fuji Velvia film with a hard light source creating high contrast, overexposed highlights showing significant film grain, and oversaturated colors.

Output Format

A) 3×3 Contact Sheet Image
"""

# ============================================================================
# CAMERA MOVEMENT PROMPTS
# ============================================================================

CAMERA_PROMPTS = [
    "The camera very smoothly and slowly orbits while pushing in on the car. The car is completely still. The car does not move in any way.",
    "The camera very smoothly and slowly lifts on a boom to view the car from a bird's eye view. The car is completely still.",
    "The camera very smoothly and slowly lowers on a boom while orbiting to the rear of the car. The car is completely still. The car does not move in any way.",
    "The camera very smoothly and slowly lifts on a boom to view the car from the rear. The car is completely still.",
    "The camera very smoothly and slowly dollies forward along the side of the car. The car is completely still.",
    "The camera very smoothly and slowly lowers on a boom to view the wheel of the car. The car is completely still.",
    "The camera very smoothly and slowly orbits the car to view the front grill. The car is completely still.",
    "The camera very smoothly and slowly dollies out. The car is completely still.",
    "The camera very smoothly and orbits the car then crash zooms out. The car is completely still.",
]

# ============================================================================
# PIPELINE FUNCTIONS
# ============================================================================

def load_images_from_folder(folder_path: str) -> List[str]:
    """Load all image file paths from a folder."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder not found: {folder_path}")
    
    image_files = [str(f) for f in folder.iterdir() if f.suffix.lower() in image_extensions]
    
    if not image_files:
        raise ValueError(f"No image files found in {folder_path}")
    
    logger.info(f"Found {len(image_files)} images in {folder_path}")
    return image_files

def crop_contact_sheet(contact_sheet_path: str, output_dir: str) -> List[str]:
    """Crop a 3x3 contact sheet into 9 individual frames and resize for Kling compatibility."""
    img = Image.open(contact_sheet_path)
    width, height = img.size
    
    frame_width = width // 3
    frame_height = height // 3
    
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    cropped_frames = []
    frame_num = 0
    
    # Kling requires dimensions divisible by 8, with common sizes being:
    # 1024x576 (16:9), 576x1024 (9:16), 768x768 (1:1), 1280x720 (16:9)
    # We'll use 1024x576 (16:9) as it's a good horizontal format for cars
    TARGET_WIDTH = 1024
    TARGET_HEIGHT = 576
    
    for row in range(3):
        for col in range(3):
            frame_num += 1
            left = col * frame_width
            top = row * frame_height
            right = left + frame_width
            bottom = top + frame_height
            
            cropped = img.crop((left, top, right, bottom))
            
            # Resize to Kling-compatible dimensions (1024x576, 16:9)
            # Use LANCZOS for high-quality resizing
            resized = cropped.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
            
            output_path = output_dir_path / f"frame_{frame_num:02d}.png"
            resized.save(output_path, format='PNG')
            cropped_frames.append(str(output_path))
            logger.info(f"Cropped and resized frame {frame_num} to {TARGET_WIDTH}x{TARGET_HEIGHT}: {output_path}")
    
    return cropped_frames

async def generate_videos_from_frames(frame_paths: List[str], output_dir: str) -> List[Dict[str, Any]]:
    """Generate videos using consecutive frames as start/end images with batch concurrency."""
    if len(frame_paths) != 9:
        raise ValueError(f"Expected 9 frames, got {len(frame_paths)}")
    
    videos = []
    
    # Create all video generation tasks
    async def generate_single_video(i: int):
        start_frame = frame_paths[i]
        end_frame = frame_paths[i + 1]
        prompt = CAMERA_PROMPTS[i] if i < len(CAMERA_PROMPTS) else CAMERA_PROMPTS[-1]
        output_path = Path(output_dir) / f"video_segment_{i+1:02d}.mp4"
        
        logger.info(f"Generating video segment {i+1}/8: frame {i+1} -> frame {i+2}")
        logger.info("=" * 80)
        logger.info(f"VIDEO SEGMENT {i+1} PROMPT:")
        logger.info("-" * 80)
        logger.info(prompt)
        logger.info("=" * 80)
        
        return await generate_higgsfield(
            prompt=prompt,
            start_image_path=start_frame,
            end_image_path=end_frame,
            output_path=str(output_path),
            duration_seconds=5,
            model_name="kling-video/v2.6/pro/image-to-video",
        )
    
    # Process videos in batches of 3 for safety
    BATCH_SIZE = 3
    logger.info(f"Generating videos in batches of {BATCH_SIZE} concurrent requests...")
    
    for batch_start in range(0, 8, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, 8)
        batch_indices = range(batch_start, batch_end)
        
        logger.info(f"Starting batch: videos {batch_start+1}-{batch_end}")
        
        # Generate this batch concurrently
        batch_tasks = [generate_single_video(i) for i in batch_indices]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Process results
        for i, result in zip(batch_indices, batch_results):
            if isinstance(result, Exception):
                logger.error(f"Video segment {i+1} failed with exception: {result}")
                videos.append({
                    "success": False,
                    "error": str(result),
                })
            else:
                videos.append(result)
                if result.get("success"):
                    logger.info(f"✓ Video segment {i+1} completed successfully")
                else:
                    logger.error(f"✗ Video segment {i+1} failed: {result.get('error')}")
        
        # Small delay between batches to be extra safe
        if batch_end < 8:
            logger.info(f"Batch complete. Waiting 2 seconds before next batch...")
            await asyncio.sleep(2)
    
    return videos

async def stitch_videos(video_paths: List[str], output_path: str) -> Dict[str, Any]:
    """Stitch multiple videos into one final video using ffmpeg."""
    try:
        import subprocess
        
        logger.info(f"\n[STITCHING] Combining {len(video_paths)} videos into final output...")
        
        # Create a file list for ffmpeg
        list_file = Path(output_path).parent / "ffmpeg_list.txt"
        with open(list_file, 'w') as f:
            for video_path in video_paths:
                # Use absolute paths and escape special characters
                abs_path = Path(video_path).absolute()
                f.write(f"file '{abs_path}'\n")
        
        # Run ffmpeg to concatenate videos
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-c', 'copy',  # Copy codec (fast, no re-encoding)
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        logger.info(f"Running ffmpeg to stitch videos...")
        
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True
        )
        
        # Clean up temp file
        list_file.unlink()
        
        if result.returncode == 0:
            logger.info(f"✓ Final stitched video saved to: {output_path}")
            return {
                "success": True,
                "path": output_path,
            }
        else:
            logger.error(f"ffmpeg failed: {result.stderr}")
            return {
                "success": False,
                "error": f"ffmpeg error: {result.stderr}",
            }
            
    except FileNotFoundError:
        logger.error("❌ ffmpeg not found! Please install ffmpeg to stitch videos.")
        logger.error("   Windows: choco install ffmpeg  OR  download from https://ffmpeg.org/")
        logger.error("   Mac: brew install ffmpeg")
        logger.error("   Linux: sudo apt install ffmpeg")
        return {
            "success": False,
            "error": "ffmpeg not installed",
        }
    except Exception as e:
        logger.exception("Error stitching videos", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }

async def upscale_frames(frame_paths: List[str], output_dir: str) -> List[str]:
    """Upscale individual frames using Gemini image generation."""
    logger.info(f"Upscaling {len(frame_paths)} frames...")
    
    upscale_prompt = "Upscale the image, keep all details of the original image exactly the same."
    
    logger.info("=" * 80)
    logger.info("UPSCALE PROMPT (Used for all frames):")
    logger.info("-" * 80)
    logger.info(upscale_prompt)
    logger.info("=" * 80)
    
    upscaled_paths = []
    
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    for i, frame_path in enumerate(frame_paths, 1):
        output_path = output_dir_path / f"upscaled_frame_{i:02d}.png"
        
        logger.info(f"Upscaling frame {i}/{len(frame_paths)}...")
        
        result = await generate_image(
            prompt=upscale_prompt,
            image_paths=[frame_path],
            output_path=str(output_path),
            aspect_ratio=AspectRatio.RATIO_3_2,
            output_format=OutputFormat.PNG,
            model_name="gemini-3-pro-image-preview",
            image_size="2K",
            use_two_stage=False,  # No need for two-stage on upscale
        )
        
        if result.get("success"):
            upscaled_paths.append(str(output_path))
            logger.info(f"✓ Frame {i} upscaled successfully")
        else:
            logger.warning(f"✗ Frame {i} upscale failed: {result.get('error')}, using original frame")
            upscaled_paths.append(frame_path)
    
    return upscaled_paths

async def process_car_images(
    input_folder: str,
    output_dir: str = "./output",
) -> Dict[str, Any]:
    """Main pipeline function."""
    logger.info("=" * 80)
    logger.info("Starting Car Video Generation Pipeline - LOCAL STORAGE")
    logger.info("=" * 80)
    
    # Step 1: Load input images
    logger.info("\n[STEP 1] Loading car images from folder...")
    car_image_paths = load_images_from_folder(input_folder)
    
    # Step 2: Generate contact sheet with Gemini 3 Pro
    logger.info("\n[STEP 2] Generating 3x3 contact sheet with Gemini 3 Pro Image Preview...")
    logger.info("=" * 80)
    logger.info("CONTACT SHEET BASE TEMPLATE PROMPT:")
    logger.info("-" * 80)
    logger.info(AUTOMOTIVE_PROMPT_TEMPLATE[:500] + "..." if len(AUTOMOTIVE_PROMPT_TEMPLATE) > 500 else AUTOMOTIVE_PROMPT_TEMPLATE)
    logger.info("=" * 80)
    
    contact_sheet_path = Path(output_dir) / "contact_sheet.png"
    
    contact_sheet_result = await generate_image(
        prompt=AUTOMOTIVE_PROMPT_TEMPLATE,
        image_paths=car_image_paths,
        output_path=str(contact_sheet_path),
        aspect_ratio=AspectRatio.RATIO_3_2,
        output_format=OutputFormat.PNG,
        model_name="gemini-3-pro-image-preview",
        image_size="2K",
    )
    
    if not contact_sheet_result.get("success"):
        error_msg = contact_sheet_result.get("error", "Unknown error")
        logger.error(f"Failed to generate contact sheet: {error_msg}")
        return {"error": error_msg}
    
    logger.info(f"Contact sheet saved: {contact_sheet_path}")
    
    # Step 3: Crop contact sheet
    logger.info("\n[STEP 3] Cropping contact sheet into 9 frames...")
    frames_dir = Path(output_dir) / "frames"
    frame_paths = crop_contact_sheet(str(contact_sheet_path), str(frames_dir))
    
    # Step 4: Upscale frames
    logger.info("\n[STEP 4] Upscaling frames to 2K resolution (3:2 aspect ratio)...")
    upscaled_dir = Path(output_dir) / "upscaled_frames"
    upscaled_frame_paths = await upscale_frames(frame_paths, str(upscaled_dir))
    
    # Step 5: Generate videos
    logger.info("\n[STEP 5] Generating 8 video segments with Kling 2.5-turbo...")
    videos_dir = Path(output_dir) / "videos"
    videos = await generate_videos_from_frames(upscaled_frame_paths, str(videos_dir))
    
    # Step 6: Stitch videos into final output
    successful_video_paths = [v.get("path") for v in videos if v.get("success") and v.get("path")]
    
    final_video_path = None
    if successful_video_paths:
        logger.info(f"\n[STEP 6] Stitching {len(successful_video_paths)} videos into final output...")
        final_video_path = Path(output_dir) / "final_video.mp4"
        stitch_result = await stitch_videos(successful_video_paths, str(final_video_path))
        
        if not stitch_result.get("success"):
            logger.warning(f"Video stitching failed: {stitch_result.get('error')}")
            logger.warning("Individual video segments are still available in the videos/ folder")
            final_video_path = None
    else:
        logger.warning("No successful videos to stitch!")
    
    logger.info("\n" + "=" * 80)
    logger.info("Pipeline Complete!")
    logger.info("=" * 80)
    
    return {
        "contact_sheet_path": str(contact_sheet_path),
        "frame_paths": frame_paths,
        "upscaled_frame_paths": upscaled_frame_paths,
        "videos": videos,
        "final_video_path": str(final_video_path) if final_video_path else None,
        "summary": {
            "total_frames": len(frame_paths),
            "total_videos": len(videos),
            "successful_videos": sum(1 for v in videos if v.get("success")),
            "failed_videos": sum(1 for v in videos if not v.get("success")),
        }
    }

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Example usage"""
    if len(sys.argv) < 2:
        print("Usage: python car_video_pipeline.py <input_folder> [output_dir]")
        print("Example: python car_video_pipeline.py ./car_images ./output")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
    
    result = await process_car_images(input_folder, output_dir)
    
    if "error" in result:
        print(f"\nERROR: {result['error']}")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Contact Sheet: {result.get('contact_sheet_path')}")
    
    if result.get('final_video_path'):
        print(f"\n🎬 FINAL VIDEO: {result.get('final_video_path')}")
    
    print(f"\nFrames ({len(result.get('frame_paths', []))}):")
    for i, path in enumerate(result.get('frame_paths', []), 1):
        print(f"  Frame {i}: {path}")
    
    print(f"\nUpscaled Frames ({len(result.get('upscaled_frame_paths', []))}):")
    for i, path in enumerate(result.get('upscaled_frame_paths', []), 1):
        print(f"  Upscaled Frame {i}: {path}")
    
    print(f"\nVideos ({len(result.get('videos', []))}):")
    for i, video in enumerate(result.get('videos', []), 1):
        if video.get('success'):
            print(f"  Video {i}: {video['path']}")
        else:
            error = video.get('error', 'Unknown error')
            print(f"  Video {i}: FAILED - {error}")
    
    print(f"\nSummary:")
    print(f"  Total Frames: {result['summary']['total_frames']}")
    print(f"  Total Videos: {result['summary']['total_videos']}")
    print(f"  Successful: {result['summary']['successful_videos']}")
    print(f"  Failed: {result['summary']['failed_videos']}")
    
    if result.get('final_video_path'):
        print(f"\n✅ Complete showcase video: {result.get('final_video_path')}")
    else:
        print(f"\n⚠️  Final video not created (check if ffmpeg is installed)")
    
    print(f"\nAll outputs saved to: {output_dir}/")

if __name__ == "__main__":
    asyncio.run(main())