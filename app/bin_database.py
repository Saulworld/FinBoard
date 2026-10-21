"""Card BIN database and resolution module for FinBoard."""

from __future__ import annotations

import re
from typing import Any

# Precise 8-digit and 6-digit BIN mappings verified against actual card issuers
BIN_DATABASE: dict[str, dict[str, str]] = {
    # 2026-10-19: exact 8-digit lookup https://bincheck.io/details/52294395
    # BIN register names Paynetics AD; Trading 212's UK card agreement names
    # Paynetics UK Limited. Do not extend this to the conflicting 6-digit range.
    "52294395": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Paynetics AD",
    },
    # Binlist 2026-09-30: six-digit lookup; identical result for 53734906.
    "537349": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Monavate Limited",
    },
    # 8-digit exact BINs
    "44136436": {
        "country": "美国",
        "alpha2": "US",
        "flag": "🇺🇸",
        "issuer": "Coastal Community Bank",
    },
    "44136980": {
        "country": "波多黎各(美属)",
        "alpha2": "PR",
        "flag": "🇵🇷",
        "issuer": "Third National Puerto Rico / Rain",
    },
    "48344219": {
        "country": "菲律宾",
        "alpha2": "PH",
        "flag": "🇵🇭",
        "issuer": "Maya Bank, Inc. / Maya Philippines",
    },
    "42403270": {
        "country": "美国",
        "alpha2": "US",
        "flag": "🇺🇸",
        "issuer": "Sutton Bank",
    },
    "45492414": {
        "country": "波多黎各(美属)",
        "alpha2": "PR",
        "flag": "🇵🇷",
        "issuer": "Banco San Juan Internacional, Inc.",
    },
    "45492406": {
        "country": "波多黎各(美属)",
        "alpha2": "PR",
        "flag": "🇵🇷",
        "issuer": "Banco San Juan Internacional, Inc.",
    },
    "45492423": {
        "country": "波多黎各(美属)",
        "alpha2": "PR",
        "flag": "🇵🇷",
        "issuer": "Nimbus LLC / Banco San Juan Internacional",
    },
    "44135399": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "PFH Finance, Ltd. / Adyen",
    },
    "49372420": {
        "country": "新加坡",
        "alpha2": "SG",
        "flag": "🇸🇬",
        "issuer": "Xfers Pte. Ltd. (StraitsX)",
    },
    "49372421": {
        "country": "新加坡",
        "alpha2": "SG",
        "flag": "🇸🇬",
        "issuer": "Xfers Pte. Ltd. / Sunrate",
    },
    "53211342": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Monavate",
    },
    "52598101": {
        "country": "马耳他",
        "alpha2": "MT",
        "flag": "🇲🇹",
        "issuer": "Papaya Ltd.",
    },
    "52595910": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Paysafe",
    },
    "49387519": {
        "country": "香港",
        "alpha2": "HK",
        "flag": "🇭🇰",
        "issuer": "Unicard Solution Ltd. (Rain)",
    },
    "49387551": {
        "country": "香港",
        "alpha2": "HK",
        "flag": "🇭🇰",
        "issuer": "Unicard Solution Ltd.",
    },
    "22800118": {
        "country": "新加坡",
        "alpha2": "SG",
        "flag": "🇸🇬",
        "issuer": "WoTransfer / OCBC",
    },
    "45993917": {
        "country": "马来西亚",
        "alpha2": "MY",
        "flag": "🇲🇾",
        "issuer": "CIMB Bank Berhad",
    },
    "40433705": {
        "country": "新加坡",
        "alpha2": "SG",
        "flag": "🇸🇬",
        "issuer": "DCS Card Centre Pte. Ltd.",
    },
    "53746503": {
        "country": "荷兰",
        "alpha2": "NL",
        "flag": "🇳🇱",
        "issuer": "bunq B.V.",
    },
    "53317148": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Transact Payments Limited",
    },
    "45600702": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Altery",
    },
    "62245433": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Altery",
    },
    "45672510": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Zopa Bank Limited",
    },
    "52401394": {
        "country": "香港",
        "alpha2": "HK",
        "flag": "🇭🇰",
        "issuer": "Photon Dance (Hong Kong), Ltd.",
    },
    "49218171": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Lloyds Bank plc",
    },
    "43195900": {
        "country": "爱尔兰",
        "alpha2": "IE",
        "flag": "🇮🇪",
        "issuer": "Paysafe Payment Solutions Limited",
    },
    "53990021": {
        "country": "澳大利亚",
        "alpha2": "AU",
        "flag": "🇦🇺",
        "issuer": "Fly Wallet Pty. Ltd.",
    },
    "44260100": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Wirex Limited",
    },
    "49382815": {
        "country": "香港",
        "alpha2": "HK",
        "flag": "🇭🇰",
        "issuer": "Unicard Solution Ltd. / Gate",
    },
    "45492418": {
        "country": "波多黎各(美属)",
        "alpha2": "PR",
        "flag": "🇵🇷",
        "issuer": "Banco San Juan Internacional, Inc. (Rain)",
    },
    "53710074": {
        "country": "美国",
        "alpha2": "US",
        "flag": "🇺🇸",
        "issuer": "Sutton Bank",
    },
    # 6-digit prefix fallbacks
    "454924": {
        "country": "波多黎各(美属)",
        "alpha2": "PR",
        "flag": "🇵🇷",
        "issuer": "Banco San Juan Internacional, Inc.",
    },
    "483442": {
        "country": "菲律宾",
        "alpha2": "PH",
        "flag": "🇵🇭",
        "issuer": "Maya Bank, Inc. / Maya Philippines",
    },
    "493724": {
        "country": "新加坡",
        "alpha2": "SG",
        "flag": "🇸🇬",
        "issuer": "Xfers / Sunrate",
    },
    "532113": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Monavate",
    },
    "525981": {
        "country": "马耳他",
        "alpha2": "MT",
        "flag": "🇲🇹",
        "issuer": "Papaya Ltd.",
    },
    "525959": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Paysafe",
    },
    "493875": {
        "country": "香港",
        "alpha2": "HK",
        "flag": "🇭🇰",
        "issuer": "Unicard Solution Ltd.",
    },
    "228001": {
        "country": "新加坡",
        "alpha2": "SG",
        "flag": "🇸🇬",
        "issuer": "WoTransfer / OCBC",
    },
    "459939": {
        "country": "马来西亚",
        "alpha2": "MY",
        "flag": "🇲🇾",
        "issuer": "CIMB Bank Berhad",
    },
    "404337": {
        "country": "新加坡",
        "alpha2": "SG",
        "flag": "🇸🇬",
        "issuer": "DCS Card Centre",
    },
    "537465": {
        "country": "荷兰",
        "alpha2": "NL",
        "flag": "🇳🇱",
        "issuer": "bunq B.V.",
    },
    "533171": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Transact Payments Limited",
    },
    "456007": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Altery",
    },
    "622454": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Altery",
    },
    "456725": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Zopa Bank Limited",
    },
    "524013": {
        "country": "香港",
        "alpha2": "HK",
        "flag": "🇭🇰",
        "issuer": "Photon Dance (Hong Kong), Ltd.",
    },
    "492181": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Lloyds Bank plc",
    },
    "431959": {
        "country": "爱尔兰",
        "alpha2": "IE",
        "flag": "🇮🇪",
        "issuer": "Paysafe Payment Solutions Limited",
    },
    "539900": {
        "country": "澳大利亚",
        "alpha2": "AU",
        "flag": "🇦🇺",
        "issuer": "Fly Wallet Pty. Ltd.",
    },
    "442601": {
        "country": "英国",
        "alpha2": "GB",
        "flag": "🇬🇧",
        "issuer": "Wirex Limited",
    },
    "493828": {
        "country": "香港",
        "alpha2": "HK",
        "flag": "🇭🇰",
        "issuer": "Unicard Solution Ltd. / Gate",
    },
    "537100": {
        "country": "美国",
        "alpha2": "US",
        "flag": "🇺🇸",
        "issuer": "Sutton Bank",
    },
}


