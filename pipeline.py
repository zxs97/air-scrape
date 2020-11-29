from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import os
import re
import datetime
import argparse
import time

# setup selenium
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

# Display is needed in Docker runner


def get_browser(args):
    if args.mode == "dev":
        opts = Options()
        opts.add_argument("--headless")
        opts.log.level = "trace"

        ff_binary = r"/home/hong/lib/firefox67/firefox"
        binary = FirefoxBinary(ff_binary)
        executable_path = r"/home/hong/.custom_bin/geckodriver"
        browser = webdriver.Firefox(
            executable_path=executable_path, firefox_binary=binary, options=opts
        )
    elif args.mode == "prod":
        browser = webdriver.Firefox()
    else:
        raise EnvironmentError
    return browser


def scrape_target(year, month, day, target_logics):
    results = {}
    for k, scrape_func in target_logics.items():
        print(f"Scraping {k}")
        hit_dates = scrape_func(year, month, day)
        if hit_dates:
            results[k] = hit_dates
    return results


def scrape_south_china_air(year, month, day):
    hit_dates = {}
    southchina_targets = {
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210101": "http://oversea.csair.com/new/us/en/shop/?execution=8313fc0e1a5b24caf6ccdc886d1034b8",
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210103": "http://oversea.csair.com/new/us/en/shop/?execution=687bc0f127a16052d196b6ad60f69988",
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210108": "http://oversea.csair.com/new/us/en/shop/?execution=70c97df0c592b23ae539d9fcd6bd1f85",
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210110": "http://oversea.csair.com/new/us/en/shop/?execution=858419db94efd7f0cd1cf2bf946ce99d",
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210115": "http://oversea.csair.com/new/us/en/shop/?execution=a449bde682b78327aa6e019cc7e37ab3",
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210117": "http://oversea.csair.com/new/us/en/shop/?execution=7c564b1ec7f55d3bc25e05b90cff499e",
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210122": "http://oversea.csair.com/new/us/en/shop/?execution=33bc7cfcb262af2288d9bcdb791ac734",
        "oversea.csair.com/new/us/en/flights?m=0&p=100&flex=1&t=LAX-CAN-20210124": "http://oversea.csair.com/new/us/en/shop/?execution=146446d228b651081de823f54b6da3ed",
    }
    price_limit = 14000

    start = time.time()
    for k, v in southchina_targets.items():
        date = re.search(r"(2021)(\d{2})(\d{2})", k)
        y, m, d = date.groups()
        if datetime.date(year, month, day) > datetime.date(int(y), int(m), int(d)):
            continue

        time.sleep(3)
        browser.get(v)
        try:
            txt = [
                e.get_attribute("textContent")
                for e in browser.find_elements_by_class_name("day")
            ]
            txt = [e for e in txt if "USD" in e]
            p = r"USD ([\d\.]+)"
            hit_txt = []
            for e in txt:
                price = float(re.search(p, e).group(1))
                if price <= price_limit:
                    hit_txt.append(e)
            hit = "\n".join(hit_txt)
            if hit:
                hit_dates[f"{y}{m}{d}"] = hit
        except ValueError:
            pass
        print(
            f"scrape_south_china_air @@ DONE {y}{m}{d}, elapsed {time.time()-start:.2f} sec"
        )
    return hit_dates


def scrape_xmair(year, month, day):
    hit_dates = {}
    candidate_dates = gen_dates_in_month(year, month, day, good_weekday=[2, 6])
    for d_ in candidate_dates:
        start = time.time()
        print(f"@@ Date: {d_}")
        url = gen_xmair_url(**d_)

        txt = get_response_xmair(url, attempt=10)

        if txt:
            res = parse_xmairline(txt)
            print(res, txt)
            if res == True:
                hit_y, hit_m, hit_d = d_["year"], d_["month"], d_["day"]
                hit_dates[f"{hit_y}_{hit_m}_{hit_d}"] = txt
        else:
            print("No response")

        print(f"Elapsed {time.time()-start:.2f} sec")
    return hit_dates


def gen_dates_in_month(year, month, date, good_weekday):
    start = datetime.date(year, month, date)
    res = []
    for i in range(31):
        d = start + datetime.timedelta(days=i)
        if d.month != month:
            break
        if d.weekday() in good_weekday:
            res.append({"year": d.year, "month": d.month, "day": d.day})
    return res


def gen_xmair_url(year, month, day):
    return f"https://www.xiamenair.com/zh-cn/nticket.html?tripType=OW&orgCodeArr%5B0%5D=LAX&dstCodeArr%5B0%5D=XMN&orgDateArr%5B0%5D={year}-{str(month).zfill(2)}-{day}&dstDate=&isInter=true&adtNum=1&chdNum=0&JFCabinFirst=false&acntCd=&mode=Money&partner=false&jcgm=false"


def get_response_xmair(url, attempt=5):
    txt = None
    start = time.time()
    print(f"get_response_xmair, url={url}, attempt={attempt}")
    while txt is None and attempt:
        try:
            browser.get(url)
            print(
                f"get_response_xmair attempt{attempt}@@ Elapsed {time.time()-start:.2f} sec"
            )
            txt = browser.find_element_by_class_name("flight-info").text
        except:
            time.sleep(3)
        attempt -= 1
    return txt


def parse_xmairline(txt, price_limit=30000):
    # '22:55\n洛杉矶国际机场TB\n直飞：\n06:00 (+2)\n厦门高崎T3\n15小时5分钟\n¥ 64674 起\n(含税总价)'
    tokens = txt.split("\n")
    price = tokens[-2]
    pattern = r"¥ (\d+) "
    match = re.search(pattern, price)
    if len(match.groups()) == 1 and match.group(1).isnumeric():
        price = int(match.group(1))
        if price < price_limit:
            return True
    return False


# data action
def act_on_results(results):
    code = 1
    body = {}
    for target, hit_dates in results.items():
        entry = "\n".join([f"{date_}-->{hit_}\n" for date_, hit_ in hit_dates.items()])
        body[target] = entry
    if body:
        body = "\n".join([f"@@@{target}\n{entry}" for target, entry in body.items()])
        code = sms_notify(body)
    return code


def sms_notify(result):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    body = f"###\nPositive result: {result}\nAt time: {now}"
    curl_cmd = get_curl_cmd(body, args)
    code = os.system(curl_cmd)
    return code


def get_curl_cmd(body, args):
    data = {"To": args.tonumber, "From": args.fromnumber, "Body": body}

    payload = "&".join([f"{k}={v}" for k, v in data.items()])

    twillio_url = (
        f"https://api.twilio.com/2010-04-01/Accounts/{args.login}/Messages.json"
    )
    login_name = args.login
    pwd = args.password
    cmd = f"curl '{twillio_url}' -X POST -u {login_name}:{pwd} -d '{payload}'"
    return cmd


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--login")
    parser.add_argument("--password")
    parser.add_argument("--fromnumber")
    parser.add_argument("--tonumber")
    parser.add_argument("--mode")
    args = parser.parse_args()

    if args.mode == "prod":
        from pyvirtualdisplay import Display

        display = Display(visible=0, size=(800, 600))
        display.start()

    browser = get_browser(args)
    target_logics = {
        "xmair": scrape_xmair,
        "southchina_air": scrape_south_china_air
    }
    results = scrape_target(2021, 1, 1, target_logics)
    act_on_results(results)

    if args.mode == "prod":
        browser.quit()
        display.stop()
