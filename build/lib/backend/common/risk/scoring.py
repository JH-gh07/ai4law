def risk_level(is_ciio: bool, contains_important_data: bool, pii_count: int, spi_count: int) -> str:
    if is_ciio or contains_important_data or pii_count >= 1_000_000 or spi_count >= 10_000:
        return "HIGH"
    if pii_count >= 100_000:
        return "MEDIUM"
    return "LOW"
