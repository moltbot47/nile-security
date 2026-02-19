"""Seed script — populates database with initial person profiles and soul tokens."""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from nile.config import settings
from nile.models.person import Person
from nile.models.soul_token import SoulToken

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_PERSONS = [
    {
        "display_name": "LeBron James",
        "slug": "lebron-james",
        "bio": "4x NBA Champion, all-time leading scorer. Cultural icon and media mogul.",
        "verification_level": "premium",
        "category": "athlete",
        "tags": ["nba", "basketball", "lakers", "media"],
        "social_links": {"twitter": "KingJames", "instagram": "kingjames"},
        "nile_name_score": 95,
        "nile_image_score": 90,
        "nile_likeness_score": 88,
        "nile_essence_score": 92,
        "nile_total_score": 91.25,
        "token_name": "LeBron Token",
        "token_symbol": "BRON",
        "price_eth": 0.0058,
        "price_usd": 14.50,
        "market_cap": 2_500_000,
        "supply": 172_413,
        "reserve": 8.5,
        "volume": 125_000,
        "holders": 847,
    },
    {
        "display_name": "Taylor Swift",
        "slug": "taylor-swift",
        "bio": "Grammy-winning artist, cultural phenomenon. Eras Tour highest-grossing tour ever.",
        "verification_level": "premium",
        "category": "musician",
        "tags": ["music", "pop", "songwriter", "grammy"],
        "social_links": {"twitter": "taylorswift13", "instagram": "taylorswift"},
        "nile_name_score": 92,
        "nile_image_score": 94,
        "nile_likeness_score": 90,
        "nile_essence_score": 86,
        "nile_total_score": 90.50,
        "token_name": "Swift Token",
        "token_symbol": "SWIFT",
        "price_eth": 0.00892,
        "price_usd": 22.30,
        "market_cap": 4_100_000,
        "supply": 183_856,
        "reserve": 12.2,
        "volume": 210_000,
        "holders": 1_234,
    },
    {
        "display_name": "MrBeast",
        "slug": "mrbeast",
        "bio": "YouTube's most subscribed creator. Philanthropist and entrepreneur.",
        "verification_level": "verified",
        "category": "creator",
        "tags": ["youtube", "philanthropy", "content", "feastables"],
        "social_links": {"twitter": "MrBeast", "instagram": "mrbeast"},
        "nile_name_score": 82,
        "nile_image_score": 85,
        "nile_likeness_score": 78,
        "nile_essence_score": 88,
        "nile_total_score": 83.25,
        "token_name": "Beast Token",
        "token_symbol": "BEAST",
        "price_eth": 0.00324,
        "price_usd": 8.10,
        "market_cap": 980_000,
        "supply": 120_987,
        "reserve": 4.1,
        "volume": 65_000,
        "holders": 512,
    },
    {
        "display_name": "Elon Musk",
        "slug": "elon-musk",
        "bio": "CEO of Tesla and SpaceX. Owner of X. Leading Mars colonization.",
        "verification_level": "premium",
        "category": "entrepreneur",
        "tags": ["tech", "space", "tesla", "ai"],
        "social_links": {"twitter": "elonmusk"},
        "nile_name_score": 90,
        "nile_image_score": 72,
        "nile_likeness_score": 85,
        "nile_essence_score": 94,
        "nile_total_score": 85.25,
        "token_name": "Musk Token",
        "token_symbol": "MUSK",
        "price_eth": 0.01248,
        "price_usd": 31.20,
        "market_cap": 6_200_000,
        "supply": 198_717,
        "reserve": 18.5,
        "volume": 340_000,
        "holders": 2_100,
    },
    {
        "display_name": "Zendaya",
        "slug": "zendaya",
        "bio": "Emmy-winning actress. Stars in Euphoria, Dune, and Spider-Man. Fashion icon.",
        "verification_level": "verified",
        "category": "actor",
        "tags": ["acting", "fashion", "euphoria", "dune"],
        "social_links": {"twitter": "Zendaya", "instagram": "zendaya"},
        "nile_name_score": 80,
        "nile_image_score": 92,
        "nile_likeness_score": 82,
        "nile_essence_score": 78,
        "nile_total_score": 83.00,
        "token_name": "Zendaya Token",
        "token_symbol": "ZEN",
        "price_eth": 0.00276,
        "price_usd": 6.90,
        "market_cap": 720_000,
        "supply": 104_347,
        "reserve": 3.2,
        "volume": 42_000,
        "holders": 389,
    },
    {
        "display_name": "Patrick Mahomes",
        "slug": "patrick-mahomes",
        "bio": "3x Super Bowl Champion, 3x MVP. Kansas City Chiefs quarterback.",
        "verification_level": "verified",
        "category": "athlete",
        "tags": ["nfl", "football", "chiefs", "quarterback"],
        "social_links": {"twitter": "PatrickMahomes", "instagram": "patrickmahomes"},
        "nile_name_score": 85,
        "nile_image_score": 86,
        "nile_likeness_score": 84,
        "nile_essence_score": 90,
        "nile_total_score": 86.25,
        "token_name": "Mahomes Token",
        "token_symbol": "MAHM",
        "price_eth": 0.00472,
        "price_usd": 11.80,
        "market_cap": 1_800_000,
        "supply": 152_542,
        "reserve": 6.8,
        "volume": 95_000,
        "holders": 678,
    },
    {
        "display_name": "Lionel Messi",
        "slug": "lionel-messi",
        "bio": "8x Ballon d'Or winner. World Cup champion. Greatest footballer of all time.",
        "verification_level": "premium",
        "category": "athlete",
        "tags": ["soccer", "football", "mls", "worldcup"],
        "social_links": {"twitter": "TeamMessi", "instagram": "leomessi"},
        "nile_name_score": 96,
        "nile_image_score": 95,
        "nile_likeness_score": 92,
        "nile_essence_score": 94,
        "nile_total_score": 94.25,
        "token_name": "Messi Token",
        "token_symbol": "MESSI",
        "price_eth": 0.0104,
        "price_usd": 26.00,
        "market_cap": 5_200_000,
        "supply": 200_000,
        "reserve": 16.0,
        "volume": 280_000,
        "holders": 1_890,
    },
    {
        "display_name": "Rihanna",
        "slug": "rihanna",
        "bio": "Multi-platinum recording artist. Fenty Beauty & Savage X Fenty founder.",
        "verification_level": "premium",
        "category": "musician",
        "tags": ["music", "fashion", "fenty", "beauty"],
        "social_links": {"twitter": "rihanna", "instagram": "badgalriri"},
        "nile_name_score": 88,
        "nile_image_score": 93,
        "nile_likeness_score": 87,
        "nile_essence_score": 85,
        "nile_total_score": 88.25,
        "token_name": "Rihanna Token",
        "token_symbol": "RIRI",
        "price_eth": 0.00680,
        "price_usd": 17.00,
        "market_cap": 3_200_000,
        "supply": 188_235,
        "reserve": 10.5,
        "volume": 175_000,
        "holders": 1_045,
    },
]


