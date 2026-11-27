# PLAIN ENGLISH (Florida Medicaid enrollment status check)
# Decides: Nothing. Reads the public Enrollment Status page of the Florida Medicaid Web Portal for one application
#   (ATN + business or last name, exactly as submitted) and prints each document's status (VERIFIED / REJECTED /
#   NOT RECEIVED / OPTIONAL), the application status (e.g. APPLICATION DEFICIENT) and the deficiency text.
# Rules it uses: The page needs no login. It is the same search a person runs at portal.flmmis.com > Provider Services >
#   Enrollment > Enrollment Status. A deficient application is fixed on that same page with UPLOAD Documentation, then
#   CORRECT Application > Submit, in one sitting (the portal says the resubmission is not finished otherwise).
# Never touches: The application itself. It does not upload, correct, cancel or submit anything, and it never logs in.
# ---
"""Usage: python3 fl_medicaid_status.py <ATN> <LAST-OR-BUSINESS-NAME> [--json]

Example: python3 fl_medicaid_status.py 1234567 SMITH
Works for any practice: the ATN is printed on the wizard's confirmation page and on every Gainwell letter ("RE: <ATN>").
"""
import html
import json
import re
import sys

import requests

BASE = "https://portal.flmmis.com/FLPublic"
STATUS_URL = BASE + "/Provider_ProviderServices/Provider_Enrollment/Provider_Enrollment_EnrollmentStatus/tabId/57/Default.aspx"
FIELD_ATN = "dnn$EnrollmentSearchPage$SearchPage$CriteriaPanel$ctl02$ctl00$ETN$mb_ETN"
FIELD_NAME = "dnn$EnrollmentSearchPage$SearchPage$CriteriaPanel$ctl02$ctl01$Name$mb_Name"
SEARCH_TARGET = "dnn$EnrollmentSearchPage$SearchPage$CriteriaPanel$ctl02$ctl01$SearchButton"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def _hidden_fields(page):
    fields = {}
    for tag in re.findall(r"<input[^>]+>", page, re.I):
        if not re.search(r'type="hidden"', tag, re.I):
            continue
        name = re.search(r'name="([^"]+)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            fields[html.unescape(name.group(1))] = html.unescape(value.group(1)) if value else ""
    return fields


def _text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", fragment))).strip()


def check(atn, name):
    s = requests.Session()
    s.headers["User-Agent"] = UA
    s.get(BASE + "/Default.aspx", timeout=60)  # the portal wants its session cookie before the status page
    first = s.get(STATUS_URL, timeout=60).text
    form = _hidden_fields(first)
    form.update({FIELD_ATN: str(atn), FIELD_NAME: name.upper(), "__EVENTTARGET": SEARCH_TARGET, "__EVENTARGUMENT": ""})
    page = s.post(STATUS_URL, data=form, timeout=60).text
    rows = []
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        cells = [_text(c) for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", tr)]
        if len(cells) >= 4 and cells[0] == str(atn):
            rows.append({"name": cells[1], "document": cells[2], "status": cells[3],
                         "status_date": cells[4] if len(cells) > 4 else "",
                         "provider_id": cells[5] if len(cells) > 5 else "",
                         "effective": cells[6] if len(cells) > 6 else "",
                         "screening_category": cells[7] if len(cells) > 7 else ""})
    deficiencies = []
    m = re.search(r"(?is)Application Deficiencies(.*?)(ALERT!|Need enrollment forms|Application Status Code)", page)
    if m:
        deficiencies = [_text(li) for li in re.findall(r"(?is)<li[^>]*>(.*?)</li>", m.group(1)) if _text(li)]
    return {"atn": str(atn), "name": name.upper(), "rows": rows, "deficiencies": deficiencies,
            "found": bool(rows)}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    result = check(args[0], args[1])
    if "--json" in sys.argv:
        print(json.dumps(result, indent=1))
        sys.exit(0)
    if not result["found"]:
        print("No application found for ATN %s / %s (check the spelling: it must match the application exactly)." % (result["atn"], result["name"]))
        sys.exit(1)
    for r in result["rows"]:
        print("%-55s %-22s %s" % (r["document"], r["status"], r["status_date"]))
    if result["deficiencies"]:
        print("\nDeficiencies:")
        for d in result["deficiencies"]:
            print(" - " + d)
