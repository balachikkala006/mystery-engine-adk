"""Built-in mystery case templates and deterministic forensic fixtures.

Having curated, airtight starter cases ensures:
1. Immediate playability and deterministic automated testing / ADK evaluations.
2. Consistent ground truth that the CaseForgePipeline can either load directly
   or use as structural inspiration when generating custom themes.
"""

from __future__ import annotations

from mystery_engine.schemas import CaseDossier, Clue, SealedSolution, Suspect

CURATED_CASES: dict[str, CaseDossier] = {
    "noir": CaseDossier(
        case_id="case_noir_clocktower",
        title="The Midnight Horologist",
        theme="noir",
        difficulty="standard",
        setting="Ashworth Observatory & Clocktower, rain-slicked harbor district",
        victim="Julian Ashworth, master watchmaker and rare-horology collector",
        time_of_crime="21:30",
        opening_brief=(
            "At 21:30 during a coastal blackout, Julian Ashworth collapsed inside his "
            "locked clockwork vault. His prized 18th-century 'Eclipse Chronometer' is "
            "missing, and three guests remained inside the tower when the backup "
            "generator kicked on at 21:40."
        ),
        suspects=[
            Suspect(
                name="Clara Vance",
                role="Former apprentice and restoration specialist",
                personality="Sharp, guarded, speaks with technical precision",
                claimed_alibi="Calibrating pendulums in the West Gallery",
                alibi_window="21:15-21:45",
                secret="She forged a provenance certificate for Julian last year.",
                motive="Julian threatened to expose her forgery to the horology guild.",
                fingerprint_id="FP-VANCE-104",
            ),
            Suspect(
                name="Marcus Sterling",
                role="Private auctioneer and debt-ridden investor",
                personality="Smooth, defensive when pressed about finances",
                claimed_alibi="Making a phone call on the East Balcony",
                alibi_window="21:20-21:40",
                secret="He owed syndicate creditors $400,000 due at midnight.",
                motive="Selling the Eclipse Chronometer would clear his debts immediately.",
                fingerprint_id="FP-STERLING-209",
            ),
            Suspect(
                name="Dr. Elena Rostova",
                role="Museum curator and Julian's estranged sister",
                personality="Composed, analytical, quietly resentful",
                claimed_alibi="Cataloguing ledger books in the Archive Room",
                alibi_window="21:10-21:45",
                secret="She secretly copied the vault blueprint weeks ago to audit the estate.",
                motive="Julian cut her museum out of his will earlier that afternoon.",
                fingerprint_id="FP-ROSTOVA-317",
            ),
        ],
        clues=[
            Clue(
                clue_id="clue_1",
                title="Shattered Pocket Watch",
                location="Vault threshold near the brass door",
                surface_description="A silver pocket watch cracked face-down, hands frozen at 21:32.",
                forensic_detail=(
                    "Smudged watchmaker's oil and a partial right-thumb print (FP-STERLING-209) "
                    "sit on the interior latch—not from regular handling, but from prying the "
                    "vault override gear."
                ),
                fingerprint_sample="FP-STERLING-209",
                links_to_suspect="Marcus Sterling",
            ),
            Clue(
                clue_id="clue_2",
                title="Encrypted Telegram Slip",
                location="Inside Julian's desk blotter",
                surface_description="A torn slip reading 'PHHW DW GRFN IRXU ZLWK FKURQRPHWHU'.",
                forensic_detail=(
                    "Caesar-shifted by +3 letters. Decoded text reads: "
                    "'MEET AT DOCK FOUR WITH CHRONOMETER', addressed to a harbor smuggler "
                    "known to work with Marcus Sterling's creditors."
                ),
                cipher_text="PHHW DW GRFN IRXU ZLWK FKURQRPHWHU",
                links_to_suspect="Marcus Sterling",
            ),
            Clue(
                clue_id="clue_3",
                title="Breaker Panel Log",
                location="Sub-basement electrical room",
                surface_description="The master power switch was tripped manually at 21:28.",
                forensic_detail=(
                    "A dry wool cuff fiber caught on the lever matches the navy cashmere "
                    "jacket worn on the East Balcony—yet the balcony telephone line had zero "
                    "outgoing calls between 21:20 and 21:40, falsifying Sterling's alibi."
                ),
                links_to_suspect="Marcus Sterling",
            ),
            Clue(
                clue_id="clue_4",
                title="Restorer's Ledger Note",
                location="West Gallery workbench",
                surface_description="Ink annotations correcting serial numbers on a 1790 ledger.",
                forensic_detail=(
                    "The ink was still wet at 21:35 according to humidity smudge tests, "
                    "corroborating that Clara Vance remained at her workbench during the blackout."
                ),
                fingerprint_sample="FP-VANCE-104",
                links_to_suspect=None,
            ),
        ],
        solution=SealedSolution(
            culprit_name="Marcus Sterling",
            true_motive=(
                "Desperate to pay $400,000 in midnight gambling debts, he cut power to steal "
                "the Eclipse Chronometer and sell it at Dock Four."
            ),
            method=(
                "Tripped the sub-basement breaker at 21:28, forced the vault override gear at "
                "21:32 during the blackout, and faked an East Balcony phone alibi."
            ),
            key_clue_ids=["clue_1", "clue_2", "clue_3"],
        ),
    ),
    "scifi": CaseDossier(
        case_id="case_scifi_orbital",
        title="Signal Lost on Orbital Station Helion",
        theme="scifi",
        difficulty="standard",
        setting="Helion-7 Deep-Space Research Station in lunar orbit",
        victim="Commander Priya Nair, Chief Telemetry Officer (sedated, navigation core sabotaged)",
        time_of_crime="03:15",
        opening_brief=(
            "At 03:15 UTC, Helion-7's quantum navigation core went offline and Commander Nair "
            "was found sedated in the telemetry bay. Only three crew members held biometric "
            "clearance for Deck C during the night cycle."
        ),
        suspects=[
            Suspect(
                name="Dr. Kenji Sato",
                role="Propulsion physicist",
                personality="Methodical, anxious, eager to prove innocence",
                claimed_alibi="Running plasma diagnostics in Reactor Bay 2",
                alibi_window="03:00-03:30",
                secret="He hid a minor coolant leak to avoid delaying the mission.",
                motive="Nair planned to scrub his propulsion burn test.",
                fingerprint_id="FP-SATO-401",
            ),
            Suspect(
                name="Sora Lindqvist",
                role="Corporate liaison from Aether Dynamics",
                personality="Cool, calculating, quotes corporate protocol",
                claimed_alibi="Asleep in Habitation Pod 4",
                alibi_window="02:30-03:45",
                secret="She carries an unauthorized orbital trajectory override chip.",
                motive="Diverting Helion-7 protects Aether Dynamics' patent claim on an asteroid.",
                fingerprint_id="FP-LINDQVIST-512",
            ),
            Suspect(
                name="Mateo Cruz",
                role="Systems engineer",
                personality="Blunt, sarcastic, fiercely protective of the crew",
                claimed_alibi="Replacing air scrubbers in Hydroponics",
                alibi_window="03:05-03:35",
                secret="He bypassed crew comms quotas to message his family on Earth.",
                motive="Nair reprimanded him formally earlier in the shift.",
                fingerprint_id="FP-CRUZ-628",
            ),
        ],
        clues=[
            Clue(
                clue_id="clue_1",
                title="Tampered Biometric Scanner",
                location="Deck C Telemetry Airlock",
                surface_description="A faint resin film across the optical thumb pad.",
                forensic_detail=(
                    "Lab analysis identifies synthetic glove polymer bearing partial ridge "
                    "transfer FP-LINDQVIST-512 logged at 03:12 UTC."
                ),
                fingerprint_sample="FP-LINDQVIST-512",
                links_to_suspect="Sora Lindqvist",
            ),
            Clue(
                clue_id="clue_2",
                title="Encrypted Burst Transmission",
                location="Telemetry buffer cache",
                surface_description="Queued burst string: 'GLYHUW KHOLRQ WR VHFWRU QLQH'.",
                forensic_detail=(
                    "Caesar +3 cipher decodes to 'DIVERT HELION TO SECTOR NINE', signed with "
                    "an Aether Dynamics executive key."
                ),
                cipher_text="GLYHUW KHOLRQ WR VHFWRU QLQH",
                links_to_suspect="Sora Lindqvist",
            ),
            Clue(
                clue_id="clue_3",
                title="Habitation Pod Door Sensor",
                location="Deck B Corridor Logs",
                surface_description="Pod 4 lock shows a manual maintenance override at 03:08.",
                forensic_detail=(
                    "Pod 4's oxygen sensor dropped to unoccupied baseline from 03:08 to 03:24, "
                    "proving Sora Lindqvist was NOT asleep inside her pod."
                ),
                links_to_suspect="Sora Lindqvist",
            ),
        ],
        solution=SealedSolution(
            culprit_name="Sora Lindqvist",
            true_motive=(
                "Acting for Aether Dynamics, she sabotaged the navigation core to divert "
                "Helion-7 toward Sector Nine before a rival claim expired."
            ),
            method=(
                "Left Habitation Pod 4 via maintenance override at 03:08, accessed Deck C "
                "at 03:12, sedated Commander Nair, and queued the trajectory burst."
            ),
            key_clue_ids=["clue_1", "clue_2", "clue_3"],
        ),
    ),
}

