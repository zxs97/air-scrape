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
from pyvirtualdisplay import Display
# Display is needed in Docker runner

# opts = Options()
# opts.add_argument("--headless")
# # opts.log.level = "trace"

# # ff_binary = r"/home/hong/lib/firefox67/firefox"
# # binary = FirefoxBinary(ff_binary)
# # executable_path = r"/home/hong/.custom_bin/geckodriver"
# # browser = webdriver.Firefox(
# #     executable_path=executable_path, firefox_binary=binary, options=opts
# # )
# browser = webdriver.Firefox(options=opts)
def get_browser(args):
    if args.mode == 'dev':
        opts = Options()
        opts.add_argument("--headless")
        opts.log.level = "trace"

        ff_binary = r"/home/hong/lib/firefox67/firefox"
        binary = FirefoxBinary(ff_binary)
        executable_path = r"/home/hong/.custom_bin/geckodriver"
        browser = webdriver.Firefox(
            executable_path=executable_path, firefox_binary=binary, options=opts
        )
    elif args.mode == 'prod':
        browser = webdriver.Firefox()
    else:
        raise EnvironmentError
    return browser


suffix = lambda x: "&qp=storepickupstores_facet%3DStore~{store_id}&extStoreId={store_id}".format(store_id=x)
bb_ns = "https://www.bestbuy.com/site/nintendo-switch-32gb-console-neon-red-neon-blue-joy-con/6364255.p?skuId=6364255"
# bb_ns_cambridge = bb_ns + suffix(537)
# bb_ns_everett = bb_ns + suffix(1088)
# bb_ns_southbay = bb_ns + suffix(1126)
# bb_ns_watertown = bb_ns + suffix(596)
bb_rf = "https://www.bestbuy.com/site/ring-fit-adventure-nintendo-switch/6352149.p?skuId=6352149"
bb_urls = {}
for key_itm, url_itm in zip(['bb_ns','bb_rf'], [bb_ns, bb_rf]):
    for store_num in [187, 873, 1896, 499, 1021, 2639]:
        _key = f"{key_itm}_{store_num}"
        _url = url_itm + suffix(store_num)
        bb_urls[_key] = _url

tg_ns = "https://www.target.com/p/nintendo-switch-with-neon-blue-and-neon-red-joy-con/-/A-77464001"
tg_rf = "https://www.target.com/p/ring-fit-adventure-nintendo-switch/-/A-76593324"
tg_urls = {
    "tg_ns": tg_ns, "tg_rf": tg_rf
}


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


def get_result_target(url, itv=2):
    browser.get(url)
    time.sleep(5)
    try:
        browser.find_element_by_xpath("//button[@data-test='fiatsButton']").click()
        print('@')
        time.sleep(itv)
        browser.find_element_by_xpath("//a[@data-test='storeSearchLink']").click()
        print('@@')
        time.sleep(itv)
        browser.find_element_by_id("storeSearch").clear()
        print('@@@')
        time.sleep(itv)
        browser.find_element_by_id("storeSearch").send_keys("02140")
        print('@@@@')
        time.sleep(itv)
        browser.find_element_by_xpath(
            "//button[@data-test='fiatsUpdateLocationSubmitButton']"
        ).click()
        print('@@@@@')
        time.sleep(itv)
        browser.find_element_by_xpath("//div[@class='switch-track']").click()
        print('@@@@@@')
        time.sleep(itv)
        results = browser.find_elements_by_xpath(
            "//div[@data-test='storeAvailabilityStoreCard']"
        )
        results = [_.text for _ in results]
        print('@@@@@@@')
        print('Found results, to be filtered result by closest..')
    except:
        print(f"Did not get response for query {url}")
        results = None
    return results


def get_response(urls):
    results = {}
    for k, url in urls.items():
        print(f"Scraping {url}")
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


def parse_result_target(results, threshold=50):
    n_mile = None
    if results is None:
        print('No result for target')
        return None
    output = []
    nearby = None
    for result in results:
        if 'mile' not in result:
            continue # dont save local store's hit
            # output.append(result)
        else:
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
                            nearby = (n_mile, result) if ((nearby is None) or (n_mile < nearby[0])) else nearby
                # print(f'Checked, nothing within {threshold} miles at time {now}')
    if nearby is not None:
        output.append(nearby[1])
    if len(output) == 0:
        return None
    else:
        return "\n".join(output)


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
    curl_cmd = get_curl_cmd(body, args)
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
    parser.add_argument('--mode')
    args = parser.parse_args()

    now = datetime.now().strftime("%H:%M:%S")
    urls = {
        **bb_urls,
        **tg_urls,
    }

    # get browser
    # display is needed in docker runner
    display = Display(visible=0, size=(800, 600))
    display.start()
    
    browser = get_browser(args)

    results = get_response(urls)
    code = act_on_results(results)
    for k, r in results.items():
        print(f"{k}=============================")
        if isinstance(r, list): r = "\n\n".join(r)
        print(r)

    print(code)
    print(now)

    browser.quit()
    display.stop()
