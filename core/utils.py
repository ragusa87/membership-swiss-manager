from decimal import Decimal


def chf_to_centimes(value) -> int:
    return int(Decimal(str(value)) * 100)