# Forensics reference databases consumed by both the MCP server and local tools
FINGERPRINT_DATABASE: dict[str, dict[str, str]] = {
    "FP-VANCE-104": {
        "owner": "Clara Vance",
        "confidence": "99.1%",
        "notes": "Fine horology oil residue consistent with workbench calibration.",
    },
    "FP-STERLING-209": {
        "owner": "Marcus Sterling",
        "confidence": "98.7%",
        "notes": "High-pressure smudge pattern consistent with forcing a brass latch.",
    },
    "FP-ROSTOVA-317": {
        "owner": "Dr. Elena Rostova",
        "confidence": "99.4%",
        "notes": "Archive dust traces; matches ledger handling.",
    },
    "FP-SATO-401": {
        "owner": "Dr. Kenji Sato",
        "confidence": "98.9%",
        "notes": "Trace ionized coolant residue from Reactor Bay 2.",
    },
    "FP-LINDQVIST-512": {
        "owner": "Sora Lindqvist",
        "confidence": "99.3%",
        "notes": "Synthetic polymer transfer from biometric bypass film.",
    },
    "FP-CRUZ-628": {
        "owner": "Mateo Cruz",
        "confidence": "99.0%",
        "notes": "Hydroponic nutrient salt trace consistent with scrubber repair.",
    },
}

