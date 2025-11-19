"""Application constants and enums.

This module contains all application-level constants, enums, and static values
that should not be configurable through environment variables.
"""

from enum import Enum
from typing import Dict, Any


class ContentType(str, Enum):
    """Content type enumeration."""
    POST = "posts"
    STORY = "story"


class ProcessingStatus(str, Enum):
    """Image processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    """Content approval status enumeration."""
    PENDING = ""
    APPROVED = "y"
    REJECTED = "n"


class PostingStatus(str, Enum):
    """Instagram posting status enumeration."""
    NOT_POSTED = ""
    POSTED = "posted"
    FAILED = "failed"


# Stable Diffusion model configurations
STABLE_DIFFUSION_MODELS = {
    ContentType.POST: {
        "sampler_name": "DPM++ 2M",
        "steps": 120,
        "cfg_scale": 3.5,
        "width": 512,
        "height": 512,
        "restore_faces": True,
    },
    ContentType.STORY: {
        "sampler_name": "DPM++ 2M Karras",
        "steps": 100,
        "cfg_scale": 7,
        "width": 720,
        "height": 1080,
        "restore_faces": True,
    }
}

# Standard negative prompts for different content types
NEGATIVE_PROMPTS = {
    "default": (
        "(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, "
        "sketch, cartoon, drawing, anime:1.4), text, close up, cropped, "
        "out of frame, worst quality, low quality, jpeg artifacts, ugly, "
        "duplicate, morbid, mutilated, extra fingers, mutated hands, "
        "poorly drawn hands, poorly drawn face, mutation, deformed, blurry, "
        "dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, "
        "disfigured, gross proportions, malformed limbs, missing arms, "
        "missing legs, extra arms, extra legs, fused fingers, too many "
        "fingers, long neck"
    ),
    "face_processing": (
        "fingers, dress, (deformed iris, deformed pupils, semi-realistic, "
        "cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), text, "
        "close up, cropped, out of frame, worst quality, low quality, "
        "jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, "
        "mutated hands, poorly drawn hands, poorly drawn face, mutation, "
        "deformed, blurry, dehydrated, bad anatomy, bad proportions, "
        "extra limbs, cloned face, disfigured, gross proportions, "
        "malformed limbs, missing arms, missing legs, extra arms, "
        "extra legs, fused fingers, too many fingers, long neck"
    ),
    "skin_processing": (
        "dress, bra, clothing, (deformed iris, deformed pupils, "
        "semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, "
        "anime:1.4), text, close up, cropped, out of frame, worst quality, "
        "low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, "
        "extra fingers, mutated hands, poorly drawn hands, poorly drawn "
        "face, mutation, deformed, blurry, dehydrated, bad anatomy, "
        "bad proportions, extra limbs, cloned face, disfigured, "
        "gross proportions, malformed limbs, missing arms, missing legs, "
        "extra arms, extra legs, fused fingers, too many fingers, long neck"
    )
}

# Standard prompts for different processing types
STANDARD_PROMPTS = {
    "base_character": (
        "a beautiful and cute aashvi-500, single girl, long haircut, "
        "light skin, (high detailed skin:1.3), 8k UHD DSLR, bokeh effect, "
        "soft lighting, high quality"
    ),
    "face_fix": (
        "a beautiful and cute aashvi-500, detailed skin, white skin, "
        "cloudy eyes, thick long haircut, light skin, (high detailed "
        "skin:1.3), 8k UHD DSLR, bokeh effect, soft lighting, high quality"
    ),
    "skin_processing": (
        "detailed skin, light brown skin, cloudy eyes, black hair, "
        "thick long haircut, light skin,(high detailed skin:1.3), "
        "8k UHD DSLR, bokeh effect, soft lighting, high quality"
    )
}

# ControlNet model configurations
CONTROLNET_MODELS = {
    "openpose_face": "control_v11p_sd15_openpose [cab727d4]",
    "openpose_full": "control_v11p_sd15_openpose [cab727d4]"
}

# Face processing configurations
FACE_PROCESSING_CONFIG = {
    "excel_images": {
        "denoising_strength": 0.8,
        "mask_blur": 18,
        "steps": 140,
        "cfg_scale": 3
    },
    "regular_images": {
        "denoising_strength": 0.85,
        "mask_blur": 15,
        "steps": 180,
        "cfg_scale": 3
    }
}

# Skin processing configuration
SKIN_PROCESSING_CONFIG = {
    "denoising_strength": 0.4,
    "mask_blur": 18,
    "steps": 150,
    "cfg_scale": 12
}

# Google Sheets column mappings
SHEET_COLUMNS = [
    "index", "type", "prompt", "location", "group_id", "seed", 
    "image", "generated_on", "caption", "approved", 
    "posted_on_instagram", "hyperlink_image"
]

# Instagram automation selectors and timeouts
INSTAGRAM_SELECTORS = {
    "create_button": "//div[text()='Create']",
    "file_input": "//form/input[@accept='image/jpeg,image/png,image/heic,image/heif,video/mp4,video/quicktime']",
    "next_button": "//div[text()='Next']",
    "caption_area": "//div[@aria-label='Write a caption...']",
    "accessibility_button": "//span[text()='Accessibility']",
    "alt_text_input": "//*[@placeholder='Write alt text...']",
    "location_input": "//*[@name='creation-location-input']",
    "share_button": "//div[text()='Share']",
    "run_anyway_button": "//mwc-button[text()='Run anyway']",
    "yes_button": "//mwc-button[text()='Yes']",
    "connect_without_gpu": "//mwc-button[text()='Connect without GPU']"
}

# Timing constants (in seconds)
TIMING = {
    "page_load": 30,
    "element_wait": 10,
    "file_upload": 5,
    "form_interaction": 2,
    "post_completion": 20,
    "colab_startup": 80,
    "colab_retry": 10
}

# Error messages
ERROR_MESSAGES = {
    "automatic1111_inactive": "Automatic1111 is not active, please update the url",
    "no_posts_to_post": "No posts to post on instagram, please check the sheet",
    "no_stories_to_post": "No stories to post, please check the sheet",
    "missing_values": "Missing required values for content row",
    "image_generation_failed": "Failed to generate image",
    "upload_failed": "Failed to upload image to Google Drive",
    "posting_failed": "Failed to post content to Instagram"
}

# Success messages
SUCCESS_MESSAGES = {
    "image_generated": "Image generated successfully",
    "content_posted": "Successfully posted on instagram, checkout https://www.instagram.com/aashvithemodel",
    "process_completed": "Process completed successfully"
}