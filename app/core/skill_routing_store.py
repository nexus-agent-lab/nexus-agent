import logging
from collections import defaultdict
from typing import Dict, List, Tuple

from sqlmodel import delete, select

from app.core.db import AsyncSessionLocal
from app.models.skill_routing_anchor import SkillRoutingAnchor

logger = logging.getLogger(__name__)


class SkillRoutingStore:
    @staticmethod
    def build_anchor_payloads(skill: dict) -> List[dict]:
        metadata = skill.get("metadata", {}) or {}
        skill_name = skill.get("name", "")
        payloads: List[dict] = []

        def add_anchor(text: str, anchor_type: str, weight: float) -> None:
            cleaned = str(text).strip()
            if not cleaned:
                return
            payloads.append(
                {
                    "skill_name": skill_name,
                    "anchor_type": anchor_type,
                    "language": "auto",
                    "text": cleaned,
                    "weight": weight,
                    "source": "skill_frontmatter",
                    "enabled": True,
                }
            )

        add_anchor(metadata.get("description", ""), "description", 1.0)

        for keyword in metadata.get("intent_keywords", []) or []:
            add_anchor(keyword, "keyword", 0.8)

        for example in metadata.get("routing_examples", []) or []:
            add_anchor(example, "synthetic_query", 1.15)

        return payloads

    @classmethod
    async def sync_skills(cls, skills: List[dict], embeddings) -> None:
        if embeddings is None:
            logger.warning("Skipping skill routing anchor sync; embeddings client is not available.")
            return

        skill_names = [skill.get("name") for skill in skills if skill.get("name")]
        payloads_by_skill: Dict[str, List[dict]] = {}

        for skill in skills:
            skill_name = skill.get("name")
            if not skill_name:
                continue
            payloads_by_skill[skill_name] = cls.build_anchor_payloads(skill)

        try:
            async with AsyncSessionLocal() as session:
                existing_rows = []
                if skill_names:
                    existing_rows = (
                        (
                            await session.execute(
                                select(SkillRoutingAnchor).where(SkillRoutingAnchor.skill_name.in_(skill_names))
                            )
                        )
                        .scalars()
                        .all()
                    )

                existing_by_skill: Dict[str, List[SkillRoutingAnchor]] = defaultdict(list)
                for row in existing_rows:
                    existing_by_skill[row.skill_name].append(row)

                changed_skill_names: List[str] = []
                anchor_payloads: List[dict] = []

                for skill_name, payloads in payloads_by_skill.items():
                    existing_signature = cls._row_signature(existing_by_skill.get(skill_name, []))
                    new_signature = cls._payload_signature(payloads)
                    if existing_signature == new_signature:
                        continue
                    changed_skill_names.append(skill_name)
                    anchor_payloads.extend(payloads)

                if skill_names:
                    await session.execute(
                        delete(SkillRoutingAnchor).where(~SkillRoutingAnchor.skill_name.in_(skill_names))
                    )
                if changed_skill_names:
                    await session.execute(
                        delete(SkillRoutingAnchor).where(SkillRoutingAnchor.skill_name.in_(changed_skill_names))
                    )
                elif not skill_names:
                    await session.execute(delete(SkillRoutingAnchor))

                if anchor_payloads:
                    vectors = await embeddings.aembed_documents([payload["text"] for payload in anchor_payloads])
                    for payload, vector in zip(anchor_payloads, vectors):
                        session.add(SkillRoutingAnchor(**payload, embedding=vector))

                await session.commit()

            logger.info(
                "Synced %d changed routing anchors across %d skills into pgvector.",
                sum(len(payloads_by_skill[name]) for name in changed_skill_names),
                len(skill_names),
            )
        except Exception as e:
            logger.error("Failed to sync skill routing anchors: %s", e)
            raise

    @classmethod
    async def search(cls, query_vector: List[float], limit: int = 12) -> List[dict]:
        distance_expr = SkillRoutingAnchor.embedding.cosine_distance(query_vector)
        stmt = (
            select(SkillRoutingAnchor, distance_expr.label("distance"))
            .where(SkillRoutingAnchor.enabled == True)  # noqa: E712
            .order_by(distance_expr)
            .limit(limit)
        )

        async with AsyncSessionLocal() as session:
            results = await session.execute(stmt)
            rows = results.all()

        hits: List[dict] = []
        for anchor, distance in rows:
            similarity = 1.0 - float(distance)
            hits.append(
                {
                    "skill_name": anchor.skill_name,
                    "anchor_type": anchor.anchor_type,
                    "text": anchor.text,
                    "weight": anchor.weight,
                    "similarity": similarity,
                    "weighted_score": similarity * anchor.weight,
                }
            )
        return hits

    @staticmethod
    def aggregate_hits(hits: List[dict]) -> List[dict]:
        grouped: Dict[str, List[dict]] = defaultdict(list)
        for hit in hits:
            grouped[hit["skill_name"]].append(hit)

        aggregated: List[dict] = []
        for skill_name, skill_hits in grouped.items():
            sorted_hits = sorted(skill_hits, key=lambda item: item["weighted_score"], reverse=True)
            top_hits = sorted_hits[:3]
            max_score = top_hits[0]["weighted_score"]
            mean_score = sum(item["weighted_score"] for item in top_hits) / len(top_hits)
            aggregated.append(
                {
                    "skill_name": skill_name,
                    "score": max_score + 0.2 * mean_score,
                    "hits": top_hits,
                }
            )

        return sorted(aggregated, key=lambda item: item["score"], reverse=True)

    @staticmethod
    def _payload_signature(payloads: List[dict]) -> List[Tuple[str, str, float, str]]:
        return sorted(
            (item["anchor_type"], item["text"], float(item["weight"]), item.get("source", "")) for item in payloads
        )

    @staticmethod
    def _row_signature(rows: List[SkillRoutingAnchor]) -> List[Tuple[str, str, float, str]]:
        return sorted((row.anchor_type, row.text, float(row.weight), row.source or "") for row in rows)
