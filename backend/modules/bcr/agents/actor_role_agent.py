"""Agent 3: BCRActorRoleAgent — identify entity roles beyond regex.

Performs context-aware entity role identification:
- Extracts organization names from document text
- Maps each entity to: EU liable entity, BCR member, client controller, external recipient
- Links roles to liability clauses, compensation commitments, third-party beneficiary rights
"""

from __future__ import annotations

import re

from backend.modules.bcr.agents import BCRAgentBase


class BCRActorRoleAgent(BCRAgentBase):
    agent_name = "bcr_actor_role"
    max_tokens = 500

    # EU/EEA country patterns for location detection
    _EU_EEA_COUNTRIES = [
        "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech",
        "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
        "Hungary", "Iceland", "Ireland", "Italy", "Latvia", "Liechtenstein",
        "Lithuania", "Luxembourg", "Malta", "Netherlands", "Norway", "Poland",
        "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
    ]

    # Entity detection patterns
    _ENTITY_PATTERNS = [
        r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Ltd|Limited|LLC|Inc|GmbH|SA|NV|BV|SARL|SpA|AG|AB|Oy|AS|PLC|Corp))",
        r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Group|Holdings|International|Europe|Global))",
        r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Data|Tech|Pharma|Finance|Health|Media))",
    ]

    # EU liable entity signals
    _EU_LIABLE_SIGNALS = [
        r"(?:EU\s+)?liable\s+(?:entity|person|member|company)",
        r"responsible\s+(?:for|to)\s+(?:ensuring|guaranteeing)\s+compliance",
        r"headquarters?\s+(?:in|at)\s+(?:" + "|".join(_EU_EEA_COUNTRIES) + r")",
        r"registered\s+(?:office|address)\s+(?:in|at)\s+(?:" + "|".join(_EU_EEA_COUNTRIES) + r")",
        r"shall\s+(?:assume|accept|bear)\s+(?:full\s+)?(?:responsibility|liability)",
        r"acts?\s+as\s+(?:the\s+)?data\s+(?:exporter|controller)\s+(?:for|under)\s+these?\s+(?:Rules|BCR)",
    ]

    # BCR member signals
    _BCR_MEMBER_SIGNALS = [
        r"group\s+(?:member|entity|company|subsidiary|affiliate)",
        r"member\s+of\s+the\s+(?:group|BCR)",
        r"bound\s+by\s+(?:these\s+Rules|the\s+BCR|this\s+BCR)",
        r"shall\s+comply\s+with\s+(?:these\s+Rules|the\s+BCR)",
        r"listed\s+in\s+Annex\s+(?:I|A|1)",
    ]

    # Client controller signals (BCR-P context)
    _CLIENT_CONTROLLER_SIGNALS = [
        r"on\s+behalf\s+of\s+(?:the\s+)?(?:client|data\s+controller)",
        r"(?:client|data\s+controller)\s+(?:shall|may|has|retains)",
        r"according\s+to\s+(?:the\s+)?(?:client[´']?s?|controller[´']?s?)\s+instructions",
        r"representing\s+(?:the\s+)?(?:client|controller)",
    ]

    def run(self, text: str, scenario_context: dict | None = None,
            bcr_type: str = "BCR-C") -> dict:
        """Identify entity roles from BCR document text.

        Returns structured entity list with role assignments.
        """
        entities: list[dict] = []
        eu_liable_entity = None
        has_clear_eu_liable_entity = False

        # ── 1. Extract organization names ──
        found_names: set[str] = set()
        for pattern in self._ENTITY_PATTERNS:
            for m in re.finditer(pattern, text[:15000]):
                name = m.group(0).strip()
                if len(name) > 4 and name not in found_names:
                    found_names.add(name)

        # ── 2. Classify each entity ──
        for name in found_names:
            # Find surrounding context (500 chars around first mention)
            name_idx = text.find(name)
            start = max(0, name_idx - 250)
            end = min(len(text), name_idx + 250)
            context = text[start:end]
            context_lower = context.lower()

            roles: list[str] = []
            evidence: list[str] = []

            # Check EU liable entity signals
            for pattern in self._EU_LIABLE_SIGNALS:
                if re.search(pattern, context_lower):
                    if "EU liable entity" not in roles:
                        roles.append("EU liable entity")
                    evidence.append(f"Matched pattern: {pattern[:60]}")

            # Check whether it's the designated liable entity
            is_liable = "liable entity" in " ".join(roles).lower()

            # Check BCR member signals
            for pattern in self._BCR_MEMBER_SIGNALS:
                if re.search(pattern, context_lower):
                    if "BCR member" not in roles:
                        roles.append("BCR member")
                    if not evidence:
                        evidence.append(f"Matched member pattern: {pattern[:60]}")

            # Check client controller signals
            for pattern in self._CLIENT_CONTROLLER_SIGNALS:
                if re.search(pattern, context_lower):
                    if "client controller" not in roles:
                        roles.append("client controller")
                    if not evidence:
                        evidence.append(f"Matched client pattern: {pattern[:60]}")

            # If no role found, check location for hint
            if not roles:
                for country in self._EU_EEA_COUNTRIES:
                    if country.lower() in context_lower:
                        roles.append("BCR member")
                        evidence.append(f"Located in EU/EEA: {country}")
                        break
                if not roles:
                    roles.append("unknown")
                    evidence.append("No role signals found in context")

            # Detect location
            location = ""
            for country in self._EU_EEA_COUNTRIES:
                if country.lower() in context_lower:
                    location = country
                    break

            if not location:
                loc_match = re.search(r"(?:in|at|located\s+in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", context)
                if loc_match:
                    location = loc_match.group(1)

            entities.append({
                "name": name,
                "location": location,
                "roles": roles,
                "evidence": "; ".join(evidence[:2]),
            })

            # Track primary liable entity
            if is_liable and eu_liable_entity is None:
                eu_liable_entity = name

        # ── 3. Check if clear EU liable entity exists ──
        has_clear_eu_liable_entity = eu_liable_entity is not None

        # ── 4. LLM enhancement if no clear liable entity ──
        if not has_clear_eu_liable_entity and found_names:
            llm_result = self._try_llm_entity_identification(text, list(found_names), bcr_type)
            if llm_result:
                if llm_result.get("eu_liable_entity"):
                    eu_liable_entity = llm_result["eu_liable_entity"]
                    has_clear_eu_liable_entity = True
                if llm_result.get("entities"):
                    for llm_ent in llm_result["entities"]:
                        name = llm_ent.get("name", "")
                        existing = next((e for e in entities if e["name"] == name), None)
                        if existing:
                            existing["roles"] = llm_ent.get("roles", existing["roles"])
                            existing["evidence"] = llm_ent.get("evidence", existing["evidence"])

        return {
            "entities": entities,
            "eu_liable_entity": eu_liable_entity,
            "has_clear_eu_liable_entity": has_clear_eu_liable_entity,
            "total_entities_found": len(entities),
        }

    def _try_llm_entity_identification(self, text: str, entity_names: list[str],
                                        bcr_type: str) -> dict | None:
        prompt = f"""Identify entity roles in this BCR document ({bcr_type}).

Entities detected: {entity_names[:10]}

Text excerpt (first 3000 chars):
{text[:3000]}

Return JSON:
{{
  "eu_liable_entity": "<entity name or null>",
  "entities": [
    {{"name": "<name>", "location": "<country>", "roles": ["EU liable entity" | "BCR member" | "client controller" | "external recipient"], "evidence": "<quote>"}}
  ],
  "has_clear_eu_liable_entity": true | false
}}"""
        return self._call_llm(prompt)
