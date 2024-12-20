from bs4 import BeautifulSoup
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from urllib.parse import urljoin
import time

BEGIN_PAG = 1
END_PAG = 15

username = 'usr'
password = 'pwd'

session = requests.Session()
login_url = 'https://www.mangaupdates.com/login.html'
payload = {'username': username, 'password': password, 'act': 'login'}
response = session.post(login_url, data=payload)

def resize_image(img, max_height=224):
    width, height = img.size
    if height > max_height:
        new_height = max_height
        aspect_ratio = width / height
        new_width = int(new_height * aspect_ratio)
        img = img.resize((new_width, new_height), Image.ANTIALIAS)
    return img


def parse_series_page(url):
    response = session.get(url)
    series_soup = BeautifulSoup(response.text, 'html.parser')


    for type_tag in series_soup.find_all('div', {'class': 'info-box_sContent__CTwJh'}):
        type_text = type_tag.get_text().strip()
        if type_text == "Manhwa" or type_text == "Manhua" or type_text == "Doujinshi":
            print (url, 'hwa, hua, shi')
            return None

    for cat_div, content_div in zip(series_soup.find_all('div', {'class': 'sCat'}),
                                    series_soup.find_all('div', {'class': 'sContent'})):
        cat_text = cat_div.get_text().strip()
        content_text = content_div.get_text().strip()
        if "Completely Scanlated?" in cat_text and content_text == "No":
            print(url, 'not complete')
            return None

    img_tags = series_soup.find_all('img', {'class': 'img-fluid'})
    for img_tag in img_tags:
        img_url = img_tag.get('src')
        alt_text = img_tag.get('alt', '').strip()

        if alt_text == "Series Image" and img_url:
            if not img_url.startswith(('http:', 'https:')):
                img_url = urljoin(url, img_url)

            try:
                img_response = requests.get(img_url)
                img = Image.open(BytesIO(img_response.content))
                return img
            except requests.exceptions.MissingSchema:
                print("Invalid URL for image:", img_url)
                return None

    placeholder_img = Image.new('RGB', (160, 225), color='gray')
    draw = ImageDraw.Draw(placeholder_img)
    try:
        font = ImageFont.truetype("arial.ttf", 20) 
    except IOError:
        font = ImageFont.load_default()
    text = "No Image"
    text_width, text_height = draw.textsize(text, font=font)
    text_position = ((placeholder_img.width - text_width) // 2, (placeholder_img.height - text_height) // 2)
    draw.text(text_position, text, fill="black", font=font)

    return placeholder_img


def break_text(text, max_length=18):
    if len(text) <= max_length:
        return [text]

    lines = []
    current_line = ""

    for word in text.split(" "):
        if len(current_line) + len(word) + 1 > max_length:
            lines.append(current_line)
            current_line = ""

        current_line += (word + " ")

    lines.append(current_line)
    return lines


def truncate_text(text, max_length=50):
    if len(text) > max_length:
        return text[:45] + "..."
    return text


def create_montage(images, titles, first_date, last_date, images_per_row=10):
    images = [img for img in images if img is not None]

    if len(images) == 0:
        print("No images to create a montage.")
        return

    img_width, img_height = images[0].size
    text_height = 60
    title_height = 40  # Height for the title text
    new_img_height = img_height + text_height

    num_rows = (len(images) - 1) // images_per_row + 1
    montage_width = img_width * min(images_per_row, len(images))
    montage_height = new_img_height * num_rows + title_height  # Adding height for title

    montage = Image.new(mode="RGB", size=(montage_width, montage_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(montage)

    try:
        font = ImageFont.truetype("arial.ttf", 16)
        title_font = ImageFont.truetype("arial.ttf", 24)  # Font for title
    except IOError:
        print("Arial font not found, using default.")
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    # Draw title
    title_text = f"Series completed from {last_date} to {first_date}"
    title_width, title_height_actual = draw.textsize(title_text, font=title_font)
    title_position = ((montage_width - title_width) // 2, 10)  # X-center the text
    draw.text(title_position, title_text, font=title_font, fill=(0, 0, 0))

    for i, (img, title) in enumerate(zip(images, titles)):
        row = i // images_per_row
        col = i % images_per_row
        x_offset = col * img_width
        y_offset = row * new_img_height + title_height  # Y-offset adjusted for title height

        montage.paste(img, (x_offset, y_offset))

        truncated_title = truncate_text(title)
        lines = break_text(truncated_title)
        for j, line in enumerate(lines):
            draw.text((x_offset, y_offset + img_height + j * 20), line.strip(), font=font, fill=(0, 0, 0))

    # montage.show()
    montage.save("montage.png")

first_date = None
last_date = None

ended_series = []
date_elements = []

for page_num in range(BEGIN_PAG, END_PAG+1):
    time.sleep(10)
    url = f"https://www.mangaupdates.com/releases?page={page_num}"
    print("url= ", url)
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    date_span = soup.find('div', {'class': 'pt-3 new-release-day_release_day_title__YXsvx'}).find('i').find('span')
    if date_span:
        date_text = date_span.get_text().strip()
        date_elements.append(date_text)

    for div in soup.find_all('div', {'class': 'col-2 ps-1 new-release-item_pbreak__h_dGC'}):
        text = div.get_text().strip()

        if "(end)" in text:
            prev_div = div.find_previous_sibling('div', {'class': 'col-6 new-release-item_pbreak__h_dGC'})

            if prev_div is not None:
                link_tag = prev_div.find('a')

                if link_tag is not None and link_tag.get_text() != 'Add':
                    series_name = link_tag.get_text()
                    series_link = link_tag['href']

                    series_image = parse_series_page(series_link)

                    # print("series_name ", series_name)
                    # print("series_link ", series_link)
                    # print("series_image ", series_image)

                    if series_image is not None:
                        print(f"{series_name}: {series_link}")
                        ended_series.append({
                            'name': series_name,
                            'link': series_link,
                            'image': series_image
                        })

if len(date_elements) > 0:
    first_date = date_elements[0]
    last_date = date_elements[-1]

images = [series.get('image', None) for series in ended_series]
titles = [series.get('name', '') for series in ended_series]
resized_images = [resize_image(img) for img in images]

create_montage(resized_images, titles, first_date, last_date)
