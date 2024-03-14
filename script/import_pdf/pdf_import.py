import requests
from validators import url as is_url

def url_request(option, url: str, new_name: str = None) -> bool | None:
    if not is_url(url):
        print(f"Invalid url: {url}")
        return

    try:
        response = requests.get(url, timeout=option.request_timeout)
    except requests.exceptions.Timeout:
        print(f"Timeout (>{option.request_timeout}s) for {url}")
        return
    if response.status_code != 200:
        print(f"Failed to download {url}. (Status code: {response.status_code})")
        return
    
    if "content-disposition" in response.headers:
        content_disposition = response.headers["content-disposition"]
        old_name = content_disposition.split("filename=")[1]
    else:
        old_name = url.split("/")[-1]
    
    old_name = old_name.replace('"', "").replace("'", "")

    if not old_name.endswith(".pdf"):
        try: 
            has_pdf_header = response.headers["content-type"] != "application/pdf"
        except KeyError:
            print(f"Invalid file extension: {old_name}")
            has_pdf_header = True
        finally:
            old_name += ".pdf"
            if not has_pdf_header:
                print(f"{url} does not give a pdf file")

    pdf_path = option.pdf_folder + (new_name if new_name != None else old_name)
    with open(pdf_path, mode="wb") as file:
        file.write(response.content)
        print(f"Downloaded {url} to {pdf_path}")
    
    return True