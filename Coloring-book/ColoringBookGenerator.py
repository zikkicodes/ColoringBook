import os
import random
import re
import requests
import shutil
import time
import uuid

from PIL import Image
import PyPDF2

from playwright.sync_api import sync_playwright
import eel
import openai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

#isFrontPage = 1
# Set OpenAI API key.
openai.api_key = "sk-"


@eel.expose
def download_upscaled_images(page, prompt_text, isFrontPage):
    print("ENTERING DL")
    try:
        messages = page.query_selector_all(".messageListItem-ZZ7v6g")
        last_four_messages = messages[-4:]
        for message in last_four_messages:
            message_text = message.evaluate_handle('(node) => node.innerText')
            print(f"LAST 4 Messages!: {message_text}")
            message_text = str(message_text)
            print(f"Printing msg txt: {message_text}")
            #print(message_text)
        if 'Custom Zoom' in message_text and 'Web' in message_text:
            print("ENTERING make variations")
            try:
                #last_img = page.query_selector_all('.originalLink-Azwuo9')[0]
                last_image = page.query_selector_all('.originalLink-Azwuo9')[-1]
                second_last_image = page.query_selector_all('.originalLink-Azwuo9')[-2]
                third_last_image = page.query_selector_all('.originalLink-Azwuo9')[-3]
                fourth_last_image = page.query_selector_all('.originalLink-Azwuo9')[-4]

                for image in [last_image, second_last_image, third_last_image, fourth_last_image]:
                    src = image.get_attribute('href')
                    url = src
                    print(f"Printing src: {url}")
                    response = re.sub(r'[^a-zA-Z0-9\s]', '', prompt_text)
                    response = response.replace(',', '_').replace(' ', '_')
                    print(f"response 1: {response}")
                    response = response[:50]
                    print(f"response 2: {response}")
                    r = requests.get(url, stream=True)
                    if isFrontPage == 1:
                        with open(f'coverpage/coverpage{str(response) + str(uuid.uuid1())}.png', 'wb') as out_file:
                            shutil.copyfileobj(r.raw, out_file)
                        del r
                    else:
                        with open(f'dl/{str(response) + str(uuid.uuid1())}.png', 'wb') as out_file:
                            shutil.copyfileobj(r.raw, out_file)
                        del r
            except Exception as e:
                print(f"An error occurred while downloading the images: {e}")
        else:
            print("ENTERING upscaled")
            download_upscaled_images(page, prompt_text)
    except Exception as e:
        print(f"An error occurred while finding the last message: {e}")


@eel.expose
def generate_prompt_and_submit_command(page, prompt, rest_prompt, isFrontPage, aspect_ratio, level, front_prompt):
    try:
        prompt_text = gpt3_midjourney_prompt(prompt, rest_prompt, isFrontPage, aspect_ratio, level, front_prompt)
        time.sleep(random.randint(1, 5))
        pill_value = page.locator('xpath=//*[@id="app-mount"]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[3]/div/main/form/div/div[2]/div/div[2]/div/div/div/span[2]/span[2]')
        pill_value.fill(prompt_text)
        time.sleep(random.randint(1, 5))
        page.keyboard.press("Enter")
        print(f'Successfully submitted prompt: {prompt_text}')
        wait_and_select_upscale_options(page, prompt_text, isFrontPage)
    except Exception as e:
        print(f"An error occurred while submitting the prompt: {e}")


@eel.expose
def gpt3_midjourney_prompt(prompt, rest_prompt,isFrontPage, aspect_ratio, level, front_prompt, engine='text-davinci-003', temp=0.7, top_p=1.0, tokens=400, freq_pen=0.0, pres_pen=0.0):
    try:
        if not prompt:
            raise ValueError("Prompt cannot be empty.")
        prompt = prompt.encode(encoding='ASCII', errors='ignore').decode()
        inst = "children's coloring book which has not been colored yet. No shading, No Colors, only thick black outline --ar 9:16"
        openai.api_key = "sk-"
        response = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            temperature=temp,
            max_tokens=tokens,
            top_p=top_p,
            frequency_penalty=freq_pen,
            presence_penalty=pres_pen
        )
        print(f"THIS IS THE RESPONSE {response}")
        if not response.choices:
            raise ValueError("No response from OpenAI API.")
        text = response.choices[0].text.strip()
        if not text:
            raise ValueError("Response text cannot be empty.")
        if isFrontPage == 1:
            return text + front_prompt + " --ar " + aspect_ratio
        else:
            return text + rest_prompt + " level should be " + level + " --ar " + aspect_ratio
    except Exception as e:
        print(f"Error occurred: {e} while generating prompt.")
        return None


