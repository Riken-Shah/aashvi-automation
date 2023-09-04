import requests
from automation import AUTOMATIC1111_URL, check_if_automatic1111_is_active
import traceback
import json
from utils import creds, get_gspread_client, send_messages
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from googleapiclient.http import MediaIoBaseDownload
import io

service = build('drive', 'v3', credentials=creds)
file_name_to_id_map = {}
file_name_to_mask_map = {}
file_name_to_skin_mask_map = {}
gsheet = get_gspread_client()

ROOT_DIR = "/Users/rikenshah/Desktop/Fun/insta-model/"


def download_images(folder_id, save_path, to_map):
    try:
        files = []
        page_token = None
        # Download Queued Images
        while True:
            # pylint: disable=maybe-no-member
            response = service.files().list(q=f"'{folder_id}' in parents",
                                            spaces='drive',
                                            fields='nextPageToken, '
                                                   'files(id, name)',
                                            pageToken=page_token).execute()
            for file in response.get('files', []):
                # Process change
                to_map[file.get("name")] = file.get("id")
                print(F'Found file: {file.get("name")}, {file.get("id")}')
                file_id = file.get("id")
                try:
                    request = service.files().get_media(fileId=file_id)
                    img = io.BytesIO()
                    downloader = MediaIoBaseDownload(img, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        print(F'Download {int(status.progress() * 100)}.')
                        with open(save_path + file.get("name"), "wb") as f:
                            # print(img.getvalue(), file=f)
                            f.write(img.getvalue())
                except HttpError as error:
                    print(F'An error occurred: {error}')

            file = None
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    except HttpError as error:
        print(F'An error occurred: {error}')
        files = None


from googleapiclient.http import MediaFileUpload


def upload_image_to_drive(filename, folder_id, DIR):
    try:
        # create the file metadata
        file_metadata = {'name': filename.replace(DIR, ""), 'parents': [folder_id]}
        m = MediaFileUpload(filename, mimetype='image/png')

        # upload the image data
        media = service.files().create(body=file_metadata, media_body=m, fields='id',
                                       media_mime_type="image/png").execute()

        # get the file ID and public URL of the uploaded image
        file_id = media.get('id')

        return f"https://drive.google.com/uc?export=view&id={file_id}"
    except Exception as e:
        print(f'An error occurred: {e}')

    return ""


def move_file_to_folder(file_id, folder_id):
    """Move specified file to the specified folder.
    Args:
        file_id: Id of the file to move.
        folder_id: Id of the folder
    Print: An object containing the new parent folder and other meta data
    Returns : Parent Ids for the file

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """

    try:

        # pylint: disable=maybe-no-member
        # Retrieve the existing parents to remove
        file = service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        # Move the file to the new folder
        file = service.files().update(fileId=file_id, addParents=folder_id,
                                      removeParents=previous_parents,
                                      fields='id, parents').execute()
        return file.get('parents')

    except HttpError as error:
        print(F'An error occurred: {error}')
        return None


def face_fix_process():
    IMAGE_FILES = [i for i in os.listdir(ROOT_DIR + "raw/")]
    print("found images: ", IMAGE_FILES)
    for image in IMAGE_FILES:
        # avoid if file already exists
        # if os.path.exists(f"./final/{image}"):
        #     continue
        original_img_path = f"{ROOT_DIR}raw/{image}"
        mask_path = f"{ROOT_DIR}mask/{image}"
        original_image_base64 = None
        mask_base64 = None
        name, ext = image.split(".")
        is_img_from_xcel = name.isnumeric()

        try:
            with open(original_img_path, "rb") as img_file:
                original_image_base64 = base64.b64encode(img_file.read()).decode()
            with open(mask_path, "rb") as img_file:
                mask_base64 = base64.b64encode(img_file.read()).decode()
        except Exception as e:
            print(e)
            continue
        # Call Img2Img API with image and mask
        headers = {'Content-Type': 'application/json'}

        body = {
            "prompt": "a beautiful and cute aashvi-500, detailed skin, white skin, cloudy eyes, thick long haircut, light skin, "
                      "(high detailed skin:1.3), 8k UHD DSLR, bokeh effect, soft lighting, high quality",
            # "enable_hr": True,
            # "hr_resize_x": 1080,
            # "hr_resize_y": 1080,
            # "hr_upscaler": "R-ESRGAN 4x+",
            "denoising_strength": 0.8 if is_img_from_xcel else 0.85,
            "mask_blur": 18 if is_img_from_xcel else 15,
            # "hr_second_pass_steps": 20,
            "seed": -1,
            "sampler_index": "DPM++ 2M Karras",
            "batch_size": 1,
            "n_iter": 1,
            "steps": 140 if is_img_from_xcel else 180,
            "cfg_scale": 3,
            "width": 512,
            "height": 512,
            "restore_faces": True,
            "negative_prompt": "fingers, dress, (deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, "
                               "drawing, anime:1.4), text, close up, cropped, out of frame, worst quality, low quality, "
                               "jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, mutated hands, "
                               "poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, "
                               "bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, "
                               "malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, "
                               "too many fingers, long neck",
            "send_images": True,
            "save_images": False,
            "mask": mask_base64,
            "init_images": [original_image_base64],
            "include_init_images": True,
            "alwayson_scripts": {
                "controlnet": {
                    "args": [
                        {"input_image": original_image_base64,
                         "module": "openpose_face",
                         "model": "control_v11p_sd15_openpose [cab727d4]", }
                    ]
                }
            }
        }
        x = json.dumps(body)
        print(AUTOMATIC1111_URL)
        resp = requests.post(AUTOMATIC1111_URL + "sdapi/v1/img2img", data=x, headers=headers, ).json()
        img_data = resp['images'][0]
        # save image
        img_data = base64.b64decode(img_data)
        with open(f"{ROOT_DIR}final/{image}", "wb") as fh:
            fh.write(img_data)
            if image in file_name_to_mask_map:
                move_file_to_folder(file_name_to_mask_map[image], "1wVXqsunwblNZDBEMz63_alrdgPWbtA5k")
        if is_img_from_xcel:
            img_fixed = gsheet.find('img_fixed')
            image_cell = gsheet.find("image")
            hyperlink_imge = gsheet.find("hyperlink_image")
            index = gsheet.find(name)
            url = upload_image_to_drive(f"final/{image}", "1rEysVX6M0vEZFYGbdDVc96G4ZBXYhDDs", "final/")
            print("updating tht excel sheet", url)
            gsheet.update_cell(index.row, image_cell.col, f'=IMAGE("{url}", 4, 120, 120)')
            gsheet.update_cell(index.row, hyperlink_imge.col, f'=HYPERLINK("{url}", "Link")')
            gsheet.update_cell(index.row, img_fixed.col, "TRUE")
            if image in file_name_to_id_map:
                move_file_to_folder(file_name_to_id_map[image], "10PtowEawQ-81V4lSkM4K3-r-xQ-T7dW7")


def skin_masks_process():
    IMAGE_FILES = [i for i in os.listdir(f"{ROOT_DIR}raw/")]
    for image_path in IMAGE_FILES:
        # avoid if file already exists
        # if os.path.exists(f"./processed/{image}"):
        #     continue
        original_img_path = f"{ROOT_DIR}final/{image_path}"
        mask_path = f"{ROOT_DIR}skin_masks/{image_path}"
        original_image_base64 = None
        mask_base64 = None
        # image = Image.open(original_img_path)
        # mask = Image.open(mask_path)
        # alpha_mask = ImageOps.invert(image.split()[-1]).convert('L').point(lambda x: 255 if x > 0 else 0, mode='1')
        # mask = ImageChops.lighter(alpha_mask, mask.convert('L')).convert('L')
        # mask.save(f"./skin_masks/{image_path}")
        try:
            with open(original_img_path, "rb") as img_file:
                original_image_base64 = base64.b64encode(img_file.read()).decode()
            with open(mask_path, "rb") as img_file:
                mask_base64 = base64.b64encode(img_file.read()).decode()
        except Exception as e:
            print(e)
            continue
        print(len(original_image_base64), len(mask_base64))
        # Call Img2Img API with image and mask
        headers = {'Content-Type': 'application/json'}
        import cv2

        # body = {
        #     "prompt": "highly detailed, brown skin, match with face, "
        #               "(high detailed skin:1.3), soft lighting, high quality",
        #     # "enable_hr": True,
        #     # "hr_resize_x": 1080,
        #     # "hr_resize_y": 1080,
        #     # "hr_upscaler": "R-ESRGAN 4x+",
        #     "denoising_strength": 0.10,
        #     "mask_blur": 8,
        #     # "hr_second_pass_steps": 20,
        #     "seed": -1,
        #     "sampler_index": "DPM++ 2M Karras",
        #     "batch_size": 1,
        #     "n_iter": 1,
        #     "steps": 140,
        #     "cfg_scale": 9.5,
        #     "width": 512,
        #     "height": 512,
        #     "restore_faces": False,
        #     "negative_prompt": "(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, "
        #                        "drawing, anime:1.4), text, close up, cropped, out of frame, worst quality, low quality, "
        #                        "jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, mutated hands, "
        #                        "poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, "
        #                        "bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, "
        #                        "malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, "
        #                        "too many fingers, long neck",
        #     "send_images": True,
        #     "save_images": False,
        #     "mask": mask_base64,
        #     "init_images": [orignal_image_base64],
        #     "include_init_images": True,
        #     "alwayson_scripts": {
        #         "controlnet": {
        #             "args":[
        #                 {"input_image": orignal_image_base64,
        #                  "module": "openpose_full",
        #                  "model": "control_v11p_sd15_openpose [cab727d4]", }
        # ]
        #         }
        #     }
        # }

        body = {
            "prompt": "detailed skin, light brown skin, cloudy eyes, black hair, thick long haircut, light skin,(high detailed skin:1.3), 8k UHD DSLR, bokeh effect, soft lighting, high quality",
            # "enable_hr": True,
            # "hr_resize_x": 1080,
            # "hr_resize_y": 1080,
            # "hr_upscaler": "R-ESRGAN 4x+",
            "denoising_strength": 0.4,
            "mask_blur": 18,
            # "hr_second_pass_steps": 20,
            "seed": -1,
            "sampler_index": "DPM++ 2M Karras",
            "batch_size": 1,
            "n_iter": 1,
            "steps": 150,
            "cfg_scale": 12,
            "width": 512,
            "height": 512,
            "restore_faces": False,
            "negative_prompt": "dress, bra, clothing, (deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, "
                               "drawing, anime:1.4), text, close up, cropped, out of frame, worst quality, low quality, "
                               "jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, mutated hands, "
                               "poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, "
                               "bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, "
                               "malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, "
                               "too many fingers, long neck",
            "send_images": True,
            "save_images": False,
            "mask": mask_base64,
            "init_images": [original_image_base64],
            "include_init_images": True,
            "alwayson_scripts": {
                "controlnet": {
                    "args": [
                        {"input_image": original_image_base64,
                         "module": "openpose_full",
                         "model": "control_v11p_sd15_openpose [cab727d4]", }
                    ]
                }
            }
        }
        x = json.dumps(body)
        resp = requests.post(AUTOMATIC1111_URL + "sdapi/v1/img2img", data=x, headers=headers, ).json()
        img_data = resp['images'][0]
        # save image
        img_data = base64.b64decode(img_data)
        with open(f"{ROOT_DIR}processed/{image_path}", "wb") as fh:
            fh.write(img_data)
            upload_image_to_drive(f"{ROOT_DIR}processed/{image_path}", "1xiEh0AGKjtPhztcqwY27IUC_t0xMzph_",
                                  f"processed/")
            if image_path in file_name_to_id_map:
                move_file_to_folder(file_name_to_id_map[image_path], "10PtowEawQ-81V4lSkM4K3-r-xQ-T7dW7")
            if image_path in file_name_to_skin_mask_map:
                move_file_to_folder(file_name_to_skin_mask_map[image_path], "1JZWascB8Pgv1klKWh3lFOY4-46o3xsX6")


if __name__ == "__main__":
    AUTOMATIC1111_URL = check_if_automatic1111_is_active()
    if not AUTOMATIC1111_URL:
        send_messages("Automatic1111 is not active, please update the url \n Process has been stopped")
        exit(0)

    print(AUTOMATIC1111_URL)
    # delete all the files in the folder
    os.system(f"rm -rf {ROOT_DIR}/raw/*")
    os.system(f"rm -rf {ROOT_DIR}/mask/*")
    os.system(f"rm -rf {ROOT_DIR}/skin_masks/*")
    os.system(f"rm -rf {ROOT_DIR}/processed/*")
    os.system(f"rm -rf {ROOT_DIR}/final/*")
    download_images("1JZNYd_Q30ouTDx76YX4DmEiSb6KI9UFh", f"{ROOT_DIR}/raw/", file_name_to_id_map)
    download_images("1aEJg4sPOyUS63OiaBIjHPeeLnXaJizu2", f"{ROOT_DIR}/mask/", file_name_to_mask_map)
    download_images("1VCaEG3Rs6ZujBFwi1oMn7rbQlR9LlH5I", f"{ROOT_DIR}/skin_masks/", file_name_to_skin_mask_map)
    try:
        face_fix_process()
    except Exception as e:
        print("Error in face fix process", e)
        send_messages(f"Error in face fix process {e} \n {traceback.print_exc()}")

    try:
        skin_masks_process()
    except Exception as e:
        print("Error in skin masks process", e)
        send_messages(f"Error in skin masks process {e} \n {traceback.print_exc()}")
