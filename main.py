import re
import bs4
import requests
from VAR import URL, TOKEN

SECTIONS = {
    "cookie": "cookies",
    "параметры запроса": "query",
    "данные формы": "data",
    "загрузите файлы": "files",
    "заголовки": "headers",
}


def table_to_dict(table):
    cells = [c.get_text() for c in table.find_all("code")]
    return dict(zip(cells[::2], cells[1::2]))


def collect_tables(soup):
    result = {name: {} for name in SECTIONS.values()}
    current = None

    for node in soup.descendants:
        if isinstance(node, bs4.NavigableString):
            if node.find_parent("table"):
                continue
            text = node.lower()
            for phrase, section in SECTIONS.items():
                if phrase in text:
                    current = section
        elif node.name == "table":
            result[current] = table_to_dict(node)

    return result


def detect_method_and_path(page_text, soup):
    first_code = soup.find("code")

    if "Загрузите файлы" in page_text or "POST" in page_text:
        return "POST", first_code.text
    if "ссылке" in page_text:
        return "GET", soup.find("a", href=True)["href"]
    if "GET" in page_text:
        return "GET", first_code.text


def build_request(page_text):
    soup = bs4.BeautifulSoup(page_text, "lxml")
    method, path = detect_method_and_path(page_text, soup)
    tables = collect_tables(soup)

    cookies = {"user": TOKEN, **tables["cookies"]}
    headers = dict(tables["headers"])
    headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())

    return {
        "method": method,
        "url": URL + path,
        "params": tables["query"],
        "headers": headers,
        "data": tables["data"],
        "files": {k: v.encode("utf-8") for k, v in tables["files"].items()},
    }


def print_steps(page_text):
    soup = bs4.BeautifulSoup(page_text, "lxml")
    for s in soup.find_all(string=re.compile("Шаг")):
        print(s.strip())


def main():
    page = requests.get(URL, headers={"Cookie": f"user={TOKEN}"}).text

    while "Поздравляем," not in page:
        print_steps(page)
        page = requests.request(**build_request(page)).text

    print(bs4.BeautifulSoup(page, "lxml").find("code").text)


if __name__ == "__main__":
    main()