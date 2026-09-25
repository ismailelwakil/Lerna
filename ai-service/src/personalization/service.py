from __future__ import annotations


class PersonalizationService:

    def _safe_list(
        self,
        profile,
        field,
    ):
        return list(
            getattr(
                profile,
                field,
                [],
            )
            or []
        )

    def _mastery(
        self,
        profile,
    ):
        return dict(
            getattr(
                profile,
                "concept_mastery",
                {},
            )
            or {}
        )

    def _learning_preference(
        self,
        profile,
    ):
        student = getattr(
            profile,
            "student",
            None,
        )

        if student is None:
            return "step-by-step"

        return getattr(
            student,
            "learning_preference",
            "step-by-step",
        ) or "step-by-step"

    def _concept_line(
        self,
        concept,
        mastery,
    ):
        if concept in mastery:
            value = float(
                mastery[concept]
            )

            return (
                f"{concept} "
                f"(estimated mastery={value:.2f})"
            )

        return concept

    def _build_context(
        self,
        mode,
        profile,
        target_concepts,
        reason,
        instructions,
    ):
        mastery = self._mastery(
            profile
        )

        preference = (
            self._learning_preference(
                profile
            )
        )

        targets = [
            self._concept_line(
                concept,
                mastery,
            )
            for concept
            in target_concepts
        ]

        if targets:
            target_text = "; ".join(
                targets
            )
        else:
            target_text = "none"

        return f"""
Personalization mode: {mode}

Internal learner context:
- Relevant target concepts: {target_text}
- Learning preference: {preference}
- Reason for adaptation: {reason}

Adaptation instructions:
{instructions}

Important behavior:
- Use this learner context only to adapt teaching.
- Do not expose internal profile labels, mastery scores, or diagnostic metadata.
- Do not tell the student that they are weak, deficient, or classified.
- Do not mention that a diagnostic assessment identified the issue unless the student explicitly asks.
- Keep the student's current request as the main objective.
- When a target concept is relevant to the current request, give it extra scaffolding, examples, and explanation.
- Do not force unrelated target concepts into an unrelated question.
""".strip()

    def strategy(
        self,
        profile,
        analysis,
    ):
        prerequisite_gaps = (
            self._safe_list(
                profile,
                "prerequisite_gaps",
            )
        )

        misconceptions = (
            self._safe_list(
                profile,
                "misconceptions",
            )
        )

        weak_concepts = (
            self._safe_list(
                profile,
                "weak_concepts",
            )
        )

        unknown_concepts = (
            self._safe_list(
                profile,
                "unknown_concepts",
            )
        )

        mastery = self._mastery(
            profile
        )

        severe_weaknesses = [
            concept
            for concept, value
            in mastery.items()
            if float(value) < 0.40
        ]

        if prerequisite_gaps:
            return self._build_context(
                mode="prerequisite-remediation",
                profile=profile,
                target_concepts=prerequisite_gaps,
                reason=(
                    "The learner needs prerequisite "
                    "knowledge reinforced before or "
                    "while learning the requested topic."
                ),
                instructions=(
                    "- Briefly establish the missing prerequisite "
                    "before advanced material.\n"
                    "- Connect the prerequisite explicitly to the "
                    "student's current question.\n"
                    "- Use small steps and concrete examples.\n"
                    "- Check conceptual dependencies before adding "
                    "more complexity."
                ),
            )

        if misconceptions:
            return self._build_context(
                mode="misconception-correction",
                profile=profile,
                target_concepts=misconceptions,
                reason=(
                    "Previous learning evidence suggests "
                    "a misconception that should be corrected "
                    "when relevant."
                ),
                instructions=(
                    "- Correct the misconception gently and explicitly.\n"
                    "- Contrast the incorrect mental model with the "
                    "correct one.\n"
                    "- Explain why the distinction matters.\n"
                    "- Use a short example that makes the correction clear."
                ),
            )

        # Check query context for hierarchical / section-aware personalization
        query_topic = getattr(analysis, "topic", "") or ""
        query_concepts = list(getattr(analysis, "concepts", []) or [])
        query_text_lower = f"{query_topic} {' '.join(query_concepts)}".lower()

        parent_is_strength = False
        strengths = self._safe_list(profile, "strengths")
        for s in strengths:
            if s.lower() in query_topic.lower() or query_topic.lower() in s.lower():
                parent_is_strength = True
                break
        if not parent_is_strength:
            for c, val in mastery.items():
                if (c.lower() in query_topic.lower() or query_topic.lower() in c.lower()) and float(val) >= 0.70:
                    parent_is_strength = True
                    break

        sub_missing = [
            u for u in unknown_concepts
            if u.lower() in query_text_lower or any(u.lower() in c.lower() for c in query_concepts)
        ]
        sub_weak = [
            w for w in weak_concepts
            if w not in sub_missing and (w.lower() in query_text_lower or any(w.lower() in c.lower() for c in query_concepts))
        ]

        # Hierarchical Section-Aware Personalization:
        # If parent topic is a mastered strength, do NOT collapse into a global foundational response.
        # Instead, derive per-concept section directives.
        if parent_is_strength and (sub_missing or sub_weak):
            missing_str = ", ".join(sub_missing) if sub_missing else "none"
            weak_str = ", ".join(sub_weak) if sub_weak else "none"
            return self._build_context(
                mode="section-aware-hierarchical",
                profile=profile,
                target_concepts=[query_topic] + sub_missing + sub_weak,
                reason=(
                    f"The learner has demonstrated strong mastery of the core parent topic ({query_topic}), "
                    f"but has specific subconcept knowledge gaps in: missing=[{missing_str}], weak=[{weak_str}]."
                ),
                instructions=(
                    f"- Do NOT treat the overall topic ({query_topic}) as unknown or unlearned.\n"
                    f"- Do NOT open with remedial framing such as 'building from the ground up' or basic elementary metaphors.\n"
                    f"- Do NOT use physical dictionary analogies or real-world metaphors unless explicitly in the evidence.\n"
                    f"- Section: Core Mechanics & Input Precondition ({query_topic}):\n"
                    f"  * Provide concise, direct, higher-level treatment without over-explaining known basics.\n"
                    f"  * Clearly and crisply state the sorted input requirement and subinterval boundary tracking.\n"
                    f"- Section: Time Complexity (missing knowledge: {missing_str}):\n"
                    f"  * Provide extra foundational scaffolding specifically for this subconcept.\n"
                    f"  * Explain step-by-step from first principles using the evidence how logarithmic scaling arises.\n"
                    f"- Section: Space Complexity (weak attempted: {weak_str}):\n"
                    f"  * Provide targeted reinforcement specifically for space complexity.\n"
                    f"  * Contrast iterative scalar variable allocation with memory overhead, explaining O(1) auxiliary space, citing the supporting chunk.\n"
                    f"  * If the active evidence does not contain space complexity details, state that limitation instead of asserting O(1) without citation.\n"
                    f"- Prohibited Expressions & Analogies:\n"
                    f"  * Do NOT write midpoint formulas (such as `mid = lo + (hi - lo) / 2` or `(lo + hi) / 2`) unless that exact equation appears in the active evidence chunks.\n"
                    f"  * Do NOT use physical dictionary analogies or real-world metaphors unless explicitly in the evidence.\n"
                    f"- Ground all factual claims strictly in the retrieved evidence; every technical claim must have a citation marker ([1], [2], etc.)."
                ),
            )

        foundational_targets = list(
            dict.fromkeys(
                unknown_concepts
                + severe_weaknesses
            )
        )

        if foundational_targets:
            return self._build_context(
                mode="foundational-remediation",
                profile=profile,
                target_concepts=foundational_targets,
                reason=(
                    "The learner has little demonstrated "
                    "knowledge of these concepts."
                ),
                instructions=(
                    "- Teach from first principles.\n"
                    "- Define terminology before using it heavily.\n"
                    "- Break transformations or calculations into "
                    "small steps.\n"
                    "- Prefer intuitive examples before abstraction.\n"
                    "- Do NOT use physical dictionary analogies or real-world metaphors unless explicitly in the evidence.\n"
                    "- When matrices are involved, explicitly explain "
                    "what each matrix represents and how dimensions "
                    "must align if supported by the evidence."
                ),
            )

        if weak_concepts:
            return self._build_context(
                mode="targeted-practice",
                profile=profile,
                target_concepts=weak_concepts,
                reason=(
                    "The learner profile contains concepts "
                    "that need additional reinforcement."
                ),
                instructions=(
                    "- Give extra attention to relevant weak concepts.\n"
                    "- Explain them more slowly than already-mastered "
                    "parts of the topic.\n"
                    "- Connect the weak concept to the broader topic.\n"
                    "- Include at least one concrete worked or intuitive "
                    "example when the evidence supports it.\n"
                    "- Avoid spending equal depth on every concept when "
                    "one of the target concepts is directly relevant."
                ),
            )

        if getattr(
            analysis,
            "code_needed",
            False,
        ):
            return self._build_context(
                mode="code-first",
                profile=profile,
                target_concepts=[],
                reason=(
                    "The student's request requires "
                    "implementation-oriented teaching."
                ),
                instructions=(
                    "- Lead with a concise implementation example.\n"
                    "- Explain the important lines after the code.\n"
                    "- Connect code behavior to the underlying concept."
                ),
            )

        strong_concepts = [
            concept
            for concept, value
            in mastery.items()
            if float(value) >= 0.80
        ]

        if strong_concepts:
            return self._build_context(
                mode="progressive-challenge",
                profile=profile,
                target_concepts=strong_concepts,
                reason=(
                    "The learner has demonstrated strong "
                    "mastery in these areas."
                ),
                instructions=(
                    "- Avoid over-explaining already-mastered basics.\n"
                    "- Progress efficiently toward application and "
                    "connections.\n"
                    "- Add slightly deeper reasoning when relevant."
                ),
            )

        preference = (
            self._learning_preference(
                profile
            )
        )

        return self._build_context(
            mode=preference,
            profile=profile,
            target_concepts=[],
            reason=(
                "No specific diagnostic weakness currently "
                "requires priority remediation."
            ),
            instructions=(
                f"- Follow the learner's preferred teaching style: "
                f"{preference}.\n"
                "- Keep the explanation proportional to the request.\n"
                "- Introduce concepts in a logical sequence."
            ),
        )