def get_card_bin_info(card_number: str) -> dict[str, Any]:
    """Extract and resolve BIN information for a given card number."""
    clean_number = re.sub(r"[\s-]", "", card_number or "")
    if len(clean_number) < 6:
        return {
            "country": "",
            "alpha2": "",
            "flag": "",
            "issuer": "",
            "bin": "",
            "badge": "",
            "display": "--",
        }

    bin8 = clean_number[:8] if len(clean_number) >= 8 else ""
    bin6 = clean_number[:6]

    info = BIN_DATABASE.get(bin8) or BIN_DATABASE.get(bin6)
    if not info:
        return {
            "country": "其他",
            "alpha2": "",
            "flag": "🌐",
            "issuer": "--",
            "bin": bin8 or bin6,
            "badge": "",
            "display": f"未收录BIN({bin8 or bin6})",
        }

    country = info["country"]
    alpha2 = info["alpha2"]
    flag = info["flag"]
    issuer = info["issuer"]
    matched_bin = bin8 if bin8 in BIN_DATABASE else bin6

    badge = f"{flag}{alpha2}" if flag and alpha2 else country
    display = f"{flag}{country}({alpha2})·{issuer}(BIN:{matched_bin})"

    return {
        "country": country,
        "alpha2": alpha2,
        "flag": flag,
        "issuer": issuer,
        "bin": matched_bin,
        "badge": badge,
        "display": display,
    }
