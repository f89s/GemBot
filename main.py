from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import pywikibot

from Services.ru_account_service import SoybooruAuth


def get_site():
    """Login to the wiki and return the site object."""
    site = pywikibot.Site()
    site.login()
    return site


def is_wiki_blocked(site):
    """Check if the bot account is blocked on the wiki."""
    data = site.simple_request(
        action="query",
        meta="userinfo",
        uiprop="blockinfo"
    ).submit()
    userinfo = data.get("query", {}).get("userinfo", {})
    return "blockedby" in userinfo


def get_site_if_allowed():
    """Get site, but return None if the bot is blocked."""
    site = get_site()
    if is_wiki_blocked(site):
        print("[x] Bot is blocked on the wiki. Skipping tasks.")
        return None
    return site


def is_ru_banned(auth):
    """Check if the bot's SoyBooru account is banned."""
    res = auth.get("https://soybooru.com/api/User/Dailyjak")
    res.raise_for_status()
    data = res.json()
    return bool(data.get("activeBans") or data.get("activeBanZones"))


def get_ru_auth_if_allowed():
    """Get SoyBooru auth, but return None if banned."""
    auth = SoybooruAuth()
    if is_ru_banned(auth):
        print("[x] SoyBooru bot is banned. Skipping SoyBooru tasks.")
        return None
    return auth


def main():
    scheduler = BlockingScheduler()

    # --- Add your scheduled jobs here ---
    # Example:
    # scheduler.add_job(
    #     my_task,
    #     trigger=CronTrigger(hour=0, minute=0),
    #     name="My Task",
    #     coalesce=True,
    #     misfire_grace_time=3600,
    # )

    try:
        print("[*] Starting scheduler...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[x] Scheduler shutting down...")


if __name__ == "__main__":
    main()
