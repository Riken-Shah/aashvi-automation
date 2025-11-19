import traceback
from utils import get_gspread_client, send_images_to_bot, send_messages
from automation import v1_generate_story_idea, get_location
from datetime import datetime


if __name__ == '__main__':
    gsheet = get_gspread_client()
    image_urls = []
    i = 0
    posted_on_instagram = gsheet.find("posted_on_instagram")
    for row in gsheet.get_all_records(value_render_option="FORMULA"):
        if row["type"] == "story" and row["posted_on_instagram"] == "" and row["image"] != "":
            image_url = row["image"]
            print(image_url)
            image_urls.append(image_url.replace("=IMAGE(\"", "").replace("\", 4, 120, 120)", ""))
            i += 1
            gsheet.update_cell(row["index"]+1, posted_on_instagram.col,
                               datetime.now().strftime("%Y-%m-%d %H:%M"))
            print(f"Story on instagram for {row['index']} row")
            if i == 4:
                break
    if i == 0:
        send_messages("No stories to post, please check the sheet")
    else:
        send_images_to_bot(f"Hey! It's been 3 hours, post a story for {get_location()} ", image_urls)
    try:
        v1_generate_story_idea()
    except Exception as e:
        print(e)
        send_messages(f"Error generating story idea: {e} \n {traceback.print_exc()}")
