import requests

# Default as-of date for eCFR (use a fixed date for reproducible results)
DEFAULT_ECFR_DATE = "2024-02-01"


class ECFRClient:
    """Client for fetching CFR parts from the eCFR API (https://www.ecfr.gov)."""

    @staticmethod
    def get_part(title: int, part: int, as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """Fetches a CFR part from the eCFR API.

        Args:
            title: CFR title (e.g., 21 for Food and Drugs, 45 for Public Welfare).
            part: Part number within the title.
            as_of_date: Date for versioned content (YYYY-MM-DD).

        Returns:
            XML text of the requested part.
        """
        url = f"https://www.ecfr.gov/api/versioner/v1/full/{as_of_date}/title-{title}.xml?part={part}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        raise Exception(f"Failed to fetch eCFR data: {response.status_code}")

    # --- 21 CFR (Food and Drugs) ---

    @staticmethod
    def get_part_11_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """21 CFR Part 11 — Electronic records; electronic signatures."""
        return ECFRClient.get_part(21, 11, as_of_date)

    @staticmethod
    def get_part_50_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """21 CFR Part 50 — Protection of human subjects (informed consent, etc.)."""
        return ECFRClient.get_part(21, 50, as_of_date)

    @staticmethod
    def get_part_56_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """21 CFR Part 56 — Institutional Review Boards (IRBs)."""
        return ECFRClient.get_part(21, 56, as_of_date)

    @staticmethod
    def get_part_58_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """21 CFR Part 58 — Good Laboratory Practice for nonclinical studies."""
        return ECFRClient.get_part(21, 58, as_of_date)

    @staticmethod
    def get_part_211_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """21 CFR Part 211 — cGMP for finished pharmaceuticals."""
        return ECFRClient.get_part(21, 211, as_of_date)

    @staticmethod
    def get_part_312_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """21 CFR Part 312 — Investigational New Drug (IND) application."""
        return ECFRClient.get_part(21, 312, as_of_date)

    @staticmethod
    def get_part_314_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """21 CFR Part 314 — Applications for FDA approval (NDA/ANDA)."""
        return ECFRClient.get_part(21, 314, as_of_date)

    # --- 45 CFR (Public Welfare) — Common Rule ---

    @staticmethod
    def get_part_45_46_text(as_of_date: str = DEFAULT_ECFR_DATE) -> str:
        """45 CFR Part 46 — Protection of human subjects (HHS Common Rule)."""
        return ECFRClient.get_part(45, 46, as_of_date)