def analyze_research_gap(topic: str):

    topic_clean = topic.strip()

    topic_lower = topic_clean.lower()


    # --------------------------------------------------
    # Research Area Detection
    # --------------------------------------------------

    research_area = "General Computer Science"


    if any(
        keyword in topic_lower
        for keyword in [
            "computer vision",
            "image processing",
            "object detection",
            "yolo",
            "cnn"
        ]
    ):

        research_area = (
            "Computer Vision / Deep Learning"
        )


    elif any(
        keyword in topic_lower
        for keyword in [
            "machine learning",
            "deep learning",
            "artificial intelligence",
            "ai"
        ]
    ):

        research_area = (
            "Artificial Intelligence / Machine Learning"
        )


    elif any(
        keyword in topic_lower
        for keyword in [
            "blockchain",
            "smart contract",
            "defi"
        ]
    ):

        research_area = "Blockchain"


    elif any(
        keyword in topic_lower
        for keyword in [
            "cybersecurity",
            "cyber security",
            "malware",
            "intrusion"
        ]
    ):

        research_area = "Cybersecurity"


    # --------------------------------------------------
    # Identify Potential Research Gaps
    # --------------------------------------------------

    identified_gaps = []


    # Dataset Gap

    if any(
        keyword in topic_lower
        for keyword in [
            "detection",
            "classification",
            "prediction",
            "recognition"
        ]
    ):

        identified_gaps.append(

            "Dataset diversity and representation "
            "may be a potential research gap."

        )


    # Real-Time Gap

    if (
        "real-time" in topic_lower
        or "real time" in topic_lower
    ):

        identified_gaps.append(

            "Real-time performance, latency, and "
            "computational efficiency can be investigated."

        )

    else:

        identified_gaps.append(

            "Real-time deployment and computational "
            "efficiency can be investigated as possible "
            "research directions."

        )


    # Explainability Gap

    if not any(
        keyword in topic_lower
        for keyword in [
            "explainable",
            "explainability",
            "interpretable"
        ]
    ):

        identified_gaps.append(

            "Explainability and interpretability of "
            "the proposed approach could be investigated."

        )


    # State-of-the-Art Comparison Gap

    identified_gaps.append(

        "Performance comparison with recent "
        "state-of-the-art methods should be investigated."

    )


    # --------------------------------------------------
    # Gap Summary
    # --------------------------------------------------

    gap_summary = (

        f"Potential research gaps were identified "
        f"in the area of {research_area}. "

        "These gaps are preliminary and must be "
        "validated against recent research literature."

    )


    # --------------------------------------------------
    # Research Direction
    # --------------------------------------------------

    research_direction = (

        "Conduct a systematic literature review and "
        "compare existing datasets, methodologies, "
        "limitations, and evaluation metrics to "
        "identify a defensible research gap."

    )


    return {

        "topic": topic_clean,

        "research_area": research_area,

        "identified_gaps": identified_gaps,

        "gap_summary": gap_summary,

        "research_direction": research_direction

    }