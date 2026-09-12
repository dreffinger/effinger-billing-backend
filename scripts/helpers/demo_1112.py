# PLAIN ENGLISH (chart reads, 9/12 7am ET run): getdemographic for the patients William answered on the board -
# insurance plans (id, carrier, subscriber num masked to last 4, sequence, dates), referral plans, address, responsible party. Reads only.
import amd, re, sys
for pid in sys.argv[1:]:
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    pat = re.search(r'<patient [^>]*>', t)
    a = dict(re.findall(r'(\w+)="([^"]*)"', pat.group(0))) if pat else {}
    print("==", pid, a.get("name"), "dob", a.get("dob"), "insorder", a.get("insorder"), "respparty", a.get("respparty"), "profile", a.get("profile"))
    ad = re.search(r'<address [^>]*>', t)
    if ad: print("   address", {k: v for k, v in re.findall(r'(\w+)="([^"]*)"', ad.group(0)) if k in ("address1","address2","city","state","zipcode","zip")})
    for ip in re.findall(r'<insplan [^>]*>', t):
        d = dict(re.findall(r'(\w+)="([^"]*)"', ip))
        print("   insplan", d.get("id"), d.get("carrier"), d.get("carriercode") or "", "num=***%s" % (d.get("subscribernum") or "")[-4:], "seq", d.get("sequence"), d.get("begindate"), "-", d.get("enddate"), "grp=%s/%s" % (d.get("grpnum"), d.get("grpname")))
    for rp in re.findall(r'<refplan [^>]*>', t):
        d = dict(re.findall(r'(\w+)="([^"]*)"', rp))
        print("   refplan", d.get("id"), "ismain", d.get("ismain"), "preauth", d.get("preauth"), d.get("begindate"), "-", d.get("enddate"), "status", d.get("status"))
