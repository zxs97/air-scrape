TODO
1. refactor: env->docker, scraper_logic: pipeline code, config_data: user(location, account),store_url,product,filter_criterion
2. notification system: twilio -> [sns+ifttt](https://github.com/danilop/SNS2IFTTT)


BUG
1. skip when there's no url (from bb)
2. selenium.common.exceptions.InvalidSessionIdException: Message: Tried to run command without establishing a connection
  1. This is due to clash of browser: refactor into a class, to allow reset browser once `browser.get()` fails
