from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import os
import re
from datetime import datetime
import argparse
import time

# setup selenium
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

opts = Options()
opts.add_argument("--headless")
opts.log.level = "trace"

ff_binary = r"/home/hong/lib/firefox67/firefox"
binary = FirefoxBinary(ff_binary)
executable_path = r"/home/hong/.custom_bin/geckodriver"
browser = webdriver.Firefox(
    executable_path=executable_path, firefox_binary=binary, options=opts
)

bb_ns = "https://www.bestbuy.com/site/nintendo-switch-32gb-console-neon-red-neon-blue-joy-con/6364255.p?skuId=6364255"
tg_ns = "https://www.target.com/p/nintendo-switch-with-neon-blue-and-neon-red-joy-con/-/A-77464001"
tg_rf = "https://www.target.com/p/ring-fit-adventure-nintendo-switch/-/A-76593324"


wd = Path.cwd()


def get_result_bestbuy(url):
    browser.get(url)
    time.sleep(2)
    try:
        browser.find_element_by_class_name("fulfillment-add-to-cart-button").click()
        time.sleep(2)
        result = browser.find_element_by_class_name(
            "fulfillment-add-to-cart-button"
        ).text
    except:
        print(f"Did not click for query {url}")
        result = None
    return result


def get_result_target(url, itv=1):
    browser.get(url)
    time.sleep(itv)
    try:
        browser.find_element_by_xpath("//button[@data-test='fiatsButton']").click()
        time.sleep(itv)
        browser.find_element_by_xpath("//a[@data-test='storeSearchLink']").click()
        time.sleep(itv)
        browser.find_element_by_id("storeSearch").clear()
        time.sleep(itv)
        browser.find_element_by_id("storeSearch").send_keys("02140")
        time.sleep(itv)
        browser.find_element_by_xpath(
            "//button[@data-test='fiatsUpdateLocationSubmitButton']"
        ).click()
        time.sleep(itv)
        browser.find_element_by_xpath("//div[@class='switch-track']").click()
        time.sleep(itv)
        result = browser.find_element_by_xpath(
            "//div[@data-test='storeAvailabilityStoreCard']"
        ).text
    except:
        print(f"Did not get response for query {url}")
        result = None
    return result


def get_response(urls):
    results = {}
    for k, url in urls.items():
        if "bb" in k:
            results[k] = get_result_bestbuy(url)
        elif "tg" in k:
            results[k] = get_result_target(url)
    return results


def parse_result_bestbuy(result):
    if (
        "sold out" in result.lower()
    ):  # both "find a store" and "add to cart" can be a positive; otherwise
        return None
    else:
        return result


def parse_result_target(result, threshold=50):
    n_mile = None
    for elm in result.split("\n"):
        if "mile" in elm:
            res = re.search("^([\d\.]+)\s+miles$", elm)
            if res is not None:
                try:
                    n_mile = float(res.group(1))
                except ValueError:
                    print("not a float")
                    break
                if n_mile is not None and n_mile <= threshold:
                    return result
    #     print(f'Checked, nothing within {threshold} miles at time {now}')
    return None


# data action
def get_curl_cmd(body, args):
    data = {"To": args.tonumber,  "From": args.fromnumber,  "Body": body}
    payload = "&".join([f"{k}={v}" for k, v in data.items()])

    twillio_url = f"https://api.twilio.com/2010-04-01/Accounts/{args.login}/Messages.json"
    login_name = args.login
    pwd = args.password
    cmd = f"curl '{twillio_url}' -X POST -u {login_name}:{pwd} -d '{payload}'"
    return cmd


def sms_notify(result):
    now = datetime.now().strftime("%H:%M:%S")
    body = f"###\nPositive result: {result}\nAt time: {now}"
    curl_cmd = get_curl_cmd(body)
    code = os.system(curl_cmd)
    return code


def act_on_results(results):
    found_available = {}
    code = 1
    for k, result in results.items():
        if "bb" in k:
            result = parse_result_bestbuy(result)
        elif "tg" in k:
            result = parse_result_target(result)
        if result is not None:
            found_available[k] = result
    if len(found_available):
        body = "\n".join([f"{k}-->{r}\n" for k, r in found_available.items()])
        code = sms_notify(body)
    return code


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--login')
    parser.add_argument('--password')
    parser.add_argument('--fromnumber')
    parser.add_argument('--tonumber')
    args = parser.parse_args()

    now = datetime.now().strftime("%H:%M:%S")
    urls = {"bb_ns": bb_ns, "tg_ns": tg_ns, "tg_rf": tg_rf}
    results = get_response(urls)
    code = act_on_results(results)
    print(results)
    print(code)
    print(now)