@eel.expose
def get_last_message(page):
    messages = page.query_selector_all(".messageListItem-ZZ7v6g")
    last_message = messages[-1]
    last_message_text = last_message.evaluate_handle('(node) => node.innerText')
    last_message_text = str(last_message_text)
    print(last_message_text)
    return last_message_text


@eel.expose
def main(bot_command, channel_url, PROMPT, pgno, rest_prompt, aspect_ratio, level, front_prompt):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.discord.com/login")
        with open("credentials.txt", "r") as f:
            email = f.readline()
            password = f.readline()
        page.fill("input[name='email']", email)
        time.sleep(random.randint(1, 5))
        page.fill("input[name='password']", password)
        time.sleep(random.randint(1, 5))
        page.click("button[type='submit']")
        time.sleep(random.randint(5, 10))
        page.wait_for_url("https://discord.com/channels/@me", timeout=15000)
        print("Successfully logged into Discord.")
        time.sleep(random.randint(1, 5))
        pgno1 = round(int(pgno)/4)
        open_discord_channel(page, channel_url, bot_command, PROMPT, rest_prompt, 1 , aspect_ratio, level, front_prompt)
        for i in range(pgno1):
            open_discord_channel(page, channel_url, bot_command, PROMPT, rest_prompt, 0, aspect_ratio, level, front_prompt)
            print(f"Iteration {i+1} completed.")
            if i == pgno1 - 1:
                images_folder = '/Users/zee/Downloads/coloring-book/dl'
                output_pdf = 'clbook.pdf'
                create_pdf(images_folder, output_pdf)
                folder_path = '/Users/zee/Downloads/coloring-book/coverpage'
                pdf_path = 'clbook.pdf'
                try:
                    concatenate_images_to_pdf(folder_path, pdf_path)
                except Exception as e:
                    print(e)
                #concatenate_images_to_pdf(folder_path, pdf_path)
                print("CREATED BOOK")
                transfer_images("dl", "Collection")
                transfer_images("coverpage", "Collection")


def transfer_images(source_folder, destination_folder, image_extensions=['.jpg', '.jpeg', '.png']):
    try:
        # Create the destination folder if it doesn't exist
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        # List all files in the source folder
        files = os.listdir(source_folder)

        for file in files:
            # Check if the file is an image based on the extension
            if any(file.lower().endswith(ext) for ext in image_extensions):
                source_path = os.path.join(source_folder, file)
                destination_path = os.path.join(destination_folder, file)
                shutil.move(source_path, destination_path)
                print(f"Moved: {file} to {destination_path}")
    except Exception as e:
        print(f"Error occurred: {e}")

def resize_to_letter(image_path):
    image = Image.open(image_path)
    letter_size = (612, 792)  # Letter size in pixels (8.5x11 inches at 72 DPI)
    image.thumbnail(letter_size, Image.ANTIALIAS)
    return image

def concatenate_images_to_pdf(images_folder, pdf_path):
    # Get the list of image files from the folder
    image_files = sorted([f for f in os.listdir(images_folder) if f.endswith('.png') or f.endswith('.jpg')])

    # Make sure there are exactly 4 image files in the folder
    if len(image_files) != 4:
        print("Error: There should be exactly 4 image files in the folder.")
        return

    # Open the PDF file
    with open(pdf_path, "rb") as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        pdf_writer = PyPDF2.PdfWriter()

        # Concatenate the first two images to the first two pages of the PDF
        for i in range(2):
            image_path = os.path.join(images_folder, image_files[i])
            image = resize_to_letter(image_path)
            img_temp = "temp_image_page_{}.pdf".format(i)
            image.save(img_temp, "PDF", resolution=72.0, save_all=True)
            with open(img_temp, "rb") as img_file:
                pdf_writer.add_page(PyPDF2.PdfReader(img_file).pages[0])  # Add the image page

        # Append the remaining pages from the original PDF
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)

        # Concatenate the last two images to the last two pages of the PDF
        for i in range(2, 4):
            image_path = os.path.join(images_folder, image_files[i])
            image = resize_to_letter(image_path)
            img_temp = "temp_image_page_{}.pdf".format(i+2)
            image.save(img_temp, "PDF", resolution=72.0, save_all=True)
            with open(img_temp, "rb") as img_file:
                pdf_writer.add_page(PyPDF2.PdfReader(img_file).pages[0])  # Add the image page

        # Save the final concatenated PDF
        output_pdf_path = "Final_Book.pdf"
        with open(output_pdf_path, "wb") as output_pdf:
            pdf_writer.write(output_pdf)

        # Clean up temporary image PDF files
        for i in range(4):
            os.remove("temp_image_page_{}.pdf".format(i))

    print("PDF concatenation completed. Output saved to 'Final_Book.pdf'.")


