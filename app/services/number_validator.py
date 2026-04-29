"""Cross-validation of technical numbers against source chunks."""
import re


def extract_technical_numbers(text: str) -> list[dict]:
    """Extract numbers with units: pressures, temps, depths, densities, concentrations."""
    patterns = [
        r'(\d[\d,\.]*)\s*(bar|psi|kPa|MPa|atm)',
        r'(\d[\d,\.]*)\s*(°C|°F|K)',
        r'(\d[\d,\.]*)\s*(m|ft|km)',
        r'(\d[\d,\.]*)\s*(ppg|g/cm³|kg/m³)',
        r'(\d[\d,\.]*)\s*(ppm|ppb|%)',
    ]
    numbers = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            numbers.append({
                "value": match.group(1).replace(",", ""),
                "unit": match.group(2).lower(),
                "context": text[max(0, match.start()-20):match.end()+20]
            })
    return numbers


def validate_numbers_against_chunks(answer_numbers: list[dict], chunks: list[str]) -> dict:
    validations = []
    for num in answer_numbers:
        found = any(
            num["value"] in chunk and num["unit"] in chunk.lower()
            for chunk in chunks
        )
        validations.append({**num, "verified_in_source": found})
    return {
        "all_verified": all(v["verified_in_source"] for v in validations),
        "details": validations,
        "verified_count": sum(1 for v in validations if v["verified_in_source"]),
        "total_count": len(validations)
    }