async def seed(db: AsyncSession) -> None:
    """Insert seed persons and soul tokens if they don't exist."""
    for data in SEED_PERSONS:
        # Check if person exists
        existing = await db.execute(
            select(Person).where(Person.slug == data["slug"])
        )
        if existing.scalar_one_or_none():
            logger.info("Person '%s' already exists, skipping", data["slug"])
            continue

        person = Person(
            id=uuid.uuid4(),
            display_name=data["display_name"],
            slug=data["slug"],
            bio=data["bio"],
            verification_level=data["verification_level"],
            category=data["category"],
            tags=data["tags"],
            social_links=data["social_links"],
            nile_name_score=data["nile_name_score"],
            nile_image_score=data["nile_image_score"],
            nile_likeness_score=data["nile_likeness_score"],
            nile_essence_score=data["nile_essence_score"],
            nile_total_score=data["nile_total_score"],
        )
        db.add(person)
        await db.flush()

        token = SoulToken(
            id=uuid.uuid4(),
            person_id=person.id,
            name=data["token_name"],
            symbol=data["token_symbol"],
            phase="bonding",
            chain="base",
            current_price_eth=data["price_eth"],
            current_price_usd=data["price_usd"],
            market_cap_usd=data["market_cap"],
            total_supply=data["supply"],
            reserve_balance_eth=data["reserve"],
            volume_24h_usd=data["volume"],
            holder_count=data["holders"],
            nile_valuation_total=data["nile_total_score"],
            graduation_threshold_eth=20,
        )
        db.add(token)
        logger.info(
            "Seeded: %s ($%s) — NILE %.2f",
            data["display_name"],
            data["token_symbol"],
            data["nile_total_score"],
        )

    await db.commit()
    logger.info("Seed complete!")


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
