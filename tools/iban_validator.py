# -*- coding: utf-8 -*-
"""Austrian IBAN validation and account information extraction.

This module provides utilities for validating Austrian IBANs and extracting
bank code and account number information.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountInfo:
    """Parsed Austrian bank account information.

    Attributes:
        iban: Normalized IBAN (20 characters, starting with AT).
        bank_code: 5-digit bank code (positions 5-9 of IBAN).
        account_number: Account number with leading zeros stripped.
    """

    iban: str
    bank_code: str
    account_number: str


# Austrian IBAN pattern: AT + 18 digits
IBAN_AT_REGEX = re.compile(r"^AT\d{18}$")


def normalize_iban(iban: Optional[str]) -> str:
    """Normalize an IBAN by removing whitespace and converting to uppercase.

    Args:
        iban: Raw IBAN string, may contain spaces and mixed case.

    Returns:
        str: Normalized IBAN with no spaces, uppercase letters.
    """
    if iban is None:
        return ""
    return re.sub(r"\s+", "", iban).upper()


def validate_austrian_iban(iban: str) -> bool:
    """Validate format of an Austrian IBAN.

    Checks that the IBAN starts with "AT" and has exactly 20 characters
    (2 country code + 18 digits).

    Args:
        iban: IBAN to validate (will be normalized first).

    Returns:
        bool: ``True`` if the IBAN matches Austrian format, ``False`` otherwise.

    Note:
        This only validates the format, not the check digits.
    """
    iban_norm = normalize_iban(iban)
    return bool(IBAN_AT_REGEX.match(iban_norm))


def extract_account_info(iban: str) -> AccountInfo:
    """Extract bank code and account number from Austrian IBAN.

    Austrian IBAN structure (20 characters):
    - Positions 0-1: Country code "AT"
    - Positions 2-3: Check digits
    - Positions 4-8: Bank code (5 digits)
    - Positions 9-19: Account number (11 digits)

    Args:
        iban: IBAN to parse. Will be normalized and validated.

    Returns:
        AccountInfo: Parsed account information with IBAN, bank code,
        and account number (with leading zeros stripped).

    Raises:
        ValueError: If the IBAN is not a valid Austrian IBAN format.

    Example:
        >>> info = extract_account_info("AT61 1904 3002 3457 3201")
        >>> info.bank_code
        '19043'
        >>> info.account_number
        '234573201'
    """
    iban_norm = normalize_iban(iban)

    if not iban_norm.startswith("AT") or len(iban_norm) != 20:
        raise ValueError(
            f"Invalid Austrian IBAN: {iban}. "
            f"Expected format: AT + 18 digits (20 chars total)"
        )

    # Extract bank code (positions 4-9, 5 digits)
    bank_code = iban_norm[4:9]

    # Extract account number (positions 9-20, 11 digits)
    # Strip leading zeros but keep at least one digit
    account_number = re.sub(r"^0+", "", iban_norm[9:]) or "0"

    return AccountInfo(
        iban=iban_norm,
        bank_code=bank_code,
        account_number=account_number,
    )