def create_pdf(images_folder, output_pdf):
    c = canvas.Canvas(output_pdf, pagesize=letter)

    # Get a list of image files in the folder
    image_files = [f for f in os.listdir(images_folder) if f.endswith('.jpg') or f.endswith('.png')]

    for image_file in image_files:
        image_path = os.path.join(images_folder, image_file)
        c.drawImage(image_path, 0, 0, width=letter[0], height=letter[1], preserveAspectRatio=True, anchor='c')
        c.showPage()

    c.save()

@eel.expose
def open_discord_channel(page, channel_url, bot_command, PROMPT, rest_prompt, isFrontPage, aspect_ratio, level, front_prompt):
    page.goto(f"{channel_url}")
    time.sleep(random.randint(1, 5))
    page.wait_for_load_state("networkidle")
    print("Opened appropriate channel.")
    print("Entering the specified bot command.")
    send_bot_command(page, bot_command, PROMPT, rest_prompt, isFrontPage, aspect_ratio, level, front_prompt)
    return page


@eel.expose
def select_upscale_option(page, option_text):
    page.locator(f"button:has-text('{option_text}')").locator("nth=-1").click()
    print(f"Clicked {option_text} upscale option.")


@eel.expose
def send_bot_command(page, command, PROMPT, rest_prompt, isFrontPage, aspect_ratio, level, front_prompt):
    print("Clicking on chat bar.")
    chat_bar = page.locator('xpath=//*[@id="app-mount"]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[3]/div[2]/main/form/div/div[1]/div/div[3]/div/div[2]/div')
    time.sleep(random.randint(1, 5))
    print("Typing in bot command")
    chat_bar.fill(command)
    time.sleep(random.randint(1, 5))
    print("Selecting the prompt option in the suggestions menu")
    prompt_option = page.locator('xpath=/html/body/div[1]/div[2]/div[1]/div[1]/div/div[2]/div/div/div/div/div[3]/div[2]/main/form/div/div[2]/div/div/div[2]/div[1]/div/div/div')
    time.sleep(random.randint(1, 5))
    prompt_option.click()
    print("Generating prompt using OpenAI's API.")
    generate_prompt_and_submit_command(page, PROMPT, rest_prompt, isFrontPage, aspect_ratio, level, front_prompt)


@eel.expose
def start_bot(pgno, channel_url, topic, rest_prompt, aspect_ratio, level, front_prompt):
    PROMPT = f"Generate a Midjourney prompt to result in an image about {topic} ."
    print(f"Prompt: {PROMPT}")
    bot_command = "/imagine"
    main(bot_command, channel_url, PROMPT, pgno, rest_prompt, aspect_ratio, level, front_prompt)


@eel.expose
def wait_and_select_upscale_options(page, prompt_text, isFrontPage):
    prompt_text = prompt_text.lower()
    try:
        time.sleep(5)
        last_message = get_last_message(page)
        if 'U1' in last_message:
            print("Found upscale options.")
            print("Attempting to upscale all generated images.")
            try:
                select_upscale_option(page, 'U1')
                time.sleep(random.randint(3, 5))
                select_upscale_option(page, 'U2')
                time.sleep(random.randint(3, 5))
                select_upscale_option(page, 'U3')
                time.sleep(random.randint(3, 5))
                select_upscale_option(page, 'U4')
                time.sleep(random.randint(3, 5))

                time.sleep(10)
            except Exception as e:
                print("An error occurred while selecting upscale options:", e)
            download_upscaled_images(page, prompt_text, isFrontPage)
        else:
            print("Photo(s) not fully loaded.")
            wait_and_select_upscale_options(page, prompt_text, isFrontPage)
    except Exception as e:
        print("An error occurred while finding the last message:", e)


# Initialize eel with your web files folder
eel.init('web')

# Keep this at the bottom, it will start the web server.
eel.start('index.html', mode='chrome', cmdline_args=['--kiosk'])
