# random, fake, test data, names, csv, json, generator

from pathlib import Path
from typing import Literal
import csv
import json
from faker import Faker


def random_data_generator(
    rows: int = 20,
    kind: Literal["people", "companies", "addresses", "products", "credit_cards_test", "sentences"] = "people",
    output: Literal["csv", "json"] = "csv",
    locale: Literal["en_US", "en_GB", "de_DE", "fr_FR", "es_ES", "it_IT", "ja_JP"] = "en_US",
) -> Path:
    """Generate realistic-looking fake data for testing: people (name, email, phone,
    birthday...), companies, addresses, products with prices, test credit card
    numbers, or sentences.
    """
    fake = Faker(locale)
    rows = max(1, min(rows, 5000))
    makers = {
        "people": lambda: {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "birthday": fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
            "job": fake.job(),
            "city": fake.city(),
        },
        "companies": lambda: {
            "company": fake.company(),
            "slogan": fake.catch_phrase(),
            "domain": fake.domain_name(),
            "industry": fake.bs(),
            "founded": fake.year(),
            "country": fake.country(),
        },
        "addresses": lambda: {
            "street": fake.street_address(),
            "city": fake.city(),
            "postcode": fake.postcode(),
            "country": fake.country(),
            "latitude": float(fake.latitude()),
            "longitude": float(fake.longitude()),
        },
        "products": lambda: {
            "sku": fake.bothify("??-#####").upper(),
            "name": fake.catch_phrase(),
            "color": fake.color_name(),
            "price": round(fake.pyfloat(min_value=1, max_value=500), 2),
            "in_stock": fake.pybool(),
            "ean": fake.ean13(),
        },
        "credit_cards_test": lambda: {
            "provider": fake.credit_card_provider(),
            "number": fake.credit_card_number(),
            "expiry": fake.credit_card_expire(),
            "name": fake.name(),
        },
        "sentences": lambda: {
            "sentence": fake.sentence(nb_words=12),
            "words": fake.sentence(nb_words=12).count(" ") + 1,
        },
    }
    records = [makers[kind]() for _ in range(rows)]
    out = Path(f"fake_{kind}_{rows}.{output}")
    if output == "json":
        out.write_text(json.dumps(records, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    else:
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    return out