ALIBI_TELEMETRY_RECORDS: dict[str, dict[str, str | bool]] = {
    "clara vance": {
        "verified": True,
        "source": "West Gallery ink-drying & acoustic sensor",
        "detail": "Continuous bench activity recorded 21:15-21:45.",
    },
    "marcus sterling": {
        "verified": False,
        "source": "East Balcony telecom switchboard",
        "detail": "Zero calls placed or received on East Balcony line 21:20-21:40.",
    },
    "dr. elena rostova": {
        "verified": True,
        "source": "Archive Room keycard badge log",
        "detail": "Badge remained docked inside Archive terminal 21:12-21:43.",
    },
    "dr. kenji sato": {
        "verified": True,
        "source": "Reactor Bay 2 console audit",
        "detail": "Interactive console keystrokes logged continuously 03:02-03:29.",
    },
    "sora lindqvist": {
        "verified": False,
        "source": "Habitation Pod 4 O2 & door sensor",
        "detail": "Pod 4 unoccupied from 03:08 to 03:24 after manual door override.",
    },
    "mateo cruz": {
        "verified": True,
        "source": "Hydroponics airflow telemetry",
        "detail": "Scrubber filter swap confirmed via pressure drop at 03:16.",
    },
}


def get_curated_case(theme: str = "noir") -> CaseDossier:
    """Return a deep copy of a curated mystery case matching the requested theme."""
    normalized = theme.strip().lower()
    if any(k in normalized for k in ("sci", "space", "orbit", "station", "future")):
        return CURATED_CASES["scifi"].model_copy(deep=True)
    return CURATED_CASES["noir"].model_copy(deep=True)
